# AMP2026 認知測驗電池 (35 項作業) 假說基準值、統計檢定與實驗設計優化指引

**研究主持人**：朱國大醫師 (Kwo-Ta Chu, MD, PhD)  
**學術範疇**：認知神經科學、計算神經動力學、臨床認知評估  
**涵蓋任務**：全套 35 項認知測驗（記憶模組 M01–M09 共 9 項；注意力模組 A01–A26 共 26 項）

---

## 一、35 項認知作業核心假說、檢定指標與模擬結果表

下表由 10 位模擬受試者（SIM01–SIM10）的無頭模擬重新計算（2026-10-21 修正版；M01–M03 取自 memory-pilot-10，其餘取自 battery-pilot-10）。單樣本為雙尾 $t$（$df = N-1$）；M08 為組間 Welch $t$（control − misled）；A12 為比例與 Wilson 95% CI。Holm 只校正可估計的檢定（$m = 33$）；N < 2 或零變異標為「不可估計」。

> **解讀限制**：模擬效應量是反應器設定值，表中「模擬估計」只代表管線能還原設定的效應，不是實徵常模。「規劃參考值」取自登錄表 `benchmark`，尚未逐一對照原始文獻。

| 任務 ID | 名稱 | 主要 DV | 設計 | 單位 | N | 模擬估計 | 95% CI | t | Holm p | 效應量 | 規劃參考值 |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **M01** | 圖像記憶衰退與部分報告優勢 | `partial_superiority_free_isi0` | one_sample | items | 10 | 6.72 | [6.13, 7.32] | 25.7 | 2.98e-08 | 8.12 | +2.0 ~ +4.5 items |
| **M02** | 序列回憶感官模態與後綴抑制 | `suffix_effect_aud` | one_sample | proportion | 10 | 0.317 | [0.189, 0.445] | 5.59 | 0.00441 | 1.77 | +15% ~ +35% |
| **M03** | 連續干擾比率法則與近因效應 | `ratio_rule_slope` | one_sample | proportion/log-ratio | 10 | 0.103 | [0.0526, 0.154] | 4.61 | 0.0115 | 1.46 | > 0.0 |
| **M04** | 前攝干擾累積與類別轉換釋放 | `release_magnitude` | one_sample | proportion | 10 | 0.311 | [0.221, 0.401] | 7.8 | 0.000542 | 2.47 | +25% ~ +50% |
| **M05** | 記憶掃描線性搜尋與平行擴散 | `slope_all` | one_sample | ms/item | 10 | 37 | [32.9, 41.2] | 20 | 2.66e-07 | 6.32 | 30 ~ 50 ms/item |
| **M06** | 生成效應與遷移適當處理 | `gen_effect_word_std` | one_sample | d′ | 10 | 0.941 | [0.555, 1.33] | 5.51 | 0.0045 | 1.74 | 尚無本實作之實測參考範圍 |
| **M07** | 間隔複習效應與頻率判斷 | `recall_spacing_effect` | one_sample | proportion | 10 | 0.675 | [0.337, 1.01] | 4.52 | 0.0116 | 1.43 | +15% ~ +35% |
| **M08** | 目擊者誤導資訊與來源記憶監控 | `acc_standard` | between | proportion | 10 | 0.05 | [-0.522, 0.622] | 0.206 | 0.842 | 0.13 | +0.05 ~ +0.20（control − misled） |
| **M09** | 內隱與外顯記憶雙重分離 | `priming_score_implicit` | one_sample | proportion | 10 | 0.35 | [0.158, 0.542] | 4.12 | 0.0182 | 1.3 | +0.10 ~ +0.30 |
| **A01** | 內源設定與外源突現注意捕捉 | `capture_cost_rt` | one_sample | ms | 10 | 57 | [38.8, 75.2] | 7.09 | 0.00104 | 2.24 | +25 ~ +65 ms |
| **A02** | 3×3 視覺部分報告身分與位置衰退 | `partial_superiority_isi0` | one_sample | items | 10 | 6.08 | [4.89, 7.27] | 11.5 | 2.84e-05 | 3.64 | +1.5 ~ +3.5 items |
| **A03** | 知覺負荷與側抑制干擾 | `flanker_low` | one_sample | ms | 10 | 67.8 | [53.2, 82.5] | 10.5 | 6.1e-05 | 3.31 | +30 ~ +70 ms |
| **A04** | 特徵搜尋與連結搜尋斜率差異 | `slope_conjunction_present` | one_sample | ms/item | 10 | 8.35 | [4.61, 12.1] | 5.05 | 0.00758 | 1.6 | 20 ~ 45 ms/item |
| **A05** | 跨感官肢體姿勢空間重對應 | `postural_cost_rt` | one_sample | ms | 10 | 56.9 | [40.8, 73.1] | 7.98 | 0.000474 | 2.52 | +25 ~ +60 ms |
| **A06** | 心理不應期與注意瞬脫雙重瓶頸 | `ab_depth` | one_sample | proportion | 10 | 0.194 | [0.119, 0.268] | 5.89 | 0.00323 | 1.86 | +25% ~ +55% |
| **A07** | 一致映射搜尋自動化與傾斜平衡 | `search_slope_cm_vs_vm` | one_sample | ms/item | 10 | 26.6 | [16.6, 36.7] | 6.01 | 0.00299 | 1.9 | +15 ~ +35 ms/item |
| **A08** | 作業切換代價與殘餘切換定勢 | `switch_cost_value_100` | one_sample | ms | 10 | 86.1 | [60.8, 111] | 7.71 | 0.000562 | 2.44 | +60 ~ +150 ms |
| **A09** | 閃爍變化盲視與客觀遮蔽促發 | `masked_priming_facilitation_ms` | one_sample | ms | 10 | 47.6 | [20.9, 74.2] | 4.04 | 0.0182 | 1.28 | +15 ~ +45 ms |
| **A10** | 內隱空間注意火花辨識優勢 | `accuracy_cueing_effect` | one_sample | proportion | 10 | 0.167 | [0.0625, 0.271] | 3.62 | 0.025 | 1.14 | +15% ~ +40% |
| **A11** | 物件檔案移動框架特定預覽效益 | `object_specific_advantage_ms` | one_sample | ms | 10 | 76.8 | [51.8, 102] | 6.94 | 0.00108 | 2.2 | +20 ~ +50 ms |
| **A12** | 高負荷交叉作業下之無注意視盲 | `inattentional_blindness_rate` | proportion | proportion | 10 | 0.4 | [0.168, 0.687] | — | — | — | 0.40 ~ 0.75 |
| **A13** | 物件中心與場景中心負啟動 | `negative_priming_cost_ms` | one_sample | ms | 10 | 82.9 | [61.6, 104] | 8.81 | 0.000235 | 2.78 | +15 ~ +40 ms |
| **A14** | 字母算術實例提取與自動化轉折 | `instance_retrieval_transition_point` | one_sample | ms | 3 | 3（不可估計） | — | — | — | — | > 0 |
| **A15** | 外源變焦與返回抑制 (IOR) 起始 | `ior_onset_ctoa_ms` | one_sample | ms | 7 | 474 | [289, 659] | 6.26 | 0.0077 | 2.37 | 200 ~ 400 ms |
| **A16** | 突現新物件與單一特徵注意捕捉 | `capture_probability_index` | one_sample | index | 10 | 1.05 | [0.778, 1.32] | 8.8 | 0.000235 | 2.78 | > 0.2 |
| **A17** | 多物件動態追蹤容量限制 | `max_velocity_threshold_80pct` | one_sample | °/s | 10 | 7.83 | [7.42, 8.23] | 43.8 | 2.78e-10 | 13.9 | 6.0 ~ 10.0 °/s |
| **A18** | 跨感官視聽線索促進與 IOR | `crossmodal_facilitation_100_ms` | one_sample | ms | 10 | 10.6 | [-16.7, 37.9] | 0.88 | 0.804 | 0.278 | +15 ~ +40 ms |
| **A19** | 嬰兒注意解離代價與預期注視 | `proxy_disengagement_cost_ms` | one_sample | ms | 10 | 122 | [108, 137] | 18.9 | 4.25e-07 | 5.97 | +30 ~ +80 ms |
| **A20** | 嬰兒視聽一致性空間結合效應 | `crossmodal_binding_effect_ms` | one_sample | ms | 10 | 66.1 | [44.8, 87.4] | 7.03 | 0.00104 | 2.22 | +20 ~ +50 ms |
| **A21** | RSVP 注意瞬脫深度與 Lag-1 豁免 | `blink_depth` | one_sample | proportion | 10 | 0.561 | [0.492, 0.63] | 18.3 | 5.32e-07 | 5.79 | +30% ~ +60% |
| **A22** | 非反射性多位置返回抑制與容量 | `ior_ms_uninformative` | one_sample | ms | 10 | 59.9 | [23.2, 96.7] | 3.69 | 0.025 | 1.17 | +15 ~ +40 ms |
| **A23** | 視覺搜尋正確率與呈現時間 (Palmer) | `search_time_rt_slope` | one_sample | ms/item | 10 | 7.35 | [2.63, 12.1] | 3.52 | 0.025 | 1.11 | 10 ~ 30 ms/item |
| **A24** | 連結搜尋中干擾群組遞迴拒絕 | `recursive_rejection_efficiency_index` | one_sample | ms/item | 10 | 21.6 | [20.1, 23] | 32.8 | 3.55e-09 | 10.4 | +15 ~ +35 ms/item |
| **A25** | 注意力定向與空間解析變焦 | `resolving_cost_ms` | one_sample | ms | 10 | 54.5 | [49.9, 59.1] | 26.9 | 2.05e-08 | 8.5 | +30 ~ +70 ms |
| **A26** | ERP P1/N1 特徵結合抑制與錯覺結合 | `illusory_binding_cost` | one_sample | proportion | 10 | 0.45 | [0.337, 0.563] | 9 | 0.000205 | 2.85 | +0.15 ~ +0.35 |

---

## 二、記憶作業專題深入診斷 (M01–M04 及全記憶組)

朱國大醫師針對資料夾中 9 項記憶測驗（特別是早期之 M01–M03 及本批之 M04–M09）的理論機制、計算流形與實驗設計進行系統解構：

### 1. M01 (Sperling Iconic Memory 視覺圖像記憶衰退)
- **神經機制**：初級視覺皮質 (V1/V2) 瞬時高容量非語意表徵向頂下葉／顳葉工作記憶固化之衰退過程。
- **模擬設定（非實徵）**：模擬中 0 ms ISI 的 partial 優勢為 6.72 items（反應器設定，高於規劃參考值，需校正）。隨著 ISI 延遲至 300 ms、500 ms、1000 ms，partial 優勢完全消逝。
- **設計優化**：
  - *網頁端限制*：部分音效提示（Tone Cue: High/Mid/Low）在部分行動裝置 Safari 瀏覽器存在音訊上下文解鎖延遲（AudioContext Latency 20–50 ms）。
  - *修訂方案*：音訊提示應提前 50 ms 預先載入緩衝區，或改用**周邊箭頭視覺線索**輔助對照，消除音訊驅動器抖動對 ISI 標記之污染。

### 2. M02 (Modality & Suffix Effect 聽覺優勢與末端綴詞效應)
- **神經機制**：前聽覺儲存庫 (Pre-perceptual Acoustic Store, PAS) 具備較高之時間解析度與短暫抗衰退能力；然而非目標之語音綴詞會產生競爭性置換。
- **模擬設定（非實徵）**：無綴詞時聽覺呈現之第 8 位置回憶率顯著高於視覺呈現（聽覺優勢達 $+0.35$）；單一語音綴詞使聽覺尾端優勢顯著崩解。
- **設計優化**：
  - *設計缺陷*：讀唇條件 (Lip-read) 在無真人視訊下僅以 SVG 動畫代理，受試者知覺整合難度較高。
  - *修訂方案*：人體正式試驗中應採用標準化高畫質發音嘴形影片，並在刺激呈現前進行嘴形辨識校準（Lip-ID Calibration）。

### 3. M03 (Continuous Distractor & Ratio Rule 連續干擾與比率定律)
- **神經機制**：情境時間區辨性理論 (Temporal Distinctiveness Theory, SIMPLE 模型)。回憶機率取決於項目間間隔 (IPI) 與回憶延遲 (RI) 之對數比值 $\log(\text{IPI}/\text{RI})$。
- **模擬設定（非實徵）**：延遲自由回憶（Delayed Recall）在試次尾端遭受心算干擾時近因效應消失；而在連續干擾條件（每個單詞後均插入干擾心算）下，近因效應奇蹟般重現。
- **設計優化**：
  - *設計缺陷*：目前 Demo preset 僅包含 2 種 IPI/RI 組合，無法繪出完整的連續心理物理比率曲線。
  - *修訂方案*：在正式試驗中擴充至 4 組對數比值階梯（$\log(\text{IPI}/\text{RI}) \in \{0.5, 1.0, 1.5, 2.0\}$），以精確擬合神經動力學流形。

### 4. M04–M09 記憶模組綜合評析
- **M04 (PI Release)**：心算倒數任務必須具備嚴格的節奏限制，避免受試者偷背單字。
- **M05 (Sternberg Scanning)**：建議納入反應時間分佈（Ex-Gaussian 分解）以檢驗記憶搜尋之傾斜尾部。
- **M06 (Generation Effect)**：中文產生字詞需嚴格審核聯想常模強度，避免單詞過於直覺。
- **M07 (Spacing Effect)**：增加多清單交叉平衡，防止注意力疲勞干擾長間隔項目。
- **M08 (Misinformation Effect)**：閱讀敘述必須設定最低停留時間（Dwell Time），確保誤導資訊確實輸入。
- **M09 (Implicit Priming)**：殘詞補全應嚴格限制每題作答時限（< 3000 ms），預防受試者轉向外顯拼字策略。

---

## 三、注意力作業專題診斷 (A01–A26 關鍵亮點)

1. **A10 (Helmholtz Spark)**：16.67 ms 極短呈現極度依賴螢幕垂直同步 (VSync)。若螢幕為 60 Hz，恰為 1 個 VSync 幀；若為 120 Hz，則為 2 幀。必須在實驗啟動前進行硬體幀率檢測，剔除掉格試次。
2. **A12 (Inattentional Blindness)**：非預期目標穿過動態追蹤區域時，計數作業之難度直接決定視盲率。計數項目不可過少（最少 3 白 3 黑互相彈跳）。
3. **A17 (Multiple Object Tracking MOT)**：以心理物理學 PEST / 階梯法自適應逼近 80% 門檻速度，能大幅提升個體差異辨別度。
4. **A21 (Attentional Blink)**：Lag 1 豁免（Lag-1 Sparing）要求 T1 與 T2 呈現間隔無遮蔽刺激；Lag 2/3 進入注意瓶頸，T2 正確率驟降；至 Lag 7 逐漸恢復，展現經典 U 型曲線。
