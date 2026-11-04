# Provider/data policy and Germany-first inputs

## Provider adapters
Each provider declares: capability, license/terms link and checked date, access mode, key requirement, service region/language, allowed caching, permitted derivative use/republication, attribution, rate/cost limits, API schema version and freshness. Capability `disabled` and `unavailable` must be distinguishable. No downstream business module should parse vendor-specific payloads.

## Candidate inputs
- **OpenStreetMap/Geofabrik**: roads, addresses, restaurants, supermarkets, schools, parking, transit nodes and other POIs. https://www.openstreetmap.org/copyright and https://download.geofabrik.de/europe/germany.html . Data completeness varies and public tile/Overpass infrastructure is not a commercial SLA. ODbL attribution and derivative database obligations must be reviewed.
- **Photon**: geocoding from OSM; use governed hosted service or self-host when justified. https://github.com/komoot/photon
- **OpenRouteService / other routing**: walking/driving/cycling time regions. https://openrouteservice.org and https://github.com/GIScience/openrouteservice . Isochrones depend on road mode, speed assumptions and data update date.
- **Zensus 2022**: German census population/households by spatial grid where released; https://www.zensus2022.de and https://www.destatis.de . Census year must not be labeled as live 2026 population. Suppressed/missing cells require explicit treatment; spatial allocation should report approximation.
- **Public transport**: OSM + appropriate local GTFS/open transport authority data when licensed. Station nearby does not imply service frequency or mobility accessibility.
- **Companies/offices**: OSM business/office POIs, permitted public registries or commercial business directories; company count not employee count and POI coverage is incomplete.
- **Optional commercial**: Google Places, Targomo/Nexiga, local authority datasets. Contract review before storage, cross-provider joins, paid report inclusion or re-distribution. For Google Places validate current EEA-specific rules and permitted stored identifiers; Google data not assumed transferable to unrestricted MapLibre/OSM output.
- **Walk-by traffic**: measured sensors such as approved provider or on-site manual counting; NEVER infer actual restaurant visitors from population, POI or Google directions requests.

## Provenance and quality
Required output properties: raw provider ID when legally retainable; source and retrieval references; query geometry/parameters; dataset date and retrieval timestamp; license identifier and attribution; aggregation method; coverage and limitations; measured/derived/estimated/unverified status; missingness and uncertainty. Separate confidence of location match from reliability/completeness of source data.

## Privacy and security
Keep provider keys server-side in secret stores. Third-party geocoding sends potentially sensitive address queries offsite; document GDPR role, purpose and processing basis if personal data may be included. Minimize logs. Rate-limit and bound geographic queries. External licensed data is not automatically open data merely because it is returned by an API.
