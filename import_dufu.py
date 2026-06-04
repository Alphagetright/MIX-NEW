# -*- coding: utf-8 -*-
"""将杜甫数据接入系统，编号 D0001-D1346"""
import json, os, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')

src = os.path.join(os.path.dirname(__file__), "dufu", "poem-json")
dst = os.path.join(os.path.dirname(__file__), "poem_json")

count = 0
for fn in sorted(os.listdir(src)):
    if not fn.endswith('.json'):
        continue
    src_path = os.path.join(src, fn)
    with open(src_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 提取原诗歌编号数字部分
    old_id = data.get("诗歌编号", "")
    num = old_id.replace("P", "")
    if not num.isdigit():
        continue

    new_id = f"D{int(num):04d}"
    data["诗歌编号"] = new_id

    # 更新所有子字段
    for u in data.get("分析单元", []):
        u["诗歌编号"] = new_id
        uid = u.get("单元编号", "")
        u["单元编号"] = uid.replace(old_id, new_id)
        line_id = u.get("诗行编号", "")
        u["诗行编号"] = line_id.replace(old_id, new_id)

    for l in data.get("诗行", []):
        lid = l.get("诗行编号", "")
        l["诗行编号"] = lid.replace(old_id, new_id)

    for r in data.get("意象关系", []):
        for ref in ["来源单元", "目标单元"]:
            if r.get(ref):
                r[ref] = r[ref].replace(old_id, new_id)

    for e in data.get("情感轨迹", []):
        if e.get("诗行编号"):
            e["诗行编号"] = e["诗行编号"].replace(old_id, new_id)

    # 写文件
    dst_path = os.path.join(dst, f"{new_id}.json")
    with open(dst_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    count += 1

print(f"完成: {count} 首 (D0001-D{count:04d})")
