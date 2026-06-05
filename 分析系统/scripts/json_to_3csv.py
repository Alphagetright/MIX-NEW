import json
import csv
import os
import glob

def aggregate_jsons_to_csv():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_folder = os.path.join(base_dir, 'json_data')
    
    if not os.path.exists(json_folder):
        print(f"❌ 找不到文件夹: {json_folder}，请创建并放入JSON文件！")
        return

    json_files = glob.glob(os.path.join(json_folder, '*.json'))
    if not json_files:
        print("❌ 文件夹里没有找到任何 .json 文件！")
        return

    print(f"🔍 发现 {len(json_files)} 个 JSON 文件，正在执行安全解析与聚合...")

    # --- 1. 定义三张表的表头 ---
    header_a = [
        "诗歌编号", "标题", "作者", "分类标签", "诗行编号", 
        "单元编号", "文本", "行内位置", "词性", "成分类型", 
        "是否意象", "大类编码", "子类编码", "感知通道", "素材类型", 
        "内部结构", "指涉来源", "表现功能", "文化流通性", "跨文化性", 
        "认知强度", "核心意象", "结构功能组", "情感极性", "情感类别", "情感置信度"
    ]
    
    header_b = [
        "诗歌编号", "标题", "作者", "分类标签", 
        "诗行编号", "诗行原文", 
        "平均情感极性", "主导情感", "情感波动值"
    ]
    
    header_c = [
        "诗歌编号", "标题", "作者", "关系编号", 
        "来源单元编号", "来源文本", 
        "目标单元编号", "目标文本", 
        "关系类型", "关系强度"
    ]

    rows_a, rows_b, rows_c = [], [], []

    # 全局计数器（解决所有文件都从 P01 和 U001 开始的 Bug）
    global_poem_idx = 1
    global_unit_idx = 1
    global_rel_idx = 1
    global_traj_idx = 1

    # --- 2. 遍历所有 JSON 文件 ---
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️ 解析失败，跳过损坏的 JSON 文件 {os.path.basename(file_path)}: {e}")
            continue

        poems = data.get("诗歌集", []) if isinstance(data, dict) else data
        
        # --- 3. 遍历文件内的诗歌 ---
        for p in poems:
            # 分配全局唯一的诗歌 ID
            new_p_id = f"P{global_poem_idx:03d}"
            global_poem_idx += 1
            
            title = p.get("标题", "")
            author = p.get("作者", "")
            tag = p.get("分类标签", "")
            base_meta = [new_p_id, title, author, tag]

            # 建立旧 ID 到新 ID 的映射字典，防止指针错乱
            line_id_map = {}
            unit_id_map = {}
            unit_text_map = {} # 用于关系表反查文本

            # 3.1 提取诗行并映射新 ID
            line_text_map = {}
            for i, line in enumerate(p.get("诗行", []), 1):
                old_l_id = line.get("诗行编号", "")
                new_l_id = f"{new_p_id}_L{i:02d}"
                line_id_map[old_l_id] = new_l_id
                line_text_map[new_l_id] = line.get("原文", "")

            # 3.2 解析表 A：分析单元 (并映射全局单元 ID)
            for u in p.get("分析单元", []):
                old_u_id = u.get("单元编号", "")
                new_u_id = f"U{global_unit_idx:05d}"
                global_unit_idx += 1
                
                unit_id_map[old_u_id] = new_u_id
                text_val = u.get("文本", "")
                unit_text_map[new_u_id] = text_val
                
                # 转换对应的诗行 ID
                old_u_line = u.get("诗行编号", "")
                mapped_l_id = line_id_map.get(old_u_line, old_u_line)

                rows_a.append([
                    new_p_id, title, author, tag, mapped_l_id,
                    new_u_id, text_val, u.get("行内位置", ""), 
                    u.get("词性", ""), u.get("成分类型", ""), u.get("是否意象", ""), 
                    u.get("大类编码", ""), u.get("子类编码", ""), u.get("感知通道", ""), 
                    u.get("素材类型", ""), u.get("内部结构", ""), u.get("指涉来源", ""), 
                    u.get("表现功能", ""), u.get("文化流通性", ""), u.get("跨文化性", ""), 
                    u.get("认知强度", ""), u.get("核心意象", ""), u.get("结构功能组", ""), 
                    u.get("情感极性", ""), u.get("情感类别", ""), u.get("情感置信度", "")
                ])

            # 3.3 解析表 B：情感轨迹
            for traj in p.get("情感轨迹", []):
                old_t_line = traj.get("诗行编号", "")
                mapped_t_line = line_id_map.get(old_t_line, old_t_line)
                
                rows_b.append(base_meta + [
                    mapped_t_line, line_text_map.get(mapped_t_line, ""),
                    traj.get("平均情感极性", ""), traj.get("主导情感", ""), traj.get("情感波动值", "")
                ])

            # 3.4 解析表 C：意象关系网络 (核心：修复指针)
            for r in p.get("意象关系", []):
                new_r_id = f"R{global_rel_idx:04d}"
                global_rel_idx += 1
                
                old_src = r.get("来源单元", "")
                old_tgt = r.get("目标单元", "")
                
                # 指针映射到新的全局 ID
                new_src = unit_id_map.get(old_src, old_src)
                new_tgt = unit_id_map.get(old_tgt, old_tgt)

                rows_c.append([new_p_id, title, author] + [
                    new_r_id, 
                    new_src, unit_text_map.get(new_src, "未知"), 
                    new_tgt, unit_text_map.get(new_tgt, "未知"), 
                    r.get("关系类型", ""), r.get("关系强度", "")
                ])

    # --- 4. 写入 CSV 文件的标准函数 ---
    def save_csv(filename, header, rows):
        output_path = os.path.join(base_dir, filename)
        # utf-8-sig 防止 Excel 打开中文乱码
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        return output_path

    if rows_a:
        path_a = save_csv("Table_A_Atomic.csv", header_a, rows_a)
        path_b = save_csv("Table_B_Lines.csv", header_b, rows_b)
        path_c = save_csv("Table_C_Relations.csv", header_c, rows_c)

        print("\n✅ 数据转换与全局重排成功！文件已生成至当前目录：")
        print(f"📊 Table A (共 {len(rows_a)} 个分析单元): {path_a}")
        print(f"📊 Table B (共 {len(rows_b)} 条诗行轨迹): {path_b}")
        print(f"📊 Table C (共 {len(rows_c)} 对意象关系): {path_c}")
    else:
        print("\n⚠️ 警告：没有从 JSON 文件中提取到任何有效数据。")

if __name__ == "__main__":
    aggregate_jsons_to_csv()