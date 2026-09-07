// Replay the actual Grafana 12.0.0 data-frame library without a browser DOM.
// The stubs cover local storage only; transformation/display code is unmodified.
const fs = require('fs');
global.window = {addEventListener() {}, localStorage: {getItem() {return null;}, setItem() {}}};
const g = require('./runtime/node_modules/@grafana/data');
g.standardTransformersRegistry.setInit(() => [...new Map(Object.values(g.standardTransformers).map(t => [t.id, {id: t.id, name: t.name, transformation: t}])).values()]);
const {lastValueFrom} = require('./runtime/node_modules/rxjs');
const ts = require('E:/github/BioactivityDataAcquisition/grafana/plugins/bioetl-scenes-app/node_modules/typescript');
const prom = {};
const compiled = ts.transpileModule(fs.readFileSync(__dirname + '/result_transformer.ts', 'utf8'), {compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020}}).outputText;
new Function('require', 'exports', compiled)(name => {
  if (name === '@grafana/data') return g;
  if (name === 'lodash') return require('./runtime/node_modules/lodash');
  if (name === '@grafana/runtime') return {getDataSourceSrv() {throw new Error('Exemplar links are outside this audit');}};
  throw new Error('Unexpected source dependency: ' + name);
}, prom);

async function main() {
  const input = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  // All shipped values are already typed JSON. Use Grafana's actual override
  // matcher, priority, reducer and display processor with identity value editors.
  const properties = new Set(['unit','decimals','min','max','noValue','mappings','thresholds','color','displayName','links']);
  for (const item of input) for (const rule of item.panel.fieldConfig?.overrides || []) for (const p of rule.properties) properties.add(p.id);
  g.standardFieldConfigEditorRegistry.setInit(() => [...properties].map(id => ({id, path: id.replace(/^custom\./, ''), isCustom: id.startsWith('custom.'), shouldApply: () => true, process: v => {
    if (id === 'thresholds' && v?.steps?.length) return {...v, steps: v.steps.map((s,i) => i ? s : {...s, value: -Infinity})};
    return v;
  }})));
  const output = [];
  for (const item of input) {
    if (!item.response) {output.push({id:item.id, status:'NA', reason:'unsupported selector combination'}); continue;}
    try {
      let frames = Object.values(item.response.results || {}).flatMap(r => r.frames || []).map(g.dataFrameFromJSON);
      const stages = [{operation: 'raw', frames: frames.map(serialize)}];
      if (item.request?.queries?.[0]?.datasource?.type === 'prometheus') {
        frames = prom.transformV2({data:frames}, {targets:item.request.queries, app:'dashboard'}, {}).data;
        stages.push({operation:'prometheus-transformV2', frames:frames.map(serialize)});
      }
      for (const t of item.panel.transformations || []) {
        frames = await lastValueFrom(g.transformDataFrame([t], frames));
        stages.push({operation: t.id, frames: frames.map(serialize)});
      }
      const theme = g.createTheme();
      const data = g.applyFieldOverrides({data: frames, fieldConfig: item.panel.fieldConfig || {defaults: {}, overrides: []}, theme, replaceVariables: s => s, timeZone: 'utc'});
      const displays = ['stat', 'gauge'].includes(item.panel.type) ? g.getFieldDisplayValues({data, fieldConfig: item.panel.fieldConfig, reduceOptions: item.panel.options.reduceOptions, replaceVariables: s => s, timeZone: 'utc', theme}).map(v => ({name: v.name, display: v.display})) : [];
      const stateFrame = g.toDataFrame({fields:[{name:'Value',type:'number',values:[0]}]});
      const stateData = g.applyFieldOverrides({data:[stateFrame],fieldConfig:item.panel.fieldConfig,theme,replaceVariables:s=>s,timeZone:'utc'});
      const processor = stateData[0].fields[0].display;
      const syntheticDisplayStates = ['stat','gauge'].includes(item.panel.type) ? {zero:processor(0),null:processor(null),nan:processor(NaN),provenance:'synthetic presentation probe, not source telemetry'} : null;
      output.push({id: item.id, version: '12.0.0', stages, frames: data.map(serialize), displays, syntheticDisplayStates});
    } catch (e) {
      output.push({id: item.id, error: String(e.stack || e)});
    }
  }
  fs.writeFileSync(process.argv[3], JSON.stringify(output, null, 2));
}
function serialize(f) {
  return {name: f.name, refId: f.refId, length: f.length, fields: f.fields.map(x => ({name: x.name, displayName:g.getFieldDisplayName(x,f), type: x.type, labels: x.labels, config: x.config, values: Array.from(x.values)}))};
}
main().catch(e => {console.error(e); process.exitCode = 1;});
