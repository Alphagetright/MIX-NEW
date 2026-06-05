# -*- coding: utf-8 -*-
"""Generate terminal-style screenshots for build_docx.py"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = r"C:\Users\Administrator\Desktop\All Mix\cli_ops\screenshots"
os.makedirs(OUT_DIR, exist_ok=True)

FONT_PATH = None
for p in [
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\cour.ttf",
    r"C:\Windows\Fonts\msgothic.ttf",
]:
    if os.path.exists(p):
        FONT_PATH = p
        break


def render(text, name, title="tang-cli"):
    lines = text.split("\n")
    try:
        font = ImageFont.truetype(FONT_PATH, 14) if FONT_PATH else ImageFont.load_default()
        font_title = ImageFont.truetype(FONT_PATH, 12) if FONT_PATH else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
        font_title = ImageFont.load_default()

    img_w = 900
    line_h = 20
    padding = 20
    title_h = 30
    img_h = title_h + len(lines) * line_h + padding * 2
    if img_h > 8000:
        img_h = 8000

    img = Image.new("RGB", (img_w, img_h), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, img_w, title_h], fill=(60, 60, 60))
    try:
        draw.text((10, 7), title, fill=(200, 200, 200), font=font_title)
    except Exception:
        draw.text((10, 7), title, fill=(200, 200, 200))

    y = title_h + padding
    for line in lines:
        if y > img_h - padding:
            break
        clean = ""
        i = 0
        while i < len(line):
            if line[i] in ("\033", "\x1b"):
                j = i + 1
                while j < len(line) and line[j] != "m":
                    j += 1
                if j < len(line):
                    i = j + 1
                else:
                    break
            else:
                clean += line[i]
                i += 1
        try:
            draw.text((padding, y), clean, fill=(220, 220, 220), font=font)
        except Exception:
            draw.text((padding, y), clean, fill=(220, 220, 220))
        y += line_h

    path = os.path.join(OUT_DIR, name)
    img.save(path, "PNG")
    print(f"  {name} ({img_w}x{img_h})")


# ── All 10 screenshots ──

render(r"""  / 命令 -- 本地执行，不走 LLM

  数据操作
  /status        系统综合状态      /scan          扫描数据
  /export        多格式导出        /list-exports  导出列表

  运维管理
  /health        健康检查          /monitor-snap  监控快照
  /report        运维报告          /config-info   配置信息

  向量检索
  /search-rag    语义检索          /check-rag     向量库状态
  /build-rag     构建索引

  系统维护
  /clear-cache   清理缓存          /clean-logs    清理日志
  /backup        数据备份          /model         切换模型

  /help          显示帮助          /q /quit /exit 退出""", "01_help.png", "帮助命令列表 /help")

render(r"""  版本: 1.0.0        时间: 2026-05-29 02:57:59

  目录状态
  数据目录       : 存在 | 5 文件 | 110.11 MB
  导出目录       : 存在 | 11 文件 | 38.70 KB
  日志目录       : 存在 | 8 文件 | 19.93 KB
  缓存目录       : 存在 | 0 文件 | 0.00 B
  向量库         : 存在 | 5 文件 | 110.11 MB
  报告目录       : 存在 | 1 文件 | 2.95 KB
  备份目录       : 存在 | 0 文件 | 0.00 B

  缓存状态
  内存缓存条目   : 0          内存命中率     : 0.0%
  缓存启用       : 是          文件缓存条目   : 0

  系统资源
  磁盘使用率     : 97.0%      磁盘可用       : 6.9 GB
  内存使用率     : 68.2%      CPU 使用率     : 6.4%
  CPU 核心数     : 16

  导出文件: 11 个
  rag_边塞战争诗_20260528_054909.csv
  rag_杜甫描写山景的诗句_20260528_042936.csv
  rag_李白月亮_20260528_042922.csv""", "02_status.png", "系统状态总览 /status")

render(r"""  CURRENT_ENV                    : development
  DATA_DIR                       : cli_ops_system\data
  EXPORT_DIR                     : cli_ops_system\exports
  LOG_DIR                        : cli_ops_system\logs
  CACHE_DIR                      : cli_ops_system\cache
  LOG_LEVEL                      : INFO
  LOG_MAX_BYTES                  : 10485760
  LOG_BACKUP_COUNT               : 10
  CACHE_ENABLED                  : True
  CACHE_DEFAULT_TTL              : 600
  CACHE_MAX_MEMORY_ITEMS         : 5000
  CACHE_CLEANUP_STRATEGY         : lru
  EXPORT_CSV_ENCODING            : utf-8-sig
  EXPORT_MAX_ROWS                : 50000
  MONITOR_COLLECTION_INTERVAL    : 60
  MONITOR_DISK_THRESHOLD_PCT     : 90.0
  MONITOR_MEMORY_THRESHOLD_PCT   : 90.0
  MONITOR_CPU_THRESHOLD_PCT      : 85.0
  SCANNER_FILE_EXTENSIONS        : [.json, .txt, .csv, .tsv]
  SCANNER_MAX_FILE_SIZE_MB       : 500
  BATCH_PROCESSOR_MAX_WORKERS    : 4
  BATCH_PROCESSOR_CHUNK_SIZE     : 100
  HEALTH_CHECK_TIMEOUT           : 30
  HEALTH_CHECK_RETRIES           : 3""", "03_config_info.png", "系统配置信息 /config-info")

render(r"""============================================================
  系统健康检查报告
============================================================
  检查时间: 2026-05-29 02:58:08
  健康状态: 健康
  通过率:   87.5% (7/8)
  检查耗时: 1.23秒
------------------------------------------------------------

  警告 (1):
    1. [rag_db] 向量数据库存在但无集合

  建议操作 (1):
    1. 执行 build-rag 构建向量库
============================================================""", "04_health.png", "系统健康检查 /health")

render(r"""  扩展名过滤: 默认 (.json, .txt, .csv, .tsv)
  递归扫描: 是

  总文件数       : 4
  总大小         : 109.93 MB
  扫描耗时       : 0.02 秒
  跳过文件       : 0
  错误数         : 0
  无效JSON       : 1

  按扩展名分布:
    .json         :     4

  按大小分布:
    tiny          :     0
    small         :     3
    medium        :     0
    large         :     0
    huge          :     1""", "05_scan.png", "数据目录扫描 /scan")

render(r"""  导出目录: cli_ops_system\exports
  总文件数: 11    总大小: 0.04 MB

  文件名                                 格式     大小    修改时间
  --------------------------------------------------------------------------
  rag_边塞战争诗_20260528_054909.csv       csv   1.3 KB  2026-05-28 05:49
  rag_边塞战争诗_20260528_053559.csv       csv   1.3 KB  2026-05-28 05:35
  rag_杜甫描写山景的诗句_20260528_042936.csv  csv   1.1 KB  2026-05-28 04:29
  rag_李白月亮_20260528_042922.csv        csv   0.3 KB  2026-05-28 04:29
  rag_李白写月亮的诗_20260528_055517.csv    csv   1.1 KB  2026-05-28 05:55
  poetry_json_to_csv_20260528_041524.csv  csv   8.0 KB  2026-05-28 04:15
  export_csv_20260529_020917.csv          csv   8.0 KB  2026-05-29 02:09
  export_csv_20260528_041730.csv          csv   8.0 KB  2026-05-28 04:17
  export_csv_20260528_041703.csv          csv   8.0 KB  2026-05-28 04:17""", "06_list_exports.png", "导出文件列表 /list-exports")

render(r"""  索引文件    : poem_index.json
  构建时间    : 2026-05-28 05:21:58
  文档总数    : 15081
  已向量化    : 2000
  向量维度    : 2560
  模型        : text-embedding-qwen3-embedding-4b
  索引大小    : 109.87 MB""", "07_check_rag.png", "向量数据库状态 /check-rag")

render(r"""  采集时间: 2026-05-29 03:06:16

  磁盘: 97.0% 使用 | 可用 6.9GB / 总量 226.54GB
  内存: 76.7% 使用 | 可用 7.25GB / 总量 31.12GB
  CPU:  7.9% 使用 | 16 核心

  进程 PID: 59652 | Python 3.13.5
  运行时间: 0.6 秒
  内存 RSS: 47.01 MB

  历史快照: 1 条 (最新5条):
    2026-05-29 03:06:16  CPU=7.9%  Mem=76.7%  Disk=97.0%""", "08_monitor_snap.png", "系统监控快照 /monitor-snap")

render(r"""  模块导入测试 & 功能断言测试

  测试结果汇总:
  config              : PASS
  errors              : PASS
  logger              : PASS
  utils               : PASS
  validators          : FAIL
  models              : FAIL
  cache_manager       : FAIL
  monitor             : FAIL
  export_engine       : FAIL
  preprocessor        : FAIL
  data_scanner        : FAIL
  health_checker      : FAIL
  report_generator    : FAIL
  batch_processor     : FAIL

  测试结果: 4/18 通过, 14 失败
  (失败项需检查模块导入路径配置)""", "09_test.png", "单元测试 /test")

render(r"""  报告已生成: reports\ops_report_20260529_030625.txt
  文件大小: 3.0 KB

  报告内容包含:
  - 系统基本信息 (版本/环境/运行时间)
  - 数据概览 (文件数/总大小/数据质量)
  - 导出历史摘要
  - 系统资源趋势
  - 健康检查结果
  - 日志统计""", "10_report.png", "运维报告 /report")

print(f"\nDone! {len(os.listdir(OUT_DIR))} screenshots in {OUT_DIR}")
