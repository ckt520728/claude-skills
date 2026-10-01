"""[D] the GTD clarify/organize decisions, built on the jev-engineering skill.

It decides **labels**: is this actionable, which bucket, which life area, how urgent, how
much energy, which vault folder. It writes nothing and generates no prose — the coaching,
the reflection, the weekly synthesis stay [G] on the frontier model. Subtraction.

Order of operations (invariant 5):

    1. hard rules in code      <- FIRST; a captured note is arbitrary text
    2. one jev.decide() call   <- every question shares the state (skill rule 5)
    3. jev.gate()              <- per-label thresholds; policy flags beat confidence

## How the questions honour the skill's seven rules

1. *Meaning lives in the instructions.* Every option carries criteria text, bilingual,
   listing the verbs and nouns that describe it. The `local` provider scores the state
   against exactly this text — so these criteria ARE the vocabulary. Edit them against
   real captures (UNKNOWNS U3b); do not add a separate lexicon.
2. *One judgment per question.* Bucket, area, urgency and energy are separate questions.
3. *Situations, not moods.* Urgency levels describe deadlines, never "very urgent".
4. *Every Choice has an exit.* `other`, never auto-filed.
5. *Ask everything in one call.* `assess()` sends all of them at once.
6. *Math and dates in code.* Unlock days, consistency and the 知識庫 overlap are [C].
7. *Shadow first.* The calibrator starts cold; every resolved ask is a label.
"""

import io
import os
import re
from collections import OrderedDict

from . import jev
from .jev import Choice, Exit, Noul, Score
from .jev.providers.local import tokenize
from .layer import DEFAULT_CALIBRATION, Layer

__all__ = [
    "ASK", "AUTO", "BLOCK",
    "BUCKETS", "FOLDERS", "BUCKET_TAU", "FOLDER_TAU",
    "AUTO_FILE_CONFIDENCE", "ESCALATE_FLOOR", "ACTIONABLE_YES", "ACTIONABLE_NO",
    "Decision", "questions", "assess", "clarify", "organize", "layer_for_env",
    "hard_rules", "record_outcome", "kb_candidates", "duplicate_check", "summarize",
    "CLARIFY", "ORGANIZE",
]

# --- verdicts (Life OS vocabulary over the skill's four exits) -----------------
ASK = "ask"      # a human sees a proposal; nothing happens without a click
AUTO = "auto"    # file it without asking (jev Exit.ACT)
BLOCK = "block"  # reserved: do not file, do not propose

# --- thresholds (invariant 6: named, in code, never in a prompt) --------------
# None tuned against real traffic (UNKNOWNS U3). The calibrator makes that safe: a cold
# band reports 0.30, below every number here.
AUTO_FILE_CONFIDENCE = 0.75   # default tau_act
ESCALATE_FLOOR = 0.50         # tau_ask: below this the proposal is shown as a guess
ACTIONABLE_YES = 0.80
ACTIONABLE_NO = 0.20
NEVER = 1.01                  # unreachable on purpose: always a human

# Per-label tau_act, because blast radius differs within one question (skill:
# thresholds_for_actions). Filing a project wrongly costs more than filing a reference.
BUCKET_TAU = OrderedDict([
    ("two_minute", AUTO_FILE_CONFIDENCE),
    ("next_action", AUTO_FILE_CONFIDENCE),
    ("project", 0.85),
    ("reference", AUTO_FILE_CONFIDENCE),
    ("someday", AUTO_FILE_CONFIDENCE),
    ("other", NEVER),
])

# Clippings belongs to the Web Clipper and is immutable (vault CLAUDE.md). 知識庫 carries an
# index.md/log.md duty nothing automates yet — so it is never auto-filed until it is.
FOLDER_TAU = OrderedDict([
    ("Clippings", NEVER),
    ("知識庫", NEVER),
    ("創作庫", 0.85),
    ("GTD", AUTO_FILE_CONFIDENCE),
    ("other", NEVER),
])

BUCKETS = tuple(BUCKET_TAU)
FOLDERS = tuple(FOLDER_TAU)

# Two captures sharing this many content tokens with a 知識庫 index line is a candidate
# duplicate. [C], not [D]: the local layer has no way to read the vault.
KB_OVERLAP_MIN = 3

# --- the questions ------------------------------------------------------------
ACTIONABLE = Noul(
    instructions="這則收件需要使用者親自去做某件事。 The captured item requires the user to act.",
    criteria={
        "yes": "需要去做：打電話、寄信、回覆、預約、掛號、買、訂、填、送出、繳交、處理、安排、"
               "準備、完成、修、改、寫、讀完、提醒、記得。 call email reply book buy order "
               "submit fix schedule prepare finish remind todo need must",
        "no": "不需要行動，只是資訊或靈感：文章、文獻、論文摘要、連結、網址、引用、摘錄、想法、"
              "發現、原來、知識、數據。 article paper abstract link url http quote idea "
              "insight fact note fyi",
    },
)

BUCKET = Choice(
    instructions="GTD 釐清：這則收件屬於哪一類？ GTD clarify: which kind of item is this?",
    criteria=OrderedDict([
        ("two_minute", "兩分鐘內可完成的小事：回覆、回信、回電、轉寄、確認、簽名、傳訊息、"
                       "按讚、存檔。 two-minute job: reply forward confirm sign text rsvp"),
        ("next_action", "一個具體可執行的下一步：打電話、寄信、預約、掛號、訂位、買、填表、"
                        "送出、列印、繳交、讀完。 one concrete next action: call email book "
                        "order buy fill submit print read"),
        ("project", "需要多個步驟才能完成的結果：計畫、專案、系統、建置、重構、研究、課程、"
                    "論文、投稿、規劃、準備、然後、接著。 needs several actions: project plan "
                    "build launch research paper course then"),
        ("reference", "不需要行動、值得保存的資料：文章、文獻、連結、網址、筆記、摘錄、引用、"
                      "數據、發現、原來。 no action, worth keeping: article paper link url "
                      "http quote note fact insight"),
        ("someday", "現在不做、將來也許：有空、以後、某天、想學、想去、想試、夢想、或許、"
                    "考慮、有機會。 not now: someday maybe one day wishlist would like"),
        ("other", "以上皆不適用：看不懂、不完整的片段。 none of these fits: unclear fragment"),
    ]),
)

URGENCY = Score(
    instructions="這件事的期限有多近？ How close is the deadline?",
    criteria=[
        "沒有期限，隨時都可以做。 no deadline whenever",
        "幾週內或這個月、下個月。 within weeks this month next month",
        "這週內、週末前、週五前。 this week before weekend by friday",
        "明天、後天、明早之前。 tomorrow by tomorrow morning",
        "今天、馬上、立刻、緊急、已經逾期。 today now urgent asap overdue",
    ],
)

ENERGY = Score(
    instructions="做這件事需要多少專注力？ How much focus does doing this take?",
    criteria=[
        "低能量、不用動腦：整理、歸檔、回覆、雜事、跑腿、繳費。 low energy: tidy file errand admin",
        "中等專注：閱讀、會議、討論、打電話、規劃、檢查。 medium focus: read meeting discuss plan review",
        "高能量深度工作：寫作、研究、分析、設計、論文、程式、投稿。 deep work: write research "
        "analyse design code manuscript",
    ],
)

FOLDER = Choice(
    instructions="這則內容應該存到 vault 的哪個資料夾？ Which vault folder does this go to?",
    criteria=OrderedDict([
        ("Clippings", "別人的原始資料，原封不動保存：剪藏的網頁、期刊文章、新聞、報導、"
                      "網址。 someone else's material kept verbatim: clipped page journal "
                      "article news http https www doi pdf url"),
        ("知識庫", "消化整理後的結構化知識：重點整理、摘要、概念、機制、比較、懶人包、指引。 "
                   "digested structured knowledge: summary concept mechanism guideline review"),
        ("創作庫", "使用者自己的產出：我的想法、草稿、文章、病例分析、研究報告、投影片、演講。 "
                   "the user's own output: my draft essay slides talk manuscript"),
        ("GTD", "要做的事，放進任務清單：待辦、下一步、提醒、預約、打電話、買、寄。 an action "
                "for the task list: todo next action reminder call buy email"),
        ("other", "以上皆不適用。 none of these fits"),
    ]),
)

CLARIFY = ("actionable", "bucket", "area", "urgency", "energy")
ORGANIZE = ("folder",)

# --- hard rules, step 1 --------------------------------------------------------
# Deliberately broad: a false positive costs one confirmation click, a false negative
# files something sensitive unattended.
_SENSITIVE = (
    ("clinical", re.compile(
        r"病人|患者|個案|病歷|主訴|診斷|處方|用藥|檢驗|住院|門診|手術|"
        r"patient|diagnos|prescri|medical record", re.I)),
    ("money", re.compile(
        r"匯款|轉帳|付款|報稅|發票|薪資|貸款|帳號|信用卡|"
        r"invoice|payment|salary|tax|bank account|credit card", re.I)),
    ("people", re.compile(
        r"生日|禮物|吵架|道歉|離婚|分手|喪|葬|懷孕|"
        r"birthday|apolog|divorce|funeral|pregnan", re.I)),
)


def hard_rules(text, config=None):
    """(tag, reason) for every guard the text trips. Non-empty forces ASK (invariant 4)."""
    return [(tag, "matched the %s guard in code" % tag)
            for tag, pattern in _SENSITIVE if pattern.search(text or "")]


class Decision(object):
    """What the layer believed, what the code decided, and why. `reasons` is the audit trail."""

    __slots__ = ("verdict", "label", "confidence", "reasons", "probabilities", "question",
                 "raw_confidence", "warm", "exit")

    def __init__(self, verdict, label, confidence, question, reasons=None, probabilities=None,
                 raw_confidence=None, warm=None, exit=None):
        self.verdict = verdict
        self.label = label
        self.confidence = confidence
        self.question = question
        self.reasons = list(reasons or [])
        self.probabilities = probabilities or {}
        self.raw_confidence = raw_confidence
        self.warm = warm
        self.exit = exit

    @property
    def is_auto(self):
        return self.verdict == AUTO

    def explain(self):
        return "%s -> %s (%s, conf=%.2f): %s" % (
            self.question, self.label, self.verdict,
            (self.confidence if self.confidence is not None else -1.0),
            "; ".join(self.reasons) or "no notes")

    def __repr__(self):
        return "Decision(%s, %r)" % (self.verdict, self.label)


def layer_for_env(env=None):
    """The decision layer: the skill's `local` provider, calibrated in the vault.

    `LIFEOS_PROVIDER` may name another registered jev provider (e.g. `jev` once a
    TYPESAFE_API_KEY exists) — as something to measure against, not an automatic upgrade.
    """
    env = env if env is not None else os.environ
    return Layer(provider=env.get("LIFEOS_PROVIDER") or "local",
                 path=env.get("LIFEOS_CALIBRATION") or DEFAULT_CALIBRATION)


def area_question(config):
    """Built from the SSOT: one option per wheel area, criteria from its description."""
    areas = getattr(config, "wheel_areas", None) or []
    if not areas:
        return None
    crit = OrderedDict()
    for a in areas:
        text = a.get("criteria") or a.get("name") or a["id"]
        crit[a["id"]] = "%s：%s" % (a.get("name") or a["id"], text) if a.get("criteria") else text
    crit["other"] = "不屬於以上任何領域。 none of these areas"
    return Choice(instructions="這件事屬於人生輪的哪個領域？ Which life area does this belong to?",
                  criteria=crit)


def questions(config, which=None):
    """The question map for one decide() call."""
    table = OrderedDict([
        ("actionable", ACTIONABLE), ("bucket", BUCKET), ("area", area_question(config)),
        ("urgency", URGENCY), ("energy", ENERGY), ("folder", FOLDER),
    ])
    keep = which or tuple(table)
    return OrderedDict((k, v) for k, v in table.items() if k in keep and v is not None)


def _gate(answer_label, conf, qid, guards, tau_table=None, raw=None, warm=None,
          probabilities=None, extra=None):
    """Belief -> verdict via the skill's gate(). The only place that mapping happens."""
    reasons = list(extra or [])
    if warm is False:
        reasons.append("calibration still cold for this band — confidence floored")
    tau = (tau_table or {}).get(answer_label, AUTO_FILE_CONFIDENCE)
    probe = jev.Answer(id=qid, type="choice", choice=answer_label,
                       confidence=conf if conf is not None else 0.0)
    if conf is None:
        reasons.append("no confidence reported; failing to ask (invariant 3)")
        return Decision(ASK, answer_label, None, qid, reasons, probabilities, raw, warm,
                        Exit.ABSTAIN)
    d = jev.gate(probe, tau_act=tau, tau_ask=ESCALATE_FLOOR,
                 policy_flags=[bool(guards)],
                 policy_reason="policy outranks classification (invariant 4)")
    if guards:
        reasons.extend(r for _t, r in guards)
    if answer_label == "other" and d.exit is Exit.HUMAN and not guards:
        reasons.append("`other` is never auto-filed (invariant 4)")
    elif tau >= NEVER and not guards:
        reasons.append("%s is never auto-filed — policy table" % answer_label)
    reasons.append(d.reason)
    verdict = AUTO if d.exit is Exit.ACT else ASK
    return Decision(verdict, answer_label, conf, qid, reasons, probabilities, raw, warm, d.exit)


def assess(text, config, layer=None, which=None):
    """Clarify + organize in ONE decide() call. Returns {question: Decision}."""
    layer = layer or layer_for_env()
    guards = hard_rules(text, config)
    qs = questions(config, which)
    state = text or ""
    try:
        result = layer.decide(state, qs)
    except Exception as exc:  # network blip, bad provider: fail to ask (invariant 3)
        return dict((q, Decision(ASK, None, None, q, ["decision layer error: %s" % exc],
                                 exit=Exit.ABSTAIN)) for q in qs)

    out = {}
    for qid in qs:
        ans = result.answers[qid]
        conf, raw, warm = layer.confidence_of(result, qid)
        if ans.type == "noul":
            p = ans.noul
            if p is None:
                out[qid] = Decision(ASK, None, None, qid, ["no value returned"], exit=Exit.ABSTAIN)
            elif p >= ACTIONABLE_YES or p <= ACTIONABLE_NO:
                label = "yes" if p >= ACTIONABLE_YES else "no"
                out[qid] = _gate(label, conf, qid, guards, raw=raw, warm=warm,
                                 extra=["noul %.2f (decisiveness %.2f)" % (p, raw or 0.0)])
            else:
                out[qid] = Decision(
                    ASK, "unclear", conf, qid,
                    ["noul %.2f between %.2f and %.2f — the state does not separate the cases"
                     % (p, ACTIONABLE_NO, ACTIONABLE_YES)], raw_confidence=raw, warm=warm,
                    exit=Exit.ESCALATE)
        elif ans.type == "score" and raw == 0.0:
            # A flat distribution means no level's criteria matched. Its expected value is
            # the midpoint, which would read as a real proposal. Say so instead.
            out[qid] = Decision(ASK, None, conf, qid,
                                ["no level's criteria matched the capture — no proposal"],
                                raw_confidence=raw, warm=warm, exit=Exit.ABSTAIN)
        elif ans.type == "score":
            label = "%d" % int(round(ans.score or 0.0))
            out[qid] = _gate(label, conf, qid, guards, raw=raw, warm=warm,
                             probabilities=ans.probabilities,
                             extra=["score %.2f of %d" % (ans.score or 0.0,
                                                          len(qs[qid].criteria) - 1)])
        else:
            table = {"bucket": BUCKET_TAU, "folder": FOLDER_TAU}.get(qid)
            out[qid] = _gate(ans.choice, conf, qid, guards, tau_table=table, raw=raw,
                             warm=warm, probabilities=ans.probabilities)
    if "folder" in out and out["folder"].label == "知識庫":
        out["folder"].reasons.append(
            "知識庫 additions must also update index.md and log.md (vault CLAUDE.md)")
    return out


def clarify(text, config, layer=None):
    """GTD clarify: actionable? which bucket, which area, how urgent, how much energy."""
    return assess(text, config, layer, CLARIFY)


def kb_candidates(text, index_text):
    """[C] 知識庫 index lines sharing >= KB_OVERLAP_MIN content tokens with the capture."""
    # Multi-character tokens only: a single Han character is shared by almost anything.
    content = lambda t: set(x for x in tokenize(t) if len(x) >= 2)
    mine = content(text)
    hits = []
    for line in (index_text or "").splitlines():
        if "[[" not in line:
            continue
        shared = len(mine & content(line))
        if shared >= KB_OVERLAP_MIN:
            hits.append((shared, line.strip()))
    hits.sort(key=lambda h: -h[0])
    return [line for _n, line in hits[:3]]


DEFAULT_KB_INDEX = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    DEFAULT_CALIBRATION))), "知識庫", "index.md")


def duplicate_check(text, kb_index_path=None):
    """[C] Is this already covered in 知識庫? Candidates always go to a human."""
    path = DEFAULT_KB_INDEX if kb_index_path is None else kb_index_path
    if not (path and os.path.exists(path)):
        return Decision(ASK, "unknown", None, "duplicate",
                        ["知識庫/index.md not readable — cannot check"])
    with io.open(path, "r", encoding="utf-8") as fh:
        cands = kb_candidates(text, fh.read())
    if cands:
        return Decision(ASK, "likely", None, "duplicate",
                        ["shares terms with: " + " | ".join(cands)])
    return Decision(AUTO, "unlikely", None, "duplicate",
                    ["no 知識庫 index line shares %d+ terms" % KB_OVERLAP_MIN])


def organize(text, config, layer=None, kb_index_path=None):
    """GTD organize: which folder, and is it already covered in 知識庫?"""
    out = assess(text, config, layer, ORGANIZE)
    out["duplicate"] = duplicate_check(text, kb_index_path)
    return out


def record_outcome(layer, decisions, question, chosen_label, save=True):
    """Teach the layer from one adjudicated decision. Returns a report string or None."""
    d = decisions.get(question)
    if d is None or layer is None:
        return None
    return layer.record(question, d.raw_confidence, d.label == chosen_label, save=save)


def summarize(decisions):
    """One line per decision, auto first."""
    rows = sorted(decisions.values(), key=lambda d: (d.verdict != AUTO, d.question))
    return [d.explain() for d in rows]
