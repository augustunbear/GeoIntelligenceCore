# ADR-0003：开源能力选型与接入边界

日期：2026-11-04。
状态：根据用户“完成详细调研并形成最终选型和最佳接入方案”的请求形成的工程选型基线；生产启用仍须满足验证条件，未声称已实现或测试。
前置：ADR-0001 独立共享包；ADR-0002 通用核心、可选配置与用途模板。

## 选择
- 基础契约：Pydantic 2 与标准库；Shapely＋pyproj 作为可选 geometry。
- 网络适配：HTTPX；Photon 地址；ORS 路线/等时圈（新 HeiGIT 地址）；Overpass POI。
- 批量/统计：pyosmium 可选 PBF；GeoPandas＋pandas＋pyogrio；官方 Zensus/BKG 数据按用途使用。
- 时间：opening_hours_py 可选解析；公交采用独立环境 R5py 及配套 JAR、GTFS validator。
- 调用方地图：MapLibre；已有 Leaflet 不强制迁移。
- 自有薄层：来源/质量/配置/模板/实体核实/比较快照，不重造地理算法。
- 暂不采用默认 PostGIS、H3、OSMnx；QGIS 仅人工 QA；不嵌入上游服务器或复制仓库。

## 选择边界
库/引擎确定不等于生产 endpoint/服务合同已确定。Photon 生产实例和瓦片提供者按具体使用权配置；没有实例即未配置，不偷偷依赖 demo。
ORS 当前完整 ToS/配额本次抓取无正文，官方近期回复提供部分商用与 CC-BY-SA 依据，生产前必须核实全部条件。
不使用公共 Nominatim 联想；不使用已经移除的 OTP TravelTime API；R5py 等时线不等于可直接叠加的区域面。
Python 3.12 是首次验证目标；版本表是观察快照，不是已通过兼容测试的锁文件。

## 理由与替代
Photon 匹配地址联想需求；Pelias 留作多源地址质量不足时替换。
ORS 提供所需道路分析组合；Valhalla 留作自托管替代。
GeoPandas 路线保留离线统计，数据库非必要；PBF 保留可控批量数据路线。
R5py 的矩阵分析适合公交区域研究；OTP 适合其他行程服务而不是使用旧等时圈接口。
不承诺一个库能解决企业人数、购买力或实时人流资料缺失。

## 证据与验收
[详细调研](../../research/OPEN_SOURCE_SELECTION.md) 包含逐功能矩阵、来源及替换条件。
[核验快照](../../research/OPEN_SOURCE_VERIFICATION_2026-11-04.md) 记录 31 项候选。
[接入方案](../INTEGRATION_BLUEPRINT.md) 的 A01—A11 是启用前验证门，结果尚未执行。
