import json,re,sys
DASH=re.compile(r'\s*[—–]\s*|\s+-\s+'); COMMA=re.compile(r',\s*(?=[,.!?…:;»)"”]|$)')
def tidy(s):
    if not s: return s
    s=DASH.sub(', ',s); s=COMMA.sub('',s); s=re.sub(r'\s{2,}',' ',s).strip().lstrip(', ')
    while True:
        t=s.rstrip(); q=len(t)
        while q>0 and t[q-1] in '»"”)': q-=1
        body,tail=t[:q],t[q:]
        if body.endswith('...'): return body[:-3].rstrip()+'…'+tail
        if body.endswith('.') and not body.endswith('..'): s=body[:-1].rstrip()+tail; continue
        return t
def texts(d):
    """yield (container,key) for every spoken text"""
    def T(o):
        if isinstance(o,dict):
            for k in ('ru','en'):
                if isinstance(o.get(k),str): yield (o,k)
    yield from T(d.get('greeting'))
    for k in ('pool','refuse','openers','busy','leave','tics','unanswered'):
        for o in d.get(k,[]): yield from T(o)
    for p in d.get('pairs',[]): yield from T(p.get('reply'))
    for r in d.get('requests',[]): yield from T(r.get('ask')); yield from T(r.get('thanks'))
    for i in d.get('interests',[]):
        for a in i.get('asks',[]): yield from T(a)
    for l in d.get('lines',[]):
        yield from T(l)
        for b in l.get('byPhase',[]): yield from T(b)
if __name__=='__main__':
    f=sys.argv[1]; d=json.load(open(f)); mode=sys.argv[2]
    bad=0
    for o,k in texts(d):
        n=tidy(o[k])
        if n!=o[k]:
            bad+=1
            if mode=='show' and ('—' in o[k] or '–' in o[k] or ' - ' in o[k]): print(repr(o[k]),'->',repr(n))
            if mode=='fix': o[k]=n
    print('changed' if mode=='fix' else 'to change',bad)
    if mode=='fix': open(f,'w').write(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
