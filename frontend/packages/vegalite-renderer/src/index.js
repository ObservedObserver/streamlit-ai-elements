import vegaEmbed from "vega-embed";
import { hash, whenReady } from "@ai-elements/shared";

/** Resolve "container" width to actual pixels before vegaEmbed sees it. */
function resolveContainerSize(spec, el) {
  const resolved = { ...spec };
  const w = el.clientWidth;
  if (resolved.width === "container" && w > 0) {
    resolved.width = w - 2;
  }
  return resolved;
}

export default function (component) {
  const { data, parentElement } = component;
  if (!data || !data.spec) return;

  const root = parentElement.querySelector("#_r");
  if (!root) return;

  const dh = hash(JSON.stringify(data.spec));
  if (root.dataset.h === dh) return;
  root.dataset.h = dh;

  root.innerHTML = "";

  whenReady(root).then(() => {
    const spec =
      typeof data.spec === "string" ? JSON.parse(data.spec) : data.spec;
    const resolved = resolveContainerSize(spec, root);

    vegaEmbed(root, resolved, {
      actions: false,
      renderer: "canvas",
      ...(data.opts || {}),
    })
      .then((result) => {
        let resizeTimer;
        new ResizeObserver(() => {
          clearTimeout(resizeTimer);
          resizeTimer = setTimeout(() => {
            const w = root.clientWidth;
            if (w > 0) {
              result.view.width(w - 2).resize().runAsync();
            }
          }, 100);
        }).observe(root);
      })
      .catch((e) => {
        root.innerHTML =
          '<pre style="color:#ff6b6b;padding:12px;white-space:pre-wrap">' +
          e.message +
          "</pre>";
      });
  });
}
