"""Пример агента на LangChain (DeepSeek) для демонстрации experiment.py.

Агент-продавец: системный промпт с «базой знаний» + инструмент get_price
(функциональные вызовы, OpenAI-совместимо — DeepSeek это умеет).

Запуск (нужен DEEPSEEK_API_KEY):
    uv run python examples/sales_agent.py
"""

from __future__ import annotations

import os

from langchain_openai import ChatOpenAI

from examples.sales_prompts import TOOLS, build_system_prompt


def make_llm() -> ChatOpenAI:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("DEEPSEEK_API_KEY не задан (export DEEPSEEK_API_KEY=sk-...)")
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=key,
        base_url="https://api.deepseek.com",
        temperature=0.2,
        max_tokens=150,
    )


def agent_turn(llm: ChatOpenAI, messages: list) -> list:
    """Один ход агента: вызов модели + выполнение tool-вызовов (простой цикл)."""
    resp = llm.invoke(messages, tools=TOOLS)
    messages.append(resp)
    while getattr(resp, "tool_calls", None):
        for tc in resp.tool_calls:
            args = tc.get("args") or {}
            sku = args.get("sku", "?")
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": f"Цена {sku}: 1490 руб."})
        resp = llm.invoke(messages, tools=TOOLS)
        messages.append(resp)
    return messages


def main() -> None:
    import sys

    version = sys.argv[1] if len(sys.argv) > 1 else "fixed"
    query = sys.argv[2] if len(sys.argv) > 2 else "Сколько стоит SKU-001?"
    llm = make_llm()
    messages: list = [{"role": "system", "content": build_system_prompt(version)}]
    messages.append({"role": "user", "content": query})
    messages = agent_turn(llm, messages)
    last = messages[-1]
    print(f"[{version}] ответ: {last.content}")


if __name__ == "__main__":
    main()
