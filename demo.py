"""
AI Chat with Visual Elements
Run:  streamlit run demo.py
"""

import os
import pandas as pd
from openai import OpenAI
import streamlit as st

import streamlit_ai_elements as ai
from streamlit_ai_elements.chat_support import (
    build_api_messages,
    call_llm,
    render_element,
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Elements Chat", layout="centered")


def build_demo_resources(uploaded_file) -> tuple[dict[str, ai.RuntimeResource], pd.DataFrame | None]:
    if uploaded_file is None:
        return {}, None

    uploaded_file.seek(0)
    dataframe = pd.read_csv(uploaded_file)
    return (
        ai.resources(
            dataset=ai.resource.dataframe(
                dataframe,
                description=f"User-uploaded CSV file: {uploaded_file.name}",
                max_rows=1000,
                sample_rows=5,
            )
        ),
        dataframe,
    )

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
        "- **Sandbox** — interactive dashboards (ECharts)\n"
        "- **Pre-Built Component** — Vega-Lite, Excalidraw, and other structured renderers\n"
    )
    st.divider()
    uploaded_csv = st.file_uploader("Upload CSV Data", type=["csv"])

resources, uploaded_df = build_demo_resources(uploaded_csv)

with st.sidebar:
    if uploaded_df is not None:
        st.caption("Available to the assistant as runtime resource `dataset`.")
        st.caption(f"{len(uploaded_df):,} rows x {len(uploaded_df.columns)} columns")
        with st.expander("Preview Data", expanded=False):
            st.dataframe(uploaded_df.head(10), use_container_width=True)
    else:
        st.caption("Upload a CSV to make tabular data available during chat.")

# ── OpenAI client ─────────────────────────────────────────────────────────────
api_key = os.environ.get("OPENAI_API_KEY", "")
base_url = os.environ.get("OPENAI_API_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or None

if not api_key:
    st.warning("Set `OPENAI_API_KEY` in your `.env` or environment to start chatting.")
    st.stop()

client = OpenAI(api_key=api_key, base_url=base_url)

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []  # display format: {role, content, elements?}


# ── Render chat history ───────────────────────────────────────────────────────
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        # Render elements first, then text
        for j, elem in enumerate(msg.get("elements", [])):
            render_element(elem, key=f"el_{i}_{j}", resources=resources)
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
                result = call_llm(
                    client,
                    model,
                    build_api_messages(st.session_state.messages, resources=resources),
                )
            except Exception as e:
                st.error(f"API error: {e}")
                st.stop()

        # Render elements
        msg_idx = len(st.session_state.messages)
        for j, elem in enumerate(result["elements"]):
            render_element(elem, key=f"el_{msg_idx}_{j}", resources=resources)

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
