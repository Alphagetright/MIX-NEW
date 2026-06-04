# -*- coding: utf-8 -*-
"""连接 LM Studio 本地模型，多线程批量分类杜甫诗歌"""
import json, os, sys, re, time, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.stdout.reconfigure(encoding='utf-8')

POEM_JSON_DIR = r"C:\Users\Administrator\Desktop\All Mix\poem_json"
LMSTUDIO_URL = "http://127.0.0.1:44787/v1/chat/completions"

# 分类规则http://127.0.0.1:44787
RULES = """边塞征战：边塞风光、将士思乡、战争实录、从军建功。
山水田园：自然景观、隐逸生活、农家情趣、四时之景。
咏史怀古：凭吊古迹、王朝兴衰、政治理想、借古讽今。
托物言志：人格象征（梅兰竹菊等）、政治寓托、人生志向。
送别酬赠：友人离别、席间唱和、友情寄托。
思乡怀人：羁旅愁思、客中思家、亲友怀念。
闺怨宫怨：女子哀怨、宫廷生活、相思之苦。
哲理感悟：人生哲理、禅意境界、世事洞察。"""

SYSTEM_PROMPT = f"""你是一个唐诗题材分类专家。请为以下杜甫诗歌标注题材分类。

分类标准（严格按此执行）：
{RULES}

输出格式：每行一个 JSON 对象，不要换行，不要 markdown，不要多余文字，只要纯 JSON 行：
{{"诗歌编号":"D0001","标题":"望岳","分类标签":"山水田园-自然景观"}}

标签格式：大类-子类，例如"山水田园-自然景观"、"边塞征战-战争实录"。
必须严格对应上面的分类标准，不要自创分类。"""

def load_poems():
    """加载所有尚未分类的 D 开头诗歌"""
    poems = []
    for fn in sorted(os.listdir(POEM_JSON_DIR)):
        if not fn.startswith('D') or not fn.endswith('.json'):
            continue
        fp = os.path.join(POEM_JSON_DIR, fn)
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get("分类标签"):
            continue  # 已分类，跳过
        poems.append({
            "filepath": fp,
            "诗歌编号": data.get("诗歌编号", fn.replace('.json', '')),
            "标题": data.get("标题", ""),
            "原文": data.get("原文", "")
        })
    return poems

def build_batch_text(batch):
    """构建一批诗歌的文本"""
    lines = []
    for p in batch:
        lines.append(f"{p['诗歌编号']}\t{p['标题']}\t{p['原文']}")
    return "\n".join(lines)

def parse_response(text):
    """从模型回复中提取 JSON 行"""
    results = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                obj = json.loads(line)
                if "诗歌编号" in obj and "分类标签" in obj:
                    results.append(obj)
            except json.JSONDecodeError:
                continue
    return results

def call_lmstudio(user_prompt, timeout=300):
    """调用 LM Studio API（流式 → 非流式降级）"""
    payload = {
        "model": "local-model",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
        "stream": True,
    }
    all_text = ""
    try:
        resp = requests.post(LMSTUDIO_URL, json=payload, timeout=timeout, stream=True)
        if resp.status_code != 200:
            return f"ERROR: HTTP {resp.status_code} {resp.text[:200]}"
        for line in resp.iter_lines():
            if not line:
                continue
            raw = line.decode('utf-8')
            if raw.startswith('data: '):
                raw = raw[6:].strip()
            if raw == "[DONE]":
                break
            try:
                chunk = json.loads(raw)
                if chunk.get("choices"):
                    delta = chunk["choices"][0].get("delta", {})
                    # 推理模型可能用 reasoning_content 而非 content
                    d = delta.get("content", "") or delta.get("reasoning_content", "") or ""
                    if d:
                        all_text += d
            except json.JSONDecodeError:
                continue
    except requests.exceptions.Timeout:
        return "ERROR: 请求超时"
    except requests.exceptions.ConnectionError as e:
        return f"ERROR: 连接失败 - {e}"
    except Exception as e:
        return f"ERROR: {e}"

    # 流式没拿到内容？降级到非流式重试
    if not all_text:
        try:
            payload["stream"] = False
            resp = requests.post(LMSTUDIO_URL, json=payload, timeout=timeout)
            if resp.status_code == 200:
                body = resp.json()
                if body.get("choices"):
                    msg = body["choices"][0].get("message", {})
                    all_text = msg.get("content", "") or msg.get("reasoning_content", "") or ""
        except Exception:
            pass

    if not all_text:
        return "ERROR: 返回内容为空"
    return all_text

def process_batch(batch, batch_id):
    """处理一批诗歌（带重试）"""
    tag = f"[批次{batch_id:03d}]"
    ids = [p["诗歌编号"] for p in batch]
    print(f"{tag} 开始处理: {ids[0]}~{ids[-1]} ({len(batch)}首)")

    text = build_batch_text(batch)

    # 重试循环
    for attempt in range(3):
        if attempt > 0:
            wait = 10 * (2 ** attempt)
            print(f"{tag} 第{attempt+1}次重试，等待{wait}秒...")
            time.sleep(wait)

        resp = call_lmstudio(text)
        if resp.startswith("ERROR:"):
            print(f"{tag} 尝试{attempt+1}失败: {resp}")
            continue

        parsed = parse_response(resp)
        if not parsed:
            print(f"{tag} 尝试{attempt+1}未能解析回复:")
            print(resp[:300])
            continue

        # 回写 JSON
        ok = 0
        for obj in parsed:
            pid = obj["诗歌编号"]
            tag_label = obj["分类标签"]
            fp = os.path.join(POEM_JSON_DIR, f"{pid}.json")
            if not os.path.exists(fp):
                continue
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                data["分类标签"] = tag_label
                with open(fp, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                ok += 1
            except Exception as e:
                print(f"{tag} 回写出错 {pid}: {e}")

        print(f"{tag} 完成: 成功 {ok}/{len(batch)} 首")
        return ok

    print(f"{tag} 重试3次均失败，放弃")
    return 0

def main():
    poems = load_poems()
    total = len(poems)
    print(f"待分类诗歌: {total} 首")

    if total == 0:
        print("全部已分类，无需处理")
        return

    # 按 8 首一批分组
    BATCH_SIZE = 8
    batches = [poems[i:i+BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
    print(f"共 {len(batches)} 批 (每批最多 {BATCH_SIZE} 首)")

    # 多线程处理
    THREADS = 3  # 根据本地模型显存调整
    success = 0
    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        futures = {}
        for i, batch in enumerate(batches):
            f = pool.submit(process_batch, batch, i + 1)
            futures[f] = batch

        for f in as_completed(futures):
            success += f.result()

    print(f"\n全部完成: 成功 {success}/{total} 首")

if __name__ == '__main__':
    main()
