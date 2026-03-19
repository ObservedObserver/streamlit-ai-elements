"""Streamlit UI primitives for the chat subsystem."""

from __future__ import annotations

import json
from typing import Any, Callable

import streamlit as st

from .tools import render_element
from .types import ChatEvent, ChatMessage, StreamingSessionState, ToolCallCard, replay_timeline


ToolCardRenderer = Callable[[ToolCallCard, str, dict[str, Any] | None], None]
_TOOL_CARD_RENDERERS: dict[str, ToolCardRenderer] = {}


def register_tool_card_renderer(name: str, renderer: ToolCardRenderer) -> None:
    _TOOL_CARD_RENDERERS[name] = renderer


def chat_container(*, key: str | None = None):
    del key  # reserved for future keyed layouts
    return st.container()


def chat_message(role: str, *, name: str | None = None):
    return st.chat_message(role, name=name)


def chat_reasoning(content: str, *, expanded: bool = False, label: str = "Thinking") -> None:
    if not content:
        return
    title = f"{label}..." if expanded else label
    with st.expander(title, expanded=expanded):
        st.markdown(content)


def chat_tool_card(
    card: ToolCallCard,
    *,
    key: str,
    resources: dict[str, Any] | None = None,
) -> None:
    renderer = _TOOL_CARD_RENDERERS.get(card.tool_name, _render_generic_tool_card)
    renderer(card, key, resources)


def render_chat_message(
    message: ChatMessage,
    *,
    key_prefix: str,
    resources: dict[str, Any] | None = None,
    render_nonce: str | None = None,
) -> None:
    with st.chat_message(message.role):
        if message.reasoning:
            chat_reasoning(message.reasoning, expanded=message.status == "streaming")

        for index, tool_card in enumerate(message.tool_calls):
            tool_key = f"{key_prefix}_{message.id}_tool_{tool_card.id or index}"
            if render_nonce:
                tool_key = f"{tool_key}_{render_nonce}"
            chat_tool_card(
                tool_card,
                key=tool_key,
                resources=resources,
            )

        if message.content:
            st.markdown(message.content)

        if message.error:
            st.error(message.error)


def render_chat_session(
    state: StreamingSessionState | list[ChatEvent],
    *,
    resources: dict[str, Any] | None = None,
    key_prefix: str = "chat",
) -> StreamingSessionState:
    session = state if isinstance(state, StreamingSessionState) else replay_timeline(state)
    for index, message in enumerate(session.messages):
        render_chat_message(
            message,
            key_prefix=f"{key_prefix}_{message.id or index}",
            resources=resources,
        )
    return session


def chat_stream(
    events: Any,
    *,
    state: StreamingSessionState,
    resources: dict[str, Any] | None = None,
    key_prefix: str = "chat_stream",
) -> StreamingSessionState:
    live_timeline = list(state.timeline)
    placeholder = st.empty()
    for event in events:
        live_timeline.append(event)
        live_state = replay_timeline(live_timeline, session_id=state.session_id)
        if not live_state.messages:
            continue
        with placeholder.container():
            render_chat_message(
                live_state.messages[-1],
                key_prefix=key_prefix,
                resources=resources,
                render_nonce=str(len(live_timeline)),
            )
        state.timeline = list(live_state.timeline)
        state.messages = list(live_state.messages)
    return state


def _render_generic_tool_card(
    card: ToolCallCard,
    key: str,
    resources: dict[str, Any] | None,
) -> None:
    del resources  # not used
    del key
    label = _tool_card_label("Tool", card.tool_name, card.status)
    with st.expander(label, expanded=card.status != "completed"):
        if card.argument_preview:
            st.caption("Arguments")
            st.code(_format_json_preview(card.argument_preview), language="json")
        if card.output_preview:
            st.caption("Output")
            st.code(card.output_preview)


def _render_renderer_tool_card(
    card: ToolCallCard,
    key: str,
    resources: dict[str, Any] | None,
) -> None:
    label = _tool_card_label("Renderer", card.tool_name, card.status)
    with st.container():
        st.caption(label)
        if card.element is not None:
            if card.argument_preview and card.card_policy == "augment":
                with st.expander("Tool call", expanded=False):
                    st.code(_format_json_preview(card.argument_preview), language="json")
            render_element(card.element, key=key, resources=resources)
            return

        if card.output_preview:
            st.warning(card.output_preview)
        if card.argument_preview:
            with st.expander("Tool call", expanded=card.status == "streaming"):
                st.code(_format_json_preview(card.argument_preview), language="json")
        elif not card.output_preview:
            st.caption("Preparing renderer…")


def _format_json_preview(raw_arguments: str) -> str:
    try:
        return json.dumps(json.loads(raw_arguments), ensure_ascii=True, indent=2)
    except json.JSONDecodeError:
        return raw_arguments


def _tool_card_label(kind: str, tool_name: str, status: str) -> str:
    if status in {"streaming", "rendering"}:
        return f"{kind}: `{tool_name}`..."
    if status == "error":
        return f"{kind}: `{tool_name}` error"
    return f"{kind}: `{tool_name}`"


for _renderer_tool in ("js_raw", "sandbox", "prebuilt_component", "vega_lite", "excalidraw"):
    register_tool_card_renderer(_renderer_tool, _render_renderer_tool_card)
