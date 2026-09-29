# 08 — Real-time control: games, bots, robots, trading loops

The forks above trade tokens for money. This one trades them for **time**: a loop that must close in tens of milliseconds cannot contain a frontier model call, so the decision layer is not an optimisation here, it is what makes the loop possible at all.

Reported reference points: a per-block trading decision at ~81 ms model latency; per-step desktop control at 0.13-0.38 s against 5.2 s, and $0.0002 against $0.032 per decision; a browser agent finding flights in 7.1 s total.

## The budget, stated honestly

| | |
|---|---|
| Model latency | 70-500 ms end to end, most calls ~100 ms |
| Median measured | ~0.15 s |
| p95 | materially worse than median — a 120-item panel estimates tails poorly |

So: **this suits a control loop whose period is ~200 ms or longer.** It does not suit a 10 ms inner loop, a physics step, or an order-book reaction where microseconds decide the fill. For those, the decision layer sets *policy* at 1-10 Hz and a deterministic controller executes inside it.

```
   1-10 Hz  ──> decide(): which regime, which target, hold or act
 100-1000 Hz ──> code: PID / state machine / execution logic, no model in the path
```

That split is the whole design. A model in the inner loop is a design error regardless of how fast the model is, because its p95 is not bounded.

## Rebuild the menu every step

The single best idea to steal from browser agents. Available actions change after every action taken, so do not describe a fixed action space once — build a fresh list of what is observable *now* and choose from that.

```python
from jev import decide, Choice, Noul

def step(observation):
    actions = {a.id: a.description for a in enumerate_available_actions(observation)}
    actions["wait"] = "No action improves the position this tick."
    actions["other"] = "None of the above fits."

    r = decide(
        state={"goal": goal, "observation": render(observation), "last_3_actions": history[-3:]},
        questions={
            "action": Choice(instructions="Choose the next action from the listed options.", criteria=actions),
            "done":   Noul(instructions="The goal has been achieved and no further action is needed."),
        },
    )
    a = r.answers["action"]
    return a.choice if a.confidence >= TAU else "wait", r.answers["done"].noul
```

`wait` and `other` are both no-ops that keep the machine safe. The most confident answer in the world is useless when the option it picked no longer exists — which is what a stale menu guarantees.

## Uncertainty maps to hold, not to a coin flip

In a control loop the default on low confidence is **the null action**, not the best guess:

```python
action = a.choice if a.confidence >= TAU else "wait"
```

This is the opposite of the eval cascade, where escalation buys a better answer. Here there is no time to escalate, so the fallback must be the action that does nothing. Choose `TAU` from the cost of a wrong action versus the cost of a missed tick — in trading those are wildly asymmetric and `TAU` belongs near 0.95; in a game loop a wrong step is free and 0.70 is fine.

## Trading loops: the parts that are not the model

The model decides a label. Everything that makes a trading loop safe is code, and none of it is negotiable:

- **Position limits, per-trade and aggregate.** Code.
- **Daily loss limit and a kill switch.** Code. Checked before every order, not after.
- **Rate and spend caps.** Code.
- **Arithmetic** — P&L, position sizing, risk per trade, spread, fees. Code. The model reads numbers as text and miscounts; rule 6 has teeth here.
- **Idempotency and order dedup.** Code, keyed on a client order ID, because a retried decision must not become two orders.
- **Independent fill confirmation.** A confident answer cannot prove an order filled. Query the exchange.

What the model is good for: regime classification (`trending / ranging / news_shock / other`), whether a setup matches a described pattern, whether news text is material, and how urgent an exit looks. Not the price, not the size.

## Games and robots

- **State rendering is the work.** A screenshot is not an option — input is text only, so you must render the observation as text or JSON. The quality of that rendering is the quality of the decision, more than any threshold is.
- **Cache identical states.** A tick where nothing changed needs no call. Hash the rendered observation and reuse the last verdict; browser agents cut median protocol calls from 1,092 to 101 largely by not re-predicting on irrelevant animation.
- **Latency in a loop is usually structural, not model-bound.** Audit repeated tool calls before paying for a faster anything.
- **Robots: the null action must be genuinely safe.** "Hold" is not safe for a moving actuator. Define the fallback as the physically safe state (stop, retract, brake) and have code enforce it on timeout — a decision that has not arrived within the tick budget must be treated as a low-confidence decision, automatically.

## Stuck detection

Cheap insurance for any long-running loop. Run it every N iterations.

```python
r = decide(
    state={"goal": goal, "last_5_actions": recent_actions, "last_5_observations": recent_observations},
    questions={
        "progressing": Noul(instructions="The last five actions moved measurably closer to the goal."),
        "repeating":   Noul(instructions="The agent is repeating an action that already failed."),
    },
)
if r.answers["repeating"].noul > 0.70 or r.answers["progressing"].noul < 0.30:
    escalate()
```

It costs almost nothing and it is the cheapest protection there is against an overnight run that spends its whole budget going in circles.

## Hard caps stay in code

Action limit, wall-clock limit, spend limit, and saved progress after every action. After an interruption, inspect the last completed action before repeating anything.

## `ControlLoop`: the pattern, assembled

`assets/jev/control.py` is the loop above with the safety parts already in code:

```python
from jev import ControlLoop

loop = ControlLoop(
    goal="Find the cheapest direct flight under 300 CHF",
    observe=lambda: render(page),                 # -> text or JSON; text input only
    actions=lambda obs: available_controls(obs),  # -> {id: description}, rebuilt every tick
    execute=lambda action, obs: click(action),
    null_action="wait",
    tau=0.85,
    verify_done=lambda: results_are_on_screen(),  # independent of the model
)

for tick in loop.run(max_ticks=60, max_seconds=90, max_usd=0.05):
    ...
print(loop.stats())
```

Five behaviours worth knowing, because each encodes a rule from above:

**The menu is rebuilt every tick** from `actions(observation)`, with `null_action` and `other` always added. A stale menu makes the most confident answer useless.

**A missed tick budget IS a low-confidence decision.** If the call overruns `tick_budget_s`, the loop takes the null action — enforced by the clock, not by judgement. This is the mechanism that makes an unbounded p95 safe to live with.

```
t2   wait   HELD   hold: click_submit at 0.60 < tau 0.85
t7   wait   HELD   hold: missed the 600ms budget (812ms)
```

**Low confidence maps to the null action, never to a guess.** Opposite of the eval cascade: there is no time to escalate, so the fallback must be the action that does nothing.

**An unchanged observation costs nothing.** Identical rendered state plus identical menu reuses the last verdict — 83% cache hits over six frozen ticks in the test suite. This is the same lever that took a browser runtime from 1,092 median protocol calls to 101.

**`verify_done` outranks the model.** When the model says done and verification disagrees, the loop logs the disagreement and keeps going:

```
NOTE: model says done (0.97) but verification disagrees -- continuing
```

Stuck detection runs every `stuck_every` ticks and tries the cheap check first: code can see a repeated action or an all-held window with no model call at all. Only if those pass does it spend a call on `progressing` / `repeating`.

## Trading: `RiskLimits`

Everything that keeps a trading loop safe is code, and `RiskLimits.blocks()` is checked **before every order**, never after:

```python
from jev import RiskLimits, classify_regime

limits = RiskLimits(max_position=10, max_daily_loss=100, max_trades_per_day=3)
if reason := limits.blocks(size=size, client_order_id=oid):
    skip(reason)
else:
    send(order); limits.record(size=size, client_order_id=oid)
```

```
size 8 : position limit (+5.0000 +8.0000 exceeds 10)
dup id : duplicate client_order_id o1 -- a retried decision is not a second order
loss   : daily loss limit hit (-150.00 <= -100.00)
count  : daily trade count reached (3)
```

That third-from-last line is the one people omit. A retried decision must not become a second order, so idempotency is keyed on a client order id inside the limit check itself rather than left to the caller to remember.

`classify_regime()` is what the model is genuinely for here — `trending / ranging / news_shock / illiquid / other`, plus whether a described setup is present and whether news text is material. It receives numbers that **code computed** (spread, realised volatility, depth, position) and never calculates them itself.
