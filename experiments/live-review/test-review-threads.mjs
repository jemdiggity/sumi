import { chromium } from "../../.playground/live-tools/node_modules/playwright/index.mjs";
import fs from "node:fs";
import assert from "node:assert/strict";
const bundle = fs.readFileSync(process.argv[2], "utf8");
const browser = await chromium.launch();
try {
  const page = await browser.newPage({
      viewport: { width: 1100, height: 800 },
    }),
    errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  let revision = "a".repeat(40),
    request;
  const thread = {
    id: "thread-1",
    title: "Make the button quieter",
    annotation: { fullPath: "#target" },
    revision,
    scene: {},
    status: "ready",
    job_status: "published",
    created: "2026-09-25",
    messages: [
      { id: "m1", role: "you", text: "Make the button quieter" },
      { id: "m2", role: "agent", text: "Adjusted the button" },
    ],
  };
  await page.route("**/*", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/assets/review.js")
      return route.fulfill({ contentType: "text/javascript", body: bundle });
    if (path === "/api/state")
      return route.fulfill({
        json: {
          revision,
          paused: false,
          busy: 0,
          workers: 6,
          queued: 0,
          jobs: [],
          threads: [thread],
        },
      });
    if (path === "/api/review-thread") {
      request = route.request().postDataJSON();
      if (request.action === "accept") thread.status = "accepted";
      if (request.action === "reopen") thread.status = "reopened";
      if (request.action === "reply") {
        thread.status = "working";
        thread.messages.push({ id: "m3", role: "you", text: request.message });
      }
      return route.fulfill({ json: { id: "reply-job" } });
    }
    const viewed = path.split("/")[2] || revision;
    return route.fulfill({
      contentType: "text/html",
      body: `<!doctype html><html><head></head><body><h1>Fixture</h1><button id="target" style="margin:80px">Target</button><script>window.SUMI_REVIEW={revision:'${viewed}',token:'test',appName:'Sumi chat review'}</script><script src="/assets/review.js"></script></body></html>`,
    });
  });
  await page.goto("http://127.0.0.1:9998/r/" + revision + "/");
  const pin = page.getByRole("button", {
    name: "Review comment 1: Make the button quieter",
    exact: true,
  });
  await pin.waitFor();
  assert.equal(
    await pin.evaluate((e) => getComputedStyle(e).backgroundColor),
    "rgb(115, 184, 255)",
  );
  await page
    .getByRole("button", { name: "Start feedback mode", exact: true })
    .click();
  await pin.click();
  const card = page.locator("details.review-thread");
  await card.getByRole("button", { name: "Accept", exact: true }).click();
  await page.waitForFunction(() =>
    [...document.querySelectorAll("*")].some(
      (e) =>
        e.shadowRoot?.querySelector(".thread-badge")?.textContent ===
        "Accepted",
    ),
  );
  assert.equal(
    await pin.evaluate((e) => getComputedStyle(e).backgroundColor),
    "rgb(112, 207, 150)",
  );
  await page.reload();
  await pin.waitFor();
  assert.equal(await card.getAttribute("open"), "");
  await card.getByRole("button", { name: "Reopen", exact: true }).click();
  const reply = card.getByRole("textbox", { name: "Reply to review comment" });
  await reply.fill("Still too bright. Use a muted green.");
  await page.locator("h1").click();
  revision = "b".repeat(40);
  await page.waitForTimeout(3000);
  assert.match(
    page.url(),
    /\/r\/a{40}\//,
    "Draft must defer automatic navigation even after blur",
  );
  await page.reload();
  await reply.waitFor();
  assert.equal(
    await reply.inputValue(),
    "Still too bright. Use a muted green.",
  );
  await card.getByRole("button", { name: "Reply & send", exact: true }).click();
  await page.waitForURL("**/r/" + revision + "/?*");
  await pin.waitFor();
  assert.equal(request.action, "reply");
  assert.equal(request.thread_id, "thread-1");
  assert.equal(request.message, "Still too bright. Use a muted green.");
  assert.equal(
    await card
      .locator(".thread-log")
      .textContent()
      .then((s) => s.includes("Still too bright")),
    true,
  );
  await page.locator("#target").evaluate((el) => el.remove());
  await pin.waitFor({ state: "hidden" });
  assert.match(await card.locator(".thread-anchor").innerText(), /unavailable/);
  assert.equal(
    await card
      .getByRole("link", { name: "Original location ↗" })
      .getAttribute("href"),
    "/r/" + "a".repeat(40) + "/?live=0&scene=%7B%7D",
  );
  assert.deepEqual(errors, []);
  console.log(
    "PASS sticky pins, review colors, acceptance/reopen, refresh/drafts, reply delivery, revision transition, missing-anchor fallback",
  );
} finally {
  await browser.close();
}
