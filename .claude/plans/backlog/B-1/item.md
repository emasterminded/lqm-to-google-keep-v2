# B-1 - Backfill COVERAGE.md for code no run has mapped yet
**Category:** User feature | **Class:** 2 | **Priority:** High
**Origin:** Ed (2026-10-02 via orchestrator agents 7bcf117) | **Effort:** M | **Tag:** [backend] | **Filed by:** orchestrator on Ed's word (2026-10-02)
**Rank:** 1 of 1 (2026-10-18)
**Depends on:** none
**Status:** OPEN
**Groomed:** 2026-10-18 by backlog-keeper - converted from legacy tier 3; class 2 because filed on Ed's word (Ed may reclass to QoL)

**Why.** Code shipped before agents 7bcf117 has no COVERAGE.md map, so "what is the coverage of X" has no answer.

**What.** Since agents 7bcf117, the tester writes `COVERAGE.md` at the repo root (Tests step 6): a smoke table, one row per major feature, and a unit table, one row per meaningful path of each function with its CC, covering test (`file::name`) and result. It maps only what a run touches, so code shipped before that has no map and "what is the coverage of X" has no answer.

**Fix direction.** Test-only run, no implementation change. The planner lists the major features (README, routes/commands/screens) and every function with its CC (the repo's CC tool over the whole tree). the tester builds both tables from the existing tests and records each path's real result from a suite run; an untested feature or path is `NONE`. Pre-existing `NONE` rows do not fail this run: each one goes to `unverified-findings.md` as a coverage gap for the planner to rank. Header `as of <sha>`. Merge to the base branch.

**Definition of Done:**
- [ ] `COVERAGE.md` on the base branch has a row for every major feature (check: compare rows against the README/routes/commands/screens list in the plan)
- [ ] `COVERAGE.md` has a row for every meaningful function path (check: compare rows against the CC tool output over the whole tree)
- [ ] its `as of` sha is the merge commit's parent (check: `git rev-parse <merge>^1` equals the header sha)
- [ ] every `NONE` row is filed (check: each `NONE` row has an entry in `unverified-findings.md` or a follow-up item)
**Does not block close:** filling the `NONE` gaps themselves (filed as follow-up items unless Ed says otherwise at ship time).

**Ed asks (at ship time).** Fill the `NONE` gaps in this run, or file them as follow-up items (default)?
