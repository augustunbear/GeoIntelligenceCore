# Partial E04 offline COMPANY verification

## Baseline and isolation

Remote GitHub main was verified as `77e888dc338bf592dfdb1ce3725fd5b7f76aebbd`.
The cloud workspace reconstructed main as local commit `3aec618`; E04 starts
from that commit in the separate `GeoIntelligenceCore-e04` worktree on
`feat/e04-offline-company`. Open PRs #41–#45 were inspected before implementation.
Their source changes were not modified or incorporated. Changelog/status additions
are shared documentation that will need ordinary reconciliation on integration.
No user desktop, consumer repository or provider was used. The completed local
candidate was subsequently pushed as draft PR #46 with explicit user approval;
it remains unmerged and does not activate or deploy anything.

## Test and review evidence

- Clean reconstructed-main baseline: 308 passed, 3 opt-in live skips.
- Initial new test run: 36 assertion failures because COMPANY import was absent;
  implementing the additive contract made those 36 tests pass.
- Additional malformed-model/address/schema cases and independent-review
  regressions bring focused COMPANY unit + contract coverage to 44 passing tests.
- Independent reviewer reproduced uncaught `AttributeError` for incomplete nested
  `Point.model_construct()` / `WorkforceFact.model_construct()`. Both regressions
  failed before the fix and pass after atomic invalid-input handling. Reviewer
  reran the 43 unit tests and found no remaining issue; documentation was reviewed.
- Wheel and sdist build passed. Extracted base-wheel COMPANY imports passed with
  network connection blocked, without GIS/provider extras or credentials.

Final full offline suite: **352 passed, 3 opt-in live skips**, no warnings,
in 98.99 seconds. Command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src
../GeoIntelligenceCore/.venv/bin/python -m pytest -q`. This includes isolated
wheel/sdist installation and base/geometry/provider-extra packaging checks.
`git diff --check` passed.

## Limits

All COMPANY records, industry cases and rights claims in tests are synthetic.
No company dataset license, field accuracy, operating-site evidence, workforce
accuracy or real-source acceptance is established. This is a validated local
import path, not a company dataset or verified enrichment service. E04 transport
facts, live providers, source enablement, consumer changes, release and deployment
are absent. Existing `CompanySite` has not been weakened or changed.
