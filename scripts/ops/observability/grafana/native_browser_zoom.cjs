/** Native Chromium zoom in a disposable profile; never uses the user's browser. */
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

async function createNativeZoomContext(chromium, launchOptions = {}) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'bioetl-native-zoom-'));
  const extension = path.join(directory, 'extension');
  fs.mkdirSync(extension);
  fs.writeFileSync(path.join(extension, 'manifest.json'), JSON.stringify({
    manifest_version: 3, name: 'BioETL native browser zoom measurement', version: '1.0',
    permissions: ['tabs'], background: {service_worker: 'worker.js'},
  }));
  fs.writeFileSync(path.join(extension, 'worker.js'),
    'chrome.runtime.onInstalled.addListener(() => {});');
  const context = await chromium.launchPersistentContext(path.join(directory, 'profile'), {
    ...launchOptions, headless: true, channel: 'chromium', viewport: null,
    args: [...(launchOptions.args || []), '--window-size=1366,768',
      `--disable-extensions-except=${extension}`, `--load-extension=${extension}`],
  });
  const worker = context.serviceWorkers()[0] ||
    await context.waitForEvent('serviceworker', {timeout: 15000});
  async function setZoom(page, viewport, percent) {
    if (![100, 200].includes(percent)) throw new Error('Only 100% and 200% are supported');
    const tabId = await worker.evaluate(async url => {
      const matches = (await chrome.tabs.query({})).filter(tab => tab.url === url);
      if (matches.length !== 1) throw new Error('Native zoom requires one matching tab');
      return matches[0].id;
    }, page.url());
    await worker.evaluate(id => chrome.tabs.setZoom(id, 1), tabId);
    const cdp = await context.newCDPSession(page);
    const browserVersion = (await cdp.send('Browser.getVersion')).product;
    const {windowId} = await cdp.send('Browser.getWindowForTarget');
    // Calibrate the content viewport at 100%; retain real browser chrome.
    for (let attempt = 0; attempt < 3; attempt++) {
      const actual = await page.evaluate(() => ({innerWidth, innerHeight, outerWidth, outerHeight}));
      if (actual.innerWidth === viewport.width && actual.innerHeight === viewport.height) break;
      await cdp.send('Browser.setWindowBounds', {windowId, bounds: {
        width: actual.outerWidth + viewport.width - actual.innerWidth,
        height: actual.outerHeight + viewport.height - actual.innerHeight,
      }});
      await page.waitForTimeout(150);
    }
    await worker.evaluate(async ({id, scale}) => chrome.tabs.setZoom(id, scale),
      {id: tabId, scale: percent / 100});
    await page.waitForTimeout(300);
    const factor = await worker.evaluate(id => chrome.tabs.getZoom(id), tabId);
    const actual = await page.evaluate(() => ({innerWidth, innerHeight, outerWidth,
      outerHeight, devicePixelRatio, cssZoom: getComputedStyle(document.documentElement).zoom}));
    await cdp.detach();
    const expected = {width: Math.floor(viewport.width / factor), height: Math.floor(viewport.height / factor)};
    if (factor !== percent / 100 || actual.innerWidth !== expected.width || actual.innerHeight !== expected.height ||
        actual.devicePixelRatio !== factor || !['1', 'normal'].includes(actual.cssZoom)) {
      throw new Error(`Native browser zoom mismatch: ${JSON.stringify({factor, expected, actual})}`);
    }
    return {method: 'chrome.tabs.setZoom/getZoom; native content viewport; no device emulation',
      requestedPercent: percent, actualFactor: factor, physicalContentViewport: viewport, browserVersion, actual};
  }
  async function close() {
    await context.close();
    const resolved = fs.realpathSync(directory);
    const temporary = fs.realpathSync(os.tmpdir());
    if (path.dirname(resolved) !== temporary || !path.basename(resolved).startsWith('bioetl-native-zoom-')) {
      throw new Error('Refusing to clean a profile outside the owned temporary directory');
    }
    fs.rmSync(resolved, {recursive: true, force: true});
  }
  return {context, setZoom, close};
}

async function capturePageScreenshot(page, options) {
  if (!page.nativeZoomEvidence) return page.screenshot(options);
  const cdp = await page.context().newCDPSession(page);
  try {
    const parameters = {format: 'png', captureBeyondViewport: true};
    // CDP clip coordinates are device-independent screen pixels, while DOM
    // rectangles shrink in CSS pixels under native browser zoom. Keep scale=1:
    // rescaling a CSS-sized crop would magnify only a fraction of the viewport.
    if (options.clip) {
      const factor = page.nativeZoomEvidence.actualFactor;
      parameters.clip = Object.fromEntries(Object.entries(options.clip).map(([key, value]) => [key, value * factor]));
      parameters.clip.scale = 1;
    }
    const {data} = await cdp.send('Page.captureScreenshot', parameters);
    const bytes = Buffer.from(data, 'base64');
    if (options.path) await fs.promises.writeFile(options.path, bytes);
    return bytes;
  } finally {await cdp.detach();}
}

async function captureElementScreenshot(page, element, options) {
  if (!page.nativeZoomEvidence) return element.screenshot(options);
  await element.scrollIntoViewIfNeeded();
  const clip = await element.boundingBox();
  if (!clip) throw new Error('Native panel capture requires a visible bounding box');
  return capturePageScreenshot(page, {...options, clip});
}

module.exports = {createNativeZoomContext, capturePageScreenshot, captureElementScreenshot};
