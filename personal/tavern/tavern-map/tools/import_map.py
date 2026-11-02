import json,glob,os,sys
src,game=sys.argv[1],sys.argv[2]
BLANK={"pts":[],"style":"","dir":0,"x":0.0,"y":0.0,"w":0.0,"h":0.0,"rot":0.0,"fl":0,"text":"","size":"","type":"","color":"","img":"","lv":[],"pk":False,"px":0.0,"py":0.0}
LV={"big":[3],"mid":[2],"small":[1]}
feats=[]
for f in glob.glob(src+'/features/*.json'):
    d=json.load(open(f)); fid=os.path.basename(f)[:-5]
    o={"id":fid,"kind":d["kind"],"t":d.get("t",0)}
    for k,v in BLANK.items():
        x=d.get(k,v)
        if isinstance(v,float) and x is not None: x=float(x)
        if k=="dir" or k=="fl": x=int(x or 0)
        o[k]=x if x is not None else v
    if d["kind"]=="label" and "lv" not in d: o["lv"]=LV.get(d.get("size",""),[])
    if d["kind"]=="hill" and ("px" in d or "py" in d): o["pk"]=True
    feats.append(o)
feats.sort(key=lambda o:(o["t"],o["id"]))
tiles=[{"id":os.path.basename(f)[:-5],"on":bool(json.load(open(f)).get("on"))} for f in sorted(glob.glob(src+'/tiles/*.json'))]
old=json.load(open(game))
out={"tiles":tiles,"features":feats,"anchors":old.get("anchors",[])}
print(json.dumps(out,ensure_ascii=False,indent=1))
