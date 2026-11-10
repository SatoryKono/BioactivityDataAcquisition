/** Observe every native pagination page; retain full cell text and link targets. */
const fs = require('node:fs');
const path = require('node:path');

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

async function captureScrollTiles(page, root, {dir,index,outputDir,pngEvidence,timeout}) {
  const grids=root.locator('[role="grid"]');
  const tiles=[];
  for(let g=0;g<await grids.count();g++) {
    const grid=grids.nth(g);
    const size=await grid.evaluate(el=>({w:el.clientWidth,h:el.clientHeight,
      sw:el.scrollWidth,sh:el.scrollHeight,x:el.scrollLeft,y:el.scrollTop}));
    if(size.sw<=size.w+2 && size.sh<=size.h+2)continue;
    if(size.w<=0 || size.h<=0)throw new Error('Table grid has no visible scroll viewport');
    const positions=(extent,viewport)=>{
      const result=[0],max=Math.max(0,extent-viewport);
      // Overlap retains sticky headers and rows crossing viewport boundaries.
      while(result.at(-1)<max)result.push(Math.min(max,result.at(-1)+Math.max(1,Math.floor(viewport/2))));
      return result;
    };
    try {
      for(const y of positions(size.sh,size.h))for(const x of positions(size.sw,size.w)){
        if(tiles.length>=1000)throw new Error('Table scroll capture exceeded 1000 tiles');
        await grid.evaluate((el,{x,y})=>{el.scrollLeft=x;el.scrollTop=y;},{x,y});
        await page.waitForTimeout(150);
        const evidence=await root.evaluate(tableEvidence);
        const file=path.join(dir,`page-${index}-scroll-${tiles.length+1}.png`);
        const bytes=await require('./native_browser_zoom.cjs').captureElementScreenshot(page,root,{path:file,animations:'disabled',timeout});
        tiles.push({grid:g,x,y,...evidence,file:path.relative(outputDir,file),...pngEvidence(bytes)});
      }
    } finally {
      await grid.evaluate((el,{x,y})=>{el.scrollLeft=x;el.scrollTop=y;},size);
    }
  }
  return tiles;
}

async function captureInspectedValues(page, root, cells, {dir,index,outputDir,pngEvidence,timeout}) {
  const results=[];
  const values=[...new Set(cells.filter(c=>c.clipped && c.role!=='columnheader').map(c=>c.text))];
  for(const text of values){
    // The accessible name also contains the Inspect button's label.
    const cell=root.locator('[role="gridcell"]').filter({hasText:text}).first();
    if(!await cell.count()){
      results.push({text,status:'CELL_NOT_MOUNTED'});continue;
    }
    await cell.scrollIntoViewIfNeeded({timeout});
    await cell.hover();
    const inspect=cell.getByRole('button',{name:'Inspect value',exact:true});
    if(!await inspect.count()){
      results.push({text,status:'INSPECT_UNAVAILABLE'});continue;
    }
    await inspect.click();
    try {
      await page.getByRole('tab',{name:'Plain text',exact:true}).waitFor({state:'visible',timeout});
      const value=page.getByText(text,{exact:true}).last();
      await value.waitFor({state:'visible',timeout});
      const observed=await value.innerText();
      if(observed!==text)throw new Error('Inspect value differs from the captured table cell');
      const file=path.join(dir,`page-${index}-inspect-${results.length+1}.png`);
      const bytes=await require('./native_browser_zoom.cjs').capturePageScreenshot(page,{path:file,animations:'disabled',timeout});
      results.push({text,observed,status:'VERIFIED',file:path.relative(outputDir,file),...pngEvidence(bytes)});
    } finally {
      await page.getByRole('button',{name:'Close',exact:true}).click();
    }
  }
  return results;
}
async function captureTablePages(page, {dashboard, outputDir, pngEvidence, timeout}) {
  const results = [];
  for (const panel of dashboard.tablePanels || dashboard.firstWindowPanels || []) {
    if (panel.type !== 'table') continue;
    const root = page.locator(`[data-viz-panel-key="panel-${panel.id}"]`).first();
    await root.scrollIntoViewIfNeeded({timeout});
    await root.waitFor({state:'visible',timeout});
    const next = root.getByRole('button', {name:'next page', exact:true});
    const paginated = (await next.count()) > 0;
    const previous = root.getByRole('button', {name:'previous page', exact:true});
    const pages = [];
    let complete = false;
    for (let index = 1; index <= 100; index++) {
      const evidence = await root.evaluate(tableEvidence);
      const dir=path.join(outputDir,'panels',dashboard.uid,String(panel.id));
      await fs.promises.mkdir(dir,{recursive:true});
      const file=path.join(dir,`page-${index}.png`);
      const bytes=await require('./native_browser_zoom.cjs').captureElementScreenshot(page,root,
        {path:file,animations:'disabled',timeout});
      const scrollTiles=await captureScrollTiles(page,root,{dir,index,outputDir,pngEvidence,timeout});
      const inspectedValues=await captureInspectedValues(page,root,
        [ ...evidence.cells, ...scrollTiles.flatMap(t=>t.cells)],{dir,index,outputDir,pngEvidence,timeout});
      pages.push({page:index,...evidence,scrollTiles,inspectedValues,file:path.relative(outputDir,file),...pngEvidence(bytes)});
      if (!paginated || await next.isDisabled()) { complete=true; break; }
      const before = await root.innerText();
      await next.focus();
      await page.keyboard.press('Enter');
      await page.waitForFunction(({id,before}) =>
        document.querySelector(`[data-viz-panel-key="panel-${id}"]`)?.innerText !== before,
        {id:panel.id,before},{timeout});
    }
    for (let i=0; paginated && i<pages.length && !await previous.isDisabled(); i++) {
      await previous.click(); await page.waitForTimeout(100);
    }
    results.push({panelId:panel.id,title:panel.title,paginated,status:complete?'COMPLETE':'NOT_PROVEN',
      method:'native next-page button activated with Enter; original first page restored',pages});
  }
  if (results.some(result => result.status !== 'COMPLETE')) {
    throw new Error('Table capture incomplete: pagination exceeded 100 pages');
  }
  return results;
}
module.exports={captureTablePages};
