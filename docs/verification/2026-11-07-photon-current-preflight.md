# Photon current-workspace preflight — 2026-11-07

Candidate PR [#39](https://github.com/augustunbear/GeoIntelligenceCore/pull/39)
head `09b04540bda3da0bf0cd81a4022cfc9c60e66460` was clean at the start of
this check and its [offline CI](https://github.com/augustunbear/GeoIntelligenceCore/actions/runs/42374583214)
passed. Main remained `05872fdd7aa728337deca2c1cdb4278da9e5b6f3`.
The [four predeclared address controls](2026-11-07-photon-address-controls.md)
passed offline request/expectation shape validation. They were not measured.

The selected Photon demo host is listed in the environment's restricted HTTP
policy; an inherited HTTPS proxy and CA bundle file are present. This only
establishes that a possible transport path exists, not that the actual request
would succeed. The current process has no `GEO_LIVE_ACTIVATION_FILE`,
`GEO_LIVE_BUDGET_DB` or `GEO_LIVE_REPORT_DIR` binding. The only SQLite quota
files found under this workspace are generated test fixtures; no prior shared
same-host production/trial ledger path was established. Creating a fresh ledger
would not account for other agents or previous requests and cannot prove the
50-attempt UTC-day aggregate. There is no reviewed activation record for this
Photon instance and exact candidate source/settings. **Zero Photon HTTP
attempts** were made in this preflight.

The [Photon operator policy](https://github.com/komoot/photon/blob/master/README.md#demo-server)
currently permits reasonable project use of its demo endpoint and warns that
extensive use may be throttled or banned; it gives no numeric quota or uptime
guarantee. [OSM's copyright page](https://www.openstreetmap.org/copyright)
requires attribution and ODbL notice for its data. These references do not by
themselves establish the consumer's retention/export rights, privacy treatment
for submitted addresses or a sustainable production request budget.

Before a real run, bind a reviewed activation file to this exact clean source
and frozen sample/threshold hashes; establish a **single existing persistent
same-host ledger** and source-wide lock that includes all Photon diagnostics and
parallel work; verify the target proxy policy and provider-use purpose. Run
small batches within five attempts including retries, preserving failures.
Recheck Pasing separately. FF-05 still also needs target consumer wheel/runtime,
privacy, rights and durable application-wide quota/concurrency validation.
No source was enabled or merged.
