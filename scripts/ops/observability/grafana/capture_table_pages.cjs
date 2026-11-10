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

function collectValueMappings(fieldConfig) {
  const pairs = [];
  const push = (list) => {
    for (const mapping of list || []) {
      if (!mapping || typeof mapping !== 'object') continue;
      if (mapping.type === 'value' && mapping.options && typeof mapping.options === 'object') {
        for (const [raw, cfg] of Object.entries(mapping.options)) {
          if (cfg && typeof cfg.text === 'string') pairs.push({type: 'value', raw, display: cfg.text});
        }
      }
      if (
        mapping.type === 'regex'
        && typeof mapping.options?.pattern === 'string'
        && typeof mapping.options?.result?.text === 'string'
      ) {
        pairs.push({
          type: 'regex',
          pattern: mapping.options.pattern,
          display: mapping.options.result.text,
        });
      }
    }
  };
  push(fieldConfig?.defaults?.mappings);
  for (const override of fieldConfig?.overrides || []) {
    for (const prop of override.properties || []) {
      if (prop?.id === 'mappings') push(prop.value);
    }
  }
  return pairs;
}

function inspectMatchesCell(observed, displayed, {noValue, valueMappings}) {
  if (observed === displayed) return {status: 'VERIFIED'};
  if (observed === '' && noValue === displayed) {
    return {status: 'VERIFIED_NO_VALUE_MAPPING', mapping: {raw: observed, display: displayed, type: 'noValue'}};
  }
  for (const mapping of valueMappings || []) {
    if (mapping.type === 'value' && mapping.raw === observed && mapping.display === displayed) {
      return {status: 'VERIFIED_VALUE_MAPPING', mapping: {raw: observed, display: displayed, type: 'value'}};
    }
    if (mapping.type === 'regex' && mapping.display === displayed) {
      try {
        if (new RegExp(mapping.pattern).test(observed)) {
          return {
            status: 'VERIFIED_VALUE_MAPPING',
            mapping: {raw: observed, display: displayed, type: 'regex', pattern: mapping.pattern},
          };
        }
      } catch {
        // Invalid dashboard regex is not a capture failure mode here.
      }
    }
  }
  return null;
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

async function captureInspectedValues(page, root, cells, {dir,index,outputDir,pngEvidence,timeout,noValue,valueMappings,seen,inspectCounter}) {
  const results=[];
  const known = seen instanceof Set ? seen : new Set(seen || []);
  const counter = inspectCounter || {n: 0};
  const values=[...new Set(cells.filter(c=>c.clipped && c.role!=='columnheader').map(c=>c.text))]
    .filter(text => !known.has(text));
  await sequential(values, async text => {
    // The accessible name also contains the Inspect button's label.
    const cell=root.locator('[role="gridcell"]').filter({hasText:new RegExp('^'+text.replace(/[.*+?^${}()|[\]\\]/g,String.raw`\$&`)+'$')}).first();
    if(!await cell.count()){
      // Leave unseen so a later scroll tile can still mount and Inspect this value.
      results.push({text,status:'CELL_NOT_MOUNTED'});return;
    }
    known.add(text);
    if(await cell.evaluate(el=>el.textContent)!==text)throw new Error('Selected cell differs from requested value');
    await cell.scrollIntoViewIfNeeded({timeout});
    await cell.hover();
    const inspect=cell.getByRole('button',{name:'Inspect value',exact:true});
    if(!await inspect.count()){
      results.push({text,status:'INSPECT_UNAVAILABLE'});return;
    }
    await inspect.click();
    try {
      await page.getByRole('tab',{name:'Plain text',exact:true}).waitFor({state:'visible',timeout});
      const dialog=page.getByRole('dialog').filter({has:page.getByRole('tab',{name:'Plain text',exact:true})});
      const value=dialog.locator('pre');
      await value.waitFor({state:'visible',timeout});
      const observed=await value.innerText();
      const match=inspectMatchesCell(observed, text, {noValue, valueMappings});
      if(!match)throw new Error('Inspect value differs from the captured table cell');
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
    if (panel.type !== 'table') return;
    const root = page.locator(`[data-viz-panel-key="panel-${panel.id}"]`).first();
    await root.scrollIntoViewIfNeeded({timeout});
    await root.waitFor({state:'visible',timeout});
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
  captureTablePages,
  captureInspectedValues,
  captureScrollTiles,
  mergeInspected,
  collectValueMappings,
  inspectMatchesCell,
};
