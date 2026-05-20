// Writes a new vote document to Firestore for the classroom-vote skill.
// Usage: node create_vote.mjs <code> <question> <optA> <optB> <optC> <optD>
// Exits 0 on success with "OK <code>" on stdout, 1 on failure with error on stderr.
//
// Firebase 設定載入順序（公開 repo 版本不內嵌金鑰）：
//   1. 同資料夾的 firebase.config.json（已 gitignore，放你的真實設定）
//   2. FIREBASE_CONFIG 環境變數（JSON 字串）
//   3. 下方 placeholder（未替換前不會運作）
// 範本見 firebase.config.example.json。

import { initializeApp } from 'firebase/app';
import { getFirestore, doc, setDoc, serverTimestamp } from 'firebase/firestore';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));

function loadConfig() {
  // 1) 本地設定檔（gitignored）
  try {
    return JSON.parse(readFileSync(join(__dirname, 'firebase.config.json'), 'utf8'));
  } catch {}
  // 2) 環境變數
  if (process.env.FIREBASE_CONFIG) {
    try { return JSON.parse(process.env.FIREBASE_CONFIG); } catch {}
  }
  // 3) placeholder（請替換，或改用上面任一方式）
  return {
    apiKey: "YOUR_FIREBASE_API_KEY",
    authDomain: "YOUR_PROJECT.firebaseapp.com",
    projectId: "YOUR_PROJECT_ID",
    storageBucket: "YOUR_PROJECT.firebasestorage.app",
    messagingSenderId: "YOUR_SENDER_ID",
    appId: "YOUR_APP_ID",
    measurementId: "YOUR_MEASUREMENT_ID"
  };
}

const firebaseConfig = loadConfig();
if (firebaseConfig.apiKey === "YOUR_FIREBASE_API_KEY") {
  console.error('FAIL: 尚未設定 Firebase。請在本資料夾放 firebase.config.json（見 firebase.config.example.json），或設定 FIREBASE_CONFIG 環境變數。');
  process.exit(1);
}

const args = process.argv.slice(2);
if (args.length < 6) {
  console.error('Usage: node create_vote.mjs <code> <question> <optA> <optB> <optC> <optD>');
  process.exit(1);
}
const [code, question, optA, optB, optC, optD] = args;
const options = [optA, optB, optC, optD];

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

try {
  await setDoc(doc(db, 'votes', code), {
    question,
    options,
    active: true,
    createdAt: serverTimestamp(),
    responses: {}
  });
  console.log('OK ' + code);
  process.exit(0);
} catch (err) {
  console.error('FAIL ' + (err && err.message ? err.message : String(err)));
  process.exit(1);
}
