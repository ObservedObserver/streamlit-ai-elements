"""
AI Chat with Visual Elements
Run: streamlit run demo.py
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from openai import OpenAI

import streamlit_ai_elements as ai

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


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


with st.sidebar:
    st.title("AI Elements")
    model = st.selectbox("Model", ["gpt-5.4", "gpt-4o", "gpt-4o-mini", "o4-mini"], index=0)
    backend = st.selectbox(
        "Backend",
        ["responses", "chat_completions"],
        index=0,
        help="Responses API is the canonical streaming path. Chat Completions is adapted into the same event model.",
    )
    if st.button("Clear chat"):
        st.session_state.chat_session = ai.create_chat_session()
        st.rerun()
    st.divider()
    st.markdown(
        "**Rendering modes**\n\n"
        "- **JS Raw**: animated SVGs, custom HTML\n"
        "- **Sandbox**: interactive dashboards with ECharts\n"
        "- **Pre-Built Component**: Vega-Lite and Excalidraw\n"
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


api_key = os.environ.get("OPENAI_API_KEY", "")
base_url = os.environ.get("OPENAI_API_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or None

if not api_key:
    st.warning("Set `OPENAI_API_KEY` in your `.env` or environment to start chatting.")
    st.stop()

client = OpenAI(api_key=api_key, base_url=base_url)

if "chat_session" not in st.session_state:
    st.session_state.chat_session = ai.create_chat_session()


ai.render_chat_session(st.session_state.chat_session, resources=resources)


if prompt := st.chat_input("Ask me to create something visual…"):
    st.session_state.chat_session = ai.append_user_message(st.session_state.chat_session, prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    config = ai.ChatBackendConfig(
        model=model,
        backend=backend,
        reasoning_effort="medium",
        reasoning_summary="auto",
    )
    ai.chat_stream(
        ai.stream_assistant_turn(
            client,
            state=st.session_state.chat_session,
            config=config,
            resources=resources,
        ),
        state=st.session_state.chat_session,
        resources=resources,
        key_prefix="demo_stream",
    )
