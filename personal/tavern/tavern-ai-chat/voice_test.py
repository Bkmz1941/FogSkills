import json, re, time, urllib.request
src = open('/media/ilya/T714/Unity/Tavern-fresh/Assets/Game/UI/LlmBridge.cs').read()
def cs(block):
    return ''.join(json.loads('"%s"' % m) for m in re.findall(r'"((?:[^"\\]|\\.)*)"', block))
rules = cs(re.search(r'Rules =(.*?),\n\s*Agents', src, re.S).group(1))
prompts = [cs(m) for m in re.findall(r'Prompt =(.*?),\n\s*\},', src, re.S)]
TESTS = ["алло помогите", "я в доме в лесу, все пропали", "тут кто-то ходит вокруг дома в тумане", "ты бот?", "my friends are gone, please help"]
def ask(h):
    b = json.dumps({"model": "qwen3:8b", "messages": h, "stream": False, "think": False, "options": {"temperature": 0.8, "num_predict": 90, "repeat_penalty": 1.15}}).encode()
    with urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:11434/api/chat", b, {"Content-Type": "application/json"}), timeout=180) as r:
        return json.load(r)["message"]["content"].strip()
for name, p in zip(["ДЕНЬ", "НОЧЬ"], prompts):
    h = [{"role": "system", "content": rules + "\n" + p}]
    print("=====", name)
    for msg in TESTS:
        h.append({"role": "user", "content": msg}); t = time.time(); r = ask(h); h.append({"role": "assistant", "content": r})
        print("> %s\n< (%.1fs) %s" % (msg, time.time() - t, r))
