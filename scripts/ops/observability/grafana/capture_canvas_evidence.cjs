/** Observe native canvas draw calls without changing the rendered commands. */
function observeCanvasDrawing() {
  const records = new Map();
  window.__bioetlCanvasEvidence = records;
  for (const method of ['fillText','strokeText','stroke','fill']) {
    const original = CanvasRenderingContext2D.prototype[method];
    CanvasRenderingContext2D.prototype[method] = function(...args) {
      const value = {method, text:method.endsWith('Text')?String(args[0]):null,
        foreground:method.startsWith('stroke')?this.strokeStyle:this.fillStyle,
        font:this.font,alpha:this.globalAlpha,composition:this.globalCompositeOperation,
        lineWidth:this.lineWidth,lineDash:this.getLineDash(),
        transform:Array.from(this.getTransform().toFloat64Array())};
      if(!records.has(this.canvas))records.set(this.canvas,new Map());
      records.get(this.canvas).set(JSON.stringify(value),value);
      return original.apply(this,args);
    };
  }
}
function canvasEvidenceFromDom() {
  return [...document.querySelectorAll('[data-viz-panel-key] canvas')].map(canvas=>{
    const r=canvas.getBoundingClientRect();
    return {panel:canvas.closest('[data-viz-panel-key]').dataset.vizPanelKey,
      bbox:{x:r.x,y:r.y,width:r.width,height:r.height},width:canvas.width,height:canvas.height,
      calls:[...(window.__bioetlCanvasEvidence?.get(canvas)?.values() || [])],
      status:'REQUIRES_CLASSIFICATION',pixelData:canvas.toDataURL('image/png')};
  });
}
module.exports={observeCanvasDrawing,canvasEvidenceFromDom};
