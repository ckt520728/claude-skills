---
name: medagentbench-setup
description: "在 Windows 11 / PowerShell 上從零部署 Stanford MedAgentBench(虛擬 EHR / FHIR 環境下評測 LLM agent)。一條龍流程:clone repo、conda Python 3.9 環境、Docker 拉 HAPI FHIR 模擬病歷資料庫、Stanford Box 下載 refsol.py、設定 OpenAI/Gemini/Claude API key、起 20 個 task worker、跑 assigner 派 100 道題、讀 overall.json。也內建所有實測踩坑(importlib_metadata 缺、agent_test 是互動 REPL、PowerShell 剪貼簿黏連、Docker container 命名陷阱、FHIR 啟動訊號判讀)。觸發詞:「裝 MedAgentBench」「部署 MedAgentBench」「Stanford MedAgent」「FHIR LLM agent benchmark」「跑 medagentbench」「測試醫療 LLM agent」「虛擬 EHR 評測」「HAPI FHIR 模擬病歷」「benchmark medical agent」「跑 LLM on FHIR」「s41591 medagent」。不適用:其他醫療 benchmark(MedQA、MedMCQA — 那是純 QA,不是 agent)、真實 EHR 接入(本 skill 只用模擬資料)、自訓醫療 LLM(本 skill 是評測,不是訓練)。先決條件:Docker Desktop 已裝(沒裝先用 [[install-docker-desktop-windows]])、有 OpenAI/Gemini/Claude API key、C 槽 >= 15 GB。"
---

# MedAgentBench 部署 Skill (Windows)

從 `git clone` 到 `overall.json` 出來,Stanford 的 [MedAgentBench](https://github.com/stanfordmlgroup/MedAgentBench) 完整部署流程。NEJM AI 2025 publication 對應 codebase。

---

## 🚨 鐵則

1. **Docker Desktop 必須先就緒** — 鯨魚圖示要綠且穩定。沒裝先用 [[install-docker-desktop-windows]]
2. **Python 一定要 3.9** — README 寫死,3.10+ 在 transformers 老版本上會掛
3. **refsol.py 不在 GitHub** — 含敏感資料,必須從 Stanford Box 下載
4. **需要 3 個 PowerShell 視窗同時開** — Docker / task_workers / assigner,**任一關掉前面就斷**
5. **agent_test 是互動式 REPL** — 沒進 stdin 會掛住等 `>>>`,不代表壞掉
6. **OpenAI API 會真的扣錢** — 跑 100 題 gpt-4o-mini 大約 $0.5–$2,要心理準備

---

## Step 0 — 先決條件檢查

```powershell
docker --version          # 應印出 Docker version
docker ps                 # 應印出空表格(無 container 在跑)
conda --version           # 應印出 conda 版本
Get-PSDrive C | Select-Object @{N='Free(GB)';E={[math]::Round($_.Free/1GB,1)}}
```

若 docker 失敗 → 走 [[install-docker-desktop-windows]]
若 conda 失敗 → 裝 Anaconda 或 Miniconda
若 C 槽 < 15 GB → 先清

---

## Step 1 — Clone repo + 建 Python 環境

```powershell
cd C:\Users\User\
git clone https://github.com/stanfordmlgroup/MedAgentBench.git
cd MedAgentBench
conda create -n medagentbench python=3.9 -y
conda activate medagentbench
pip install -r requirements.txt
```

**踩坑預警:** requirements.txt 不含 `importlib_metadata`,但 transformers 老版本在 Python 3.9 需要它。看到下面這段錯誤就補裝:

```
RuntimeError: Failed to import transformers.generation.utils
No module named 'importlib_metadata'
```

修法:
```powershell
pip install importlib_metadata
```

---

## Step 2 — 啟動模擬 FHIR Database

### 拉 image + 跑 container

```powershell
docker pull jyxsu6/medagentbench:latest
docker tag jyxsu6/medagentbench:latest medagentbench
docker run -p 8080:8080 medagentbench
```

最後一行**會卡住執行**(這正常,FHIR server 在前景跑),這個 PowerShell 視窗**全程不能關**。

### 啟動成功訊號

當 log 出現這行,代表 FHIR ready:

```
Started Application in 28.456 seconds (process running for 29.123)
```

(秒數會不一樣。)

### 瀏覽器驗證(關鍵步驟,不要跳過)

打開瀏覽器:

```
http://localhost:8080/fhir/Patient?_count=3
```

正確會看到 HTTP 200 + JSON Bundle,內含 Patient 物件(`resourceType: "Patient"`,有 id、name、extension)。

**不要靠 Docker Desktop GUI 判斷成功**:
- GUI 的綠燈不代表 FHIR API 真的能回應
- GUI 上可能會看到一個 `welcome-to-docker` container(port 8088),那是 Docker 安裝後預設的教學範例,**跟你的 FHIR 無關**
- 用 `docker ps` 在 PowerShell 看才看得全

### 預期會看到的無害 log

啟動後會持續刷:

```
WARN ... No mapping for GET /content/custom/logo.jpg
WARN ... No mapping for GET /content/custom/welcome.html
WARN ... No mapping for GET /favicon.ico
```

這是 HAPI 找不到自訂 UI 圖片的裝飾性 404,**不影響 API**。

---

## Step 3 — 下載 refsol.py(評分標準)

`refsol.py` 含 100 題 ground truth,**不在 GitHub repo 內**。

連結(README 提供):
```
https://stanfordmedicine.box.com/s/fizv0unyjgkb1r3a83rfn5p3dc673uho
```

下載後**放到**:
```
C:\Users\User\MedAgentBench\src\server\tasks\medagentbench\refsol.py
```

驗證:
```powershell
$f = 'C:\Users\User\MedAgentBench\src\server\tasks\medagentbench\refsol.py'
if (Test-Path $f) { "size = $((Get-Item $f).Length) bytes" } else { "MISSING" }
```

正常會看到約 15,000 bytes。

---

## Step 4 — 設定 API Key

編輯:
```powershell
notepad C:\Users\User\MedAgentBench\configs\agents\openai-chat.yaml
```

第 6 行:
```yaml
Authorization: Bearer [YOUR OPENAI API HERE]
```

把 `[YOUR OPENAI API HERE]` 換成實際 key(`Bearer ` 後留一個空格):
```yaml
Authorization: Bearer sk-proj-xxxxxxxxxxxxxxxxxxxx
```

存檔關閉。

其他 model 對應 yaml:
- Gemini:`configs/agents/gemini-chat.yaml`(需 `gcloud auth print-access-token` 拿 token)
- Claude(Vertex AI):`configs/agents/claude-chat.yaml`(同上)

---

## Step 5 — agent_test 是互動 REPL,**不是測試腳本**

```powershell
python -m src.client.agent_test
```

這個指令的**正確行為**:
1. Import 全部 dependencies(沒錯就代表環境 OK)
2. 載入 yaml 設定、建 AgentClient
3. **進入互動式 REPL**,印 `>>> ` 等你打字
4. 你打什麼就轉發給 LLM,印回應

**沒看到任何錯誤 = 設定完備**。看到 `>>>` 提示時:
- 想試一下:打 "hello" 看 LLM 回應
- 想結束:按 `Ctrl+C`

**不要把它當 "跑一次測試就退出" 的指令**,它不會自動結束。

如果你在自動化腳本裡 pipe 它,它會在 stdin 用完時 hang 住等輸入。

---

## Step 6 — 三視窗開跑

### 視窗 #1(已開):FHIR Server

仍然是 Step 2 那個跑 `docker run` 的視窗,**不關**。

### 視窗 #2:Task Workers

```powershell
cd C:\Users\User\MedAgentBench
conda activate medagentbench
python -m src.start_task -a
```

會在 port 5000-5015 起 20 個 worker。**等大約 1 分鐘**,看到 log 出現 `200 OK`,代表 ready。**這個視窗也不關**。

注意 port 5000 在 macOS 上常被 AirPlay 佔用;Windows 一般沒這問題。

### 視窗 #3:Assigner(派題)

```powershell
cd C:\Users\User\MedAgentBench
conda activate medagentbench
python -m src.assigner
```

派 `test_data_v2.json` 的 100 道題。`max_round=8`,每題最多 8 輪 agent–FHIR 互動。會跑數十分鐘到一兩小時(視 model 速度)。

跑完會自動結束。

---

## Step 7 — 讀結果

```
C:\Users\User\MedAgentBench\outputs\MedAgentBenchv1\gpt-4o-mini\medagentbench-std\overall.json
```

裡面是 100 題 task-by-task 的 score(0/1)、agent 對話 trace、FHIR API 呼叫紀錄。

簡單看通過率:
```powershell
$r = Get-Content 'C:\Users\User\MedAgentBench\outputs\MedAgentBenchv1\gpt-4o-mini\medagentbench-std\overall.json' | ConvertFrom-Json
$r | Format-Table -AutoSize
```

---

## 🪦 踩坑紀錄

### 坑 1:`No module named 'importlib_metadata'`

README requirements.txt 漏了。pip install 補一個即可。在 transformers ≥ 4.40 + Python 3.9 環境特別常見。

### 坑 2:agent_test 永遠不結束

它是 REPL。不是 bug。詳見 Step 5。

### 坑 3:PowerShell 剪貼簿黏連

從文字編輯器或瀏覽器選取「指令 + 後文說明」一起 paste 到 PowerShell,指令會被串接成怪東西:

```
docker run -p 8080:8080 medagentbenchStarted Application in XX seconds
                                    ↑ 多選了說明文字
```

Docker 把整串當 image 名稱,報:
```
docker: invalid reference format: repository name (library/medagentbenchStarted) must be lowercase
```

修法:
- PowerShell 按 `Esc` 清行
- **手動逐字輸入**指令,或寫成 .ps1 腳本

### 坑 4:Docker Desktop GUI 顯示的 `welcome-to-docker` 不是你的服務

那是教學範例 container(port 8088:80),Docker Desktop 安裝時自動跑的。跟 MedAgentBench 的 FHIR(port 8080:8080)沒關係。**忽略**。`docker ps` 在 PowerShell 才看得全。

### 坑 5:FHIR 已就緒卻不是綠燈,但 HTTP 200 拿到了

Docker Desktop GUI 的 status indicator 跟 HAPI FHIR 內部就緒度不完全同步。**判斷標準是瀏覽器拿到 HTTP 200 + JSON Patient bundle**,GUI 顏色當參考即可。

### 坑 6:Stanford Box 下載按鈕找不到

Box 的 UI 有時把 Download 按鈕藏在 `...` 選單。如果頁面顯示 preview 但沒 download,點右上角的 `Download` 文字按鈕,或頁面上 `Download` icon。

### 坑 7:`open //./pipe/docker_engine` — Docker daemon 連不上

Docker CLI 找到了、但 Docker Desktop 應用程式沒在跑。從開始選單啟動 Docker Desktop,等鯨魚變綠後重跑。

### 坑 8:8080 port 被佔用

很少見,但若你有跑其他 server 在 8080(常見:Tomcat、其他 HAPI、Jenkins):
```powershell
netstat -ano | findstr :8080
```
看哪個 PID 佔用,停掉。或改 docker run 的 port mapping(同時要改 `configs/tasks/medagentbench.yaml` 的 `fhir_api_base`)。

---

## 整體資料流(心智模型)

```
[Assigner]─派題─▶[Task Server: 20 workers]◀─agent action──[LLM via API]
                       │                                        │
                       ├──模擬病歷讀寫─▶[FHIR DB Docker:8080]
                       │
                       └─[refsol.py 評分]─▶ overall.json
```

---

## 何時觸發此 skill

- 使用者要在 Windows 跑 MedAgentBench / Stanford 醫療 agent benchmark
- 使用者問「怎麼裝模擬 FHIR」「我要 benchmark 我的醫療 LLM」
- 使用者要重現 *NEJM AI* 2025 那篇 MedAgentBench paper 的結果
- 使用者 clone 了 stanfordmlgroup/MedAgentBench 但 README 卡住
- 使用者跑 `pip install -r requirements.txt` 後跑 `agent_test` 報 `importlib_metadata` 錯

## 連結

- Paper:https://ai.nejm.org/doi/full/10.1056/AIdbp2500144
- GitHub:https://github.com/stanfordmlgroup/MedAgentBench
- refsol.py:https://stanfordmedicine.box.com/s/fizv0unyjgkb1r3a83rfn5p3dc673uho
- Docker image:`jyxsu6/medagentbench:latest`(Docker Hub)
