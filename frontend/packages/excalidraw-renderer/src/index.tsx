import React, { useEffect, useMemo, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { Excalidraw, FONT_FAMILY, convertToExcalidrawElements } from "@excalidraw/excalidraw";

import {
  cleanupRoot,
  getRendererRoot,
  hash,
  renderError,
} from "@ai-elements/shared";
import type { RendererCleanup, RendererComponent, RendererRoot } from "@ai-elements/shared";

type ShapeKind =
  | "rectangle"
  | "rounded-rectangle"
  | "ellipse"
  | "diamond"
  | "triangle"
  | "hexagon"
  | "text";

interface ExcalidrawAnchor {
  x?: number;
  y?: number;
}

interface ExcalidrawShapeSpec {
  id?: string;
  type: ShapeKind;
  x: number;
  y: number;
  width?: number;
  height?: number;
  text?: string;
  color?: string;
  fill?: "none" | "semi" | "solid" | "pattern";
  dash?: "draw" | "solid" | "dashed" | "dotted";
  size?: "s" | "m" | "l" | "xl";
  font?: "draw" | "sans" | "serif" | "mono";
  align?: "start" | "middle" | "end";
  verticalAlign?: "start" | "middle" | "end";
}

interface ExcalidrawConnectorSpec {
  id?: string;
  from: string;
  to: string;
  text?: string;
  color?: string;
  dash?: "draw" | "solid" | "dashed" | "dotted";
  bend?: number;
  fromAnchor?: ExcalidrawAnchor;
  toAnchor?: ExcalidrawAnchor;
  arrowheadStart?: "none" | "arrow" | "triangle" | "square" | "dot" | "pipe" | "diamond" | "inverted" | "bar";
  arrowheadEnd?: "none" | "arrow" | "triangle" | "square" | "dot" | "pipe" | "diamond" | "inverted" | "bar";
}

interface ExcalidrawRendererData {
  readonly?: boolean;
  hideUi?: boolean;
  zoomToFit?: boolean;
  camera?: {
    x?: number;
    y?: number;
    z?: number;
  };
  shapes?: ExcalidrawShapeSpec[];
  connectors?: ExcalidrawConnectorSpec[];
}

interface ExcalidrawSceneState {
  elements: unknown[];
  appState: Record<string, unknown>;
}

interface ExcalidrawRendererRoot extends RendererRoot {
  _reactRoot?: Root;
}

const ERROR_STYLE =
  "color:#ff6b6b;background:#2d1b1b;padding:12px;border-radius:6px;white-space:pre-wrap";
const COLOR_MAP: Record<string, string> = {
  black: "#1e1e1e",
  gray: "#495057",
  slate: "#475569",
  blue: "#4c6ef5",
  green: "#12b886",
  red: "#e03131",
  orange: "#f08c00",
  yellow: "#fab005",
  violet: "#ae3ec9",
  pink: "#d6336c",
  cyan: "#1098ad",
  brown: "#8d6e63",
};

function shapeId(id: string | undefined, index: number): string {
  return id ?? `shape-${index + 1}`;
}

function shapeWidth(shape: ExcalidrawShapeSpec): number {
  return shape.width ?? (shape.type === "text" ? 0 : 180);
}

function shapeHeight(shape: ExcalidrawShapeSpec): number {
  return shape.height ?? (shape.type === "text" ? 0 : 96);
}

function mapColor(value: string | undefined, fallback: string): string {
  if (!value) {
    return fallback;
  }

  return COLOR_MAP[value.toLowerCase()] ?? value;
}

function mapFont(font: ExcalidrawShapeSpec["font"]): number {
  switch (font) {
    case "draw":
      return FONT_FAMILY.Virgil;
    case "mono":
      return FONT_FAMILY.Cascadia;
    case "serif":
      return FONT_FAMILY.Nunito;
    case "sans":
    default:
      return FONT_FAMILY.Helvetica;
  }
}

function mapTextAlign(value: ExcalidrawShapeSpec["align"]): string {
  switch (value) {
    case "start":
      return "left";
    case "end":
      return "right";
    case "middle":
    default:
      return "center";
  }
}

function mapVerticalAlign(value: ExcalidrawShapeSpec["verticalAlign"]): string {
  switch (value) {
    case "start":
      return "top";
    case "end":
      return "bottom";
    case "middle":
    default:
      return "middle";
  }
}

function mapFontSize(size: ExcalidrawShapeSpec["size"]): number {
  switch (size) {
    case "s":
      return 16;
    case "l":
      return 24;
    case "xl":
      return 28;
    case "m":
    default:
      return 20;
  }
}

function mapFillStyle(fill: ExcalidrawShapeSpec["fill"]): string {
  switch (fill) {
    case "solid":
      return "solid";
    case "pattern":
      return "cross-hatch";
    case "none":
      return "hachure";
    case "semi":
    default:
      return "hachure";
  }
}

function mapBackgroundColor(shape: ExcalidrawShapeSpec): string {
  if (shape.fill === "none") {
    return "transparent";
  }
  return mapColor(shape.color, "#dbe4ff");
}

function mapStrokeStyle(dash: ExcalidrawShapeSpec["dash"] | ExcalidrawConnectorSpec["dash"]): string {
  switch (dash) {
    case "dashed":
      return "dashed";
    case "dotted":
      return "dotted";
    case "draw":
    case "solid":
    default:
      return "solid";
  }
}

function mapArrowhead(
  value: ExcalidrawConnectorSpec["arrowheadStart"] | ExcalidrawConnectorSpec["arrowheadEnd"],
): string | null {
  switch (value) {
    case "none":
      return null;
    case "pipe":
    case "square":
    case "bar":
      return "bar";
    case "triangle":
      return "triangle";
    case "diamond":
      return "diamond";
    case "dot":
      return "dot";
    case "inverted":
      return "triangle_outline";
    case "arrow":
    default:
      return "arrow";
  }
}

function shapeType(kind: ShapeKind): "rectangle" | "ellipse" | "diamond" | "text" {
  switch (kind) {
    case "ellipse":
      return "ellipse";
    case "diamond":
      return "diamond";
    case "text":
      return "text";
    case "triangle":
    case "hexagon":
    case "rounded-rectangle":
    case "rectangle":
    default:
      return "rectangle";
  }
}

function anchorPoint(shape: ExcalidrawShapeSpec, anchor?: ExcalidrawAnchor): { x: number; y: number } {
  const width = shapeWidth(shape);
  const height = shapeHeight(shape);
  const ratioX = typeof anchor?.x === "number" ? anchor.x : 0.5;
  const ratioY = typeof anchor?.y === "number" ? anchor.y : 0.5;

  return {
    x: shape.x + width * ratioX,
    y: shape.y + height * ratioY,
  };
}

function buildScene(data: ExcalidrawRendererData): ExcalidrawSceneState {
  const shapes = data.shapes ?? [];
  const connectors = data.connectors ?? [];
  const shapeSpecs = new Map<string, ExcalidrawShapeSpec>();

  const skeleton: any[] = shapes.map((shape, index) => {
    const id = shapeId(shape.id, index);
    shapeSpecs.set(id, shape);

    if (shape.type === "text") {
      return {
        id,
        type: "text",
        text: shape.text ?? "",
        x: shape.x,
        y: shape.y,
        strokeColor: mapColor(shape.color, "#1e1e1e"),
        fontFamily: mapFont(shape.font),
        fontSize: mapFontSize(shape.size),
        textAlign: mapTextAlign(shape.align),
        verticalAlign: mapVerticalAlign(shape.verticalAlign),
      };
    }

    return {
      id,
      type: shapeType(shape.type),
      x: shape.x,
      y: shape.y,
      width: shapeWidth(shape),
      height: shapeHeight(shape),
      strokeColor: mapColor(shape.color, "#4c6ef5"),
      backgroundColor: mapBackgroundColor(shape),
      strokeStyle: mapStrokeStyle(shape.dash),
      fillStyle: mapFillStyle(shape.fill),
      roundness: shape.type === "rounded-rectangle" ? { type: 3 } : null,
      label: shape.text
        ? {
            text: shape.text,
            fontSize: mapFontSize(shape.size),
            fontFamily: mapFont(shape.font),
            textAlign: mapTextAlign(shape.align),
            verticalAlign: mapVerticalAlign(shape.verticalAlign),
          }
        : undefined,
    };
  });

  for (const connector of connectors) {
    const fromShape = shapeSpecs.get(connector.from);
    const toShape = shapeSpecs.get(connector.to);
    if (!fromShape || !toShape) {
      continue;
    }

    const startPoint = anchorPoint(fromShape, connector.fromAnchor);
    const endPoint = anchorPoint(toShape, connector.toAnchor);
    const deltaX = endPoint.x - startPoint.x;
    const deltaY = endPoint.y - startPoint.y;

    skeleton.push({
      id: connector.id ?? `connector-${connector.from}-${connector.to}`,
      type: "arrow",
      x: startPoint.x,
      y: startPoint.y,
      points:
        typeof connector.bend === "number" && connector.bend !== 0
          ? [
              [0, 0],
              [deltaX / 2, connector.bend],
              [deltaX, deltaY],
            ]
          : [
              [0, 0],
              [deltaX, deltaY],
            ],
      strokeColor: mapColor(connector.color, "#1e1e1e"),
      strokeStyle: mapStrokeStyle(connector.dash),
      startArrowhead: mapArrowhead(connector.arrowheadStart),
      endArrowhead: mapArrowhead(connector.arrowheadEnd ?? "arrow"),
      label: connector.text
        ? {
            text: connector.text,
            fontSize: 16,
            fontFamily: FONT_FAMILY.Helvetica,
            textAlign: "center",
            verticalAlign: "middle",
          }
        : undefined,
    });
  }

  const zoom = Number.isFinite(data.camera?.z) ? Math.max(0.1, Number(data.camera?.z)) : 1;
  const appState: Record<string, unknown> = {
    viewModeEnabled: Boolean(data.readonly),
    gridSize: null,
    viewBackgroundColor: "#ffffff",
    currentItemStrokeColor: "#4c6ef5",
    currentItemBackgroundColor: "#dbe4ff",
    currentItemFillStyle: "hachure",
    currentItemStrokeStyle: "solid",
    currentItemFontFamily: FONT_FAMILY.Helvetica,
    currentItemRoundness: "round",
    zoom: { value: zoom },
  };

  if (typeof data.camera?.x === "number") {
    appState.scrollX = -data.camera.x;
  }
  if (typeof data.camera?.y === "number") {
    appState.scrollY = -data.camera.y;
  }

  return {
    elements: convertToExcalidrawElements(skeleton as never, {
      regenerateIds: false,
    }) as unknown[],
    appState,
  };
}

function DiagramEditor({ data }: { data: ExcalidrawRendererData }): React.JSX.Element {
  const [api, setApi] = useState<any>(null);
  const initialData = useMemo(() => buildScene(data), [data]);

  useEffect(() => {
    if (!api || data.zoomToFit === false) {
      return;
    }

    const frame = window.requestAnimationFrame(() => {
      const elements = api.getSceneElements();
      if (elements.length > 0) {
        api.scrollToContent(elements, {
          fitToViewport: true,
          viewportZoomFactor: 0.9,
          animate: false,
        });
      }
    });

    return () => window.cancelAnimationFrame(frame);
  }, [api, data.zoomToFit]);

  return (
    <div className="ai-elements-excalidraw-mount">
      <Excalidraw
        excalidrawAPI={setApi}
        initialData={initialData as never}
        viewModeEnabled={Boolean(data.readonly)}
        zenModeEnabled={Boolean(data.hideUi)}
        handleKeyboardGlobally={false}
        autoFocus={false}
      />
    </div>
  );
}

export default function renderExcalidraw(
  component: RendererComponent<ExcalidrawRendererData>,
): RendererCleanup | undefined {
  const { data, parentElement } = component;
  if (!data) {
    return undefined;
  }

  const root = getRendererRoot(parentElement) as ExcalidrawRendererRoot | null;
  if (!root) {
    return undefined;
  }

  const dataHash = hash(JSON.stringify(data));
  if (root.dataset.h === dataHash) {
    return root._cleanup;
  }

  cleanupRoot(root);
  root.dataset.h = dataHash;
  root.classList.add("ai-elements-excalidraw-root");
  root.classList.toggle("ai-elements-excalidraw-hide-ui", Boolean(data.hideUi));
  root.innerHTML = "";
  const resolvedHeight = Math.max(420, Math.round(root.clientHeight || root.getBoundingClientRect().height || 560));
  root.style.height = `${resolvedHeight}px`;

  const mount = document.createElement("div");
  mount.className = "ai-elements-excalidraw-mount";
  mount.style.height = `${resolvedHeight}px`;
  root.appendChild(mount);

  try {
    const reactRoot = createRoot(mount);
    root._reactRoot = reactRoot;
    reactRoot.render(<DiagramEditor data={data} />);
  } catch (error) {
    renderError(root, error, ERROR_STYLE);
  }

  root._cleanup = () => {
    root._reactRoot?.unmount();
    delete root._reactRoot;
    root.style.height = "";
    root.innerHTML = "";
  };

  return root._cleanup;
}
