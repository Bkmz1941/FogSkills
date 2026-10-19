import json,subprocess,sys,time,os
S=os.path.dirname(os.path.abspath(__file__)); OUTDIR=os.environ.get("OUT","/tmp")
nofog,noplants,tag=sys.argv[1],sys.argv[2],sys.argv[3]
out=f"{OUTDIR}/trap_{tag}.txt"
if os.path.exists(out): os.remove(out)
code=open(f"{S}/trap_walk.cs").read().replace("__NOFOG__",nofog).replace("__NOPLANTS__",noplants).replace("__OUT__",out)
r=subprocess.run(["python3","mcp_call.py","execute_code",json.dumps({"action":"execute","code":code})],capture_output=True,text=True,cwd=os.path.expanduser("~/.claude/skills/tavern-game"))
print(r.stdout[-400:],r.stderr[-300:])
for i in range(40):
    if os.path.exists(out): break
    time.sleep(2)
print(open(out).read() if os.path.exists(out) else "нет файла")
