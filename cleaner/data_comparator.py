# -*- coding: utf-8 -*-
"""
数据对比模块
============
对比两个数据集/文件的差异，包括结构对比、内容对比、字段覆盖度对比。
"""

import os, json, time
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple

from .logger import get_logger

logger = get_logger("data_comparator")


class DataComparator:
    """
    数据对比器

    对比两个数据目录或文件集之间的差异。

    Usage:
        comparator = DataComparator()
        result = comparator.compare_directories("./data_v1", "./data_v2")
        print(f"新增: {result['added']}, 修改: {result['modified']}")
    """

    def __init__(self):
        self._results: Dict[str, Any] = {}

    def compare_files(self, file1: str, file2: str) -> Dict[str, Any]:
        """逐行对比两个文件"""
        result = {"file1": file1, "file2": file2, "same": False,
                  "differences": [], "similarity": 0.0}
        if not os.path.exists(file1) or not os.path.exists(file2):
            result["error"] = "文件不存在"; return result

        s1 = os.path.getsize(file1); s2 = os.path.getsize(file2)
        if s1 == s2:
            with open(file1, "rb") as f1, open(file2, "rb") as f2:
                same = f1.read() == f2.read()
            if same:
                result["same"] = True; result["similarity"] = 100.0; return result

        with open(file1, "r", encoding="utf-8", errors="replace") as f1:
            lines1 = f1.readlines()
        with open(file2, "r", encoding="utf-8", errors="replace") as f2:
            lines2 = f2.readlines()

        max_len = max(len(lines1), len(lines2))
        same_lines = sum(1 for i, l1 in enumerate(lines1) if i < len(lines2) and l1 == lines2[i])
        result["similarity"] = round(same_lines / max_len * 100, 2) if max_len > 0 else 100.0
        result["line_diff"] = len(lines2) - len(lines1)
        result["lines_same"] = same_lines; result["lines_changed"] = max_len - same_lines
        return result

    def compare_json_structure(self, data1: Any, data2: Any,
                               path: str = "root") -> List[Dict[str, Any]]:
        """递归对比两个JSON数据结构"""
        diffs = []
        t1, t2 = type(data1).__name__, type(data2).__name__
        if t1 != t2:
            return [{"path": path, "type": "type_mismatch", "v1": t1, "v2": t2}]

        if isinstance(data1, dict):
            keys1, keys2 = set(data1.keys()), set(data2.keys())
            for k in keys1 - keys2:
                diffs.append({"path": f"{path}.{k}", "type": "removed", "v1": str(data1[k])[:100]})
            for k in keys2 - keys1:
                diffs.append({"path": f"{path}.{k}", "type": "added", "v2": str(data2[k])[:100]})
            for k in keys1 & keys2:
                diffs.extend(self.compare_json_structure(data1[k], data2[k], f"{path}.{k}"))
        elif isinstance(data1, list):
            if len(data1) != len(data2):
                diffs.append({"path": path, "type": "length_diff",
                              "v1": len(data1), "v2": len(data2)})
            for i in range(min(len(data1), len(data2))):
                diffs.extend(self.compare_json_structure(data1[i], data2[i], f"{path}[{i}]"))
        else:
            if data1 != data2:
                diffs.append({"path": path, "type": "value_diff",
                              "v1": str(data1)[:100], "v2": str(data2)[:100]})
        return diffs

    def compare_json_files(self, file1: str, file2: str,
                           max_diffs: int = 50) -> Dict[str, Any]:
        """对比两个JSON文件的结构差异"""
        from .preprocessor import safe_parse_json
        data1, errs1 = safe_parse_json(file1)
        data2, errs2 = safe_parse_json(file2)

        result = {"file1": file1, "file2": file2, "json1_valid": data1 is not None,
                  "json2_valid": data2 is not None, "differences": []}

        if data1 is None or data2 is None:
            result["errors"] = errs1 + errs2; return result

        diffs = self.compare_json_structure(data1, data2)
        result["differences"] = diffs[:max_diffs]; result["total_diffs"] = len(diffs)
        return result

    def compare_directories(self, dir1: str, dir2: str) -> Dict[str, Any]:
        """对比两个目录的文件清单"""
        from .utils import list_files
        files1 = set(os.path.basename(f) for f in list_files(dir1))
        files2 = set(os.path.basename(f) for f in list_files(dir2))

        only_in_1 = sorted(files1 - files2)
        only_in_2 = sorted(files2 - files1)
        common = sorted(files1 & files2)

        modified = []
        for fn in common[:20]:
            fp1 = os.path.join(dir1, fn); fp2 = os.path.join(dir2, fn)
            s1 = os.path.getsize(fp1) if os.path.exists(fp1) else 0
            s2 = os.path.getsize(fp2) if os.path.exists(fp2) else 0
            if s1 != s2 or os.path.getmtime(fp1) != os.path.getmtime(fp2):
                modified.append({"file": fn, "size_diff": s2 - s1})

        return {"dir1": dir1, "dir2": dir2, "only_in_dir1": only_in_1,
                "only_in_dir2": only_in_2, "common": len(common),
                "modified": modified, "total_diff_files": len(only_in_1) + len(only_in_2)}

    def compare_field_values(self, data1: List[Dict], data2: List[Dict],
                             field: str) -> Dict[str, Any]:
        """对比两个数据集中某个字段的值分布"""
        vals1 = [item.get(field, "") for item in data1 if item.get(field)]
        vals2 = [item.get(field, "") for item in data2 if item.get(field)]

        c1 = Counter(vals1); c2 = Counter(vals2)
        all_values = set(list(c1.keys()) + list(c2.keys()))

        changes = []
        for v in all_values:
            diff = c2.get(v, 0) - c1.get(v, 0)
            if diff != 0:
                changes.append({"value": str(v)[:50], "before": c1.get(v, 0),
                                "after": c2.get(v, 0), "diff": diff})

        changes.sort(key=lambda x: abs(x["diff"]), reverse=True)
        return {"field": field, "total_values": len(all_values),
                "changed_values": len(changes), "top_changes": changes[:20]}


def quick_compare(file1: str, file2: str) -> Dict[str, Any]:
    """快速对比两个文件"""
    comparator = DataComparator()
    ext1 = os.path.splitext(file1)[1].lower()
    if ext1 in (".json", ".txt"):
        return comparator.compare_json_files(file1, file2)
    return comparator.compare_files(file1, file2)


def directory_snapshot(directory: str) -> Dict[str, Any]:
    """生成目录快照（用于后续对比）"""
    from .utils import list_files
    files = list_files(directory)
    return {
        "directory": directory,
        "timestamp": time.time(),
        "files": {os.path.basename(f): {
            "size": os.path.getsize(f),
            "mtime": os.path.getmtime(f),
        } for f in files},
    }


def diff_snapshots(snap1: Dict, snap2: Dict) -> Dict[str, Any]:
    """对比两个目录快照"""
    f1, f2 = snap1.get("files", {}), snap2.get("files", {})
    keys1, keys2 = set(f1.keys()), set(f2.keys())
    added = sorted(keys2 - keys1)
    removed = sorted(keys1 - keys2)
    changed = []
    for k in keys1 & keys2:
        if f1[k]["size"] != f2[k]["size"] or f1[k]["mtime"] != f2[k]["mtime"]:
            changed.append(k)
    return {"added": added, "removed": removed, "modified": sorted(changed),
            "unchanged": len(keys1 & keys2) - len(changed)}
