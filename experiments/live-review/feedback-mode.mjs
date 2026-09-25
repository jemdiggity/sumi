// Agentation 3.1 has no controlled active-mode prop. Use its accessible launcher,
// scoped to the toolbar, rather than private React state or generated CSS names.
function launcher(root) {
  const button = root.querySelector(
    '[data-feedback-toolbar] button[aria-expanded][aria-label="Exit"], ' +
      '[data-feedback-toolbar] button[aria-expanded][aria-label="Start feedback mode"]',
  );
  if (button) return button;
  for (const element of root.querySelectorAll("*")) {
    if (element.shadowRoot) {
      const found = launcher(element.shadowRoot);
      if (found) return found;
    }
  }
  return null;
}

export function feedbackActive(document) {
  return launcher(document)?.getAttribute("aria-expanded") === "true";
}

export function restoreFeedbackMode(win) {
  // React and its shadow portals mount after the reload controller. Retry for a
  // bounded interval, stopping at the first mounted launcher (never toggle twice).
  const deadline = Date.now() + 5000;
  function restore() {
    const button = launcher(win.document);
    if (!button) {
      if (Date.now() < deadline) win.setTimeout(restore, 25);
      return;
    }
    if (button.getAttribute("aria-expanded") !== "true") {
      // detail=1 avoids Agentation's keyboard-launch focus jump to the controls.
      button.dispatchEvent(
        new win.MouseEvent("click", {
          bubbles: true,
          composed: true,
          detail: 1,
        }),
      );
    }
  }
  restore();
}
