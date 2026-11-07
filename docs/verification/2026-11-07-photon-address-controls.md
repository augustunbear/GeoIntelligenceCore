# Predeclared public address controls — 2026-11-07

These [requests](samples/2026-11-07-photon-address-controls-samples.json)
and [thresholds](samples/2026-11-07-photon-address-controls-thresholds.json)
were written before any Photon request for this batch. They are **unmeasured**.
They retain the existing 100 m candidate-position, 8 s batch p95 and 100 MB
traced-memory ceilings. The same-name pair deliberately sends identical
`Hauptstraße 1` text with different near-point biases. Near is a ranking bias,
not a hard geographic filter; a wrong first result or absent labeled identity
fails. The third request names a street without a house number. It must not be
represented as house-level precision.

Frozen file SHA-256 values: requests
`00cb23a070f378bbad5c73720741320e2e50260b77329c4e068ec05305f8bf14`;
thresholds `fc20258c49b6e13d6ed8a3449d70af8dbba03598be226122d8630de4738ed085`.

| Case | Independent public address evidence | OSM-linked identity/point evidence | Label |
| --- | --- | --- | --- |
| a, d | [Gemeinde Grettstadt](https://www.grettstadt.de/verzeichnis/visitenkarte.php?mandat=189500) publishes Rathaus, Hauptstraße 1, 97508 Grettstadt. | [Mapcarta way 308128589](https://mapcarta.com/de/W308128589) gives 10.31238 E, 49.98471 N and the same civic address. | `house`, forward and reverse. |
| b | [Stadt Göppingen](https://www.goeppingen.de/start/erleben/ipunkt.html) publishes its Rathaus at Hauptstraße 1, 73033 Göppingen. | [Mapcarta node 94190766](https://mapcarta.com/N94190766) gives 9.65379 E, 48.70346 N and that address. | `house`, forward. |
| c | [Landeshauptstadt Potsdam](https://www.potsdam.de/de/brandenburger-strasse-als-veranstaltungsort) publishes the Brandenburger Straße pedestrian area, without a house number. | [OSM-derived way 30825768](https://www.strassenkatalog.de/osm/brandenburger_strasse%2C30825768w.html) identifies the street; a separate [published street point](https://placesofgermany.de/de/places/potsdam-brandenburger-strasse/) gives 13.0535164 E, 52.4002488 N. | `street`, forward. |

Municipal pages independently support the address/name and lack of house
number. The OSM-linked identity and location references are **not** independent
field surveys and can share source lineage with Photon. In particular, an OSM
street way can have multiple segments or a centroid that differs from the
published street point. The 100 m label remains fixed; a failed measurement is
evidence to investigate, not a reason to widen it after observing output.

This batch has four cases, leaving one attempt under the five-attempt run cap
only if no retry is needed. To preserve retries within that cap, split it into
smaller predeclared batches when actually measured, keeping the same labels.
Verify a persistent same-host ledger and source-wide lock before any I/O, count
all attempts including diagnostics, and record the clean package/settings
fingerprint. Recheck the original Pasing failure separately. This batch adds
two publicly verifiable same-text addresses and a genuine no-number street
request; it does not establish representative six-strata field readiness.
