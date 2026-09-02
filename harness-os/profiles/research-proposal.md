# Profile: research-proposal

國科會 (NSTC) 計畫、學術研究計畫申請書，以及其他有固定章節與預算表的結構化提案。

## Deliverables

| Name | Target | Split |
|---|---|---|
| `proposal` | `draft/proposal.md` | held_in |
| `budget` | `draft/budget.json` | held_in |
| `consistency` | cross-check script | held_in |
| `refs` | `draft/proposal.md` | held_out |

## Contracts

```bash
$K contract --name proposal --target draft/proposal.md --split held_in \
  --checks "exists,min_words:4000,no_placeholder,sections:研究背景與目的|文獻回顧|研究方法|預期成果|經費預算|研究進度"
$K contract --name budget --target draft/budget.json --split held_in \
  --checks "exists,valid_json,json_keys:equipment;personnel;consumables;total"
$K contract --name consistency --target draft/proposal.md --split held_in \
  --checks "cmd:python $V/check_budget_alignment.py --doc draft/proposal.md --budget draft/budget.json --methods 研究方法"
$K contract --name refs --target draft/proposal.md --split held_out \
  --checks "regex_present:\\[[0-9]{1,3}\\],regex_absent:\\[citation needed\\]"
$K contract --name refs_resolve --target draft/proposal.md --split held_out \
  --checks "cmd:python $V/check_citations_resolve.py --doc draft/proposal.md --bib draft/refs.bib"
```

> `$V` = `<plugin>/scripts/verifiers/`. These scripts ship with the plugin and are tested (`python scripts/verifiers/test_verifiers.py`). Run any of them with `--help` for the full option list.

`check_budget_alignment.py` is the highest-value item in this profile:
every instrument named in 研究方法 must appear as a budget line item, and the
totals must add up. This is the most common reviewer-visible defect in a
proposal, and it is fully mechanical — so mechanise it.

## Decomposition

One job per section, plus `refs_align` and `budget_reconcile` as their own jobs.

Sections drafted in parallel drift in terminology. Keep a glossary file and make
terminology consistency a `cmd:` check against it — do not rely on remembering.

## Known failure mechanisms

| Mechanism | Symptom | Component to fix |
|---|---|---|
| `budget_not_reconciled_with_methods` | 方法提到的儀器沒出現在預算表 | tool — the alignment script |
| `section_terminology_drift` | 同一概念在第二節與第四節用不同術語 | memory (glossary) + `cmd:` check |
| `citation_placeholder_survives` | `[citation needed]` ships | middleware — `regex_absent` on every assert |
| `word_budget_blown_late` | 各章節各自寫滿，總長超限 | middleware — per-section budget set at fork time |
| `deadline_state_lost` | 跨 session 之後忘記寫到哪 | playbook + `$K status` on resume |
| `citation_fabricated` | 引用看起來合理但不存在 | tool — resolve every citation against a real source before assert |

`citation_fabricated` deserves emphasis: a structural check confirms a citation
marker exists, not that the paper does. Verify citations against an actual
database. Do not let a `regex_present` check stand in for that.

## Boundary condition

Structure, consistency, budget arithmetic and citation hygiene are checkable, and
this loop handles them well.

**Novelty, significance, and whether reviewers will be persuaded are not.** Use
[[verify-with-rubric]] with a separate context-isolated sub-agent for those,
present the result as advice to a human, and never let an automated loop optimise
against it.
