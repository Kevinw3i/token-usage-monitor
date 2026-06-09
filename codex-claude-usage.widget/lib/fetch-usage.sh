#!/usr/bin/env bash
# 取數入口:呼叫 usage.py(讀本機 token、只打官方 HTTPS、token 不外送/不印)。
# 真實取數成功 → 真資料;失敗 → demo。
# 校準欄位:  bash fetch-usage.sh --probe   (印兩邊原始 JSON;分享前請遮掉疑似 token 的長字串)
DIR="$(cd "$(dirname "$0")" && pwd)"
exec /usr/bin/python3 "$DIR/usage.py" "$@"
