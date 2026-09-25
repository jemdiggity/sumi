import fs from "node:fs";
import vm from "node:vm";
import { pathToFileURL } from "node:url";
const { parseHTML } = await import(pathToFileURL(process.argv[2]));
const text = fs.readFileSync(process.argv[3], "utf8");
function assert(ok, message) {
  if (!ok) throw Error(message);
}
assert(
  !/^(?:<{7,}|>{7,}|\|{7,}|={7,}|%{7,}|\+{7,}|-{7,}|\\{7,})(?:\s|$)/m.test(
    text,
  ),
  "Merge markers",
);
const { window, document } = parseHTML(text);
const storage = new Map();
const localStorage = {
  getItem: (key) => storage.get(key),
  setItem: (key, value) => storage.set(key, value),
};
const context = vm.createContext({
  window,
  document,
  localStorage,
  console,
  requestAnimationFrame: (fn) => fn(),
  setInterval: () => {},
  fetch: () => {
    throw Error("Unexpected startup request");
  },
});
for (const script of document.querySelectorAll("script")) {
  assert(!script.hasAttribute("src"), "Source must stay self-contained");
  new vm.Script(script.textContent).runInContext(context, { timeout: 2500 });
}
for (const id of [
  "composer",
  "prompt",
  "send",
  "stop",
  "messages",
  "model",
  "effort",
  "conversations",
])
  assert(document.getElementById(id), `${id} missing`);
assert(window.SumiScene?.get && window.SumiScene?.set, "Scene hooks missing");
window.SumiScene.set({
  conversation: null,
  draft: "Keep my draft",
  inspectorHidden: true,
});
assert(
  window.SumiScene.get().draft === "Keep my draft",
  "Draft restoration broken",
);
assert(
  document.querySelector("#prompt").getAttribute("maxlength") === "16000",
  "Composer bound missing",
);
console.log(
  "PASS chat structure, script initialization, scene and draft restoration",
);
