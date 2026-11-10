/** Preserve native-zoom panel pixels by capturing tall panels in visible pieces. */
const fs=require('node:fs');
const crypto=require('node:crypto');

async function captureTallPanel(page,element,options,capture) {
  const state=await element.evaluate(el=>{
    let parent=el.parentElement;
    while(parent && !(parent.scrollHeight>parent.clientHeight+2 && /auto|scroll/.test(getComputedStyle(parent).overflowY)))parent=parent.parentElement;
    parent ||= document.scrollingElement;
    parent.dataset.bioetlPanelScroll='true';
    return {top:parent.scrollTop,left:parent.scrollLeft};
  });
  const tiles=[];
  async function part(target) {
    if(tiles.length>=100)throw new Error('Panel viewport capture exceeded 100 tiles');
    await element.evaluate((el,target)=>{
      const parent=document.querySelector('[data-bioetl-panel-scroll]');
      const p=parent.getBoundingClientRect(),r=el.getBoundingClientRect();
      // Sticky/fixed chrome outside the panel only — ignore the panel header itself.
      const top=[...parent.querySelectorAll('*')].reduce((edge,node)=>{
        if(node===el || el.contains(node))return edge;
        const b=node.getBoundingClientRect(),style=getComputedStyle(node);
        return ['sticky','fixed'].includes(style.position) && b.top>=0 && b.top<innerHeight/2 && b.width>innerWidth/2 ? Math.max(edge,b.bottom):edge;
      },Math.max(0,p.top));
      parent.scrollTop+=r.top-top+target;
    },target);
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    const geometry=await element.evaluate(el=>{
      const r=el.getBoundingClientRect();
      const parent=document.querySelector('[data-bioetl-panel-scroll]'),p=parent.getBoundingClientRect();
      const top=[...parent.querySelectorAll('*')].reduce((edge,node)=>{
        if(node===el || el.contains(node))return edge;
        const style=getComputedStyle(node),b=node.getBoundingClientRect();
        return ['sticky','fixed'].includes(style.position) && b.top>=0 && b.top<innerHeight/2 && b.width>innerWidth/2 ? Math.max(edge,b.bottom):edge;
      },Math.max(0,p.top));
      const y=Math.max(top,r.top),bottom=Math.min(innerHeight,p.bottom,r.bottom);
      return {x:r.x,y,width:r.width,height:bottom-y,offset:y-r.top,totalHeight:r.height};
    });
    if(geometry.height<=0 || geometry.x<0)throw new Error('Panel tile is not visible');
    const covered=tiles.length ? tiles.at(-1).offset+tiles.at(-1).cssHeight:0;
    if(geometry.offset>covered+2 || geometry.offset+geometry.height<=covered)throw new Error('Panel tile coverage has a gap or made no progress');
    const clip={x:geometry.x,y:geometry.y,width:geometry.width,height:geometry.height};
    const file=options.path.replace(/\.png$/,`-viewport-${tiles.length+1}.png`);
    const bytes=await capture(page,{...options,path:file,clip});
    tiles.push({file,offset:geometry.offset,cssHeight:geometry.height,cssWidth:geometry.width,
      width:bytes.readUInt32BE(16),height:bytes.readUInt32BE(20),sha256:crypto.createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length});
    if(geometry.offset+geometry.height<geometry.totalHeight-1)await part(geometry.offset+geometry.height-1);
  }
  try {await part(0);}
  finally {
    await page.evaluate(state=>{
      const parent=document.querySelector('[data-bioetl-panel-scroll]');
      parent.scrollTop=state.top;parent.scrollLeft=state.left;delete parent.dataset.bioetlPanelScroll;
    },state);
  }
  const images=await Promise.all(tiles.map(tile=>fs.promises.readFile(tile.file).then(b=>b.toString('base64'))));
  const compositor=await page.context().newPage();
  try {
    const data=await compositor.evaluate(async({tiles,images})=>{
      const scale=tiles[0].width/tiles[0].cssWidth;
      const canvas=document.createElement('canvas');canvas.width=tiles[0].width;
      canvas.height=Math.round((tiles.at(-1).offset+tiles.at(-1).cssHeight)*scale);
      const context=canvas.getContext('2d');
      const loaded=await Promise.all(images.map(async src=>{const image=new Image();image.src='data:image/png;base64,'+src;await image.decode();return image;}));
      loaded.forEach((image,i)=>context.drawImage(image,0,Math.round(tiles[i].offset*scale)));
      return canvas.toDataURL('image/png').split(',')[1];
    },{tiles,images});
    const bytes=Buffer.from(data,'base64');await fs.promises.writeFile(options.path,bytes);
    bytes.viewportTiles=tiles;return bytes;
  } finally {await compositor.close();}
}
module.exports={captureTallPanel};
