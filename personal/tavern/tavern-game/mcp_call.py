import json, sys, urllib.request
URL = "http://127.0.0.1:8090/mcp"
def post(payload, sid=None):
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json"); req.add_header("Accept", "application/json, text/event-stream")
    if sid: req.add_header("Mcp-Session-Id", sid)
    with urllib.request.urlopen(req, timeout=120) as r:
        sid = r.headers.get("mcp-session-id", sid); body = r.read().decode()
    msgs = []
    for line in body.splitlines():
        if line.startswith("data:"):
            try: msgs.append(json.loads(line[5:].strip()))
            except Exception: pass
    return sid, msgs
sid, _ = post({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}})
post({"jsonrpc":"2.0","method":"notifications/initialized"}, sid)
tool = sys.argv[1]
args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
if tool == "schema":
    _, m = post({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}, sid)
    for t in m[-1]["result"]["tools"]:
        if t["name"] in args.get("names", [t["name"]]): print(t["name"], json.dumps(t.get("inputSchema"), ensure_ascii=False)[:1500])
    sys.exit()
_, m = post({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":tool,"arguments":args}}, sid)
res = m[-1].get("result", m[-1])
for c in res.get("content", []) if isinstance(res, dict) else []:
    print(c.get("text", c))
if not isinstance(res, dict) or "content" not in res: print(json.dumps(res, ensure_ascii=False)[:3000])
