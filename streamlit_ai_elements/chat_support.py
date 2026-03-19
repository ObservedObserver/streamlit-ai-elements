"""Compatibility/demo helpers built on top of the Chat Kit internals."""

from __future__ import annotations

import json
from typing import Any

import streamlit_ai_elements as ai

from .chat.tools import (
    DEFAULT_HEIGHTS,
    PREBUILT_COMPONENT_HEIGHTS,
    SYSTEM_PROMPT,
    build_chat_completions_tools,
    build_system_prompt,
    element_from_tool_call,
    render_element,
)

TOOLS = build_chat_completions_tools()


def build_api_messages(
    messages: list[dict[str, Any]],
    resources: dict[str, ai.RuntimeResource] | None = None,
) -> list[dict[str, Any]]:
    """Convert display messages to Chat Completions API format."""
    api_messages = [{"role": "system", "content": build_system_prompt(resources)}]
    for message in messages:
        api_messages.append(
            {
                "role": message["role"],
                "content": message.get("content", "") or "",
            }
        )
    return api_messages


def call_llm(client: Any, model: str, api_messages: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Legacy non-streaming helper used by the existing tests and compatibility paths.
    Returns {"content": str, "elements": list[dict]}.
    """
    response = client.chat.completions.create(
        model=model,
        messages=api_messages,
        tools=TOOLS,
    )
    message = response.choices[0].message

    elements: list[dict[str, Any]] = []
    text_parts: list[str] = []

    if message.content:
        text_parts.append(message.content)

    if message.tool_calls:
        assistant_tool_calls_payload: list[dict[str, Any]] = []
        for tool_call in message.tool_calls:
            raw_arguments = tool_call.function.arguments
            try:
                parsed_arguments = json.loads(raw_arguments)
            except json.JSONDecodeError:
                parsed_arguments = {}

            element = element_from_tool_call(tool_call.function.name, parsed_arguments)
            if element is not None:
                elements.append(element)

            assistant_tool_calls_payload.append(
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": raw_arguments,
                    },
                }
            )

        api_messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": assistant_tool_calls_payload,
            }
        )
        for tool_call in message.tool_calls:
            api_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": "Element rendered successfully in the chat.",
                }
            )

        follow_up = client.chat.completions.create(
            model=model,
            messages=api_messages,
        )
        if follow_up.choices[0].message.content:
            text_parts.append(follow_up.choices[0].message.content)

    return {"content": "\n\n".join(text_parts), "elements": elements}


__all__ = [
    "DEFAULT_HEIGHTS",
    "PREBUILT_COMPONENT_HEIGHTS",
    "SYSTEM_PROMPT",
    "TOOLS",
    "build_api_messages",
    "call_llm",
    "render_element",
]
