# classroom-vote

即時課堂 A/B/C/D 投票，後端用 Firestore。`create_vote.mjs` 會寫入一筆 vote 文件。

## 設定（公開 repo 不內嵌金鑰）

1. 安裝相依套件：
   ```bash
   npm install firebase
   ```
2. 複製設定範本並填入你自己的 Firebase 專案設定：
   ```bash
   cp firebase.config.example.json firebase.config.json
   # 編輯 firebase.config.json，填入 apiKey / projectId 等
   ```
   `firebase.config.json` 已被 `.gitignore`，不會進版控。
   或改用環境變數：`FIREBASE_CONFIG='{"apiKey":"...","projectId":"..."}'`。

## 用法

```bash
node create_vote.mjs <code> <question> <optA> <optB> <optC> <optD>
```
成功印出 `OK <code>` 並 exit 0；失敗印錯誤訊息並 exit 1。

> 安全提醒：Firebase web apiKey 設計上可公開，真正防護來自 Firestore 安全規則。
> 請確認 `votes` collection 的規則符合你的需求（例如限制可寫入的欄位與頻率）。
