#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { existsSync, mkdirSync } from "node:fs";
import { join, resolve } from "node:path";

const requireRoot = process.env.PLAYWRIGHT_REQUIRE_ROOT
  ? resolve(process.env.PLAYWRIGHT_REQUIRE_ROOT)
  : process.cwd();
const require = createRequire(join(requireRoot, "package.json"));
const { chromium } = require("playwright");

const baseUrl = process.env.NEBULA_DEMO_BASE_URL || "http://localhost:8080";
const output = resolve(process.env.NEBULA_DEMO_GIF || "docs/assets/screenshots/demo.gif");
const frameDir = resolve(process.env.NEBULA_DEMO_FRAME_DIR || "tmp/demo-gif-frames");
const username = process.env.NEBULA_DEMO_USERNAME || "admin";
const password = process.env.NEBULA_DEMO_PASSWORD || "ChangeMe@1234!";
const executablePath =
  process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ||
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

mkdirSync(frameDir, { recursive: true });
mkdirSync(resolve("docs/assets/screenshots"), { recursive: true });

function assertTool(command, message) {
  const result = spawnSync(command, ["-version"], { encoding: "utf-8" });
  if (result.error) {
    throw new Error(message);
  }
}

async function clickFirst(page, labels, timeout = 1500) {
  for (const label of labels) {
    const locator = page.getByText(label, { exact: true }).first();
    try {
      await locator.waitFor({ state: "visible", timeout });
      await locator.click();
      return true;
    } catch {
      // Try the next label.
    }
  }
  return false;
}

async function fillLoginForm(page) {
  const inputs = page.locator("input:visible");
  const count = await inputs.count();
  if (count === 0) {
    return false;
  }

  const usernameInput = page
    .getByRole("textbox", { name: /请输入用户名|用户名|username/i })
    .first();
  try {
    await usernameInput.fill(username, { timeout: 1500 });
  } catch {
    await inputs.nth(0).fill(username);
  }

  const passwordInput = page.locator('input[type="password"]:visible').first();
  try {
    await passwordInput.fill(password, { timeout: 1500 });
  } catch {
    if (count > 1) {
      await inputs.nth(1).fill(password);
    }
  }

  const loginButton = page
    .getByRole("button", { name: /登录|login/i })
    .first();
  try {
    await loginButton.click({ timeout: 1500 });
  } catch {
    await page.locator("button:visible").first().click();
  }
  return true;
}

async function closePasswordDialog(page) {
  const labels = ["取消", "稍后再说", "以后再说", "Cancel"];
  await clickFirst(page, labels, 1000);
}

async function capture(page, frames, name, delay) {
  await page.waitForTimeout(700);
  const file = join(frameDir, `${String(frames.length + 1).padStart(2, "0")}-${name}.png`);
  await page.screenshot({ path: file, fullPage: false });
  frames.push({ file, delay });
}

async function main() {
  assertTool("magick", "ImageMagick `magick` is required to build the demo GIF.");
  if (!existsSync(executablePath)) {
    throw new Error(`Chromium executable not found: ${executablePath}`);
  }

  const browser = await chromium.launch({
    headless: true,
    executablePath,
    args: ["--no-sandbox"],
  });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 2,
    locale: "zh-CN",
  });
  const page = await context.newPage();
  const frames = [];

  await page.goto(`${baseUrl}/admin/`, { waitUntil: "networkidle" });
  await page.waitForURL(/\/admin\/login|\/admin\/?/, { timeout: 5000 }).catch(() => {});
  await capture(page, frames, "login", 200);

  if (await fillLoginForm(page)) {
    await page.waitForTimeout(3000);
    await closePasswordDialog(page);
  }
  await capture(page, frames, "dashboard", 300);

  await clickFirst(page, ["知识库", "Knowledge"]);
  await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
  await capture(page, frames, "knowledge-list", 250);

  const openedCreate = await clickFirst(page, ["创建", "新建", "Create", "New"]);
  if (openedCreate) {
    await page.waitForTimeout(1200);
  }
  await capture(page, frames, "knowledge-create-or-detail", 200);

  await clickFirst(page, ["知识运营", "运营看板", "运营总览"]);
  await page.waitForTimeout(1000);
  await clickFirst(page, ["质量闭环", "反馈闭环", "Quality"]);
  await page.waitForTimeout(400);
  await page.mouse.wheel(0, 700);
  await capture(page, frames, "quality-loop", 200);

  const docsPage = await context.newPage();
  await docsPage.goto(`${baseUrl}/healthz`, { waitUntil: "networkidle" });
  await capture(docsPage, frames, "api-or-health", 200);

  await browser.close();

  const args = [];
  for (const frame of frames) {
    args.push("-delay", String(frame.delay), frame.file);
  }
  args.push("-resize", "1000x", "-layers", "Optimize", "-loop", "0", output);
  const result = spawnSync("magick", args, { stdio: "inherit" });
  if (result.status !== 0) {
    throw new Error("ImageMagick failed to build the demo GIF.");
  }

  console.log(`Demo GIF written to ${output}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
