# 开源项目核验快照（2026-11-04）

本表来自本次读取 GitHub repository 与 releases/latest 的返回值。所有列出项目的 archived 均为 false。
pushed_at 仅代表仓库活动，不证明代码质量、安全或用户支持。latest Release 不等于包注册表版本，也不等于本项目已锁定的版本。
未取得 Release 可能是该端点没有结果，不能据此认定停止维护。许可列是 GitHub 自动识别，不替代目标版本 LICENSE 与传递依赖核对。

| 项目 | 观察到的 Release | 发布日期 UTC | 仓库推送日期 UTC | GitHub 许可识别 | 本项目决定 |
|---|---|---|---|---|---|
| [komoot/photon](https://github.com/komoot/photon) | [1.3.0](https://github.com/komoot/photon/releases/tag/1.3.0) | 2026-08-07 | 2026-11-02 | Apache-2.0 | 首选地址引擎；可配置适配器，公共/演示实例按最新受控使用策略显式评估 |
| [pelias/pelias](https://github.com/pelias/pelias) | 未取得 latest Release；不推定无发布 | — | 2026-07-24 | MIT | 备选地址平台；多源地址确有增益时替换，不初始自建 |
| [osm-search/Nominatim](https://github.com/osm-search/Nominatim) | [v5.3.3](https://github.com/osm-search/Nominatim/releases/tag/v5.3.3) | 2026-10-14 | 2026-11-03 | GPL-3.0 | 不选公共接口作联想；自建/合约服务可做地址核实备选 |
| [GIScience/openrouteservice](https://github.com/GIScience/openrouteservice) | [v10.1.0](https://github.com/GIScience/openrouteservice/releases/tag/v10.1.0) | 2026-10-14 | 2026-11-03 | GPL-3.0 | 首选步行/骑行/驾车路线与等时圈接口 |
| [valhalla/valhalla](https://github.com/valhalla/valhalla) | [3.9.1](https://github.com/valhalla/valhalla/releases/tag/3.9.1) | 2026-10-06 | 2026-11-04 | NOASSERTION | 自托管路由备选；不与 ORS 同时常驻部署 |
| [drolbr/Overpass-API](https://github.com/drolbr/Overpass-API) | [osm3s_v0.7.62.4](https://github.com/drolbr/Overpass-API/releases/tag/osm3s_v0.7.62.4) | 2024-11-21 | 2026-02-19 | AGPL-3.0 | 首选小范围 OSM POI 查询协议/服务；不嵌入服务器代码 |
| [shapely/shapely](https://github.com/shapely/shapely) | [2.2.0](https://github.com/shapely/shapely/releases/tag/2.2.0) | 2026-10-07 | 2026-11-03 | BSD-3-Clause | 首选本地几何运算与空间索引 |
| [pyproj4/pyproj](https://github.com/pyproj4/pyproj) | [3.8.0](https://github.com/pyproj4/pyproj/releases/tag/3.8.0) | 2026-09-05 | 2026-11-02 | MIT | 首选坐标转换、测地距离与面积 |
| [geopandas/geopandas](https://github.com/geopandas/geopandas) | [v1.2.0](https://github.com/geopandas/geopandas/releases/tag/v1.2.0) | 2026-09-28 | 2026-10-31 | BSD-3-Clause | 首选可选统计/批量空间分析 |
| [geopandas/pyogrio](https://github.com/geopandas/pyogrio) | [v0.13.0](https://github.com/geopandas/pyogrio/releases/tag/v0.13.0) | 2026-06-26 | 2026-11-04 | MIT | 统计附加能力的矢量文件读取，避免单独 GIS 服务 |
| [gboeing/osmnx](https://github.com/gboeing/osmnx) | 未取得 latest Release；不推定无发布 | — | 2026-07-31 | MIT | 分析/校验工具，不用作每次在线查询的通用路由引擎 |
| [maplibre/maplibre-gl-js](https://github.com/maplibre/maplibre-gl-js) | [v6.16.0](https://github.com/maplibre/maplibre-gl-js/releases/tag/v6.16.0) | 2026-10-25 | 2026-11-04 | NOASSERTION | 首选调用方地图；不进入 Python 核心依赖 |
| [postgis/postgis](https://github.com/postgis/postgis) | 未取得 latest Release；不推定无发布 | — | 2026-10-30 | GPL-2.0 | 有持久化/高并发空间查询需求后启用，不必需 |
| [uber/h3](https://github.com/uber/h3) | [v4.5.0](https://github.com/uber/h3/releases/tag/v4.5.0) | 2026-05-21 | 2026-11-01 | Apache-2.0 | 暂不引入；保留原始人口网格，避免无必要重采样 |
| [qgis/QGIS](https://github.com/qgis/QGIS) | [final-3_44_15](https://github.com/qgis/QGIS/releases/tag/final-3_44_15) | 2026-09-25 | 2026-11-04 | GPL-2.0 | 人工 QA 工具，不嵌入服务器或应用 |
| [pydantic/pydantic](https://github.com/pydantic/pydantic) | [v2.14.2](https://github.com/pydantic/pydantic/releases/tag/v2.14.2) | 2026-10-29 | 2026-11-04 | MIT | 首选契约/配置验证与 JSON Schema |
| [encode/httpx](https://github.com/encode/httpx) | [0.28.1](https://github.com/encode/httpx/releases/tag/0.28.1) | 2024-12-06 | 2026-10-02 | BSD-3-Clause | 首选可选 HTTP 适配层，共用超时/连接限制 |
| [rapidfuzz/RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) | [v3.14.6-1](https://github.com/rapidfuzz/RapidFuzz/releases/tag/v3.14.6-1) | 2026-08-30 | 2026-11-03 | MIT | 可选疑似重复候选排序；不得凭相似度自动合并 |
| [MobilityData/gtfs-validator](https://github.com/MobilityData/gtfs-validator) | [v8.0.1](https://github.com/MobilityData/gtfs-validator/releases/tag/v8.0.1) | 2026-05-12 | 2026-11-03 | Apache-2.0 | 首选离线 GTFS 质量检查工具 |
| [opentripplanner/OpenTripPlanner](https://github.com/opentripplanner/OpenTripPlanner) | [v2.10.0](https://github.com/opentripplanner/OpenTripPlanner/releases/tag/v2.10.0) | 2026-09-09 | 2026-11-04 | NOASSERTION | 不选等时圈主路径；现行版本不能依赖旧 TravelTime API |
| [osmcode/pyosmium](https://github.com/osmcode/pyosmium) | [v4.3.2](https://github.com/osmcode/pyosmium/releases/tag/v4.3.2) | 2026-10-18 | 2026-11-01 | BSD-2-Clause | 可选区域 PBF 批量导入，替代规模化公共 Overpass 抓取 |
| [pelias/api](https://github.com/pelias/api) | [v7.11.0](https://github.com/pelias/api/releases/tag/v7.11.0) | 2026-09-25 | 2026-10-21 | MIT | Pelias HTTP 入口参考；不将其 Node 服务嵌入 Python |
| [pandas-dev/pandas](https://github.com/pandas-dev/pandas) | [v3.1.1](https://github.com/pandas-dev/pandas/releases/tag/v3.1.1) | 2026-11-04 | 2026-11-04 | BSD-3-Clause | 统计附加能力的表格处理，不因最新发布就强制升级 |
| [Leaflet/Leaflet](https://github.com/Leaflet/Leaflet) | [v1.9.4](https://github.com/Leaflet/Leaflet/releases/tag/v1.9.4) | 2023-05-18 | 2026-11-04 | BSD-2-Clause | 已有简单地图的可保留备选，不强制迁移 |
| [remi-dupre/opening-hours-rs](https://github.com/remi-dupre/opening-hours-rs) | 未取得 latest Release；不推定无发布 | — | 2026-11-04 | Apache-2.0 | 首选可选营业时间解析 Python 绑定 |
| [opening-hours/opening_hours.js](https://github.com/opening-hours/opening_hours.js) | [v3.15.0](https://github.com/opening-hours/opening_hours.js/releases/tag/v3.15.0) | 2026-09-21 | 2026-11-02 | 未识别 | 语义对照/前端备选，不给 Python 核心新增 Node 运行时 |
| [geopy/geopy](https://github.com/geopy/geopy) | [2.5.0](https://github.com/geopy/geopy/releases/tag/2.5.0) | 2026-07-12 | 2026-07-12 | MIT | 暂不引入；不能代替来源元数据和本项目 provider 合约 |
| [DinoTools/python-overpy](https://github.com/DinoTools/python-overpy) | 未取得 latest Release；不推定无发布 | — | 2026-11-02 | MIT | 暂不引入；小范围 JSON 查询直接通过 HTTPX，减少包装层 |
| [Project-OSRM/osrm-backend](https://github.com/Project-OSRM/osrm-backend) | [v26.11.0](https://github.com/Project-OSRM/osrm-backend/releases/tag/v26.11.0) | 2026-11-01 | 2026-11-02 | BSD-2-Clause | 不选初始方案；重点是路线/矩阵，非本项目等时圈主路径 |
| [r5py/r5py](https://github.com/r5py/r5py) | [v1.1.7](https://github.com/r5py/r5py/releases/tag/v1.1.7) | 2026-06-29 | 2026-09-20 | NOASSERTION | 条件备选公交区域分析；暂缓启用，不为人口单独引入 |
| [conveyal/r5](https://github.com/conveyal/r5) | [v7.6](https://github.com/conveyal/r5/releases/tag/v7.6) | 2026-08-01 | 2026-11-04 | MIT | R5py 下层引擎参考；不得擅自以最新版本替换其配套 JAR |

## 人工补充核验
- Valhalla COPYING 内容为 MIT：https://github.com/valhalla/valhalla/blob/master/COPYING 。
- MapLibre LICENSE.txt 包含 BSD-3-Clause 条款及第三方声明：https://github.com/maplibre/maplibre-gl-js/blob/main/LICENSE.txt 。不能因 API 返回 NOASSERTION 就说没有许可。
- OpenTripPlanner LICENSE 为 LGPL-3.0-or-later 主许可及历史第三方条款：https://github.com/opentripplanner/OpenTripPlanner/blob/dev-2.x/LICENSE 。
- R5py v1.1.7 README 和 pyproject 明确 GPL-3.0-or-later OR MIT；本项目选 MIT 路径，仍核对分发依赖：https://github.com/r5py/r5py/blob/v1.1.7/README.md 。
- opening-hours Python 绑定 Cargo.toml 为 MIT OR Apache-2.0；当前源码版本 2.1.5 不是已验证的 PyPI 发布版本：https://github.com/remi-dupre/opening-hours-rs/blob/master/opening-hours-py/Cargo.toml 。
- OSMnx 当前 pyproject 版本 2.1.1，仅为源码观测，不当作已核实发行包版本：https://github.com/gboeing/osmnx/blob/main/pyproject.toml 。

## 兼容性证据
已按 tag 读取：
- [Shapely 2.2.0](https://github.com/shapely/shapely/blob/2.2.0/pyproject.toml)：Python >=3.11，NumPy >=1.26。
- [pyproj 3.8.0](https://github.com/pyproj4/pyproj/blob/3.8.0/pyproject.toml)：Python >=3.12。
- [GeoPandas 1.2.0](https://github.com/geopandas/geopandas/blob/v1.2.0/pyproject.toml)：Python >=3.11，NumPy >=2，pandas >=2.2，pyproj >=3.7，Shapely >=2.1，pyogrio >=0.8。
- [R5py 1.1.7](https://github.com/r5py/r5py/blob/v1.1.7/pyproject.toml)：Python >=3.10，并引入 JPype、GeoPandas、rasterio 等较重依赖。
据此选择 Python 3.12 作为首次兼容性验证目标；这是本项目方案，非声称已验证当前消费者运行时。
精确包版本锁、wheel 平台可用性、GEOS/PROJ/GDAL/JVM 组合及漏洞审计留在接入验收门，不伪造 lockfile。

## 核验范围
已完成仓库元数据、关键 README、接口文档、选定版本依赖声明及关键许可原文的桌面核验。
未执行安装、性能基准、在线生产查询、安全漏洞全量扫描或德国覆盖率采样。所列版本是调查证据，不是已经通过测试的依赖清单。
