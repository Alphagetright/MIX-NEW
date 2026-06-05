# -*- coding: utf-8 -*-
"""Test script for LLM connectivity and agent loop."""
import os
import sys

# Set DeepSeek API config
os.environ["TCO_LLM_API_URL"] = "https://api.deepseek.com/v1/chat/completions"
os.environ["TCO_LLM_API_KEY"] = "sk-756637f89b754d17b7730e38ad37f651"
os.environ["TCO_LLM_MODEL"] = "deepseek-chat"

# Add parent (All Mix) to path so 'import cli_ops' works
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli_ops.llm_client import call_llm, call_llm_with_tools
from cli_ops.tools import registry
from cli_ops.agent_loop import AgentLoop

def test_llm():
    print("=== Test 1: Basic LLM call ===")
    response = call_llm(
        "Reply with ONLY valid JSON, no markdown.",
        'Output: {"status": "ok", "message": "hello from deepseek"}'
    )
    print(f"  Response: {response[:200]}")
    return bool(response)

def test_function_calling():
    print("\n=== Test 2: Function calling ===")
    tools = registry.list_for_llm()
    result = call_llm_with_tools(
        "You are a CLI operations agent. Use tools to answer.",
        "Show me the current system status.",
        tools[:5]
    )
    print(f"  Result: {result}")
    return result is not None

def test_agent_loop_simple():
    print("\n=== Test 3: Agent Loop (simple task) ===")
    loop = AgentLoop(max_steps=3, verbose=True)
    result = loop.run("Check the system status and list export files")
    print(f"\n  Success: {result.success}")
    print(f"  Steps: {result.step_count}")
    for s in result.steps:
        print(f"    [{s.step}] {s.tool_name} ok={s.result_ok} {s.duration_ms}ms")
    print(f"  Summary: {result.final_summary[:200]}")
    return result.success

if __name__ == "__main__":
    ok1 = test_llm()
    if not ok1:
        print("\n  LLM connection failed - check API key/network")
        sys.exit(1)

    ok2 = test_function_calling()
    ok3 = test_agent_loop_simple()

    print(f"\n{'='*60}")
    print(f"Results: LLM={ok1}, FuncCall={ok2}, AgentLoop={ok3}")
    print(f"{'='*60}")
