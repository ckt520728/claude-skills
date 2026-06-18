// Multi-Agent Research Pipeline v2.5 — PHCSSM Paper Analysis Workflow
// Paper: "Parallelized Hierarchical Connectome: A Spatiotemporal Recurrent Framework
//         for Spiking State-Space Models" (Po-Han Chiang, NYCU, arXiv 2604.01295, 2026)
// Skill: https://github.com/ckt520728/2026-Hermes/blob/main/multi_agent_research_skill_v2.5.md
// Usage: Paste into Claude Code Workflow tool when ready to run.

export const meta = {
  name: 'phcssm-paper-analysis',
  description: 'Multi-agent research pipeline v2.5 analysis of the PHCSSM paper',
  phases: [
    { title: 'Parallel Analysis', detail: 'Agents 1,2,3,4,6 analyze the paper simultaneously' },
    { title: 'Monitor Gate',      detail: 'Agent 7 quality-checks all parallel outputs' },
    { title: 'Reflector',         detail: 'Agent 8 adversarially critiques' },
    { title: 'Synthesis',         detail: 'Agent 5 produces final integrated report' },
  ],
}

const PAPER = `
PAPER: Parallelized Hierarchical Connectome: A Spatiotemporal Recurrent Framework for Spiking State-Space Models
arXiv: 2604.01295, April 2026. Author: Po-Han Chiang (NYCU, Taiwan).

CORE INNOVATION: PHCSSM unifies recurrent SNN dynamics with diagonal SSM parallelism,
resolving the trade-off between learnable lateral connections and parallel scan efficiency.

ARCHITECTURE:
- Neuron Layer (NL): ALIF neurons with strictly diagonal recurrence (membrane dynamics)
- Synapse Layer (SL): Biologically constrained inter-neuronal communication weights
- Multi-Transmission Loop: Depth-M intra-timestep spatial recurrence, O(log T) parallelism
- Neurons partitioned into hierarchical regions governed by connectome topology

FIVE BIOLOGICAL CONSTRAINTS:
1. ALIF Dynamics: Adaptive thresholds, intrinsic temporal memory
2. Short-Term Plasticity (STP): Tsodyks-Markram formalism, time-varying effective weights
3. Dale's Law: Excitatory/inhibitory neurotransmitter consistency
4. Hierarchical Connectome Topology: Structured regional projections
5. Reward-Modulated STDP (R-STDP): Online Hebbian learning, batch-level reward gating

TECHNICAL:
- All dynamics reformulated as affine recurrences via log-domain parallel prefix sums
- Eliminates O(T) BPTT; preserves binary spike representations
- Parameter complexity: Theta(D^2) vs Theta(D^2*L) for L-layer stacks
- Training: 27-129s/1000 steps; 10-48 MB GPU memory

RESULTS (UEA physiological benchmarks):
- SCP2: 59.3% (LinOSS-IMEX: 58.9%)
- MotorImagery: 53.7% (+6pp vs Mamba)
- EigenWorms: 83.9% (2,701 parameters)
- Params: 1,748-9,485 vs 67K-401K for comparable SSMs

ABLATION: ALIF removal: -5.23pp; R-STDP removal: -4.37pp; all constraints non-redundant.
`

// === Phase 1: Parallel Analysis (Agents 1, 2, 3, 4, 6) ===
phase('Parallel Analysis')

const [a1_compute, a2_litSearch, a3_data, a4_applications, a6_lit] = await parallel([

  // Agent 1 (Compute / Opus): Mathematical framework
  () => agent(`You are Agent 1 (Compute). Deep mathematical analysis of PHCSSM.

${PAPER}

Analyze:
1. How ALIF, STP, R-STDP dynamics are reformulated as affine recurrences for log-domain
   parallel prefix sums — what mathematical structure enables this?
2. How the Multi-Transmission Loop achieves depth-M spatial recurrence while preserving
   O(log T) parallelism — explain the decoupling mechanism precisely.
3. Why PHC reduces parameter complexity from Theta(D^2*L) to Theta(D^2).
4. Theoretical limitations: approximation gaps, gradient flow, convergence.
5. Mathematical rigor assessment.

Be precise and critical.`,
    {label: 'A1:Compute', phase: 'Parallel Analysis', model: 'opus'}),

  // Agent 2 (Lit / Sonnet): Literature positioning
  () => agent(`You are Agent 2 (Literature & Positioning). Analyze PHCSSM's position in the field.

${PAPER}

Analyze:
1. Compare to SSM family: S4, Mamba, LinOSS-IMEX, GraphS4mer, GraphMamba.
2. Compare to SNN training: BPTT, surrogate gradient, STBP.
3. Relation to biological models: Tsodyks-Markram STP, ALIF, Dale's Law.
4. Is "first to unify recurrent SNN dynamics with diagonal SSM parallelism" well-supported?
5. Novelty assessment relative to the literature.`,
    {label: 'A2:LitSearch', phase: 'Parallel Analysis', model: 'sonnet'}),

  // Agent 3 (Data / Sonnet): Experimental results
  () => agent(`You are Agent 3 (Data Analyst). Critical analysis of experimental results.

${PAPER}

Analyze:
1. Are the 6 UEA physiological benchmarks appropriate and sufficient? What is absent?
2. SCP2: 59.3% vs 58.9% (LinOSS-IMEX) — is a 0.4pp margin meaningful?
3. Parameter efficiency: 1,748-9,485 vs 67K-401K — is this a fair comparison?
4. Ablation validity: is single-constraint removal sufficient for non-redundancy?
5. Missing experiments that would strengthen or weaken the claims.`,
    {label: 'A3:Data', phase: 'Parallel Analysis', model: 'sonnet'}),

  // Agent 4 (Applications / Opus): Practical implications
  () => agent(`You are Agent 4 (Applications & Impact). Practical implications of PHCSSM.

${PAPER}

Analyze:
1. Neuromorphic hardware compatibility: Intel Loihi, IBM TrueNorth, SpiNNaker deployment.
2. High-value application domains: EEG, BCI, neural decoding, edge computing.
3. Scalability: does the Multi-Transmission Loop create inference latency at scale?
4. Biological plausibility as a scientific tool vs pure engineering artifact.
5. Conditions where biological constraints hurt rather than help.`,
    {label: 'A4:Applications', phase: 'Parallel Analysis', model: 'opus'}),

  // Agent 6 (Lit / Haiku): Quick literature scan
  () => agent(`You are Agent 6 (Literature Scan). Rapid literature context for PHCSSM.

${PAPER}

Identify:
1. 3-5 most directly competing papers and their limitations vs PHCSSM.
2. 2-3 neuroscience papers whose models are incorporated — faithful implementation?
3. Significant omissions in the related work.
4. The broader research trend this paper fits into.

Be concise. Focus on gaps.`,
    {label: 'A6:Lit', phase: 'Parallel Analysis', model: 'haiku'}),
])

// === Phase 2: Monitor Gate (Agent 7) ===
phase('Monitor Gate')

const a7_monitor = await agent(`You are Agent 7 (Monitor). Quality-check the five parallel analysis outputs.

AGENT 1 (Compute): ${a1_compute}
AGENT 2 (Lit/Search): ${a2_litSearch}
AGENT 3 (Data): ${a3_data}
AGENT 4 (Applications): ${a4_applications}
AGENT 6 (Lit Scan): ${a6_lit}

Check for:
- Inter-agent contradictions
- Claims without evidence
- Important paper aspects not covered by any agent
- Coverage gaps: technical depth, empirical rigor, novelty, application

Output a concise Monitor Report: contradictions, gaps, instructions for synthesis.`,
  {label: 'A7:Monitor', phase: 'Monitor Gate', model: 'haiku'})

// === Phase 3: Adversarial Reflector (Agent 8) ===
phase('Reflector')

const a8_reflector = await agent(`You are Agent 8 (Adversarial Reflector). Find what all agents missed or got wrong.

PAPER: ${PAPER}
A1: ${a1_compute}
A2: ${a2_litSearch}
A3: ${a3_data}
A4: ${a4_applications}
A6: ${a6_lit}
A7 Monitor: ${a7_monitor}

1. The single most important weakness all agents underweighted.
2. Is the parameter efficiency comparison (1,748-9,485 vs 67K-401K) misleading?
3. Is testing on physiological EEG/EMG cherry-picking for biological constraints?
4. Reproducibility concerns: code availability, hyperparameter sensitivity.
5. What would a strong NeurIPS/ICLR reviewer reject this paper for?

Be adversarial. Do not hedge.`,
  {label: 'A8:Reflector', phase: 'Reflector', model: 'opus'})

// === Phase 4: Synthesis (Agent 5) ===
phase('Synthesis')

const a5_synthesis = await agent(`You are Agent 5 (Synthesis). Final comprehensive analysis report of PHCSSM.

PAPER: ${PAPER}
A1 (Mathematical Framework): ${a1_compute}
A2 (Literature & Positioning): ${a2_litSearch}
A3 (Experimental Results): ${a3_data}
A4 (Applications & Impact): ${a4_applications}
A6 (Literature Scan): ${a6_lit}
A7 (Monitor Report): ${a7_monitor}
A8 (Adversarial Reflector): ${a8_reflector}

Produce structured final report:
1. **Executive Summary** (3-4 sentences)
2. **Core Technical Contribution** (the parallelism-biology unification mechanism)
3. **Experimental Evidence Assessment** (what results prove and what they don't)
4. **Novelty & Positioning** (is the "first" claim justified?)
5. **Strengths** (top 3-4)
6. **Weaknesses & Limitations** (top 3-4, including adversarial critique)
7. **Practical Impact & Future Directions** (neuromorphic, BCI, scientific modeling)
8. **Overall Verdict** (accept/major revision/reject framing; score /10)

Integrate Monitor gap-filling and Reflector adversarial critique. Be balanced but honest.`,
  {label: 'A5:Synthesis', phase: 'Synthesis', model: 'opus'})

return {
  mathematical_analysis:   a1_compute,
  literature_positioning:  a2_litSearch,
  experimental_analysis:   a3_data,
  applications_impact:     a4_applications,
  literature_scan:         a6_lit,
  monitor_report:          a7_monitor,
  adversarial_critique:    a8_reflector,
  final_report:            a5_synthesis,
}
