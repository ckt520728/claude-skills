---
name: classroom-vote
description: Create a real-time classroom A/B/C/D voting session backed by a Firestore-backed Firebase project. Use whenever the user wants to start a new vote, poll, or quick in-class quiz — phrases like "開投票"、"出題"、"課堂投票"、"即時投票"、"幫我問學生..."、"poll the class"、"create a vote / poll / quiz", or any time the user describes a question they want to ask students and gather live responses for. Trigger this skill even if the user doesn't explicitly use the word "vote" — if the intent is to gather A/B/C/D-style answers from students in real time, that's this skill.
---

# Classroom Vote

Generate a live classroom voting session in three moves: write a vote document to Firestore, make sure the local web server is running, and hand back URLs the teacher and students open in their browsers.

This skill drives an existing web-app deployment (a static site under `<your-web-app>/public` plus a Firebase/Firestore project) programmatically — no UI clicks needed. Set up your Firebase config per `README.md` (`firebase.config.json` or `FIREBASE_CONFIG`), and set your own Firestore security rules for the `votes/` collection (see the security note in `README.md`).

## Steps

### 1. Parse the user's input

Extract two things:

- **question** (required): the question text. Example: `「哪個是腎絲球過濾率最敏感的指標？」`
- **options** (exactly 4 strings): if the user provides them (e.g., separated by `|`、`/`、`、`、 newlines, or as a list), use them. Otherwise default to `["A", "B", "C", "D"]`.

If the user provides 2 or 3 options, ask whether to pad with `C`/`D` placeholders or treat the remaining ones as "（不選）". If 5+, ask which to drop. The student UI is hardwired to 4 buttons, so this matters.

### 2. One-time dependency install

Check whether `node_modules` exists in the skill folder. If not:

```bash
cd ~/.claude/skills/classroom-vote && npm install --silent
```

This pulls the `firebase` package (~10 MB, ~15 s). Subsequent invocations skip it.

### 3. Generate a 6-character vote code

Use the alphabet `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` (no I/O/0/1 to avoid confusion when reading aloud). Code is 6 characters, uppercase. A short bash one-liner works:

```bash
tr -dc 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789' </dev/urandom | head -c 6
```

### 4. Ensure the local server is running on port 5050

Quick probe:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5050/index.html
```

If the response is not `200`, `301`, or `304`, start the server in the background:

```bash
cd "<your-web-app>/public" && nohup npx.cmd -y serve@latest -l 5050 . > /dev/null 2>&1 &
```

Wait ~3 seconds, then re-probe. If still not up, surface the error.

### 5. Write the vote document to Firestore

Run the bundled Node script (uses Firebase Web SDK; ensure your Firestore rules permit the intended writes — see README security note):

```bash
cd ~/.claude/skills/classroom-vote
node create_vote.mjs <CODE> "<QUESTION>" "<OPT_A>" "<OPT_B>" "<OPT_C>" "<OPT_D>"
```

Expected output: `OK <CODE>`. The script exits non-zero on failure with the error on stderr — surface it to the user verbatim if that happens.

### 6. Output to the user

Format clearly with a big code and click-ready URLs:

```
✅ 投票已建立！

📋 投票代碼：<CODE>

🧑‍🏫 老師端（即時長條圖）：
http://localhost:5050/teacher.html?code=<CODE>

🧑‍🎓 學生端（學生開這個）：
http://localhost:5050/student.html?code=<CODE>

→ 老師點老師端網址 → 直接看即時長條圖（不用再建立投票）。
→ 學生開學生端網址 → 代碼已預填，只要輸入班級代號 + 座號即可投。

⚠️ 學生用手機要連同一個 Wi-Fi 並把 localhost 換成電腦內網 IP（例如 192.168.x.x）；要讓校外學生也能連，告訴使用者「部署到 Firebase Hosting」即可。
```

## Why this design

- **Web SDK in Node, not Admin SDK**: avoids needing a service account credential file. With Firestore rules that permit the writes you intend for the `votes/` collection, an anonymous Web SDK client is enough. This keeps the skill self-contained — no service-account secret to manage. (Set rules deliberately; `allow write: if true` is convenient for a quick LAN demo but unsafe for public hosting — scope it down before deploying publicly.)
- **`?code=XXX` URL param**: Both teacher.html and student.html have been adapted to read this param. Teacher URL goes straight to the live tally; student URL pre-fills the code box so students only type their seat number. This is what makes the skill feel one-shot.
- **Local `npx serve` instead of Firebase Hosting**: zero deploy time. Tradeoff: only works on the LAN. If the user later wants public access, that's a separate task (`firebase init hosting` + `firebase deploy --only hosting`).

## When NOT to use this skill

- The user wants to *view* an existing vote — that's just opening `teacher.html?code=<existing>` directly, no new document needed.
- The user wants more than 4 options or non-button input (text answers, ranking, etc.) — the existing UI doesn't support it; tell the user this is out of scope.
- The user wants to delete or end a vote — that's done via the 結束投票 button on teacher.html, or ask the assistant to do it via Firebase MCP / a separate script.
