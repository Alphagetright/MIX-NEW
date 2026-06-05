# -*- coding: utf-8 -*-
"""
编码检测与转换模块
==================
自动检测文本文件的字符编码，并转换为指定编码。
支持 UTF-8/GBK/GB2312/UTF-16/Big5/Latin-1 等常见编码。
"""

import os
from typing import Any, Dict, List, Optional, Tuple

from .config import COMMON_ENCODINGS
from .logger import get_logger
from .models import FileMeta

logger = get_logger("encoding_detector")


def detect_bom(file_path: str) -> Optional[str]:
    """检测文件 BOM 头"""
    with open(file_path, "rb") as f:
        head = f.read(4)
    if head.startswith(b"\xef\xbb\xbf"): return "utf-8-sig"
    if head.startswith(b"\xff\xfe\x00\x00"): return "utf-32-le"
    if head.startswith(b"\x00\x00\xfe\xff"): return "utf-32-be"
    if head.startswith(b"\xff\xfe"): return "utf-16-le"
    if head.startswith(b"\xfe\xff"): return "utf-16-be"
    return None


def detect_encoding(file_path: str, sample_size: int = 65536) -> Tuple[str, float]:
    """
    自动检测文件编码

    返回: (encoding_name, confidence)
    """
    # 先检查BOM
    bom_enc = detect_bom(file_path)
    if bom_enc:
        return bom_enc, 1.0

    # 读取样本
    try:
        with open(file_path, "rb") as f:
            raw = f.read(sample_size)
    except (OSError, PermissionError):
        return "unknown", 0.0

    if not raw:
        return "ascii", 1.0

    results = []
    for enc in COMMON_ENCODINGS:
        try:
            decoded = raw.decode(enc)
            # 评分：解码成功+中文占比合理 → 高分
            score = 1.0
            # 检测中文字符
            chinese_chars = sum(1 for c in decoded if "一" <= c <= "鿿")
            total_chars = len(decoded)
            if total_chars > 0 and chinese_chars > 0:
                score += min(chinese_chars / total_chars * 2, 1.0)
            # 检测乱码字符（替换字符、控制字符）
            bad = sum(1 for c in decoded if c in "�\x00\x01\x02\x03\x04\x05\x06\x07\x08")
            if bad > 0:
                score -= bad / total_chars * 5
            if score > 0:
                results.append((enc, score))
        except (UnicodeDecodeError, LookupError):
            continue

    results.sort(key=lambda x: x[1], reverse=True)
    if results:
        best_enc, best_score = results[0]
        confidence = min(best_score / 3.0, 1.0)
        return best_enc, round(confidence, 2)
    return "unknown", 0.0


def convert_encoding(file_path: str, target_encoding: str = "utf-8",
                     source_encoding: str = None) -> Tuple[str, str]:
    """
    将文件转换为目标编码

    返回: (new_file_path, detected_source_encoding)
    """
    if source_encoding is None:
        source_encoding, _ = detect_encoding(file_path)

    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        decoded = raw.decode(source_encoding)
        new_path = file_path + ".converted"
        with open(new_path, "w", encoding=target_encoding) as f:
            f.write(decoded)
        logger.info(f"编码转换: {file_path} ({source_encoding} → {target_encoding})")
        return new_path, source_encoding
    except (UnicodeDecodeError, UnicodeEncodeError) as e:
        logger.error(f"编码转换失败 [{file_path}]: {e}")
        return "", source_encoding


def detect_directory_encodings(directory: str,
                               extensions: List[str] = None) -> Dict[str, Any]:
    """
    批量检测目录下所有文件的编码

    返回: {"files": [{path, encoding, confidence}], "stats": {encoding: count}}
    """
    from .utils import list_files
    if extensions is None:
        extensions = [".json", ".txt", ".csv", ".tsv"]

    files = list_files(directory, extensions=extensions, recursive=True)
    results = []
    stats: Dict[str, int] = {}

    for fp in files:
        enc, conf = detect_encoding(fp)
        results.append({"path": fp, "encoding": enc, "confidence": conf})
        stats[enc] = stats.get(enc, 0) + 1
        if len(results) % 100 == 0:
            logger.debug(f"编码检测进度: {len(results)}/{len(files)}")

    logger.info(f"编码检测完成: {len(results)} 个文件, {len(stats)} 种编码")
    return {"files": results, "stats": stats, "total": len(results)}


def batch_convert_encoding(directory: str, target_encoding: str = "utf-8",
                           source_encoding: str = None) -> Dict[str, Any]:
    """批量转换目录下所有文件的编码"""
    from .utils import list_files
    files = list_files(directory, extensions=[".json", ".txt", ".csv"], recursive=True)
    converted = 0; failed = 0; errors = []
    for fp in files:
        new_path, detected = convert_encoding(fp, target_encoding, source_encoding)
        if new_path:
            # 替换原文件
            try:
                os.replace(new_path, fp)
                converted += 1
            except OSError as e:
                errors.append(str(e))
                failed += 1
        else:
            failed += 1

    return {"total": len(files), "converted": converted, "failed": failed,
            "target_encoding": target_encoding, "errors": errors}


def detect_encoding_quality(file_path: str) -> Dict[str, Any]:
    """评估文件编码质量"""
    enc, conf = detect_encoding(file_path)
    bom = detect_bom(file_path)
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
    except OSError:
        return {"encoding": enc, "confidence": conf, "quality": "unknown"}
    # 检测乱码字符比例
    try:
        decoded = raw.decode(enc) if enc != "unknown" else raw.decode("utf-8", errors="replace")
        total = len(decoded)
        bad_chars = sum(1 for c in decoded if c in "\x00\x01\x02\x03\x04\x05\x06\x07\x08�")
        quality = "good" if bad_chars / max(1, total) < 0.001 else "poor" if bad_chars / max(1, total) > 0.05 else "acceptable"
    except Exception:
        quality = "unreadable"
    return {"encoding": enc, "confidence": conf, "has_bom": bom is not None,
            "bom_type": bom, "quality": quality, "file_size_bytes": len(raw)}


def get_file_meta(file_path: str) -> FileMeta:
    """获取文件的完整元信息（含编码检测）"""
    import time as _time
    info = FileMeta()
    info.path = file_path; info.name = os.path.basename(file_path)
    info.extension = os.path.splitext(file_path)[1].lower()
    if os.path.exists(file_path):
        stat = os.stat(file_path)
        info.size = stat.st_size; info.modified = stat.st_mtime
        info.encoding, info.encoding_confidence = detect_encoding(file_path)
        info.has_bom = detect_bom(file_path) is not None
        try:
            with open(info.encoding or "utf-8", encoding=info.encoding or "utf-8") as f:
                content = f.read()
            info.has_markdown_wrap = content.strip().startswith("```")
            info.line_count = content.count("\n") + 1
            import json
            json.loads(content)
            info.is_valid_json = True
        except Exception:
            info.is_valid_json = False
    return info


# ─── 扩展编码功能 ───

def guess_encoding_by_content(raw_bytes: bytes) -> str:
    """通过字节内容特征猜测编码"""
    if not raw_bytes: return "ascii"
    if raw_bytes[:3] == b"\xef\xbb\xbf": return "utf-8-sig"
    if raw_bytes[:2] == b"\xff\xfe": return "utf-16-le"
    if raw_bytes[:2] == b"\xfe\xff": return "utf-16-be"
    try:
        decoded = raw_bytes.decode("utf-8")
        chinese = sum(1 for c in decoded if "一" <= c <= "鿿")
        if chinese > 0: return "utf-8"
    except: pass
    try:
        decoded = raw_bytes.decode("gbk")
        chinese = sum(1 for c in decoded if "一" <= c <= "鿿")
        if chinese > len(decoded) * 0.05: return "gbk"
    except: pass
    return "unknown"


def is_binary_file(file_path: str, sample_size: int = 1024) -> bool:
    """检测文件是否为二进制文件"""
    try:
        with open(file_path, "rb") as f:
            sample = f.read(sample_size)
        textchars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
        return bool(sample.translate(None, textchars))
    except: return True


def validate_encoding_consistency(file_path: str, declared_encoding: str) -> Dict[str, Any]:
    """验证文件声明的编码与实际编码是否一致"""
    detected, confidence = detect_encoding(file_path)
    result = {"file": file_path, "declared": declared_encoding,
              "detected": detected, "confidence": confidence,
              "consistent": detected == declared_encoding or
              (detected in declared_encoding) or (declared_encoding in detected)}
    if not result["consistent"]:
        result["warning"] = f"编码不一致: 声明{declared_encoding}, 检测{detected}"
    return result
