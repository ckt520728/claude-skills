# UNKNOWNS

## 2026-10-02 — v1.2 兩階段政策與證據

- **已實作並離線驗證：** high 規劃／medium-low 執行、八類工具能力 gate、task 依賴與精簡交接、named confidence 與預算上限、模型可用性與資料政策、實際檔案產出及獨立驗收。測試都是 stub，沒有呼叫付費模型。
- **本地政策：** `ROUTE_CONFIDENCE=0.85` 與 `Limits` 數值未經真實流量校準。使用者要求 high 不生成成品；這是新預設，不是 TypeSafe 的官方要求。
- **未量測：** 實際 token 節省、費用、延遲、完成率及語意品質。模型 registry 的舊價格／ID 未因本次升級而重新認證。沒有可用且已驗證的 medium/low 模型時應 ask。
- **宿主責任：** callback 與角色檔不等於安全 sandbox。宿主必須實際套用模型、effort、token cap、唯讀 planner、工具 middleware 與獨立驗收。原生 Claude agent 定義使用已記載的 opus/sonnet/haiku alias，但仍可能被宿主配置覆寫；未進行真實付費 agent 執行測試。
- **用量完整性：** 舊 ToolGate 不回傳 usage；工作流使用它後將 `usage_complete=false`。驗收器如使用模型，其用量由宿主補計，不能拿不完整帳目宣稱節省。
- **來源查核：** [TypeSafe 官方介紹](https://docs.typesafe.ai/introduction) 確认 Jev 回傳 typed decisions，而非文字生成。[Claude Code subagents](https://code.claude.com/docs/en/sub-agents) 與 [plugin manifest](https://code.claude.com/docs/en/plugins-reference) 支援本次角色格式。參考 GitHub 原始 SKILL blob SHA：`237f7fbeb54effa9ba0f8d86ed676b07a57dea18`。此紀錄僅覆蓋這次查核，不能更新下方所有歷史聲明。

---

What is verified, what is taken on someone's word, and what would change the design if it
turned out otherwise. Sorted by the four quadrants: the map is what the sources say, the
territory is the working API and a real workload.

Last pass: 2026-09-29, against `docs.typesafe.ai`. Extended the same day with the model
registry, self-switching, and the economics layer (v1.1).

---

## Quadrant 1 — Known knowns (verified against the live docs)

Checked directly on 2026-09-29. Where the corpus and the docs disagree, the docs won.

| Fact | Where it is used |
|---|---|
| `POST https://api.typesafe.ai/v1/systemone`, `Authorization: Bearer $TYPESAFE_API_KEY` | `assets/jev/providers/jev_api.py` |
| Request is `{model, state, questions}`; a question is `{type, instructions, criteria?}` | `assets/jev/types.py` |
| Response is `{model, answers, usage}`; answers keyed by **your** question id | `Result.from_wire` |
| An answer carries `type` plus `choice` / `score` / `noul`, with `probabilities` and `confidence` | `Answer.from_wire` |
| **A Noul has no `confidence` field.** The probability field is literally `noul` | `Answer.certainty` |
| Accessor is `response.answers[id].noul` — one accessor, not three | `references/00-primitives.md` |
| `Score` takes 2-10 ordered, described levels | `Score.__post_init__` validation |
| `confidence` is a statistic of the distribution, on `Choice` and `Score` only | `references/09-confidence-gate.md` |
| Documented bands are qualitative — high act / medium confirm / low do not act. The cut points are the caller's | `gate()` defaults are ours, not the vendor's |
| Models: `jev-1.13.0`; aliases `jev-latest` and `jev-preview` both point at it today | `DEFAULT_MODEL`, rule 7 |
| Context 64k total, 32k state, state + longest single question also 32k | `references/12-failure-modes.md` |
| Text only — string, JSON object, or array of text values. No image, audio or video | `08-realtime-control.md` state-rendering note |
| Rate limits ~250k tokens/sec and ~1,200 req/min, **documented as changeable without notice** | `bulk.py` `DEFAULT_RPM = 1000` |
| Errors: 401 bad key, 422 validation, 429 rate limited, 529 overloaded | `jev_api._explain` |
| `state` may be a plain string as well as an object | `decide()` signature |

### Errors found in the source articles

Recorded because the corpus is what a future session will reach for first.

1. **`result.choices[...]`, `result.scores[...]`, `result.nouls[...]` do not exist.** Two of the
   four articles use them. The documented shape is `answers[...]` for every primitive, and the
   same corpus uses `res.answers["risk"]` correctly elsewhere — so it is inconsistent *within
   itself*. Code copied from those snippets will `AttributeError` at runtime.
2. **`Score(labels=[...])`** appears once in a fan-out example. Everywhere else, and in the docs,
   the parameter is `criteria`. `labels` is treated as wrong here.
3. **The `$0.042` price could not be confirmed by direct fetch.** The docs models page rendered as
   "$42,000 per million input tokens", which is a rendering artifact of some kind. All five corpus
   sources independently say $0.042 per million input tokens with output free, so that is what is
   used — but every cost figure in `references/11-economics.md` inherits this one unconfirmed
   number. **Check the live pricing page before quoting a bill to anyone.**

---

## Quadrant 2 — Known unknowns (decided, with the decision recorded)

Resolved by asking rather than guessing. Each would have produced a different repo.

| Question | Decision | What the alternative would have changed |
|---|---|---|
| Package shape | Portable skill pack **plus** a plugin manifest | A plugin-only build would not drop into GPT-6 Astra or Cursor |
| Backend coupling | Pluggable `decide()`, Jev as default, `llm` and `local` adapters | Jev-only code would be shorter and would die with the vendor |
| Use-case granularity | One skill + 9 reference playbooks | A router plus 9 sub-skills would pay permanent context load for ten descriptions |

Still open, and genuinely the user's to decide:

- **Which fork to move first in a real loop.** The audit protocol ranks by frequency, but the
  repo has no real loop to rank. Nothing downstream is blocked by this.
- **Whether `jev-engineering` should be published to a marketplace** or stay local. Affects
  whether `.claude-plugin/marketplace.json` needs a real owner and repo URL.
- **Whether the three tiers are the right bands for this workload.** The tier assignment in
  `models.json` is the user's, taken as given. Whether Sonnet 5.5 and Gemini 3.6 Flash-high
  really belong in the same band is an empirical claim about *their* traffic, checkable with
  `references/10-threshold-tuning.md` and not checked here.

---

## Quadrant 3 — Unknown knowns (assumptions made explicit)

Things chosen here that look like facts but are not. Each is a defensible default, not a finding.

| Assumption | Why | Cost if wrong |
|---|---|---|
| Noul certainty as `abs(noul - 0.5) * 2` | A Noul has no confidence, but a shared gate needs one number | Reusing a Choice threshold on it silently mis-sets the gate. Documented in `Answer.certainty` and `09-confidence-gate.md` |
| `tau = 0.90` as the starting threshold everywhere | It is the value the paper's cascade was measured at | Copied without tuning it is a guess wearing a number's clothes. Every playbook says so |
| `tau = 0.95` for guardrails, higher than the rest | Style-adversarial confidence degrades (AUROC 0.77) | Too loose a bar on exactly the inputs designed to beat it |
| Uncertainty routes **up** in model routing, **to hold** in control loops, **to a human** in triage | The recoverable failure differs per fork | A single global default would be wrong in two of the three |
| `fee_ratio = 290` default in the sweep | $12.18 / $0.042 from the paper's panel | Only affects the fee column; accuracy columns are unaffected |
| 16 workers, 1,000 rpm in `bulk.py` | Under the documented 1,200 rpm ceiling | Too high once the ceiling moves; too low is merely slow |
| Python 3.9 as the floor | The interpreter on this machine | The vendor SDK wants 3.12+; our package deliberately does not depend on it |
| Hooks ship inert | Discovered live: enabling them with no key prompts on every Bash call | A "working" install that makes the agent unusable |
| `retry_recovery = 0.25` in `TierProfile` | Most failures are capability, not luck; a tier that cannot do a task does not start being able to on attempt three | Near 1.0 makes a weak tier look artificially cheap. This single number moves every policy comparison |
| A misroute lands **one tier below** where it belonged | The expensive direction, so `compare_policies` does not flatter the router | If misroutes actually go upward, routing looks worse here than it is |
| Four capability classes at threshold `1.01` in `ToolGate` | `network_egress`, `credential_access`, `spend`, `other` are policy, not classification | An organisation that auto-approves egress will find the gate obstructive and should change the table, not the code |
| Only `read` and `local_write` verdicts are cached | `normalise_call()` erases numeric literals and paths, so a verdict that depends on them must not be reused | Caching `destructive` would reuse a verdict across genuinely different commands |
| `tau_agreement = 0.75` for ensembles | For three variants this means unanimity; 2-of-3 would be nearly free to satisfy | Too low and the second uncertainty signal stops signalling |
| Control loops treat a missed tick budget as low confidence | p95 latency is unbounded, so the clock must decide rather than a judgement call | A loop with a genuinely slow-but-fine backend will hold more than it needs to |

---

## Quadrant 4 — Unknown unknowns (what has never been exercised)

The honest list. Everything here is a gap between this repo and a working deployment.

1. **The live API has never been called from this repo.** Every test used a stub provider. The
   request shape matches the documented one and the response parser matches the documented
   response — but a real call has not been made. **First real call is the first real test.**
2. **No threshold here has been tuned against real traffic.** Every number is the paper's, the
   vendor's, or a placeholder. `references/10-threshold-tuning.md` is the protocol; nobody has run
   it on a workload yet.
3. **Whether native `confidence` and `q = max(p)` diverge on a given workload.** They correlate at
   Spearman 0.95-0.999 on the paper's benchmarks. `Answer.certainty` prefers native, `Answer.q`
   exposes the max-probability version, so both are available — but which one to gate on is an
   empirical question per workload.
4. **Whether a batch endpoint exists.** `bulk.py` sends one request per row with a thread pool. If
   the API gained a batch endpoint, `label_rows` would be rewritten around it and the rate-limit
   logic would change shape.
5. **Async.** Everything here is synchronous. A high-throughput deployment would want the async
   SDK, and the provider contract would need an async sibling.
6. **Whether `state` as an array of text values behaves differently from an object.** Both are
   documented as accepted. All examples here use objects.
7. **The LangChain integration names** — `langchain_typesafe.experimental.middleware`,
   `AutoModeMiddleware`, `ModelRouterMiddleware`, `ModelChoice`. Taken from one article, never
   imported. `experimental` in the path suggests they will move.
8. **The install commands** `claude plugin marketplace add typesafe-ai/skills` and
   `npx skills add typesafe-ai/skills --skill typesafe-ai` — from an article, not run.
9. **`Choice` supports up to 255 options** — asserted by the articles, not stated on the docs page
   fetched. `types.py` enforces 255 as a guard; if the real limit is lower, a large `Choice` fails
   at the API rather than at construction.
10. **Everything about the vendor's provenance and funding** (RLCD training, InstructGPT lineage,
    $40M seed) is press material. None of it is load-bearing for any code here, and none of it was
    checked.

### Added by the v1.1 routing and economics layer

11. **Seven of nine models in `models.json` have no price and six have no `api_id`.** The tier
    assignment is the user's and is taken as given; the identifiers and prices are not. Until
    they are filled, `select()` falls back to platform preference order and every cost figure
    from `economics` is arithmetic on synthetic inputs. `Registry.audit()` is the checklist.
12. **The 5.5-generation Claude ids are blank because they postdate what could be confirmed at
    build time.** `claude-opus-5`, `claude-sonnet-5` and `claude-haiku-4-5-20251001` were the
    newest confirmable ids; `claude-haiku-4.5` is therefore the only Anthropic row marked
    verified. Do not assume "Opus 5.5" maps to `claude-opus-5-5`.
13. **"Sol-high", "Terra-high", "Luna-high" and the Gemini efforts are the user's naming, not a
    verified provider taxonomy.** The paper's own panel names `gpt-5.6-sol`, `gpt-6-astra`,
    `claude-sonnet-5` and `gemini-3.1-pro-preview` — a different generation. Whether an
    effort suffix is a separate model id, a request parameter, or both is unresolved, and it
    changes how `Model.effort` must be sent.
14. **Sol-high's price is the paper's figure for `gpt-5.6-sol` at LOW effort.** High effort will
    cost more, so the one cost comparison the registry can currently make understates the
    cheapest high-tier option. Noted in its `price_source`.
15. **No success rate in this repo was measured.** `TierProfile.success_rate` is the input that
    decides every policy comparison, and every value used in the examples is illustrative. A
    routing decision made on these numbers is a decision made on a guess.
16. **The switch economics assume a cold cache on the return leg.** `cache_read_multiplier` is
    in the registry and `Model.cost_usd()` accepts `cached_mtok`, but `switch_cost()` does not
    apply it — so the rebuild penalty is an upper bound. With a warm prefix cache the real
    penalty is smaller and the break-even context larger.
17. **Whether a provider's reported `input_tokens` is the right measure of `context_mtok`.**
    It is what the code uses, and it is at least *a* real number rather than an estimate, but
    cache hits and provider-side prompt rewriting both make it an imperfect proxy for what the
    next model would have to load.
18. **`ToolGate.check_batch` shims `matches_stated_intent` to 1.0.** Asking the off-pattern
    question per call would triple the question count in a batch, so batched gating loses that
    signal. A batch is therefore slightly weaker than N individual checks — deliberate, and
    worth knowing before putting a batch on the security path.
19. **The cascade fee model is the simple one** (cheap-on-all plus fallback-on-escalated) and
    gives 34.3% of the fee where the paper reports 47% at the same escalation rate. The gap is
    the paper's both-orders judging and its conservative usage reservation. Use it for a
    break-even, not to reproduce a published figure.
20. **The LangChain middleware names still have not been imported**, and the routing playbook
    now leans on them more than before (`ModelRouterMiddleware`, `ModelChoice`). Still one
    scratch venv away from being settled.

---

## How to close one

Cheapest first, and each one is permanent once closed:

1. **Fill `models.json`** — nine `api_id`s and nine price pairs from the providers' live pages,
   with retrieval dates in `price_source`. Half an hour, closes #11-#14, and turns the whole
   economics layer from arithmetic-on-blanks into a measurement. `Registry.audit()` tells you
   when you are done.
2. Set `TYPESAFE_API_KEY` and run `examples/router.py`. Closes #1 and confirms the price page.
3. Label 150 items from a real workload, run `examples/tune_threshold.py`, record the result
   beside the threshold constant. Closes #2 and #3.
4. Label 100 real requests with the tier that *actually* completed them and derive
   `success_rate` per tier. Closes #15 — and until it is closed, `compare_policies()` output
   is not evidence for or against building a router.
5. Import the LangChain middleware in a scratch venv. Closes #7 and #20 in about a minute.

Re-read this file before changing a threshold, a criteria string, or a cited number — those are
the three places where an assumption here becomes a claim somewhere else.
