// Multi-Agent Literature-Review Pipeline v1.0 — Virtual Brain / E-I Balance in Aging & AD
// Project: D:\Virtual brain_simulation_Neuronal_E_I_balance
// Goal: synthesize 3 NotebookLM source notes (+ their 13 cited primary papers) into an
//       English APA-7th literature review on inferring neuronal E/I balance from EEG/MEG via
//       neural-mass / virtual-brain models in NORMAL AGING vs ALZHEIMER'S DISEASE.
//
// Reuses the PHCSSM v3.0 (Robin MAS) pattern + its 6 reusable schemas:
//   [R1] Structured JSON Schemas      — prevent error cascading
//   [R2] A1 Consensus Trajectories    — 3x mathematical analysis, >=2/3 intersection = consensus
//   [R3] Grounding Check Gate         — every claim must trace to the SOURCE notes (no model-weight claims)
//   [R4] BTL Tournament Gate          — pairwise contradiction resolution
//   [R5] Consensus Adversarial Critique — 3x Reflector, >=2/3 intersection
//   + Self-Healing Synthesis Loop
//
// Grounding note: analysis agents read the embedded SOURCES digest (English, condensed from the
// 3 notes). The Grounding agent ALSO reads the 3 ORIGINAL note files to catch digest drift.

export const meta = {
  name: 'vbm-ei-ad-review-v1',
  description: 'Literature-review multi-agent synthesis: virtual-brain E/I inference in aging & AD',
  phases: [
    { title: 'Domain Analysis',  detail: 'A1(x3 math consensus), A2 methods, A3 evidence, A4 mechanism, A6 gaps — structured JSON [R1][R2]' },
    { title: 'Math Consensus',   detail: '3 NMM-math trajectories merged by >=2/3 intersection [R2]' },
    { title: 'Grounding Check',  detail: 'All claims verified against the 3 source notes; drift/overreach flagged [R3]' },
    { title: 'BTL Tournament',   detail: 'Pairwise resolution of inter-source contradictions [R4]' },
    { title: 'Consensus Critique', detail: '3 adversarial reflectors -> >=2/3 consensus weaknesses [R5]' },
    { title: 'Synthesis',        detail: 'Full English review draft with in-text citations; self-healing gap-fill' },
  ],
}

// Original note files (Grounding agent reads these directly)
const NOTE_FILES = [
  'D:\\Virtual brain_simulation_Neuronal_E_I_balance\\notebooklm-note-neural-mass-model-神經質量模型與阿茲海默症虛擬大腦分析-2026-06-21.md',
  'D:\\Virtual brain_simulation_Neuronal_E_I_balance\\notebooklm-note-virtual-brain-model-虛擬大腦模型-解碼阿茲海默症神經網絡失能機制-2026-06-21.md',
  'D:\\Virtual brain_simulation_Neuronal_E_I_balance\\notebooklm-note-ad-virtual-brain-model-阿茲海默症虛擬大腦-從分子病理到神經動態建模-2026-06-21.md',
]

// ─── Source corpus (paper attributions; agents cite by Author Year) ─────────────
const SOURCE_MAP = `
PRIMARY PAPERS (cite by Author Year in every paper_evidence field):
- Clusella 2022 — "Comparison between an exact and a heuristic neural mass model with second-order synapses." Exact mean-field (QIF/Montbrio-Pazo-Roxin) NMM2 vs heuristic sigmoid NMM1.
- Cooray 2023 — "Global dynamics of neural mass models." Adiabatic approximation; potential-function / gradient-flow; SDE + Fokker-Planck steady state; exit/dwell times.
- Deschle 2021 — "On the validity of neural mass models." E/I topology parameter lambda = Nexc/(Ninh+Nexc); mean-field validity boundary near low-freq synchronization onset only.
- Deco 2015 — resting-state fluctuation dynamics / large-scale modeling (context for whole-brain modeling).
- Glomb 2017 — "Resting state networks in empirical and simulated dynamic functional connectivity" (NeuroImage).
- Lu 2022 — "Multiscale brain network models for neuropsychiatric disease" (Electronics) — review of BNM framework, descriptive vs generative, DCM scalability limits.
- Schirner 2018 — "Inferring multi-scale neural mechanisms with brain network modelling" (eLife) — hybrid model: empirical EEG source injected as EPSC; predicts 20-min subject-specific fMRI; inhibitory half-wave rectification of alpha -> slow RSN fluctuations.
- Stam 2023 — "Network hyperexcitability in early Alzheimer's disease is functional" — 78-node Stuart-Landau whole-brain; bifurcation param a (E/I) and global coupling G; AEC vs PC sensitivity; theta-band AECc peaks at hyperexcitable critical point; MEG in SCD/MCI (SCD r=0.697, MCI r=0.587).
- Stefanovski 2019 — "Linking molecular pathways and large-scale computational modeling to assess candidate disease mechanisms and pharmacodynamics in Alzheimer's disease" (Front. Comput. Neurosci.) — TVB + Jansen-Rit; ADNI-3 N=33 (10 AD/8 MCI/15 HC); AV-45 Abeta-PET SUVR -> sigmoid -> local tau_i (14->up to 50 ms); alpha->theta slowing on fixed healthy SC; virtual Memantine (c31 -25%) normalizes spectra.
- Stefanovski 2021 — "Bridging scales in Alzheimer's disease: biological framework for brain simulation with The Virtual Brain" (Front. Neuroinform.) — framework/review; Tau vs Abeta; multi-scale.
- Yokoyama 2023 — "A data assimilation method to track excitation-inhibition balance using scalp EEG" — nonlinear NMM + variational-Bayes constrained ensemble Kalman filter (vbcEnKF); mE/I = A/(A+B); 19 subjects whole-night sleep EEG; sub-second E/I tracking; outperforms 1/f E/I-slope.
- Zimmermann 2018 — "Differentiation of Alzheimer's disease based on local and global parameters in personalized Virtual Brain models" (NeuroImage: Clinical) — MAS cohort N=124 (73 HC/35 aMCI/16 AD); per-subject SC; parameter-space exploration of G, E-E, E-I, I-E; PLS to 6 cognitive scores; limbic subnet embeddedness; model params beat raw SC/FC for predicting cognition.
- Maestu 2021 — "Neuronal excitation/inhibition imbalance: core element of a translational perspective on Alzheimer pathophysiology" (Ageing Res. Rev.) — E/I imbalance as translational hub linking Abeta toxicity to network dysfunction; anterior hypersynchrony / posterior hyposynchrony; Levetiracetam stratification.
`

// ─── SOURCES — English digest of the 3 notes (analysis agents ground in this) ───
const SOURCES = `
=== SOURCE DIGEST (condensed faithfully from 3 NotebookLM notes; cite papers by Author Year) ===

THEME A — MATHEMATICAL BASIS OF NEURAL MASS MODELS (NMMs)
A1. Exact vs heuristic NMM (Clusella 2022): Heuristic NMM1 assumes population mean firing rate r is a
   static nonlinear sigmoid of mean membrane potential. Clusella, from exact mean-field of QIF neurons
   (Montbrio-Pazo-Roxin), derives NMM2 where firing rate is NOT static but coupled to mean membrane
   potential v via two nonlinear ODEs. As N->inf, membrane-potential density follows a Lorentzian
   (Ott-Antonsen-type) ansatz giving macroscopic eqs: tau_m r' = Delta/(pi tau_m) + 2 r v ;
   tau_m v' = eta - (pi r tau_m)^2 + v^2 + tau_m J s + I_E(t), with s a 2nd-order synaptic variable and
   J the coupling (E/I). Heuristic NMM1 is only the infinitely-slow-synapse limit of the exact theory.
   Consequence for AD: NMM1 cannot produce self-sustained ING (interneuron-gamma) oscillations in
   inhibitory networks; NMM2, via the tau_m/tau_s ratio, reproduces them — relevant to AD gamma/PV+
   interneuron pathology.
A2. Adiabatic approximation & potential landscape (Cooray 2023): separate fast phase dynamics (fast
   EEG oscillation) from slow amplitude modulation via timescale separation + 2nd-order perturbation.
   Slow amplitude mean rate becomes gradient flow on a potential U: dI = -grad U dt + sigma dB (an SDE).
   Fokker-Planck steady state p_st = (1/Z) exp(-2U/sigma^2). Enables closed-form mean exit/dwell times
   between brain states (e.g., resting vs seizure-like). Changing the anatomical synaptic coupling matrix
   G (e.g., AD synapse loss) directly reshapes the landscape U and predicts abnormal state dwell times.
   Causal direction is micro(fast)->macro(slow); a common misconception is that slow drives fast.
A3. Mean-field validity boundary (Deschle 2021): define E/I topology lambda = Nexc/(Ninh+Nexc). Compared
   true LIF-network mean to two perturbatively-derived NMMs. The crude assumption <g v> ~= <g> Vbar
   (single neuron tracks population mean) fails badly under high synchronization (high-freq) or full
   desynchronization. NMMs faithfully represent the network ONLY near the low-frequency synchronization
   onset (roughly lambda in 0.70-0.85). Spectral predictions diverge from LIF (significant chi^2) at
   high-freq sync; only the critical transition region has high fidelity.
A4. Prior-method gaps (math): Jansen-Rit / Epileptor inject a slow "permittivity" variable by hand to
   model seizures (no micro-synaptic evidence); static sigmoid transfer lacks physical basis for
   resonant responses. Cooray DERIVES slow dynamics from the synaptic matrix G; Clusella's 2nd-order
   synaptic kinetics (tau_m, tau_s) naturally bridge single-neuron physics to mesoscale activity.
   Deschle's warning: even rigorously derived NMMs are fragile for dense/heterogeneous nets away from
   the critical point — predictions can be qualitatively wrong when E/I ratio leaves criticality.
A5. Strengths/limits of the NMM math: NMM2 embeds tau_m and tau_s -> strong biophysical meaning;
   landscape/gradient-flow gives closed-form densities & mean exit times -> efficient EEG-based inversion
   of synaptic params. Limits: homogeneity assumption (identical neurons per mass) unrealistic for AD's
   heterogeneous plaque/tangle load; mean-field breaks at high-freq sync (chi^2 divergence); high-fidelity
   only in the critical transition band.

THEME B — MULTISCALE VIRTUAL-BRAIN MODELING & E/I INFERENCE METHODS
B1. Network hyperexcitability & E/I imbalance (Maestu 2021): in early AD, Abeta oligomers impair
   glutamate reuptake / damage inhibitory interneurons -> pyramidal hyperexcitability. E/I imbalance is
   the translational hub linking molecular Abeta toxicity to macroscale network failure; manifests as
   band-specific (esp. theta) hypersynchronization predicting later network collapse and cognitive decline.
B2. Multiscale Brain Network Models (BNMs) (Lu 2022): structural connectome (SC) from dMRI/DWI = edges;
   NMMs or oscillators (e.g., Stuart-Landau) = nodes. BNMs simulate fMRI BOLD or M/EEG and allow inverse
   inference of hidden physiological params (local E/I). Descriptive graph-theory BNMs (hubs, path length)
   show WHAT changes but not WHY (no causal mechanism); DCM is causal but doesn't scale to whole brain.
B3. Data assimilation & hybrid modeling: (Schirner 2018) hybrid model injects empirical EEG source
   activity as excitatory postsynaptic current (EPSC) into nodes -> predicts 20-min subject-specific fMRI;
   reveals inhibitory half-wave rectification converting alpha-power envelope into slow firing-rate
   fluctuations -> slow RSNs via neurovascular coupling. (Yokoyama 2023) variational-Bayes constrained
   ensemble Kalman filter (vbcEnKF) assimilates EEG sample-by-sample in a nonlinear NMM; variational-Bayes
   noise adaptation prevents divergence under nonstationary observation noise; stable E/I extraction even
   <20 Hz (vs gamma-dependent 1/f E/I-slope). mE/I = A/(A+B) from excitatory gain A & inhibitory gain B.
B4. Node-dynamics choice: for macroscale FC dysfunction -> Stuart-Landau oscillator (cheap; bifurcation
   param a tunes E/I; maximizes AEC fidelity). For specific synaptic/drug mechanism -> biophysical NMM
   (Jansen-Rit / Reduced Wong-Wang) with explicit E/I postsynaptic potentials, suited to data assimilation.

THEME C — EMPIRICAL EVIDENCE ACROSS NORMAL AGING AND AD
C1. Stam 2023 (Stuart-Landau, MEG): 78-node whole-brain; vary bifurcation a (E/I) & global coupling G;
   compare model FC to real MEG of 18 SCD + 18 MCI. Amplitude-envelope correlation (corrected, AECc)
   peaks at the dynamic critical point (noisy fixed point -> limit cycle, a>0 hyperexcitable). Best match
   to empirical theta-band (4-8 Hz) network at HIGH E/I (hyperexcitable) + moderate coupling (G~1):
   SCD r=0.697, MCI r=0.587. -> Theta AEC is the most sensitive marker of early-AD hyperexcitability;
   AEC and phase-consistency have DIFFERENT E/I sensitivity (FC as surrogate for hyperexcitability).
C2. Yokoyama 2023 (vbcEnKF, EEG): nonlinear NMM + vbcEnKF on 19 healthy subjects' whole-night sleep EEG;
   independent estimates of excitatory gain A & inhibitory gain B; mE/I = A/(A+B). Captures sub-second
   E/I shifts: mE/I rises in deep NREM (excitation-dominant), falls in REM (inhibition-dominant);
   traditional E/I-slope detects none of these physiological transitions. -> robust synaptic-level
   decoding from routine EEG.
C3. Schirner 2018 (hybrid): inject 15 subjects' EEG source as EPSC into their DWI SC; predicts 20-min
   subject-specific fMRI; mechanism = inhibitory half-wave rectification of high-amplitude alpha (cannot
   produce negative firing rate) -> alpha envelope becomes low-freq rate fluctuation -> fMRI slow RSNs.
   -> nonlinear physiological bounds (rate>=0) are essential to reproduce macro dynamics.
C4. Stefanovski 2019 (TVB + Jansen-Rit, Abeta-PET-driven): ADNI-3 N=33 (10 AD/8 MCI/15 HC). Hold whole-
   brain SC fixed at healthy mean (control confound); per-region AV-45 SUVR via sigmoid lengthens local
   tau_i (default 14 ms -> up to 50 ms above 1.4 SUVR threshold). Result: virtual EEG/LFP shows marked
   alpha->theta (~4 Hz peak) slowing + chaotic dynamics; shuffling Abeta spatial distribution keeps
   slowing concentrated at network hubs (heterogeneity + hub propagation required; homogeneous Abeta gives
   no slowing). Virtual Memantine (excitatory c31 -25%, NMDA-antagonist) renormalizes mean frequency
   toward HC/MCI; drug effect concentrates on hyperactive hubs. Heun integration, 5 ms step.
C5. Zimmermann 2018 (TVB inverse, fMRI->params->cognition): MAS cohort N=124 (73 HC/35 aMCI/16 AD);
   per-subject SC; parameter-space search of global G and local E-E, E-I, I-E to best fit empirical FC;
   PLS to 6 cognitive scores. In limbic subnet: higher G and excitatory coupling (E-E, E-I) correlate
   NEGATIVELY with cognition; local inhibition (I-E) correlates POSITIVELY. Model params predict cognition
   BETTER than raw SC/FC. "Embeddedness" = difference between limbic-subnet-optimal and whole-brain-optimal
   params, a candidate biomarker of network integration breakdown.

THEME D — MOLECULAR-TO-NETWORK MECHANISM & TRANSLATIONAL IMPLICATIONS
D1. Claim map: Abeta/Tau (molecular) -> inhibitory interneuron damage / glutamate dysregulation (synaptic)
   -> local E/I imbalance & hyperexcitability (circuit) -> spectral change: alpha-power drop, theta
   hypersynchronization (network) -> impaired information transfer -> cognitive decline. BNM + data
   assimilation inverts macro EEG/MEG back to hidden E/I params.
D2. Disinhibition mechanism (Stefanovski 2019): Abeta selectively harms fast-spiking inhibitory
   interneurons (reduced GABA_A PSC), removing pyramidal-cell braking -> local hyperexcitability;
   modeled as lengthened inhibitory time constant tau_i in Jansen-Rit.
D3. Hub propagation of slowing (Stefanovski 2019): EEG slowing is not just local death; few high-Abeta
   regions broadcast abnormal slow oscillation through structural hubs (e.g., DMN/precuneus). Homogeneous
   Abeta -> no slowing (spatial heterogeneity necessary).
D4. Dual-hit recommendation (Stefanovski 2021; AD note): use Tau-PET / atrophy to LOWER local coupling
   (neuronal death/disconnection) AND Abeta-PET to LENGTHEN tau_i (hyperexcitability) — dual pathology
   raises clinical realism. Reduced Wong-Wang or Jansen-Rit allow independent E and I manipulation.
D5. Translational: internal params map to neurobiology (tau_e, tau_i, synaptic gains) -> in-silico drug
   tests (Memantine NMDA-antagonist; Levetiracetam for hyperexcitability stratification; Maestu 2021).
   AECc theta sensitivity (Stam 2023) -> patient-stratification biomarker for anti-hyperexcitability trials.

KEY TENSIONS / OPEN QUESTIONS (for BTL + reflectors):
- Stuart-Landau (phenomenological, cheap) vs Jansen-Rit / Wong-Wang (biophysical) — which is "right" for
  inferring E/I? Depends on question (macro FC vs synaptic/drug).
- Abeta-only (Stefanovski 2019) vs dual-hit Abeta+Tau (Stefanovski 2021) — single-molecule attribution may
  overestimate Abeta's pure dynamic effect (Tau correlates better with atrophy/cognition).
- Mean-field validity (Deschle 2021): inferred E/I may be unreliable in strongly de/hyper-synchronized AD
  regions outside the critical band.
- NORMAL AGING vs AD differentiation: aging ~ diffuse SC weight loss (global G dominates); AD adds local
  I-E/E-I synaptic derailment + Abeta/Tau heterogeneity. aMCI shows highest variance (compensation vs
  collapse transition).
- Validation gaps: ADNI-3 had no concurrent real EEG to validate virtual EEG (Stefanovski 2019);
  Zimmermann lacks conduction delays; Yokoyama single-channel; BOLD neurovascular confounds in AD.
`

// ─── 6 reusable schemas (PHCSSM v3.0) ──────────────────────────────────────────
const ANALYSIS_SCHEMA = {
  type: 'object',
  properties: {
    agent_id: { type: 'string' },
    key_findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          paper_evidence: { type: 'string', description: 'Source attribution (Author Year) + the specific SOURCES content supporting this claim' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['claim', 'paper_evidence', 'confidence'],
      },
    },
    strengths: { type: 'array', items: { type: 'string' }, description: 'Strengths of this body of work for the review thesis' },
    weaknesses: { type: 'array', items: { type: 'string' } },
    unverified_claims: { type: 'array', items: { type: 'string' }, description: 'Assertions that lack sufficient evidence in the sources' },
    overall_confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
  },
  required: ['agent_id', 'key_findings', 'strengths', 'weaknesses', 'unverified_claims', 'overall_confidence'],
}

const A1_CONSENSUS_SCHEMA = {
  type: 'object',
  properties: {
    consensus_findings: { type: 'array', items: { type: 'string' }, description: 'Math claims in >=2 of 3 trajectories' },
    trajectory_divergences: {
      type: 'array',
      items: {
        type: 'object',
        properties: { topic: { type: 'string' }, t1_position: { type: 'string' }, t2_position: { type: 'string' }, t3_position: { type: 'string' } },
        required: ['topic'],
      },
    },
    consensus_unverified_claims: { type: 'array', items: { type: 'string' } },
    merged_confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
  },
  required: ['consensus_findings', 'trajectory_divergences', 'consensus_unverified_claims', 'merged_confidence'],
}

const GROUNDING_SCHEMA = {
  type: 'object',
  properties: {
    grounded_claims: { type: 'array', items: { type: 'string' } },
    hallucination_flags: {
      type: 'array',
      items: {
        type: 'object',
        properties: { agent: { type: 'string' }, claim: { type: 'string' }, issue: { type: 'string' } },
        required: ['agent', 'claim', 'issue'],
      },
      description: 'Claims that exceed/contradict the source notes (incl. digest drift vs original files)',
    },
    coverage_gaps: { type: 'array', items: { type: 'string' } },
  },
  required: ['grounded_claims', 'hallucination_flags', 'coverage_gaps'],
}

const BTL_SCHEMA = {
  type: 'object',
  properties: {
    contradictions: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          topic: { type: 'string' },
          agent_a: { type: 'string' }, claim_a: { type: 'string' },
          agent_b: { type: 'string' }, claim_b: { type: 'string' },
          winner: { type: 'string', enum: ['agent_a', 'agent_b', 'tie'] },
          rationale: { type: 'string' },
        },
        required: ['topic', 'agent_a', 'claim_a', 'agent_b', 'claim_b', 'winner', 'rationale'],
      },
    },
    resolved_consensus: { type: 'array', items: { type: 'string' } },
    synthesis_instructions: { type: 'array', items: { type: 'string' } },
  },
  required: ['contradictions', 'resolved_consensus', 'synthesis_instructions'],
}

const CRITIQUE_SCHEMA = {
  type: 'object',
  properties: {
    critical_weaknesses: {
      type: 'array',
      items: {
        type: 'object',
        properties: { weakness: { type: 'string' }, severity: { type: 'string', enum: ['fatal', 'major', 'minor'] } },
        required: ['weakness', 'severity'],
      },
    },
    aging_vs_ad_differentiation: { type: 'string', description: 'Does the corpus genuinely separate normal aging from AD E/I changes? Where is it weak?' },
    validity_and_validation_assessment: { type: 'string', description: 'Mean-field validity limits + empirical validation gaps' },
    reviewer_rejection_reasons: { type: 'array', items: { type: 'string' }, description: 'Why a journal reviewer would push back on a review built on this corpus' },
  },
  required: ['critical_weaknesses', 'aging_vs_ad_differentiation', 'validity_and_validation_assessment', 'reviewer_rejection_reasons'],
}

const REFLECTOR_CONSENSUS_SCHEMA = {
  type: 'object',
  properties: {
    consensus_weaknesses: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          weakness: { type: 'string' },
          severity: { type: 'string', enum: ['fatal', 'major', 'minor'] },
          source_reflectors: { type: 'array', items: { type: 'string' } },
        },
        required: ['weakness', 'severity', 'source_reflectors'],
      },
    },
    single_reflector_findings: { type: 'array', items: { type: 'string' } },
    overall_verdict_recommendation: { type: 'string' },
  },
  required: ['consensus_weaknesses', 'single_reflector_findings', 'overall_verdict_recommendation'],
}

const REVIEW_SYNTHESIS_SCHEMA = {
  type: 'object',
  properties: {
    title: { type: 'string', description: 'Academic review paper title (English)' },
    abstract: { type: 'string', description: '200-300 word structured abstract' },
    sections: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          heading: { type: 'string' },
          markdown_body: { type: 'string', description: 'Full prose with in-text citations (Author, Year). Multi-paragraph.' },
        },
        required: ['heading', 'markdown_body'],
      },
      description: 'Ordered sections: Introduction; Mathematical Foundations of NMMs; Multiscale Virtual-Brain Modeling & E/I Inference; Empirical Evidence Across Normal Aging and AD; Molecular-to-Network Mechanisms & Translation; Limitations & Validity Boundaries; Future Directions; Conclusion',
    },
    citations_used: { type: 'array', items: { type: 'string' }, description: 'Every Author-Year cited in text (must all map to SOURCE_MAP papers)' },
    open_questions: { type: 'array', items: { type: 'string' } },
    all_btl_instructions_addressed: { type: 'boolean' },
    all_consensus_weaknesses_addressed: { type: 'boolean' },
    missed_items: { type: 'array', items: { type: 'string' } },
  },
  required: ['title', 'abstract', 'sections', 'citations_used', 'open_questions',
    'all_btl_instructions_addressed', 'all_consensus_weaknesses_addressed', 'missed_items'],
}

const GROUND_RULE = `IMPORTANT: Every claim MUST be grounded in the SOURCES digest and attributed to a paper
(Author Year) from SOURCE_MAP. Do NOT introduce facts, numbers, or papers from your own training; if a
needed fact is absent from SOURCES, say so rather than inventing it. Distinguish normal aging from AD
wherever the sources allow.`

// ─── Phase 1: Domain Analysis ──────────────────────────────────────────────────
phase('Domain Analysis')

const [a1_t1, a1_t2, a1_t3, a2_methods, a3_evidence, a4_mechanism, a6_gaps] = await parallel([

  // A1 — Math basis, Trajectory 1: exact mean-field derivation completeness
  () => agent(`You are Agent 1 (NMM Mathematics, Trajectory 1 — Formal Derivation). ${GROUND_RULE}

${SOURCE_MAP}
${SOURCES}

Focus — formal completeness of the NMM mathematics:
1. How does the exact mean-field NMM2 (Clusella 2022) differ formally from the heuristic sigmoid NMM1, and why is NMM1 only a limiting case?
2. State the macroscopic ODEs and the role of tau_m, tau_s, J, and the 2nd-order synaptic variable s. Why does this matter for ING/gamma in AD?
3. Cooray 2023: how is slow amplitude dynamics derived as gradient flow on a potential U, and what does the SDE + Fokker-Planck steady state buy you (closed-form dwell/exit times)?
4. Which biological terms are dropped to reach affine/closed form?
For every key_finding, put the paper attribution + specific SOURCES evidence in paper_evidence.`,
    { label: 'A1:Math-T1', phase: 'Domain Analysis', model: 'opus', schema: ANALYSIS_SCHEMA }),

  // A1 — Trajectory 2: failure modes / validity boundaries
  () => agent(`You are Agent 1 (NMM Mathematics, Trajectory 2 — Failure Modes & Validity). ${GROUND_RULE}

${SOURCE_MAP}
${SOURCES}

Focus — where the mean-field mathematics breaks:
1. Deschle 2021: define lambda = Nexc/(Ninh+Nexc); which approximation (<g v> ~= <g> Vbar) fails and under what synchronization regimes? Quantify the validity band (lambda ~0.70-0.85, near low-freq onset).
2. What are the consequences for INFERRING E/I from EEG in strongly hyper- or de-synchronized AD regions?
3. Homogeneity assumption: why is "identical neurons per mass" unrealistic for AD heterogeneity?
4. Does lengthening tau_i (Stefanovski 2019) create a math artifact (rising absolute inhibition AUC) that confounds "hyperexcitability"? Explain the relative-vs-absolute excitation issue.
For every key_finding, put paper attribution + SOURCES evidence in paper_evidence.`,
    { label: 'A1:Math-T2', phase: 'Domain Analysis', model: 'opus', schema: ANALYSIS_SCHEMA }),

  // A1 — Trajectory 3: landscape dynamics & inversion
  () => agent(`You are Agent 1 (NMM Mathematics, Trajectory 3 — Landscape Dynamics & Inversion). ${GROUND_RULE}

${SOURCE_MAP}
${SOURCES}

Focus — dynamics, bifurcation and model inversion:
1. How does changing the coupling matrix G (synapse loss) reshape Cooray's potential U and alter state dwell times? Link to AD seizure-like transitions.
2. Stuart-Landau bifurcation parameter a (Stam 2023): how does crossing the noisy-fixed-point -> limit-cycle boundary correspond to E/I and to peak AEC?
3. Model inversion: how are local (E-E, E-I, I-E) and global G parameters recovered by fitting simulated FC to empirical FC (Zimmermann 2018) or by Kalman assimilation (Yokoyama 2023)? What makes inversion identifiable or not?
For every key_finding, put paper attribution + SOURCES evidence in paper_evidence.`,
    { label: 'A1:Math-T3', phase: 'Domain Analysis', model: 'opus', schema: ANALYSIS_SCHEMA }),

  // A2 — Virtual-brain modeling & E/I inference methods
  () => agent(`You are Agent 2 (Modeling Frameworks & E/I Inference Methods). ${GROUND_RULE}

${SOURCE_MAP}
${SOURCES}

Analyze the methodological toolbox:
1. Multiscale BNM anatomy (Lu 2022): SC-from-dMRI edges + NMM/oscillator nodes; descriptive vs generative; why DCM doesn't scale.
2. Node-dynamics choice: Stuart-Landau vs Jansen-Rit vs Reduced Wong-Wang — when to use which, and the cost/biophysical-fidelity tradeoff.
3. Data assimilation: Yokoyama vbcEnKF (sample-by-sample, variational-Bayes noise adaptation, mE/I=A/(A+B), works <20 Hz) vs the 1/f E/I-slope method's limits.
4. Hybrid modeling: Schirner 2018 EEG-as-EPSC injection; inhibitory half-wave rectification producing slow RSNs; the autonomy cost of needing external drive.
5. The forward (Abeta-PET -> tau_i, Stefanovski 2019) vs inverse (FC -> params, Zimmermann 2018) modeling directions.
For every key_finding, put paper attribution + SOURCES evidence in paper_evidence.`,
    { label: 'A2:Methods', phase: 'Domain Analysis', model: 'sonnet', schema: ANALYSIS_SCHEMA }),

  // A3 — Empirical evidence across aging & AD
  () => agent(`You are Agent 3 (Empirical Evidence — Aging & AD). ${GROUND_RULE}

${SOURCE_MAP}
${SOURCES}

Critically summarize the empirical evidence (designs, cohorts, numbers, results, strength):
1. Stam 2023 — Stuart-Landau vs MEG (SCD/MCI); theta AECc peak at hyperexcitable critical point; r values; AEC vs phase-consistency.
2. Yokoyama 2023 — vbcEnKF sleep-EEG E/I tracking (NREM up, REM down); beats E/I-slope.
3. Stefanovski 2019 — ADNI-3 N=33 Abeta-PET-driven virtual EEG slowing; hub propagation; shuffle/homogeneous controls; virtual Memantine.
4. Zimmermann 2018 — MAS N=124 inverse params vs 6 cognitive scores; limbic E/I directions; params beat SC/FC; embeddedness.
Be explicit about sample sizes, what is proven vs suggested, and what separates AGING from AD.
For every key_finding, put paper attribution + SOURCES evidence in paper_evidence.`,
    { label: 'A3:Evidence', phase: 'Domain Analysis', model: 'opus', schema: ANALYSIS_SCHEMA }),

  // A4 — Molecular-to-network mechanism & translation
  () => agent(`You are Agent 4 (Molecular-to-Network Mechanism & Translation). ${GROUND_RULE}

${SOURCE_MAP}
${SOURCES}

Analyze the mechanistic chain and clinical translation:
1. The claim map Abeta/Tau -> interneuron damage -> local E/I imbalance/hyperexcitability -> theta hypersynchrony/alpha drop -> cognitive decline (Maestu 2021; Stefanovski 2019).
2. Disinhibition modeled as tau_i lengthening; hub/DMN propagation; necessity of Abeta spatial heterogeneity.
3. Dual-hit (Abeta lengthens tau_i; Tau/atrophy lowers coupling) — Stefanovski 2021 recommendation.
4. In-silico pharmacology: virtual Memantine normalization; Levetiracetam stratification; theta-AECc as trial biomarker.
5. Anterior hypersynchrony / posterior hyposynchrony pattern.
For every key_finding, put paper attribution + SOURCES evidence in paper_evidence.`,
    { label: 'A4:Mechanism', phase: 'Domain Analysis', model: 'sonnet', schema: ANALYSIS_SCHEMA }),

  // A6 — Gaps & aging-vs-AD contrast scan (concise)
  () => agent(`You are Agent 6 (Gaps & Aging-vs-AD Contrast). Be concise. ${GROUND_RULE}

${SOURCE_MAP}
${SOURCES}

Identify:
1. How (if at all) the corpus distinguishes NORMAL AGING E/I changes from AD-specific changes (global SC loss vs local synaptic derailment; aMCI variance as compensation/collapse).
2. The most important unmet needs / validation gaps (no concurrent real EEG in ADNI-3; single-channel; missing conduction delays; BOLD neurovascular confound; small N).
3. What a comprehensive review MUST cover that the 3 notes underweight.
4. The broader research trend this corpus sits in.
For every key_finding, put paper attribution + SOURCES evidence in paper_evidence.`,
    { label: 'A6:Gaps', phase: 'Domain Analysis', model: 'haiku', schema: ANALYSIS_SCHEMA }),
])

// ─── Phase 2: Math Consensus Merge ─────────────────────────────────────────────
phase('Math Consensus')

const a1_consensus = await agent(`You are the A1 Math Consensus Merger. Apply the Robin rule: a finding is consensus if >=2 of 3 trajectories make the same core claim.

TRAJECTORY 1 (Formal Derivation): ${JSON.stringify(a1_t1)}
TRAJECTORY 2 (Failure Modes & Validity): ${JSON.stringify(a1_t2)}
TRAJECTORY 3 (Landscape Dynamics & Inversion): ${JSON.stringify(a1_t3)}

1. consensus_findings: claims agreed by >=2 trajectories (wording may differ).
2. trajectory_divergences: topics where they disagree — high-uncertainty signals.
3. consensus_unverified_claims: under-supported claims flagged by >=2 trajectories.
4. merged_confidence: 'high' if all 3 agree, 'medium' if 2/3, 'low' if major divergence.
Do not invent consensus.`,
  { label: 'A1:Consensus', phase: 'Math Consensus', model: 'sonnet', schema: A1_CONSENSUS_SCHEMA })

// ─── Phase 3: Grounding Check (reads the ORIGINAL note files) ───────────────────
phase('Grounding Check')

const a_grounding = await agent(`You are Agent G (Grounding Checker). First, READ these three original source-note files in full using your Read tool, then verify every major agent claim against them. A claim is grounded ONLY if the notes contain direct support. Be strict; also flag any place where the SOURCES digest drifted from the original notes.

ORIGINAL NOTE FILES TO READ:
- ${NOTE_FILES[0]}
- ${NOTE_FILES[1]}
- ${NOTE_FILES[2]}

AGENT OUTPUTS TO CHECK:
A1_CONSENSUS (Math): ${JSON.stringify(a1_consensus)}
A2 (Methods): ${JSON.stringify(a2_methods)}
A3 (Evidence): ${JSON.stringify(a3_evidence)}
A4 (Mechanism): ${JSON.stringify(a4_mechanism)}
A6 (Gaps): ${JSON.stringify(a6_gaps)}

For each agent: list grounded_claims (clear note support); hallucination_flags (claims exceeding/contradicting the notes, incl. digest drift — give the issue); coverage_gaps (important note content no agent covered).`,
  { label: 'A-G:Grounding', phase: 'Grounding Check', model: 'sonnet', schema: GROUNDING_SCHEMA })

// ─── Phase 4: BTL Tournament ───────────────────────────────────────────────────
phase('BTL Tournament')

const a_btl = await agent(`You are Agent BTL (Bradley-Terry-Luce Tournament Judge). Identify inter-source contradictions/tensions and resolve each by pairwise comparison (better-grounded, more precise, internally consistent wins). Use the grounding report to penalize ungrounded claims.

A1_CONSENSUS: ${JSON.stringify(a1_consensus)}
A2 (Methods): ${JSON.stringify(a2_methods)}
A3 (Evidence): ${JSON.stringify(a3_evidence)}
A4 (Mechanism): ${JSON.stringify(a4_mechanism)}
A6 (Gaps): ${JSON.stringify(a6_gaps)}
GROUNDING: ${JSON.stringify(a_grounding)}

Resolve at least these tensions where present: Stuart-Landau vs Jansen-Rit/Wong-Wang for E/I inference; Abeta-only vs dual-hit Abeta+Tau; mean-field validity scope for E/I inference; AEC vs phase-based FC sensitivity; how cleanly aging is separated from AD.
Produce resolved_consensus (definitive stances for the synthesis) and synthesis_instructions (explicit directives). Be decisive.`,
  { label: 'A-BTL:Tournament', phase: 'BTL Tournament', model: 'opus', schema: BTL_SCHEMA })

// ─── Phase 5: Consensus Adversarial Critique ───────────────────────────────────
phase('Consensus Critique')

const [r1, r2, r3] = await parallel([

  () => agent(`You are Reflector 1 (Methodological Rigor Lens). Adversarially critique a review built on this corpus. Do not hedge.

${SOURCE_MAP}
A1_CONSENSUS: ${JSON.stringify(a1_consensus)}
A2 (Methods): ${JSON.stringify(a2_methods)}
BTL: ${JSON.stringify(a_btl)}

Angle — modeling rigor & identifiability:
1. Mean-field validity (Deschle 2021): does inferring E/I outside the critical band undermine the central claims?
2. Model-inversion identifiability: are G, E-E, E-I, I-E jointly identifiable from FC alone (Zimmermann 2018)? Degeneracy risk?
3. Homogeneity & fixed-healthy-SC assumptions (Stefanovski 2019) — what do they bias?
4. The tau_i absolute-vs-relative inhibition artifact.
Fill aging_vs_ad_differentiation, validity_and_validation_assessment, reviewer_rejection_reasons.`,
    { label: 'R1:Rigor', phase: 'Consensus Critique', model: 'opus', schema: CRITIQUE_SCHEMA }),

  () => agent(`You are Reflector 2 (Clinical & Empirical Validity Lens). Adversarially critique. Do not hedge.

${SOURCE_MAP}
A3 (Evidence): ${JSON.stringify(a3_evidence)}
A4 (Mechanism): ${JSON.stringify(a4_mechanism)}
BTL: ${JSON.stringify(a_btl)}

Angle — empirical validity & translation:
1. Small/heterogeneous cohorts (N=33; N=124; 18+18; 19) — what can/can't be concluded?
2. Validation gaps: no concurrent real EEG to validate virtual EEG (Stefanovski 2019); BOLD neurovascular confound in AD (Zimmermann 2018); single-channel (Yokoyama 2023).
3. Is virtual Memantine normalization clinically meaningful or in-silico proof-of-concept only?
4. Does theta-AECc generalize as a stratification biomarker?
Fill aging_vs_ad_differentiation, validity_and_validation_assessment, reviewer_rejection_reasons.`,
    { label: 'R2:Clinical', phase: 'Consensus Critique', model: 'opus', schema: CRITIQUE_SCHEMA }),

  () => agent(`You are Reflector 3 (Aging-vs-AD & Reproducibility Lens). Adversarially critique. Do not hedge.

${SOURCE_MAP}
A6 (Gaps): ${JSON.stringify(a6_gaps)}
A3 (Evidence): ${JSON.stringify(a3_evidence)}
BTL: ${JSON.stringify(a_btl)}

Angle — does the corpus actually deliver an AGING-vs-AD E/I account, and is it reproducible:
1. Is "normal aging" modeled at all, or only HC controls? Is the aging<->AD continuum (SCD->aMCI->AD) mechanistically resolved?
2. Reproducibility: code/data availability, parameter-space search reproducibility, generalization across cohorts/scanners.
3. Circular-validation or confirmation-bias risks in fitting models to the same modality used to define pathology.
Fill aging_vs_ad_differentiation, validity_and_validation_assessment, reviewer_rejection_reasons.`,
    { label: 'R3:AgingAD', phase: 'Consensus Critique', model: 'sonnet', schema: CRITIQUE_SCHEMA }),
])

const reflector_consensus = await agent(`You are the Reflector Consensus Merger. A weakness is consensus only if >=2 of 3 Reflectors identify it. Single-reflector findings are flagged uncertain.

R1 (Rigor): ${JSON.stringify(r1)}
R2 (Clinical): ${JSON.stringify(r2)}
R3 (Aging-vs-AD): ${JSON.stringify(r3)}

1. consensus_weaknesses (>=2/3) with severity fatal/major/minor and source_reflectors.
2. single_reflector_findings (uncertain).
3. overall_verdict_recommendation for a review built on this corpus.
Do not dilute fatal weaknesses.`,
  { label: 'R-Consensus', phase: 'Consensus Critique', model: 'sonnet', schema: REFLECTOR_CONSENSUS_SCHEMA })

// ─── Phase 6: Synthesis with Self-Healing Loop ─────────────────────────────────
phase('Synthesis')

const SYN_PROMPT = `You are Agent 5 (Synthesis). Write a comprehensive ENGLISH literature-review paper draft, grounded ONLY in the agent outputs and SOURCES, with in-text citations in APA author-year style "(Author, Year)" using ONLY the SOURCE_MAP papers. Distinguish normal aging from AD throughout. Be scholarly, critical, and specific (include the key numbers: tau_i 14->50 ms, ADNI-3 N=33, MAS N=124, theta 4-8 Hz, SCD r=0.697 / MCI r=0.587, lambda 0.70-0.85, etc.).

${SOURCE_MAP}

INPUTS:
A1_CONSENSUS (Math): ${JSON.stringify(a1_consensus)}
A2 (Methods): ${JSON.stringify(a2_methods)}
A3 (Evidence): ${JSON.stringify(a3_evidence)}
A4 (Mechanism): ${JSON.stringify(a4_mechanism)}
A6 (Gaps): ${JSON.stringify(a6_gaps)}
GROUNDING: ${JSON.stringify(a_grounding)}
BTL RESOLUTION: ${JSON.stringify(a_btl)}
REFLECTOR CONSENSUS: ${JSON.stringify(reflector_consensus)}

Produce sections in this order, each with full multi-paragraph prose and in-text citations:
1. Introduction (E/I balance as the translational hub; why infer it from EEG/MEG; aging vs AD framing)
2. Mathematical Foundations of Neural Mass Models (exact vs heuristic; adiabatic landscape; validity boundaries)
3. Multiscale Virtual-Brain Modeling and E/I Inference Methods (BNM anatomy; node dynamics choice; data assimilation; hybrid; forward vs inverse)
4. Empirical Evidence Across Normal Aging and Alzheimer's Disease (Stam, Yokoyama, Stefanovski, Zimmermann with designs/numbers/strength)
5. Molecular-to-Network Mechanisms and Translational Implications (disinhibition, hub propagation, dual-hit, in-silico pharmacology)
6. Limitations and Validity Boundaries (MANDATORY: incorporate EVERY consensus_weakness from Reflector Consensus; honor BTL synthesis_instructions)
7. Future Directions
8. Conclusion

MANDATORY: all_btl_instructions_addressed true ONLY if every BTL synthesis_instruction is incorporated; all_consensus_weaknesses_addressed true ONLY if every consensus_weakness appears in section 6; missed_items lists anything you could not address. citations_used must list every Author-Year you cite.`

let synthesis = await agent(SYN_PROMPT, { label: 'A5:Synthesis', phase: 'Synthesis', model: 'opus', schema: REVIEW_SYNTHESIS_SCHEMA })

if (synthesis && (!synthesis.all_btl_instructions_addressed || !synthesis.all_consensus_weaknesses_addressed)) {
  log(`Self-healing: synthesis missed items — ${(synthesis.missed_items || []).join(' | ')}. Retrying.`)
  synthesis = await agent(`You are Agent 5 (Synthesis, Self-Healing Retry). Your previous draft missed items. Revise to incorporate EVERY missed item, BTL synthesis_instruction, and consensus_weakness. Return the COMPLETE report (all 8 sections in full).

MISSED ITEMS: ${JSON.stringify(synthesis.missed_items)}
BTL SYNTHESIS INSTRUCTIONS: ${JSON.stringify(a_btl ? a_btl.synthesis_instructions : [])}
CONSENSUS WEAKNESSES: ${JSON.stringify(reflector_consensus ? reflector_consensus.consensus_weaknesses : [])}

PREVIOUS DRAFT: ${JSON.stringify(synthesis)}`,
    { label: 'A5:Synthesis-Retry', phase: 'Synthesis', model: 'opus', schema: REVIEW_SYNTHESIS_SCHEMA })
}

return {
  a1_trajectory_1: a1_t1, a1_trajectory_2: a1_t2, a1_trajectory_3: a1_t3,
  a1_consensus,
  methods: a2_methods,
  evidence: a3_evidence,
  mechanism: a4_mechanism,
  gaps: a6_gaps,
  grounding_report: a_grounding,
  btl_tournament: a_btl,
  reflector_r1: r1, reflector_r2: r2, reflector_r3: r3,
  reflector_consensus,
  review_synthesis: synthesis,
}
