/** Observe every native pagination page; retain full cell text and link targets. */
const fs = require('node:fs');
const path = require('node:path');

// A single browser is shared: each action must finish before the next starts.
const sequential = (items, action) => items.reduce(
  (pending, item) => pending.then(() => action(item)), Promise.resolve());

function tableEvidence(el) {
  const rect = node => {const r=node.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};};
  const grids = [...el.querySelectorAll('[role="grid"]')];
  return {
    cells:[...el.querySelectorAll('[role="cell"], [role="gridcell"], [role="columnheader"]')].map(cell=>({
      role:cell.getAttribute('role'),text:cell.textContent,bbox:rect(cell),
      row:cell.closest('[role="row"]')?.getAttribute('aria-rowindex'),
      column:cell.getAttribute('aria-colindex'),
      clipped:cell.scrollWidth>cell.clientWidth+2 || cell.scrollHeight>cell.clientHeight+2,
      links:[...cell.querySelectorAll('a[href]')].map(a=>({text:a.textContent,href:a.href,title:a.title,tabIndex:a.tabIndex})),
    })),
    scrollers:[...el.querySelectorAll('[role="grid"],.scrollbar-view,[data-testid*="scrollbar viewport"]')].map(s=>({
      grid:grids.indexOf(s),bbox:rect(s),clientHeight:s.clientHeight,scrollHeight:s.scrollHeight,clientWidth:s.clientWidth,scrollWidth:s.scrollWidth,
      scrollTop:s.scrollTop,scrollLeft:s.scrollLeft,
    })),
    summary:(/\b\d+\s*[-–]\s*\d+ of \d+ rows\b/).exec(el.innerText)?.[0] || null,
  };
}

function mergeInspected(existing, next) {
  const byText = new Map(existing.map(item => [item.text, item]));
  for (const item of next) {
    const prior = byText.get(item.text);
    if (!prior || prior.status === 'CELL_NOT_MOUNTED') byText.set(item.text, item);
  }
  return [...byText.values()];
}

function valueMappingEntries(mapping) {
  if (mapping?.type !== 'value' || typeof mapping.options !== 'object' || !mapping.options) {
    return [];
  }
  return Object.entries(mapping.options)
    .filter(([, cfg]) => cfg && typeof cfg.text === 'string')
    .map(([raw, cfg]) => ({type: 'value', raw, display: cfg.text}));
}

function regexMappingEntry(mapping) {
  const pattern = mapping?.options?.pattern;
  const display = mapping?.options?.result?.text;
  if (mapping?.type !== 'regex' || typeof pattern !== 'string' || typeof display !== 'string') {
    return null;
  }
  return {type: 'regex', pattern, display};
}

function appendMappingList(pairs, list) {
  for (const mapping of list || []) {
    if (!mapping || typeof mapping !== 'object') continue;
    pairs.push(...valueMappingEntries(mapping));
    const regex = regexMappingEntry(mapping);
    if (regex) pairs.push(regex);
  }
}

function collectValueMappings(fieldConfig) {
  const pairs = [];
  appendMappingList(pairs, fieldConfig?.defaults?.mappings);
  for (const override of fieldConfig?.overrides || []) {
    for (const prop of override.properties || []) {
      if (prop?.id === 'mappings') appendMappingList(pairs, prop.value);
      if (prop?.id === 'noValue' && typeof prop.value === 'string') {
        pairs.push({type:'value',raw:'',display:prop.value});
      }
    }
  }
  return pairs;
}

function fieldFormatFromProps(properties, fallback = {}) {
  const props = Object.fromEntries(
    (properties || [])
      .filter((prop) => prop && typeof prop.id === 'string')
      .map((prop) => [prop.id, prop.value]),
  );
  const unit = props.unit ?? fallback.unit;
  if (!unit || unit === 'none') return null;
  const decimals = props.decimals ?? fallback.decimals;
  return {
    unit,
    decimals: Number.isInteger(decimals) ? decimals : null,
  };
}

function collectFieldFormats(fieldConfig) {
  const defaults = fieldConfig?.defaults || {};
  const formats = [];
  const seen = new Set();
  const push = (fmt) => {
    if (!fmt) return;
    const key = `${fmt.unit}:${fmt.decimals}`;
    if (seen.has(key)) return;
    seen.add(key);
    formats.push(fmt);
  };
  push(fieldFormatFromProps(
    Object.entries(defaults)
      .filter(([id]) => id === 'unit' || id === 'decimals')
      .map(([id, value]) => ({id, value})),
  ));
  for (const override of fieldConfig?.overrides || []) {
    push(fieldFormatFromProps(override.properties, {
      unit: defaults.unit,
      decimals: defaults.decimals,
    }));
  }
  return formats;
}

function unitDisplayLabel(unit) {
  if (!unit || unit === 'none' || unit === 'short') return null;
  if (unit.startsWith('time:')) return null;
  if (unit.startsWith('suffix:')) return unit.slice('suffix:'.length);
  if (unit.startsWith('prefix:')) return null;
  if (unit === 'percent') return '%';
  return unit;
}

function trimFractionalZeros(fixed) {
  const dot = fixed.indexOf('.');
  if (dot < 0) return fixed;
  let end = fixed.length;
  while (end > dot + 1 && fixed.charAt(end - 1) === '0') end -= 1;
  if (end === dot + 1) return fixed.slice(0, dot);
  return fixed.slice(0, end);
}

function unitDisplayCandidates(raw, fmt) {
  if (fmt.unit === 'time:YYYY-MM-DD HH:mm' && fmt.timeZone && fmt.timeZone !== 'browser' && Number.isFinite(raw)) {
    try {
      const parts = Object.fromEntries(new Intl.DateTimeFormat('en-GB', {timeZone:fmt.timeZone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(raw)).map(part=>[part.type,part.value]));
      return [`${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}`];
    } catch { return []; }
  }
  const label = unitDisplayLabel(fmt.unit);
  if (label == null || !Number.isFinite(raw)) return [];
  const places = fmt.decimals == null ? [0, 1, 2, 3] : [fmt.decimals];
  const out = new Set();
  for (const decimals of places) {
    const fixed = decimals === 0 ? String(Math.round(raw)) : raw.toFixed(decimals);
    const trimmed = trimFractionalZeros(fixed);
    for (const body of new Set([fixed, trimmed, String(raw)])) {
      out.add(`${body} ${label}`);
      out.add(`${body}${label}`);
    }
  }
  return [...out];
}

function matchExactOrNoValue(observed, displayed, noValue) {
  if (observed === displayed) return {status: 'VERIFIED'};
  if (observed === '' && noValue === displayed) {
    return {
      status: 'VERIFIED_NO_VALUE_MAPPING',
      mapping: {raw: observed, display: displayed, type: 'noValue'},
    };
  }
  return null;
}

function matchValueMapping(observed, displayed, mapping) {
  if (mapping.type !== 'value' || mapping.raw !== observed || mapping.display !== displayed) {
    return null;
  }
  return {
    status: 'VERIFIED_VALUE_MAPPING',
    mapping: {raw: observed, display: displayed, type: 'value'},
  };
}

function matchRegexMapping(observed, displayed, mapping) {
  if (mapping.type !== 'regex' || mapping.display !== displayed) return null;
  try {
    if (!new RegExp(mapping.pattern).test(observed)) return null;
  } catch {
    // Invalid dashboard regex is not a capture failure mode here.
    return null;
  }
  return {
    status: 'VERIFIED_VALUE_MAPPING',
    mapping: {raw: observed, display: displayed, type: 'regex', pattern: mapping.pattern},
  };
}

function matchUnitFormat(observed, displayed, fieldFormats) {
  const raw = Number(String(observed).trim());
  if (!Number.isFinite(raw)) return null;
  const text = String(displayed).trim();
  for (const fmt of fieldFormats || []) {
    if (unitDisplayCandidates(raw, fmt).includes(text)) {
      return {
        status: 'VERIFIED_UNIT_FORMAT',
        mapping: {raw: observed, display: displayed, type: 'unit', unit: fmt.unit},
      };
    }
  }
  return null;
}

function inspectMatchesCell(observed, displayed, {noValue, valueMappings, fieldFormats}) {
  const direct = matchExactOrNoValue(observed, displayed, noValue);
  if (direct) return direct;
  for (const mapping of valueMappings || []) {
    const matched = matchValueMapping(observed, displayed, mapping)
      || matchRegexMapping(observed, displayed, mapping);
    if (matched) return matched;
  }
  return matchUnitFormat(observed, displayed, fieldFormats);
}

async function captureScrollTiles(page, root, {dir,index,outputDir,pngEvidence,timeout,inspect}) {
  const grids=root.locator('[role="grid"]');
  const tiles=[];
  let inspectedValues=[];
  await sequential(Array.from({length:await grids.count()},(_,i)=>i), async g => {
    const grid=grids.nth(g);
    const size=await grid.evaluate(el=>({w:el.clientWidth,h:el.clientHeight,
      sw:el.scrollWidth,sh:el.scrollHeight,x:el.scrollLeft,y:el.scrollTop}));
    if(size.sw<=size.w+2 && size.sh<=size.h+2)return;
    if(size.w<=0 || size.h<=0)throw new Error('Table grid has no visible scroll viewport');
    const positions=(extent,viewport)=>{
      const result=[0],max=Math.max(0,extent-viewport);
      // Overlap retains sticky headers and rows crossing viewport boundaries.
      while(result.at(-1)<max)result.push(Math.min(max,result.at(-1)+Math.max(1,Math.floor(viewport/2))));
      return result;
    };
    try {
      const coordinates=positions(size.sh,size.h).flatMap(y=>positions(size.sw,size.w).map(x=>({x,y})));
      await sequential(coordinates, async ({x,y}) => {
        if(tiles.length>=1000)throw new Error('Table scroll capture exceeded 1000 tiles');
        await grid.evaluate((el,{x,y})=>{el.scrollLeft=x;el.scrollTop=y;},{x,y});
        await page.waitForTimeout(150);
        const evidence=await root.evaluate(tableEvidence);
        // Tile PNG must match recorded scroll offsets before Inspect moves the grid.
        const file=path.join(dir,`page-${index}-scroll-${tiles.length+1}.png`);
        const bytes=await require('./native_browser_zoom.cjs').captureElementScreenshot(page,root,{path:file,animations:'disabled',timeout});
        tiles.push({grid:g,x,y,...evidence,file:path.relative(outputDir,file),...pngEvidence(bytes),viewportTiles:(bytes.viewportTiles || []).map(t=>({...t,file:path.relative(outputDir,t.file)}))});
        // Inspect while virtualized rows for this tile are still mounted.
        if (inspect) {
          inspectedValues = mergeInspected(
            inspectedValues,
            await inspect(evidence.cells),
          );
          await grid.evaluate((el,{x,y})=>{el.scrollLeft=x;el.scrollTop=y;},{x,y});
        }
      });
    } finally {
      await grid.evaluate((el,{x,y})=>{el.scrollLeft=x;el.scrollTop=y;},size);
    }
  });
  return {tiles, inspectedValues};
}

function cellTextPattern(text) {
  // Hover adds the Inspect control; reject other values sharing this prefix.
  return new RegExp('^' + text.replace(/[.*+?^${}()|[\]\\]/g, String.raw`\$&`) + '(?:\\s*Inspect value)?$');
}

async function captureInspectedValues(page, root, cells, {dir,index,outputDir,pngEvidence,timeout,noValue,valueMappings,fieldFormats,seen,inspectCounter}) {
  const results=[];
  const known = seen instanceof Set ? seen : new Set(seen || []);
  const counter = inspectCounter || {n: 0};
  const values=[...new Set(cells.filter(c=>c.clipped && c.role!=='columnheader').map(c=>c.text))]
    .filter(text => !known.has(text));
  await sequential(values, async text => {
    // Dismiss the preceding cell link popover before moving to another value.
    await page.keyboard.press('Escape');
    await page.mouse.move(0, 0);
    await page.waitForTimeout(150);
    // The accessible name also contains the Inspect button's label.
    const cell=root.locator('[role="cell"], [role="gridcell"]').filter({hasText:cellTextPattern(text)}).first();
    if(!await cell.count()){
      // Leave unseen so a later scroll tile can still mount and Inspect this value.
      results.push({text,status:'CELL_NOT_MOUNTED'});return;
    }
    known.add(text);
    if(await cell.evaluate(el=>{const copy=el.cloneNode(true);copy.querySelectorAll('button').forEach(b=>b.remove());return copy.textContent;})!==text)throw new Error('Selected cell differs from requested value');
    await cell.scrollIntoViewIfNeeded({timeout});
    await cell.hover();
    const inspect=cell.getByRole('button',{name:'Inspect value',exact:true});
    if(!await inspect.count()){
      results.push({text,status:'INSPECT_UNAVAILABLE'});return;
    }
    // Sticky neighbouring cells can cover this virtualized action on phones.
    // Activate the actual accessible control through its supported keyboard path.
    await inspect.press('Enter');
    try {
      await page.getByRole('tab',{name:'Plain text',exact:true}).waitFor({state:'visible',timeout});
      const dialog=page.getByRole('dialog').filter({has:page.getByRole('tab',{name:'Plain text',exact:true})});
      const value=dialog.locator('pre');
      await value.waitFor({state:'visible',timeout});
      const observed=await value.innerText();
      const match=inspectMatchesCell(observed, text, {noValue, valueMappings, fieldFormats});
      if(!match)throw new Error(`Inspect value differs from the captured table cell: ${JSON.stringify({text,observed})}`);
      counter.n += 1;
      const file=path.join(dir,`page-${index}-inspect-${counter.n}.png`);
      const bytes=await require('./native_browser_zoom.cjs').capturePageScreenshot(page,{path:file,animations:'disabled',timeout});
      results.push({
        text,observed,status:match.status,
        ...(match.mapping ? {mapping: match.mapping} : {}),
        file:path.relative(outputDir,file),...pngEvidence(bytes),
        viewportTiles:(bytes.viewportTiles || []).map(t=>({...t,file:path.relative(outputDir,t.file)})),
      });
    } finally {
      await page.getByRole('button',{name:'Close',exact:true}).click();
    }
  });
  return results;
}
async function captureTablePages(page, {dashboard, outputDir, pngEvidence, timeout}) {
  // PNG capture may legitimately be unlimited; UI transitions never may be.
  const transitionTimeout = Number.isFinite(timeout) && timeout > 0 ? timeout : 30000;
  const results = [];
  await sequential(dashboard.tablePanels || dashboard.firstWindowPanels || [], async panel => {
    if (!['table','bioetl-selectorshell-panel'].includes(panel.type)) return;
    const root = page.locator(`[data-viz-panel-key="panel-${panel.id}"]`).first();
    await root.scrollIntoViewIfNeeded({timeout});
    await root.waitFor({state:'visible',timeout});
    if(panel.type==='bioetl-selectorshell-panel'){
      const compact=await require('./capture_adaptive_table_pages.cjs').captureAdaptivePages(page,root,{panel,dashboard,outputDir,pngEvidence,timeout:transitionTimeout});
      if(compact){results.push(compact);return;}
    }
    const next = root.getByRole('button', {name:'next page', exact:true});
    const paginated = (await next.count()) > 0;
    const previous = root.getByRole('button', {name:'previous page', exact:true});
    const pages = [];
    async function capturePage(index) {
      if(index>100)throw new Error('Table capture incomplete: pagination exceeded 100 pages');
      const evidence = await root.evaluate(tableEvidence);
      const dir=path.join(outputDir,'panels',dashboard.uid,String(panel.id));
      await fs.promises.mkdir(dir,{recursive:true});
      const file=path.join(dir,`page-${index}.png`);
      const bytes=await require('./native_browser_zoom.cjs').captureElementScreenshot(page,root,
        {path:file,animations:'disabled',timeout});
      const seen = new Set();
      const inspectCounter = {n: 0};
      const inspectOpts = {
        dir,index,outputDir,pngEvidence,timeout,
        noValue:panel.noValue,
        valueMappings:panel.valueMappings || [],
        fieldFormats:(panel.fieldFormats || []).map(fmt=>({...fmt,timeZone:new URL(page.url()).searchParams.get('timezone')})),
        seen,inspectCounter,
      };
      // Inspect the initial viewport before any scroll restore can unmount rows.
      let inspectedValues = await captureInspectedValues(page,root,evidence.cells,inspectOpts);
      const scrollCapture = await captureScrollTiles(page,root,{
        dir,index,outputDir,pngEvidence,timeout,
        inspect: cells => captureInspectedValues(page,root,cells,inspectOpts),
      });
      inspectedValues = mergeInspected(inspectedValues, scrollCapture.inspectedValues);
      const incompleteInspect = inspectedValues.some(
        item => item.status === 'CELL_NOT_MOUNTED' || item.status === 'INSPECT_UNAVAILABLE',
      );
      pages.push({
        page:index,...evidence,scrollTiles:scrollCapture.tiles,inspectedValues,
        file:path.relative(outputDir,file),...pngEvidence(bytes),
        viewportTiles:(bytes.viewportTiles || []).map(t=>({...t,file:path.relative(outputDir,t.file)})),
      });
      if (!paginated || await next.isDisabled()) {
        return {incompleteInspect};
      }
      const before = await root.innerText();
      await next.focus();
      await page.keyboard.press('Enter');
      await page.waitForFunction(({id,before}) =>
        document.querySelector(`[data-viz-panel-key="panel-${id}"]`)?.innerText !== before,
        {id:panel.id,before},{timeout:transitionTimeout});
      const nested = await capturePage(index+1);
      return {incompleteInspect: incompleteInspect || nested.incompleteInspect};
    }
    async function restorePage(remaining) {
      if(remaining<=0 || await previous.isDisabled())return;
      await previous.click(); await page.waitForTimeout(100);
      await restorePage(remaining-1);
    }
    let incompleteInspect = false;
    try {
      const outcome = await capturePage(1);
      incompleteInspect = Boolean(outcome?.incompleteInspect);
    }
    finally {if(paginated)await restorePage(100);}
    results.push({
      panelId:panel.id,title:panel.title,paginated,
      status: incompleteInspect ? 'INCOMPLETE_INSPECT' : 'COMPLETE',
      method:'native next-page button activated with Enter; original first page restored; Inspect runs before scroll restore',
      pages,
    });
  });
  return results;
}
module.exports={
  cellTextPattern,
  captureTablePages,
  captureInspectedValues,
  captureScrollTiles,
  mergeInspected,
  collectValueMappings,
  collectFieldFormats,
  inspectMatchesCell,
};
