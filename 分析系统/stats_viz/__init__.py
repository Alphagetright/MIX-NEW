# -*- coding: utf-8 -*-
"""
诗歌意象多维统计与可视化系统
============================
独立的统计分析系统，提供古典诗歌意象数据的多维聚合统计、交互式可视化图表、
结构化数据导出和统计报告生成功能。

核心模块：
  - stats_engine        多维统计引擎（频次/分类/情感/感知/诗人/交叉分析）
  - data_loader         数据加载与缓存管理
  - chart_data_builder  图表数据构建（ECharts 适配）
  - export_service      多格式数据导出（CSV/JSON/HTML报告）
  - report_builder      统计分析报告生成
  - preprocessor        数据预处理与清洗
  - models              核心数据模型定义
  - config              配置管理
  - logger              日志系统
  - errors              异常体系
  - utils               通用工具函数集
  - validators           输入校验模块

版本：V1.0
开发完成日期：2026年5月
"""

__version__ = "1.0.0"
__all__ = [
    "stats_engine", "data_loader", "chart_data_builder",
    "export_service", "report_builder", "preprocessor",
    "models", "config", "logger", "errors", "utils", "validators",
]
