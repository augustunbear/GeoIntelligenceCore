# Optional offline opening-hours evaluation

Install `pip install 'geo-intelligence-core[temporal]'`. The optional dependency
is exactly `opening-hours-py==2.1.5`, with `tzdata==2026.6` providing an IANA
fallback when the host lacks a system database (including Windows). Core import
does not load the parser. CI uses
`requirements/temporal-py312.lock` alongside the existing hashed locks. That
lock deliberately covers the audited Linux x86_64 wheel only; other platforms
can install the pinned extra but need their own audited artifact hashes.

```python
from datetime import datetime
from geo_intelligence_core import evaluate_opening_hours

result = evaluate_opening_hours(
    'Mo 22:00-02:00',
    at=datetime.fromisoformat('2026-11-10T00:30:00+00:00'),
    timezone='Europe/Berlin',
)
assert result.status == 'ok' and result.data.state == 'open'
```

The caller supplies an offset-aware instant and explicit IANA place timezone.
Equivalent offsets identify the same instant; repeated autumn wall-clock times
need an offset or a correctly supplied ZoneInfo fold. Naive timestamps, including
DST gaps and folds, return unknown. No timezone or location is inferred.
UTC conversion followed by conversion to the place ZoneInfo works around the
upstream binding's requirement for a timezone object with a `key` attribute.
Opening boundaries are inclusive, closing boundaries exclusive. Overnight and
Berlin spring/autumn DST are covered by synthetic offline tests.

The immutable result retains the raw expression, evaluation instant (UTC),
timezone, parser name/version and method version. Parser name/version are null
unless the verified backend is actually invoked. State is `open`, `closed` or
`unknown`; uncertainty gives `Status.unknown` and an issue, never a false closed.
Missing/invalid syntax, missing optional parser, unverified parser versions and
backend failures fail closed. Dates before 1900 or local years after 9998 and
expressions longer than 4096 characters are outside this adapter's supported
bounds and return unknown.

## Deliberate conservative exclusions

- All PH, SH and Easter expressions return unknown, even with whitespace-free selectors
  such as `PH09:00-18:00` or `Mo,PH09:00-18:00`. There is no country/subdivision
  argument. Upstream exposes a country-level embedded public-holiday database;
  this does not establish German state or school-holiday coverage. No holiday
  details, holiday overrides or ordinary-weekday fallbacks are invented.
- Sunrise, sunset, dawn and dusk return unknown. No coordinates are inferred or
  defaults accepted for solar events.
- Any plus sign returns unknown, including open-ended times such as `09:00+`
  and `09:00-17:00+`. The adapter does not guess a closing time.
- Quoted comments return unknown, including comment-only appointment schedules.
  Upstream can classify a comment-only schedule as open, which is insufficient
  evidence for this adapter.

These guards intentionally over-reject token occurrences inside comments or
other strings. They are safety exclusions, not a reimplementation of the OSM
grammar. All remaining syntax and schedule evaluation belongs to upstream.
This API is separate from analysis, POI filtering and observation normalization.
It never establishes real-world freshness, source acceptance, attendance, rights,
collection permission, live activation or source quality. Source evidence and
rights remain caller-owned and are not synthesized by evaluating a string.

## Dependency provenance and license

- Distribution: [opening-hours-py 2.1.5 on PyPI](https://pypi.org/project/opening-hours-py/2.1.5/).
- Upstream: [opening-hours-rs Python bindings](https://github.com/remi-dupre/opening-hours-rs/tree/master/opening-hours-py).
- Installed wheel metadata declares `MIT OR Apache-2.0`, Python >=3.10,<4,
  and no runtime Python dependencies of its own. This project selects the MIT option.
- Copyright (c) 2021 Rémi Dupré. The exact upstream MIT notice from that wheel
  is preserved in [the license notice](../licenses/opening-hours-py-MIT.txt).
- Audited artifact: `opening_hours_py-2.1.5-cp310-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`;
  SHA256 `9e3e08babe6049777d8b1dfdc4e7ee955e9e9755c4b8112571cfc2d7d43a8f2b`.

The pinned [tzdata 2026.6](https://pypi.org/project/tzdata/2026.6/) wheel
`tzdata-2026.6-py2.py3-none-any.whl` has SHA256
`0a10eec6e13ef16b627fabed9a5f2ba61a62b1c67f327305f4e7e412a70b4aec`.
Its metadata selects Apache-2.0; the [copyright/data notice](../licenses/tzdata-LICENSE.txt)
and [Apache license](../licenses/tzdata-LICENSE_APACHE.txt) are copied from that
wheel. The fallback contains IANA 2026f. Python uses its normal system database search before this fallback;
there is no claim that every host has identical timezone data. Installed-wheel
tests force an empty system timezone search path to verify the fallback offline.

No upstream implementation is vendored. The dependency software license does not
grant rights to OSM schedules or holiday datasets. Embedded holiday data is not
used in this slice; any later holiday support requires separate capability,
coverage, vintage and rights review. No Node runtime or service is introduced.
