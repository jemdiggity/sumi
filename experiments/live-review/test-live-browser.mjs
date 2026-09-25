// Isolated browser + intercepted revisions/API: no comments dispatched to workers.
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";
const { chromium } = await import(pathToFileURL(process.env.SUMI_PLAYWRIGHT));
const origin = "http://127.0.0.1:8770";
const realState = await (await fetch(origin + "/api/state")).json();
const html = await (await fetch(`${origin}/r/${realState.revision}/`)).text();
const first = "a".repeat(40),
  second = "b".repeat(40),
  third = "c".repeat(40);
let latest = first;
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/api/**", (route) => {
    if (!route.request().url().endsWith("/api/state")) return route.abort();
    return route.fulfill({
      json: {
        revision: latest,
        paused: false,
        workers: 6,
        busy: 0,
        queued: 0,
        jobs: [],
      },
    });
  });
  await page.route("**/r/*/", (route) => {
    const revision = new URL(route.request().url()).pathname.split("/")[2];
    return route.fulfill({
      contentType: "text/html",
      body: html.replaceAll(realState.revision, revision),
    });
  });
  // Query strings also used by automatic scene restoration.
  await page.route("**/r/*/?*", (route) => {
    const revision = new URL(route.request().url()).pathname.split("/")[2];
    return route.fulfill({
      contentType: "text/html",
      body: html.replaceAll(realState.revision, revision),
    });
  });
  await page.goto(`${origin}/r/${first}/`);
  await page
    .getByRole("button", { name: "Start feedback mode", exact: true })
    .click();
  await page.getByRole("button", { name: "Exit", exact: true }).waitFor();
  latest = second;
  await page.waitForURL(`**/r/${second}/?*`);
  await page.getByRole("button", { name: "Exit", exact: true }).waitFor();
  console.log("PASS active comment tool restored after publication");
  await page.locator("[data-character]").first().click();
  const editor = page.locator("[data-annotation-popup] textarea").first();
  await editor.fill("Keep this unfinished draft");
  latest = third;
  await page.waitForTimeout(3500);
  assert.equal(new URL(page.url()).pathname, `/r/${second}/`);
  assert.equal(await editor.inputValue(), "Keep this unfinished draft");
  console.log("PASS draft protected while newer revision waits");
  await editor.press("Escape");
  // Escape closes the popup without exiting the tool.
  await page.waitForURL(`**/r/${third}/?*`);
  await page.getByRole("button", { name: "Exit", exact: true }).waitFor();
  console.log(
    "PASS next update restores active tool again after draft dismissed",
  );
  await page.getByRole("button", { name: "Exit", exact: true }).click();
  latest = "d".repeat(40);
  await page.waitForURL(`**/r/${latest}/?*`);
  await page
    .getByRole("button", { name: "Start feedback mode", exact: true })
    .waitFor();
  console.log("PASS deliberately disabled tool stays disabled");
  assert.deepEqual(errors, []);
} finally {
  await browser.close();
}
