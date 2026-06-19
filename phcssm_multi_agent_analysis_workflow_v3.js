// Multi-Agent Research Pipeline v3.0 — PHCSSM Paper Analysis Workflow
// Paper: "Parallelized Hierarchical Connectome: A Spatiotemporal Recurrent Framework
//         for Spiking State-Space Models" (Po-Han Chiang, NYCU, arXiv 2604.01295, 2026)
// Skill: https://github.com/ckt520728/2026-Hermes/blob/main/multi_agent_research_skill_v2.5.md
//
// Robin MAS Optimizations (Ghareeb et al., 2026, Nature — 5 core concepts applied):
//   [R1] Structured JSON Schemas     — prevent error cascading (BixBench: 15.3% on multi-step vs 47.9% single-step)
//   [R2] A1 Consensus Trajectories   — 3x mathematical analysis; 50%+ intersection = consensus (Finch 8x pattern)
//   [R3] Grounding Check Gate        — every claim must cite PAPER text; no claim from model weights (0% hallucination rule)
//   [R4] BTL Tournament Gate         — pairwise contradiction resolution replaces single Monitor (BTL > absolute scoring)
//   [R5] Consensus Adversarial Critique — 3x Reflector → 50%+ intersection; 1-of-3 finding = uncertain

export const meta = {
  name: 'phcssm-paper-analysis-v3',
  description: 'PHCSSM multi-agent analysis v3.0 — Robin MAS optimized',
  phases: [
    { title: 'Parallel Analysis',   detail: 'A1(x3 consensus), A2, A3, A4, A6 — all structured JSON output [R1][R2]' },
    { title: 'A1 Consensus Merge',  detail: '3x mathematical trajectories merged by 50%+ intersection rule [R2]' },
    { title: 'Grounding Check',     detail: 'All claims verified against PAPER text; hallucinations flagged [R3]' },
    { title: 'BTL Tournament',      detail: 'Pairwise contradiction ranking resolves inter-agent disagreements [R4]' },
    { title: 'Consensus Critique',  detail: '3x adversarial Reflectors → 50%+ consensus weaknesses only [R5]' },
    { title: 'Synthesis',           detail: 'Final report with self-healing gap-fill loop on BTL + consensus gaps' },
  ],
}

// ─── Paper Content ─────────────────────────────────────────────────────────────
const PAPER = `
PAPER: Parallelized Hierarchical Connectome: A Spatiotemporal Recurrent Framework for Spiking State-Space Models
arXiv: 2604.01295, April 2026. Author: Po-Han Chiang (NYCU, Taiwan).

ABSTRACT / CORE INNOVATION:
PHCSSM unifies recurrent spiking neural network dynamics with diagonal SSM parallelism.
It resolves the trade-off: "learnable lateral connections and temporal parallel scan efficiency
have been mutually exclusive."

ARCHITECTURE:
- Neuron Layer (NL): Adaptive Leaky Integrate-and-Fire (ALIF) neurons; strictly diagonal
  recurrence. Encodes membrane dynamics.
- Synapse Layer (SL): Inter-neuronal communication through biologically constrained weights.
- Multi-Transmission Loop: Enables intra-timestep spatial recurrence (depth-M) while
  preserving O(log T) temporal parallelism.
- PHC maps the diagonal SSM core to a shared Neuron Layer; inter-neuronal communication
  to a shared Synapse Layer; neurons partitioned into hierarchical regions governed by
  connectome topology.

FIVE BIOLOGICAL CONSTRAINTS:
1. ALIF Dynamics: Adaptive thresholds provide intrinsic temporal memory.
2. Short-Term Plasticity (STP): Tsodyks-Markram formalism converts static weights into
   time-varying effective weights.
3. Dale's Law: Enforces excitatory/inhibitory neurotransmitter consistency.
4. Hierarchical Connectome Topology: Organizes neurons into regions with structured
   regional projections.
5. Reward-Modulated STDP (R-STDP): Online Hebbian learning gated by batch-level reward.

TECHNICAL DETAILS:
- All biological dynamics reformulated as affine recurrences solvable via log-domain
  parallel prefix sums.
- Eliminates O(T) BPTT bottleneck while preserving binary spike representations.
- Parameter complexity: Theta(D^2) vs Theta(D^2 * L) for L-layer stacked architectures.
- Training: 27-129 seconds per 1,000 steps; 10-48 MB GPU memory.

EXPERIMENTAL RESULTS (UEA Multivariate Time-Series Archive — physiological benchmarks):
- SCP2: 59.3% (highest SSM accuracy; LinOSS-IMEX was 58.9%)
- MotorImagery: 53.7% (outperforms Mamba by +6pp)
- EigenWorms: 83.9% (ultra-long sequences, only 2,701 parameters)
- Parameter count: 1,748-9,485 vs 67K-401K for comparable SSMs (>10x smaller)

ABLATION RESULTS (removing each constraint individually):
- Removing ALIF: -5.23pp accuracy
- Removing R-STDP: -4.37pp accuracy
- All constraints contribute non-redundantly.

COMPARISON WITH PRIOR WORK:
- PD-SSM: One-to-one permutation routing, no learnable lateral weights.
- xLSTM (sLSTM): Lateral connections but not parallelizable;
  mLSTM: parallel but no lateral connections.
- GraphS4mer / GraphMamba: Spatial interaction confined to post-hoc aggregation
  outside recurrence.
- PHCSSM: First to achieve weighted spatiotemporal recurrence inside SSM while
  preserving O(log L) efficiency.

SIGNIFICANCE:
Biological constraints act as stabilizing inductive biases, not performance bottlenecks.
Model is directly unrollable as sequential spiking network at inference
(neuromorphic hardware compatible).
`

// ─── [R1] JSON Schemas — Structured Output (prevents error cascading) ──────────
// Robin lesson: BixBench multi-step pipeline fails at 15.3% when output format is ambiguous.
// All agents return schema-validated JSON so downstream agents parse data, not prose.

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
          paper_evidence: { type: 'string', description: 'Direct quote or specific section from PAPER supporting this claim' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['claim', 'paper_evidence', 'confidence'],
      },
    },
    strengths: { type: 'array', items: { type: 'string' } },
    weaknesses: { type: 'array', items: { type: 'string' } },
    unverified_claims: {
      type: 'array',
      items: { type: 'string' },
      description: 'Claims in the paper that are asserted but lack sufficient evidence or derivation',
    },
    overall_confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
  },
  required: ['agent_id', 'key_findings', 'strengths', 'weaknesses', 'unverified_claims', 'overall_confidence'],
}

const A1_CONSENSUS_SCHEMA = {
  type: 'object',
  properties: {
    consensus_findings: {
      type: 'array',
      items: { type: 'string' },
      description: 'Mathematical claims appearing in ≥2 of 3 trajectories',
    },
    trajectory_divergences: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          topic: { type: 'string' },
          t1_position: { type: 'string' },
          t2_position: { type: 'string' },
          t3_position: { type: 'string' },
        },
        required: ['topic'],
      },
      description: 'Mathematical claims where trajectories disagree — high uncertainty signals',
    },
    consensus_unverified_claims: {
      type: 'array',
      items: { type: 'string' },
      description: 'Unverified paper claims flagged by ≥2 trajectories',
    },
    merged_confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
  },
  required: ['consensus_findings', 'trajectory_divergences', 'consensus_unverified_claims', 'merged_confidence'],
}

const GROUNDING_SCHEMA = {
  type: 'object',
  properties: {
    grounded_claims: {
      type: 'array',
      items: { type: 'string' },
      description: 'Agent claims with clear PAPER text support',
    },
    hallucination_flags: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          agent: { type: 'string' },
          claim: { type: 'string' },
          issue: { type: 'string', description: 'Why this claim exceeds or contradicts PAPER text' },
        },
        required: ['agent', 'claim', 'issue'],
      },
    },
    coverage_gaps: {
      type: 'array',
      items: { type: 'string' },
      description: 'Important paper aspects no agent covered',
    },
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
          agent_a: { type: 'string' },
          claim_a: { type: 'string' },
          agent_b: { type: 'string' },
          claim_b: { type: 'string' },
          winner: { type: 'string', enum: ['agent_a', 'agent_b', 'tie'] },
          rationale: { type: 'string', description: 'Which paper evidence supports the winner' },
        },
        required: ['topic', 'agent_a', 'claim_a', 'agent_b', 'claim_b', 'winner', 'rationale'],
      },
    },
    resolved_consensus: {
      type: 'array',
      items: { type: 'string' },
      description: 'Consensus positions after BTL resolution — definitive stances for Agent 5',
    },
    synthesis_instructions: {
      type: 'array',
      items: { type: 'string' },
      description: 'Explicit instructions for Agent 5 on how to handle each resolved contradiction',
    },
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
        properties: {
          weakness: { type: 'string' },
          severity: { type: 'string', enum: ['fatal', 'major', 'minor'] },
        },
        required: ['weakness', 'severity'],
      },
    },
    parameter_comparison_validity: {
      type: 'string',
      description: 'Is the 1,748-9,485 vs 67K-401K comparison fair? What architectural assumptions does it hide?',
    },
    benchmark_bias_assessment: {
      type: 'string',
      description: 'Is testing exclusively on physiological benchmarks cherry-picking for biological constraints?',
    },
    reviewer_rejection_reasons: {
      type: 'array',
      items: { type: 'string' },
      description: 'Specific reasons a NeurIPS/ICLR reviewer would reject this paper',
    },
  },
  required: ['critical_weaknesses', 'parameter_comparison_validity', 'benchmark_bias_assessment', 'reviewer_rejection_reasons'],
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
      description: 'Weaknesses found in ≥2 of 3 Reflectors — high-confidence adversarial findings',
    },
    single_reflector_findings: {
      type: 'array',
      items: { type: 'string' },
      description: 'Findings from only 1 Reflector — uncertain; flag but do not assert as consensus',
    },
    overall_verdict_recommendation: {
      type: 'string',
      description: 'Accept / Major Revision / Reject based on consensus weaknesses',
    },
  },
  required: ['consensus_weaknesses', 'single_reflector_findings', 'overall_verdict_recommendation'],
}

const SYNTHESIS_SCHEMA = {
  type: 'object',
  properties: {
    executive_summary: { type: 'string' },
    core_technical_contribution: { type: 'string' },
    experimental_evidence_assessment: { type: 'string' },
    novelty_positioning: { type: 'string' },
    strengths: { type: 'array', items: { type: 'string' } },
    weaknesses: { type: 'array', items: { type: 'string' } },
    practical_impact_and_future: { type: 'string' },
    overall_verdict: { type: 'string', description: 'Accept/Major Revision/Reject framing with score /10' },
    all_btl_instructions_addressed: {
      type: 'boolean',
      description: 'True only if every BTL synthesis instruction was incorporated into this report',
    },
    all_consensus_weaknesses_addressed: {
      type: 'boolean',
      description: 'True only if every consensus adversarial weakness appears in section 6 Weaknesses',
    },
    missed_items: {
      type: 'array',
      items: { type: 'string' },
      description: 'Any BTL instruction or consensus weakness you could NOT address, and why',
    },
  },
  required: [
    'executive_summary', 'core_technical_contribution', 'experimental_evidence_assessment',
    'novelty_positioning', 'strengths', 'weaknesses', 'practical_impact_and_future',
    'overall_verdict', 'all_btl_instructions_addressed', 'all_consensus_weaknesses_addressed', 'missed_items',
  ],
}

// ─── Phase 1: Parallel Analysis ────────────────────────────────────────────────
// [R1] All agents return ANALYSIS_SCHEMA — structured JSON prevents error cascading downstream
// [R2] A1 runs 3 independent trajectories with different analytical angles
phase('Parallel Analysis')

const [a1_t1, a1_t2, a1_t3, a2_litSearch, a3_data, a4_applications, a6_lit] = await parallel([

  // Agent 1 — Trajectory 1: Formal derivation completeness
  () => agent(`You are Agent 1 (Compute, Trajectory 1 — Formal Completeness). Analyze PHCSSM mathematically.
IMPORTANT: Every claim MUST cite a specific section, equation, or direct quote from the PAPER. Do not rely on general knowledge.

${PAPER}

Focus — formal derivation completeness:
1. Are ALIF, STP, and R-STDP dynamics reformulated as EXACT affine recurrences, or are approximations made?
   Which specific biological terms, if any, are dropped to achieve affine form?
2. How does the Multi-Transmission Loop achieve depth-M spatial recurrence while preserving O(log T)?
   Explain the decoupling mechanism precisely. What are the constant factors hidden in O notation?
3. Why does PHC reduce parameter complexity from Theta(D^2*L) to Theta(D^2)?
   Is this a genuine saving or an artifact of the specific architectural choices?
4. Is the log-domain parallel prefix sum formulation complete? Are there non-affine residual terms ignored?
5. Assess mathematical rigor. Flag any claim that is asserted without derivation.

For every key_finding, populate paper_evidence with a direct quote or equation reference.`,
    { label: 'A1:Compute-T1', phase: 'Parallel Analysis', model: 'opus', schema: ANALYSIS_SCHEMA }),

  // Agent 1 — Trajectory 2: Failure mode and approximation angle
  () => agent(`You are Agent 1 (Compute, Trajectory 2 — Failure Mode Analysis). Analyze PHCSSM mathematically.
IMPORTANT: Every claim MUST cite a specific section, equation, or direct quote from the PAPER. Do not rely on general knowledge.

${PAPER}

Focus — where the mathematics might break:
1. ALIF adaptive thresholds: does the affine reformulation hold under all threshold dynamics, or only linearized versions?
2. R-STDP is described as "online Hebbian learning gated by batch-level reward" — does online learning inside a batched parallel scan create a mathematical contradiction? Is this tension resolved in the paper?
3. STP (Tsodyks-Markram) produces time-varying effective weights — how exactly does this enter the affine recurrence? Is there an approximation?
4. Gradient flow: does the log-domain parallel scan alter gradient magnitudes relative to standard BPTT?
5. Do the ablation results (single constraint removal) prove non-redundancy, or could pairwise interactions confound the result?

For every key_finding, populate paper_evidence with a direct quote or equation reference.`,
    { label: 'A1:Compute-T2', phase: 'Parallel Analysis', model: 'opus', schema: ANALYSIS_SCHEMA }),

  // Agent 1 — Trajectory 3: PHC topology and convergence
  () => agent(`You are Agent 1 (Compute, Trajectory 3 — Topology & Convergence). Analyze PHCSSM mathematically.
IMPORTANT: Every claim MUST cite a specific section, equation, or direct quote from the PAPER. Do not rely on general knowledge.

${PAPER}

Focus — connectome topology and learning convergence:
1. How tightly is the PHC hierarchical connectome topology connected to the diagonal SSM core? Is this connection a mathematical theorem or an architectural design choice?
2. R-STDP convergence: does the paper provide any convergence guarantees for the Hebbian online learning rule? Under what conditions might it diverge?
3. Dale's Law constraint: how is excitatory/inhibitory consistency enforced during gradient descent without violating the affine recurrence property?
4. Is the Theta(D^2) parameter count consistent across all five biological constraints, or do some constraints introduce additional parameters?
5. What are the theoretical limitations of the log-domain parallel scan formulation for very long sequences (beyond benchmark lengths)?

For every key_finding, populate paper_evidence with a direct quote or equation reference.`,
    { label: 'A1:Compute-T3', phase: 'Parallel Analysis', model: 'opus', schema: ANALYSIS_SCHEMA }),

  // Agent 2 (Literature & Positioning)
  () => agent(`You are Agent 2 (Literature & Positioning). Analyze PHCSSM's positioning in the literature.
IMPORTANT: Every claim MUST cite a specific section or direct quote from the PAPER. Do not rely on general knowledge.

${PAPER}

Analyze:
1. Compare to SSM family (S4, Mamba, LinOSS-IMEX, GraphS4mer, GraphMamba) — where does the paper situate each?
2. Compare to SNN training approaches (BPTT, surrogate gradient, STBP) as described in the paper.
3. Relation to biological models (Tsodyks-Markram STP, ALIF, Dale's Law) — does the paper accurately represent these?
4. Is the "first model to achieve weighted spatiotemporal recurrence inside SSM while preserving O(log L)" claim well-supported? What prior work does the paper exclude or underrepresent?
5. Evaluate the novelty claim: is it incremental or a genuine architectural breakthrough?

For every key_finding, populate paper_evidence with a direct quote or equation reference.`,
    { label: 'A2:LitSearch', phase: 'Parallel Analysis', model: 'sonnet', schema: ANALYSIS_SCHEMA }),

  // Agent 3 (Data Analyst)
  () => agent(`You are Agent 3 (Data Analyst). Critically analyze the experimental results of PHCSSM.
IMPORTANT: Every claim MUST cite a specific section or direct quote from the PAPER. Do not rely on general knowledge.

${PAPER}

Analyze:
1. Are the 6 UEA physiological benchmarks appropriate for evaluating a general SSM? What benchmark categories are notably absent?
2. SCP2: 59.3% vs 58.9% (LinOSS-IMEX) — is a 0.4pp margin meaningful without statistical significance testing?
3. Parameter efficiency: 1,748-9,485 vs 67K-401K — is this architecturally fair? Do the compared models solve the same task at the same sequence length?
4. Ablation validity: is removing one constraint at a time sufficient to prove all five are non-redundant? What about pairwise interactions?
5. What missing experiments would most strengthen or weaken the paper's claims?
6. Training efficiency (27-129s/1000 steps, 10-48 MB) — is the GPU hardware and batch size specified? Is this comparable to baselines?

For every key_finding, populate paper_evidence with a direct quote or equation reference.`,
    { label: 'A3:Data', phase: 'Parallel Analysis', model: 'sonnet', schema: ANALYSIS_SCHEMA }),

  // Agent 4 (Applications & Impact)
  () => agent(`You are Agent 4 (Applications & Impact). Analyze the practical implications of PHCSSM.
IMPORTANT: Every claim MUST cite a specific section or direct quote from the PAPER. Do not rely on general knowledge.

${PAPER}

Analyze:
1. Neuromorphic hardware compatibility: what exactly does "directly unrollable as sequential spiking network" imply for Intel Loihi, IBM TrueNorth, SpiNNaker deployment?
2. Application domains: EEG, BCI, neural decoding, edge computing — which does the paper explicitly address vs which are speculative?
3. Scalability: does depth-M Multi-Transmission Loop create inference latency at scale? What is the complexity at inference?
4. Biological plausibility as a scientific tool vs engineering artifact — does the paper make this distinction?
5. Conditions where biological constraints could hurt rather than help — does the paper address this or is it a gap?

For every key_finding, populate paper_evidence with a direct quote or equation reference.`,
    { label: 'A4:Applications', phase: 'Parallel Analysis', model: 'opus', schema: ANALYSIS_SCHEMA }),

  // Agent 6 (Literature Scan — concise)
  () => agent(`You are Agent 6 (Literature Scan). Rapid literature context for PHCSSM. Be concise.
IMPORTANT: Every claim MUST cite a specific section or direct quote from the PAPER. Do not rely on general knowledge.

${PAPER}

Identify:
1. 3-5 most directly competing papers as cited by PHCSSM and their stated limitations.
2. 2-3 biological neuroscience papers whose models are incorporated — does the paper faithfully implement them?
3. Significant gaps in the related work section — what competing work is not cited?
4. The broader research trend this paper fits into.

Focus on gaps and omissions. For every key_finding, populate paper_evidence with a direct quote.`,
    { label: 'A6:Lit', phase: 'Parallel Analysis', model: 'haiku', schema: ANALYSIS_SCHEMA }),
])

// ─── Phase 2: A1 Consensus Merge ───────────────────────────────────────────────
// [R2] Robin's Finch 8x trajectory pattern: take 50%+ intersection as consensus
// A1 is the highest-risk agent for mathematical hallucination — 3x trajectories reduce stochasticity
phase('A1 Consensus Merge')

const a1_consensus = await agent(`You are the A1 Consensus Merger.
Three independent mathematical analysis trajectories have been run on the PHCSSM paper.
Apply the Robin MAS consensus rule: a finding is "consensus" if ≥2 of 3 trajectories make the same core claim.

TRAJECTORY 1 (Formal Completeness): ${JSON.stringify(a1_t1)}
TRAJECTORY 2 (Failure Mode Analysis): ${JSON.stringify(a1_t2)}
TRAJECTORY 3 (Topology & Convergence): ${JSON.stringify(a1_t3)}

Instructions:
1. For key_findings: include only claims where ≥2 trajectories agree on the core assertion (wording may differ).
2. For trajectory_divergences: list topics where trajectories reach different conclusions — these are high-uncertainty signals for Agent 5.
3. For consensus_unverified_claims: include paper claims flagged as underspecified or unproven by ≥2 trajectories.
4. Set merged_confidence to 'high' only if all 3 trajectories agree; 'medium' if 2/3 agree; 'low' if significant divergences exist.

Do NOT invent consensus where trajectories diverge. Divergence is valuable signal.`,
  { label: 'A1:Consensus', phase: 'A1 Consensus Merge', model: 'sonnet', schema: A1_CONSENSUS_SCHEMA })

// ─── Phase 3: Grounding Check Gate ─────────────────────────────────────────────
// [R3] Robin anti-hallucination principle: "絕不能讓 LLM 直接憑內部權重默寫醫療文獻"
// Applied: every agent claim must be traceable to PAPER text, not model internal knowledge.
// Robin ablation showed: removing grounding agents → 44.5% hallucination rate.
phase('Grounding Check')

const a_grounding = await agent(`You are Agent G (Grounding Checker).
Robin MAS showed removing document-grounding agents causes 44.5% hallucination rate.
Your task: verify every major claim from all parallel agents against the exact PAPER text.
A claim is "grounded" ONLY if the PAPER text contains direct evidence. Be strict.

PAPER: ${PAPER}

A1_CONSENSUS (Mathematical): ${JSON.stringify(a1_consensus)}
A2 (Literature): ${JSON.stringify(a2_litSearch)}
A3 (Data): ${JSON.stringify(a3_data)}
A4 (Applications): ${JSON.stringify(a4_applications)}
A6 (Lit Scan): ${JSON.stringify(a6_lit)}

For each agent, check:
1. Claims that go beyond what PAPER states — flag as hallucination_flags with specific issue
2. Claims well-supported by direct PAPER text — add to grounded_claims
3. Important paper aspects no agent covered — add to coverage_gaps

Flag anything an agent stated as fact that the PAPER does not explicitly support.`,
  { label: 'A-G:Grounding', phase: 'Grounding Check', model: 'sonnet', schema: GROUNDING_SCHEMA })

// ─── Phase 4: BTL Tournament Gate ──────────────────────────────────────────────
// [R4] Robin BTL principle: pairwise comparison > absolute scoring for contradiction resolution
// "使用 Bradley-Terry-Luce 統計模型計算出全局排名" — applied to inter-agent contradictions
// Replaces the single Monitor Agent (v2.5) with tournament-based resolution
phase('BTL Tournament')

const a_btl = await agent(`You are Agent BTL (Bradley-Terry-Luce Tournament Judge).
Robin MAS showed pairwise comparison outperforms absolute scoring for evaluating competing claims.
Your task: identify all inter-agent contradictions and resolve each via pairwise tournament.

A1_CONSENSUS (Mathematical): ${JSON.stringify(a1_consensus)}
A2 (Literature): ${JSON.stringify(a2_litSearch)}
A3 (Data): ${JSON.stringify(a3_data)}
A4 (Applications): ${JSON.stringify(a4_applications)}
A6 (Lit Scan): ${JSON.stringify(a6_lit)}
GROUNDING REPORT: ${JSON.stringify(a_grounding)}

BTL Tournament Rules:
1. For each contradiction between two agents (agent_a vs agent_b), state the specific competing claims.
2. Award win to whichever claim is: (a) better grounded in PAPER text, (b) internally consistent, (c) more precise.
3. Tie ONLY when paper support is genuinely equal.
4. Use grounding_report hallucination_flags to penalize ungrounded claims.
5. Produce resolved_consensus: definitive positions after all pairwise resolutions.
6. Produce synthesis_instructions: explicit directives for Agent 5 on how to handle each resolved point.

Be decisive. Contradictions must be resolved, not deferred to Agent 5.`,
  { label: 'A-BTL:Tournament', phase: 'BTL Tournament', model: 'opus', schema: BTL_SCHEMA })

// ─── Phase 5: Consensus Adversarial Critique ───────────────────────────────────
// [R5] Robin consensus-driven analysis: 3x parallel Reflectors, each with a different critical lens
// Only weaknesses found in ≥2/3 trajectories enter the consensus — prevents single-agent blind spots
phase('Consensus Critique')

const [r1, r2, r3] = await parallel([

  // Reflector 1: Mathematical rigor lens
  () => agent(`You are Reflector 1 (Mathematical Rigor Lens). Your job: adversarially critique PHCSSM.
Find what all previous agents missed or underweighted. Be adversarial. Do not hedge.

PAPER: ${PAPER}
A1_CONSENSUS: ${JSON.stringify(a1_consensus)}
BTL RESOLUTION: ${JSON.stringify(a_btl)}

Your specific angle — mathematical rigor:
1. Is the parameter comparison (1,748-9,485 vs 67K-401K) hiding unfair architectural assumptions?
   Are the compared models solving the same problem at the same scale?
2. What is the most important mathematical weakness all agents underweighted?
3. Does the Multi-Transmission Loop actually preserve O(log T) or does depth-M introduce a hidden O(M) factor?
4. What would an ICLR mathematical/theory reviewer reject this paper for?
5. Reproducibility: are the mathematical derivations complete enough to reimplement without the original code?`,
    { label: 'R1:Math', phase: 'Consensus Critique', model: 'opus', schema: CRITIQUE_SCHEMA }),

  // Reflector 2: Empirical validity lens
  () => agent(`You are Reflector 2 (Empirical Validity Lens). Your job: adversarially critique PHCSSM.
Find what all previous agents missed or underweighted. Be adversarial. Do not hedge.

PAPER: ${PAPER}
A3_DATA: ${JSON.stringify(a3_data)}
BTL RESOLUTION: ${JSON.stringify(a_btl)}

Your specific angle — experimental validity:
1. Is testing exclusively on physiological EEG/EMG benchmarks cherry-picking for biological constraints?
   What would happen on non-physiological benchmarks (e.g., speech, finance, climate)?
2. Is the 0.4pp SCP2 margin meaningful without reported confidence intervals or significance tests?
3. Are the ablation results interpretable given only single-constraint removal (no combinatorial ablations)?
4. What missing experiments would most severely weaken the paper's central claims?
5. What would a NeurIPS empirical reviewer reject this paper for?`,
    { label: 'R2:Empirical', phase: 'Consensus Critique', model: 'opus', schema: CRITIQUE_SCHEMA }),

  // Reflector 3: Novelty and reproducibility lens
  () => agent(`You are Reflector 3 (Novelty & Reproducibility Lens). Your job: adversarially critique PHCSSM.
Find what all previous agents missed or underweighted. Be adversarial. Do not hedge.

PAPER: ${PAPER}
A2_LIT: ${JSON.stringify(a2_litSearch)}
A6_LIT: ${JSON.stringify(a6_lit)}
BTL RESOLUTION: ${JSON.stringify(a_btl)}

Your specific angle — novelty and reproducibility:
1. Is the "first to achieve weighted spatiotemporal recurrence inside SSM while preserving O(log L)" claim defensible?
   What prior work in parallel RNNs or biological SSMs might challenge this?
2. Code availability: is the paper's implementation publicly available? Without code, is the model reproducible?
3. Hyperparameter sensitivity: the 5 biological constraints each likely introduce tunable parameters — is sensitivity analysis provided?
4. Is the PHC topology (hierarchical connectome structure) based on real connectome data or a designed approximation?
5. What would an ICLR novelty/related-work reviewer reject this paper for?`,
    { label: 'R3:Novelty', phase: 'Consensus Critique', model: 'sonnet', schema: CRITIQUE_SCHEMA }),
])

// Merge: apply 50%+ intersection rule across 3 Reflectors
const reflector_consensus = await agent(`You are the Reflector Consensus Merger.
Apply Robin's 50%+ consensus rule: a weakness is "consensus" only if ≥2 of 3 Reflectors identify it.
Single-reflector findings are flagged as uncertain.

REFLECTOR 1 (Mathematical Rigor): ${JSON.stringify(r1)}
REFLECTOR 2 (Empirical Validity): ${JSON.stringify(r2)}
REFLECTOR 3 (Novelty & Reproducibility): ${JSON.stringify(r3)}

Instructions:
1. Identify weaknesses that appear in ≥2 of 3 Reflectors — these are high-confidence adversarial findings.
2. Assign severity: 'fatal' = would cause rejection; 'major' = major revision required; 'minor' = addressable.
3. Single-reflector findings: include in single_reflector_findings as uncertain but noteworthy signals.
4. Produce overall_verdict_recommendation based on the weight of consensus_weaknesses.

Do not dilute fatal weaknesses. If ≥2 Reflectors call something fatal, report it as fatal.`,
  { label: 'R-Consensus', phase: 'Consensus Critique', model: 'sonnet', schema: REFLECTOR_CONSENSUS_SCHEMA })

// ─── Phase 6: Synthesis with Self-Healing Loop ─────────────────────────────────
// Robin lesson: Agent 5 must address ALL BTL synthesis_instructions and ALL consensus_weaknesses.
// Self-healing: if synthesis reports missed items (all_btl_instructions_addressed = false or
// all_consensus_weaknesses_addressed = false), run one retry with explicit gap list.
phase('Synthesis')

let a5_synthesis = await agent(`You are Agent 5 (Synthesis). Produce the final comprehensive analysis report.

PAPER: ${PAPER}
A1_CONSENSUS (Mathematical): ${JSON.stringify(a1_consensus)}
A2 (Literature & Positioning): ${JSON.stringify(a2_litSearch)}
A3 (Experimental Results): ${JSON.stringify(a3_data)}
A4 (Applications & Impact): ${JSON.stringify(a4_applications)}
A6 (Literature Scan): ${JSON.stringify(a6_lit)}
GROUNDING REPORT: ${JSON.stringify(a_grounding)}
BTL TOURNAMENT RESOLUTION: ${JSON.stringify(a_btl)}
REFLECTOR CONSENSUS: ${JSON.stringify(reflector_consensus)}

Produce a structured final report:
1. **Executive Summary** (3-4 sentences)
2. **Core Technical Contribution** (the parallelism-biology unification mechanism; use BTL resolved_consensus)
3. **Experimental Evidence Assessment** (what results prove and what they do not; use A3 + grounding_flags)
4. **Novelty & Positioning** (is the "first" claim justified? use BTL resolution + A2 + A6)
5. **Strengths** (top 3-4; must be grounded claims only)
6. **Weaknesses & Limitations** (MANDATORY: incorporate ALL consensus_weaknesses from Reflector Consensus; none may be omitted)
7. **Practical Impact & Future Directions** (neuromorphic, BCI, scientific modeling; use A4)
8. **Overall Verdict** (Accept / Major Revision / Reject framing; score /10)

MANDATORY FIELDS:
- all_btl_instructions_addressed: set true ONLY if every item in BTL synthesis_instructions is incorporated.
- all_consensus_weaknesses_addressed: set true ONLY if every consensus_weakness appears in section 6.
- missed_items: list anything you could NOT address and why (prefer empty list).`,
  { label: 'A5:Synthesis', phase: 'Synthesis', model: 'opus', schema: SYNTHESIS_SCHEMA })

// Self-healing loop: retry once if Agent 5 missed BTL instructions or consensus weaknesses
if (a5_synthesis && (!a5_synthesis.all_btl_instructions_addressed || !a5_synthesis.all_consensus_weaknesses_addressed)) {
  log(`Self-healing: synthesis missed items — ${a5_synthesis.missed_items.join(' | ')}. Running targeted retry.`)

  a5_synthesis = await agent(`You are Agent 5 (Synthesis, Self-Healing Retry).
Your previous synthesis was incomplete. The following items were NOT addressed:

MISSED ITEMS: ${JSON.stringify(a5_synthesis.missed_items)}

PREVIOUS SYNTHESIS (complete, to be revised):
${JSON.stringify(a5_synthesis)}

BTL SYNTHESIS INSTRUCTIONS (all must be addressed):
${JSON.stringify(a_btl ? a_btl.synthesis_instructions : [])}

CONSENSUS WEAKNESSES (all must appear in Weaknesses section):
${JSON.stringify(reflector_consensus ? reflector_consensus.consensus_weaknesses : [])}

Revise the synthesis to explicitly incorporate every missed item.
Return the complete updated report. Do not summarize — return all sections in full.`,
    { label: 'A5:Synthesis-Retry', phase: 'Synthesis', model: 'opus', schema: SYNTHESIS_SCHEMA })
}

// ─── Return All Outputs ────────────────────────────────────────────────────────
return {
  a1_trajectory_1:        a1_t1,
  a1_trajectory_2:        a1_t2,
  a1_trajectory_3:        a1_t3,
  a1_consensus,
  literature_positioning: a2_litSearch,
  experimental_analysis:  a3_data,
  applications_impact:    a4_applications,
  literature_scan:        a6_lit,
  grounding_report:       a_grounding,
  btl_tournament:         a_btl,
  reflector_r1:           r1,
  reflector_r2:           r2,
  reflector_r3:           r3,
  reflector_consensus,
  final_report:           a5_synthesis,
}
