# -*- coding: utf-8 -*-
"""
TangCLI 便携启动器
==================
一键启动：Web 服务 + REPL（支持自然语言 Agent）

打包为 EXE 后，拷贝整个 dist/ 文件夹到任意电脑即可使用。
"""

import os
import sys
import time
import threading
import socket


def _find_free_port(start=5001):
    """找一个可用端口"""
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return 5001


def _get_base_dir():
    """获取项目根目录（兼容 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    base = _get_base_dir()

    # 确保工作目录正确
    os.chdir(base)

    # 设置数据目录（兼容 PyInstaller）
    for d in ["exports", "logs", "cache", "reports", "backups", "rag_db"]:
        os.makedirs(os.path.join(base, d), exist_ok=True)

    # 启动 Web 服务
    port = _find_free_port(5001)
    web_url = f"http://127.0.0.1:{port}"

    def _run_web():
        from cli_ops.web.app import app
        app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

    web_thread = threading.Thread(target=_run_web, daemon=True)
    web_thread.start()
    time.sleep(0.5)

    print(f"\n{'='*60}")
    print(f"  唐诗意象数据运维管理系统")
    print(f"  TangCLI v1.0  Portable Edition")
    print(f"{'='*60}")
    print(f"  Web 控制台:  {web_url}")
    print(f"  API 端点:    {web_url}/api/v1/")
    print(f"  Agent 端点:  POST {web_url}/api/v1/agent/run")
    print(f"  工具发现:    {web_url}/api/v1/agent/tools")
    print(f"{'='*60}")
    print(f"  输入自然语言让 AI Agent 自动执行任务")
    print(f"  或使用斜杠命令: /help /status /scan /export ...")
    print(f"  Ctrl+C 退出")
    print(f"{'='*60}\n")

    # 启动 REPL
    try:
        from cli_ops.repl import launch_repl
        launch_repl()
    except KeyboardInterrupt:
        print("\n  再见。")
    except Exception as e:
        print(f"\n  错误: {e}")
        print("  按 Enter 退出...")
        input()


if __name__ == "__main__":
    main()
