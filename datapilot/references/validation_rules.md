# Validation rules & reporting

Integrate everything that is valid; FLAG the rest. Never delete a row silently.

## Required fields (row is "flagged" if any missing)
- ID present and unique (within the file AND against the existing master).
- gender present and in {女/男 -> F/M}.
- birthday present and parseable -> age computed and in range 0–120.

## Additional checks
- eduyear: education value recognized (see mapping); else flag.
- IRB Check: must be TRUE; FALSE/blank -> flag "IRB not confirmed".
- Duplicates: same ID appearing twice in the file, or already in the master -> flag.
- Uncertain mappings (character, source, sport_types): leave blank -> list as
  "awaiting mapping confirmation".
- Unmapped source columns: list them so the owner can decide.

## Report structure (the validation digest)
1. **Summary line** — read N subjects; integrated M; flagged K; new columns U.
2. **Counts table** — issue type vs count (missing gender, bad birthday,
   IRB not confirmed, duplicates, unrecognized education…).
3. **Row-level flags** — ID + which check failed (no personal names).
4. **Columns awaiting confirmation** — uncertain + unmapped columns.
5. **Next actions** — the shortest human to-do list to clear the flags.
