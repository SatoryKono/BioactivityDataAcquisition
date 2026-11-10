/** Observe every native pagination page; retain full cell text and link targets. */
const fs = require("node:fs");
const path = require("node:path");

// Browser operations share a viewport, focus and pagination state.
async function visitSequentially(items, visit) {
    const iterator = items[Symbol.iterator]();
    async function advance() {
        const item = iterator.next();
        if (!item.done && (await visit(item.value)) !== false) {
            await advance();
        }
    }
    await advance();
}

function indices(length) {
    return Array.from({ length }, (_, index) => index);
}

function tableEvidence(el) {
    const rect = (node) => {
        const r = node.getBoundingClientRect();
        return { x: r.x, y: r.y, width: r.width, height: r.height };
    };
    const grids = [...el.querySelectorAll('[role="grid"]')];
    return {
        cells: [
            ...el.querySelectorAll(
                '[role="cell"], [role="gridcell"], [role="columnheader"]',
            ),
        ].map((cell) => ({
            role: cell.getAttribute("role"),
            text: cell.textContent,
            bbox: rect(cell),
            row: cell.closest('[role="row"]')?.getAttribute("aria-rowindex"),
            column: cell.getAttribute("aria-colindex"),
            clipped:
                cell.scrollWidth > cell.clientWidth + 2 ||
                cell.scrollHeight > cell.clientHeight + 2,
            links: [...cell.querySelectorAll("a[href]")].map((a) => ({
                text: a.textContent,
                href: a.href,
                title: a.title,
                tabIndex: a.tabIndex,
            })),
        })),
        scrollers: [
            ...el.querySelectorAll(
                '[role="grid"],.scrollbar-view,[data-testid*="scrollbar viewport"]',
            ),
        ].map((s) => ({
            grid: grids.indexOf(s),
            bbox: rect(s),
            clientHeight: s.clientHeight,
            scrollHeight: s.scrollHeight,
            clientWidth: s.clientWidth,
            scrollWidth: s.scrollWidth,
            scrollTop: s.scrollTop,
            scrollLeft: s.scrollLeft,
        })),
        summary:
            /\b\d+\s*[-–]\s*\d+ of \d+ rows\b/.exec(el.innerText)?.[0] || null,
    };
}

async function captureScrollTiles(
    page,
    root,
    { dir, index, outputDir, pngEvidence, timeout },
) {
    const grids = root.locator('[role="grid"]');
    const tiles = [];
    await visitSequentially(indices(await grids.count()), async (g) => {
        const grid = grids.nth(g);
        const size = await grid.evaluate((el) => ({
            w: el.clientWidth,
            h: el.clientHeight,
            sw: el.scrollWidth,
            sh: el.scrollHeight,
            x: el.scrollLeft,
            y: el.scrollTop,
        }));
        if (size.sw <= size.w + 2 && size.sh <= size.h + 2) return;
        if (size.w <= 0 || size.h <= 0)
            throw new Error("Table grid has no visible scroll viewport");
        const positions = (extent, viewport) => {
            const result = [0],
                max = Math.max(0, extent - viewport);
            // Overlap retains sticky headers and rows crossing viewport boundaries.
            while (result.at(-1) < max)
                result.push(
                    Math.min(
                        max,
                        result.at(-1) + Math.max(1, Math.floor(viewport / 2)),
                    ),
                );
            return result;
        };
        try {
            const columns = positions(size.sw, size.w);
            await visitSequentially(positions(size.sh, size.h), (y) =>
                visitSequentially(columns, async (x) => {
                    if (tiles.length >= 1000)
                        throw new Error(
                            "Table scroll capture exceeded 1000 tiles",
                        );
                    await grid.evaluate(
                        (el, { x, y }) => {
                            el.scrollLeft = x;
                            el.scrollTop = y;
                        },
                        { x, y },
                    );
                    await page.waitForTimeout(150);
                    const evidence = await root.evaluate(tableEvidence);
                    const file = path.join(
                        dir,
                        `page-${index}-scroll-${tiles.length + 1}.png`,
                    );
                    const bytes =
                        await require("./native_browser_zoom.cjs").captureElementScreenshot(
                            page,
                            root,
                            {
                                path: file,
                                animations: "disabled",
                                timeout,
                                allowVerticalTiles: true,
                            },
                        );
                    tiles.push({
                        grid: g,
                        x,
                        y,
                        ...evidence,
                        file: path.relative(outputDir, file),
                        ...pngEvidence(bytes),
                    });
                }),
            );
        } finally {
            await grid.evaluate((el, { x, y }) => {
                el.scrollLeft = x;
                el.scrollTop = y;
            }, size);
        }
    });
    return tiles;
}

async function captureInspectedValues(
    page,
    root,
    cells,
    { dir, index, outputDir, pngEvidence, timeout },
) {
    const results = [];
    const values = [
        ...new Set(
            cells
                .filter((c) => c.clipped && c.role !== "columnheader")
                .map((c) => c.text),
        ),
    ];
    await visitSequentially(values, async (text) => {
        // The accessible name also contains the Inspect button's label.
        const literal = text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const cell = root
            .locator('[role="gridcell"]')
            .filter({ hasText: new RegExp(`^${literal}$`) })
            .first();
        if (!(await cell.count())) {
            results.push({ text, status: "CELL_NOT_MOUNTED" });
            return;
        }
        await cell.scrollIntoViewIfNeeded({ timeout });
        await cell.hover();
        const inspect = cell.getByRole("button", {
            name: "Inspect value",
            exact: true,
        });
        if (!(await inspect.count())) {
            results.push({ text, status: "INSPECT_UNAVAILABLE" });
            return;
        }
        await inspect.click();
        try {
            await page
                .getByRole("tab", { name: "Plain text", exact: true })
                .waitFor({ state: "visible", timeout });
            const value = page.getByText(text, { exact: true }).last();
            await value.waitFor({ state: "visible", timeout });
            const observed = await value.innerText();
            if (observed !== text)
                throw new Error(
                    "Inspect value differs from the captured table cell",
                );
            const file = path.join(
                dir,
                `page-${index}-inspect-${results.length + 1}.png`,
            );
            const bytes =
                await require("./native_browser_zoom.cjs").capturePageScreenshot(
                    page,
                    { path: file, animations: "disabled", timeout },
                );
            results.push({
                text,
                observed,
                status: "VERIFIED",
                file: path.relative(outputDir, file),
                ...pngEvidence(bytes),
            });
        } finally {
            await page
                .getByRole("button", { name: "Close", exact: true })
                .click();
        }
    });
    return results;
}
async function captureTablePages(
    page,
    { dashboard, outputDir, pngEvidence, timeout },
) {
    const results = [];
    const panels = dashboard.tablePanels || dashboard.firstWindowPanels || [];
    await visitSequentially(panels, async (panel) => {
        if (panel.type !== "table") return;
        const root = page
            .locator(`[data-viz-panel-key="panel-${panel.id}"]`)
            .first();
        await root.scrollIntoViewIfNeeded({ timeout });
        await root.waitFor({ state: "visible", timeout });
        const next = root.getByRole("button", {
            name: "next page",
            exact: true,
        });
        const paginated = (await next.count()) > 0;
        const previous = root.getByRole("button", {
            name: "previous page",
            exact: true,
        });
        const pages = [];
        let complete = false;
        try {
            await visitSequentially(indices(100), async (pageIndex) => {
                const index = pageIndex + 1;
                const evidence = await root.evaluate(tableEvidence);
                const dir = path.join(
                    outputDir,
                    "panels",
                    dashboard.uid,
                    String(panel.id),
                );
                await fs.promises.mkdir(dir, { recursive: true });
                const file = path.join(dir, `page-${index}.png`);
                const bytes =
                    await require("./native_browser_zoom.cjs").captureElementScreenshot(
                        page,
                        root,
                        {
                            path: file,
                            animations: "disabled",
                            timeout,
                            allowVerticalTiles: true,
                        },
                    );
                const scrollTiles = await captureScrollTiles(page, root, {
                    dir,
                    index,
                    outputDir,
                    pngEvidence,
                    timeout,
                });
                const inspectedValues = await captureInspectedValues(
                    page,
                    root,
                    [...evidence.cells, ...scrollTiles.flatMap((t) => t.cells)],
                    { dir, index, outputDir, pngEvidence, timeout },
                );
                pages.push({
                    page: index,
                    ...evidence,
                    scrollTiles,
                    inspectedValues,
                    file: path.relative(outputDir, file),
                    ...pngEvidence(bytes),
                });
                if (!paginated || (await next.isDisabled())) {
                    complete = true;
                    return false;
                }
                const before = await root.innerText();
                await next.focus();
                await page.keyboard.press("Enter");
                await page.waitForFunction(
                    ({ id, before }) =>
                        document.querySelector(
                            `[data-viz-panel-key="panel-${id}"]`,
                        )?.innerText !== before,
                    { id: panel.id, before },
                    { timeout },
                );
            });
        } finally {
            if (paginated) {
                await visitSequentially(pages, async () => {
                    if (await previous.isDisabled()) return false;
                    await previous.click();
                    await page.waitForTimeout(100);
                });
            }
        }
        results.push({
            panelId: panel.id,
            title: panel.title,
            paginated,
            status: complete ? "COMPLETE" : "NOT_PROVEN",
            method: "native next-page button activated with Enter; original first page restored",
            pages,
        });
    });
    if (results.some((result) => result.status !== "COMPLETE")) {
        throw new Error(
            "Table capture incomplete: pagination exceeded 100 pages",
        );
    }
    return results;
}
module.exports = { captureTablePages };
