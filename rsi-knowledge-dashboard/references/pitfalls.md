# Pitfalls

Each of these really happened while building and auditing a dashboard like this one. Most looked like success.

## False success

| Pitfall | How it appeared | How to detect it | Prevention |
|---|---|---|---|
| **Status text with nothing behind it** | "HIPAA PASS" and "Active" were hard-coded HTML | Search the page for status words, then ask what sets each one | Every status comes from a run report |
| **A "research agent" that does no research** | Output was template strings. Search results were fetched and never used | Change the topic and diff the output | Test that each input changes the output |
| **Controls that do nothing** | The passes selector was only written to a log | Trace each setting to where it is used | Remove it or make it work |
| **Mock output treated as success** | A missing SDK returned plausible text marked as finished | Run with the provider removed | Raise an error; mocks must be explicitly requested |
| **Fake fallback data** | When a search failed, curated papers appeared. Their IDs belonged to unrelated physics and mathematics papers | Look up every built-in citation by title | Failed sources contribute nothing and say so |
| **A verifier that checks a constant** | The CLI verify command checked a hard-coded string and always passed | Feed it known-bad input | Every check needs a failing test |
| **Scoring without evidence** | An empty result scored 75% because unrun checks counted as passed | Score an empty input | No evidence means no credit |
| **A "safety gate" that cannot block** | Hooks swallowed exceptions and ignored exit codes | Write a hook that denies, and confirm the action did not run | Test that blocked actions do not execute |

## Citations

| Pitfall | How it appeared | Prevention |
|---|---|---|
| **A real DOI on the wrong paper** | It resolved at doi.org but belonged to an unrelated paper. An existence check passed | Compare the registered title |
| **One citation merging two papers** | The title came from one paper, while the claims came from another by the same author | Read the sentences that cite it, and do not blindly "fix" the journal |
| **Taking a DOI from a paper's reference list** | The first DOI found in a PDF belonged to something it cited | Accept a DOI only if its registered title is on the file's first page |
| **Correct DOI, wrong title or authors** | Only title and first-author checks found these | Compare title, year and first author, using the original PDF where available |
| **PDF metadata** | Titles such as "untitled", or a filename, reached the reference list | Read the rendered reference list |
| **Treating lookup failures as fabrication** | An outage is not evidence of a fake paper, and "not registered" is not proof either | Report "could not check" and "not found" separately, in careful words |

## Checker tuning

| Pitfall | How it appeared | Prevention |
|---|---|---|
| **Splitting too finely** | Splitting on `;` and table cells separated figures from their citations, causing many false failures | One unit is a sentence or a whole table row |
| **Checking too strictly on format** | `"63.6 [E4]"` failed as a chart value | Parse leniently, but still verify the number |
| **Internal keys leaking** | Readers saw "E4 and E9 report…" | Check for bare keys outside brackets |
| **Wrong domain translation** | Models invented several Chinese terms for one concept | Supply a glossary, and fail on known wrong terms |
| **Summing a cumulative cost** | SDK session cost accumulates, so summing overcharges and stops runs early | Charge only the increase; test with a few real turns |

## Browser and server

| Pitfall | How it appeared | Prevention |
|---|---|---|
| **Form validation blocks submission** | `min="0.1" step="0.5"` made the default of 8 invalid, so the button did nothing. All API tests passed | Click it in a real browser. Use `step="any"` |
| **Local file pages cannot call the server** | The page was opened from disk, and a catch block hid the CORS failure | Detect `file:` and link to the served page |
| **Opening CORS for convenience** | Any website could then start paid runs | Same-origin, Host check, JSON only. Allow only a read-only health check |
| **A test racing the page** | The test read a list before the page refreshed it | Wait on the final state |
| **Untrusted model text in HTML** | `innerHTML` and unescaped slides | Use `textContent` and `html.escape` |

## Privacy

| Pitfall | How it appeared | Prevention |
|---|---|---|
| **A note about removing identifiers contains them** | A wrap-up listing each removed identifier was pushed to a public repo | Scan every pushed file, including notes and old versions |
| **Scanning only the changed lines** | Fine for a commit, not for publishing a whole tree | Before going public, scan and read the whole tree |
| **A secrets file in a repo** | A `.env` was committed long before anyone looked | Check the tree for `.env`, and rotate anything exposed |
| **Deleting isn't removal** | Files stay in history, and may be copied or cached | Make private first, clean history, rotate secrets, report |
| **Clone counts can't prove safety** | Traffic data lags, and stopped before the exposure began | Say what the data cannot show |

## Process and tooling

| Pitfall | How it appeared | Prevention |
|---|---|---|
| **Green tests with a fake model** | Real runs exposed slow retries, bad references and leaked keys | Do a small live run, then read and look at the outputs |
| **A comparison that never ran** | A helper named `H` was shadowed by a PowerShell alias, and the script printed "identical" | Print counts, and distrust a result you did not see computed |
| **A hashtable key named `keys`** | It hid `.Keys` in PowerShell, so a scan silently did nothing | Use an ordered list of pairs |
| **Login status that isn't true** | A CLI reported valid credentials while every real call failed | Test with a real call |
| **Broken submodule entries** | A Git install failed because of an unrelated folder in a monorepo | Give a reusable package its own repo |
| **Google Drive and virtual drives** | Random-access writes can fail | Serialize to memory, then write once. Keep virtual environments off the drive |
| **Overwriting hand-corrected files** | A button regenerated files that had been fixed by hand | Each run writes to a new folder |
