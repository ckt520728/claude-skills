# Profile: cognitive-app

設計可攜式的軟體 App — 例如門診時間可用的認知測驗問卷，或認知測驗 task
(Stroop、N-back、Trail Making、digit span)。

The defining constraint: **this software produces research or clinical data.**
An app that looks perfect and silently drops 8% of reaction times is worse than
one that crashes, because the crash is visible and the data loss is not.

## Deliverables

| Name | Target | Split |
|---|---|---|
| `app` | `app/index.html` (or `app/main.py`) | held_in |
| `timing` | timing accuracy check | held_in |
| `data_integrity` | simulated-run data check | held_in |
| `export` | `app/export_schema.json` | held_in |
| `e2e` | automated play-through | held_out |

## Contracts

```bash
$K contract --name app --target app/index.html --split held_in \
  --checks "exists,min_bytes:2000,no_placeholder,regex_present:performance\\.now"
$K contract --name export --target app/export_schema.json --split held_in \
  --checks "exists,valid_json,json_keys:subject_id;trial_index;condition;stimulus;response;rt_ms;timestamp"
$K contract --name data_integrity --target results/sim_run.csv --split held_in \
  --checks "exists,cmd:python $V/check_no_null_rt.py --csv results/sim_run.csv --expected-trials 96"
$K contract --name timing --target results/sim_run.csv --split held_in \
  --checks "cmd:python $V/check_timing_distribution.py --csv results/sim_run.csv --condition-col condition"
$K contract --name e2e --target results/e2e_report.json --split held_out \
  --checks "exists,valid_json,cmd:npx playwright test tests/stroop.spec.js"
```

> `$V` = `<plugin>/scripts/verifiers/`. These scripts ship with the plugin and are tested (`python scripts/verifiers/test_verifiers.py`). Run any of them with `--help` for the full option list.

The `data_integrity` and `timing` checks are the ones that matter. Simulate a
full session — including fast responses, no-responses, and rapid double-clicks —
and assert that every trial produced a row and no reaction time is null, zero, or
negative. Run it every round.

## Known failure mechanisms

| Mechanism | Symptom | Component to fix |
|---|---|---|
| `async_write_race` | Rows lost or `null` under fast clicking | tool — buffer trials in memory, write once at completion, plus a periodic checkpoint against browser close |
| `date_now_instead_of_performance_now` | RT quantised to ~15 ms, unusable | tool — `performance.now()` only, contract it with `regex_present` |
| `first_trial_includes_render_latency` | Trial 1 RT is a 300 ms outlier | middleware — discard or flag the first trial, preload assets |
| `no_response_recorded_as_zero` | 0 ms RTs pollute the distribution | tool — explicit `null` plus a `timed_out` flag; never conflate |
| `keypress_debounce_swallows_response` | Occasional missing response | tool — record raw events, filter at analysis time |
| `subject_id_collision` | Two patients, one file | tool — id plus timestamp plus a collision check |
| `data_lost_on_browser_close` | Whole session gone | middleware — checkpoint to localStorage each trial, reconcile on load |

`async_write_race` was the failure the original prototype design was built
around, and it remains the right example: the fix is not "retry the write", it is
"stop writing per trial". That is a mechanism change, not a patch — exactly the
distinction [[harness-mine]] is for.

## Clinical-setting constraints

門診時間有限，這些不是加分項而是必要條件：

- Runs offline. Clinic wifi fails; a network dependency loses a session.
- Recovers from an interrupted session without losing completed trials.
- Practice trials are marked and separable from scored trials.
- Instruction text is fixed and identical for every participant — variation is a
  confound, not a UX improvement.
- Export is one file per session, self-describing, openable in Excel and R.

## Validity caution

A screen-based reimplementation of a validated instrument is **not** the
validated instrument. Timing, stimulus size, viewing distance, and input device
all shift norms. Published cut-offs from the paper-and-pencil version do not
transfer. Say this in the deliverable rather than leaving it implied — and treat
any clinical interpretation as requiring separate validation.
