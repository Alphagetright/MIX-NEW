# -*- coding: utf-8 -*-
"""
RAG 检索与流式问答引擎
"""
import json

import chromadb
import requests

from config import (
    EMBED_API_URL, CHAT_API_URL, EMBED_MODEL, CHAT_MODEL,
    RAG_DB_DIR, RAG_COLLECTION_NAME, TOP_K, KNOWN_AUTHORS,
    EMBEDDING_RETRIES, EMBEDDING_TIMEOUT, CHAT_TIMEOUT,
)
from errors import EmbeddingError, LLMError
from logger import get_logger

logger = get_logger("query_rag")


def get_embedding(text):
    """获取文本向量"""
    for attempt in range(EMBEDDING_RETRIES):
        try:
            response = requests.post(
                EMBED_API_URL,
                json={"model": EMBED_MODEL, "input": text},
                timeout=EMBEDDING_TIMEOUT,
            )
            if response.status_code == 200:
                return response.json()["data"][0]["embedding"]
            else:
                logger.warning(f"Embedding API 异常: {response.status_code}，重试 {attempt+1}")
        except requests.RequestException as e:
            logger.warning(f"Embedding 请求失败: {e}，重试 {attempt+1}")
    raise EmbeddingError(f"向量化失败，已重试 {EMBEDDING_RETRIES} 次")


def extract_intent(question):
    """从问题中提取意图（检测诗人、清理无关词）"""
    detected_author = None
    for author in KNOWN_AUTHORS:
        if author in question:
            detected_author = author
            break
    clean_question = question
    if detected_author:
        clean_question = question.replace(detected_author, "").strip()
    for word in ["写过", "写了", "哪些", "有哪些", "的诗", "哪首", "什么诗", "请问", "帮我找"]:
        clean_question = clean_question.replace(word, "").strip()
    if not clean_question:
        clean_question = question
    return detected_author, clean_question


def search_poems(question, top_k=TOP_K):
    """在向量库中检索相关诗歌"""
    client = chromadb.PersistentClient(path=RAG_DB_DIR)
    collection = client.get_or_create_collection(
        name=RAG_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    detected_author, semantic_query = extract_intent(question)
    vector = get_embedding(semantic_query)

    if detected_author:
        try:
            results = collection.query(
                query_embeddings=[vector],
                n_results=top_k,
                where={"作者": detected_author},
            )
        except Exception:
            logger.warning(f"按作者过滤失败，回退到无过滤检索")
            results = collection.query(
                query_embeddings=[vector],
                n_results=top_k,
            )
    else:
        results = collection.query(
            query_embeddings=[vector],
            n_results=top_k,
        )

    poems = []
    for i in range(len(results["documents"][0])):
        poems.append({
            "原文": results["documents"][0][i],
            "标题": results["metadatas"][0][i].get("标题", ""),
            "作者": results["metadatas"][0][i].get("作者", ""),
            "相似度": round(1 - results["distances"][0][i], 3),
        })
    return poems


def _stream_chat_completion(messages, temperature=0.7, max_tokens=20000):
    """流式调用大模型"""
    try:
        response = requests.post(
            CHAT_API_URL,
            json={
                "model": CHAT_MODEL,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            },
            timeout=CHAT_TIMEOUT,
            stream=True,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise LLMError(f"大模型服务请求失败: {e}")

    for line in response.iter_lines():
        if not line:
            continue
        line_text = line.decode("utf-8")
        if line_text.startswith("data: "):
            line_text = line_text[6:]
        if line_text == "[DONE]":
            break
        try:
            chunk = json.loads(line_text)
            if not chunk.get("choices"):
                continue
            delta = chunk["choices"][0].get("delta", {})
            content = delta.get("content", "")
            if content:
                yield content
        except json.JSONDecodeError:
            continue


def build_context_block(poems):
    """构建检索到的诗歌上下文"""
    parts = []
    for p in poems:
        parts.append(f"《{p['标题']}》{p['作者']}\n{p['原文']}\n")
    return "\n".join(parts)


def _build_rag_messages(question, history):
    """构建 RAG 问答的消息列表"""
    history = history or []
    system = (
        "你是一位精通中国古典诗歌意象分析的学者，回答详尽准确，"
        "严格基于提供的资料，结合诗句原文进行分析。"
    )
    if not history:
        poems = search_poems(question)
        if not poems:
            return None, None
        ctx = build_context_block(poems)
        user_content = (
            f"你是一位精通中国古典诗歌的学者，请基于以下检索到的诗歌资料详细回答问题。\n"
            f"回答时请结合具体诗句分析，给出深入的文学解读。\n"
            f"注意：只基于提供的诗歌资料回答，不要编造不在资料中的诗歌。\n\n"
            f"诗歌资料：\n{ctx}\n\n问题：{question}\n\n请详细回答："
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]
        return messages, poems

    messages = [{"role": "system", "content": system}]
    for h in history:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": question})
    return messages, None


def stream_rag_answer_events(question, history=None):
    """
    首轮：先 yield {"type":"poems","poems":[...]}，再 yield {"type":"chunk","text":"..."}
    后续轮：仅 yield chunk。无检索结果时仅 yield poems 空列表后结束。
    """
    messages, poems = _build_rag_messages(question, history)
    history = history or []
    if not history:
        yield {"type": "poems", "poems": poems or []}
        if not messages:
            return
    else:
        if not messages:
            return
    for c in _stream_chat_completion(messages):
        yield {"type": "chunk", "text": c}


def stream_rag_answer(question, history=None):
    """纯文本流，供命令行使用"""
    for ev in stream_rag_answer_events(question, history):
        if ev.get("type") == "chunk" and ev.get("text"):
            yield ev["text"]


def stream_cognitive_analysis(system_prompt, history=None, followup=None):
    """
    认知诗学意象解析：
    首轮：user 为 followup，缺省则使用默认解析指令。
    追问：history 为完整对话；followup 为新一轮用户输入。
    """
    history = history or []
    default_first_user = "请从认知诗学角度深度解析这个意象在诗歌中的多维功能。"
    if not history:
        user_msg = (followup or "").strip() or default_first_user
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]
    else:
        messages = [{"role": "system", "content": system_prompt}]
        for h in history:
            if h.get("role") in ("user", "assistant") and h.get("content"):
                messages.append({"role": h["role"], "content": h["content"]})
        q = (followup or "").strip() or "请继续从认知诗学角度补充分析。"
        messages.append({"role": "user", "content": q})
    yield from _stream_chat_completion(messages, temperature=0.65)


def ask(question):
    """命令行交互入口"""
    logger.info(f"问答: {question}")
    print(f"\n❓ 问题：{question}")
    print("=" * 60)
    out = []
    for c in stream_rag_answer(question, None):
        out.append(c)
    print("".join(out))
    return "".join(out)


if __name__ == "__main__":
    ask("杜甫写过哪些关于秋天的诗？")
