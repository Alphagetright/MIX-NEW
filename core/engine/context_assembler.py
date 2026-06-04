# -*- coding: utf-8 -*-
"""上下文组装器 —— 指令拼接、示例注入、格式约束"""


class SystemInstructionBuilder:
    """系统指令构建"""

    def __init__(self):
        self._parts = []

    def add_instruction(self, instruction):
        self._parts.append(instruction)
        return self

    def add_constraint(self, constraint):
        self._parts.append(f"[Constraint] {constraint}")
        return self

    def add_example(self, input_text, output_text):
        self._parts.append(f"[Example]\nInput: {input_text}\nOutput: {output_text}")
        return self

    def add_format_spec(self, format_desc):
        self._parts.append(f"[Output Format]\n{format_desc}")
        return self

    def build(self, separator="\n\n"):
        return separator.join(self._parts)

    def clear(self):
        self._parts.clear()


class ContextAssembler:
    """上下文组装器"""

    def __init__(self):
        self.system = SystemInstructionBuilder()

    def assemble(self, poem_text, template_content=None, examples=None):
        parts = []
        if template_content:
            if isinstance(template_content, dict):
                if "system" in template_content:
                    parts.append(str(template_content["system"]))
                if "instructions" in template_content:
                    parts.append(str(template_content["instructions"]))
            else:
                parts.append(str(template_content))
        if examples:
            parts.append("[Examples]")
            for i, example in enumerate(examples[:3], 1):
                parts.append(f"Example {i}:")
                if isinstance(example, dict):
                    parts.append(f"  Input: {example.get('input', '')}")
                    parts.append(f"  Output: {example.get('output', '')}")
                else:
                    parts.append(f"  {example}")
        parts.append(f"[Poem Text]\n{poem_text}")
        return "\n\n".join(parts)

    def assemble_messages(self, poem_text, system_prompt=None):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": f"Analyze the following classical Chinese poem:\n\n{poem_text}"})
        return messages
