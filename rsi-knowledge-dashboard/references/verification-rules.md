# Verification rules

Each check is code. A failure message is sent back to the model as an instruction.

| Check | Rule | What it cannot prove |
|---|---|---|
| **Structure** | Required sections, slide and panel counts, valid JSON, numeric chart values | That the content is good |
| **CitationKeys** | Every `[E#]` exists; no bare `E3` in prose; no hand-typed DOI, PMID or registry ID; a minimum number of distinct sources | That the source supports the claim |
| **NumericGrounding** | Each figure appears in the text of a source cited in the same sentence or table row; at least 95% must pass | That the number means what the sentence says |
| **CleanText** | No known identifiers, raw LaTeX, forbidden terms or placeholders | That other identifiers are absent |
| **Citation lookup** | Each DOI and arXiv ID exists and is registered to this title | That the paper supports the claim, or has not been retracted |

## Tuning NumericGrounding

Getting this wrong in either direction is costly.

- **What shares a citation:** a whole table row, or one sentence. Do not split on `;` or table cells, or figures get separated from citations at the end of a row and valid text fails.
- **In JSON,** a stat or chart is one claim: the citation in its label or title covers its values.
- **Ignored:** years, integers up to 10, and the 95 in "95% CI". These are not findings.
- **The 95% threshold** means a few figures may still be unmatched. Report the score. Lower it only with a reason.
- **Metadata-only sources** contribute no text, so figures cannot be attributed to them. This is intended.

## Learned rules

A failed check proposes a rule, which is added to the next pass as a candidate. It is promoted to `.rsi/playbook.json` only if the check stopped failing in that pass **and** fitness (the share of checks with no failures on any attempt) strictly rose. Otherwise it is rejected. Both outcomes go into `.rsi/ledger.jsonl`.

Be honest about the limits:

- One pass is a small sample, and other changes between passes can also explain an improvement.
- Rejection is the common and correct result on small runs.
- The hash chain is tamper-evident, not tamper-proof: anyone who can write the file can recompute it.

## Testing the checks

A check nobody has seen fail proves nothing. For each one, keep a test where it **fails** on bad input and a test where it **passes** on good input. For a bug found by reading real output, write the failing test first, then fix it.

Before trusting a green result, confirm the check actually ran. These have both passed silently: a loop that crashed, and a comparison shadowed by a shell alias that printed "identical".
