/**
 * Shared utilities for Streamlit AI Elements renderers.
 */

export type RendererCleanup = () => void;
export type RendererCallback<TArgs extends unknown[] = []> = (...args: TArgs) => void;

export interface RendererRoot extends HTMLElement {
  _cleanup?: RendererCleanup;
  _gen?: number;
}

export interface RendererComponent<TData> {
  data?: TData | null;
  parentElement: ParentNode;
  setStateValue: (...args: unknown[]) => void;
  setTriggerValue: (...args: unknown[]) => void;
}

export interface SafeTimers {
  requestAnimationFrame: (callback: RendererCallback<[number]>) => number;
  setInterval: (
    callback: RendererCallback<unknown[]>,
    delay?: number,
    ...args: unknown[]
  ) => number;
  setTimeout: (
    callback: RendererCallback<unknown[]>,
    delay?: number,
    ...args: unknown[]
  ) => number;
}

/** Fast string hash -> short string key for data-change detection. */
export function hash(value: string): string {
  let h = 0;
  for (let i = 0; i < value.length; i += 1) {
    h = (h << 5) - h + value.charCodeAt(i);
    h |= 0;
  }
  return String(h);
}

/**
 * Returns wrapped requestAnimationFrame / setInterval / setTimeout that
 * auto-cancel when root._gen no longer matches `gen`.
 */
export function safeTimers(root: RendererRoot, gen: number): SafeTimers {
  const alive = (): boolean => root._gen === gen;
  const raf = window.requestAnimationFrame.bind(window);

  return {
    requestAnimationFrame: (callback) => raf((time) => alive() && callback(time)),
    setInterval: (callback, delay, ...args) => {
      const id = window.setInterval((...intervalArgs: unknown[]) => {
        if (!alive()) {
          window.clearInterval(id);
          return;
        }
        callback(...intervalArgs);
      }, delay, ...args);

      return id;
    },
    setTimeout: (callback, delay, ...args) =>
      window.setTimeout(
        (...timeoutArgs: unknown[]) => alive() && callback(...timeoutArgs),
        delay,
        ...args,
      ),
  };
}

/** Resolves when `el.clientWidth > 0` (element has been laid out). */
export function whenReady(el: HTMLElement): Promise<void> {
  return new Promise((resolve) => {
    if (hasLayout(el)) {
      resolve();
      return;
    }

    const observer = new ResizeObserver((entries) => {
      if (entries[0] && entries[0].contentRect.width > 0) {
        observer.disconnect();
        resolve();
      }
    });

    observer.observe(el);
  });
}

function hasLayout(el: HTMLElement): boolean {
  const rect = el.getBoundingClientRect();
  return rect.width > 0 || el.clientWidth > 0;
}

export function getRendererRoot(parentElement: ParentNode): RendererRoot | null {
  return parentElement.querySelector<RendererRoot>("#_r");
}

export function cleanupRoot(root: RendererRoot): void {
  root._cleanup?.();
  delete root._cleanup;
}

export function formatErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

export function renderError(root: HTMLElement, error: unknown, style: string): void {
  root.innerHTML = `<pre style="${style}">${escapeHtml(formatErrorMessage(error))}</pre>`;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
