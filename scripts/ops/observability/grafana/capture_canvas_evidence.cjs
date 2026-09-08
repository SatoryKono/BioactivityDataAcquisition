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
  // Kept in the callback so Playwright can serialize it into each browser realm.
  const paint = {
    rgba(value) {
      if (typeof value !== 'string') return null;
      if (/^#[0-9a-f]{6}$/i.test(value)) return [1,3,5].map(i=>Number.parseInt(value.slice(i,i+2),16)).concat(1);
      const match=/^rgba?\(([^)]+)\)$/.exec(value);
      if (!match) return null;
      const channels=match[1].split(',').map(Number);
      return channels.length===3 ? channels.concat(1) : channels;
    },
    blend(a,b) { return a.slice(0,3).map((v,i)=>v*a[3]+b[i]*(1-a[3])); },
    luminance(a) { return a.map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0); },
    contrast(a,b) { return (Math.max(this.luminance(a),this.luminance(b))+.05)/(Math.min(this.luminance(a),this.luminance(b))+.05); },
    background(canvas) {
      const layers=[];let unsupported=false;
      for(let el=canvas;el;el=el.parentElement) {
        const style=getComputedStyle(el);layers.push(this.rgba(style.backgroundColor));
        if(style.backgroundImage!=='none'||Number(style.opacity)!==1||style.filter!=='none')unsupported=true;
      }
      let color=[255,255,255];
      for(const layer of layers.toReversed())if(layer)color=this.blend(layer,color);
      return {color:color.map(Math.round),unsupported};
    },
    sample(ctx,x,y) {
      if(x<0||y<0||x>=ctx.width||y>=ctx.height)return null;
      const i=(y*ctx.width+x)*4,p=ctx.pixels;
      return this.blend([p[i],p[i+1],p[i+2],p[i+3]/255],ctx.background).map(Math.round);
    },
    adjacent(ctx,x,y) {
      for(const [dx,dy] of [[-2,0],[2,0],[0,-2],[0,2],[-3,0],[3,0],[0,-3],[0,3]]) {
        const rgb=this.sample(ctx,x+dx,y+dy);
        if(rgb?.every((v,i)=>Math.abs(v-ctx.background[i])<=1))return {x:x+dx,y:y+dy,rgb};
      }
      return null;
    },
    witness(ctx,color,bounds) {
      const left=Math.max(0,Math.floor(bounds.x)),top=Math.max(0,Math.floor(bounds.y));
      const right=Math.min(ctx.width,Math.ceil(bounds.x+bounds.width)),bottom=Math.min(ctx.height,Math.ceil(bounds.y+bounds.height));
      for(let y=top;y<bottom;y++)for(let x=left;x<right;x++) {
        const index=(y*ctx.width+x)*4,alpha=ctx.pixels[index+3];
        const tolerance=alpha?Math.ceil(255/alpha):0;
        if(alpha<32 || !color.slice(0,3).every((v,i)=>Math.abs(ctx.pixels[index+i]-v)<=tolerance))continue;
        const adjacent=this.adjacent(ctx,x,y);
        if(adjacent)return {foreground:{x,y,rgb:this.sample(ctx,x,y),rawRgba:Array.from(ctx.pixels.slice(index,index+4)),rasterAlpha:alpha/255},adjacent};
      }
      return null;
    },
    exclusion(call,color,text) {
      if(!color)return null;
      if(color[3]===0||call.alpha===0)return 'transparent paint contributes no visible graphic';
      if(!text && ['rgba(0, 10, 23, 0.09)','rgba(240, 250, 255, 0.09)'].includes(call.foreground))return 'Grafana native background grid; axis labels carry the scale';
      return null;
    },
    font(call,pair) {
      const size=Number(/\b(\d+(?:\.\d+)?)px\b/.exec(call.font)?.[1]);
      const weight=/\bbold\b|\b[7-9]00\b/.test(call.font)?700:400;
      pair.font=call.font;pair.fontSizePx=size;pair.fontWeight=weight;
      pair.threshold=size>=24||(size>=18.6667&&weight>=700)?3:4.5;
    },
    pair(ctx,call,color,text) {
      const pair={panel:ctx.panel,element:'canvas '+call.method,text:call.text,foreground:color?.slice(0,3),background:ctx.background,
        method:'native pre-antialias paint verified by current RGBA pixel and adjacent background',threshold:text?4.5:3,
        ratio:null,status:'NOT_VERIFIABLE',pixelWitness:null};
      if(color?.[3]!==1||call.alpha!==1||call.composition!=='source-over'||ctx.unsupported||call.rotated) {
        pair.reason='unsupported canvas paint/compositing/background';return pair;
      }
      if(text)this.font(call,pair);
      const bounds=text?call.bounds:{x:0,y:0,width:ctx.width,height:ctx.height};
      if(!bounds){pair.reason='text bounds missing';return pair;}
      const witness=this.witness(ctx,color,bounds);
      if(!witness){pair.reason='no visible matching native paint with adjacent background in current bitmap';return pair;}
      pair.pixelWitness=witness;pair.ratio=this.contrast(color.slice(0,3),ctx.background);
      pair.status=pair.ratio>=pair.threshold?'PASS':'FAIL';return pair;
    },
    measure(canvas,calls) {
      const {color:background,unsupported}=this.background(canvas);
      const {width,height}=canvas;
      const ctx={background,unsupported,width,height,pixels:canvas.getContext('2d').getImageData(0,0,width,height).data,
        panel:canvas.closest('[data-viz-panel-key]').dataset.vizPanelKey};
      const pairs={text:[],graphics:[]},excluded=[];
      for(const call of calls) {
        const color=this.rgba(call.foreground),text=call.method.endsWith('Text');
        const reason=this.exclusion(call,color,text);
        if(reason){excluded.push({method:call.method,foreground:call.foreground,reason});continue;}
        pairs[text?'text':'graphics'].push(this.pair(ctx,call,color,text));
      }
      const measured=Object.values(pairs).flat();
      return {pairs,excluded,background,status:measured.length && measured.every(p=>p.status==='PASS')?'PASS':'NOT_PROVEN'};
    }
  };
  return [...document.querySelectorAll('[data-viz-panel-key] canvas')].map(canvas=>{
    const r=canvas.getBoundingClientRect();
    const calls=[...(window.__bioetlCanvasEvidence?.get(canvas)?.values() || [])];
    return {panel:canvas.closest('[data-viz-panel-key]').dataset.vizPanelKey,
      bbox:{x:r.x,y:r.y,width:r.width,height:r.height},width:canvas.width,height:canvas.height,
      calls,measurements:paint.measure(canvas,calls),
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
      const png=await require('./native_browser_zoom.cjs').captureElementScreenshot(page,panel,
        {path:file,timeout,animations:'disabled'});
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
