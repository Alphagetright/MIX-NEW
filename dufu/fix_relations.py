# -*- coding: utf-8 -*-
"""
修复所有已有 JSON 的意象关系引用断裂
Pattern B: U{pid}{seq} → U{seq:05d}  (可修复)
Pattern A: 跨诗引用 → 移除无效关系
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

D = "poem-json"
fixed_count = 0
removed_count = 0
error_files = []

for fn in sorted(os.listdir(D)):
    if not fn.endswith('.json'): continue
    pid = fn.replace('.json', '')
    fpath = os.path.join(D, fn)

    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    units = data.get('分析单元', [])
    rels = data.get('意象关系', [])
    if not rels:
        continue

    unit_ids = {u['单元编号'] for u in units}
    pid_num = pid.replace('P', '')  # e.g., "044"

    new_rels = []
    fixed = 0
    removed = 0
    for rel in rels:
        src = rel.get('来源单元', '')
        tgt = rel.get('目标单元', '')
        src_ok = src in unit_ids
        tgt_ok = tgt in unit_ids

        if src_ok and tgt_ok:
            new_rels.append(rel)
            continue

        # Pattern B Fix: U{pid}{seq} → U{seq:05d}
        src_fixed = src
        tgt_fixed = tgt

        if not src_ok and src.startswith(f'U{pid_num}'):
            seq = src[len(f'U{pid_num}'):]
            if seq.isdigit():
                src_fixed = f"U{int(seq):05d}"
        if not tgt_ok and tgt.startswith(f'U{pid_num}'):
            seq = tgt[len(f'U{pid_num}'):]
            if seq.isdigit():
                tgt_fixed = f"U{int(seq):05d}"

        if src_fixed in unit_ids and tgt_fixed in unit_ids:
            rel['来源单元'] = src_fixed
            rel['目标单元'] = tgt_fixed
            new_rels.append(rel)
            fixed += 1
        else:
            # Pattern A or unfixable → skip
            removed += 1

    if fixed or removed:
        data['意象关系'] = new_rels
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        fixed_count += fixed
        removed_count += removed
        status = f"修复{fixed}条" if fixed else ""
        if removed:
            status += f" 移除{removed}条无法修复引用"
        print(f"  [✓] {fn}: {status}")

print(f"\n总计: 修复{fixed_count}条引用, 移除{removed_count}条无效引用")
