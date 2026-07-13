const { chromium, request } = require("playwright");

(async () => {
  console.error("start");
  const baseURL = "http://localhost:3000";
  const api = await request.newContext({ baseURL });
  const login = await api.post("/login", {
    data: { user: "admin", password: "changeme" },
  });
  console.error("login", login.status());
  if (!login.ok()) {
    throw new Error(`login failed: ${login.status()} ${await login.text()}`);
  }
  const browser = await chromium.launch({ headless: true });
  console.error("browser");
  const context = await browser.newContext({
    storageState: await api.storageState(),
    viewport: { width: 1024, height: 1692 },
  });
  const page = await context.newPage();
  console.error("page");
  await page.goto(
    `${baseURL}/d/bioetl-silver-reject-explorer/silver-reject-explorer?orgId=1&theme=light&from=now-12h&to=now&timezone=UTC`,
    { waitUntil: "commit", timeout: 90000 },
  );
  console.error("commit");
  await page.waitForLoadState("domcontentloaded", { timeout: 90000 }).catch((error) => {
    console.error("domcontentloaded timeout", String(error));
  });
  console.error("domcontentloaded");
  await page.waitForTimeout(12000);
  console.error("settled");
  const result = await page.evaluate(() => {
    const normalize = (value) => String(value || "").replace(/\s+/g, " ").trim();
    const ids = [1000, 1, 13, 10, 2];
    return ids.map((id) => {
      const located = document.querySelector(`[data-viz-panel-key="panel-${id}"]`);
      if (!located) return { id, missing: true };
      const ancestry = [];
      let current = located;
      for (let depth = 0; current && depth < 6; depth += 1, current = current.parentElement) {
        ancestry.push({
          tag: current.tagName,
          className: normalize(current.className),
          dataPanelId: current.getAttribute("data-panelid"),
          dataVizPanelKey: current.getAttribute("data-viz-panel-key"),
          dataGriditemKey: current.getAttribute("data-griditem-key"),
          testId: current.getAttribute("data-testid"),
          ariaLabel: current.getAttribute("aria-label"),
          text: normalize(current.innerText || current.textContent || "").slice(0, 500),
          html: current.outerHTML.slice(0, 1200),
        });
      }
      const interesting = Array.from(located.querySelectorAll("*"))
        .filter((element) => {
          const attrs = [
            element.getAttribute("aria-label") || "",
            element.getAttribute("data-testid") || "",
            element.getAttribute("aria-busy") || "",
            element.className || "",
          ].join(" ");
          return /load|busy|panel|markdown|text/i.test(attrs);
        })
        .slice(0, 30)
        .map((element) => ({
          tag: element.tagName,
          className: normalize(element.className),
          testId: element.getAttribute("data-testid"),
          ariaLabel: element.getAttribute("aria-label"),
          ariaBusy: element.getAttribute("aria-busy"),
          text: normalize(element.innerText || element.textContent || "").slice(0, 300),
          rect: (() => {
            const rect = element.getBoundingClientRect();
            return [rect.x, rect.y, rect.width, rect.height];
          })(),
        }));
      return {
        id,
        locatedTag: located.tagName,
        childCount: located.children.length,
        ancestry,
        interesting,
      };
    });
  });
  console.error("evaluated");
  console.log(JSON.stringify(result, null, 2));
  process.exit(0);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
