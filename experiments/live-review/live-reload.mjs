// Agentation renders editors in open shadow roots; a blurred draft still blocks.
export function hasEditor(root) {
  if (root.querySelector("[data-annotation-popup]")) return true;
  const active = root.activeElement;
  if (
    active?.matches(
      'input, textarea, select, [contenteditable]:not([contenteditable="false"])',
    )
  )
    return true;
  return [...root.querySelectorAll("*")].some(
    (element) => element.shadowRoot && hasEditor(element.shadowRoot),
  );
}

export function installLiveReload(win, { revision, pending, panel, status }) {
  const storageKey = "sumi-bebop-reload";
  let navigating = false;
  let composing = false;
  let lastInteraction = Date.now();
  const touch = () => {
    lastInteraction = Date.now();
  };
  for (const event of ["input", "pointerdown", "keydown", "wheel"]) {
    win.document.addEventListener(event, touch, true);
  }
  win.document.addEventListener(
    "compositionstart",
    () => {
      composing = true;
    },
    true,
  );
  win.document.addEventListener(
    "compositionend",
    () => {
      composing = false;
      touch();
    },
    true,
  );
  const url = new URL(win.location.href);
  let enabled = url.searchParams.get("live") !== "0";
  try {
    const saved = JSON.parse(win.sessionStorage.getItem(storageKey) || "null");
    win.sessionStorage.removeItem(storageKey);
    if (saved?.revision === revision && enabled) {
      win.BebopScene?.set?.(saved.scene);
      panel.open = saved.panelOpen;
      win.requestAnimationFrame(() =>
        win.requestAnimationFrame(() => win.scrollTo(saved.x, saved.y)),
      );
    }
  } catch {
    /* Storage unavailable: URL scene remains a fallback. */
  }
  return {
    get enabled() {
      return enabled;
    },
    toggle() {
      enabled = !enabled;
      const current = new URL(win.location.href);
      current.searchParams.set("live", enabled ? "1" : "0");
      win.history.replaceState(null, "", current);
      return enabled;
    },
    update(latest) {
      if (navigating) return;
      if (!enabled) {
        status.textContent = "Live updates off · revision pinned";
        return;
      }
      if (!latest || latest === revision) {
        status.textContent = "Live updates on";
        return;
      }
      if (
        pending() ||
        composing ||
        hasEditor(win.document) ||
        Date.now() - lastInteraction < 1500
      ) {
        status.textContent =
          "Update ready · waiting for you to finish editing or sending";
        return;
      }
      const scene = win.BebopScene?.get?.() || {};
      const next = new URL(`/r/${latest}/`, win.location.href);
      next.searchParams.set("live", "1");
      next.searchParams.set("scene", JSON.stringify(scene));
      try {
        win.sessionStorage.setItem(
          storageKey,
          JSON.stringify({
            revision: latest,
            scene,
            x: win.scrollX,
            y: win.scrollY,
            panelOpen: panel.open,
          }),
        );
      } catch {}
      navigating = true;
      status.textContent = "Loading published revision…";
      win.location.replace(next.href);
    },
  };
}
