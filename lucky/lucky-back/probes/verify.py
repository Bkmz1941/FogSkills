import json, subprocess, sys, yaml

def cli(*a):
    out = subprocess.run(["npx","-y","apidog-cli@2.2.9",*a], capture_output=True, text=True).stdout
    return json.loads(out[out.index("{"):])["data"]

proj, specfile = sys.argv[1], sys.argv[2]
spec = yaml.safe_load(open(specfile))
comp = (spec.get("components") or {}).get("schemas") or {}

eps = cli("endpoint","list","--project",proj)
eps = eps if isinstance(eps,list) else (eps.get("list") or eps.get("items") or [])
sel = [e for e in eps if "game-provider" in str(e.get("path","")) or "core/providers" in str(e.get("path",""))]

print(f"=== project {proj}")
bad = 0
for e in sorted(sel, key=lambda x: str(x.get("path"))):
    d = cli("endpoint","get",str(e["id"]),"--project",proj)
    m, p = str(d["method"]).upper(), d["path"]
    params = d.get("parameters") or {}
    hdr = {h.get("name","").lower(): h.get("example") for h in params.get("header") or []}
    pre = d.get("preProcessors") or []
    script = any("crypto" in str(x.get("data","")) and x.get("enable") for x in pre)
    desc = (d.get("description") or "").strip()
    want = (spec["paths"].get(p, {}).get(m.lower(), {}) or {}).get("description","").strip()
    flags = []
    if "game-provider" in p:
        if not script: flags.append("NO SCRIPT")
        if hdr.get("x-api-key") != "{{x-public-key}}": flags.append(f"HDR={hdr.get('x-api-key')}")
    # description must be the short one from the spec
    if want and desc.replace("&nbsp;"," ").strip() != want:
        flags.append("DESC DRIFT")
    body = json.dumps(d.get("requestBody") or {}, ensure_ascii=False)
    for stale in ("sessionToken","timestamp","total"):
        if stale in body: flags.append(f"body has {stale}")
    if flags: bad += 1
    print(f"  {m:<7}{p:<62}{'OK' if not flags else ' | '.join(flags)}")

schemas = cli("schema","list","--project",proj)
schemas = schemas if isinstance(schemas,list) else (schemas.get("list") or schemas.get("items") or [])
checked = 0
for s in schemas:
    n = s.get("name","")
    if n not in comp: continue
    live = cli("schema","get",str(s["id"]),"--project",proj).get("jsonSchema") or {}
    want = comp[n]
    lp,wp = set((live.get("properties") or {})), set((want.get("properties") or {}))
    lr,wr = set(live.get("required") or []), set(want.get("required") or [])
    checked += 1
    if lp!=wp or lr!=wr:
        bad += 1
        print(f"  SCHEMA {n}: extra={sorted(lp-wp)} missing={sorted(wp-lp)} req_live={sorted(lr)} req_spec={sorted(wr)}")
# EXAMPLE CHECK: a request example must not carry a field the DTO rejects
for e in sorted(sel, key=lambda x: str(x.get("path"))):
    d = cli("endpoint","get",str(e["id"]),"--project",proj)
    rb = d.get("requestBody") or {}
    exs = rb.get("examples") or []
    p_ = d["path"]; m_ = str(d["method"]).lower()
    sp = ((spec["paths"].get(p_, {}) or {}).get(m_, {}) or {}).get("requestBody")
    if not sp or not exs: continue
    raw = sp["content"]["application/json"]["schema"]
    ref = raw.get("$ref","")
    sch = comp.get(ref.split("/")[-1], {}) if ref else raw
    props = set((sch.get("properties") or {}).keys())
    for part in sch.get("allOf") or []:
        r = part.get("$ref","")
        if r: props |= set((comp.get(r.split("/")[-1], {}).get("properties") or {}).keys())
        props |= set((part.get("properties") or {}).keys())
    for ex in exs:
        try: val = json.loads(ex.get("value") or "{}")
        except Exception: continue
        extra = set(val) - props
        if extra:
            bad += 1
            print(f"  EXAMPLE {m_.upper()} {p_}: fields the DTO rejects -> {sorted(extra)}")
print(f"  schemas compared: {checked}, problems: {bad}")
