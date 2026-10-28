import random,math,json,time,os
from scene import *
ZONE=os.environ.get('ZONE');random.seed(int(os.environ.get('SEED','1010')))
P=zone_poly(areas[ZONE] if ZONE else list(areas.values())[0])
tex=tex_layer().split()[3];rl=line_layer()
def blocked(x,y,pad):
    for dx,dy in [(0,0),(pad,0),(-pad,0),(0,pad),(0,-pad),(pad*.7,pad*.7),(-pad*.7,pad*.7),(pad*.7,-pad*.7),(-pad*.7,-pad*.7)]:
        u,v=px(x+dx,y+dy)
        if 0<=u<W and 0<=v<H and (rl.getpixel((int(u),int(v))) or tex.getpixel((int(u),int(v)))): return True
    return False
def edge_d(x,y):
    m=9
    for i in range(len(P)):
        (x1,y1),(x2,y2)=P[i],P[i-1];dx,dy=x2-x1,y2-y1
        t=max(0,min(1,((x-x1)*dx+(y-y1)*dy)/(dx*dx+dy*dy)));m=min(m,math.hypot(x-x1-t*dx,y-y1-t*dy))
    return m
cot=[m for m in marks.values() if m['kind']=='cottage'][0]
no_go=[(m['x'],m['y'],{'hill':0.33,'lake':0.3}[m['kind']]+0.035) for m in marks.values() if m['kind'] in('hill','lake')]
pts=[(m['x'],m['y']) for m in marks.values() if m['kind'] in('tree','fir')]
R=0.08
xs=[p[0] for p in P];ys=[p[1] for p in P]
new=[]
for _ in range(60000):
    x=random.uniform(min(xs),max(xs));y=random.uniform(min(ys),max(ys))
    if not inpoly(x,y,P) or edge_d(x,y)<0.035: continue
    if math.hypot(x-cot['x'],y-cot['y'])<0.2: continue
    if blocked(x,y,0.035): continue
    if any(math.hypot(x-a,y-b)<r for a,b,r in no_go): continue
    if any((x-a)**2+(y-b)**2<R*R for a,b in pts): continue
    pts.append((x,y));new.append({'kind':'fir' if random.random()<0.6 else 'tree','x':round(x,3),'y':round(y,3)})
print(len(new))
t=int(time.time()*1000)
def b36(n):
    s='';a='0123456789abcdefghijklmnopqrstuvwxyz'
    while n: s=a[n%36]+s;n//=36
    return s
os.makedirs('new',exist_ok=True)
for i,m in enumerate(new):
    m['id']='mf'+b36(t)+b36(i).rjust(3,'0')
    json.dump({'kind':m['kind'],'x':m['x'],'y':m['y']},open(f"new/{m['id']}.json",'w'))
json.dump(new,open('new.json','w'))
render(new,'after.png')
