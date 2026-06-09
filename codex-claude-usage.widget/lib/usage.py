#!/usr/bin/env python3
# =============================================================
#  Codex + Claude 用量取數 → 輸出 widget 用 JSON
#  · 只讀本機 token、只打官方 HTTPS、token 不外送 / 不印出
#  · 真實取數成功 → 用真資料;全部失敗 → demo(標 demo:true)
#  · 校準模式:  python3 usage.py --probe
#       印兩邊「原始回應 JSON」供確認欄位名(分享前請遮掉任何
#       疑似 token 的長字串;此端點回應通常只含百分比/時間/方案)
#  端點來源:Codex = /backend-api/wham/usage;Claude = /api/oauth/usage
# =============================================================
import json, os, sys, time, urllib.request
from datetime import datetime, timezone

PROBE = "--probe" in sys.argv
NOW = int(time.time())

def read_json(path):
    try:
        with open(os.path.expanduser(path)) as f:
            return json.load(f)
    except Exception:
        return None

def http_get(url, headers, timeout=6):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def fmt_reset(secs):
    if secs is None:
        return ""
    secs = max(0, int(secs))
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    if d:
        return f"{d}d {h:02d}h"
    if h:
        return f"{h}h {m:02d}m"
    return f"{m}m"

def iso_to_secs(s):
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return int((dt - datetime.now(timezone.utc)).total_seconds())
    except Exception:
        return None

def win(obj):
    """把一個 window 物件正規化成 {pct, reset}。"""
    if not isinstance(obj, dict):
        return None
    pct = obj.get("used_percent", obj.get("usedPercent", obj.get("utilization")))
    if pct is None:
        return None
    secs = obj.get("reset_after_seconds", obj.get("resets_in_seconds", obj.get("seconds_until_reset")))
    if secs is None:
        ra = obj.get("reset_at", obj.get("resets_at", obj.get("resetsAt")))
        if isinstance(ra, str):
            secs = iso_to_secs(ra)
        elif ra:
            secs = ra - NOW
    return {"pct": round(pct), "reset": fmt_reset(secs)}

# ---------- Codex ----------
def codex_raw():
    auth = read_json("~/.codex/auth.json")
    tok = (auth or {}).get("tokens", {}).get("access_token")
    acct = (auth or {}).get("tokens", {}).get("account_id")
    if not tok:
        raise RuntimeError("no codex token")
    headers = {"Authorization": f"Bearer {tok}", "User-Agent": "usage-widget"}
    if acct:
        headers["ChatGPT-Account-Id"] = acct
    return http_get("https://chatgpt.com/backend-api/wham/usage", headers)

def codex_model():
    try:
        with open(os.path.expanduser("~/.codex/config.toml")) as f:
            for line in f:
                s = line.strip()
                if s.startswith("model") and "=" in s:
                    return s.split("=", 1)[1].strip().strip('"').strip("'").upper()
    except Exception:
        pass
    return "Codex"

def codex_provider():
    d = codex_raw()
    rl = d.get("rate_limit") or d.get("rateLimit") or d
    h5 = win(rl.get("primary_window") or rl.get("primary"))
    wk = win(rl.get("secondary_window") or rl.get("secondary"))
    if not (h5 and wk):
        return None
    plan = str(d.get("plan_type") or d.get("planType") or rl.get("planType") or "Pro").title()
    return {"name": "Codex", "model": codex_model(), "plan": plan, "h5": h5, "wk": wk}

# ---------- Claude ----------
def claude_token():
    # 1) 檔案
    cred = read_json("~/.claude/.credentials.json")
    if cred:
        o = cred.get("claudeAiOauth") or cred
        t = o.get("accessToken") or o.get("access_token")
        if t:
            return t
    # 2) macOS Keychain(Claude Code 預設把憑證存這裡)
    try:
        import subprocess
        r = subprocess.run(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
            capture_output=True, text=True, timeout=8)
        raw = (r.stdout or "").strip()
        if raw:
            try:
                o = json.loads(raw)
                o = o.get("claudeAiOauth") or o
                return o.get("accessToken") or o.get("access_token")
            except Exception:
                return raw  # 萬一直接就是 token 字串
    except Exception:
        pass
    return None

def claude_raw():
    tok = claude_token()
    if not tok:
        raise RuntimeError("no claude token (檔案與 Keychain 皆讀不到)")
    headers = {"Authorization": f"Bearer {tok}", "anthropic-beta": "oauth-2025-04-20", "User-Agent": "usage-widget"}
    return http_get("https://api.anthropic.com/api/oauth/usage", headers)

def claude_provider():
    d = claude_raw()
    h5 = win(d.get("five_hour") or d.get("fiveHour"))
    wk = win(d.get("seven_day") or d.get("sevenDay") or d.get("weekly"))
    if not (h5 and wk):
        return None
    plan = d.get("plan") or d.get("plan_type") or "Max"
    return {"name": "Claude", "model": "Opus 4.8", "plan": plan, "h5": h5, "wk": wk}

# ---------- main ----------
if PROBE:
    out = {}
    for name, fn in (("codex", codex_raw), ("claude", claude_raw)):
        try:
            out[name] = fn()
        except Exception as e:
            out[name] = {"_error": str(e)}
    cx = out.get("codex")          # 遮蔽個資,供安全分享
    if isinstance(cx, dict):
        for k in ("email", "user_id", "account_id"):
            cx.pop(k, None)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    sys.exit(0)

providers = []
for fn in (codex_provider, claude_provider):
    try:
        p = fn()
        if p:
            providers.append(p)
    except Exception:
        pass

if providers:
    print(json.dumps({"demo": False, "providers": providers}, ensure_ascii=False))
else:
    print(json.dumps({"demo": True, "providers": [
        {"name": "Codex",  "model": "GPT-5.5",  "plan": "Pro",     "h5": {"pct": 67, "reset": "1h 24m"}, "wk": {"pct": 42, "reset": "4d 06h"}},
        {"name": "Claude", "model": "Opus 4.8", "plan": "Max 20×", "h5": {"pct": 38, "reset": "2h 51m"}, "wk": {"pct": 73, "reset": "3d 12h"}},
    ]}, ensure_ascii=False))
