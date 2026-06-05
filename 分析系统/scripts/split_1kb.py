import os

def split_poetry_1kb_extreme(input_file, max_bytes=1024):
    if not os.path.exists(input_file):
        print(f"❌ 找不到文件: {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    poems = [p.strip() for p in content.split('==============================') if p.strip()]
    
    output_dir = "api_chunks_1kb"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"📄 共读取到 {len(poems)} 首诗歌。启动【1KB 极限防爆防截断】切分引擎...")

    current_chunk = []
    current_bytes = 0
    file_index = 1

    for poem in poems:
        poem_text = f"{poem}\n\n==============================\n\n"
        # 核心：计算真实的 UTF-8 字节数 (中文字符占 3 字节)
        poem_bytes = len(poem_text.encode('utf-8'))

        # 如果加入这首诗会超过 1KB (1024 bytes)，且当前块里已经有数据了，立刻封包！
        if current_bytes + poem_bytes > max_bytes and current_chunk:
            output_path = os.path.join(output_dir, f"chunk_{file_index:03d}.txt")
            with open(output_path, 'w', encoding='utf-8') as out_f:
                out_f.write("".join(current_chunk))
            print(f"✅ 生成切片: chunk_{file_index:03d}.txt (大小: {current_bytes} 字节)")
            
            # 重置状态，准备下一个文件
            file_index += 1
            current_chunk = []
            current_bytes = 0

        current_chunk.append(poem_text)
        current_bytes += poem_bytes

    # 把最后剩下的一点点尾料封包
    if current_chunk:
        output_path = os.path.join(output_dir, f"chunk_{file_index:03d}.txt")
        with open(output_path, 'w', encoding='utf-8') as out_f:
            out_f.write("".join(current_chunk))
        print(f"✅ 生成收尾切片: chunk_{file_index:03d}.txt (大小: {current_bytes} 字节)")

    print(f"🎉 全部切分完成！文件已安全存放在目录: {os.path.abspath(output_dir)}")
    print(f"⚠️ 警告：拿着这些 1KB 的碎片去请求 API，绝对不会再触发截断！")

if __name__ == "__main__":
    # 确保你的古诗源文件名为 source.txt
    split_poetry_1kb_extreme('source.txt', max_bytes=1024)