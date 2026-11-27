"""Domain ontology for the research topic:
"The role of physical activity in mitigating neurocognitive aging:
 insights from electrophysiological biomarkers and neuroimaging studies."

The ontology is a *gate* (see Reference/Graph_engineering): extraction prompts are
constrained to these types/predicates, and anything off-list is normalized to the
closest allowed value (or RELATED_TO) so the graph topology does not drift.
Swap this module (or pass --ontology) to reuse the engine for another domain.
"""
from __future__ import annotations

import os

# Injected into every prompt. Override with KG_TOPIC for another corpus (bump PROMPT_VERSION too).
RESEARCH_TOPIC = os.environ.get("KG_TOPIC") or (
    "The role of physical activity in mitigating neurocognitive aging: insights from "
    "electrophysiological biomarkers (EEG/MEG/ERP) and neuroimaging studies.")

ENTITY_TYPES: dict[str, str] = {
    "INTERVENTION": "Exercise / physical-activity exposure or other intervention (aerobic training, resistance training, tai chi, cardiorespiratory fitness, step count, sedentary time, rTMS).",
    "BIOMARKER": "A measured electrophysiological, imaging, blood or physiological marker (individual alpha peak frequency, P300 latency, theta/beta ratio, hippocampal volume, white-matter hyperintensity, BDNF level, VO2max, brain age gap).",
    "BRAIN_REGION": "Anatomical structure or network (hippocampus, prefrontal cortex, default mode network, white matter tracts).",
    "COGNITIVE_DOMAIN": "Cognitive function or test construct (executive function, episodic memory, processing speed, MoCA score, Stroop).",
    "CONDITION": "Disease, syndrome or aging state (Alzheimer's disease, MCI, cognitive aging, frailty, depression, type 2 diabetes).",
    "POPULATION": "Study population or cohort (healthy older adults, amyloid-positive adults, children, UK Biobank).",
    "METHOD": "Measurement or analysis method (EEG, MEG, fMRI, DTI, PET, ERP, source localization, meta-analysis, RCT).",
    "MECHANISM": "Biological mechanism or pathway (neurogenesis, angiogenesis, neuroinflammation, cerebral blood flow, neurotrophic signalling, amyloid clearance).",
    "CONCEPT": "Theoretical construct or framework (cognitive reserve, brain maintenance, compensation, CRUNCH, STAC model).",
}

# Allowed predicates. Direction is always (source) -[PREDICATE]-> (target).
PREDICATES: dict[str, str] = {
    "IMPROVES": "source improves/benefits target (functional improvement)",
    "INCREASES": "source increases the level/size/value of target",
    "DECREASES": "source decreases/reduces target",
    "NO_EFFECT_ON": "source was tested and showed no significant effect on target",
    "PROTECTS_AGAINST": "source lowers risk or slows progression of target",
    "RISK_FACTOR_FOR": "source raises risk of target",
    "ASSOCIATED_WITH": "correlational association without stated direction",
    "PREDICTS": "source predicts target (prognostic/statistical prediction)",
    "BIOMARKER_OF": "source is a marker/indicator of target",
    "MEDIATES": "source mediates an effect (on target)",
    "MODERATES": "source moderates an effect on target",
    "MEASURED_BY": "source construct/biomarker is measured with method/test target",
    "ALTERED_IN": "source biomarker/region is altered in condition/population target",
    "LOCATED_IN": "source (biomarker/activity) is localized in brain region target",
    "PART_OF": "source is a part/sub-type of target",
    "IS_A": "source is an instance/type of target",
    "STUDIED_IN": "source was studied in population target",
    "RELATED_TO": "fallback when no other predicate fits",
}

# Edge qualifier (ADR 0004): acute-bout and chronic-training effects are different claims and are
# kept as separate edges. Applies to effect claims of an INTERVENTION; everything else is "unspecified".
TIMESCALES: dict[str, str] = {
    "acute": "effect of a single exercise bout / session, measured during or shortly (minutes-hours) after it",
    "chronic": "effect of repeated training over weeks or longer, or of long-term habitual physical activity / fitness",
    "unspecified": "not an exercise/intervention effect, or the text does not say which",
}

SYNONYMS: dict[str, str] = {
    "ENHANCES": "IMPROVES", "BENEFITS": "IMPROVES", "PROMOTES": "IMPROVES",
    "ATTENUATES": "DECREASES", "REDUCES": "DECREASES", "LOWERS": "DECREASES", "SLOWS": "DECREASES",
    "RAISES": "INCREASES", "ELEVATES": "INCREASES", "UPREGULATES": "INCREASES",
    "CORRELATES_WITH": "ASSOCIATED_WITH", "LINKED_TO": "ASSOCIATED_WITH", "RELATED_WITH": "ASSOCIATED_WITH",
    "INDICATES": "BIOMARKER_OF", "MARKER_OF": "BIOMARKER_OF",
    "PREVENTS": "PROTECTS_AGAINST", "MITIGATES": "PROTECTS_AGAINST",
    "ASSESSED_BY": "MEASURED_BY", "QUANTIFIED_BY": "MEASURED_BY",
    "SUBTYPE_OF": "IS_A", "TYPE_OF": "IS_A", "COMPONENT_OF": "PART_OF",
}


def normalize_predicate(p: str) -> str:
    key = p.strip().upper().replace(" ", "_").replace("-", "_")
    if key in PREDICATES:
        return key
    return SYNONYMS.get(key, "RELATED_TO")


def normalize_type(t: str) -> str:
    key = t.strip().upper().replace(" ", "_")
    return key if key in ENTITY_TYPES else "CONCEPT"


def describe() -> str:
    ents = "\n".join(f"- {k}: {v}" for k, v in ENTITY_TYPES.items())
    preds = "\n".join(f"- {k}: {v}" for k, v in PREDICATES.items())
    ts = "\n".join(f"- {k}: {v}" for k, v in TIMESCALES.items())
    return (f"Entity types:\n{ents}\n\nAllowed predicates (source -> target):\n{preds}"
            f"\n\nRelation timescale (required on every relation):\n{ts}")


def normalize_timescale(t: str | None) -> str:
    t = (t or "").strip().lower()
    return t if t in TIMESCALES else "unspecified"
