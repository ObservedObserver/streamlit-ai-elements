/**
 * Shared utilities for Streamlit AI Elements renderers.
 */

/** Fast string hash → short string key for data-change detection. */
export function hash(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h) + s.charCodeAt(i);
    h |= 0;
  }
  return String(h);
}

/**
 * Returns wrapped requestAnimationFrame / setInterval / setTimeout that
 * auto-cancel when root._gen no longer matches `gen`.
 */
export function safeTimers(root, gen) {
  const alive = () => root._gen === gen;
  const _raf = window.requestAnimationFrame.bind(window);
  return {
    requestAnimationFrame: (fn) => _raf((t) => alive() && fn(t)),
    setInterval: (fn, ms, ...a) => {
      const id = window.setInterval(
        (...x) => {
          if (!alive()) { clearInterval(id); return; }
          fn(...x);
        },
        ms,
        ...a,
      );
      return id;
    },
    setTimeout: (fn, ms, ...a) =>
      window.setTimeout((...x) => alive() && fn(...x), ms, ...a),
  };
}

/** Resolves when `el.clientWidth > 0` (element has been laid out). */
export function whenReady(el) {
  return new Promise((resolve) => {
    if (el.clientWidth > 0) return resolve();
    const ro = new ResizeObserver((entries) => {
      if (entries[0].contentRect.width > 0) {
        ro.disconnect();
        resolve();
      }
    });
    ro.observe(el);
  });
}
