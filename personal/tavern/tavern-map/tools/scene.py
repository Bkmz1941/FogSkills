import json,glob,os,math
from PIL import Image,ImageDraw
import sys
D=os.environ.get('MAPDB','./cur')
def load(c): return {os.path.basename(p)[:-5]:json.load(open(p)) for p in glob.glob(f'{D}/{c}/*.json')}
marks,roads,strokes,areas=load('marks'),load('roads'),load('strokes'),load('areas')
X0,X1,Y0,Y1=-6.8,-1.8,-1.3,2.0
K=400
W,H=int((X1-X0)*K),int((Y1-Y0)*K)
def px(x,y): return ((x-X0)*K,(Y1-y)*K)
def tex_layer():
    L=Image.new('RGBA',(W,H),(0,0,0,0))
    for s in sorted(strokes.values(),key=lambda s:s.get('t',0)):
        p=s['pts'];pts=[px(p[i],p[i+1]) for i in range(0,len(p),2)]
        w=max(1,int(s['size']*K))
        col=(0,0,0,0) if s.get('erase') else tuple(int(s['color'][i:i+2],16) for i in (1,3,5))+(255,)
        tmp=Image.new('L',(W,H),0);d=ImageDraw.Draw(tmp)
        if len(pts)>1: d.line(pts,fill=255,width=w,joint='curve')
        for q in pts: d.ellipse([q[0]-w/2,q[1]-w/2,q[0]+w/2,q[1]+w/2],fill=255)
        L.paste(Image.new('RGBA',(W,H),col),(0,0),tmp)
    return L
def line_layer():
    L=Image.new('L',(W,H),0);d=ImageDraw.Draw(L)
    for r in roads.values():
        p=r['pts'];pts=[px(p[i],p[i+1]) for i in range(0,len(p),2)]
        w=max(r.get('w') or 0,r.get('w0') or 0)
        d.line(pts,fill=255,width=max(1,int(w*K)),joint='curve')
        for q in pts: d.ellipse([q[0]-w*K/2,q[1]-w*K/2,q[0]+w*K/2,q[1]+w*K/2],fill=255)
    return L
def zone_poly(a): p=a['pts'];return [(p[i],p[i+1]) for i in range(0,len(p),2)]
def inpoly(x,y,P):
    c=False
    for i in range(len(P)):
        (x1,y1),(x2,y2)=P[i],P[i-1]
        if (y1>y)!=(y2>y) and x<(x2-x1)*(y-y1)/(y2-y1)+x1: c=not c
    return c
def render(extra=(),out='scene.png'):
    img=Image.new('RGBA',(W,H),(238,232,214,255))
    img.alpha_composite(tex_layer())
    rl=line_layer();img.paste((120,100,80,255),(0,0),rl)
    d=ImageDraw.Draw(img)
    for a in areas.values(): d.polygon([px(*q) for q in zone_poly(a)],outline=(74,144,194,255),width=3)
    for m in list(marks.values())+list(extra):
        x,y=px(m['x'],m['y']);k=m['kind'];r={'tree':.045,'fir':.05,'cottage':.12,'hill':.33}.get(k,.05)*K
        c={'tree':(110,160,70),'fir':(40,90,50),'cottage':(200,60,60),'hill':(170,150,110)}.get(k,(0,0,0))
        if m in extra: c=tuple(min(255,v+60) for v in c)
        if k=='hill': d.ellipse([x-r,y-r,x+r,y+r],outline=c,width=2)
        else: d.ellipse([x-r/2,y-r/2,x+r/2,y+r/2],fill=c)
    img.save(out)
if __name__=='__main__': render()
