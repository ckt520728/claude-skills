---
name: mcp-obsidian-setup
description: Use this skill whenever the user wants to install, configure, debug, or troubleshoot the mcp-obsidian MCP server (connecting Claude Code to Obsidian), or encounters general MCP server problems like "Authentication expired" (especially when nlm login appears successful but tools still fail), file lock errors during MCP CLI upgrades (os error 32), version mismatches between MCP CLI and a remote backend (e.g., notebooklm-mcp-cli vs Google's batchexecute API returning HTTP 200 with empty wrb.fr response), or wants to verify which Obsidian vault is actually being used. Also trigger when the user mentions Obsidian Local REST API plugin setup, NotebookLM MCP connection failures, "MCP not connecting / not showing up" in /mcp, or wants the manual workaround when NotebookLM MCP cannot be fixed (manual export from notebooklm.google.com). Triggers include phrases like "連接 Obsidian"、"安裝 MCP"、"MCP 沒反應"、"Local REST API"、"MCP 升級失敗"、"NotebookLM 連不上"、"vault 路徑不對"、"認證過期"、"refresh_auth 沒用"、"nlm login 完還是失敗"、"os error 32"、"file lock"、"檔案鎖".
---

# MCP Obsidian 安裝與疑難排解（針對 Claude Code on Windows）

這份 skill 記錄了實際踩過的坑與已驗證的解法。內容針對 Windows + uv/uvx 環境。

---

## 第一部分：mcp-obsidian 完整安裝流程

### 步驟 1：安裝 Obsidian Local REST API 外掛

1. 在 Obsidian 內：**設定 → 社群外掛 → 瀏覽**，搜尋 `Local REST API`（作者 coddingtonbear），安裝並啟用
2. 進入該外掛設定頁面，複製 **API Key**（很長一串）
3. Port 預設 `27124`（HTTPS）

⚠️ **不要去 Swagger 文件網站找 API Key**——那是讓你**測試** API 用的，不是發 key 的地方。Key 只在 Obsidian 應用程式內部的外掛設定頁。

### 步驟 2：先驗證 vault 路徑（避免最常見的坑）

**Windows 的 Obsidian vault 設定檔位置**：
```
C:\Users\<USER>\AppData\Roaming\obsidian\obsidian.json
```

用以下指令列出所有已知的 vault 路徑：

```bash
cat "/c/Users/<USER>/AppData/Roaming/obsidian/obsidian.json" | python -c "import json,sys; d=json.load(sys.stdin); [print(k, '=>', v.get('path','?')) for k,v in d.get('vaults',{}).items()]"
```

⚠️ **常見陷阱**：使用者可能有多個同名 vault（例如 `C:\Users\User\Second Brain` 和 `G:\我的雲端硬碟\Second Brain`），但 Obsidian 實際開啟的只有一個。Claude Code 的工作目錄可能跟 Obsidian 開啟的 vault **不同**——這會造成 MCP 操作的檔案跟 Claude Code 直接讀寫的檔案是兩份不同的副本，越用越混亂。

**驗證實際開啟的 vault**：用 API 列出 vault 內容，跟檔案系統比對：

```bash
curl -k -s -H "Authorization: Bearer <API_KEY>" https://127.0.0.1:27124/vault/
```

如果回傳的檔案清單跟你預期的工作目錄不一致，代表 Obsidian 開的是另一個 vault。此時必須二選一：
- (A) 在 Obsidian 切換到正確 vault
- (B) 改變 Claude Code 工作目錄到 Obsidian 開的那個 vault

### 步驟 3：寫入 ~/.claude.json

**先備份**：

```bash
cp ~/.claude.json ~/.claude.json.backup-$(date +%Y%m%d-%H%M%S)
```

用 Python 安全地新增 `mcpServers` 區塊（直接編輯 JSON 容易破壞結構）：

```python
import json, os
path = os.path.expanduser('~/.claude.json')
with open(path, 'r', encoding='utf-8') as f:
    d = json.load(f)
if 'mcpServers' not in d:
    d['mcpServers'] = {}
d['mcpServers']['mcp-obsidian'] = {
    'command': 'uvx',
    'args': ['mcp-obsidian'],
    'env': {
        'OBSIDIAN_API_KEY': '<KEY>',
        'OBSIDIAN_HOST': '127.0.0.1',
        'OBSIDIAN_PORT': '27124'
    }
}
with open(path, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
```

`mcpServers` 應該放在 JSON **最頂層**（不是嵌在 `projects.<path>` 底下）——這樣所有專案都能用。

### 步驟 4：重啟 Claude Code 並驗證

完全關閉 Claude Code 再開，然後在對話框輸入 `/mcp`，應該看到：

```
mcp-obsidian    ✓ connected    12 tools
```

⚠️ **不要在 Obsidian 的外掛清單找 mcp-obsidian**——它是 **Claude Code 的 MCP server**，不是 Obsidian 外掛。Obsidian 那邊只會看到 Local REST API。

`uvx` 第一次執行 `mcp-obsidian` 會自動下載套件（約 35 個依賴），等 10–30 秒。

---

## 第二部分：mcp-obsidian 已知行為陷阱

### 空資料夾不會出現

Local REST API 只列出**包含 .md 檔案**的資料夾。空資料夾會被當成不存在，呼叫 `obsidian_list_files_in_dir` 時會得到 `404`。這不是 bug，是 API 設計。

### Obsidian 必須保持開啟

Local REST API 是 Obsidian 的**外掛**，不是獨立服務。Obsidian 一關，REST API 就死，所有 MCP 工具會失敗。

### 列表只看到部分檔案

如果 `obsidian_list_files_in_vault` 回傳的內容比實際檔案系統少很多，先檢查：
1. Obsidian 開的 vault 是不是預期的那個（見上方 vault 路徑陷阱）
2. 是不是有大量空資料夾（不會被列出）

---

## 第三部分：MCP server 升級的「檔案鎖」陷阱（通用，不限 mcp-obsidian）

### 症狀

升級任何已安裝的 MCP server CLI 時，例如：

```bash
uv tool install --force notebooklm-mcp-cli@latest
```

跑出錯誤：

```
error: Failed to install entrypoint
Caused by: failed to copy file from ...\AppData\Roaming\uv\tools\<name>\Scripts\<name>.exe
to ...\.local\bin\<name>.exe: 程式無法存取檔案，因為檔案正由另一個程序使用。
(os error 32)
```

### 根本原因

**Claude Code 啟動時會把所有 MCP server 的 .exe 載入記憶體並鎖住**。當你 `uv tool install --force` 時，套件本身已經更新到 `AppData\Roaming\uv\tools\`，但要把新 `.exe` 複製到 `.local\bin\` 覆蓋舊版時，因為舊版正在運行，Windows 不允許覆蓋。

### 解法 A：終止子程序（不需關閉 Claude Code）

```bash
# 找出 PID
tasklist | grep -i "<mcp-name>"

# 用 cmd 包裝（直接在 Git Bash 用 taskkill /F 會把 / 當路徑）
cmd //c "taskkill /F /PID <PID1> & taskkill /F /PID <PID2>"
```

殺掉後**立即**回終端機跑升級指令，要快——只要在 Claude Code 又呼叫該 MCP 工具，子程序會被重新啟動，鎖又回來。

### 解法 B：完全關閉 Claude Code

最保險但最麻煩——關閉 Claude Code，跑升級，再開。如果 Claude Code 有未完成對話會中斷。

### 防範策略

**先升級，再用**。每次發現某個 MCP server 有新版時，趁還沒呼叫它的工具就先升級，避免被自己鎖住。

---

## 第四部分：MCP 認證問題（NotebookLM 為典型）

### 症狀

呼叫 MCP 工具時錯誤訊息：

```
Authentication expired. Run 'nlm login' in your terminal to re-authenticate.
```

或更早期版本（CLI 太舊）：

```
Failed to ...: Client error '400 Bad Request' for url 'https://notebooklm.google.com/...'
```

### 診斷流程

1. **先檢查版本**：

   ```
   呼叫 server_info 工具，看 update_available 是否為 true
   ```

   如果版本太舊，Google 後端的 RPC ID 可能已被廢棄，會出現 400 而不是明確的 401。**先升級**（用第三部分的解法）。

2. **升級後仍失敗 → 用 refresh_auth 工具**

   - 如果回傳 `Auth tokens reloaded from disk cache.`，**只代表從本地檔案重新讀取**——並沒有跟 Google 重新認證
   - 如果原本 token 是過期的，`refresh_auth` **無法救回來**

3. **真正的解法：在終端機跑 `nlm login`**

   - 會打開瀏覽器讓你登入 Google
   - 完成後本地 token 才真正更新
   - 之後 `refresh_auth` 才會有用

### 區分這兩件事很重要

| 動作 | 做什麼 | 何時用 |
|---|---|---|
| `nlm login`（CLI 指令） | 跟 Google 重新認證、寫入新 token | token 過期、第一次設定 |
| `refresh_auth`（MCP 工具） | 從硬碟讀本地 token 到記憶體 | 剛跑完 `nlm login` 後通知 MCP server 重載 |

### Layer 3：跑完 `nlm login` 後仍報「Authentication expired」（**最棘手**）

**症狀**：
- `nlm login` 成功，畫面顯示 `✓ Successfully authenticated! Cookies: 45 extracted`
- `metadata.json` 的 `last_validated` 時間戳很新（剛剛幾分鐘前）
- 但呼叫任何 notebook 工具仍報 `Authentication expired`
- `nlm login --check` 也報相同錯誤

**這時錯誤訊息在說謊**——cookies 其實完全有效。先驗證：

```python
import json, time, os
path = os.path.expanduser('~') + r'\.notebooklm-mcp-cli\profiles\default\cookies.json'
with open(path) as f:
    cookies = json.load(f)
now = time.time()
critical = [c for c in cookies if c['name'] in ('SID','SSID','HSID','APISID','SAPISID','__Secure-1PSID','__Secure-3PSID')]
for c in critical:
    exp = c.get('expires', -1)
    status = 'EXPIRED' if 0 < exp < now else 'OK'
    print(f"{c['name']:25s} -> {status}")
```

如果關鍵 cookies（SID、SSID、HSID、APISID、SAPISID、__Secure-1PSID、__Secure-3PSID）全部 OK，再用 `--debug` 看真實 HTTP 回應：

```bash
nlm --debug login --check
```

**關鍵特徵**：

```
Response Status: 200          ← HTTP 是 200，不是 401！
Raw response: [["wrb.fr","wXbhsf",null,null,null,[16],"generic"]]
                                       ^^^^ 應該是資料，但是 null
              [["e",4,null,null,142]]  ← Google 回傳的內部錯誤碼
```

**根本原因**：CLI 用的 RPC ID（`wXbhsf`）或 build label（`bl=boq_labs-tailwind-frontend_<日期>.<版本>_p0`）跟 Google 後端目前的版本不同步。Google 收到請求、認證通過、但回傳「協定不匹配」的空 response，CLI 把這個誤解讀成「認證過期」。

**這個情況 `nlm login` 永遠救不了**——再登入幾次都一樣。詳見第六部分。

---

## 第六部分：未解決問題 — NotebookLM CLI 與 Google 後端版本錯位

這是 2026-05-05 在 notebooklm-mcp-cli `0.6.4` 上實際遭遇、**目前無解**的狀況。寫進 skill 是為了讓未來的 Claude 不要浪費時間在錯誤的方向上鬼打牆。

### 症狀組合

- `server_info` 顯示已是最新版（0.6.4，update_available: false）
- `nlm login` 走完瀏覽器流程，回報 `Successfully authenticated`
- `metadata.json` 的 `csrf_token`、`session_id`、`email` 都齊全
- 45 個 cookies 全部有效，到 2027 年都不過期
- `--debug` 看 HTTP 200 + 空 wrb.fr response（見 Layer 3）
- 殺掉 MCP 子程序強制重啟仍無效
- `refresh_auth` 仍無效

### 嘗試過但沒用的修復路徑

| 動作 | 結果 |
|---|---|
| `uv tool install --force notebooklm-mcp-cli@latest` | 升到 0.6.4，仍失敗 |
| `nlm login` 重做一次 | 重新認證成功，仍失敗 |
| 殺掉 notebooklm-mcp.exe 強制重新生成子程序 | 仍失敗 |
| `refresh_auth` MCP 工具 | 只會印 `reloaded from disk cache`，仍失敗 |

### 什麼可能會幫助（未驗證）

- **`nlm login --clear --force`**：完全清空 profile 後重新登入。值得試但不保證。
- **等 CLI 出新版**：套件作者需要把 RPC ID/build label 更新到對應 Google 最新後端。檢查方式：

  ```bash
  pip index versions notebooklm-mcp-cli   # 或瀏覽 GitHub release
  ```

- **直接用 `nlm` CLI 而非 MCP**：如果有些指令在 CLI 直接呼叫成功（即便 MCP 失敗），代表 MCP wrapper 有額外問題。

### 替代方案：手動匯出取代 MCP

當 NotebookLM MCP 無法用，但使用者真的需要 notebook 內容時，**不要繼續硬修 API**——改走以下路徑：

1. 使用者打開 [notebooklm.google.com](https://notebooklm.google.com)
2. 進入目標 notebook
3. 複製：
   - AI 摘要（notebook 開啟時左側面板）
   - 重要 sources 的標題與 quote
   - Q&A 對話紀錄（chat history）
4. 貼到 Claude Code 對話，或存成 .md 檔放到 vault
5. Claude 用這份手動匯出的內容繼續工作

這個方案 5 分鐘搞定，遠比繼續 debug API 有效率。

### 給未來的 Claude 的建議

如果你進入這個對話發現 NotebookLM 又在報 Authentication expired：

1. **跑一次 Layer 1+2 確認**（升級、refresh_auth、nlm login）——可能 CLI 已修好
2. **如果走完 Layer 3 還是 200+空 response → 立刻停止 debug**，告訴使用者狀況並提議手動匯出方案
3. **不要再對使用者下「重做 nlm login」的指令**——已知無效，浪費他們的時間

---

## 第五部分：診斷檢查清單（疑難排解時依序跑）

當使用者說「MCP 連不上」或「MCP 沒反應」時：

1. **MCP server 有沒有出現在 `/mcp` 清單？**
   - 沒有 → 檢查 `~/.claude.json` 的 `mcpServers` 區塊
   - 有但顯示 `failed` → 看下面

2. **`server_info` 工具回傳什麼？**
   - 失敗 → server 根本沒啟動，看 stderr/log
   - 成功但 `update_available: true` → 先升級
   - 成功且最新 → 可能是認證問題

3. **認證問題 → `refresh_auth`，再用一次**
   - 成功 → 應該已經修好
   - 仍失敗 → 在終端機跑 `nlm login`（或對應 CLI）
   - **跑完 nlm login 還是失敗** → 用 `nlm --debug login --check` 看真實 HTTP 回應；如果是 200 + 空 wrb.fr response，那是 API 版本錯位（第六部分），**直接改用手動匯出方案**，不要再 debug

4. **針對 mcp-obsidian 額外檢查**
   - Obsidian 是否開啟？
   - Obsidian 開的 vault 是不是預期的？（用 `obsidian.json` 比對）
   - Local REST API 外掛是否啟用？
   - API Key 是否還有效？

5. **檔案鎖症狀（升級時 os error 32）**
   - 用 `tasklist | grep <name>` 找 PID
   - `cmd //c "taskkill /F /PID <PID>"`
   - 立刻重跑升級指令

---

## 附錄：Git Bash 在 Windows 上常見的小坑

- `taskkill /F /PID 1234` → Bash 把 `/F` 當路徑。改用 `cmd //c "taskkill /F /PID 1234"`
- `~/.claude.json` 在 Python 內要用 `os.path.expanduser('~/.claude.json')`，不要直接用 `/c/Users/<USER>/...`（Python 不認 Git Bash 的路徑映射）
- 編輯 JSON 一律先備份再用 Python 處理，別用 `sed`

---

## 為什麼這份 skill 這樣寫

這些坑都來自實際踩過一輪。最容易卡住的不是技術問題本身，而是「症狀指向的方向是錯的」：
- 「找不到 API Key」其實是看錯網站（Swagger ≠ 外掛設定）
- 「MCP 沒連上」其實是 Obsidian 開了另一個同名 vault
- 「升級失敗」其實是自己鎖住自己
- 「重新認證沒用」其實是 `refresh_auth` 跟 `nlm login` 是兩件事
- 「Authentication expired」**不一定**真的是認證問題——也可能是 CLI 與 Google 後端版本錯位（第六部分）

把症狀對應到正確的根本原因，比任何具體指令都重要。

## 誠實聲明

這份 skill **沒有完全解決 NotebookLM MCP 的問題**。從 0.5.16 升到 0.6.4、走完完整 nlm login、清掉子程序快取、驗證 cookies 全部有效——做完這一切之後，notebook_list 仍然失敗。第六部分記錄了這個無解狀態，並建議遇到時直接走手動匯出方案，不要再循環嘗試已知無效的修復步驟。

寫這段話是為了：
1. 給未來的 Claude 一個明確的「停損點」，避免重蹈覆轍
2. 對使用者誠實——skill 不是萬能的，有些問題的解法在 skill 之外（套件作者修 bug、Google 改 API）
3. 把 skill 當成「結構化的失敗報告」而不只是「成功手冊」——失敗的記錄同樣有價值

---

## 變更紀錄

- **2026-05-05 v1.0** — 初版，涵蓋 mcp-obsidian 完整安裝、檔案鎖、認證 Layer 1+2、診斷清單
- **2026-05-05 v1.1** — 加入 Layer 3（200 OK + 空 response）診斷與第六部分（NotebookLM CLI 與 Google 後端版本錯位的無解狀態與替代方案）
