# MapLibre consumer boundary

The Python consumer can request `export_result(retained_snapshot, format="geojson", language="en", purpose="example")`. Parse `result.data` only when `result.status` is `ok` or `partial`; inspect `result.issues` and `redactions` for omitted source data. The output is a GeoJSON `FeatureCollection` in WGS84 longitude/latitude order. A `partial` export is incomplete by design.

```js
const collection = JSON.parse(geojsonFromAuthorizedPythonConsumer);
if (collection.type !== 'FeatureCollection') throw new Error('Invalid GeoJSON');
map.addSource('facts', { type: 'geojson', data: collection });
map.addLayer({ id: 'facts-points', type: 'circle', source: 'facts',
  filter: ['==', '$type', 'Point'], paint: { 'circle-radius': 5 } });
```

This snippet assumes the host app has already initialized `map`, checked caller authorization, and received an export for its permitted purpose. Display the source attribution and omissions supplied with the result. The host app chooses and licenses its own basemap tiles; this package does not bundle tiles or grant MapLibre hosting rights. Keep private corrections and case data scoped in the host app, and never send `scope_token` to a public map service. This is an integration sketch, not a map app or a live provider demonstration.
