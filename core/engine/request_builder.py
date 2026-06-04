# -*- coding: utf-8 -*-
"""请求构建 —— API参数封装与消息结构组装"""


class APIParameters:
    """API参数配置"""

    def __init__(self, temperature=0.7, max_tokens=2048, top_p=0.9,
                 frequency_penalty=0.0, presence_penalty=0.0):
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty

    def to_dict(self):
        return {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
        }

    def validate(self):
        errors = []
        if not 0.0 <= self.temperature <= 2.0:
            errors.append("temperature must be in [0.0, 2.0]")
        if self.max_tokens < 1:
            errors.append("max_tokens must be >= 1")
        if not 0.0 <= self.top_p <= 1.0:
            errors.append("top_p must be in [0.0, 1.0]")
        return errors


class MessageBuilder:
    """消息结构构建"""

    def __init__(self):
        self._messages = []

    def add_system(self, content):
        self._messages.append({"role": "system", "content": content})
        return self

    def add_user(self, content):
        self._messages.append({"role": "user", "content": content})
        return self

    def add_assistant(self, content):
        self._messages.append({"role": "assistant", "content": content})
        return self

    def add_tool_result(self, tool_call_id, content):
        self._messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })
        return self

    def build(self):
        return list(self._messages)

    def count_messages(self):
        return len(self._messages)

    def clear(self):
        self._messages.clear()


class RequestBuilder:
    """完整请求构建"""

    def __init__(self, api_parameters=None):
        self.api_parameters = api_parameters or APIParameters()
        self.message_builder = MessageBuilder()

    def build_request(self, model="default", stream=False):
        messages = self.message_builder.build()
        if not messages:
            raise ValueError("No messages to send")
        request = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **self.api_parameters.to_dict(),
        }
        return request

    def build_batch_request(self, entries, model="default"):
        requests = []
        for entry in entries:
            self.message_builder.clear()
            if "system" in entry:
                self.message_builder.add_system(entry["system"])
            self.message_builder.add_user(entry.get("user", ""))
            if "assistant" in entry:
                self.message_builder.add_assistant(entry["assistant"])
            requests.append(self.build_request(model=model))
        return requests


class RequestValidator:
    """请求参数校验"""

    def validate(self, request):
        errors = []
        if "messages" not in request:
            errors.append("Missing 'messages' field")
            return errors
        messages = request["messages"]
        if not messages:
            errors.append("Empty messages list")
        for i, msg in enumerate(messages):
            if "role" not in msg:
                errors.append(f"Message {i}: missing 'role'")
            if "content" not in msg:
                errors.append(f"Message {i}: missing 'content'")
            if msg.get("role") not in ("system", "user", "assistant", "tool"):
                errors.append(f"Message {i}: invalid role '{msg.get('role')}'")
        if "temperature" in request:
            t = request["temperature"]
            if not isinstance(t, (int, float)) or t < 0 or t > 2:
                errors.append("temperature must be a float in [0, 2]")
        return errors

    def is_valid(self, request):
        return len(self.validate(request)) == 0
