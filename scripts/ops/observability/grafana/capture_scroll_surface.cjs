/** Capture a scrolling dashboard without changing its layout viewport. */
const fs = require('node:fs');
const path = require('node:path');

function visiblePanelGeometryFromDom() {
  return [...document.querySelectorAll('[data-viz-panel-key]')].flatMap(el => {
    const r = el.getBoundingClientRect();
    if (r.bottom <= 0 || r.top >= innerHeight || !r.width || !r.height) return [];
    return [{panel: el.dataset.vizPanelKey, bbox: {x:r.x,y:r.y,width:r.width,height:r.height},
      clientWidth:el.clientWidth,scrollWidth:el.scrollWidth,clientHeight:el.clientHeight,scrollHeight:el.scrollHeight}];
  });
}

function tileIsStable(evidence, scrollTop, scrollAfter, verify) {
  if (scrollTop !== scrollAfter) return false;
  if (!verify) return true;
  const ids = terminal => terminal.panelStates.map(panel => panel.id).sort((a,b)=>a-b);
  return JSON.stringify(ids(evidence.terminal)) === JSON.stringify(ids(evidence.terminalAfter));
}

async function captureStableTile(page, {tileDir, index, timeout, measure, verify, pngEvidence}) {
  const deadline = Date.now() + timeout;
  const rejected = [];
  let attempt = 0;
  while (Date.now() < deadline) {
    const evidence = await measure();
    const panels = await page.evaluate(visiblePanelGeometryFromDom);
    const file = path.join(tileDir, `${String(index).padStart(3,'0')}-${attempt}.png`);
    const scrollTop = await page.evaluate(() => document.querySelector('[data-bioetl-capture-scroll]').scrollTop);
    const bytes = await require('./native_browser_zoom.cjs').capturePageScreenshot(page,
      {path:file,timeout,animations:'disabled',caret:'hide'});
    if (verify) evidence.terminalAfter = await verify();
    const scrollAfter = await page.evaluate(() => document.querySelector('[data-bioetl-capture-scroll]').scrollTop);
    const result = {file, ...pngEvidence(bytes), panels, evidence, scrollTop};
    if (tileIsStable(evidence, scrollTop, scrollAfter, verify)) {
      return {...result, rejected};
    }
    rejected.push({...result, reason:'visible panel set changed across capture'});
    await fs.promises.writeFile(path.join(tileDir, `${index}-rejected.json`), JSON.stringify(rejected));
    attempt++;
  }
  throw new Error('Visible panel set did not stabilize within the capture timeout');
}

function compositionSlices(surface, tiles) {
  const canvasHeight = Math.round((surface.top + surface.scrollHeight) * surface.scale);
  let covered = 0;
  const slices = tiles.map((tile, index) => {
    const offset = Math.round(tile.scrollTop * surface.scale);
    const sourceY = index === 0 ? 0 : covered - offset;
    const minimum = index === 0 ? 0 : Math.ceil(surface.stickyBottom * surface.scale);
    if (sourceY < minimum || sourceY >= tile.height) {
      throw new Error('Scroll tiles cannot cover the document without sticky chrome or a gap');
    }
    const height = Math.min(tile.height - sourceY, canvasHeight - covered);
    if (height <= 0) throw new Error('Scroll tile adds no document pixels');
    const slice = {sourceY, destinationY: covered, height};
    covered += height;
    return slice;
  });
  if (covered !== canvasHeight) throw new Error('Scroll tiles leave an incomplete document');
  return {canvasHeight, slices};
}

async function captureScrollSurface(page, {filePath, timeout, pngEvidence, measure, verify}) {
  const surface = await page.evaluate(() => {
    const candidates = [...document.querySelectorAll('*')].filter(el => {
      const r=el.getBoundingClientRect();
      return r.width>0 && r.height>0 && el.clientHeight<=innerHeight+2 && el.scrollHeight>el.clientHeight+2
        && el.querySelectorAll('[data-viz-panel-key]').length>1;
    }).sort((a,b)=>b.querySelectorAll('[data-viz-panel-key]').length-a.querySelectorAll('[data-viz-panel-key]').length);
    let el=candidates.find(candidate=>{
      const before=candidate.scrollTop;candidate.scrollTop=1;
      const scrollable=candidate.scrollTop>0;candidate.scrollTop=before;
      return scrollable;
    });
    if (!el) {
      // A short dashboard can fit completely in the requested viewport.
      // Accept that case only when every mounted panel is inside the frame.
      const panels = [...document.querySelectorAll('[data-viz-panel-key]')];
      const fits = panels.length > 0 && panels.every(panel => {
        const box = panel.getBoundingClientRect();
        return box.width > 0 && box.height > 0 && box.top >= 0 && box.bottom <= innerHeight + 2;
      });
      if (!fits) throw new Error('No programmatically scrollable dashboard container');
      el = document.scrollingElement;
    }
    el.dataset.bioetlCaptureScroll='true';
    el.scrollTop=0;
    const r=el.getBoundingClientRect();
    const stickyBottom = [...el.querySelectorAll('*')].reduce((bottom,node)=>{
      const style=getComputedStyle(node),box=node.getBoundingClientRect();
      return ['sticky','fixed'].includes(style.position) && box.top>=0 && box.top<innerHeight/2 && box.width>innerWidth/2
        ? Math.max(bottom,Math.min(box.bottom,innerHeight/2)) : bottom;
    },Math.max(0,r.top));
    return {top:Math.max(0,r.top),stickyBottom,clientHeight:Math.min(el.clientHeight,innerHeight-Math.max(0,r.top)),
      scrollHeight:el.scrollHeight,elementClientHeight:el.clientHeight,layoutViewport:{width:innerWidth,height:innerHeight},scale:devicePixelRatio};
  });
  if (!Number.isFinite(surface.clientHeight) || surface.clientHeight<=0) throw new Error('No measurable dashboard scroll surface');
  const tileDir=filePath.replace(/\.png$/,'-tiles');
  await fs.promises.mkdir(tileDir,{recursive:true});
  await fs.promises.writeFile(path.join(tileDir,'surface.json'),JSON.stringify(surface,null,2));
  const tiles=[];
  let previous=-1;
  const visibleHeight=surface.clientHeight-(surface.stickyBottom-surface.top);
  if(!Number.isFinite(visibleHeight) || visibleHeight<=0)throw new Error('Sticky chrome covers scroll surface');
  // Keep toolbar shadows inside the overlap rather than copying them over content.
  const overlap=Math.min(64,Math.floor(visibleHeight/4));
  let target=0;
  for (;;) {
    let actual=await page.evaluate(y=>{
      const el=document.querySelector('[data-bioetl-capture-scroll]');el.scrollTop=y;return el.scrollTop;
    },target);
    if(actual<=previous)throw new Error(`Dashboard scroll capture stalled at ${actual}; surface=${JSON.stringify(surface)}`);
    previous=actual;
    await page.waitForTimeout(750);
    const tile = await captureStableTile(page, {tileDir,index:tiles.length,timeout,measure,verify,pngEvidence});
    actual = tile.scrollTop;
    tiles.push({...tile,file:path.relative(path.dirname(filePath),tile.file)});
    if(actual+surface.clientHeight>=surface.scrollHeight-2)break;
    const next=Math.min(actual+visibleHeight-overlap,surface.scrollHeight-surface.clientHeight);
    if(next<=actual)throw new Error('Dashboard scroll capture made no progress');
    target=next;
  }
  const composition=compositionSlices(surface,tiles);
  const buffers=await Promise.all(tiles.map(t=>fs.promises.readFile(path.join(path.dirname(filePath),t.file))));
  const compositor=await page.context().newPage();
  try {
    const png=await compositor.evaluate(async({composition,tiles,images})=>{
      const canvas=document.createElement('canvas');canvas.width=tiles[0].width;
      canvas.height=composition.canvasHeight;
      const context=canvas.getContext('2d');
      for(let i=0;i<images.length;i++){
        const img=new Image();img.src='data:image/png;base64,'+images[i];await img.decode();
        const {sourceY,destinationY,height}=composition.slices[i];
        context.drawImage(img,0,sourceY,img.width,height,0,destinationY,img.width,height);
      }
      return canvas.toDataURL('image/png').split(',')[1];
    },{composition,tiles,images:buffers.map(b=>b.toString('base64'))});
    await fs.promises.writeFile(filePath,Buffer.from(png,'base64'));
  } finally {await compositor.close();}
  await page.evaluate(()=>{
    const el=document.querySelector('[data-bioetl-capture-scroll]');el.scrollTop=0;delete el.dataset.bioetlCaptureScroll;
  });
  return {method:'overlapping vertical tiles; each document row copied once; original tiles retained',surface,overlap,composition,tiles};
}
module.exports={captureScrollSurface,compositionSlices};
