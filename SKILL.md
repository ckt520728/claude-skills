---
name: install-docker-desktop-windows
description: "在 Windows 11 上從零安裝 Docker Desktop 的完整 skill,含磁碟空間預檢、官方下載直連、WSL 2 設定、PATH 更新時機、與所有實測踩過的坑(welcome-to-docker 教學容器誤認、pipe/docker_engine 連線錯誤、PowerShell 終端剪貼簿黏連)。觸發詞:「裝 Docker」「Docker Desktop 安裝」「install Docker on Windows」「無法辨識 docker 詞彙」「docker: command not found Windows」「pipe/docker_engine 錯誤」「docker daemon 連不上」「Docker Desktop 怎麼裝」「Windows 跑 Docker container」。也適用於:Docker Desktop 裝完之後 docker 指令仍找不到、安裝程式顯示空間不足、不確定要不要勾 WSL 2。不適用:Linux 上裝 Docker Engine(那是另一套)、Docker Hub 帳號管理、Kubernetes(k8s)安裝。"
---

# Install Docker Desktop on Windows

從零到 `docker ps` 印出表格,Windows 11 上 Docker Desktop 完整安裝流程。**4 個常見坑位**全部列在每一步。

---

## 🚨 鐵則

1. **先檢查 C 槽空間** — 不足 10 GB 不要開始裝,安裝程式會中斷
2. **WSL 2 必選** — 預設勾選不要拿掉,Hyper-V 後端在 Windows 11 已是次等選項
3. **裝完必重開機** — 沒有重開機 PATH 不會更新,新開的 PowerShell 也找不到 docker
4. **驗證用「新開」的 PowerShell** — 老視窗的 PATH 是安裝前的,看不到新加的 docker

---

## Step 1 — 預檢磁碟空間

```powershell
Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Name -eq 'C' } | Select-Object Name, @{N='Free(GB)';E={[math]::Round($_.Free/1GB,1)}}, @{N='Total(GB)';E={[math]::Round(($_.Used+$_.Free)/1GB,1)}}
```

**最小空間需求:**
- Docker Desktop 安裝本體:約 4 GB
- WSL 2 distro(預設):約 1-2 GB
- Image 快取緩衝:建議 5+ GB
- → **至少騰出 10 GB**,建議 15 GB 以上

空間不足怎麼辦:
- 清空資源回收筒
- 清 `C:\Users\User\AppData\Local\Temp`
- 清 conda pkgs cache(`conda clean --all --yes`)
- 清 pip cache(`pip cache purge`)
- 把 `C:\Users\User\Downloads` 大檔搬到 D 槽

---

## Step 2 — 直接從官方 CDN 下載

**不要走 docker.com 首頁的下載按鈕**,那個會把你導到「You're almost done!」頁面,試圖呼叫已安裝的 Docker Desktop(對你沒裝的人無效)。

直接點這個 CDN 連結:

```
https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe
```

檔案約 1 GB,檔名 `Docker Desktop Installer.exe`。

**建議下載到 D 槽**(避免污染 C\Downloads)。如果預設下載到 C,裝完手動刪掉 .exe 即可。

---

## Step 3 — 執行安裝

1. 雙擊 `Docker Desktop Installer.exe`
2. 安裝對話框會問:
   - **Use WSL 2 instead of Hyper-V** → ✅ **保留勾選**
   - Add shortcut to desktop → 可勾可不勾
3. 點 OK,等 3-5 分鐘
4. 結束時會要求**登出或重開機**

**必須重開機**,否則:
- PATH 環境變數不會 reload → `docker` 指令找不到
- WSL 2 整合的後端服務不會起來

---

## Step 4 — 啟動 Docker Desktop

重開機後:

1. 開始選單搜尋 `Docker Desktop`,啟動
2. 第一次跑會:
   - 同意服務條款 → Accept
   - 可能要求登入 Docker Hub 帳號 → 可點 **"Continue without signing in"**(不需要帳號就能用)
3. 等右下角系統匣的鯨魚圖示**從動態變成靜止**,代表 daemon 就緒(約 1-2 分鐘)

---

## Step 5 — 驗證

**必須開「全新」的 PowerShell**(不要用安裝前打開的舊視窗):

```powershell
docker --version
docker ps
```

- `docker --version` 印出版本號(例如 `Docker version 27.x.x`)
- `docker ps` 印出空表格(沒有 container 在跑,正常)

兩個都過 = 完成。

---

## 🪦 踩坑紀錄

### 坑 1:`open //./pipe/docker_engine: The system cannot find the file specified`

**症狀:** 跑 `docker pull/run` 出現上面這段。

**原因:** Docker CLI 找得到、但 Docker Desktop 應用程式沒在跑,daemon 連不上。

**解法:** 開始選單啟動 Docker Desktop,等右下角鯨魚變綠(靜止),再跑指令。

### 坑 2:`無法辨識 'docker' 詞彙`(中文 PowerShell 錯誤)

**症狀:** 全新安裝完跑 `docker --version`,PowerShell 說找不到指令。

**原因 A:** 沒重開機,PATH 沒更新。 → **重開機**。

**原因 B:** 開的是裝 Docker **之前**就已經打開的舊 PowerShell。 → **關掉,開新的**。

**原因 C:** 安裝沒完成或安裝路徑壞掉。 → 確認 `C:\Program Files\Docker\Docker\resources\bin\docker.exe` 存在。

### 坑 3:Docker Desktop 顯示的 "welcome-to-docker" 不是你拉的 image

**症狀:** 安裝完打開 Docker Desktop GUI,Containers 頁籤裡看到一個 `welcome-to-docker` container 在 port 8088:80,使用者誤以為是自己拉的服務。

**原因:** 那是 Docker Desktop 首次安裝時內建的教學範例,port 是 8088(不是常用的 8080),image 是 `docker/welcome-to-docker`。

**解法:** 跟自己拉的 image 無關,可以無視或停掉。`docker ps` 在 PowerShell 才看得到全部 container 的全貌。

### 坑 4:你的指令意外被「黏」上後續貼上的文字(剪貼簿陷阱)

**症狀:** 在 PowerShell 跑 `docker run -p 8080:8080 medagentbench`,Docker 卻說 `repository name (library/medagentbenchStarted) must be lowercase`。

**原因:** 從某對話/筆記複製指令時,**選取範圍多含到後面的說明文字**(例如「等到看到 Started Application 就 OK」),整段被當成同一行指令貼進 PowerShell,image 名稱被解析成 `medagentbenchStarted`。

**解法:**
1. PowerShell 有問題的那一行按 `Esc` 或 `Ctrl+C` 清空
2. **逐字手動輸入**指令,不要從說明文字裡複製
3. 或:把指令寫成 .ps1 腳本檔,直接執行腳本

預防:**對於只用一次的指令,寫成 .ps1 比一直複製貼上安全**:

```powershell
# C:\Users\User\start-fhir.ps1
docker run -p 8080:8080 medagentbench
```

執行:`.\start-fhir.ps1`

---

## 何時觸發此 skill

- 使用者問「Docker 怎麼裝」
- 使用者跑 `docker` 指令收到 `command not found` 或 `無法辨識 'docker' 詞彙`
- 使用者收到 `open //./pipe/docker_engine` 錯誤
- 使用者要在 Windows 上跑任何需要 Docker 的工具(MedAgentBench、其他 HAPI FHIR、Postgres container、自架 LLM 服務等)
- 安裝程式報空間不足
