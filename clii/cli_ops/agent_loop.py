# -*- coding: utf-8 -*-
"""
Agent Loop — 自主多步任务执行引擎
==================================

核心设计：
  用户输入自然语言目标 → LLM 拆解为多步工具调用 → 执行 → 观察结果 → 继续或结束

这使 cli_ops 从"等人类敲命令"升级为"接收一句话，自动干活"。
灵感来自 Claude Code 的 agent loop，但专为运维场景定制。

使用方式：
    from cli_ops.agent_loop import AgentLoop
    loop = AgentLoop()
    result = loop.run("检查系统状态，然后导出 CSV")

架构层次：
  用户自然语言
    → AgentLoop.run()
      → LLM（理解意图 + 选择工具）
        → ToolRegistry.execute()
          → cmd_* 函数（捕获输出）
        → 结果反馈给 LLM
      → 循环直到 done 或 max_steps
    → AgentResult
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .tools import registry, ToolResult
from .llm_client import call_llm_messages, build_agent_prompt, parse_agent_response


# ============================================================================
# 数据模型
# ============================================================================


@dataclass
class AgentStep:
    """单步执行记录"""
    step: int
    tool_name: str
    tool_args: Dict[str, Any]
    result_ok: bool
    result_output: str
    result_error: str
    duration_ms: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "tool": self.tool_name,
            "args": self.tool_args,
            "ok": self.result_ok,
            "output": self.result_output[:500],
            "error": self.result_error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class AgentResult:
    """Agent 完整执行结果"""
    success: bool
    goal: str
    steps: List[AgentStep] = field(default_factory=list)
    final_summary: str = ""
    total_duration_ms: float = 0.0
    error: str = ""

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def tools_called(self) -> List[str]:
        return [s.tool_name for s in self.steps]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "goal": self.goal,
            "step_count": self.step_count,
            "tools_called": self.tools_called,
            "steps": [s.to_dict() for s in self.steps],
            "final_summary": self.final_summary,
            "total_duration_ms": self.total_duration_ms,
            "error": self.error,
        }


# ============================================================================
# Agent Loop
# ============================================================================


class AgentLoop:
    """
    自主 Agent 循环引擎

    参数:
        max_steps: 最大执行步数（防止无限循环）
        verbose: 是否在控制台输出详细日志
        temperature: LLM 温度参数

    使用示例:
        loop = AgentLoop(max_steps=10)
        result = loop.run("扫描数据目录，检查健康状态，导出 CSV")
        if result.success:
            print(result.final_summary)
        else:
            print(f"Failed: {result.error}")
    """

    def __init__(
        self,
        max_steps: int = 10,
        verbose: bool = False,
        temperature: float = 0.1,
        on_step: callable = None,
        on_think: callable = None,
    ):
        self.max_steps = max_steps
        self.verbose = verbose
        self.temperature = temperature
        self.on_step = on_step    # callback(step: AgentStep) — 每步执行后
        self.on_think = on_think  # callback() — LLM 开始思考时

    # ── 主入口 ──

    def run(self, goal: str) -> AgentResult:
        """
        执行一个自然语言目标。

        参数:
            goal: 自然语言描述的任务，如 "检查系统状态并导出 CSV"

        返回:
            AgentResult: 完整执行结果
        """
        start_time = time.time()
        steps: List[AgentStep] = []

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"  Agent Goal: {goal}")
            print(f"{'='*60}\n", flush=True)

        # 获取工具描述
        tools_desc = registry.list_for_prompt()

        # 构建初始 prompt
        system_prompt, _ = build_agent_prompt(tools_desc, goal)

        # 对话历史：system + user + (assistant + user)*
        conversation = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": goal},
        ]

        for i in range(self.max_steps):
            # 通知思考开始
            if self.on_think:
                self.on_think()

            # 调用 LLM
            llm_response = self._call_llm_with_history(conversation)

            if not llm_response:
                result = AgentResult(
                    success=False,
                    goal=goal,
                    steps=steps,
                    error="LLM returned empty response",
                    total_duration_ms=round((time.time() - start_time) * 1000, 1),
                )
                return result

            # 解析响应
            parsed = parse_agent_response(llm_response)

            if parsed is None:
                # 解析失败，把原始响应当作文本继续
                conversation.append({"role": "assistant", "content": llm_response})
                conversation.append({"role": "user", "content": "Please respond with valid JSON: {\"tool\": \"...\", \"args\": {...}} or {\"done\": true, \"summary\": \"...\"}"})
                continue

            # 检查是否完成
            if parsed.get("done"):
                final_summary = parsed.get("summary", "Task completed.")
                if self.verbose:
                    print(f"\n  [DONE] {final_summary}\n", flush=True)
                result = AgentResult(
                    success=True,
                    goal=goal,
                    steps=steps,
                    final_summary=final_summary,
                    total_duration_ms=round((time.time() - start_time) * 1000, 1),
                )
                return result

            # 执行工具调用
            tool_name = parsed.get("tool", "")
            tool_args = parsed.get("args", {})

            if not tool_name:
                conversation.append({"role": "assistant", "content": llm_response})
                conversation.append({"role": "user", "content": "You didn't specify a tool. Available tools: " + ", ".join(registry.list_names())})
                continue

            if self.verbose:
                print(f"  [{i+1}/{self.max_steps}] Calling: {tool_name}({json.dumps(tool_args, ensure_ascii=False)})")

            tool_result = registry.execute(tool_name, tool_args)

            step = AgentStep(
                step=i + 1,
                tool_name=tool_name,
                tool_args=tool_args,
                result_ok=tool_result.ok,
                result_output=tool_result.output,
                result_error=tool_result.error,
                duration_ms=tool_result.duration_ms,
            )
            steps.append(step)

            # 通知步骤完成
            if self.on_step:
                self.on_step(step)

            if self.verbose:
                status = "[OK]" if tool_result.ok else "[FAIL]"
                preview = tool_result.output[:200].replace("\n", " ")
                print(f"  {status} {tool_result.duration_ms}ms | {preview}...", flush=True)

            # 将工具执行结果喂回 LLM
            feedback = self._format_tool_feedback(tool_result)
            conversation.append({"role": "assistant", "content": llm_response})
            conversation.append({"role": "user", "content": feedback})

        # 达到最大步数
        if self.verbose:
            print(f"\n  [WARN] Max steps ({self.max_steps}) reached.\n", flush=True)

        # 让 LLM 做最终总结
        summary = self._request_summary(conversation, steps)

        return AgentResult(
            success=False,
            goal=goal,
            steps=steps,
            final_summary=summary,
            error=f"Reached max steps ({self.max_steps}) without completing the task",
            total_duration_ms=round((time.time() - start_time) * 1000, 1),
        )

    # ── 内部方法 ──

    def _call_llm_with_history(self, conversation: list) -> str:
        """
        用完整对话历史调用 LLM（真正的多轮对话）。

        使用 messages 数组保持完整的上下文结构：
        system → user(task) → assistant(tool call) → user(result) → ...
        """
        # 裁剪过长历史：保留 system + 最近 N 轮对话
        if len(conversation) > 9:  # system + 4 round-trips max
            conversation = [conversation[0]] + conversation[-8:]

        # 裁剪每条 tool output 到合理长度
        trimmed = []
        for msg in conversation:
            content = msg.get("content", "")
            if msg["role"] == "user" and len(content) > 3000:
                # 截断过长的 tool output，保留开头和结尾
                content = content[:2000] + "\n...(output truncated)...\n" + content[-500:]
            trimmed.append({"role": msg["role"], "content": content})

        return call_llm_messages(trimmed, temperature=self.temperature)

    def _format_tool_feedback(self, result: ToolResult) -> str:
        """将工具执行结果格式化为 LLM 可理解的反馈"""
        if result.ok:
            return (
                f"Tool '{result.tool_name}' executed successfully in {result.duration_ms}ms.\n\n"
                f"Output:\n```\n{result.output[:2000]}\n```\n\n"
                f"Based on this output, decide: do you need another tool, or is the task done?\n"
                f"Respond with {{\"tool\": \"...\", \"args\": {{...}}}} or {{\"done\": true, \"summary\": \"...\"}}"
            )
        else:
            return (
                f"Tool '{result.tool_name}' FAILED: {result.error}\n\n"
                f"Partial output:\n```\n{result.output[:1000]}\n```\n\n"
                f"Decide: try a different approach, report the error, or mark as done."
            )

    def _request_summary(self, conversation: list, steps: List[AgentStep]) -> str:
        """任务未完成时，请求 LLM 总结已完成的工作"""
        summary_prompt = (
            f"The task could not be fully completed within {self.max_steps} steps. "
            f"Here's what was done:\n"
            + "\n".join(f"- {s.tool_name}: {'OK' if s.result_ok else 'FAILED'}" for s in steps)
            + "\n\nPlease provide a brief summary of what was accomplished and what remains."
        )
        conversation.append({"role": "user", "content": summary_prompt})
        text = self._call_llm_with_history(conversation)
        parsed = parse_agent_response(text)
        if parsed and parsed.get("summary"):
            return parsed["summary"]
        return text or "Task partially completed."


# ============================================================================
# 便捷函数
# ============================================================================


def run_agent(goal: str, max_steps: int = 10, verbose: bool = False) -> AgentResult:
    """
    一行式调用 Agent Loop。

    参数:
        goal: 自然语言任务描述
        max_steps: 最大步数
        verbose: 是否输出详细日志
    """
    loop = AgentLoop(max_steps=max_steps, verbose=verbose)
    return loop.run(goal)
