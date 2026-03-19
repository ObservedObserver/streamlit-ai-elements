import * as echarts from "echarts";
import { hash, safeTimers } from "@ai-elements/shared";

export default function (component) {
  const { data, parentElement, setStateValue, setTriggerValue } = component;
  if (!data || !data.js) return;

  const root = parentElement.querySelector("#_r");
  if (!root) return;

  const dh = hash(data.js + (data.context ? JSON.stringify(data.context) : ""));
  if (root.dataset.h === dh) return root._cleanup;
  root.dataset.h = dh;

  const gen = (root._gen = (root._gen || 0) + 1);
  const timers = safeTimers(root, gen);

  root.innerHTML = "";

  const ctx = {
    container: root,
    echarts: echarts,
    setStateValue: setStateValue,
    setTriggerValue: setTriggerValue,
    data: data.context || {},
    requestAnimationFrame: timers.requestAnimationFrame,
    setInterval: timers.setInterval,
    setTimeout: timers.setTimeout,
  };

  const names = Object.keys(ctx);
  const vals = Object.values(ctx);
  try {
    new Function(...names, data.js)(...vals);
  } catch (e) {
    root.innerHTML =
      '<pre style="color:#ff6b6b;background:#2d1b1b;padding:12px;border-radius:6px;white-space:pre-wrap">' +
      e.message +
      "</pre>";
  }

  root._cleanup = () => {
    root._gen = -1;
  };
  return root._cleanup;
}
