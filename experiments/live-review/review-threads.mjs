const labels = {
  working: "Working",
  ready: "Ready for review",
  accepted: "Accepted",
  reopened: "Reopened",
  attention: "Needs attention",
};
const palette = {
  working: "#e2a746",
  ready: "#73b8ff",
  accepted: "#70cf96",
  reopened: "#e2a746",
  attention: "#ee8c83",
};
export function installReviewThreads(win, { shadow, config, enqueue }) {
  const doc = win.document,
    cards = new Map();
  const layer = doc.createElement("div");
  layer.dataset.agentationIgnore = "";
  layer.dataset.feedbackToolbar = "";
  doc.body.append(layer);
  const pins = layer.attachShadow({ mode: "open" });
  const rail = doc.createElement("div");
  rail.setAttribute("aria-label", "Review comments without a visible anchor");
  rail.style.cssText =
    "position:fixed;right:6px;top:80px;bottom:60px;display:flex;flex-direction:column;gap:4px;overflow-y:auto;pointer-events:auto";
  pins.innerHTML =
    "<style>:host{position:fixed;inset:0;pointer-events:none;z-index:99996}button{position:fixed;pointer-events:auto;border:2px solid #142034;border-radius:50%;width:29px;height:29px;font:700 10px system-ui;box-shadow:0 2px 8px #0005;cursor:pointer;color:#142034}</style>";
  pins.append(rail);
  const style = doc.createElement("style");
  style.textContent = `.review-thread{margin:10px 0;border-left:3px solid var(--status);box-shadow:none!important}.review-thread summary{padding:9px 12px;font-size:12px}.review-thread .thread-body{padding:0 12px 12px}.thread-badge{display:block;color:var(--status);font-size:11px;margin-top:3px}.thread-log{max-height:240px;overflow:auto}.thread-message{white-space:pre-wrap;border-top:1px solid #3d4556;padding:9px 0}.thread-message strong{font-size:10px;text-transform:uppercase;color:#aeb9cc}.review-thread textarea{box-sizing:border-box;width:100%;min-height:68px;margin:10px 0;background:#111827;color:#fff;border:1px solid #657188;border-radius:6px;padding:8px;resize:vertical;font:12px/1.5 system-ui}.thread-actions{display:flex;gap:6px;flex-wrap:wrap}.thread-error{color:#ffb3a8}.thread-anchor{font-size:11px}.thread-link{font-size:11px}`;
  shadow.append(style);
  const $ = (s) => shadow.querySelector(s);
  const el = (tag, text) => {
    const n = doc.createElement(tag);
    if (text != null) n.textContent = text;
    return n;
  };
  let threads = [];
  const draftKey = (id) => "sumi-review-draft-" + id;
  const openKey = "sumi-review-open";
  let openIds = new Set();
  try {
    openIds = new Set(JSON.parse(win.sessionStorage.getItem(openKey) || "[]"));
  } catch {}
  function saveOpen() {
    win.sessionStorage.setItem(openKey, JSON.stringify([...openIds]));
  }
  function anchor(thread) {
    const scene = (win.SumiScene || win.BebopScene)?.get?.() || {};
    for (const key of [
      "conversation",
      "selectedCharacter",
      "search",
      "filter",
    ]) {
      if (thread.scene[key] != null && scene[key] !== thread.scene[key])
        return null;
    }
    for (const selector of [
      thread.annotation.fullPath,
      thread.annotation.elementPath,
    ]) {
      if (!selector) continue;
      try {
        const nodes = doc.querySelectorAll(selector);
        if (nodes.length === 1) return nodes[0];
        // Agentation paths can describe every message or sidebar button.
        // Only disambiguate with a unique exact text match, never DOM order.
        const text = (thread.annotation.nearbyText || "")
          .replace(/\[(?:before|after):.*?\]/g, "")
          .replace(/\s+/g, " ")
          .trim();
        if (text) {
          const matches = [...nodes].filter(
            (node) => node.textContent.replace(/\s+/g, " ").trim() === text,
          );
          if (matches.length === 1) return matches[0];
        }
      } catch {}
    }
    return null;
  }
  function place() {
    const offsets = new Map();
    threads.forEach((thread) => {
      const card = cards.get(thread.id);
      if (!card) return;
      const target = anchor(thread),
        rect = target?.getBoundingClientRect();
      const visible =
        rect &&
        rect.width > 0 &&
        rect.height > 0 &&
        rect.bottom > 0 &&
        rect.top < win.innerHeight &&
        rect.right > 0 &&
        rect.left < win.innerWidth;
      card.pin.hidden = false;
      card.pin.dataset.placement = visible ? "anchored" : "unplaced";
      if (visible) {
        if (card.pin.parentNode !== pins) pins.append(card.pin);
        card.pin.style.position = "fixed";
        card.pin.style.flexShrink = "";
      } else {
        if (card.pin.parentNode !== rail) rail.append(card.pin);
        card.pin.style.position = "relative";
        card.pin.style.left = card.pin.style.top = "auto";
        card.pin.style.flexShrink = "0";
      }
      card.anchor.textContent = target
        ? visible
          ? "Linked to this element · original revision preserved"
          : "Element is outside the visible area · pin shown in the right rail"
        : "Original location unavailable in this scene · pin shown in the right rail";
      if (visible) {
        const offset = offsets.get(target) || 0;
        offsets.set(target, offset + 32);
        card.pin.style.left =
          Math.min(win.innerWidth - 72, Math.max(4, rect.right - 15)) + "px";
        card.pin.style.top =
          Math.min(win.innerHeight - 34, Math.max(4, rect.top - 10 + offset)) +
          "px";
      }
    });
  }
  win.addEventListener("resize", place);
  doc.addEventListener("scroll", place, true);
  // Chat items mount asynchronously; scene switches can replace anchored nodes.
  const timer = win.setInterval(place, 600);
  win.addEventListener("pagehide", () => win.clearInterval(timer), {
    once: true,
  });
  function create(thread, index) {
    const details = el("details");
    details.className = "review-thread";
    details.dataset.threadId = thread.id;
    details.open = openIds.has(thread.id);
    const summary = el("summary"),
      title = el("span"),
      badge = el("span");
    badge.className = "thread-badge";
    summary.append(title, badge);
    const body = el("div");
    body.className = "thread-body";
    const location = el("p");
    location.className = "thread-anchor";
    const original = el("a", "Original location ↗");
    original.className = "thread-link";
    original.href = `/r/${thread.revision}/?live=0&scene=${encodeURIComponent(JSON.stringify(thread.scene))}`;
    const log = el("div");
    log.className = "thread-log";
    const form = el("form"),
      input = el("textarea");
    input.placeholder = "Not quite right? Reply to the agent…";
    input.setAttribute("aria-label", "Reply to review comment");
    input.maxLength = 8000;
    input.value = win.localStorage.getItem(draftKey(thread.id)) || "";
    input.oninput = () =>
      win.localStorage.setItem(draftKey(thread.id), input.value);
    const actions = el("div");
    actions.className = "thread-actions";
    const send = el("button", "Reply & send"),
      accept = el("button", "Accept"),
      reopen = el("button", "Reopen");
    send.type = "submit";
    accept.type = reopen.type = "button";
    actions.append(send, accept, reopen);
    const error = el("p");
    error.className = "thread-error";
    form.append(input, actions, error);
    body.append(location, original, log, form);
    details.append(summary, body);
    $("#jobs").append(details);
    details.ontoggle = () => {
      if (details.open) openIds.add(thread.id);
      else openIds.delete(thread.id);
      saveOpen();
    };
    const pin = el("button", String(index + 1));
    pin.setAttribute(
      "aria-label",
      `Review comment ${index + 1}: ${thread.title}`,
    );
    pin.dataset.threadId = thread.id;
    pin.onclick = () => {
      $("details").open = true;
      details.open = true;
      openIds.add(thread.id);
      saveOpen();
      details.scrollIntoView({ block: "nearest" });
    };
    pins.append(pin);
    form.onsubmit = (event) => {
      event.preventDefault();
      if (!input.value.trim()) return;
      enqueue({
        endpoint: "/api/review-thread",
        key: win.crypto.randomUUID(),
        action: "reply",
        thread_id: thread.id,
        request_id: win.crypto.randomUUID(),
        message: input.value,
        revision: config.revision,
        scene: (win.SumiScene || win.BebopScene)?.get?.() || {},
      });
      input.value = "";
      input.blur();
      win.localStorage.removeItem(draftKey(thread.id));
      error.textContent = "Reply queued for delivery.";
    };
    async function action(kind) {
      error.textContent = "";
      accept.disabled = reopen.disabled = true;
      try {
        const r = await win.fetch("/api/review-thread", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Sumi-Token": config.token,
          },
          body: JSON.stringify({ thread_id: thread.id, action: kind }),
          signal: AbortSignal.timeout(5000),
        });
        if (!r.ok) throw Error((await r.json()).error || "Action failed");
        error.textContent =
          kind === "accept"
            ? "Accepted."
            : "Reopened. Reply to request another change.";
      } catch (e) {
        error.textContent = e.message;
      } finally {
        accept.disabled = reopen.disabled = false;
      }
    }
    accept.onclick = () => void action("accept");
    reopen.onclick = () => void action("reopen");
    const card = {
      details,
      title,
      badge,
      log,
      input,
      send,
      accept,
      reopen,
      error,
      pin,
      anchor: location,
      last: "",
    };
    cards.set(thread.id, card);
    return card;
  }
  return {
    pendingDraft: () =>
      [...cards.values()].some((c) => c.input.value.trim().length > 0),
    update(data) {
      threads = data;
      data.forEach((thread, index) => {
        const card = cards.get(thread.id) || create(thread, index);
        const color = palette[thread.status] || palette.attention;
        card.details.style.setProperty("--status", color);
        card.pin.style.background = color;
        card.title.textContent = `${index + 1}. ${thread.title}`;
        card.badge.textContent = labels[thread.status] || thread.status;
        card.pin.title = `${labels[thread.status]}: ${thread.title}`;
        card.accept.hidden = thread.status === "accepted";
        card.reopen.hidden = thread.status !== "accepted";
        card.accept.disabled = thread.status === "working";
        const fingerprint = JSON.stringify(thread.messages);
        if (card.last !== fingerprint) {
          const follow =
            card.log.scrollHeight - card.log.scrollTop - card.log.clientHeight <
            30;
          card.last = fingerprint;
          card.log.replaceChildren(
            ...thread.messages.map((message) => {
              const row = el("div");
              row.className = "thread-message";
              row.append(
                el("strong", message.role === "agent" ? "Agent" : "You"),
                el("div", message.text),
              );
              if (message.revision) {
                const link = el(
                  "a",
                  message.role === "agent"
                    ? "Proposed revision ↗"
                    : "Reviewed revision ↗",
                );
                link.className = "thread-link";
                link.href = `/r/${message.revision}/?live=0`;
                row.append(link);
              }
              return row;
            }),
          );
          if (follow) card.log.scrollTop = card.log.scrollHeight;
          if (thread.messages.at(-1)?.role === "agent")
            card.error.textContent = "";
        }
      });
      place();
    },
  };
}
