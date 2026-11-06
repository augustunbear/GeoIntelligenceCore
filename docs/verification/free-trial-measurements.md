# FF-04 controlled provider measurements

The real Photon, Overpass and ORS adapter runners are implemented. **No live
measurement has been performed by this change.** No approved representative
sample/threshold files or persistent runner quota path were supplied. Existing
activation/quality decisions remain blocked. A key alone is not a quality pass.

Run each source independently after reviewing its public/account terms and
free-plan quota. Photon/Overpass do not wait for an ORS account. Set
`GEO_LIVE_TESTS=1`, `GEO_LIVE_ACTIVATION_FILE=/secure/activation.json`,
`GEO_LIVE_BUDGET_DB=/persistent/private/geo-quota.sqlite` and set
`GEO_LIVE_REPORT_DIR=/secure/reports`; invoke only that source's test:

```sh
python -m pytest tests/integration/test_photon_live.py -q
python -m pytest tests/integration/test_overpass_live.py -q
python -m pytest tests/integration/test_ors_live.py -q
```

For an approved Codex cloud environment that has an enforced restricted HTTP
sidecar policy but no local public DNS/direct route, an individual activation
record may set `"transport_mode": "codex_proxy"`. The Runner checks
`/etc/codex/network-policy.json` for the exact approved source host and proxy,
then reads the inherited `HTTPS_PROXY` and `SSL_CERT_FILE` at runtime. The
proxy URL and CA path do not belong in the activation record or report. The
report records `transport_mode` and the network-policy SHA-256. Proxy mode is
explicit and source-specific; the default direct mode still validates public
DNS and pins its IP. Codex's sidecar must enforce the destination host and IP
policy, including denial of private destinations. The Runner sends a credential-free
private-target CONNECT probe through that proxy before and after the source run;
it refuses the run unless the proxy explicitly denies it with 403. It also
rechecks the proxy, CA and policy snapshot after the run. A local policy file
is a configuration snapshot, so also confirm current enforcement through the
environment status before a real run. Do not use this mode with an arbitrary untrusted
proxy, DNS override, or different host to bypass a rate limit. The same frozen
inputs, rights, quotas, clean checkout and quality gates apply.

Live runs require a clean source checkout with an editable install of that exact
package. The runner verifies imported package location, relevant tracked/untracked
changes, runtime source/resource fingerprint and runner fingerprint before HTTP,
and rechecks identity after measurements. Running from an unrelated working
directory cannot attribute an installed wheel to that directory's git HEAD.
Installable wheels remain consumer deliverables; this runner does not infer their
source commit from an unverified manifest.

The activation record retains the P13 references and limits. Also supply a real
application name/contact URL, `samples_ref` and `thresholds_ref` pointing to
reviewed local JSON files, and optional `endpoint` / `instance_id` for a compatible
instance. Require approval, at most 5 HTTP attempts/run, concurrency 1, zero cost,
explicit response/deadline bounds. For ORS set `credential_env` to the runtime
secret variable (normally `ORS_API_KEY`); do not include a key in any JSON file.
The output contains hashes of both input files, serving instance, package/source
version, timestamp, rights/quota/purpose references, HTTP reservation count,
per-case status and quality, p50/p95 and peak traced Python memory, and separate
quality/latency/memory/budget gates. It contains no raw address, candidate payload,
key or provider error text. Opaque case IDs must contain no personal information.

Samples are a list of `{id, operation, request}` objects. `request` is the existing
typed request model serialized as JSON. Operations are `search`/`reverse` for
Photon, `places` for Overpass, `route`/`matrix`/`catchments` for ORS. Thresholds are
`{cases: {<id>: <expectation>}, max_p95_s: <positive seconds>,
max_peak_bytes: <positive bytes>}`. Freeze all labels and performance bounds
before requests. Each provider batch must include a positive quality case for every required operation: Photon search and reverse; Overpass places; ORS route, matrix and outbound catchments, plus inbound catchments whenever that capability is enabled. Missing operations block before any HTTP; negative controls cannot substitute for positive coverage. Missing/malformed labels block before provider I/O.

| Positive case | Required expectation fields besides `status: "ok"` |
| --- | --- |
| Photon | `candidate_ids`; independent `candidate_points` mapping each ID to `[longitude, latitude]`; positive `max_error_m`; required `precisions` mapping IDs to allowed precision labels, required `min_candidates`/`max_candidates`, optional `first_id` for a ranked match. Candidate labels must be distinct and cover the minimum candidate count; `first_id` must be labeled. Ambiguity uses explicit candidate bounds and multiple independently labeled IDs. Duplicate returned candidate IDs fail quality rather than inflate cardinality. |
| Overpass | Independent `source_keys` such as `osm:node:7`; positive `min_precision` and `min_recall` up to 1. A 200 response or unlabeled empty result cannot establish coverage. |
| Route | Independently approved `distance_m: [min,max]` and `duration_s: [min,max]`. Adapter checks endpoint direction and quantities. |
| Matrix | `cells` must cover exactly the request origins × destinations, mapping each directed `origin>destination` ID to `[min,max]` seconds. Missing, extra or reversed labels block before any request; missing, extra or duplicate returned cells fail quality. Test all-null known no-route cells as a separate unavailable control with `issue_code: "no_route_cells"`; mixed partial matrices do not pass. |
| Catchments | `durations_s`, `direction`, and independent `area_m2: [min,max]`. Adapter validates network geometry, thresholds and nesting. |

Negative controls can explicitly expect typed `no_results` (Photon/Overpass), or
known no-route results: route unavailable with `issue_code: "no_route"`, matrix
unavailable with `issue_code: "no_route_cells"` and explicit null `cells`. Network,
deadline and storage failures do not satisfy those controls. Unknown expectation
fields are rejected before HTTP. Controls do not replace positive accuracy/coverage. Partial, wrong-candidate, timeout,
unavailable, budget-limited and invalid responses cannot pass a positive label.
At most five cases/batch are loaded; retries and redirects share the five-attempt
budget, so operators must choose batches accordingly. Small-sample p95 describes
that batch only, not a provider SLA. Peak memory is traced Python memory, not
whole-process RSS. If tracing was already active, its historical process peak is
reported; run a fresh isolated process for a source-specific measurement. No raw source output is retained by the runner.

The test harness's SQLite ledger atomically shares a 50-attempt UTC-day cap per
protocol/source domain and a 5-attempt run cap across client reconstruction and
same-host processes. API keys and instance aliases cannot create new domains.
An OS file lock serializes each whole source operation and releases on all exits.
The ledger and lock files must be on persistent local storage shared by those
processes; ephemeral CI disks, separate machines or a network filesystem do not
establish shared daily enforcement. Do not delete/change the ledger path to reset
quota. An unavailable or indeterminate store stops HTTP; consumed reservations
are not refunded. This controlled-test ledger is not the application's database,
not a distributed service, and is not a new core infrastructure requirement.
FF-05 must use and verify the consumer's existing durable storage instead.

The runner reuses the typed `BudgetUnavailable` / gateway failure behavior from
FF-02. FF-01/FF-02 must be included before adopting the complete source candidate.
Public output rights remain unknown unless independently approved; a report's
rights reference is evidence to review, not an automatic retention/export grant.

Reviewed custom instances may supply validated `settings`, `capability_flags`
(including explicit inbound catchment support), `authentication_header` and
geometry bounds. Known hosted authentication remains mandatory. Header values
are read only from the declared runtime credential environment variable; null
means no credential variable, not a lookup of a null name. Effective limits,
instance owner/version, terms/pricing references, dependency versions and a
sanitized configuration fingerprint are retained in the report.

A total timeout is blocked and may omit partial-case diagnostics; consumed
attempts remain in the persistent ledger and are recorded as `calls` in timeout
and shared-control failure reports. No successful quality claim is made
from such a report.

Reports include `effective_settings` and a canonical `settings_sha256` (SHA-256 of sorted compact JSON from TrialSettings.model_dump(mode="json")). Consumers must use those exact settings and verify the digest before activation; changing limits or other settings requires a fresh measurement.
