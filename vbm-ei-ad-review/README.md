# Virtual-Brain E/I Balance in Aging & AD — Literature Review

Multi-agent literature review on inferring neuronal **excitation/inhibition (E/I) balance** from EEG/MEG via neural-mass / virtual-brain models, across **normal aging and Alzheimer's disease**. Produced with the PHCSSM v3.0 (Robin-MAS) multi-agent pattern adapted to literature-review mode.

| File | What it is |
|------|-----------|
| `2026-06-22_VBM-EI-AD_academic_review.md` | English academic review, APA 7th (8 sections, 11 references, 10 open questions) |
| `2026-06-22_VBM-EI-AD_blog_popular_science.md` | Traditional-Chinese popular-science blog (stadium-wave / AM-radio / city-synthesizer analogies) |
| `2026-06-22_VBM-EI-AD_Session.md` | Session wrap-up + pitfalls (design decisions, execution stats, provenance-inflation pitfall) |
| `vbm_ei_ad_review_workflow_v1.js` | The 15-agent workflow script (6 reusable schemas + review-synthesis schema) |

**Source corpus:** 3 NotebookLM notes distilling 11 primary papers (Clusella 2022; Cooray 2023; Deschle 2021; Lu 2022; Maestú 2021; Schirner 2018; Stam 2023; Stefanovski 2019/2021; Yokoyama 2023; Zimmermann 2018). Held in the local project folder `D:\Virtual brain_simulation_Neuronal_E_I_balance`.

**Provenance & integrity:** every claim grounded in the source notes (grounding gate reads originals); all bibliographic metadata independently verified against publisher records; no references, DOIs, or numbers fabricated. Generated draft — author name/affiliation and any extra-corpus claims require human completion before submission.

**Run:** `Workflow({scriptPath: ".../vbm_ei_ad_review_workflow_v1.js"})` in Claude Code (the script reads the 3 note files from the `D:` project folder).
