import vegaEmbed from "vega-embed";
import type { EmbedOptions, Result, VisualizationSpec } from "vega-embed";

import {
  cleanupRoot,
  getRendererRoot,
  hash,
  renderError,
  whenReady,
} from "@ai-elements/shared";
import type { RendererCleanup, RendererComponent } from "@ai-elements/shared";

interface VegaLiteRendererData {
  spec?: string | VisualizationSpec;
  opts?: EmbedOptions;
  containerHeight?: number | string;
}

type ResizableVisualizationSpec = VisualizationSpec & {
  width?: number | string;
  height?: number | string;
};

const ERROR_STYLE = "color:#ff6b6b;padding:12px;white-space:pre-wrap";

/** Resolve "container" dimensions to actual pixels before vegaEmbed sees them. */
function resolveContainerSize(
  spec: ResizableVisualizationSpec,
  element: HTMLElement,
): ResizableVisualizationSpec {
  const resolved = { ...spec };
  const { width, height } = measureElement(element);

  if (resolved.width === "container" && width > 0) {
    resolved.width = width - 2;
  }

  if (resolved.height === "container" && height > 0) {
    resolved.height = height;
  }

  return resolved;
}

function applyContainerHeight(
  element: HTMLElement,
  containerHeight: VegaLiteRendererData["containerHeight"],
): void {
  const normalizedHeight = normalizeContainerHeight(containerHeight);
  if (!normalizedHeight) {
    return;
  }

  element.style.height = normalizedHeight;
  element.style.minHeight = normalizedHeight;
}

function parseSpec(spec: VegaLiteRendererData["spec"]): ResizableVisualizationSpec {
  if (typeof spec === "string") {
    return JSON.parse(spec) as ResizableVisualizationSpec;
  }
  return spec as ResizableVisualizationSpec;
}

function normalizeContainerHeight(height: VegaLiteRendererData["containerHeight"]): string | null {
  if (typeof height === "number") {
    return `${height}px`;
  }

  if (typeof height !== "string") {
    return null;
  }

  const value = height.trim();
  if (!value || value === "auto") {
    return null;
  }

  return /^\d+$/.test(value) ? `${value}px` : value;
}

function measureElement(element: HTMLElement): { width: number; height: number } {
  const rect = element.getBoundingClientRect();
  return {
    width: Math.round(rect.width || element.clientWidth),
    height: Math.round(rect.height || element.clientHeight),
  };
}

async function waitForStableLayout(element: HTMLElement, attempts = 12): Promise<void> {
  let stableFrames = 0;

  for (let i = 0; i < attempts; i += 1) {
    const { width } = measureElement(element);
    if (width > 0) {
      stableFrames += 1;
      if (stableFrames >= 2) {
        return;
      }
    } else {
      stableFrames = 0;
    }

    await new Promise<void>((resolve) => {
      window.requestAnimationFrame(() => resolve());
    });
  }
}

export default function renderVegaLite(
  component: RendererComponent<VegaLiteRendererData>,
): RendererCleanup | undefined {
  const { data, parentElement } = component;
  if (!data?.spec) {
    return undefined;
  }

  const root = getRendererRoot(parentElement);
  if (!root) {
    return undefined;
  }

  const dataHash = hash(JSON.stringify(data.spec));
  if (root.dataset.h === dataHash) {
    return root._cleanup;
  }

  cleanupRoot(root);
  root.dataset.h = dataHash;
  root.innerHTML = "";
  applyContainerHeight(root, data.containerHeight);

  const gen = (root._gen ?? 0) + 1;
  root._gen = gen;
  const isAlive = (): boolean => root._gen === gen;

  void whenReady(root)
    .then(async () => {
      await waitForStableLayout(root);

      if (!isAlive()) {
        return;
      }

      const spec = parseSpec(data.spec);
      const resolved = resolveContainerSize(spec, root);
      root.dataset.resolvedWidth = String(resolved.width ?? "");
      root.dataset.resolvedHeight = String(resolved.height ?? "");
      const options: EmbedOptions = {
        actions: false,
        renderer: "svg",
        ...(data.opts ?? {}),
      };

      const result = await vegaEmbed(root, resolved, options);
      if (!isAlive()) {
        result.finalize();
        return;
      }

      attachResizeHandler(root, result, spec, gen);
    })
    .catch((error) => {
      if (!isAlive()) {
        return;
      }

      renderError(root, error, ERROR_STYLE);
      root._cleanup = () => {
        root._gen = -1;
      };
    });

  root._cleanup = () => {
    root._gen = -1;
  };

  return root._cleanup;
}

function attachResizeHandler(
  root: HTMLElement & { _cleanup?: RendererCleanup; _gen?: number },
  result: Result,
  spec: ResizableVisualizationSpec,
  gen: number,
): void {
  let resizeTimer: number | undefined;
  const responsiveWidth = spec.width === "container";
  const responsiveHeight = spec.height === "container";

  const syncViewSize = (): void => {
    const { width, height } = measureElement(root);

    if (responsiveWidth && width > 0) {
      result.view.width(width - 2);
    }

    if (responsiveHeight && height > 0) {
      result.view.height(height);
    }

    if ((responsiveWidth && width > 0) || (responsiveHeight && height > 0)) {
      void result.view.resize().runAsync();
    }
  };

  const resizeObserver = new ResizeObserver(() => {
    if (root._gen !== gen) {
      resizeObserver.disconnect();
      return;
    }

    if (resizeTimer !== undefined) {
      window.clearTimeout(resizeTimer);
    }

    resizeTimer = window.setTimeout(() => {
      if (root._gen !== gen) {
        return;
      }
      syncViewSize();
    }, 100);
  });

  resizeObserver.observe(root);
  syncViewSize();
  window.requestAnimationFrame(syncViewSize);
  window.setTimeout(syncViewSize, 120);

  root._cleanup = () => {
    root._gen = -1;
    if (resizeTimer !== undefined) {
      window.clearTimeout(resizeTimer);
    }
    resizeObserver.disconnect();
    result.finalize();
  };
}
