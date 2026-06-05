# -*- coding: utf-8 -*-
"""
杜甫诗集批量标注脚本
====================
读 poem.txt → 调 DeepSeek API → 出 JSON → 直接喂给 All Mix 系统

用法：
  1. 脚本同级放好 poem.txt 和 prompts.txt
  2. 设环境变量 DEEPSEEK_API_KEY 或在下面填 key
  3. python harvest.py
  4. 去 dufupoem-json/ 收数据
"""
import json, re, os, time, uuid, sys
import concurrent.futures
from pathlib import Path

# ==============================================================================
# 配置
# ==============================================================================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
# 如果在 Windows 上设环境变量:
#   set DEEPSEEK_API_KEY=sk-xxxxx
# 或直接改下面这行:
# DEEPSEEK_API_KEY = "sk-xxxxx"

MODEL_NAME = "deepseek-chat"
API_URL = "https://api.deepseek.com/v1/chat/completions"

PROMPT_FILE = "prompts.txt"
INPUT_FILE = "poem.txt"
OUTPUT_DIR = "poem-json"
DEEPSEEK_API_KEY = "sk-8cf0ba6f18bc452aa3d17b746124f292"
MAX_WORKERS = 6                # 并行窗口数
BATCH_CHAR_LIMIT = 200         # 批处理红线（同 V28）
MAX_POEMS_PER_BATCH = 5        # 每包最多 5 首

# ==============================================================================
# 枚举校验字典（来自 V28 + V10）
# ==============================================================================
VALID_POS = {"名词","动词","形容词","副词","代词","介词","连词","助词","量词","专有名词"}
VALID_PERCEPTION = {"视觉","听觉","触觉","嗅觉","运动","时间","身体感","认知","无"}
VALID_EMOTION = {"赞叹","崇高","喜悦","平静","忧郁","孤独","悲伤","紧张","志向","中性"}
VALID_MATERIAL = {"物象","动作","状态","抽象","逻辑","角色","背景"}
VALID_STRUCTURE = {"单纯","复合","集合","无"}
VALID_SOURCE = {"自然","文化","历史","身体","社会","抽象逻辑","无"}
VALID_FUNCTION = {"描写","象征","对比","动作推进","评价","结构过渡","情感触发","语法链接"}
VALID_CULTURE = {"公共","个体","普适"}
VALID_STRUCTGROUP = {"起始","感官加工","对比强化","参照体系","具身反应","转折过渡","高潮提升","收束升华","逻辑联系"}
VALID_COMPONENT = {"实词","虚词"}
VALID_RELATION = {"空间关联","时间关联","因果关联","对比关系","象征指向","情感传递","视线追随","主体作用"}

def load_prompt(path):
    """从 prompts.txt 加载系统提示词"""
    if not os.path.exists(path):
        print(f"⚠️  {path} 不存在，使用内置 V10 提示词")
        return _builtin_prompt()
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    # 去掉第一行的标题行（如果是以"古诗结构化"等开头）
    lines = content.split('\n', 1)
    if len(lines) > 1 and ('提示词' in lines[0] or 'V10' in lines[0] or '版' in lines[0]):
        content = lines[1].strip()
    return content

def _builtin_prompt():
    """内置 V10 提示词（万一 prompts.txt 丢了也能用）"""
    return """# Role
你是一个顶级的认知语言学与计算诗学专家。你的任务是对古诗词进行极其严谨的"语义最小成词单位"切分，并多维度分类。

# Core Rules (绝对红线)
1. 全量切分：必须覆盖原文的所有字词！以"语义最小成词单位"切分。
2. 虚实保留：即使某词是虚词、代词、逻辑词或抽象概念（意象为0），也【必须】作为独立单元输出。
3. 意象法则：采用"画面确定性原则"——仅能在读者心智中唤起稳定可感知物理图形的成分判定为 1。宏观虚指时空、动作心境、逻辑词=0。
4. 性能要求：JSON 数组内的对象必须采用单行紧凑模式输出，禁止内部换行！

# Constraints
- 【词性】：名词, 动词, 形容词, 副词, 代词, 介词, 连词, 助词, 量词, 专有名词
- 【大类编码】：1(自然), 2(社会), 3(人文) -> 意象为0时填""
- 【子类编码】：1-1~1-4, 2-1~2-3, 3-1~3-4 -> 意象为0时填""
- 【感知通道】：视觉, 听觉, 触觉, 嗅觉, 运动, 时间, 身体感, 认知, 无
- 【素材类型】：物象, 动作, 状态, 抽象, 逻辑, 角色, 背景
- 【内部结构】：单纯, 复合, 集合
- 【表现功能】：描写, 象征, 评价, 动作推进, 情感触发, 语法链接, 参照体系

# Output Format
{"诗歌集": [{"诗歌编号":"P01","标题":"","作者":"","原文":"","分类标签":"","诗行":[{"诗行编号":"P01_L01","原文":""}],"分析单元":[{"单元编号":"U00001","诗歌编号":"P01","诗行编号":"P01_L01","文本":"","行内位置":1,"词性":"名词","成分类型":"实词","是否意象":1,"大类编码":"1","子类编码":"1-1","感知通道":"视觉","素材类型":"物象","内部结构":"单纯","表现功能":"描写","结构功能组":"起始","情感极性":0.5,"情感类别":"平静","情感置信度":0.9}],"意象关系":[],"情感轨迹":[]}]}"""

# ==============================================================================

def sanitize_unit(unit):
    """铁壁洗词器 V10 —— 覆盖所有 V10 字段"""
    # 词性
    pos = unit.get("词性", "")
    if pos not in VALID_POS:
        if "名词" in pos or "时间" in pos: unit["词性"] = "名词"
        elif "动词" in pos or "动作" in pos: unit["词性"] = "动词"
        elif "代词" in pos: unit["词性"] = "代词"
        elif "副词" in pos: unit["词性"] = "副词"
        elif "形容" in pos: unit["词性"] = "形容词"
        elif "数词" in pos: unit["词性"] = "量词"
        else: unit["词性"] = "名词"

    # 成分类型
    ct = unit.get("成分类型", "")
    if ct not in VALID_COMPONENT:
        if "实" in ct or "名" in ct: unit["成分类型"] = "实词"
        else: unit["成分类型"] = "虚词"

    # 感知通道
    perc = unit.get("感知通道", "")
    if perc not in VALID_PERCEPTION:
        unit["感知通道"] = "视觉" if "视" in perc else ("听觉" if "听" in perc else
                         "触觉" if "触" in perc else "认知" if "认" in perc else "无")

    # 素材类型
    mat = unit.get("素材类型", "")
    if mat not in VALID_MATERIAL:
        unit["素材类型"] = "物象" if "物" in mat else ("动作" if "动" in mat else
                         "状态" if "状" in mat else "抽象")

    # 内部结构
    struc = unit.get("内部结构", "")
    if struc not in VALID_STRUCTURE:
        unit["内部结构"] = "单纯" if "单" in struc else ("复合" if "复" in struc else "无")

    # 指涉来源
    src = unit.get("指涉来源", "")
    if src not in VALID_SOURCE:
        unit["指涉来源"] = "自然" if "自" in src else ("文化" if "文" in src else
                         "社会" if "社" in src else "无")

    # 表现功能
    func = unit.get("表现功能", "")
    if func not in VALID_FUNCTION:
        unit["表现功能"] = "描写" if "描" in func else ("象征" if "象" in func else "语法链接")

    # 结构功能组
    sg = unit.get("结构功能组", "")
    if sg not in VALID_STRUCTGROUP:
        unit["结构功能组"] = "起始" if "起" in sg else "收束升华" if "收" in sg else "参照体系"

    # 情感
    emo = unit.get("情感类别", "")
    if emo not in VALID_EMOTION:
        if "悲" in emo or "哀" in emo or "忧" in emo: unit["情感类别"] = "忧郁"
        elif "喜" in emo or "乐" in emo: unit["情感类别"] = "喜悦"
        elif "怒" in emo: unit["情感类别"] = "紧张"
        elif "赞" in emo or "叹" in emo: unit["情感类别"] = "赞叹"
        elif "孤" in emo: unit["情感类别"] = "孤独"
        else: unit["情感类别"] = "中性"

    # 意象相关的后处理
    if unit.get("词性") in ("动词","副词","代词","介词","连词","助词"):
        unit["是否意象"] = 0
        unit["大类编码"] = ""
        unit["子类编码"] = ""

    # 数值字段兜底
    for f in ("情感极性", "情感置信度", "认知强度", "跨文化性"):
        if f not in unit or unit[f] == "":
            unit[f] = 0.0 if f != "跨文化性" else 0
    for f in ("核心意象",):
        if f not in unit or unit[f] == "":
            unit[f] = 0
    for f in ("文化流通性",):
        if f not in unit or unit[f] == "":
            unit[f] = "公共"

    return unit


def parse_poems(filepath):
    """解析 poem.txt，返回诗歌列表"""
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
    """物理切割机（防死循环版）"""
    total = len(text)
    if total <= threshold:
        return [text]
    chunks = []
    pos = 0
    while pos < total:
        end = min(pos + threshold, total)
        if end < total:
            cut = max(text[pos:end].rfind("。"), text[pos:end].rfind("！"),
                      text[pos:end].rfind("？"), text[pos:end].rfind("；"))
            if cut > 5:
                end = pos + cut + 1
        chunks.append(text[pos:end])
        pos = end
    return chunks


def load_processed(output_dir):
    """扫描输出目录，返回已处理的诗歌编号集合"""
    processed = set()
    if os.path.exists(output_dir):
        for fn in os.listdir(output_dir):
            if fn.endswith(".json"):
                processed.add(fn.replace(".json", ""))
    return processed


def call_deepseek(system_prompt, user_prompt, log_tag=""):
    """调 DeepSeek API + 流式接收 + 格式抢救"""
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt + f"\n\n[CacheBuster:{uuid.uuid4().hex[:8]}]"},
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
        resp = requests.post(API_URL, json=payload, headers=headers, timeout=180, stream=True)
        if resp.status_code != 200:
            print(f"  [✗] {log_tag} HTTP {resp.status_code}")
            return None
        for line in resp.iter_lines():
            if not line: continue
            raw = line.decode('utf-8')
            if raw.startswith('data: '): raw = raw[6:].strip()
            if raw == "[DONE]": break
            try:
                chunk = json.loads(raw)
                if chunk.get("choices"):
                    d = chunk["choices"][0].get("delta", {}).get("content", "")
                    if d: all_text += d
            except: continue
    except Exception as e:
        print(f"  [✗] {log_tag} 异常: {e}")
        return None

    # 清理标签和代码块
    res = re.sub(r'<think>.*?</think>', '', all_text, flags=re.DOTALL).strip()
    res = re.sub(r'```(?:json)?\s*|```\s*', '', res).strip()

    start = res.find('{')
    if start == -1: return None
    json_str = res[start:res.rfind('}')+1]

    for attempt in range(2):
        try:
            data = json.loads(json_str, strict=False)
            poems = data.get("诗歌集", [])
            for p in poems:
                p["分析单元"] = [sanitize_unit(u) for u in p.get("分析单元", [])]
            return poems
        except json.JSONDecodeError:
            if attempt == 0:
                # 终极抢救
                json_str = re.sub(r'(?<!\\)\n(?=(?:[^"]*"[^"]*")*[^"]*$)', '', json_str)
                json_str = json_str.replace('\t', '')
                continue
            print(f"  [✗] {log_tag} JSON 损坏")
            return None
    return None


def process_batch(system_prompt, batch, output_dir):
    """批量处理短诗"""
    tag = f"batch[{batch[0]['诗歌编号']}~{batch[-1]['诗歌编号']}]"
    chars = sum(len(p['原文']) for p in batch)
    print(f"  [→] {tag} {len(batch)}首 {chars}字")
    prompt = "请对以下多首诗歌进行分析：\n"
    for p in batch:
        prompt += f"诗歌编号：{p['诗歌编号']}\n标题：《{p['标题']}》\n原文：{p['原文']}\n\n"
    results = call_deepseek(system_prompt, prompt, tag)
    if not results:
        print(f"  [✗] {tag} 跳过")
        return []
    saved = []
    for parsed in results:
        pid = parsed.get("诗歌编号")
        orig = next((p for p in batch if p['诗歌编号'] == pid), None)
        if not orig: continue
        orig["分析单元"] = parsed.get("分析单元", [])
        # 构建旧→新ID映射，修复意象关系交叉引用
        id_map = {}
        for i, u in enumerate(orig["分析单元"], 1):
            old_id = u.get("单元编号", "")
            new_id = f"U{i:05d}"
            if old_id and old_id != new_id:
                id_map[old_id] = new_id
            u["单元编号"] = new_id
            u["诗歌编号"] = pid
        # 保留诗行、意象关系、情感轨迹（如果有）
        for field in ("诗行", "意象关系", "情感轨迹"):
            if parsed.get(field):
                orig[field] = parsed[field]
        # 修复意象关系引用（renumbering后ID变了）
        if id_map:
            for rel in orig.get("意象关系", []):
                if rel.get("来源单元") in id_map:
                    rel["来源单元"] = id_map[rel["来源单元"]]
                if rel.get("目标单元") in id_map:
                    rel["目标单元"] = id_map[rel["目标单元"]]
        # 写文件
        Path(output_dir).mkdir(exist_ok=True)
        with open(os.path.join(output_dir, f"{pid}.json"), 'w', encoding='utf-8') as f:
            json.dump(orig, f, ensure_ascii=False, indent=2)
        saved.append(pid)
        print(f"  [✓] 《{orig['标题']}》 → {pid}.json ({len(orig['分析单元'])}单元)")
    return saved


def process_long_poem(system_prompt, poem, output_dir):
    """处理长诗（切片 → 拼接）"""
    tag = f"long[{poem['诗歌编号']}]"
    print(f"  [→] {tag} 《{poem['标题']}》 {len(poem['原文'])}字 切片")
    chunks = smart_split_text(poem['原文'], BATCH_CHAR_LIMIT)
    all_units = []
    for idx, chunk in enumerate(chunks):
        prompt = f"分析片段：《{poem['标题']}》第{idx+1}/{len(chunks)}部分：\n诗歌编号：{poem['诗歌编号']}\n原文：{chunk}"
        results = call_deepseek(system_prompt, prompt, f"{tag}[{idx+1}/{len(chunks)}]")
        if results and len(results) > 0:
            all_units.extend(results[0].get("分析单元", []))
        else:
            print(f"  [✗] {tag} 切片{idx+1}失败")
            return False
        time.sleep(1)
    for i, u in enumerate(all_units, 1):
        u["单元编号"] = f"U{i:05d}"
        u["诗歌编号"] = poem["诗歌编号"]
    poem["分析单元"] = all_units
    Path(output_dir).mkdir(exist_ok=True)
    with open(os.path.join(output_dir, f"{poem['诗歌编号']}.json"), 'w', encoding='utf-8') as f:
        json.dump(poem, f, ensure_ascii=False, indent=2)
    print(f"  [✓] {tag} 缝合完成 ({len(all_units)}单元)")
    return True


def main():
    script_dir = Path(__file__).parent
    os.chdir(script_dir)  # 切到脚本所在目录

    # ── API Key ──
    if not DEEPSEEK_API_KEY:
        print("❌ DEEPSEEK_API_KEY 没设")
        print("   Windows: set DEEPSEEK_API_KEY=sk-xxxxx")
        print("   或在脚本顶部直接填")
        sys.exit(1)

    # ── 加载提示词 ──
    prompt_path = Path(PROMPT_FILE)
    if not prompt_path.exists():
        print(f"❌ {PROMPT_FILE} 不存在")
        sys.exit(1)
    system_prompt = load_prompt(str(prompt_path))
    print(f"📜 提示词已加载 ({len(system_prompt)} 字符)")

    # ── 读取诗歌 ──
    if not Path(INPUT_FILE).exists():
        print(f"❌ {INPUT_FILE} 不存在")
        sys.exit(1)
    all_poems = parse_poems(INPUT_FILE)
    print(f"📜 共 {len(all_poems)} 首")

    # ── 跳过已处理 ──
    processed = load_processed(OUTPUT_DIR)
    todo = [p for p in all_poems if p["诗歌编号"] not in processed]
    print(f"💾 已处理 {len(processed)}，待处理 {len(todo)}\n")

    if not todo:
        print("✅ 全部完成，无需处理")
        return

    # ── 构造任务队列 ──
    tasks = []
    batch = []
    chars = 0
    for p in todo:
        if len(p['原文']) > BATCH_CHAR_LIMIT:
            if batch: tasks.append(("batch", batch[:])); batch, chars = [], 0
            tasks.append(("long", p))
        elif len(batch) >= MAX_POEMS_PER_BATCH or chars + len(p['原文']) > BATCH_CHAR_LIMIT:
            tasks.append(("batch", batch[:])); batch, chars = [p], len(p['原文'])
        else:
            batch.append(p); chars += len(p['原文'])
    if batch: tasks.append(("batch", batch))

    print(f"🔧 {len(tasks)} 批 ({sum(1 for t in tasks if t[0]=='batch')} 短批 + {sum(1 for t in tasks if t[0]=='long')} 长诗)\n")

    # ── 并行执行 ──
    success = fail = 0
    lock = __import__("threading").Lock()

    def worker(task):
        nonlocal success, fail
        kind, data = task
        try:
            if kind == "batch":
                saved = process_batch(system_prompt, data, OUTPUT_DIR)
                with lock: success += len(saved)
                return
            else:
                ok = process_long_poem(system_prompt, data, OUTPUT_DIR)
                with lock:
                    if ok: success += 1
                    else: fail += 1
        except Exception as e:
            with lock: fail += 1
            print(f"  [!] worker 异常: {e}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(worker, t) for t in tasks]
        concurrent.futures.wait(futures)

    print(f"\n{'='*50}")
    print(f"🎉 完成！成功: {success}  失败: {fail}  总计: {len(todo)}")
    print(f"📂 {OUTPUT_DIR}/")


if __name__ == "__main__":
    import requests
    main()
