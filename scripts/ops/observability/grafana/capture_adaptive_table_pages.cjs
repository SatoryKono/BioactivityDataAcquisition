/** Observe every compact record and its full details; never infer hidden rows. */
const fs = require('node:fs');
const path = require('node:path');

async function captureAdaptivePages(page, root, {panel, dashboard, outputDir, pngEvidence, timeout}) {
  const compact = root.locator('[data-bioetl-adaptive-table="compact"]');
  if (await compact.count() === 0) {
    if(await root.locator('[data-bioetl-adaptive-table="wide"]').count()) return null;
    const text=await root.innerText();
    if(/unexpected error|plugin not found|error loading|error rendering/i.test(text))throw new Error('Adaptive panel frontend failed');
    return {panelId:panel.id,title:panel.title,paginated:false,status:'TERMINAL_STATE',method:'Terminal state observed; tabular row coverage is not asserted',terminalText:text,pages:[]};
  }
  const isRuns = panel.presentationMode === 'runs';
  const next = root.getByRole('button', {name:isRuns ? 'Next run' : 'Next row', exact:true});
  const previous = root.getByRole('button', {name:isRuns ? 'Previous run' : 'Previous row', exact:true});
  const paginated = (await next.count()) > 0;
  const pages = [];
  const dir = path.join(outputDir, 'panels', dashboard.uid, String(panel.id));
  await fs.promises.mkdir(dir, {recursive:true});
  try {
    for (let index=1; index<=100; index++) {
      const evidence = await compact.evaluate(el => ({
        entries:[...el.querySelectorAll('tbody tr')].map(row => ({
          label:row.querySelector('th')?.textContent.replace(/\s*⋯\s*$/, '').trim(),
          value:row.querySelector('td')?.textContent,
          clipped:[...row.querySelectorAll('th,td')].some(cell => cell.scrollWidth>cell.clientWidth+2 || cell.scrollHeight>cell.clientHeight+2),
          links:[...row.querySelectorAll('a[href]')].map(a=>({text:a.textContent,href:a.href,title:a.title})),
        })),
        summary:el.querySelector('nav span')?.textContent || null,
      }));
      if(evidence.entries.some(item=>item.clipped)) throw new Error('Compact table contains a clipped field');
      const file=path.join(dir,`record-${index}.png`);
      const bytes=await require('./native_browser_zoom.cjs').captureElementScreenshot(page,root,{path:file,animations:'disabled',timeout});
      const detailButton = root.getByRole('button',{name:paginated ? 'Details' : 'Open full details',exact:true});
      await detailButton.click();
      const modal=page.getByRole('dialog',{name:isRuns ? 'Run details' : 'Full context',exact:true});
      await modal.waitFor({state:'visible',timeout});
      let details;
      try {
        details=await modal.evaluate(el=>({
          text:el.innerText,
          entries:[...el.querySelectorAll('dl dt')].map(dt=>({label:dt.textContent,value:dt.nextElementSibling?.textContent})),
          links:[...el.querySelectorAll('a[href]')].map(a=>({text:a.textContent,href:a.href})),
        }));
        if(isRuns){
          const fullId=details.entries.find(item=>item.label==='Full Run ID')?.value;
          if(!fullId || fullId==='-')throw new Error('Full Run ID missing from compact details');
          for(const link of details.links){
            const url=new URL(link.href);
            for(const key of ['var-run_id','run_id']){
              if(url.searchParams.has(key) && url.searchParams.get(key)!==fullId)throw new Error('Compact handoff has a different Run ID');
            }
          }
        }
      } finally {
        await modal.getByRole('button',{name:'Close',exact:true}).last().click();
        await modal.waitFor({state:'hidden',timeout});
      }
      pages.push({page:index,...evidence,details,file:path.relative(outputDir,file),...pngEvidence(bytes)});
      if(!paginated || await next.isDisabled())break;
      if(index===100)throw new Error('Compact pagination exceeded 100 records');
      const before=await compact.innerText();
      await next.click();
      await page.waitForFunction(({id,before})=>document.querySelector(`[data-viz-panel-key="panel-${id}"] [data-bioetl-adaptive-table="compact"]`)?.innerText!==before,{id:panel.id,before},{timeout});
    }
  } finally {
    if(paginated){
      for(let remaining=100; remaining>0 && !(await previous.isDisabled()); remaining--)await previous.click();
    }
  }
  return {panelId:panel.id,title:panel.title,paginated,status:'COMPLETE',method:'Every compact record and full-detail dialog observed; identity handoffs verified; first record restored',pages};
}

module.exports={captureAdaptivePages};
