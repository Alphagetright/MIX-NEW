# -*- coding: utf-8 -*-
"""配置报告 —— 有效配置展示与差异对比"""


class ConfigReporter:
    """配置报告生成器"""

    def __init__(self, accessor):
        self.accessor = accessor

    def generate_report(self, format="text"):
        flat = self.accessor.flatten()
        if format == "text":
            return self._text_report(flat)
        elif format == "json":
            return self._json_report(flat)
        elif format == "table":
            return self._table_report(flat)
        return self._text_report(flat)

    def _text_report(self, flat):
        lines = ["Configuration Report", "=" * 60, ""]
        for key, value in sorted(flat.items()):
            lines.append(f"  {key:40s} = {value}")
        lines.append("")
        lines.append(f"Total config entries: {len(flat)}")
        return "\n".join(lines)

    def _json_report(self, flat):
        import json
        return json.dumps(flat, ensure_ascii=False, indent=2)

    def _table_report(self, flat):
        lines = ["+ {:-^38s} + {:-^38s} +".format("", ""), ""]
        lines[0] = "+" + "-" * 40 + "+" + "-" * 40 + "+"
        lines.insert(1, "| {:<38s} | {:<38s} |".format("Key", "Value"))
        lines.insert(2, "+" + "-" * 40 + "+" + "-" * 40 + "+")
        for key, value in sorted(flat.items()):
            val_str = str(value)[:38]
            lines.append("| {:<38s} | {:<38s} |".format(key[:38], val_str))
        lines.append("+" + "-" * 40 + "+" + "-" * 40 + "+")
        lines.append("")
        lines.append(f"Total: {len(flat)} entries")
        return "\n".join(lines)


class ConfigDiff:
    """配置差异对比"""

    @staticmethod
    def diff(config_a, config_b):
        added = {}
        removed = {}
        changed = {}

        all_keys = set(config_a.keys()) | set(config_b.keys())

        for key in all_keys:
            if key not in config_a:
                added[key] = config_b[key]
            elif key not in config_b:
                removed[key] = config_a[key]
            elif config_a[key] != config_b[key]:
                changed[key] = (config_a[key], config_b[key])

        return {
            "added": added,
            "removed": removed,
            "changed": changed,
            "added_count": len(added),
            "removed_count": len(removed),
            "changed_count": len(changed),
        }

    @staticmethod
    def diff_report(diff_result, format="text"):
        if format == "text":
            lines = ["Configuration Diff", "=" * 60, ""]
            if diff_result["added"]:
                lines.append(f"Added ({diff_result['added_count']}):")
                for k, v in diff_result["added"].items():
                    lines.append(f"  + {k} = {v}")
            if diff_result["removed"]:
                lines.append(f"Removed ({diff_result['removed_count']}):")
                for k, v in diff_result["removed"].items():
                    lines.append(f"  - {k} = {v}")
            if diff_result["changed"]:
                lines.append(f"Changed ({diff_result['changed_count']}):")
                for k, (old, new) in diff_result["changed"].items():
                    lines.append(f"  ~ {k}: {old} -> {new}")
            if not any([diff_result["added"], diff_result["removed"], diff_result["changed"]]):
                lines.append("  No differences")
            return "\n".join(lines)
        return diff_result
