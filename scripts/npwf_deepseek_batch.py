# -*- coding: utf-8 -*-
"""
NPWF 深度求索批量生产脚本
=========================
基于 V28 逻辑重构，API 切换为 DeepSeek + 多线程并行。
价格红利期倒计时 10 天，抓紧梭哈。

用法：
  1. 把诗歌 txt 扔进 INPUT_DIR
  2. python npwf_deepseek_batch.py
  3. 去 OUTPUT_DIR 收 json
"""
import json, re, os, time, uuid, sys
import concurrent.futures
from pathlib import Path

import requests

# ==============================================================================
# 配置区（你只需要改这里）
# ==============================================================================
DEEPSEEK_API_KEY = ""        # ← 你的 DeepSeek API Key
MODEL_NAME = "deepseek-chat"  # DeepSeek V3
API_URL = "https://api.deepseek.com/v1/chat/completions"

INPUT_DIR = "input_poems"     # 放 txt 的文件夹
OUTPUT_DIR = "output_json"    # 输出 json 的文件夹
PROCESSED_LOG = "_processed.log"  # 已处理记录

MAX_WORKERS = 6               # 并行窗口数（DeepSeek 免费期宽松）
BATCH_CHAR_LIMIT = 200        # 批处理防幻觉红线（同 V28）
MAX_POEMS_PER_BATCH = 5       # 每包最多 5 首

# ==============================================================================
# System Prompt —— 来自你的 V10 终极交付版 + V28 铁壁防御杂交
# ==============================================================================
SYSTEM_PROMPT = """# Role
你是一个顶级的认知语言学与计算诗学专家。你的任务是对古诗词进行极其严谨的"语义最小成词单位"切分，并多维度分类。

# Core Rules (绝对红线)
1. 深度思考：在输出最终结果前，允许你在 <think> 标签内进行充分的逻辑推导。
2. 全量切分（防偷懒）：必须覆盖原文的所有字词！以"语义最小成词单位"切分。
3. 虚实保留（防遗漏）：即使某词是虚词、代词、逻辑词或抽象概念（意象为0），也【必须】作为独立单元输出。
4. 意象法则：采用"画面确定性原则"——仅能在读者心智中唤起稳定可感知物理图形的成分判定为 1（意象）。宏观虚指时空、动作心境、逻辑词一律判定为 0。
5. 输出禁止重复多次连续输出同一字符。
6. 性能要求：JSON 数组内的对象必须采用单行紧凑模式输出，禁止内部换行！

# Constraints (严格字典)
- 【词性】：名词, 动词, 形容词, 副词, 代词, 介词, 连词, 助词, 量词, 专有名词
- 【大类编码】：1(自然), 2(社会), 3(人文) -> 意象为0时填""
- 【子类编码】：1-1~1-4, 2-1~2-3, 3-1~3-4 -> 意象为0时填""
- 【感知通道】：视觉, 听觉, 触觉, 嗅觉, 运动, 时间, 身体感, 认知, 无
- 【素材类型】：物象, 动作, 状态, 抽象, 逻辑, 角色, 背景
- 【内部结构】：单纯, 复合, 集合
- 【表现功能】：描写, 象征, 评价, 动作推进, 情感触发, 语法链接, 参照体系
- 【结构功能组】：起始, 感官加工, 对比强化, 参照体系, 具身反应, 转折过渡, 高潮提升, 收束升华, 逻辑联系
- 【情感类别】：赞叹, 喜悦, 悲凉, 孤独, 愤怒, 志向, 释然, 迷惘, 崇高, 平静, 中性

# Output Format
用户会输入一首或多首诗歌。你必须且只能输出一个合法的 JSON，结构如下：
{"诗歌集": [{"诗歌编号":"P01","标题":"","作者":"","原文":"","分类标签":"","诗行":[{"诗行编号":"P01_L01","原文":""}],"分析单元":[{"单元编号":"U00001","诗歌编号":"P01","诗行编号":"P01_L01","文本":"","行内位置":1,"词性":"名词","成分类型":"实词","是否意象":1,"大类编码":"1","子类编码":"1-1","感知通道":"视觉","素材类型":"物象","内部结构":"单纯","表现功能":"描写","结构功能组":"起始","情感极性":0.5,"情感类别":"平静","情感置信度":0.9}],"意象关系":[],"情感轨迹":[]}]}"""

# ==============================================================================
VALID_POS = {"名词","动词","形容词","副词","代词","介词","连词","助词","量词","专有名词"}
VALID_PERCEPTION = {"视觉","听觉","触觉","嗅觉","运动","时间","身体感","认知","无"}
VALID_EMOTION = {"赞叹","喜悦","悲凉","孤独","愤怒","志向","释然","迷惘","崇高","平静","中性"}
VALID_MATERIAL = {"物象","动作","状态","抽象","逻辑","角色","背景"}

# ==============================================================================

def sanitize_unit(unit):
    """同 V28 —— 铁壁洗词器"""
    pos = unit.get("词性", "")
    if pos not in VALID_POS:
        if "名词" in pos or "时间" in pos: unit["词性"] = "名词"
        elif "动词" in pos or "动作" in pos: unit["词性"] = "动词"
        elif "代词" in pos: unit["词性"] = "代词"
        elif "副词" in pos: unit["词性"] = "副词"
        elif "形容" in pos: unit["词性"] = "形容词"
        elif "数词" in pos: unit["词性"] = "量词"
        else: unit["词性"] = "名词"
    perc = unit.get("感知通道", "")
    if perc not in VALID_PERCEPTION:
        if not perc: unit["感知通道"] = "无"
        elif "视" in perc: unit["感知通道"] = "视觉"
        elif "听" in perc: unit["感知通道"] = "听觉"
        elif "触" in perc: unit["感知通道"] = "触觉"
        elif "认" in perc: unit["感知通道"] = "认知"
        else: unit["感知通道"] = "无"
    emo = unit.get("情感类别", "")
    if emo not in VALID_EMOTION:
        if "悲" in emo or "哀" in emo: unit["情感类别"] = "悲凉"
        elif "喜" in emo or "乐" in emo: unit["情感类别"] = "喜悦"
        elif "怒" in emo: unit["情感类别"] = "愤怒"
        else: unit["情感类别"] = "中性"
    mat = unit.get("素材类型", "")
    if mat not in VALID_MATERIAL:
        if "物" in mat: unit["素材类型"] = "物象"
        elif "动" in mat: unit["素材类型"] = "动作"
        elif "状" in mat: unit["素材类型"] = "状态"
        else: unit["素材类型"] = "抽象"
    if unit["词性"] in ("动词","副词","代词","介词","连词","助词"):
        unit["是否意象"] = 0
        unit["大类编码"] = ""
        unit["子类编码"] = ""
    return unit


def parse_txt_file(filepath):
    """解析单个 txt，返回诗歌列表"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    blocks = re.split(r'={10,}', content)
    poems = []
    for block in blocks:
        block = block.strip()
        if not block or "《" not in block:
            continue
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if len(lines) < 3:
            continue
        try:
            header = lines[0]
            id_match = re.search(r'(\d+)', header)
            p_id = f"P{int(id_match.group(1)):03d}" if id_match else f"P{len(poems)+1:03d}"
            title = re.search(r'《(.*?)》', header).group(1) if "《" in header else "未知"
            author = lines[1]
            raw_text = "".join(lines[2:]).replace(" ", "").replace("\t", "").replace("\n", "")
            poems.append({"诗歌编号": p_id, "标题": title, "作者": author, "原文": raw_text})
        except Exception:
            continue
    return poems


def smart_split_text(text, threshold):
    """同 V28 —— 修复了死循环 Bug 的物理切割机"""
    total_len = len(text)
    if total_len <= threshold:
        return [text]
    chunks = []
    current_pos = 0
    while current_pos < total_len:
        end_pos = min(current_pos + threshold, total_len)
        chunk = text[current_pos:end_pos]
        if end_pos < total_len:
            last_punc = max(chunk.rfind("。"), chunk.rfind("！"),
                            chunk.rfind("？"), chunk.rfind("；"), chunk.rfind("，"))
            if last_punc > 5:
                actual_end = current_pos + last_punc + 1
            else:
                actual_end = end_pos
            chunks.append(text[current_pos:actual_end])
            current_pos = actual_end
        else:
            chunks.append(chunk)
            current_pos = end_pos
    return chunks


def call_deepseek(user_prompt, log_tag=""):
    """调 DeepSeek API，流式接收 + 格式抢救（同 V28 逻辑）"""
    cache_buster = uuid.uuid4().hex[:8]
    full_system = SYSTEM_PROMPT + f"\n\n[Cache_Buster: {cache_buster}]"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": full_system},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 32000,
        "stream": True,
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    all_text = ""
    try:
        resp = requests.post(API_URL, json=payload, headers=headers,
                             timeout=120, stream=True)
        if resp.status_code != 200:
            print(f"  [✗] {log_tag} HTTP {resp.status_code}: {resp.text[:200]}")
            return None

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
                    content = delta.get("content", "")
                    if content:
                        all_text += content
            except json.JSONDecodeError:
                continue
    except Exception as e:
        print(f"  [✗] {log_tag} 请求异常: {e}")
        return None

    # 清理 think 标签 + 代码块
    res = re.sub(r'<think>.*?</think>', '', all_text, flags=re.DOTALL).strip()
    res = re.sub(r'```(?:json)?\s*|```\s*', '', res).strip()

    start = res.find('{')
    if start == -1:
        print(f"  [✗] {log_tag} 无 JSON")
        return None

    json_str = res[start:res.rfind('}')+1]
    try:
        data = json.loads(json_str, strict=False)
        poems = data.get("诗歌集", [])
        for p in poems:
            p["分析单元"] = [sanitize_unit(u) for u in p.get("分析单元", [])]
        return poems
    except json.JSONDecodeError:
        # 终极抢救
        try:
            json_str = re.sub(r'(?<!\\)\n(?=(?:[^"]*"[^"]*")*[^"]*$)', '', json_str)
            json_str = json_str.replace('\n', '\\n')
            data = json.loads(json_str, strict=False)
            poems = data.get("诗歌集", [])
            for p in poems:
                p["分析单元"] = [sanitize_unit(u) for u in p.get("分析单元", [])]
            return poems
        except:
            print(f"  [✗] {log_tag} JSON 损坏无法修复")
            return None


def process_batch(batch, output_dir):
    """批量处理短诗"""
    tag = f"batch[{batch[0]['诗歌编号']}~{batch[-1]['诗歌编号']}]"
    print(f"  [→] {tag} {len(batch)}首 {sum(len(p['原文']) for p in batch)}字")
    prompt = "请对以下多首诗歌进行分析：\n"
    for p in batch:
        prompt += f"诗歌编号：{p['诗歌编号']}\n标题：《{p['标题']}》\n原文：{p['原文']}\n\n"
    results = call_deepseek(prompt, tag)
    if not results:
        print(f"  [✗] {tag} 失败跳过")
        return []
    saved = []
    for parsed in results:
        pid = parsed.get("诗歌编号")
        orig = next((p for p in batch if p['诗歌编号'] == pid), None)
        if not orig:
            continue
        orig["分析单元"] = parsed.get("分析单元", [])
        for i, u in enumerate(orig["分析单元"], 1):
            u["单元编号"] = f"U{i:03d}"
            u["诗歌编号"] = pid
        path = os.path.join(output_dir, f"{pid}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(orig, f, ensure_ascii=False, indent=2)
        saved.append(pid)
        print(f"  [✓] 《{orig['标题']}》 → {pid}.json ({len(orig['分析单元'])}单元)")
    return saved


def process_long_poem(poem, output_dir):
    """处理长诗（切片 + 拼接）"""
    tag = f"long[{poem['诗歌编号']}]"
    print(f"  [→] {tag} 《{poem['标题']}》 {len(poem['原文'])}字 切片处理")
    chunks = smart_split_text(poem['原文'], BATCH_CHAR_LIMIT)
    all_units = []
    for idx, chunk in enumerate(chunks):
        prompt = f"分析片段：《{poem['标题']}》第{idx+1}/{len(chunks)}部分：\n诗歌编号：{poem['诗歌编号']}\n原文：{chunk}"
        results = call_deepseek(prompt, f"{tag}[{idx+1}/{len(chunks)}]")
        if results and len(results) > 0:
            all_units.extend(results[0].get("分析单元", []))
        else:
            print(f"  [✗] {tag} 切片{idx+1}失败，整诗作废")
            return False
        time.sleep(1)
    for i, u in enumerate(all_units, 1):
        u["单元编号"] = f"U{i:03d}"
        u["诗歌编号"] = poem["诗歌编号"]
    poem["分析单元"] = all_units
    path = os.path.join(output_dir, f"{poem['诗歌编号']}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(poem, f, ensure_ascii=False, indent=2)
    print(f"  [✓] {tag} 《{poem['标题']}》 缝合完成 ({len(all_units)}单元)")
    return True


def load_processed(output_dir, log_path):
    """返回已处理的诗歌编号集合"""
    processed = set()
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            processed = {l.strip() for l in f if l.strip()}
    for fn in os.listdir(output_dir):
        if fn.endswith(".json"):
            processed.add(fn.replace(".json", ""))
    return processed


def save_processed(pid, log_path):
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"{pid}\n")


def main():
    # ── 校验 ──
    if not DEEPSEEK_API_KEY:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            print("❌ 没 API Key。设环境变量 DEEPSEEK_API_KEY，或直接写在脚本顶部。")
            sys.exit(1)
        globals()["DEEPSEEK_API_KEY"] = api_key

    # ── 准备目录 ──
    input_dir = Path(INPUT_DIR)
    output_dir = Path(OUTPUT_DIR)
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    log_path = Path(PROCESSED_LOG)

    # ── 读取所有诗歌 ──
    all_poems = []
    for fp in sorted(input_dir.glob("*.txt")):
        poems = parse_txt_file(str(fp))
        print(f"  [加载] {fp.name} → {len(poems)} 首")
        all_poems.extend(poems)

    if not all_poems:
        print(f"❌ {input_dir}/ 下没有找到诗歌 txt")
        return

    print(f"\n📜 共加载 {len(all_poems)} 首\n")

    # ── 跳过已处理 ──
    processed_ids = load_processed(str(output_dir), str(log_path))
    todo = [p for p in all_poems if p["诗歌编号"] not in processed_ids]
    print(f"💾 已处理 {len(processed_ids)}，待处理 {len(todo)}\n")

    # ── 构造任务队列 ──
    # 短诗打包，长诗单独
    tasks = []
    batch = []
    char_count = 0
    for p in todo:
        if len(p['原文']) > BATCH_CHAR_LIMIT:
            if batch:
                tasks.append(("batch", batch[:]))
                batch, char_count = [], 0
            tasks.append(("long", p))
        elif len(batch) >= MAX_POEMS_PER_BATCH or char_count + len(p['原文']) > BATCH_CHAR_LIMIT:
            tasks.append(("batch", batch[:]))
            batch, char_count = [p], len(p['原文'])
        else:
            batch.append(p)
            char_count += len(p['原文'])
    if batch:
        tasks.append(("batch", batch))

    print(f"🔧 任务队列: {len(tasks)} 批 ({sum(1 for t in tasks if t[0]=='batch')} 短批 + {sum(1 for t in tasks if t[0]=='long')} 长诗)\n")

    # ── 多线程并行 ──
    success = 0
    fail = 0
    lock = __import__("threading").Lock()

    def worker(task):
        nonlocal success, fail
        kind, data = task
        try:
            if kind == "batch":
                saved = process_batch(data, str(output_dir))
                with lock:
                    for pid in saved:
                        save_processed(pid, str(log_path))
                    return len(saved), 0
            else:
                ok = process_long_poem(data, str(output_dir))
                with lock:
                    if ok:
                        save_processed(data["诗歌编号"], str(log_path))
                    return (1, 0) if ok else (0, 1)
        except Exception as e:
            print(f"  [!] worker 异常: {e}")
            return 0, 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(worker, t) for t in tasks]
        for f in concurrent.futures.as_completed(futures):
            s, f_ = f.result()
            success += s
            fail += f_

    print(f"\n{'='*50}")
    print(f"🎉 完成！成功: {success} | 失败: {fail} | 总计: {len(todo)}")
    print(f"📂 输出目录: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
