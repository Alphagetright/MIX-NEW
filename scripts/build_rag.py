# -*- coding: utf-8 -*-
"""
RAG 向量数据库构建脚本
"""
import os
import json
import time
import shutil

import chromadb
import requests

from config import (
    EMBED_API_URL, EMBED_MODEL, RAG_DB_DIR, RAG_COLLECTION_NAME,
    POEMS_JSON_DIR, EMBEDDING_RETRIES, EMBEDDING_TIMEOUT,
)
from errors import EmbeddingError
from logger import get_logger

logger = get_logger("build_rag")

POEMS_DIR = POEMS_JSON_DIR


def get_embedding(text, retries=EMBEDDING_RETRIES):
    """获取文本向量，带重试"""
    for attempt in range(retries):
        try:
            response = requests.post(
                EMBED_API_URL,
                json={"model": EMBED_MODEL, "input": text},
                timeout=EMBEDDING_TIMEOUT,
            )
            if response.status_code == 200:
                return response.json()["data"][0]["embedding"]
            else:
                logger.warning(f"API 异常: {response.status_code}，重试 {attempt+1}")
                time.sleep(2)
        except requests.RequestException as e:
            logger.warning(f"请求失败: {e}，重试 {attempt+1}")
            time.sleep(2)
    raise EmbeddingError(f"向量化失败，已重试 {retries} 次")


def main():
    """主构建流程"""
    if os.path.exists(RAG_DB_DIR):
        shutil.rmtree(RAG_DB_DIR)
        logger.info(f"已清除旧向量库: {RAG_DB_DIR}")

    logger.info(f"RAG 向量库构建启动")
    logger.info(f"读取目录: {POEMS_DIR}")
    logger.info(f"保存至: {RAG_DB_DIR}")

    client = chromadb.PersistentClient(path=RAG_DB_DIR)
    collection = client.get_or_create_collection(
        name=RAG_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    if not os.path.exists(POEMS_DIR):
        logger.error(f"数据目录不存在: {POEMS_DIR}")
        return

    all_files = [f for f in os.listdir(POEMS_DIR) if f.endswith(".json")]
    logger.info(f"共发现 {len(all_files)} 个文件")

    success_count = 0
    error_count = 0

    for filename in all_files:
        file_path = os.path.join(POEMS_DIR, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"读取失败: {filename} | {e}")
            error_count += 1
            continue

        poems_in_file = data.get("诗歌集", [data]) if isinstance(data, dict) else data

        for poem in poems_in_file:
            pid = poem.get("诗歌编号", "")
            title = poem.get("标题", "未知")
            author = poem.get("作者", "未知")
            text = poem.get("原文", "")

            if not text or not pid:
                logger.warning(f"跳过空内容或无编号: {title}")
                continue

            logger.info(f"[{pid}] 《{title}》| {author} | {len(text)}字")

            try:
                vector = get_embedding(text)
            except EmbeddingError:
                logger.error(f"向量化失败，跳过: {pid}")
                error_count += 1
                continue

            try:
                collection.add(
                    ids=[pid],
                    embeddings=[vector],
                    documents=[text],
                    metadatas=[{"标题": title, "作者": author, "诗歌编号": pid}],
                )
                logger.info(f"入库成功: {pid}")
                success_count += 1
            except Exception as e:
                logger.error(f"入库失败: {pid} | {e}")
                error_count += 1

            time.sleep(0.3)

    logger.info(f"构建完成！成功: {success_count} | 失败: {error_count}")


if __name__ == "__main__":
    main()
