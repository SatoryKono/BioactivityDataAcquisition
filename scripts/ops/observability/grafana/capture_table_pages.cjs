/** Observe every native pagination page; retain full cell text and link targets. */
const fs = require('node:fs');
const path = require('node:path');
async function captureTablePages(page, {dashboard, outputDir, pngEvidence, timeout}) {
  const results = [];
  for (const panel of dashboard.firstWindowPanels || []) {
    if (panel.type !== 'table') continue;
    const root = page.locator(`[data-viz-panel-key="panel-${panel.id}"]`).first();
    const next = root.getByRole('button', {name:'next page', exact:true});
    if (!await next.count()) {
      results.push({panelId:panel.id, status:'NOT_PAGINATED', pages:[]});
      continue;
    }
    const previous = root.getByRole('button', {name:'previous page', exact:true});
    const pages = [];
    let complete = false;
    for (let index = 1; index <= 100; index++) {
      const evidence = await root.evaluate(el => {
        const rect = node => { const r=node.getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height}; };
        return {cells:[...el.querySelectorAll('[role="cell"], [role="columnheader"]')].map(cell=>({
          role:cell.getAttribute('role'),text:cell.textContent,bbox:rect(cell),
          links:[...cell.querySelectorAll('a[href]')].map(a=>({text:a.textContent,href:a.href,title:a.title,tabIndex:a.tabIndex})),
        })), scrollers:[...el.querySelectorAll('.scrollbar-view,[data-testid*="scrollbar viewport"]')].map(s=>({
          bbox:rect(s),clientHeight:s.clientHeight,scrollHeight:s.scrollHeight,clientWidth:s.clientWidth,scrollWidth:s.scrollWidth,
        })), summary:(/\b\d+\s*-\s*\d+ of \d+ rows\b/).exec(el.innerText)?.[0] || null};
      });
      const dir=path.join(outputDir,'panels',dashboard.uid,String(panel.id));
      await fs.promises.mkdir(dir,{recursive:true});
      const file=path.join(dir,`page-${index}.png`);
      const bytes=await root.screenshot({path:file,animations:'disabled',timeout});
      pages.push({page:index,...evidence,file:path.relative(outputDir,file),...pngEvidence(bytes)});
      if (await next.isDisabled()) { complete=true; break; }
      await next.focus();
      await page.keyboard.press('Enter');
      await page.waitForTimeout(250);
    }
    for (let i=0; i<pages.length && !await previous.isDisabled(); i++) {
      await previous.click(); await page.waitForTimeout(100);
    }
    results.push({panelId:panel.id,status:complete?'COMPLETE':'NOT_PROVEN',
      method:'native next-page button activated with Enter; original first page restored',pages});
  }
  return results;
}
module.exports={captureTablePages};
