/** Observe native canvas draw calls without changing the rendered commands. */
function observeCanvasDrawing() {
  const records = new Map();
  const clear = CanvasRenderingContext2D.prototype.clearRect;
  CanvasRenderingContext2D.prototype.clearRect = function(x,y,w,h) {
    if (x === 0 && y === 0 && w >= this.canvas.width && h >= this.canvas.height) records.delete(this.canvas);
    return clear.apply(this, arguments);
  };
  window.__bioetlCanvasEvidence = records;
  for (const method of ['fillText','strokeText','stroke','fill']) {
    const original = CanvasRenderingContext2D.prototype[method];
    CanvasRenderingContext2D.prototype[method] = function(...args) {
      const value = {method, text:method.endsWith('Text')?String(args[0]):null,
        foreground:method.startsWith('stroke')?this.strokeStyle:this.fillStyle,
        font:this.font,alpha:this.globalAlpha,composition:this.globalCompositeOperation,
        lineWidth:this.lineWidth,lineDash:this.getLineDash(),
        transform:Array.from(this.getTransform().toFloat64Array())};
      if(method.endsWith('Text')) {
        const metrics=this.measureText(value.text), t=this.getTransform();
        value.bounds={x:t.a*(Number(args[1])-metrics.actualBoundingBoxLeft)+t.e,
          y:t.d*(Number(args[2])-metrics.actualBoundingBoxAscent)+t.f,
          width:t.a*(metrics.actualBoundingBoxLeft+metrics.actualBoundingBoxRight),
          height:t.d*(metrics.actualBoundingBoxAscent+metrics.actualBoundingBoxDescent)};
        value.rotated=t.b!==0 || t.c!==0;
      }
      if(!records.has(this.canvas))records.set(this.canvas,new Map());
      records.get(this.canvas).set(JSON.stringify(value),value);
      return original.apply(this,args);
    };
  }
}
function canvasEvidenceFromDom() {
/** Measure native paint before antialiasing, with current RGBA pixel witnesses. */
function measureCanvas(canvas, calls) {
  const rgba = value => {
    if(typeof value !== 'string')return null;
    if(/^#[0-9a-f]{6}$/i.test(value))return [1,3,5].map(i=>parseInt(value.slice(i,i+2),16)).concat(1);
    const m=value.match(/^rgba?\(([^)]+)\)$/);if(!m)return null;
    const a=m[1].split(',').map(Number);return a.length===3?a.concat(1):a;
  };
  const blend=(a,b)=>a.slice(0,3).map((v,i)=>v*a[3]+b[i]*(1-a[3]));
  const luminance=a=>a.map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0);
  const contrast=(a,b)=>(Math.max(luminance(a),luminance(b))+.05)/(Math.min(luminance(a),luminance(b))+.05);
  const layers=[];let unsupported=false;
  for(let el=canvas;el;el=el.parentElement){
    const s=getComputedStyle(el);layers.push(rgba(s.backgroundColor));
    if(s.backgroundImage!=='none'||Number(s.opacity)!==1||s.filter!=='none')unsupported=true;
  }
  let background=[255,255,255];
  for(const layer of layers.reverse())if(layer)background=blend(layer,background);
  background=background.map(Math.round);
  const {width:w,height:h}=canvas;
  const pixels=canvas.getContext('2d').getImageData(0,0,w,h).data;
  const at=(x,y)=>{
    if(x<0||y<0||x>=w||y>=h)return null;
    const i=(y*w+x)*4;return blend([pixels[i],pixels[i+1],pixels[i+2],pixels[i+3]/255],background).map(Math.round);
  };
  const equal=(a,b)=>a&&a.every((v,i)=>Math.abs(v-b[i])<=1);
  const pairs={text:[],graphics:[]}, excluded=[];
  const panel=canvas.closest('[data-viz-panel-key]').dataset.vizPanelKey;
  for(const call of calls){
    const color=rgba(call.foreground), text=call.method.endsWith('Text');
    if(color && (color[3]===0||call.alpha===0)){
      excluded.push({method:call.method,foreground:call.foreground,reason:'transparent paint contributes no visible graphic'});continue;
    }
    if(!text && ['rgba(0, 10, 23, 0.09)','rgba(240, 250, 255, 0.09)'].includes(call.foreground)){
      excluded.push({method:call.method,foreground:call.foreground,reason:'Grafana native background grid; axis labels carry the scale'});continue;
    }
    const pair={panel,element:'canvas '+call.method,text:call.text,foreground:color?.slice(0,3),background,
      method:'native pre-antialias paint verified by current RGBA pixel and adjacent background',threshold:text?4.5:3,
      ratio:null,status:'NOT_VERIFIABLE',pixelWitness:null};
    if(!color||color[3]!==1||call.alpha!==1||call.composition!=='source-over'||unsupported||call.rotated){
      pair.reason='unsupported canvas paint/compositing/background';pairs[text?'text':'graphics'].push(pair);continue;
    }
    if(text){
      const size=Number((call.font.match(/([\d.]+)px/)||[])[1]);
      const weight=/\bbold\b|\b[7-9]00\b/.test(call.font)?700:400;
      pair.font=call.font;pair.fontSizePx=size;pair.fontWeight=weight;
      pair.threshold=size>=24||(size>=18.6667&&weight>=700)?3:4.5;
    }
    let bounds=text?call.bounds:{x:0,y:0,width:w,height:h};
    if(!bounds){pair.reason='text bounds missing';pairs.text.push(pair);continue;}
    const left=Math.max(0,Math.floor(bounds.x)),top=Math.max(0,Math.floor(bounds.y));
    const right=Math.min(w,Math.ceil(bounds.x+bounds.width)),bottom=Math.min(h,Math.ceil(bounds.y+bounds.height));
    let core=null,adjacent=null;
    for(let y=top;y<bottom&&!core;y++)for(let x=left;x<right;x++){
      const pixelIndex=(y*w+x)*4, rasterAlpha=pixels[pixelIndex+3];
      const roundingTolerance=rasterAlpha?Math.ceil(255/rasterAlpha):0;
      if(rasterAlpha<32 || !color.slice(0,3).every((v,i)=>Math.abs(pixels[pixelIndex+i]-v)<=roundingTolerance))continue;
      for(const [dx,dy] of [[-2,0],[2,0],[0,-2],[0,2],[-3,0],[3,0],[0,-3],[0,3]]){
        if(equal(at(x+dx,y+dy),background)){core={x,y,rgb:at(x,y),rawRgba:Array.from(pixels.slice(pixelIndex,pixelIndex+4)),rasterAlpha:rasterAlpha/255};adjacent={x:x+dx,y:y+dy,rgb:at(x+dx,y+dy)};break;}
      }
      if(core)break;
    }
    if(core){
      pair.pixelWitness={foreground:core,adjacent};pair.ratio=contrast(color.slice(0,3),background);
      pair.status=pair.ratio>=pair.threshold?'PASS':'FAIL';
    } else pair.reason='no visible matching native paint with adjacent background in current bitmap';
    pairs[text?'text':'graphics'].push(pair);
  }
  return {pairs,excluded,background,status:Object.values(pairs).flat().length && Object.values(pairs).flat().every(p=>p.status==='PASS')?'PASS':'NOT_PROVEN'};
}
  return [...document.querySelectorAll('[data-viz-panel-key] canvas')].map(canvas=>{
    const r=canvas.getBoundingClientRect();
    const calls=[...(window.__bioetlCanvasEvidence?.get(canvas)?.values() || [])];
    return {panel:canvas.closest('[data-viz-panel-key]').dataset.vizPanelKey,
      bbox:{x:r.x,y:r.y,width:r.width,height:r.height},width:canvas.width,height:canvas.height,
      calls,measurements:measureCanvas(canvas,calls),
      status:'REQUIRES_CLASSIFICATION',pixelData:canvas.toDataURL('image/png')};
  });
}
/** Verify a non-color route to each plotted series through native keyboard controls. */
async function captureSeriesControls(page, {dashboard, outputDir, pngEvidence, timeout}) {
  const fs=require('node:fs'),path=require('node:path');
  const ids=await page.locator('[data-viz-panel-key]').evaluateAll(els=>els.filter(el=>el.querySelector('canvas')).map(el=>el.dataset.vizPanelKey));
  const results=[];
  for(const id of ids){
    if(!dashboard.requiredPanels.some(p=>p.id===Number(id.replace('panel-',''))&&p.type==='timeseries'))continue;
    const panel=page.locator(`[data-viz-panel-key="${id}"]`);
    const rows=panel.locator('[data-testid^="data-testid VizLegend series "]');
    const labels=await rows.locator('button').allTextContents();
    if(labels.length<2)continue;
    const entries=[];
    for(let index=0;index<labels.length;index++){
      const button=rows.locator('button').nth(index);
      await button.focus();await page.keyboard.press('Enter');await page.waitForTimeout(250);
      const active=await rows.evaluateAll(els=>els.filter(el=>!el.className.includes('LegendLabelDisabled')).map(el=>el.querySelector('button')?.textContent));
      const focused=await button.evaluate(el=>document.activeElement===el);
      const canvas=await page.evaluate(canvasEvidenceFromDom);
      const file=path.join(outputDir,'series',dashboard.uid,id,`${String(index).padStart(3,'0')}.png`);
      await fs.promises.mkdir(path.dirname(file),{recursive:true});
      const png=await panel.screenshot({path:file,timeout,animations:'disabled'});
      await button.focus();await page.keyboard.press('Enter');await page.waitForTimeout(250);
      const restored=await rows.evaluateAll(els=>els.filter(el=>!el.className.includes('LegendLabelDisabled')).map(el=>el.querySelector('button')?.textContent));
      entries.push({label:labels[index],canvas:canvas.filter(c=>c.panel===id),method:'native legend button focus + Enter isolates one named series; Enter restores all',focused,active,restored,
        status:focused&&active.length===1&&active[0]===labels[index]&&JSON.stringify(restored)===JSON.stringify(labels)?'PASS':'FAIL',
        file:path.relative(outputDir,file),...pngEvidence(png)});
    }
    results.push({panel:id,labels,entries,status:entries.every(e=>e.status==='PASS')?'PASS':'FAIL'});
  }
  return results;
}
module.exports={observeCanvasDrawing,canvasEvidenceFromDom,captureSeriesControls};
