// Publication gate. Synthetic stream fixtures exercise behavior, never live models.
import assert from "node:assert/strict";
import fs from "node:fs";
import { pathToFileURL } from "node:url";
const { chromium } = await import(pathToFileURL(process.argv[2]));
const html = fs.readFileSync(process.argv[3], "utf8");
const browser = await chromium.launch();
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 950 },
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const models = [
    { id: "gpt-6-luna", name: "Luna", efforts: ["low", "medium", "high"] },
    { id: "gpt-6-sol", name: "Sol", efforts: ["low", "medium", "high"] },
  ];
  let submitted;
  await page.addInitScript(() => {
    localStorage.setItem("sumi-chat-current", "fixture");
    window.SUMI_REVIEW = { token: "test" };
    window.EventSource = class {
      constructor() {
        window.fixtureStream = this;
        setTimeout(() => this.onopen?.(), 0);
      }
      close() {}
    };
    let sequence = 0;
    window.pushFixture = (event) =>
      window.fixtureStream.onmessage({
        data: JSON.stringify(event),
        lastEventId: String(++sequence),
      });
  });
  await page.route("**/*", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/")
      return route.fulfill({ contentType: "text/html", body: html });
    if (path === "/chat/state")
      return route.fulfill({
        json: {
          model: "gpt-6-luna",
          models,
          conversations: [{ id: "fixture", title: "Fixture", status: "idle" }],
        },
      });
    if (path === "/chat/send") {
      submitted = route.request().postDataJSON();
      return route.fulfill({ json: { id: "fixture" } });
    }
    return route.abort();
  });
  await page.goto("http://sumi.test/");
  await page.waitForFunction(() => window.fixtureStream?.onmessage);
  const push = (event) => page.evaluate((e) => window.pushFixture(e), event);
  await push({
    type: "chat.user",
    turn: 1,
    text: "First turn",
    model: "gpt-6-luna",
    effort: "low",
  });
  assert.equal(await page.locator(".thinking").count(), 1);
  await push({
    type: "item.completed",
    turn: 1,
    item: {
      id: "item_0",
      type: "reasoning",
      text: "Fixture reasoning summary",
    },
  });
  await push({
    type: "item.completed",
    turn: 1,
    item: {
      id: "item_1",
      type: "command_execution",
      command: "echo first-turn",
      aggregated_output: "first-output",
    },
  });
  await push({
    type: "item.completed",
    turn: 1,
    item: { id: "item_2", type: "agent_message", text: "First response" },
  });
  await push({
    type: "turn.completed",
    turn: 1,
    usage: { input_tokens: 111, cached_input_tokens: 50, output_tokens: 22 },
  });
  await push({ type: "chat.done", turn: 1, status: "idle", elapsed: 1.25 });
  const first = page
    .locator(".message.agent")
    .filter({ hasText: "First response" });
  assert.equal(
    await first.locator("details.response-activity").count(),
    1,
    "Response must expose turn details",
  );
  await first.locator("details.response-activity > summary").click();
  assert.match(
    await first.innerText(),
    /echo first-turn/,
    "Tool items must inherit the enclosing event turn",
  );
  assert.match(await first.innerText(), /Fixture reasoning summary/);
  assert.match(await first.innerText(), /Input: 111/);
  await first.getByText("Show output", { exact: true }).click();
  assert.match(await first.innerText(), /first-output/);
  await push({ type: "chat.user", turn: 2, text: "Second turn" });
  await push({
    type: "item.completed",
    turn: 2,
    item: { id: "item_2", type: "agent_message", text: "Second response" },
  });
  await push({ type: "chat.done", turn: 2, status: "idle", elapsed: 2 });
  assert.equal(
    await first.locator("details.response-activity").getAttribute("open"),
    "",
    "Disclosure must survive incoming events",
  );
  assert.equal(
    await first.locator("details.activity-detail").getAttribute("open"),
    "",
  );
  const second = page
    .locator(".message.agent")
    .filter({ hasText: "Second response" });
  await second.locator("summary").click();
  assert.doesNotMatch(
    await second.innerText(),
    /echo first-turn/,
    "Do not mix turns",
  );
  assert.match(
    await second.innerText(),
    /No tool calls or reasoning summaries/,
  );
  assert.equal(await page.locator(".thinking").count(), 0);
  assert.equal(
    await page.locator(".message.agent .speaker").count(),
    0,
    "No agent labels on completed replies",
  );
  await page.getByLabel("Choose chat skin").selectOption("tui");
  assert.equal(await page.evaluate(() => document.body.dataset.skin), "tui");
  const contrast = await page
    .locator(".message.user")
    .first()
    .evaluate((el) => ({
      bg: getComputedStyle(el).backgroundColor,
      fg: getComputedStyle(el).color,
    }));
  assert.notEqual(
    contrast.bg,
    "rgb(235, 236, 228)",
    "TUI messages need dark backgrounds",
  );
  await page.getByLabel("Model", { exact: true }).selectOption("gpt-6-sol");
  await page
    .getByLabel("Reasoning effort", { exact: true })
    .selectOption("high");
  await page
    .getByRole("textbox", { name: "Message the agent" })
    .fill("Model selection fixture");
  await page.getByRole("button", { name: "Send ↑", exact: true }).click();
  await page.waitForTimeout(100);
  assert.equal(submitted.model, "gpt-6-sol");
  assert.equal(submitted.effort, "high");
  assert.deepEqual(errors, []);
  console.log(
    "PASS browser: turn drilldown/output/usage, disclosure persistence, no turn leakage, working animation, TUI skin, model/effort payload",
  );
} finally {
  await browser.close();
}
