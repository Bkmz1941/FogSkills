const fs=require('fs');
const html=fs.readFileSync('dashboard.html','utf8');
const js=html.slice(html.indexOf('<script>')+8,html.lastIndexOf('</script>'));
const cut=js.indexOf('const initial=');
const dataJs=js.slice(0,js.indexOf('const chip='))+js.slice(js.indexOf('const P={'),cut)+js.slice(js.indexOf('const EC='),js.indexOf('const itemsOf='))+js.slice(js.indexOf('const PL='),js.indexOf('const face='));
const ctx={};
eval(dataJs+';ctx.S=S;ctx.END=END;ctx.FR=FR;ctx.P=P;ctx.IT=IT;ctx.PL=PL;');
const SKIP=new Set(['img','url','color','place','owners','grp','tone','people','tic_ids']);
const out=new Set();
const cyr=/[А-Яа-яЁё]/;
function walk(v,key){
 if(typeof v==='string'){if(cyr.test(v))out.add(v);return}
 if(Array.isArray(v)){v.forEach(x=>walk(x,key));return}
 if(v&&typeof v==='object'){for(const k in v){if(SKIP.has(k))continue;walk(v[k],k)}}
}
walk(ctx.S);walk(ctx.END);walk(ctx.P);walk(ctx.IT);walk(ctx.PL);
for(const k in ctx.FR){out.add(k);walk(ctx.FR[k])}
// static strings in html body and template literals
const body=html.slice(0,html.indexOf('<script>'));
for(const m of body.matchAll(/>([^<>]*[А-Яа-яЁё][^<>]*)</g))out.add(m[1].trim());
const rest=js.slice(js.indexOf('const chip='));
for(const m of rest.matchAll(/"([^"\n]*[А-Яа-яЁё][^"\n]*)"/g))out.add(m[1]);
for(const m of rest.matchAll(/>([^<>`$]*[А-Яа-яЁё][^<>`$]*)</g))out.add(m[1].trim());
const arr=[...out].filter(Boolean);
fs.writeFileSync('strings.json',JSON.stringify(arr,null,0));
console.log(arr.length, arr.reduce((a,s)=>a+s.length,0));
