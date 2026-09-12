import json, subprocess, sys, yaml, tempfile, os

PROJ = sys.argv[1]
SPEC = sys.argv[2]


def cli(*a):
    out = subprocess.run(["npx", "-y", "apidog-cli@2.2.9", *a], capture_output=True, text=True).stdout
    return json.loads(out[out.index("{"):])


spec = yaml.safe_load(open(SPEC))

# path+method -> [(name, description, payload)] taken from the spec's response examples
wanted = {}
for path, ops in spec["paths"].items():
    if "game-provider" not in path:
        continue
    for method, op in ops.items():
        for code, resp in (op.get("responses") or {}).items():
            c = (resp.get("content") or {}).get("application/json") or {}
            if "examples" in c:
                cases = [(v.get("summary") or k, v.get("description", ""), v["value"]) for k, v in c["examples"].items()]
            elif "example" in c:
                cases = [("Success", "", c["example"])]
            else:
                continue
            wanted[(path, method.upper(), str(code))] = cases

eps = cli("endpoint", "list", "--project", PROJ)["data"]
if isinstance(eps, dict):
    eps = eps.get("list") or eps.get("items") or []

for e in eps:
    path = str(e.get("path", ""))
    if "game-provider" not in path:
        continue
    d = cli("endpoint", "get", str(e["id"]), "--project", PROJ)["data"]
    method = str(d["method"]).upper()
    out = []
    for resp in d.get("responses") or []:
        key = (path, method, str(resp.get("code")))
        for name, desc, payload in wanted.get(key, []):
            entry = {"name": name, "responseId": resp["id"], "data": json.dumps(payload, ensure_ascii=False, indent=2)}
            if desc:
                entry["description"] = desc
            out.append(entry)
    if not out:
        print(f"  {method:<6}{path:<48} no example in the spec")
        continue
    fd, tmp = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as fh:
        json.dump({"responseExamples": out}, fh, ensure_ascii=False)
    res = cli("endpoint", "update", str(e["id"]), "--project", PROJ, "--file", tmp)
    os.unlink(tmp)
    names = ", ".join(x["name"] for x in out)
    print(f"  {method:<6}{path:<48} {'ok' if res.get('success') else 'FAILED'}  [{names}]")
