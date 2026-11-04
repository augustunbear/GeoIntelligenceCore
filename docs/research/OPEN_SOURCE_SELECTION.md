# 开源库详细调研与逐项选型

调研日期：2026-11-04。适用：GeoIntelligenceCore 通用核心与餐饮首个配置。
基线：[功能设计](../design/FUNCTIONAL_DESIGN.md)、[ADR-0002](../architecture/adr/ADR-0002-generic-core-industry-profiles.md)。
配套：[31 个项目版本/维护快照](OPEN_SOURCE_VERIFICATION_2026-11-04.md)、[最佳接入方案](../architecture/INTEGRATION_BLUEPRINT.md)。

## 使用规模与人口分析取舍（用户确认，2026-11-04）

系统面向受控使用者，不完全向大众开放，调用次数可控。容量规划以实际受控调用量为依据，不为假设中的公开高并发预先自建地理集群、分布式队列或批量全球数据管线。
优先使用适合小规模的现有服务，并设置应用级总量、并发、单次范围和费用上限；具体数值在实施规划中按实际需求确定，不虚构调用规模。
低调用量不自动代表可使用任意公共服务。公共/演示实例如条款允许实际用途且接受其可用性限制，可以显式配置用于受控轻量使用；不默认绑定、不绕过限制，保留手工/合法旧资料回退。专用托管或自建仅在实际质量、稳定性或额度不足时评估。

人口分析是可选能力，按实际价值与总成本取舍，不作为核心闭环或三个餐饮模板的必需前提：
- POP-01：已有合法行政区人口或用户资料的展示/引用，可在低成本且有实际用途时提供；标注年份、区域和来源，不说成门店可达范围人口。
- POP-02：自定义范围的网格人口汇总，降为低优先级；只有在资料获取、维护和误差解释成本合理时再做。
- POP-03：R5py 公交范围人口估算、复杂网格旅行时间计算或等时线转面后人口叠加，最低优先级，首批不做；若收益不足可不实现。
以上层级是本次约束下的规划建议，不代表已量化证明人口分析性价比低。评估需比较决策价值、资料/许可、一次性接入、持续更新、计算费用、等待时间、核实成本与不确定性；没有明确使用者或收益时保持停用。
不为人口分析单独引入 JVM/R5py、全国数据更新或额外基础设施。R5py 技术选型保留为条件备选，仅有独立且有价值的公交分析需求时重新评估。
不做人口分析不阻塞地址、周边设施、企业地点发现、基础交通与地理比较。已选择范围内的非人口分析可以完整完成；显式请求了人口却未取得时报告未启用/部分结果，不填零，也不冒称全主题完整。

## 1. 结论与“最终选型”的含义

本次确定用于实施规划的首选技术路线，不再把所有候选平铺交给开发者重新选择。
“确定选型”不表示已安装验证、可不限量调用、已获得商用数据许可或已批准采购/部署。
库/引擎选择与生产数据服务开通分开：前者可在本次定案，后者必须满足具体实例、许可、配额和质量验收。
若验收不通过，按本文件明确的替换条件选择备选并记录变更，而不是静默降级。

选型原则：功能语义匹配优先；Python 集成与离线计算优先；公共数据与服务条款分开；保持依赖小；数据质量可解释；拒绝复制整个第三方仓库。
评分不使用缺乏基准的数字“成熟度”。维护判断来自发布和活动证据，性能结论需实测。

## 2. 首选组合

| 能力 | 确定首选 | 使用方式 | 决策理由 |
|---|---|---|---|
| 契约、配置校验 | Pydantic 2 | 核心包依赖 | 严格验证与 JSON Schema，减少契约漂移 |
| 几何/空间关系 | Shapely 2 | geometry 可选依赖组 | 复用 GEOS 运算，不自研相交/合并算法 |
| 坐标/测地计算 | pyproj | 与 geometry 同组 | 显式投影、轴顺序和测地距离 |
| HTTP 访问 | HTTPX | providers 可选依赖组 | 统一连接、超时和可测试传输 |
| 地址联想/反查 | Photon | 可配置 HTTP 适配器 | 本项目地址体验所需能力直接匹配 |
| 步行/骑行/驾车 | openrouteservice | 可配置 HTTP 适配器 | 路线、矩阵、等时圈可用同一服务体系 |
| 周边设施 | Overpass JSON | HTTPX 薄适配器 | 精确查询 OSM 类别，保留源标识与标签 |
| 区域文件批量导入 | pyosmium | 可选离线导入工具 | 规模化时使用区域 PBF，避免公共 API 批量扫描 |
| 人口/区域统计 | GeoPandas＋pandas＋pyogrio | statistics 可选组 | 空间连接、矢量读取和表格统计 |
| 营业时间 | opening_hours_py | temporal 可选组 | 解析 OSM 表达式，避免自研语法；需验证地区假日 |
| 公交区域分析（暂缓启用） | R5py 1.1.7 技术路线保留 | 有独立需求后才启用的可选环境 | 矩阵和等时圈适合区域研究，不给基本包强加 JVM |
| GTFS 检查 | MobilityData gtfs-validator | 离线工具 | 检查 feed 结构；不把 validator 当路由器 |
| 疑似重复排序 | RapidFuzz | 可选辅助 | 仅生成候选；身份判断和审查规则由我们负责 |
| 地图 | MapLibre GL JS | 调用方前端 | 地图交互不进入 Python 包 |
| 来源/质量/模板/快照 | 本项目自有薄层 | 复用上述基础件 | 这是业务无关的组合语义，没有必要采购通用大平台替代 |

首批不引入 PostGIS、H3、OSMnx、QGIS 到运行时；不同时部署 Photon、Pelias、ORS、Valhalla、OTP 全套服务器。

## 3. 功能到库的完整映射

| 需求 | 直接复用 | 我们必须补充 | 回退与验收 |
|---|---|---|---|
| F-01 地址与位置 | Photon；Pydantic；调用方 MapLibre | 候选/入口确认、位置版本、来源与语言回退说明；地图链接仅解析获准支持的格式 | 手工坐标/选点；歧义不得自动第一名；门牌/变音符/同名城市样本验证 |
| F-02 范围与关系 | Shapely、pyproj；ORS；可选 R5py | 地理圆、路网范围、行政边界明确分类；跨日期变更与纳入规则 | 无路线时 unavailable；用户显式选择直线范围；边界设施/反经线/无效几何验证 |
| F-03 交通可达 | ORS；Overpass 站点/停车；GTFS validator＋R5py | 起终点入口、单位、班次定义、时间条件、无障碍/实时能力声明 | 无 GTFS 只报告站点；不伪造频率/空位/安全路线 |
| F-04 POI 搜索 | Overpass；pyosmium；Shapely STRtree；可选 RapidFuzz | 分类映射、跨源实体关联、疑似重复审查、状态冲突 | 超时保留合法旧结果并标龄；同址不同店不合并 |
| F-05 企业环境 | F-04 基础；获准企业表格导入 | 法律主体/营业网点/员工规模适用范围、覆盖率 | OSM 不能补齐员工数；无资料保留未知；不宣称完整企业名录 |
| F-06 人口家庭 | GeoPandas、pandas、pyogrio、pyproj、Shapely；Zensus 文件 | 读取各表元数据、缺失码、年份、网格构造、分配法、分母与误差 | 网格部分重叠标估计；禁止人口与工作人口相加 |
| F-07 时间/人流 | datetime/zoneinfo 标准库；opening_hours_py；pandas | 地点时区、假日区域、计数单位、观测期间/缺测定义 | 无时间或语法不支持返回 unknown；未知开门状态不是关门 |
| F-08 比较/覆盖 | Shapely union/intersection；GeoPandas 汇总 | 口径可比性、原始分项、联合范围统计与质量比较 | 先合并区域再汇总网格；不累加重叠统计；不生成最佳地点分数 |
| F-09 变化/监测 | 标准库 JSON/hashlib；现有空间运算 | 稳定实体关联、快照元数据、现实/数据/方法变化分类 | 数据消失不等于停业；调度/通知由调用方负责，不引入队列框架 |
| F-10 证据与核实 | Pydantic；标准库时间/标识 | 来源、权限、覆盖、冲突、核实事件和版本关系 | 原始记录不被人工修正覆盖；证据缺失时不提升质量 |
| F-11 状态/恢复 | HTTPX timeout/limits/mock transport | 统一异常、Retry-After、有限重试、总期限、额度与部分结果策略 | 区分 disabled/unconfigured/unsupported/rate_limited/unavailable/no_results/有效零；不自动乱换供应商 |
| F-12 展示/导出 | MapLibre；JSON/CSV；可选 GeoPandas 文件输出 | 可追溯摘要、图层元数据、三语言说明、字段级导出约束 | 无底图仍可显示列表；受限字段删除需提示；CSV 导出防公式注入 |
| F-13 配置/模板 | Pydantic＋版本化 JSON＋标准库资源加载 | 独立 industry profile / use-case template、覆盖与能力检查 | 强制限制和数据权利优先；显式参数再覆盖模板默认；未知版本拒绝/迁移 |
| T-01 周边环境 | F-01—F-07、F-10—F-13 | 主题组合与完整性说明 | 不同主题使用的范围明确展示 |
| T-02 商户发现 | F-01/F-02/F-04/F-10—F-13 | 餐饮类别与候选筛选 | 候选不称为直接竞争对手 |
| T-03 地点比较 | F-08 与各单点结果 | 固定比较条件 | 数据不齐不得以零排名 |

G-01—G-10 是所有适配器共同验收规则，V-01—V-08 是跨行业契约用例。它们不是再寻找一套新库来解决的功能。

## 4. 主要选择的深入比较

### 4.1 地址：Photon 优先，Pelias 备选，公共 Nominatim 排除
Photon 提供输入联想、容错、多语言、区域限制、结构化地址与反查；已读 README 和 API 文档 [S01]。
它基于 OpenSearch；当前 README 要求 Java 21+。全世界数据的存储和内存负担较大，所以不将自建全球服务作为初始必需条件。
其演示实例会限制高用量且不保证可用性；选 Photon 引擎不等于选演示实例作生产后端。
受控轻量使用路径：在明确核实用途与用量符合实例条款、接受无可用性保证并配置总量限制后，可显式选择公共/演示实例；否则使用获准受管理实例。没有可用实例时保留手工确认，自动地址能力为未配置。自建德国范围实例是需要容量和运维决策的替代，不在核心中隐式启动。
Pelias 擅长多源地址，支持独立数据导入，但组件与 Elasticsearch 运维增加负担 [S02]。只有德国样本明显表明 Photon 不能满足门牌/名称需求，才换到获准托管 Pelias；不预先部署两套。
公共 Nominatim 的政策明确禁止 autocomplete，且限制系统性 POI 获取；不作为联想或 POI 回退 [S03]。自建 Nominatim 的能力/条款另议。
geopy 只是客户端包装，不能解决本项目证据/契约问题；初期直接适配 Photon，减少间接版本依赖。
不凭供应商顺序生成匹配概率；缺少校准分数时输出精度类别、缺失字段与人工确认状态。

### 4.2 路由：ORS 优先，Valhalla 为自托管替换路径
ORS 同时覆盖路线、矩阵和等时圈；经 HTTP 隔离服务运行时，不把 Java 后端装入 Python 库。
必须使用新地址 api.heigit.org/openrouteservice/v2，旧 api.openrouteservice.org 已公布在 2026-11-02—06 关闭 [S04]。服务器根地址和路径可配置，不能依赖 HTTP 重定向携带密钥。
官方近期回复确认 Standard 商用可用，同时说明结果为 CC-BY-SA 4.0 [S05]。旧页面/第三方资料中的 CC-BY 4.0 不作为当前依据。
当前完整 ToS/套餐页可打开但抓取没有正文，旧官网条款链接返回 404。因此本次不声称已核实完整缓存、派生报告义务或准确日配额；生产启用必须补存当时完整条款和账户额度。论坛回复不是完整合同替代。
不让路线供应商代算人口作为本项目默认人口结果：本项目统一使用选定统计资料与年份。
Valhalla MIT 引擎为需要独立运维/更高调用规模时的备选 [S06]；OSRM 优秀的路线矩阵能力并不直接匹配本项目所有等时圈要求，暂不选择。
另须区分向外 outbound 与到店 inbound，及 depart-at/arrive-by；不支持的方向/时刻能力明确拒绝，不把向外范围当作客源到店范围。
无实时路况资料不声称实时；无障碍 profile 也不是现场通行保证。路由网数据版本未知时保留 unknown。

### 4.3 POI：Overpass 薄适配器；批量使用 PBF
小区域通过 HTTPX 发送经过模板化限制的 Overpass JSON 查询，取 nodes/ways/relations，保留 type+id、tags、时间与几何精度。
查询语言使用固定类别映射与经过验证的区域，不接受任意用户脚本。需要入口/面积精确关系时取实际几何；仅有 center 时标为近似，不能声称是真入口。
公共实例是共享资源，有负载保护 [S07]。禁止通过轮换公共实例规避限制；不能把“每个用户少量请求”误当整个应用无限量。
用户触发的小查询可在政策允许且额度预算内使用；持续批量/监测用获准实例或 Geofabrik 区域 PBF＋pyosmium [S08]。
pyosmium 处理 ways/relations 需要节点位置与面积组装；仅解析 tags 不能满足空间判断。
不引入 overpy/OSMnx 作为线上核心依赖：本项目只需要受控 JSON 查询，通用包装并不能提供跨源去重和质量解释。
同源 type+id 可精确关联；跨源先做空间阻塞，再按名称/地址候选匹配，RapidFuzz 仅排序。门牌、分店、入口和经营状态冲突留给核实。

### 4.4 几何和统计：Shapely＋pyproj，GeoPandas 做可选批量层
Shapely 是平面几何工具，pyproj 负责投影与测地计算，不能在经纬度坐标上直接 buffer(1000) 作为 1000 米 [S09/S10]。
接口统一经纬度顺序；投影转换显式 always_xy，保留原 CRS。局地距离可选择适合区域的投影；地理圆用测地方法；德国网格统计优先遵守数据原 CRS/等积计算要求。
GeoPandas 提供批量叠加/连接，pyogrio 读矢量文件 [S11]。标准 CSV 不需要先转成 GIS 服务器才能处理。
Zensus 2022 官方提供网格 CSV 和元数据 [S12]。逐个主题读取说明；不能假设所有指标、网格或缺失码相同。
BKG VG250 可做行政区统计边界，但其比例尺不适合门口级边界判定 [S13]。边界附近结果需解释或使用更高精度获准数据。
暂不引入 H3：它不会提供人口，且将原生网格换成六边形会新增估计。PostGIS 只在数据规模、持久化与并发使数据库空间索引有实际收益后启用。

### 4.5 公交：R5py，不能照搬 OTP 2.5 等时圈教程
GTFS 是数据格式不是全国数据授权。使用 DELFI 或当地交通机构发布的获准 feed，保存许可、覆盖日期和版本 [S14]。
先用 MobilityData validator 检查文件，再按 service calendar、exceptions、agency timezone 和超过 24:00 的时刻处理班次。静态 GTFS 不代表实时运行。
R5py 支持 TravelTimeMatrix 和 Isochrones，符合区域分析用途 [S15]；JDK 21+ 及较重 Python 依赖放在独立可选环境。
R5py 1.1.7 默认使用 r5py/r5 的 v7.5.1-r5py JAR，并在源码声明 SHA-256；不能直接换成 Conveyal 最新 v7.6 [S16]。
R5py Isochrones 返回 MultiLineString 等时线，不是可直接人口叠加的完整区域。首选统计路径是对明确网格/目标点计算时间，再按阈值选取并报告采样估计；展示线保留原形态。若提供面，必须另外验证闭合、孔洞、离岛与分辨率误差，不能随意凸包填满河流/障碍。
保留 departure、time window、percentile、grid resolution、采样参数。默认中位数不是某一秒的精确出行时间。
OTP 2.5 文档仍能搜到 TravelTime API，但新版本 changelog 已记录移除 [S17]；不为一个旧接口固定过时版本。OTP 作为未来行程规划服务备选，不是本项目等时圈首选。

### 4.6 营业时间、地图与通用工具
opening_hours_py 是 Rust 解析器的 Python 绑定，支持 OSM 表达式、时区及假日相关能力 [S18]。本项目必须验证德国州级 PH、跨夜、DST、日出日落、unknown 和非法表达式；若库不能可靠提供上下文，返回未知而不按普通工作日计算。
不在 Python 中用 Node 子进程包装 opening_hours.js；后者可用作语义对照样例。解析成功不证明现实营业资料新鲜。
MapLibre 只用于调用方前端；公开接口仍输出 GeoJSON 与普通属性，不强制消费者改用 MapLibre。
Leaflet 已有应用可以保留。瓦片、字体、样式许可与地图渲染代码许可分开；不把 OSM 公共瓦片当作有 SLA 的默认商用底图 [S19]。
Pydantic 做严格边界验证和配置结构，不能替代空间有效性检查 [S20]。
HTTPX 本身的连接重试不自动处理所有 429/503；本项目单独实现按来源规定的有限恢复 [S21]。
快照用稳定规范化序列化与明确方法版本，不用通用 JSON diff 直接宣称现实变化；分类/证据/核实语义自行设计是必要组合工作，不是重造 GIS 算法。

## 5. 数据与能力缺口：不以“有库”冒充“有数据”

| 目标资料 | 首选来源路线 | 当前限制与决定 |
|---|---|---|
| 道路、设施、地址 | OSM，按需要 Photon/Overpass/Geofabrik | 覆盖不均；需 ODbL 归属和数据使用评估 |
| 人口家庭 | Zensus 官方网格 | 历史统计；保密与缺失；不声称当年人口 |
| 行政区 | BKG VG250 | 官方统计区用途；精度与年份限制 |
| 公交时刻 | DELFI/当地 GTFS | 注册/许可、时间覆盖、质量逐 feed 验证 |
| 企业员工规模 | 用户获准文件或明确授权的企业来源 | 尚无已核实的统一开源替代；状态为未知/未配置 |
| 购买力、实时空位、实时人流 | 用户或获准供应商 | 本次不选择未经验证的商业产品，不生成推测数值 |
| 入口、无障碍、儿童安全 | OSM 可用事实＋人工确认 | 不以一般道路数据声称全面覆盖 |
| 地图底图 | 调用方获准瓦片源 | 渲染库已选，具体供应商不由 Python 库强制指定 |

来源切换必须保留数据和口径差异。绝不将 Google/商业来源混入 OSM 数据库并据此认为可自由分发。

## 6. 版本、维护、许可和安全结论

31 个候选的活动与发布信息见核验快照。主选多数存在近期发布/推送；HTTPX Release 较旧但仓库有后续活动，不能只按发布日期淘汰；Overpass 同样要区分 release 记录与实例实际版本。
目标首次验证环境为 Python 3.12；pyproj 3.8.0 要求 >=3.12，GeoPandas 1.2.0 与 Shapely 2.2.0 的声明在元数据层可兼容。消费者若仍为 3.11，必须单独评估兼容版本或消费者升级，不能静默抬高要求。
安装包从上游发行渠道依赖，不复制源码；可选模块独立安装，导入基础包不联网、不启动 JVM、不下载数据。
代码许可、打包依赖、地图数据、网络服务条款分别记录。GPL/AGPL 后端可经独立服务接口使用，但这不自动免除部署/修改/分发义务，也不意味着我们的整库自动变成 GPL；按实际分发方式核实。
主选许可路线：Pydantic MIT，HTTPX BSD-3-Clause，Shapely BSD-3-Clause，pyproj MIT，GeoPandas BSD-3-Clause，pyogrio MIT；底层 GEOS/PROJ/GDAL 等声明也要随分发核对。
本次未做漏洞全量扫描，不标记“无漏洞”。接入前产出锁定版本、哈希、依赖清单与漏洞检查结果；不可下载未校验 JAR 或允许任意 URL/脚本作为配置。

## 7. 明确的替换条件

- Photon 德国测试集无法覆盖关键门牌/名称需求：同样测试集对比 Pelias，记录差异后改地址适配器，不改通用结果契约。
- ORS 配额/条款/延迟不满足：先调整获准服务方案；需要自托管时评估 Valhalla，不转到不受限公共端点。
- Overpass 无法支撑批量/稳定性：改区域 PBF 输入或获准托管实例，共用归一化与去重层。
- 本地统计超出测定资源预算：分区读取和空间索引优先，再评估 PostGIS；不按推测提前建数据库。
- opening_hours_py 的关键语义失败：保留原始字符串并返回 unknown；替换解析器需一致性验证。
- R5py 不能满足区域或运行预算：暂关闭公交区域能力，仍提供站点/时刻资料；不伪装成驾车或直线范围。
任何变化更新选型记录及验收结果，不依赖调用方解释私有供应商格式。

## 8. 来源索引（本次直接阅读的一手资料）

- S01 Photon：[README](https://github.com/komoot/photon/blob/master/README.md)、[API](https://github.com/komoot/photon/blob/master/docs/api-v1.md)。
- S02 [Pelias README](https://github.com/pelias/pelias/blob/master/README.md)。
- S03 [OSMF Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/)。
- S04 [ORS 域名迁移公告](https://ask.openrouteservice.org/t/deprecating-api-openrouteservice-org-in-favour-of-api-heigit-org/7912/)。
- S05 [2026-10 官方商用/CC-BY-SA 回复](https://ask.openrouteservice.org/t/free-plan-in-an-app-with-a-paid-tier-license-cc-by-sa-4-0-personal-data-and-attribution-questions/8079/)、[当前 ToS](https://account.heigit.org/info/tos)、[当前套餐](https://account.heigit.org/info/plans)。后两者本次无可读正文，不作为完整核实证据。
- S06 [Valhalla COPYING](https://github.com/valhalla/valhalla/blob/master/COPYING)。
- S07 [Overpass 资源规则](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html)。
- S08 [Geofabrik Germany](https://download.geofabrik.de/europe/germany.html)、[pyosmium 官方项目](https://osmcode.org/pyosmium/)、[OSM 数据许可](https://www.openstreetmap.org/copyright)。
- S09 [Shapely manual](https://shapely.readthedocs.io/en/stable/manual.html)。
- S10 [pyproj Geod](https://pyproj4.github.io/pyproj/stable/api/geod.html)、[axis 示例](https://github.com/pyproj4/pyproj/blob/main/docs/examples.rst)。
- S11 [GeoPandas projections](https://geopandas.org/en/stable/docs/user_guide/projections.html)、[v1.2.0 依赖](https://github.com/geopandas/geopandas/blob/v1.2.0/pyproject.toml)。
- S12 [Destatis Zensus 网格下载说明](https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/Zensus2022/_publikationen.html)。
- S13 [BKG VG250 产品、精度和引用说明](https://gdz.bkg.bund.de/index.php/default/open-data/verwaltungsgebiete-1-250-000-stand-01-01-vg250-01-01.html)。
- S14 [GTFS 标准](https://gtfs.org/documentation/schedule/reference/)、[DELFI 数据入口](https://www.opendata-oepnv.de/ht/de/organisation/delfi/startseite)、[validator](https://github.com/MobilityData/gtfs-validator)。
- S15 R5py：[矩阵](https://r5py.readthedocs.io/stable/user-guide/user-manual/travel-time-matrices.html)、[等时线](https://r5py.readthedocs.io/stable/user-guide/user-manual/isochrones.html)、[安装](https://r5py.readthedocs.io/stable/user-guide/installation/installation.html)。
- S16 [R5py v1.1.7 的 JAR 与校验值](https://github.com/r5py/r5py/blob/v1.1.7/src/r5py/util/classpath.py)。
- S17 [OTP 当前版本 changelog](https://docs.opentripplanner.org/en/v2.10.0/Changelog/)、[仍可检索到的旧接口文档，仅作反例](https://docs.opentripplanner.org/en/v2.5.0/sandbox/TravelTime/)。
- S18 [opening-hours-rs README](https://github.com/remi-dupre/opening-hours-rs/blob/master/README.md)、[Python 绑定许可](https://github.com/remi-dupre/opening-hours-rs/blob/master/opening-hours-py/Cargo.toml)。
- S19 [MapLibre 许可](https://github.com/maplibre/maplibre-gl-js/blob/main/LICENSE.txt)、[OSMF tile policy](https://operations.osmfoundation.org/policies/tiles/)。
- S20 [Pydantic JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/)。
- S21 HTTPX：[timeouts](https://www.python-httpx.org/advanced/timeouts/)、[transports](https://www.python-httpx.org/advanced/transports/)。

本报告中的选型、分层和验收设计是基于上述资料的工程判断；源文档功能声明不等于本项目已实测。
