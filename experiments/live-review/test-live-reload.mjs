import { test } from "node:test";
import assert from "node:assert/strict";
import { installLiveReload, hasEditor } from "./live-reload.mjs";
import { pathToFileURL } from "node:url";
const { parseHTML } = await import(pathToFileURL(process.env.SUMI_DOM_MODULE));
function fixture(href = "http://localhost:8770/r/old/") {
  const { document } = parseHTML("<html><body></body></html>");
  const navigations = [],
    storage = new Map();
  const scene = { search: "Spike", filter: "crew", selectedCharacter: "spike" };
  const win = {
    document,
    location: { href, replace: (url) => navigations.push(url) },
    history: {
      replaceState: (_, __, url) => {
        win.location.href = String(url);
      },
    },
    sessionStorage: {
      getItem: (k) => storage.get(k),
      setItem: (k, v) => storage.set(k, v),
      removeItem: (k) => storage.delete(k),
    },
    BebopScene: {
      get: () => scene,
      set: (value) => {
        win.restored = value;
      },
    },
    scrollX: 0,
    scrollY: 420,
    scrollTo: (x, y) => {
      win.scrolled = [x, y];
    },
    requestAnimationFrame: (cb) => cb(),
  };
  let pending = false;
  const panel = { open: false },
    status = {};
  const realNow = Date.now;
  let now = realNow();
  Date.now = () => now;
  const live = installLiveReload(win, {
    revision: "old",
    pending: () => pending,
    panel,
    status,
  });
  now += 2000;
  return {
    win,
    live,
    navigations,
    scene,
    storage,
    panel,
    status,
    pending: (v) => {
      pending = v;
    },
    cleanup: () => {
      Date.now = realNow;
    },
  };
}
test("publication preserves scene, scroll and panel; navigates only once", () => {
  const f = fixture();
  try {
    f.live.update("old");
    assert.equal(f.navigations.length, 0);
    f.live.update("new");
    f.live.update("newer");
    assert.equal(f.navigations.length, 1);
    const url = new URL(f.navigations[0]);
    assert.equal(url.pathname, "/r/new/");
    assert.deepEqual(JSON.parse(url.searchParams.get("scene")), f.scene);
    installLiveReload(f.win, {
      revision: "new",
      pending: () => false,
      panel: f.panel,
      status: f.status,
    });
    assert.deepEqual(f.win.restored, f.scene);
    assert.deepEqual(f.win.scrolled, [0, 420]);
    assert.equal(f.panel.open, false);
  } finally {
    f.cleanup();
  }
});
test("blurred annotation popup in nested shadow roots and unsent feedback defer publication", () => {
  const f = fixture();
  try {
    const host = f.win.document.createElement("div");
    f.win.document.body.append(host);
    const root = host.attachShadow({ mode: "open" });
    root.innerHTML =
      "<div data-annotation-popup><textarea>unsaved comment</textarea></div>";
    assert.equal(hasEditor(f.win.document), true);
    f.live.update("new");
    assert.equal(f.navigations.length, 0);
    root.replaceChildren();
    f.pending(true);
    f.live.update("new");
    assert.equal(f.navigations.length, 0);
    f.pending(false);
    f.live.update("new");
    assert.equal(f.navigations.length, 1);
  } finally {
    f.cleanup();
  }
});
test("historical review stays pinned until live updates explicitly enabled", () => {
  const f = fixture("http://localhost:8770/r/old/?live=0");
  try {
    f.live.update("new");
    assert.equal(f.navigations.length, 0);
    f.live.toggle();
    f.live.update("new");
    assert.equal(f.navigations.length, 1);
  } finally {
    f.cleanup();
  }
});
