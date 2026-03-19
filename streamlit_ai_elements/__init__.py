"""
streamlit_ai_elements — AI-powered rendering components for Streamlit.

Rendering modes built on Streamlit Component V2:
  1. js_raw()    – render arbitrary HTML / CSS / JS
  2. vega_lite() – render a Vega-Lite specification
  3. sandbox()   – interactive dashboards with pre-injected libraries
  4. excalidraw() – structured diagram editor powered by Excalidraw
"""

import streamlit as st
import json as _json
from pathlib import Path as _Path

from .runtime_resources import (
    RuntimeResource,
    build_javascript_runtime as _build_javascript_runtime,
    inject_vega_lite_resource_data as _inject_vega_lite_resource_data,
    resolve_frontend_resources,
    resource,
    resources,
)

__version__ = "0.1.0"
__all__ = [
    "RuntimeResource",
    "resource",
    "resources",
    "resolve_frontend_resources",
    "js_raw",
    "vega_lite",
    "sandbox",
    "excalidraw",
]

# ---------------------------------------------------------------------------
# Asset loading — prefer local bundles, fall back to CDN-based inline JS
# ---------------------------------------------------------------------------
_ASSETS_DIR = _Path(__file__).parent / "assets"


def _load_asset(name: str) -> str | None:
    """Read a bundled JS file from assets/ if it exists."""
    path = _ASSETS_DIR / name
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return None


# ---------------------------------------------------------------------------
# Component registry – each renderer is created once and reused across reruns
# ---------------------------------------------------------------------------
_registry: dict = {}


def _ensure(name: str, **kwargs):
    if name not in _registry:
        _registry[name] = st.components.v2.component(name=name, **kwargs)
    return _registry[name]


def _normalize_excalidraw_shapes(shapes: list[dict]) -> list[dict]:
    normalized = []
    for shape in shapes:
        item = dict(shape)
        if "vertical_align" in item and "verticalAlign" not in item:
            item["verticalAlign"] = item.pop("vertical_align")
        normalized.append(item)
    return normalized


def _normalize_excalidraw_connectors(connectors: list[dict]) -> list[dict]:
    normalized = []
    for connector in connectors:
        item = dict(connector)
        if "from_anchor" in item and "fromAnchor" not in item:
            item["fromAnchor"] = item.pop("from_anchor")
        if "to_anchor" in item and "toAnchor" not in item:
            item["toAnchor"] = item.pop("to_anchor")
        if "start_arrowhead" in item and "arrowheadStart" not in item:
            item["arrowheadStart"] = item.pop("start_arrowhead")
        if "startArrowhead" in item and "arrowheadStart" not in item:
            item["arrowheadStart"] = item.pop("startArrowhead")
        if "end_arrowhead" in item and "arrowheadEnd" not in item:
            item["arrowheadEnd"] = item.pop("end_arrowhead")
        if "endArrowhead" in item and "arrowheadEnd" not in item:
            item["arrowheadEnd"] = item.pop("endArrowhead")
        normalized.append(item)
    return normalized


# ===========================================================================
# Shared JS helpers (used only in CDN fallback paths)
# ===========================================================================
_JS_HASH = """
function _hash(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h) + s.charCodeAt(i);
    h |= 0;
  }
  return String(h);
}
"""

_JS_LOAD_SCRIPT = """
function _loadScript(url) {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector('script[src="' + url + '"]');
    if (existing) {
      if (existing.dataset.loaded === '1') return resolve();
      existing.addEventListener('load', resolve);
      existing.addEventListener('error', reject);
      return;
    }
    const s = document.createElement('script');
    s.src = url;
    s.dataset.loaded = '0';
    s.onload = () => { s.dataset.loaded = '1'; resolve(); };
    s.onerror = reject;
    document.head.appendChild(s);
  });
}
"""

_JS_SAFE_TIMERS = """
function _safeTimers(root, gen) {
  const alive = () => root._gen === gen;
  const _raf = window.requestAnimationFrame.bind(window);
  return {
    requestAnimationFrame: (fn) => _raf((t) => alive() && fn(t)),
    setInterval: (fn, ms, ...a) => {
      const id = window.setInterval((...x) => {
        if (!alive()) { clearInterval(id); return; }
        fn(...x);
      }, ms, ...a);
      return id;
    },
    setTimeout: (fn, ms, ...a) =>
      window.setTimeout((...x) => alive() && fn(...x), ms, ...a),
  };
}
"""


# ===========================================================================
# Mode 1 — JS Raw  (no vendor libs — always inline)
# ===========================================================================
_RAW_JS = (
    _JS_HASH
    + _JS_SAFE_TIMERS
    + r"""
export default function (component) {
  const { data, parentElement } = component;
  if (!data) return;

  const root = parentElement.querySelector('#_r');
  if (!root) return;

  // Skip re-render when data hasn't changed (preserves animations)
  const dh = _hash(JSON.stringify(data));
  if (root.dataset.h === dh) return root._cleanup;
  root.dataset.h = dh;

  // Bump generation → old safe-timers auto-cancel
  const gen = (root._gen = (root._gen || 0) + 1);
  const timers = _safeTimers(root, gen);

  // Clear previous content
  root.innerHTML = '';

  // Inject CSS + HTML
  if (data.css) root.innerHTML += '<style>' + data.css + '</style>';
  if (data.html) root.insertAdjacentHTML('beforeend', data.html);

  // Execute user JS
  if (data.js) {
    try {
      const fn = new Function(
        'container',
        'resources', 'data', 'resource', 'rows', 'context',
        'requestAnimationFrame', 'setInterval', 'setTimeout',
        data.js,
      );
      fn(
        root,
        data.resources || {},
        data.data ?? {},
        data.resource ?? null,
        data.rows || [],
        data.context || {},
        timers.requestAnimationFrame,
        timers.setInterval,
        timers.setTimeout,
      );
    } catch (e) {
      root.insertAdjacentHTML(
        'beforeend',
        '<pre style="color:#ff6b6b;background:#2d1b1b;padding:12px;border-radius:6px;margin-top:8px;white-space:pre-wrap">'
          + e.message + '</pre>',
      );
    }
  }

  root._cleanup = () => { root._gen = -1; };
  return root._cleanup;
}
"""
)


def js_raw(
    html: str = "",
    css: str = "",
    js: str = "",
    height: int | str = "content",
    resource_names: list[str] | None = None,
    resources: dict[str, RuntimeResource] | None = None,
    key: str | None = None,
):
    """
    Render raw HTML / CSS / JS code.

    The JavaScript code receives:

    - ``container`` — root DOM element
    - ``resources`` — requested runtime resources materialized for frontend use
    - ``data`` — if exactly one dataframe resource is requested, that dataframe payload; otherwise a context/resource object
    - ``resource`` — the single requested resource payload when there is exactly one
    - ``rows`` — convenience alias for ``data.rows`` when the primary resource is a dataframe
    - ``context`` — explicit Python-side context payload
    - ``requestAnimationFrame`` / ``setInterval`` / ``setTimeout`` — safe timers
    """
    runtime_resources = resolve_frontend_resources(resources, resource_names)
    runtime = _build_javascript_runtime(runtime_resources)
    renderer = _ensure("ai_js_raw", html='<div id="_r"></div>', js=_RAW_JS)
    return renderer(
        data={"html": html, "css": css, "js": js, **runtime},
        height=height,
        key=key,
    )


# ===========================================================================
# Mode 2 — Pre-built Component: Vega-Lite
# ===========================================================================

# CDN fallback (used only when assets/vegalite-renderer.js doesn't exist)
_VL_CDN_JS = (
    _JS_HASH
    + _JS_LOAD_SCRIPT
    + r"""
function _whenReady(el) {
  return new Promise((resolve) => {
    const rect = el.getBoundingClientRect();
    if (rect.width > 0 || el.clientWidth > 0) return resolve();
    const ro = new ResizeObserver((entries) => {
      if (entries[0].contentRect.width > 0) { ro.disconnect(); resolve(); }
    });
    ro.observe(el);
  });
}

function _measureElement(el) {
  const rect = el.getBoundingClientRect();
  return {
    width: Math.round(rect.width || el.clientWidth),
    height: Math.round(rect.height || el.clientHeight),
  };
}

function _resolveContainerSize(spec, el) {
  const resolved = Object.assign({}, spec);
  const { width: w, height: h } = _measureElement(el);
  if (resolved.width === 'container' && w > 0) resolved.width = w - 2;
  if (resolved.height === 'container' && h > 0) resolved.height = h;
  return resolved;
}

function _normalizeContainerHeight(height) {
  if (typeof height === 'number') return height + 'px';
  if (typeof height !== 'string') return null;
  const value = height.trim();
  if (!value || value === 'auto') return null;
  return /^\d+$/.test(value) ? value + 'px' : value;
}

function _applyContainerHeight(el, height) {
  const normalized = _normalizeContainerHeight(height);
  if (!normalized) return;
  el.style.height = normalized;
  el.style.minHeight = normalized;
}

export default function (component) {
  const { data, parentElement } = component;
  if (!data || !data.spec) return;

  const root = parentElement.querySelector('#_r');
  if (!root) return;

  const dh = _hash(JSON.stringify(data.spec));
  if (root.dataset.h === dh) return;
  root.dataset.h = dh;

  root.innerHTML = '<div style="padding:1em;color:#888">Loading chart…</div>';

  (async () => {
    try {
      await _loadScript('https://cdn.jsdelivr.net/npm/vega@5/build/vega.min.js');
      await _loadScript('https://cdn.jsdelivr.net/npm/vega-lite@5/build/vega-lite.min.js');
      await _loadScript('https://cdn.jsdelivr.net/npm/vega-embed@6/build/vega-embed.min.js');

      root.innerHTML = '';
      _applyContainerHeight(root, data.containerHeight);
      await _whenReady(root);
      const spec = typeof data.spec === 'string' ? JSON.parse(data.spec) : data.spec;
      const resolved = _resolveContainerSize(spec, root);
      const result = await window.vegaEmbed(root, resolved, {
        actions: false,
        renderer: 'svg',
        ...(data.opts || {}),
      });
      const responsiveWidth = spec.width === 'container';
      const responsiveHeight = spec.height === 'container';
      const syncViewSize = () => {
        const { width: w, height: h } = _measureElement(root);
        if (responsiveWidth && w > 0) result.view.width(w - 2);
        if (responsiveHeight && h > 0) result.view.height(h);
        if ((responsiveWidth && w > 0) || (responsiveHeight && h > 0)) {
          result.view.resize().runAsync();
        }
      };
      let t;
      new ResizeObserver(() => {
        clearTimeout(t);
        t = setTimeout(() => {
          syncViewSize();
        }, 100);
      }).observe(root);
      syncViewSize();
      requestAnimationFrame(syncViewSize);
      setTimeout(syncViewSize, 120);
    } catch (e) {
      root.innerHTML =
        '<pre style="color:#ff6b6b;padding:12px;white-space:pre-wrap">' + e.message + '</pre>';
    }
  })();
}
"""
)

_VL_JS = _load_asset("vegalite-renderer.js") or _VL_CDN_JS


def vega_lite(
    spec: dict | str,
    height: int | str = 400,
    options: dict | None = None,
    resource_names: list[str] | None = None,
    data_resource: str | None = None,
    resources: dict[str, RuntimeResource] | None = None,
    key: str | None = None,
):
    """
    Render a Vega-Lite chart from a specification dict (or JSON string).
    """
    if isinstance(spec, str):
        spec = _json.loads(spec)

    selected_resource_names = [data_resource] if data_resource else resource_names
    resolved_resources = resolve_frontend_resources(resources, selected_resource_names)
    spec = _inject_vega_lite_resource_data(spec, resolved_resources, data_resource=data_resource)

    # Prefer Streamlit's built-in Vega-Lite renderer for standard specs.
    # It is more reliable inside dynamic containers such as chat messages.
    if not options:
        return st.vega_lite_chart(
            spec=spec,
            height=height,
            use_container_width=True,
            theme=None,
            key=key,
        )

    renderer = _ensure(
        "ai_vega_lite",
        html='<div id="_r" style="display:block;width:100%;height:100%;min-height:100%"></div>',
        js=_VL_JS,
        isolate_styles=False,
    )
    return renderer(
        data={"spec": spec, "opts": options, "containerHeight": height},
        height=height,
        key=key,
    )


# ===========================================================================
# Mode 3 — Sandbox (interactive dashboards)
# ===========================================================================
_SB_HTML = (
    '<style>'
    '#_r { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; '
    'color: var(--st-text-color, #262730); }'
    '</style>'
    '<div id="_r"></div>'
)

# CDN fallback (used only when assets/sandbox-renderer.js doesn't exist)
_SB_CDN_JS = (
    _JS_HASH
    + _JS_LOAD_SCRIPT
    + _JS_SAFE_TIMERS
    + r"""
const CDN = {
  echarts: 'https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js',
  d3:      'https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js',
  three:   'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js',
};

export default function (component) {
  const { data, parentElement, setStateValue, setTriggerValue } = component;
  if (!data || !data.js) return;

  const root = parentElement.querySelector('#_r');
  if (!root) return;

  const dh = _hash(JSON.stringify(data));
  if (root.dataset.h === dh) return root._cleanup;
  root.dataset.h = dh;

  const gen = (root._gen = (root._gen || 0) + 1);
  const alive = () => root._gen === gen;
  const timers = _safeTimers(root, gen);

  root.innerHTML = '<div style="padding:1em;color:#888">Loading…</div>';

  (async () => {
    try {
      const libs = data.libraries || ['echarts'];
      for (const lib of libs) {
        if (CDN[lib]) await _loadScript(CDN[lib]);
      }
      if (!alive()) return;

      root.innerHTML = '';

      const ctx = {
        container:             root,
        echarts:               window.echarts,
        d3:                    window.d3,
        THREE:                 window.THREE,
        setStateValue:         setStateValue,
        setTriggerValue:       setTriggerValue,
        data:                  data.data || {},
        resources:             data.resources || {},
        resource:              data.resource || null,
        rows:                  data.rows || [],
        context:               data.context || {},
        requestAnimationFrame: timers.requestAnimationFrame,
        setInterval:           timers.setInterval,
        setTimeout:            timers.setTimeout,
      };

      const names = Object.keys(ctx);
      const vals  = Object.values(ctx);
      new Function(...names, data.js)(...vals);
    } catch (e) {
      root.innerHTML =
        '<pre style="color:#ff6b6b;background:#2d1b1b;padding:12px;border-radius:6px;white-space:pre-wrap">'
        + e.message + '</pre>';
    }
  })();

  root._cleanup = () => { root._gen = -1; };
  return root._cleanup;
}
"""
)

_SB_JS = _load_asset("sandbox-renderer.js") or _SB_CDN_JS


def sandbox(
    js: str,
    height: int | str = "content",
    libraries: list[str] | None = None,
    context: dict | None = None,
    resource_names: list[str] | None = None,
    resources: dict[str, RuntimeResource] | None = None,
    key: str | None = None,
):
    """
    Render an interactive dashboard with pre-injected libraries.

    The JS code receives these named variables:

    - ``container``             — root DOM element
    - ``echarts``               — ECharts library  (if loaded)
    - ``d3``                    — D3.js            (if loaded)
    - ``THREE``                 — Three.js         (if loaded)
    - ``setStateValue(n, v)``   — persist state back to Python
    - ``setTriggerValue(n, v)`` — fire transient events to Python
    - ``resources``             — requested runtime resources materialized for frontend use
    - ``data``                  — if exactly one dataframe resource is requested, that dataframe payload; otherwise a context/resource object
    - ``resource``              — the single requested resource payload when there is exactly one
    - ``rows``                  — convenience alias for ``data.rows`` when the primary resource is a dataframe
    - ``context``               — custom context dict from Python
    - ``requestAnimationFrame`` — auto-cancels on re-render
    - ``setInterval``           — auto-cancels on re-render
    - ``setTimeout``            — auto-cancels on re-render
    """
    runtime_resources = resolve_frontend_resources(resources, resource_names)
    runtime = _build_javascript_runtime(runtime_resources, context=context or {})
    renderer = _ensure(
        "ai_sandbox",
        html=_SB_HTML,
        js=_SB_JS,
    )
    return renderer(
        data={
            "js": js,
            "libraries": libraries or ["echarts"],
            **runtime,
        },
        height=height,
        key=key,
    )


# ===========================================================================
# Mode 4 — Preview Component: Excalidraw diagrams
# ===========================================================================
_TD_HTML = (
    '<style>'
    'html, body { margin:0; padding:0; width:100%; height:100%; overflow:hidden; }'
    'body { position:relative; }'
    '#_r { position:relative; width:100%; height:100%; overflow:hidden; }'
    "</style>"
    '<div id="_r"></div>'
)

_TD_CSS = _load_asset("excalidraw-editor.css") or ""

_TD_FALLBACK_JS = r"""
export default function (component) {
  const { parentElement } = component;
  const root = parentElement.querySelector('#_r');
  if (!root) return;
  root.innerHTML =
    '<pre style="color:#ff6b6b;background:#2d1b1b;padding:12px;border-radius:6px;white-space:pre-wrap">'
    + 'Missing Excalidraw renderer bundle. Run the frontend build to generate streamlit_ai_elements/assets/excalidraw-renderer.js.'
    + '</pre>';
}
"""

_TD_JS = _load_asset("excalidraw-renderer.js") or _TD_FALLBACK_JS


def excalidraw(
    shapes: list[dict],
    connectors: list[dict] | None = None,
    readonly: bool = False,
    hide_ui: bool = False,
    zoom_to_fit: bool = True,
    camera: dict | None = None,
    height: int | str = 560,
    key: str | None = None,
):
    """
    Render a structured diagram in an interactive Excalidraw editor.

    ``shapes`` should contain JSON-friendly node specifications such as
    rectangles, diamonds, ellipses, or text items. ``connectors`` link those
    shapes together with arrows by referencing ``from`` / ``to`` shape ids.
    """
    renderer = _ensure(
        "ai_excalidraw_editor",
        html=_TD_HTML,
        css=_TD_CSS,
        js=_TD_JS,
        isolate_styles=False,
    )
    return renderer(
        data={
            "shapes": _normalize_excalidraw_shapes(shapes),
            "connectors": _normalize_excalidraw_connectors(connectors or []),
            "readonly": readonly,
            "hideUi": hide_ui,
            "zoomToFit": zoom_to_fit,
            "camera": camera or {},
        },
        height=height,
        key=key,
    )
