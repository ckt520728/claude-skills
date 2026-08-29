# Taiwan Regulatory Map — SaMD

Swap this file when working in another jurisdiction. The article numbers are
Taiwan-specific; the five gates are not.

> **Verify before quoting.** Everything here was read from the primary source on
> 2026-08-29. Law changes. Re-check 全國法規資料庫 and the TFDA site before
> putting any number into a client-facing document, and tag anything you have
> not personally re-read as `[unverified]`.

## Sources (primary — always read these, not summaries of them)

| Document | URL |
|---|---|
| 醫療器材管理法 | https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=L0030106 |
| 醫療器材分類分級管理辦法 | https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=L0030120 |
| 醫用軟體分類分級參考指引 (PDF) | https://www.fda.gov.tw/tc/includes/GetFile.ashx?id=f637443989833238169 |
| 醫療器材查驗登記審查準則 | https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=L0030055 |
| 醫療器材行政規費收費標準 | https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=L0030123 |
| 醫療器材網路安全指引 (PDF) | https://www.fda.gov.tw/tc/includes/GetFile.ashx?id=f637099313592115714&type=1 |
| AI/ML 醫療器材軟體查驗登記技術指引 (PDF) | https://www.fda.gov.tw/tc/includes/GetFile.ashx?id=f637354438894278725 |
| 智慧醫療器材資訊暨媒合平台 | https://aimd.fda.gov.tw/ |
| 醫療器材分類分級查詢資料庫 (工研院) | https://mdlicense.itri.org.tw/ |

**Free help before paying a consultant:** TFDA 醫療器材諮詢專線 **02-8170-6008**,
and the AI medical-device mentoring programme on the 智慧醫療器材 platform.

## The decisive passage for cognitive software

《醫用軟體分類分級參考指引》(制定 104.4.13, 修正 109.12.24), section 5:

- Subsection (三) **健康促進軟體 General Wellness Software** lists uses that are
  **not** medical devices, explicitly including **心靈（心理）管理 mental
  acuity**, alongside weight management, physical fitness, recreation,
  relaxation/stress management, and sleep management.
- Later in the same section: software that "可用於解釋病患資料，或可分析由醫療器材
  產生的資料協助病患診斷或治療" is a **Class II** medical device.

**A brain-training app with own-score trends sits in the first bucket. Adding
norm comparison moves it to the second.** No web-search summary surfaced this
passage — it had to be extracted from the PDF (see pitfalls.md §1).

The guideline's own preamble says it cannot cover every product and that
**an individual classification ruling under 醫療器材管理辦法 §6 governs**.

## The five gates

### Gate 1 — Classification 分類分級

- 管理法 **§3** defines a medical device and **explicitly includes 軟體**.
- 分類分級管理辦法 **§4**: a device whose function/use/principle does not fall
  within the identification scope of any listed item is **classified Class III**.
  This is the downside risk — an unlisted novel product is *not* automatically
  low risk.
- Route: file the individual ruling (辦法 §6). Cheap, weeks, removes the biggest
  unknown in the programme.

### Gate 2 — Applicant eligibility 業者資格

- 管理法 **§13**: a medical device firm must register with the municipal/county
  authority and hold a **醫療器材商許可執照** before operating; manufacturers and
  distributors are regulated separately.
- Consequence: **a university lab cannot be the applicant.** A company must hold
  the licence.

### Gate 3 — QMS and manufacturing licence

- 管理法 **§22**: the manufacturer must establish a QMS and obtain a
  **製造許可** after inspection **before manufacturing**. Not merely before
  selling — before making the product at all.
- Standards in practice: 醫療器材品質管理系統準則 (ISO 13485-equivalent),
  IEC 62304, ISO 14971, IEC 62366, plus the TFDA software-validation and
  cybersecurity guidances.
- Fee: QMS inspection **NT$30,000**. Manufacturing-licence changes (added items,
  content, relocation) NT$60,000; other changes NT$10,000.

### Gate 4 — Clinical evidence

- 管理法 **§37**: a medical device clinical trial requires central-authority
  approval and informed consent.
- Per the TFDA smart-medical-device platform FAQ: a trial assessed as low risk
  may proceed without TFDA approval, **but ethics review (IRB) is required in
  every case**. Confirm which applies during the Phase 0 consultation, because
  it changes the study's lead time by months.

### Gate 5 — Registration 查驗登記

- 管理法 **§25**: manufacture or import requires 查驗登記 and a product licence;
  some items use a 登錄 (listing) route instead — typically Class I.
- Class II registration review fee: **NT$25,000**.
- `[unverified]` Official processing deadlines are published by TFDA; look up the
  current version rather than estimating.
- **Open question worth asking:** whether 查驗登記 can be *filed* before the
  manufacturing licence is granted. If the two can partly overlap, the programme
  shortens by 1–2 months. Ask this on the consultation call.

## Post-market obligations

| Item | Basis | Content |
|---|---|---|
| Serious adverse event reporting | §48 | Firms and medical institutions must report to the central authority |
| **Advertising pre-approval** | **§41** | Advertisements must be **approved before publication**; approved content may not then be altered |
| UDI | Announcement | Class II devices **manufactured on or after 2023-06-01** must bear a UDI |
| Software change control | QMS | Every release must be assessed for whether it constitutes a reportable change. App release cadence does not survive contact with this |

## Penalty that makes all of the above non-optional

管理法 **§62**: manufacturing or importing a medical device without approval —
up to **3 years imprisonment**, and/or a fine up to **NT$10,000,000**.
