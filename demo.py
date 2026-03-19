"""
AI Chat with Visual Elements
Run:  streamlit run demo.py
"""

import streamlit as st
import streamlit_ai_elements as ai
from openai import OpenAI
import json
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Elements Chat", layout="centered")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("AI Elements")
    model = st.selectbox("Model", ["gpt-5.4", "gpt-4o", "gpt-4o-mini", "o4-mini"], index=0)
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.markdown(
        "**Rendering modes**\n\n"
        "- **JS Raw** — animated SVGs, custom HTML\n"
        "- **Vega-Lite** — data charts & plots\n"
        "- **Sandbox** — interactive dashboards (ECharts)\n"
    )

# ── OpenAI client ─────────────────────────────────────────────────────────────
api_key = os.environ.get("OPENAI_API_KEY", "")
base_url = os.environ.get("OPENAI_API_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or None

if not api_key:
    st.warning("Set `OPENAI_API_KEY` in your `.env` or environment to start chatting.")
    st.stop()

client = OpenAI(api_key=api_key, base_url=base_url)

# ── Tool definitions ──────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "js_raw",
            "description": (
                "Render raw HTML/CSS/JS directly in the chat. "
                "Use for animated SVGs, creative animations, canvas drawings, custom HTML elements. "
                "JS receives `container` (root DOM element) and safe `requestAnimationFrame`/`setInterval`/`setTimeout`. "
                "For SVG elements use document.createElementNS('http://www.w3.org/2000/svg', tag)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "html": {
                        "type": "string",
                        "description": "HTML markup",
                    },
                    "css": {
                        "type": "string",
                        "description": "CSS styles",
                    },
                    "js": {
                        "type": "string",
                        "description": (
                            "JavaScript code. Available globals: "
                            "container (root DOM), requestAnimationFrame, setInterval, setTimeout. "
                            "Use container.querySelector() to access elements."
                        ),
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vega_lite",
            "description": (
                "Render a Vega-Lite chart. Use for bar, line, scatter, area, and other data charts. "
                'Set "width": "container" for responsive sizing. Include data inline in the spec.'
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "spec": {
                        "type": "object",
                        "description": "A complete Vega-Lite v5 specification object.",
                    },
                },
                "required": ["spec"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sandbox",
            "description": (
                "Render an interactive dashboard with pre-loaded ECharts. "
                "Use for dashboards with sliders, metric cards, and dynamic charts. "
                "JS globals: container, echarts, d3, THREE, setStateValue, setTriggerValue, data, "
                "requestAnimationFrame, setInterval, setTimeout. "
                "Use container.innerHTML to build layout HTML, echarts.init(element) for charts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "js": {
                        "type": "string",
                        "description": "JavaScript code for the interactive dashboard.",
                    },
                    "libraries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Libraries to load: 'echarts', 'd3', 'three'. Default: ['echarts'].",
                    },
                },
                "required": ["js"],
            },
        },
    },
]

SYSTEM_PROMPT = """\
You are an AI assistant embedded in a Streamlit chat. You can render interactive \
visual elements directly in the conversation using tool calls.

When the user asks for something visual, choose the best tool:
- js_raw:    animated SVGs, creative animations, custom HTML/Canvas
- vega_lite: data charts (bar, line, scatter, area, heatmap…)
- sandbox:   interactive dashboards with sliders, metrics, ECharts

Guidelines:
- Write clean, self-contained code.
- Use modern CSS (flexbox/grid) for layouts.
- Make visualizations visually polished — choose good colors, spacing, and typography.
- Prefer SVG for vector graphics and animations.
- For sandbox dashboards: use container.innerHTML to set the layout, echarts.init() for charts.
- After rendering, briefly explain what you created.
"""

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []  # display format: {role, content, elements?}

# ── Helpers ───────────────────────────────────────────────────────────────────
DEFAULT_HEIGHTS = {"js_raw": 420, "vega_lite": 400, "sandbox": 560}


def render_element(elem: dict, key: str):
    """Dispatch a single rendered element to the right ai.* function."""
    t = elem["type"]
    args = elem["args"]
    h = DEFAULT_HEIGHTS.get(t, 400)
    if t == "js_raw":
        ai.js_raw(
            html=args.get("html", ""),
            css=args.get("css", ""),
            js=args.get("js", ""),
            height=h,
            key=key,
        )
    elif t == "vega_lite":
        ai.vega_lite(spec=args.get("spec", {}), height=h, key=key)
    elif t == "sandbox":
        ai.sandbox(
            js=args.get("js", ""),
            libraries=args.get("libraries"),
            height=h,
            key=key,
        )


def build_api_messages() -> list[dict]:
    """Convert display messages to OpenAI API format (text only, no tool history)."""
    api = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in st.session_state.messages:
        api.append({"role": msg["role"], "content": msg.get("content", "") or ""})
    return api


def call_llm(api_messages: list[dict]) -> dict:
    """
    Call OpenAI and handle tool calls.
    Returns {"content": str, "elements": list[dict]}.
    """
    response = client.chat.completions.create(
        model=model,
        messages=api_messages,
        tools=TOOLS,
    )
    message = response.choices[0].message

    elements = []
    text_parts = []

    if message.content:
        text_parts.append(message.content)

    if message.tool_calls:
        for tc in message.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            elements.append({"type": tc.function.name, "args": args})

        # Send tool results back and get follow-up text
        api_messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            }
        )
        for tc in message.tool_calls:
            api_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
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


# ── Render chat history ───────────────────────────────────────────────────────
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        # Render elements first, then text
        for j, elem in enumerate(msg.get("elements", [])):
            render_element(elem, key=f"el_{i}_{j}")
        if msg.get("content"):
            st.markdown(msg["content"])

# ── Chat input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask me to create something visual…"):
    # Show & store user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                result = call_llm(build_api_messages())
            except Exception as e:
                st.error(f"API error: {e}")
                st.stop()

        # Render elements
        msg_idx = len(st.session_state.messages)
        for j, elem in enumerate(result["elements"]):
            render_element(elem, key=f"el_{msg_idx}_{j}")

        # Display text
        if result["content"]:
            st.markdown(result["content"])

    # Store assistant message
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["content"],
            "elements": result["elements"],
        }
    )
