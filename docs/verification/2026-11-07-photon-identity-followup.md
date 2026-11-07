# Photon identity follow-up — 2026-11-07

The current main baseline is `05872fdd7aa728337deca2c1cdb4278da9e5b6f3`.
No open GeoIntelligenceCore PR was returned by the connected GitHub search at
the start of this change. The historical Pasing/Rattelsdorf measurement and
unchanged thresholds remain [failed evidence](reports/2026-11-06-photon-main-recheck.json).
The Pasing public diagnostic observed OSM way `25299100` twice in one Photon
response. The redacted report does not retain either raw feature, so it cannot
establish whether the indexed names, positions or address tags matched.

`Candidate.id` is the OSM type plus numeric ID. Repeating that pair means the
adapter cannot offer two independently identifiable choices. Even identical
features are a provider quality defect under the frozen FF-04 rule; different
features under one ID are more ambiguous. The adapter now returns
`unavailable` / `invalid_response` with null data for either case. The live
measurement still fails its required `ok` status and the duplicate cannot
inflate candidate count. Distinct OSM types retain distinct identities.

Offline regressions cover identical and conflicting duplicates in search and
reverse, a duplicate outside the requested bounding box, two separate objects
with the same place name, missing house number precision, and distinct OSM
types with the same numeric ID. These synthetic fixtures test adapter behavior,
not Photon accuracy. Earlier public samples with a city and near point do not
prove same-name disambiguation; a named square does not prove a street address
without a house number. Do not relabel them as completed strata.

## Acceptance still required

1. Freeze independent labels for the genuine same-name and missing-house-number
   *address* controls, with identity, coordinates, address components, expected
   ambiguity and provenance before invoking a provider. Do not send personal
   addresses without permission. Preserve the existing failed Pasing case and
   its thresholds.
2. On a clean candidate commit, run bounded Photon search and reverse through
   the existing Runner with the same persistent same-host ledger and source-wide
   lock. Recheck the original Pasing case and all six actual address strata.
   A result with `unavailable` is a failed quality gate, not a pass.
3. Before FF-05 activation, check the exact consumer wheel and target process,
   address privacy and notices, approved instance/version and rights for use,
   display, retention and export, durable quota and concurrency enforcement,
   and user confirmation. Photon demo's published reasonable-use policy does not
   provide a numeric production quota or SLA. No provider, consumer or target
   runtime was enabled by this change.

The current environment cannot reach GitHub's REST API through its shell proxy
and has no verified provider execution ledger or consumer checkout. This change
therefore makes no real Photon request and produces no new live quality report.
