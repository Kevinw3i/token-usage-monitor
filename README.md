# Codex + Claude 用量桌面小工具

一個 [Übersicht](https://tracesof.net/uebersicht/) 桌面 widget,在 macOS 桌面上同時顯示 **OpenAI Codex** 與 **Claude Code** 的訂閱用量(5 小時視窗 + 每週視窗),不用再開兩個網頁切來切去。

- **九種視覺樣式**,滑到 widget 上即時切換,選擇會記住(預設 Neon)
- 每個 provider 一頁,顯示 **5H 用量 / 週用量 / 當前模型 / 方案**
- 每 60 秒自動刷新;數字 count-up、各樣式專屬動畫
- 取數只讀**本機** token、只打**官方** HTTPS、token 不外送

> 想先看長相不想裝?直接用瀏覽器開 `codex-claude-usage.widget/preview.html`(內含 demo 資料,可玩切換與動畫)。

---

## 需求

| 項目 | 說明 |
|---|---|
| macOS | 14 (Sonoma) 以上 |
| [Übersicht](https://tracesof.net/uebersicht/) | 桌面 widget 宿主(免費、開源) |
| Python 3 | 取數腳本用(macOS 內建 `/usr/bin/python3` 即可) |
| Codex CLI | 已登入(`~/.codex/auth.json` 存在) |
| Claude Code | 已登入(憑證在 macOS Keychain `Claude Code-credentials`) |

---

## 安裝

```bash
# 1. 安裝 Übersicht
brew install --cask ubersicht

# 2. 先開一次,讓它建立 widgets 目錄(並到「系統設定 → 隱私權與安全性 → 螢幕錄製」勾選 Übersicht)
open -a "Übersicht"

# 3. 把 widget 複製進 Übersicht 的 widgets 目錄
cp -R ~/Desktop/usage_monitor/codex-claude-usage.widget \
      ~/Library/Application\ Support/"Übersicht"/widgets/
```

最後在 Übersicht 選單列圖示 → **Refresh All Widgets**。Neon 樣式的用量小工具會出現在桌面右上角。

> **首次刷新**會跳一次 Keychain 授權視窗(widget 要讀你的 Claude 憑證)→ 按「**一律允許**」。

---

## 使用

- **切換樣式**:滑鼠移到 widget 上,上方會浮出 template 切換列,點任一個即時切換,選擇記在 `localStorage`(key `ccu.style`)。
- **切換 provider**:點 widget 內的分頁(Codex / Claude)。
- **桌面位置**:改 `codex-claude-usage.widget/index.jsx` 最上方的 `className`(`top` / `right` 等)。
- **刷新頻率**:改 `index.jsx` 的 `refreshFrequency`(毫秒,預設 `60000`)。

### 九種樣式

`Terminal` · `Glass` · `Brutalist` · `Neon`(預設) · `Luxury` · `Pixel` · `Quant` · `Paper` · `Bento`
(完整並排比較見 `usage-widget-styles.html`)

---

## 取數原理與安全

取數由 `codex-claude-usage.widget/lib/usage.py` 負責(`fetch-usage.sh` 只是入口):

| Provider | 端點 | Token 來源 | 主要欄位 |
|---|---|---|---|
| **Codex** | `GET https://chatgpt.com/backend-api/wham/usage` | `~/.codex/auth.json` → `tokens.access_token` / `account_id` | `rate_limit.primary_window`(5h)/`secondary_window`(週) → `used_percent`、`reset_after_seconds` |
| **Claude** | `GET https://api.anthropic.com/api/oauth/usage` | macOS Keychain `Claude Code-credentials` | `five_hour` / `seven_day` → `utilization`、`resets_at`(ISO 8601) |

**安全原則**:
- token 只在本機讀取、只用於打**官方** HTTPS 端點,**不外送第三方、不寫入 log、不印出**。
- 取數**失敗會自動退回 demo 資料**(widget 右上角顯示 `DEMO` 標記),不會壞掉。
- 每位使用者讀的是**自己機器**的 token,各看各的用量。

---

## 除錯 / 校準

印出兩邊**原始回應 JSON**(已自動遮蔽 email / account_id),用來確認欄位或診斷問題:

```bash
bash ~/Desktop/usage_monitor/codex-claude-usage.widget/lib/fetch-usage.sh --probe
```

常見問題:

| 症狀 | 可能原因 / 解法 |
|---|---|
| 一直顯示 `DEMO` | 取數失敗。跑上面的 `--probe` 看哪邊 `_error` |
| Claude `no claude token` | Keychain 授權沒給,或未用 Claude Code 登入。重跑並按「一律允許」 |
| Codex 那邊 `_error` | 確認 `codex` CLI 已登入(`~/.codex/auth.json` 存在且未過期) |
| widget 沒出現 | Übersicht 未給「螢幕錄製」權限,或沒 Refresh |
| `zsh: event not found` | 別用 `!` 開頭跑指令(那是 zsh 歷史展開) |

---

## 分享給同事

這個 widget 是純文字 jsx + Python,**不需簽章**:

1. 把整個 `codex-claude-usage.widget` 資料夾 zip 給同事(或讓他們 `git clone` 這個 repo)。
2. 同事各自:裝 Übersicht → 把資料夾丟進 widgets 目錄 → Refresh。
3. 每人讀**自己**機器的 token,各看各的用量;Claude 端首次會跳一次 Keychain 授權。

---

## 檔案結構

```
usage_monitor/
├── README.md                         本文件
├── usage-widget-styles.html          九種樣式並排比較頁(設計探索用)
└── codex-claude-usage.widget/        Übersicht widget 本體
    ├── index.jsx                     widget(九樣式 + 切換 + 動畫 + 取數整合)
    ├── preview.html                  瀏覽器驗收版(免裝 Übersicht 先看效果)
    └── lib/
        ├── fetch-usage.sh            取數入口(exec python3 usage.py)
        └── usage.py                  取數主邏輯(讀 token、打官方端點、輸出 JSON)
```

---

## 客製

- **改預設樣式**:`index.jsx` controller 裡 `localStorage.getItem('ccu.style') || 'neon'` 的 `'neon'` 改成其他 id(`term`/`glass`/`brut`/`neon`/`lux`/`pixel`/`quant`/`paper`/`bento`)。
- **新增 provider**:在 `lib/usage.py` 加一個 `xxx_provider()` 回傳 `{name, model, plan, h5:{pct,reset}, wk:{pct,reset}}`,append 進 `providers` 即可;widget 端會自動多一個分頁。
- **樣式同步注意**:`usage-widget-styles.html` 與 `index.jsx` 用的是同一套九樣式 CSS/模板,改樣式時兩邊要一起改。
