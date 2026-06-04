# -*- coding: utf-8 -*-
"""模板渲染器 —— 变量替换、条件块、循环展开"""

import re


class VariableReplacer:
    """变量替换"""

    def __init__(self, pattern=r"\{\{(\w+)\}\}"):
        self.pattern = re.compile(pattern)

    def replace(self, text, variables):
        def _replacer(match):
            key = match.group(1)
            return str(variables.get(key, match.group(0)))
        return self.pattern.sub(_replacer, text)

    def extract_variables(self, text):
        return set(self.pattern.findall(text))

    def has_unresolved(self, text):
        return bool(self.pattern.search(text))


class ConditionalBlock:
    """条件块处理"""

    def __init__(self):
        self._if_pattern = re.compile(r"\{\% if (\w+) \%\}(.*?)\{\% endif \%\}", re.DOTALL)
        self._if_else_pattern = re.compile(r"\{\% if (\w+) \%\}(.*?)\{\% else \%\}(.*?)\{\% endif \%\}", re.DOTALL)

    def process(self, text, variables):
        text = self._process_if_else(text, variables)
        text = self._process_if(text, variables)
        return text

    def _process_if(self, text, variables):
        def _replacer(match):
            key = match.group(1)
            content = match.group(2)
            if variables.get(key):
                return content
            return ""
        return self._if_pattern.sub(_replacer, text)

    def _process_if_else(self, text, variables):
        def _replacer(match):
            key = match.group(1)
            if_content = match.group(2)
            else_content = match.group(3)
            if variables.get(key):
                return if_content
            return else_content
        return self._if_else_pattern.sub(_replacer, text)


class LoopBlock:
    """循环块处理"""

    def __init__(self):
        self._pattern = re.compile(r"\{\% for (\w+) in (\w+) \%\}(.*?)\{\% endfor \%\}", re.DOTALL)

    def process(self, text, variables):
        def _replacer(match):
            item_name = match.group(1)
            list_name = match.group(2)
            template = match.group(3)
            items = variables.get(list_name, [])
            result = []
            for item in items:
                item_vars = dict(variables)
                item_vars[item_name] = item
                result.append(self._replace_vars(template, item_vars))
            return "".join(result)
        return self._pattern.sub(_replacer, text)

    def _replace_vars(self, text, variables):
        return re.sub(r"\{\{(\w+)\}\}", lambda m: str(variables.get(m.group(1), m.group(0))), text)


class TemplateRenderer:
    """模板渲染器 —— 综合渲染"""

    def __init__(self):
        self.variable = VariableReplacer()
        self.conditional = ConditionalBlock()
        self.loop = LoopBlock()

    def render(self, template, variables):
        if isinstance(template, dict):
            return self._render_dict(template, variables)
        elif isinstance(template, list):
            return self._render_list(template, variables)
        else:
            return self._render_string(str(template), variables)

    def _render_string(self, text, variables):
        text = self.loop.process(text, variables)
        text = self.conditional.process(text, variables)
        text = self.variable.replace(text, variables)
        return text

    def _render_dict(self, d, variables):
        return {k: self.render(v, variables) for k, v in d.items()}

    def _render_list(self, lst, variables):
        return [self.render(item, variables) for item in lst]
