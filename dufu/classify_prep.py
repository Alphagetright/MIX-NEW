# -*- coding: utf-8 -*-
"""提取杜甫诗歌数据 → 纯文本文件（供本地模型分类使用）
   回写分类结果 → 将本地模型的输出写回 JSON 的 分类标签 字段
"""
import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

POEM_JSON_DIR = r"C:\Users\Administrator\Desktop\All Mix\poem_json"
OUTPUT_FILE = r"C:\Users\Administrator\Desktop\All Mix\dufu\classify_input.txt"

RULES = """边塞征战：边塞风光、将士思乡、战争实录、从军建功。
山水田园：自然景观、隐逸生活、农家情趣、四时之景。
咏史怀古：凭吊古迹、王朝兴衰、政治理想、借古讽今。
托物言志：人格象征（梅兰竹菊等）、政治寓托、人生志向。
送别酬赠：友人离别、席间唱和、友情寄托。
思乡怀人：羁旅愁思、客中思家、亲友怀念。
闺怨宫怨：女子哀怨、宫廷生活、相思之苦。
哲理感悟：人生哲理、禅意境界、世事洞察。"""

CLASSIFICATION_PROMPT = f"""你是一个唐诗题材分类专家。请为以下每首杜甫诗歌标注题材分类。

分类标准（严格按此执行）：
{RULES}

输出格式：每行一个 JSON 对象，不要换行，不要 markdown，只要纯 JSON 行：
{{"诗歌编号":"D0001","标题":"望岳","分类标签":"山水田园-自然景观"}}
{{"诗歌编号":"D0002","标题":"xxx","分类标签":"xxxx-xxxx"}}

标签格式：大类-子类，例如"山水田园-自然景观"、"边塞征战-战争实录"。

以下是待分类诗歌：
"""

def extract():
    """提取所有诗歌（D开头），每行格式：诗歌编号\t标题\t原文"""
    poems = []
    for fn in sorted(os.listdir(POEM_JSON_DIR)):
        if not fn.startswith('D') or not fn.endswith('.json'):
            continue
        with open(os.path.join(POEM_JSON_DIR, fn), 'r', encoding='utf-8') as f:
            data = json.load(f)
        poems.append({
            "诗歌编号": data.get("诗歌编号", fn.replace('.json', '')),
            "标题": data.get("标题", ""),
            "原文": data.get("原文", "")
        })

    print(f"共 {len(poems)} 首待分类")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(CLASSIFICATION_PROMPT)
        f.write("\n")
        for i, p in enumerate(poems):
            f.write(f"{p['诗歌编号']}\t{p['标题']}\t{p['原文']}\n")

    print(f"已写入 {OUTPUT_FILE}")
    print(f"\n使用流程：")
    print(f"  1. 将 classify_input.txt 的内容粘贴到 LM Studio，附带了分类规则")
    print(f"  2. 模型输出格式要求：每行一个 JSON 对象")
    print(f'     {{"诗歌编号":"D0001","标题":"望岳","分类标签":"山水田园-自然景观"}}')
    print(f"  3. 将输出保存到 dufu/classify_output.txt")
    print(f"  4. 运行 python classify_prep.py --writeback")
    return poems

def writeback():
    """读取本地模型输出，将分类标签写回每首诗的 JSON"""
    input_file = r"C:\Users\Administrator\Desktop\All Mix\dufu\classify_output.txt"
    if not os.path.exists(input_file):
        print(f"错误：未找到 {input_file}，请先运行本地模型并将输出保存到此文件")
        return

    ok = 0
    fail = 0
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # 跳过可能的非 JSON 行（模型可能输出思考过程）
            if not line.startswith('{'):
                continue
            try:
                obj = json.loads(line)
                pid = obj.get("诗歌编号", "")
                tag = obj.get("分类标签", "")
                if not pid or not tag:
                    continue
                json_path = os.path.join(POEM_JSON_DIR, f"{pid}.json")
                if not os.path.exists(json_path):
                    print(f"  跳过：{pid}.json 不存在")
                    fail += 1
                    continue
                with open(json_path, 'r', encoding='utf-8') as f2:
                    data = json.load(f2)
                data["分类标签"] = tag
                with open(json_path, 'w', encoding='utf-8') as f2:
                    json.dump(data, f2, ensure_ascii=False, indent=2)
                print(f"  OK: {pid} → {tag}")
                ok += 1
            except json.JSONDecodeError:
                continue

    print(f"\n完成：成功 {ok} 首，失败 {fail} 首")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--writeback':
        writeback()
    else:
        extract()
