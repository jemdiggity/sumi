import React from "react";
import { createRoot } from "react-dom/client";
import { Agentation } from "agentation";
import { installLiveReload } from "./live-reload.mjs";
const config = window.SUMI_REVIEW;
const container = document.createElement("div");
container.dataset.agentationIgnore = "";
document.body.append(container);
const panel = document.createElement("aside");
panel.dataset.agentationIgnore = "";
document.body.append(panel);
const shadow = panel.attachShadow({ mode: "open" });
shadow.innerHTML = `<style>:host{position:fixed;left:16px;bottom:16px;z-index:99997;font:13px/1.45 system-ui;color:#eee}details{background:#171d2b;border:1px solid #4b5263;border-radius:12px;box-shadow:0 8px 30px #0007;max-width:min(380px,85vw)}summary{cursor:pointer;padding:12px 16px;font-weight:600}section{padding:0 16px 14px;max-height:42vh;overflow:auto}p{margin:8px 0;color:#bfc7d5}button,a{color:#ffcd83}button{background:#283145;border:1px solid #576278;border-radius:6px;padding:6px 10px;cursor:pointer}article{padding:10px 0;border-top:1px solid #3d4556;white-space:pre-wrap}small{display:block;color:#bfc7d5}#latest{display:none;background:#efb35b;color:#151a23;padding:10px 15px;border-radius:8px;margin-bottom:8px;font-weight:650;text-decoration:none}</style><a id="latest" href="/">New revision ready →</a><details open><summary id="summary">Luna pool · connecting</summary><section><p>Click the annotation button at bottom right, select something, and save a comment. Saving sends it to a Luna immediately. Edits create another job.</p><p id="network"></p><p id="live-status"></p><button id="live">Live updates: on</button><div><button id="pause">Pause new work</button> <a href="/api/export" target="_blank">History</a></div><div id="jobs"></div></section></details>`;
const $ = (s) => shadow.querySelector(s);
const key = "sumi-bebop-outbox";
let outbox = JSON.parse(localStorage.getItem(key) || "[]"),
  sending = false,
  last = "";
try {
  const scene = new URLSearchParams(location.search).get("scene");
  if (scene) window.BebopScene?.set?.(JSON.parse(scene));
} catch {}
const live = installLiveReload(window, {
  revision: config.revision,
  pending: () => sending || outbox.length > 0,
  panel: $("details"),
  status: $("#live-status"),
});
const showLive = () => {
  $("#live").textContent = `Live updates: ${live.enabled ? "on" : "off"}`;
};
showLive();
$("#live").onclick = () => {
  live.toggle();
  showLive();
  void poll();
};
function persist() {
  localStorage.setItem(key, JSON.stringify(outbox));
}
function submit(annotation) {
  const fingerprint = JSON.stringify([
    config.revision,
    annotation.id,
    annotation.comment,
    annotation.elementPath,
  ]);
  if (!outbox.some((x) => x.key === fingerprint)) {
    outbox.push({
      key: fingerprint,
      revision: config.revision,
      annotation,
      scene: window.BebopScene?.get?.() || {},
      url: location.href,
    });
    persist();
  }
  void drain();
}
async function drain() {
  if (sending) return;
  sending = true;
  try {
    while (outbox.length) {
      const response = await fetch("/api/comments", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Sumi-Token": config.token,
        },
        body: JSON.stringify(outbox[0]),
        signal: AbortSignal.timeout(5000),
      });
      if (!response.ok) throw Error(await response.text());
      outbox.shift();
      persist();
    }
  } catch (e) {
    $("#network").textContent =
      "Comment saved locally; delivery will retry. " + e.message;
  } finally {
    sending = false;
  }
}
createRoot(container).render(
  <Agentation
    appName="Bebop live review"
    enableKeyboardShortcuts={false}
    copyToClipboard={false}
    onAnnotationAdd={submit}
    onAnnotationUpdate={submit}
    onSubmit={(_, annotations) => annotations.forEach(submit)}
  />,
);
let paused = false;
$("#pause").onclick = async () => {
  try {
    const r = await fetch("/api/pause", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Sumi-Token": config.token,
      },
      body: JSON.stringify({ paused: !paused }),
    });
    if (!r.ok) throw Error("Pause failed");
    await poll();
  } catch (e) {
    $("#network").textContent = e.message;
  }
};
async function poll() {
  try {
    const r = await fetch("/api/state", { signal: AbortSignal.timeout(5000) });
    if (!r.ok) throw Error("Server unavailable");
    const data = await r.json();
    paused = data.paused;
    $("#pause").textContent = paused ? "Resume new work" : "Pause new work";
    $("#summary").textContent =
      `Luna pool · ${data.busy}/${data.workers} busy · ${data.queued} queued${paused ? " · paused" : ""}`;
    $("#network").textContent = outbox.length
      ? `${outbox.length} comment(s) waiting to send`
      : `Viewing revision ${config.revision.slice(0, 8)} · connected`;
    const latest = $("#latest");
    latest.style.display = data.revision !== config.revision ? "block" : "none";
    latest.href = "/r/" + data.revision + "/?live=1";
    live.update(data.revision);
    const fingerprint = JSON.stringify(data.jobs);
    if (last !== fingerprint) {
      last = fingerprint;
      $("#jobs").replaceChildren();
      for (const job of data.jobs.filter(
        (j) => !j.comment.startsWith("Transport test by Codex:"),
      )) {
        const article = document.createElement("article");
        const title = document.createElement("strong");
        title.textContent = job.comment;
        const status = document.createElement("small");
        status.textContent = `${job.status}${job.elapsed_seconds != null ? " · " + Math.round(job.elapsed_seconds) + "s" : ""}${job.error ? " · " + job.error : ""}`;
        article.append(title, status);
        if (job.reply) {
          const reply = document.createElement("p");
          reply.textContent = job.reply;
          article.append(reply);
        }
        if (job.published) {
          const link = document.createElement("a");
          link.href = "/r/" + job.published + "/?live=0";
          link.textContent = "View proposed revision →";
          article.append(link);
        }
        const original = document.createElement("a");
        original.href =
          "/r/" +
          job.revision +
          "/?live=0&scene=" +
          encodeURIComponent(JSON.stringify(job.scene || {}));
        original.textContent = " Original";
        article.append(original);
        $("#jobs").append(article);
      }
    }
  } catch (e) {
    $("#network").textContent = "Disconnected — retrying. " + e.message;
  }
}
async function tick() {
  await drain();
  await poll();
  setTimeout(tick, 1500);
}
void tick();
