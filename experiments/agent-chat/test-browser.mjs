// Real native model smoke test; conversations are intentionally retained as evidence.
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";
const { chromium } = await import(pathToFileURL(process.env.SUMI_PLAYWRIGHT));
const browser = await chromium.launch();
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("http://127.0.0.1:8771/");
  await page.getByText("Connected", { exact: true }).waitFor();
  await page.screenshot({
    path: ".playground/chat-agent/empty.png",
    fullPage: true,
  });
  const input = page.getByRole("textbox", { name: "Message the agent" });
  await input.fill(
    "Remember the phrase cobalt-orbit for this conversation. Reply with only Ready. Do not use tools.",
  );
  await page.getByRole("button", { name: "Send ↑", exact: true }).click();
  await page.waitForFunction(
    () => document.querySelectorAll(".message.agent").length === 1,
    {},
    { timeout: 90000 },
  );
  await page.waitForFunction(
    () => !window.SumiLiveBusy,
    {},
    { timeout: 90000 },
  );
  const id = await page.evaluate(() => window.SumiScene.get().conversation);
  assert.ok(id);
  console.log("PASS real Luna response", id);
  await input.fill(
    "What phrase did I ask you to remember? Also create hello.txt containing that phrase in your workspace, and read it back with a shell command. Keep your answer short.",
  );
  await page.getByRole("button", { name: "Send ↑", exact: true }).click();
  await page.waitForFunction(
    () =>
      document.querySelectorAll(".message.agent").length >= 2 &&
      !window.SumiLiveBusy,
    {},
    { timeout: 120000 },
  );
  assert.match(await page.locator("#messages").innerText(), /cobalt-orbit/i);
  assert.match(
    await page.locator("#activity").innerText(),
    /command execution/i,
  );
  assert.notEqual(await page.locator("#tokens-out").innerText(), "—");
  await page.screenshot({
    path: ".playground/chat-agent/conversation.png",
    fullPage: true,
  });
  console.log("PASS resumed thread, real command activity, usage");
  await input.fill("A draft to preserve");
  await page.reload();
  await page.waitForFunction(
    () => document.querySelectorAll(".message.agent").length >= 2,
  );
  assert.equal(await input.inputValue(), "A draft to preserve");
  assert.equal(
    await page.evaluate(() => window.SumiScene.get().conversation),
    id,
  );
  console.log("PASS reload restores conversation and draft");
  await input.fill(
    "Run a shell command that sleeps for 30 seconds, then reply done.",
  );
  await page.getByRole("button", { name: "Send ↑", exact: true }).click();
  await page.getByRole("button", { name: "■ Stop", exact: true }).waitFor();
  await page.getByRole("button", { name: "■ Stop", exact: true }).click();
  await page.waitForFunction(
    () => !window.SumiLiveBusy,
    {},
    { timeout: 15000 },
  );
  const state = await (await fetch("http://127.0.0.1:8771/chat/state")).json();
  assert.equal(
    state.conversations.find((row) => row.id === id).status,
    "stopped",
  );
  assert.deepEqual(errors, []);
  console.log("PASS stop and no browser exceptions");
} finally {
  await browser.close();
}
