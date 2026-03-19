import * as echarts from "echarts";

import {
  cleanupRoot,
  getRendererRoot,
  hash,
  renderError,
  safeTimers,
} from "@ai-elements/shared";
import type { RendererCleanup, RendererComponent } from "@ai-elements/shared";

interface SandboxRendererData {
  js?: string;
  data?: unknown;
  resource?: unknown;
  rows?: unknown[];
  context?: Record<string, unknown>;
  resources?: Record<string, unknown>;
  libraries?: string[];
}

const ERROR_STYLE =
  "color:#ff6b6b;background:#2d1b1b;padding:12px;border-radius:6px;white-space:pre-wrap";

export default function renderSandbox(
  component: RendererComponent<SandboxRendererData>,
): RendererCleanup | undefined {
  const { data, parentElement, setStateValue, setTriggerValue } = component;
  if (!data?.js) {
    return undefined;
  }

  const root = getRendererRoot(parentElement);
  if (!root) {
    return undefined;
  }

  const dataHash = hash(JSON.stringify(data));
  if (root.dataset.h === dataHash) {
    return root._cleanup;
  }

  cleanupRoot(root);
  root.dataset.h = dataHash;

  const gen = (root._gen ?? 0) + 1;
  root._gen = gen;

  const timers = safeTimers(root, gen);
  root.innerHTML = "";
  const sandboxContext = {
    container: root,
    echarts,
    setStateValue,
    setTriggerValue,
    data: data.data ?? {},
    resources: data.resources ?? {},
    resource: data.resource ?? null,
    rows: data.rows ?? [],
    context: data.context ?? {},
    requestAnimationFrame: timers.requestAnimationFrame,
    setInterval: timers.setInterval,
    setTimeout: timers.setTimeout,
  };

  const names = Object.keys(sandboxContext);
  const values = Object.values(sandboxContext);

  try {
    new Function(...names, data.js)(...values);
  } catch (error) {
    renderError(root, error, ERROR_STYLE);
  }

  root._cleanup = () => {
    root._gen = -1;
  };

  return root._cleanup;
}
