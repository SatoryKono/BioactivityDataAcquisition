/** Capture a scrolling dashboard without changing its layout viewport. */
const fs = require('node:fs');
const path = require('node:path');

async function captureScrollSurface(page, {filePath, timeout, pngEvidence, measure}) {
  const surface = await page.evaluate(() => {
    const candidates = [...document.querySelectorAll('*')].filter(el => {
      const r=el.getBoundingClientRect();
      return r.width>0 && r.height>0 && el.clientHeight<=innerHeight+2 && el.scrollHeight>el.clientHeight+2
        && el.querySelectorAll('[data-viz-panel-key]').length>1;
    }).sort((a,b)=>b.querySelectorAll('[data-viz-panel-key]').length-a.querySelectorAll('[data-viz-panel-key]').length);
    const el=candidates.find(candidate=>{
      const before=candidate.scrollTop;candidate.scrollTop=1;
      const scrollable=candidate.scrollTop>0;candidate.scrollTop=before;
      return scrollable;
    });
    if(!el)throw new Error('No programmatically scrollable dashboard container');
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
  let target=0;
  for (;;) {
    const actual=await page.evaluate(y=>{
      const el=document.querySelector('[data-bioetl-capture-scroll]');el.scrollTop=y;return el.scrollTop;
    },target);
    if(actual<=previous)throw new Error(`Dashboard scroll capture stalled at ${actual}; surface=${JSON.stringify(surface)}`);
    previous=actual;
    await page.waitForTimeout(750);
    const evidence=await measure();
    const panels=await page.evaluate(()=>[...document.querySelectorAll('[data-viz-panel-key]')].flatMap(el=>{
      const r=el.getBoundingClientRect();
      if(r.bottom<=0||r.top>=innerHeight||!r.width||!r.height)return [];
      return [{panel:el.dataset.vizPanelKey,bbox:{x:r.x,y:r.y,width:r.width,height:r.height},
        clientWidth:el.clientWidth,scrollWidth:el.scrollWidth,clientHeight:el.clientHeight,scrollHeight:el.scrollHeight}];
    }));
    const file=path.join(tileDir,`${String(tiles.length).padStart(3,'0')}.png`);
    const bytes=await page.screenshot({path:file,timeout,animations:'disabled',caret:'hide'});
    tiles.push({file:path.relative(path.dirname(filePath),file),scrollTop:actual,...pngEvidence(bytes),panels,evidence});
    if(actual+surface.clientHeight>=surface.scrollHeight-2)break;
    const next=Math.min(actual+visibleHeight,surface.scrollHeight-surface.clientHeight);
    if(next<=actual)throw new Error('Dashboard scroll capture made no progress');
    target=next;
  }
  const buffers=await Promise.all(tiles.map(t=>fs.promises.readFile(path.join(path.dirname(filePath),t.file))));
  const compositor=await page.context().newPage();
  try {
    const png=await compositor.evaluate(async({surface,tiles,images})=>{
      const canvas=document.createElement('canvas');canvas.width=tiles[0].width;
      canvas.height=Math.round((surface.top+surface.scrollHeight)*surface.scale);
      const context=canvas.getContext('2d');
      for(let i=0;i<images.length;i++){
        const img=new Image();img.src='data:image/png;base64,'+images[i];await img.decode();
        if(i===0)context.drawImage(img,0,0);
        else {
          const top=Math.round(surface.stickyBottom*surface.scale);
          const height=Math.min(Math.round((surface.clientHeight-surface.stickyBottom+surface.top)*surface.scale),img.height-top);
          context.drawImage(img,0,top,img.width,height,0,Math.round((surface.stickyBottom+tiles[i].scrollTop)*surface.scale),img.width,height);
        }
      }
      return canvas.toDataURL('image/png').split(',')[1];
    },{surface,tiles,images:buffers.map(b=>b.toString('base64'))});
    await fs.promises.writeFile(filePath,Buffer.from(png,'base64'));
  } finally {await compositor.close();}
  await page.evaluate(()=>{
    const el=document.querySelector('[data-bioetl-capture-scroll]');el.scrollTop=0;delete el.dataset.bioetlCaptureScroll;
  });
  return {method:'vertical tiles at fixed browser viewport; original tiles retained',surface,tiles};
}
module.exports={captureScrollSurface};
