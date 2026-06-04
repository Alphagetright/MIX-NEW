import json
import re
import requests
import os
import time
import uuid

# ==============================================================================
# 配置区 (V29 铁壁防御 + 动态批处理版)
# ==============================================================================
API_URL = "http://127.0.0.1:44787/v1/chat/completions" 
INPUT_TXT = "poems.txt"
OUTPUT_DIR = "NPWF"  
MODEL_NAME = "qwen3.6-35b-a3b"  

TIMEOUT_LIMIT = None 
BATCH_CHAR_LIMIT = 200  # 💡 动态批处理防幻觉红线
MAX_POEMS_PER_BATCH = 5 # 💡 每一包最多 5 首诗

ACTIVE_MODEL = MODEL_NAME

SYSTEM_PROMPT = """
# Role
你是一个顶级的认知语言学与计算诗学专家。你的任务是对古诗词进行极其严谨的“语义最小成词单位”切分，并多维度分类。

# Core Rules (绝对红线)
1. 深度思考：在输出最终结果前，允许你在 <think> 标签内进行充分的逻辑推导、字意拆解和意象辨析。
2. 全量切分（防偷懒）：必须覆盖原文的所有字词！以“语义最小成词单位”切分。
3. 虚实保留（防遗漏）：即使某词是虚词、代词、逻辑词或抽象概念（意象为0），也【必须】作为独立单元输出。
4. 意象法则：仅物理实体、具体可感知的颜色/状态判定为 1（意象）。宏观虚指时空、动作心境、逻辑词一律判定为 0。
5. 输出禁止重复多次连续输出同一字符。

# Constraints (严格字典，绝不捏造)
- 【词性】：名词, 动词, 形容词, 副词, 代词, 介词, 连词, 助词, 量词, 专有名词
- 【大类编码】：1(自然), 2(社会), 3(人文) -> 意象为0时，必须填 ""
- 【子类编码】：1-1到1-4, 2-1到2-3, 3-1到3-4 -> 意象为0时，必须填 ""
- 【感知通道】：视觉, 听觉, 触觉, 嗅觉, 运动, 时间, 身体感, 认知, 无
- 【素材类型】：物象, 动作, 状态, 抽象, 逻辑, 角色, 背景
- 【内部结构】：单纯, 复合, 集合
- 【表现功能】：描写, 象征, 评价, 动作推进, 情感触发, 语法链接, 参照体系
- 【结构功能组】：起始, 感官加工, 对比强化, 参照体系, 具身反应, 转折过渡, 高潮提升, 收束升华, 逻辑联系
- 【情感类别】：赞叹, 喜悦, 悲凉, 孤独, 愤怒, 志向, 释然, 迷惘, 崇高, 平静, 中性

# Output Format
用户会输入一首或多首诗歌。你必须且只能输出一个合法的 JSON，结构如下：
{
  "诗歌集": [
    {
      "诗歌编号": "P01",
      "分析单元": [
        {"文本":"...", "词性":"名词", "是否意象":1, "大类编码":"1", "子类编码":"1-1", "感知通道":"视觉", "素材类型":"物象", "内部结构":"单纯", "表现功能":"描写", "结构功能组":"起始", "情感极性":0.5, "情感类别":"平静", "情感置信度":0.9}
      ]
    }
  ]
}
"""
# ==============================================================================

VALID_POS = {"名词", "动词", "形容词", "副词", "代词", "介词", "连词", "助词", "量词", "专有名词"}
VALID_PERCEPTION = {"视觉", "听觉", "触觉", "嗅觉", "运动", "时间", "身体感", "认知", "无"}
VALID_EMOTION = {"赞叹", "喜悦", "悲凉", "孤独", "愤怒", "志向", "释然", "迷惘", "崇高", "平静", "中性"}
VALID_MATERIAL = {"物象", "动作", "状态", "抽象", "逻辑", "角色", "背景"}

def sanitize_unit(unit):
    """🛠️ 保留你引以为傲的终极洗词器"""
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
        if not perc or perc == "": unit["感知通道"] = "无"
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
        
    if unit["词性"] in ["动词", "副词", "代词", "介词", "连词", "助词"]:
        unit["是否意象"] = 0
        unit["大类编码"] = ""
        unit["子类编码"] = ""

    return unit

def detect_active_model():
    global ACTIVE_MODEL
    try:
        models_url = API_URL.replace("/chat/completions", "/models")
        response = requests.get(models_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("data") and len(data["data"]) > 0:
                ACTIVE_MODEL = data["data"][0]["id"]
                print(f"🎯 [防爆显存机制] 已锁定当前显存中的唯一模型: {ACTIVE_MODEL}")
                return
    except: pass
    print(f"⚠️ [防爆显存机制] 无法自动检测，使用默认名称: {ACTIVE_MODEL}")

def smart_split_text(text, threshold):
    """🔪 修复了死循环 Bug 的物理切割机"""
    total_len = len(text)
    if total_len <= threshold: return [text]
    chunks = []
    current_pos = 0
    while current_pos < total_len:
        end_pos = min(current_pos + threshold, total_len)
        chunk = text[current_pos:end_pos]
        if end_pos < total_len:
            last_punc = max(chunk.rfind("。"), chunk.rfind("！"), chunk.rfind("？"), chunk.rfind("；"), chunk.rfind("，"))
            # 修复点：如果找不到标点，last_punc 是 -1，必须强制切断，否则死循环
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

def call_api_robust(user_prompt, log_title):
    """🧠 完美保留了彩色流式输出、计费雷达和格式抢救功能"""
    print(f"\n --------------------------------------------------")
    
    dynamic_system_prompt = SYSTEM_PROMPT + f"\n\n[Cache_Buster_ID: {uuid.uuid4().hex}]"
    
    payload = {
        "model": ACTIVE_MODEL, 
        "messages": [
            {"role": "system", "content": dynamic_system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1, 
        "max_tokens": 80000, 
        "stream": True,
        "stream_options": {"include_usage": True} 
    }
    
    headers = {"Content-Type": "application/json", "Connection": "close"}
    all_raw_text = ""
    is_thinking = False

    with requests.Session() as session:
        try:
            response = session.post(API_URL, json=payload, headers=headers, timeout=TIMEOUT_LIMIT, stream=True)
            if response.status_code != 200:
                print(f"\n ❌ API 拒绝服务! 状态码: {response.status_code}")
                return None 

            has_printed_json_start = False # 状态标记

            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '): line_text = line_text[6:].strip()
                    if line_text == "[DONE]": break
                    
                    try:
                        chunk_json = json.loads(line_text)
                        
                        # Token 雷达保留
                        if "usage" in chunk_json and chunk_json["usage"]:
                            usage = chunk_json["usage"]
                            print(f"\n 📊 [Token雷达] 本次消耗 -> 输入: {usage.get('prompt_tokens', 0)} | 输出: {usage.get('completion_tokens', 0)} | 总计: {usage.get('total_tokens', 0)}")
                        
                        if not chunk_json.get('choices'): continue

                        delta = chunk_json['choices'][0].get('delta', {})
                        
                        # 💡 核心分离：将“思考”与“正文”严格拆开
                        reasoning = delta.get('reasoning_content', '')
                        content = delta.get('content', '')
                        
                        # 1. 如果模型在推理专属通道发言 (仅打印，绝对不加入 all_raw_text)
                        if reasoning:
                            if not is_thinking:
                                print(" 🧠 [AI 深度思考中] ", end="")
                                is_thinking = True
                            print(f"\033[90m{reasoning}\033[0m", end='', flush=True)
                            
                        # 2. 如果模型开始输出正文
                        if content:
                            all_raw_text += content  # 💡 只有 content 有资格进入最终的 JSON 字符串！
                            
                            # 兼容某些依然在正文里吐 <think> 标签的模型
                            if '<think>' in content:
                                is_thinking = True
                                print(" 🧠 [AI 深度思考中] ", end="")
                                
                            if is_thinking and '</think>' in content:
                                is_thinking = False
                                
                            # 控制台打印逻辑
                            if is_thinking and not reasoning:
                                print(f"\033[90m{content.replace('<think>', '').replace('</think>', '')}\033[0m", end='', flush=True)
                            elif not is_thinking and not ('<think>' in content):
                                if not has_printed_json_start:
                                    print("\n 📝 [JSON 构建中] ", end="")
                                    has_printed_json_start = True
                                if len(all_raw_text) % 50 == 0: print(".", end="", flush=True)
                                
                    except Exception as e: continue
            print(" [流式接收完成]")

            # 💡 双保险：如果正文里混入了 <think>，强行挖掉
            res_text = re.sub(r'<think>.*?</think>', '', all_raw_text, flags=re.DOTALL).strip()
            res_text = re.sub(r'`{3}(?:json)?\s*|`{3}\s*', '', res_text).strip()
            
            start = res_text.find('{')
            if start != -1:
                end = res_text.rfind('}')
                if end == -1:
                    print(" ⚠️ [断头警告] 尝试强行缝合...", end="")
                    json_str = res_text[start:] + "]}]}"
                else:
                    json_str = res_text[start:end+1]
                    
                try:
                    # 💡 开启 strict=False，容忍模型在字符串内手滑敲回车
                    clean_json = json.loads(json_str, strict=False)
                    poems_data = clean_json.get("诗歌集", [])
                    for p in poems_data:
                        p["分析单元"] = [sanitize_unit(u) for u in p.get("分析单元", [])]
                    return poems_data
                except json.JSONDecodeError as e:
                    print(f" 🚨 格式受损 ({e})，尝试正则及脏字符清理...")
                    try:
                        # 终极暴力清洗非法换行
                        json_str = re.sub(r'(?<!\\)\n(?=(?:[^"]*"[^"]*")*[^"]*$)', '', json_str)
                        json_str = json_str.replace('\n', '\\n').replace('\t', '')
                        repaired_str = re.sub(r'}\s*{', '},{', json_str)
                        if not repaired_str.endswith('}'): repaired_str += "}"
                        clean_json = json.loads(repaired_str, strict=False)
                        print(" ✨ 抢救成功！")
                        poems_data = clean_json.get("诗歌集", [])
                        for p in poems_data:
                            p["分析单元"] = [sanitize_unit(u) for u in p.get("分析单元", [])]
                        return poems_data
                    except:
                        print(f" ❌ 修复失败。丢弃此段数据。")
                        return None 
            else:
                print(f" 🛑 结果中未找到 JSON。")
                return None 
                
        except Exception as e:
            print(f"\n ❌ 请求异常: {e}")
            return None

def parse_txt_robust(file_path):
    if not os.path.exists(file_path): return []
    with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
    blocks = re.split(r'={10,}', content)
    poems = []
    for block in blocks:
        block = block.strip()
        if not block or "《" not in block: continue
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if len(lines) < 3: continue 
        try:
            header = lines[0]
            id_match = re.search(r'(\d+)', header)
            p_id = f"P{int(id_match.group(1)):03d}" if id_match else f"P{len(poems)+1:03d}"
            title = re.search(r'《(.*?)》', header).group(1) if "《" in header else "未知"
            author = lines[1]
            raw_text = "".join(lines[2:]).replace(" ", "").replace("\t", "").replace("\n", "")
            poems.append({"诗歌编号": p_id, "标题": title, "作者": author, "原文": raw_text})
        except: continue
    return poems

def process_batch(batch):
    """处理短诗打包"""
    print(f"\n📦 [批处理引擎] 正在合并处理 {len(batch)} 首短诗，总字数: {sum(len(p['原文']) for p in batch)}")
    user_prompt = "请对以下多首诗歌进行分析：\n"
    for p in batch:
        user_prompt += f"诗歌编号：{p['诗歌编号']}\n标题：《{p['标题']}》\n原文：{p['原文']}\n\n"
        
    results = call_api_robust(user_prompt, "批量短诗")
    if results:
        for parsed_p in results:
            p_id = parsed_p.get("诗歌编号")
            # 找到对应的原诗
            orig_p = next((p for p in batch if p['诗歌编号'] == p_id), None)
            if orig_p:
                orig_p["分析单元"] = parsed_p.get("分析单元", [])
                
                # 生成 U001 编号
                for i, unit in enumerate(orig_p["分析单元"], 1):
                    unit["单元编号"] = f"U{i:03d}"
                    unit["诗歌编号"] = p_id
                    
                file_path = os.path.join(OUTPUT_DIR, f"{p_id}.json")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(orig_p, f, ensure_ascii=False, indent=2)
                print(f" ✨ 《{orig_p['标题']}》批量落库成功！单元数: {len(orig_p['分析单元'])}")
    else:
        print(" ⚠️ 批处理失败，本批次跳过。")
    time.sleep(2)

def process_long_poem(poem):
    """处理长诗切片（保留了原版的拼接逻辑）"""
    print(f"\n🔪 [长诗切片引擎] 《{poem['标题']}》字数 {len(poem['原文'])} 超出 {BATCH_CHAR_LIMIT}，开始切片...")
    chunks = smart_split_text(poem['原文'], BATCH_CHAR_LIMIT)
    merged_units = []
    
    for idx, chunk in enumerate(chunks):
        user_prompt = f"分析片段：《{poem['标题']}》的第 {idx+1} 部分：\n诗歌编号：{poem['诗歌编号']}\n原文：{chunk}"
        results = call_api_robust(user_prompt, f"切片 {idx+1}/{len(chunks)}")
        
        if results and len(results) > 0:
            merged_units.extend(results[0].get("分析单元", []))
            print(f" ✨ 切片 {idx+1} 成功，累计单元: {len(merged_units)}")
        else:
            print(f" ❌ 切片 {idx+1} 失败，长诗作废！")
            return
        time.sleep(1.5)
        
    for i, unit in enumerate(merged_units, 1):
        unit["单元编号"] = f"U{i:03d}"
        unit["诗歌编号"] = poem['诗歌编号']
        
    poem["分析单元"] = merged_units
    file_path = os.path.join(OUTPUT_DIR, f"{poem['诗歌编号']}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(poem, f, ensure_ascii=False, indent=2)
    print(f" ✅ 《{poem['标题']}》所有切片完美缝合存入！总单元: {len(merged_units)}")

def main():
    print(f"🔥 V29 (V26.2 防御底座 + 批处理引擎) | 阈值: {BATCH_CHAR_LIMIT}字 | 批次容量: {MAX_POEMS_PER_BATCH}首")
    
    detect_active_model()
    
    all_poems = parse_txt_robust(INPUT_TXT)
    print(f"📜 载入库文件，共 {len(all_poems)} 首待处理。")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    processed_ids = {f.replace(".json", "") for f in os.listdir(OUTPUT_DIR) if f.endswith(".json")}
    unprocessed = [p for p in all_poems if p["诗歌编号"] not in processed_ids]
    print(f"💾 已跳过 {len(processed_ids)} 首，待处理 {len(unprocessed)} 首。")

    batch_queue = []
    current_char_count = 0

    for poem in unprocessed:
        p_len = len(poem['原文'])
        
        # 如果是长诗，先清空缓存的短诗，然后走长诗专用路线
        if p_len > BATCH_CHAR_LIMIT:
            if batch_queue:
                process_batch(batch_queue)
                batch_queue, current_char_count = [], 0
            process_long_poem(poem)
            continue
            
        # 如果装满 5 首，或者字数达到了 200 字红线，打包发车
        if len(batch_queue) >= MAX_POEMS_PER_BATCH or (current_char_count + p_len) > BATCH_CHAR_LIMIT:
            process_batch(batch_queue)
            batch_queue, current_char_count = [], 0
            
        batch_queue.append(poem)
        current_char_count += p_len

    # 发送最后一包
    if batch_queue:
        process_batch(batch_queue)

    print(f"\n🎉 任务全部圆满结束！请在 {OUTPUT_DIR}/ 文件夹查看。")

if __name__ == "__main__":
    main()