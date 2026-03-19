# streamlit-ai-elements

`streamlit-ai-elements` is a Streamlit component library for rendering AI-generated UI inside chat and app layouts.

It provides:

- raw HTML/CSS/JS rendering
- sandboxed interactive dashboards with preloaded libraries
- pre-built renderers such as Vega-Lite and Excalidraw
- a lightweight Chat Kit for streaming assistant output, reasoning blocks, and tool-call cards
- runtime resources that can be exposed to both the model and the frontend



https://github.com/user-attachments/assets/ff4424a9-59d6-4a8f-8116-6732060d3e26



## Installation

```bash
pip install streamlit-ai-elements
```

For chat demos with OpenAI:

```bash
pip install openai python-dotenv
```

## Quick Start

```python
import streamlit as st
import streamlit_ai_elements as ai

st.title("Hello, AI Elements")

ai.js_raw(
    html="<div class='card'>Hello from AI Elements</div>",
    css="""
    .card {
        padding: 16px;
        border-radius: 12px;
        background: linear-gradient(135deg, #f7efe5, #dceeff);
        font: 600 18px/1.4 system-ui;
    }
    """,
)
```

## Core APIs

### Renderers

The library exposes four main rendering entrypoints:

- `ai.js_raw(...)`
- `ai.sandbox(...)`
- `ai.vega_lite(...)`
- `ai.excalidraw(...)`

### Runtime Resources

Resources let you pass structured data to renderers and chat tools:

- `ai.resource.dataframe(...)`
- `ai.resource.sql_database(...)`
- `ai.resources(...)`

### Chat Kit

The chat subsystem is built for streaming assistant output and tool-call rendering:

- `ai.ChatBackendConfig(...)`
- `ai.create_chat_session()`
- `ai.append_user_message(...)`
- `ai.stream_assistant_turn(...)`
- `ai.stream_chat_turn(...)`
- `ai.render_chat_session(...)`
- `ai.chat_stream(...)`

## Renderer Examples

### 1. Raw HTML / CSS / JS

```python
import streamlit_ai_elements as ai

ai.js_raw(
    html="<div id='app'></div>",
    css="#app { padding: 12px; font-family: system-ui; }",
    js="""
    container.querySelector("#app").innerHTML = `
      <h3>Raw Renderer</h3>
      <p>This block was rendered from HTML, CSS, and JS.</p>
    `;
    """,
)
```

### 2. Sandbox Dashboard

`sandbox(...)` is useful when you want a JavaScript runtime with preloaded libraries such as `echarts`, `d3`, or `three`.

```python
import streamlit_ai_elements as ai

ai.sandbox(
    js="""
    container.innerHTML = `
      <div style="padding:16px">
        <h3>Sandbox</h3>
        <div id="chart" style="height:320px"></div>
      </div>
    `;

    const chart = echarts.init(container.querySelector("#chart"));
    chart.setOption({
      xAxis: { type: "category", data: ["Mon", "Tue", "Wed", "Thu"] },
      yAxis: { type: "value" },
      series: [{ type: "bar", data: [12, 20, 15, 8] }],
    });
    """,
    libraries=["echarts"],
)
```

### 3. Vega-Lite Chart

Use `ai.vega_lite(...)` for standard declarative charts.

```python
import streamlit_ai_elements as ai

ai.vega_lite(
    spec={
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": "container",
        "mark": "bar",
        "data": {
            "values": [
                {"category": "A", "value": 28},
                {"category": "B", "value": 55},
                {"category": "C", "value": 43},
            ]
        },
        "encoding": {
            "x": {"field": "category", "type": "nominal"},
            "y": {"field": "value", "type": "quantitative"},
        },
    }
)
```

### 4. Excalidraw Diagram

```python
import streamlit_ai_elements as ai

ai.excalidraw(
    shapes=[
        {"id": "start", "type": "rounded-rectangle", "x": 80, "y": 80, "width": 180, "height": 64, "text": "Start"},
        {"id": "done", "type": "rectangle", "x": 360, "y": 80, "width": 180, "height": 64, "text": "Done"},
    ],
    connectors=[
        {"from": "start", "to": "done", "text": "next"},
    ],
)
```

## Using Resources

Resources can be shared with renderers and chat tools.

```python
import pandas as pd
import streamlit_ai_elements as ai

df = pd.DataFrame(
    [
        {"month": "Jan", "revenue": 120},
        {"month": "Feb", "revenue": 180},
        {"month": "Mar", "revenue": 160},
    ]
)

runtime_resources = ai.resources(
    sales=ai.resource.dataframe(
        df,
        description="Monthly sales data",
    )
)

ai.vega_lite(
    spec={
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": "container",
        "mark": "line",
        "encoding": {
            "x": {"field": "month", "type": "nominal"},
            "y": {"field": "revenue", "type": "quantitative"},
        },
    },
    data_resource="sales",
    resources=runtime_resources,
)
```

## Chat Kit Example

The Chat Kit keeps a structured timeline in `st.session_state` and replays the full conversation on rerun.

```python
import os
import streamlit as st
from openai import OpenAI
import streamlit_ai_elements as ai

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

if "chat_session" not in st.session_state:
    st.session_state.chat_session = ai.create_chat_session()

ai.render_chat_session(st.session_state.chat_session)

if prompt := st.chat_input("Ask for a chart or diagram"):
    st.session_state.chat_session = ai.append_user_message(
        st.session_state.chat_session,
        prompt,
    )

    config = ai.ChatBackendConfig(
        model="gpt-5.4",
        backend="responses",
        reasoning_effort="medium",
        reasoning_summary="auto",
    )

    ai.chat_stream(
        ai.stream_assistant_turn(
            client,
            state=st.session_state.chat_session,
            config=config,
        ),
        state=st.session_state.chat_session,
    )
```

## How the AI Tools Work

When used with the Chat Kit, the assistant can choose from three rendering modes:

- `js_raw`
- `sandbox`
- `prebuilt_component`

`prebuilt_component` currently supports:

- `component="vega_lite"`
- `component="excalidraw"`

For Vega-Lite tool calls:

- `spec` must be a non-empty object that follows Vega-Lite syntax
- use inline `data.values` or provide `data_resource` for runtime data

For Excalidraw tool calls:

- provide structured `shapes`
- optionally provide `connectors`, `camera`, and `zoom_to_fit`

## Running the Demo

```bash
streamlit run demo.py
```

## Package Layout

- `streamlit_ai_elements/__init__.py`: public renderer APIs
- `streamlit_ai_elements/runtime_resources.py`: runtime resource registry
- `streamlit_ai_elements/chat/`: Chat Kit runtime, adapters, event model, and UI helpers
- `demo.py`: example streaming chat app

## License

MIT
