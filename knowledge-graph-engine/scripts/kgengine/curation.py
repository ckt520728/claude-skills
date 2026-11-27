"""User-decided entity merges that override automatic resolution.

Raw extractions are never edited; these rules only change the alias table that
`resolve()` writes, so they are re-applied on every re-resolve and can be undone by
deleting a rule. Record each rule's decision in CONTEXT.md / docs/adr.
"""
from __future__ import annotations

import re

# canonical name, entity type, token set: a name merges if all its word tokens are in this set
CURATED_MERGES: list[dict] = [
    {   # ADR 0005 / CONTEXT.md: "physical activity", "physical exercise" and "exercise" are ONE node.
        # Sub-types (aerobic exercise, exercise training, acute exercise, exercise intervention...) stay separate.
        "canonical": "Physical activity / exercise (PA)",
        "type": "INTERVENTION",
        "tokens": {"physical", "activity", "activities", "exercise", "exercises", "pa", "pe", "ex", "and", "or"},
    },
]


def _tokens(name: str) -> set[str]:
    return set(re.findall(r"[a-z]+", name.lower()))


def matches(rule: dict, name: str) -> bool:
    t = _tokens(name)
    return bool(t) and t <= rule["tokens"] and bool(t - {"and", "or"})


def apply_curated_merges(reps: dict[str, list[str]], etype: dict[str, str]) -> int:
    """Mutates reps {canonical: [members]}. A cluster whose canonical matches a rule moves whole;
    otherwise only the matching members move. Returns the number of names moved."""
    moved = 0
    for rule in CURATED_MERGES:
        target: list[str] = []
        for canon in list(reps):
            members = reps[canon]
            if etype.get(canon) != rule["type"]:
                continue
            if canon == rule["canonical"]:
                target.extend(reps.pop(canon))
            elif matches(rule, canon):
                target.extend(reps.pop(canon))
                moved += len(members)
            else:
                hit = [m for m in members if matches(rule, m)]
                if hit:
                    reps[canon] = [m for m in members if m not in hit]
                    target.extend(hit)
                    moved += len(hit)
                    if not reps[canon]:
                        del reps[canon]
        if target:
            reps[rule["canonical"]] = target
            etype[rule["canonical"]] = rule["type"]
    return moved
