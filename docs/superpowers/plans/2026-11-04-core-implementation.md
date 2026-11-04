# 通用地理情报核心分步骤 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付可独立安装、行业无关、具备餐饮配置与三个用途模板的首版地理事实库，再按明确价值和数据条件扩展。

**Architecture:** Python包先行，基础契约/手工能力无需联网；几何与来源适配按需安装。所有输出经过状态、证据、权限和可比性处理，调用方管理界面、权限、持久化和调度。保留单项调用，不强制通过行业模板。

**Tech Stack:** Python 3.12首次验证目标；Pydantic 2；可选Shapely/pyproj、HTTPX；Photon/Overpass/ORS适配。其他选型按后续任务启用，观察版本不是锁版本。

**Spec:** [功能设计](../../design/FUNCTIONAL_DESIGN.md)、[V1目标契约](../../contracts/V1_CONTRACT.md)、[接入方案](../../architecture/INTEGRATION_BLUEPRINT.md)、ADR-0001/0002/0003。

基于2026-11-04实际读取的main：`99bce3d90186acf8a431896341ab95fc66708ac7`（PR #1已合并）；开始规划时开放PR为空，仓库仅有文档。本文新增代码路径均为**未来创建目标**，不是已存在实现。计划提交不代表开发、测试、发布或部署已完成。

## Global Constraints

- 核心保持行业无关；行业配置与用途模板独立版本。首先提供餐饮类别和三个模板；零售、教育仅验证通用性。
- 系统面向受控使用者，不完全向大众开放，调用次数可控。
- 最小基础包：Pydantic＋标准库；不需要密钥/数据库/云账号，导入不得联网或启动JVM。
- 数据权利/调用方强制约束 > 合法显式参数 > 模板可覆盖默认 > 行业基础默认。
- GeoJSON WGS84 [longitude, latitude]；距离米、持续时间秒、UTC时间戳与IANA当地时区分开。
- 未知不等于零；来源/几何/方向/时间/年份不静默切换；部分成功不丢弃有效主题。
- 私有补充、原始证据、人工核实分别保留；导出和保存遵守逐源权限。
- 不输出经营因果、竞争结论、综合分数、收益或客流推断。
- 人口可选；POP-01条件引用、POP-02低优先级、POP-03最低且首批不做。不为人口引入R5py/JVM。
- 不使用真实客户/密钥/受限商业资料作git fixture；不新建公众服务、数据库集群或常驻队列。
- 每个实施任务走功能分支/PR、实际验证和独立审查；合并/发布/部署以用户明确授权为准。本文仅规划。

## Review Focus

1. 同址不同商户、学校多入口不能被误合并或强制餐厅字段：P01/P06/P09测试。
2. 预算最后一次额度的并发竞争与429重试，不能突破应用总额：P04测试并在P13验证部署拓扑。
3. 单行路的入向/出向与到达/出发时间不能互换：P07/P08测试。
4. 请求人口但能力停用、来源半失败不能变0或全成功：P02/P09/P11测试。
5. 人工私有修正、模板更新、受限导出不得污染其他客户或历史快照：P09/P10测试。

---

## 1. 执行顺序与首批边界

| 阶段 | 步骤 | 可独立验收的交付 |
|---|---|---|
| 基础 | P01—P04 | 离线确认、公共契约、几何、受控调用基础 |
| 单项能力 | P05—P08 | 地址候选、设施/企业地点、路线矩阵、路网范围 |
| 使用闭环 | P09—P11 | 餐饮T-01/T-02/T-03、证据、三语导出、同口径比较 |
| 交付验证 | P12—P13 | 可安装包、消费者示例、真实启用与质量记录 |
| 后续 | E01—E07 | 时间/实测、历史、导入、资料深化、批量、公交、真实消费者 |
| 人口 | POP-01—POP-03 | 各自通过成本收益与权利门后启用；不阻塞首批 |

严格依赖见各任务；P05/P06/P07共享P04但不互相依赖。P13的许可/配额与需求收集可提前进行，mock实现不等许可审批。首版完成定义是P01—P12离线契约通过、P13对每项启用能力给出真实结论；不要求把未配置来源伪装可用。若无线上合格来源，只交付明确标注的离线/预览包，不宣称线上生产就绪。

不承诺工期：先完成P01—P04后按真实接口、安装和来源质量更新估算，任务范围变化另记PR。每个P步骤建议一个可审查PR；跨步骤公共契约变化先协调再改消费者。

## 2. 文件责任与接口

详细字段和统一签名以[V1_CONTRACT](../../contracts/V1_CONTRACT.md)为唯一目标定义。旧ARCHITECTURE布局只是早期示意，由本文替代文件划分。各任务中的大括号表示明确列出的多个文件，不是实际文件名。

| 路径 | 单一责任 |
|---|---|
| src/geo_intelligence_core/models/ | 不可变公共Pydantic类型、状态、证据、请求和结果 |
| location.py / geometry.py / places.py | 手工确认、本地空间运算、设施归一分别独立 |
| ports.py / providers/ | 端口协议、统一受控HTTP、具体来源适配；不泄露vendor类型 |
| configuration.py / analysis.py | 有效参数解析、主题能力预检与执行 |
| evidence.py / export.py / comparison.py | 核实与保留、合法输出、同口径比较 |
| data/categories/、mappings/、profiles/、templates/、locales/ | 通用分类、来源标签、行业默认、用途组合、三语各自版本化 |
| tests/unit/、contract/、integration/、packaging/ | 离线行为、公共契约、opt-in真实源、安装验证 |
| requirements/、schemas/v1/ | 实测依赖锁与生成JSON Schema，不手写假锁 |
| docs/usage/、operations/、verification/ | 消费方式、启用要求、实际验收结果 |
| statistics/、transit/、inputs/、temporal.py、history.py | 后续任务才创建，不预建空目录 |

公共Result含schema_version/status/data/issues/evidence/context；Result[Analysis]内部为每个selected topic的Result。每个重要值有来源，unknown与有效零值不同。所有示例使用合成数据。

### 验证与提交的共同约定
每任务下面的五步是实际执行顺序。测试描述中的名称和断言必须落到同名pytest测试；第一次因缺实现失败后，再实现最小通过逻辑。不得把所有测试统一标pass或只写文档。
P01引入pytest、Pydantic、build及锁定工具；后续沿用已经建立的命令。测试fixture在tests/conftest.py定义明确类型的合成工厂，模拟时钟/HTTP transport/预算，绝不依赖真实HTTP。
每次任务提交只stage该任务明确修改的文件，更新状态中的实际证据。下面git命令中的文件列表取该任务Files，不用git add .混入无关修改。测试首次收集ImportError仅是缺模块的红灯，后续还需验证行为断言真正能检出错误实现。

## 3. 首批工作项

### P01：可安装核心与离线地点确认

**关联：** F-01/F-10/F-11；G-01/G-02/G-03/G-08；V-01/V-07；A01。
**依赖：** 无。
**Files：** pyproject.toml; src/geo_intelligence_core/__init__.py; src/geo_intelligence_core/models/{common,evidence,location,requests,policy}.py; src/geo_intelligence_core/location.py; tests/conftest.py; tests/unit/test_location.py; tests/contract/test_core.py; .github/workflows/test.yml; requirements/core-py312.lock; CHANGELOG.md。

**Interfaces / 可见交付：** 输入 ConfirmRequest、可选 previous Location；输出 Result[Location]。实现 V1_CONTRACT 的 confirm_location；初次 version=1，修正 previous.version+1。仅基础 Pydantic/标准库，不提供搜索。

**边界、资料与失败处理：** 确认动作由调用方明确发起；未确认搜索结果不可作为已确认地点。无服务仍能完成此闭环。

- [ ] **1. 写失败测试。** test_manual_confirmation_without_industry：手工坐标+依据得到 ok/version=1；修改入口得 version=2，原对象不变。test_ambiguous_candidate_not_confirmed：未指定候选不得产生 Location。test_bad_coordinates：NaN、Inf、超界、bool 被拒绝；(longitude=11,latitude=49) 保持原序。test_import_offline：清空密钥、禁网、无 geometry/providers 包仍能 import/确认。
- [ ] **2. 验证失败。** 运行 `python -m pytest tests/unit/test_location.py tests/contract/test_core.py -q`；未实现阶段预期FAIL，确认失败源于缺失行为而非测试配置。
- [ ] **3. 实现。** 按契约实现不可变模型、验证和手工确认；基础安装/开发依赖实际解析并生成含哈希锁；建立 pytest 离线网络阻断 fixture、合成数据工厂和 schema round-trip。CI 只跑本任务已存在测试。包名 geo-intelligence-core，导入名 geo_intelligence_core，初始开发版本 0.1.0a1；首次支持 Python 3.12，消费者兼容性另验。
- [ ] **4. 验证通过。** 重跑同一命令，预期全部目标用例PASS；运行已有受影响契约回归。P13的live skip/blocked必须如实记录，不算PASS。
- [ ] **5. 提交并独立审查。** `git add <本任务实际变更文件>`，`git commit -m "feat: add installable core and manual location confirmation"`；PR列出验收证据、权利/覆盖限制与未启用能力。

### P02：结果、权限、配置与能力预检

**关联：** F-10/F-11/F-13；G-01—G-09；V-07/V-08；A09。
**依赖：** P01。
**Files：** src/geo_intelligence_core/models/{configuration,analysis,spatial,places}.py; src/geo_intelligence_core/configuration.py; src/geo_intelligence_core/ports.py; tests/unit/test_configuration.py; tests/contract/test_schemas.py; schemas/v1/{location,result,analysis,profile,template}.json。

**Interfaces / 可见交付：** resolve_config(AnalyzeRequest, Profile|None, Template|None, UsagePolicy) -> Result[EffectiveConfig]；ProviderRegistry 以 capability ID 注册端口。先实现模型与预检，不执行空壳 analyze。错误状态与聚合规则采用契约第2节。

**边界、资料与失败处理：** 无效配置不联网。未知权利不允许保留/缓存/导出；使用权限必须与用途匹配。

- [ ] **1. 写失败测试。** test_precedence：模板半径1000、显式500、policy最大800 =>有效500并记录来源；显式900 =>invalid_input而不是裁成800。test_missing_capability：必需未配置=>unconfigured且fake.calls==0；TopicSelection.required与模板required_topics取并集，显式false不得降低模板必需性。test_selected_population_disabled：人口未选不产生错误，显式选但disabled保留原因。test_schema_roundtrip：未知字段/错误类型拒绝，null与0序列化不同。
- [ ] **2. 验证失败。** 运行 `python -m pytest tests/unit/test_configuration.py tests/contract/test_schemas.py -q`；未实现阶段预期FAIL，确认失败源于缺失行为而非测试配置。
- [ ] **3. 实现。** 实现配置/模板独立版本、字段覆盖白名单、权利和强制上限优先级，语言值限定de/zh-CN/en。设计时不绑定真实 endpoint，不给网络预算无限默认；生成 JSON Schema 并校验样例。provider 端口签名以更新的契约为准，模型仅随本次验证用途落地。
- [ ] **4. 验证通过。** 重跑同一命令，预期全部目标用例PASS；运行已有受影响契约回归。P13的live skip/blocked必须如实记录，不算PASS。
- [ ] **5. 提交并独立审查。** `git add <本任务实际变更文件>`，`git commit -m "feat: validate capability configuration and result contracts"`；PR列出验收证据、权利/覆盖限制与未启用能力。

### P03：本地测地距离、区域与空间筛选

**关联：** F-02/F-08；G-03/G-05/G-08；V-02/V-07；A03。
**依赖：** P01/P02。
**Files：** src/geo_intelligence_core/geometry.py; tests/unit/test_geometry.py; requirements/geometry-py312.lock; docs/usage/geometry.md; pyproject.toml。

**Interfaces / 可见交付：** distance_m(Point,Point)->float；circle(CircleRequest, *, limits: GeometryLimits)->Result[Region]；combine(list[Region],SpatialOperation, *, limits: GeometryLimits)->Result[Region]。Region 支持合法 Polygon/MultiPolygon 和边界规则；输入行政边界必须带来源版本，此步不自动下载边界。

**边界、资料与失败处理：** 只称直线范围/指定区域，不推断道路可达性。geometry extra 缺失时核心仍可导入。

- [ ] **1. 写失败测试。** test_geodesic：赤道(0,0)到(1,0)约111319.49m，误差<=1m；同点为0。test_boundary：方形(0,0)-(1,1)边界点covers=True、within=False。test_union：两个面积4、重叠2的合成投影方形联合面积6。test_invalid_or_unsupported：自交、反经线跨越、极区、大于policy范围明确invalid_input/unsupported，不自动凸包。test_circle：生成顶点距中心误差<=1m，绝不标walk。
- [ ] **2. 验证失败。** 运行 `python -m pytest tests/unit/test_geometry.py -q`；未实现阶段预期FAIL，确认失败源于缺失行为而非测试配置。
- [ ] **3. 实现。** 复用 pyproj.Geod/Transformer(always_xy=True)、Shapely 空间关系；本次支持不跨反经线且纬度绝对值<=80的局部面运算，超出明确unsupported并写文档。距离函数可用测地全局点对。面积用适合当地的等面积投影或测地面积，环/排除/交并差保持孔洞；单项调用显式传入独立GeometryLimits，分析编排从可信policy派生该值；顶点数量在运算前检查、面积在可估算输入及最终输出检查，不要求离线调用提供网络预算。
- [ ] **4. 验证通过。** 重跑同一命令，预期全部目标用例PASS；运行已有受影响契约回归。P13的live skip/blocked必须如实记录，不算PASS。
- [ ] **5. 提交并独立审查。** `git add <本任务实际变更文件>`，`git commit -m "feat: add explicit geodesic and region operations"`；PR列出验收证据、权利/覆盖限制与未启用能力。

### P04：受控网络、额度与合法缓存通道

**关联：** F-11/F-13；G-05/G-07/G-09；A09/A11。
**依赖：** P02。
**Files：** src/geo_intelligence_core/providers/http.py; src/geo_intelligence_core/providers/budget.py; src/geo_intelligence_core/providers/cache.py; tests/unit/test_http_policy.py; requirements/providers-py312.lock; docs/operations/provider-activation.md; pyproject.toml。

**Interfaces / 可见交付：** HTTPX AsyncClient 通过 HttpGateway.request(provider_id: str, method: str, path: str, params: dict, context: RequestContext)->Result[dict]。构造注入ProviderConfig、UsagePolicy、Budget、clock、transport；Cache.get/put只接收已获retain/cache许可的对象和完整键。

**边界、资料与失败处理：** 生产具体调用量/费用/SLO没有现成证据：启用记录必须填来源条款、账户配额、计划用量、单次范围、并发和花费硬上限。缺任一必需值保持unconfigured；免费服务需记录价格0的依据，不猜账单。网络费用无法估计时拒绝收费调用。

- [ ] **1. 写失败测试。** test_retry_budget：fake budget总2次，连续429后最多2次调用，Retry-After超过总deadline则立即rate_limited。test_concurrent_reservation：两个请求竞争最后1额度，恰好1个出网。test_ssrf_redirect：允许主机重定向127.0.0.1/私网/非HTTPS被拒绝，零后续调用。test_private_cache：AnalyzeRequest.scope_token经RequestContext传播至内部缓存键，scope A不能命中B；私有记录缺scope拒绝缓存；scope不外发；rights unknown/denied不写。test_response_limit：超大响应停止读取，不按空结果返回。test_no_secret_logs：token/原地址不出现日志。
- [ ] **2. 验证失败。** 运行 `python -m pytest tests/unit/test_http_policy.py -q`；未实现阶段预期FAIL，确认失败源于缺失行为而非测试配置。
- [ ] **3. 实现。** 设置有限超时、整体期限、响应流大小、每次重试前原子额度预留；默认关闭重定向，仅管理员白名单显式许可逐跳验证，禁私网解析及环境代理隐式继承。只读白名单查询可重试，401/403/invalid_input不重试；凭据仅运行时注入。提供单进程Budget参考实现，文档明确多worker必须注入共享额度实现，否则不声称应用总量受控。缓存默认关闭，私有scope与来源/版本/语言/参数/方法完整入键；旧资料仅显式选取。
- [ ] **4. 验证通过。** 重跑同一命令，预期全部目标用例PASS；运行已有受影响契约回归。P13的live skip/blocked必须如实记录，不算PASS。
- [ ] **5. 提交并独立审查。** `git add <本任务实际变更文件>`，`git commit -m "feat: bound provider access and enforce data-use policy"`；PR列出验收证据、权利/覆盖限制与未启用能力。

### P05：Photon 地址候选与反查

**关联：** F-01；G-02/G-05/G-08；V-01/V-07；A02。
**依赖：** P01/P02/P04。
**Files：** src/geo_intelligence_core/providers/photon.py; tests/unit/test_photon.py; tests/integration/test_photon_live.py; tests/fixtures/photon/*.json; docs/usage/location.md。

**Interfaces / 可见交付：** PhotonResolver 实现 LocationResolver.search/reverse；消费 HttpGateway，返回 Candidate列表，无自动确认。SearchRequest country_codes/bbox 是硬条件，near只是偏好。

**边界、资料与失败处理：** 无获准实例=>unconfigured。公共轻量实例只能显式配置并记录条款，不自动自建、不绑定demo。实时质量验证在P13。

- [ ] **1. 写失败测试。** test_candidates：两个同名候选返回2个，confirmation不存在；缺门牌精度不标entrance。test_lang：zh-CN不支持时记录所用语言fallback和原名，不能伪称中文全覆盖。test_empty_vs_timeout：空成功为no_results，超时unavailable/data=null。test_query_mapping：按目标服务版本映射q/lang/limit/country/bbox，服务不支持硬过滤时本地过滤或unsupported。test_cancel_stale：取消过时请求后不继续重试。
- [ ] **2. 验证失败。** 运行 `python -m pytest tests/unit/test_photon.py -q`；未实现阶段预期FAIL，确认失败源于缺失行为而非测试配置。
- [ ] **3. 实现。** 薄HTTP适配器，保留来源ID、候选精度和原名；注入版本能力表，禁用旧标签参数的无依据调用。库提供取消和最小查询长度配置，调用方联想防抖；不要自行新增UI。手工回退调用P01。建立可复用德国城市/郊区/乡村、变音符、缺门牌和同名的人工标注样本规范，真实获准样本只在opt-in验证记录中。
- [ ] **4. 验证通过。** 重跑同一命令，预期全部目标用例PASS；运行已有受影响契约回归。P13的live skip/blocked必须如实记录，不算PASS。
- [ ] **5. 提交并独立审查。** `git add <本任务实际变更文件>`，`git commit -m "feat: add configurable Photon location resolver"`；PR列出验收证据、权利/覆盖限制与未启用能力。

### P06：通用类别、Overpass设施与企业地点

**关联：** F-03/F-04/F-05；G-01/G-02/G-03/G-10；V-03；A04。
**依赖：** P02/P03/P04。
**Files：** src/geo_intelligence_core/providers/overpass.py; src/geo_intelligence_core/places.py; src/geo_intelligence_core/data/categories/v1.json; src/geo_intelligence_core/data/mappings/osm-v1.json; tests/unit/test_places.py; tests/unit/test_overpass.py; tests/fixtures/overpass/*.json。

**Interfaces / 可见交付：** OverpassPlaceProvider.search(PlaceQuery,RequestContext)->Result[PlaceSet]；normalize_places(list[Place],PlaceQuery)->Result[PlaceSet]。通用category覆盖餐饮、零售、办公、教育、医疗、住宿、文体、公共服务、交通停车、开放空间。

**边界、资料与失败处理：** OSM来源记录ODbL/归属和覆盖未知；不采购企业人数，不推断办公人数/停车空位/站点班次。未知类别不强塞餐饮。

- [ ] **1. 写失败测试。** test_typed_ids：node/7和way/7不合并；同source/type/id的重复合并且保留证据。test_same_address：同址两店unique_count==2；跨源疑似同店仅标候选。test_partial_remark：带timeout remark且有记录=>partial；无可用记录=>unavailable，不是ok空列表。test_boundary_filter：按P03约定纳入。test_company_site：office记录不是已验证法律主体，workforce=null。test_parking_stop：容量/班次缺失仍null。
- [ ] **2. 验证失败。** 运行 `python -m pytest tests/unit/test_places.py tests/unit/test_overpass.py -q`；未实现阶段预期FAIL，确认失败源于缺失行为而非测试配置。
- [ ] **3. 实现。** 生成白名单类别查询，不接受调用方任意Overpass脚本；按已声明区域限制、最小必要字段、响应大小查询；中心点point_role=representative，不当入口。保留OSM标签/类别映射版本、原几何及合法公开联系字段，确定性同源去重；企业地点、停车和站点只是通用设施视图。检索计数与真实总体分开，开放时间只保留原文此步不解释。
- [ ] **4. 验证通过。** 重跑同一命令，预期全部目标用例PASS；运行已有受影响契约回归。P13的live skip/blocked必须如实记录，不算PASS。
- [ ] **5. 提交并独立审查。** `git add <本任务实际变更文件>`，`git commit -m "feat: discover bounded OSM places with provenance"`；PR列出验收证据、权利/覆盖限制与未启用能力。

### P07：ORS 路线与起终点矩阵

**关联：** F-03；G-03/G-05/G-08；V-02；A05。
**依赖：** P02/P03/P04。
**Files：** src/geo_intelligence_core/providers/ors.py; tests/unit/test_ors_routes.py; tests/integration/test_ors_live.py; tests/fixtures/ors/*.json; docs/usage/routing.md。

**Interfaces / 可见交付：** OrsRoutingProvider.route/matrix实现契约；route显式origin/destination，MatrixRequest保留有序origin/destination IDs，每格独立status。endpoint配置使用经启用核实的新HeiGIT路由。

**边界、资料与失败处理：** 适配器mock可交付；线上启用必须取得完整当前ToS/账户配额/输出归属和报告使用规则。未通过不得标生产可用。

- [ ] **1. 写失败测试。** test_units：供应商秒值保留秒、km明确转m；禁止无单位输入猜测。test_directed_matrix：A到B=600s、B到A=900s，结果不转置；null格不是0。test_no_route：unavailable/unsupported原因可解释，无直线替代。test_time_support：不支持arrive_by的模式在请求前unsupported。test_endpoints：未经允许的旧主机不自动回退。
- [ ] **2. 验证失败。** 运行 `python -m pytest tests/unit/test_ors_routes.py -q`；未实现阶段预期FAIL，确认失败源于缺失行为而非测试配置。
- [ ] **3. 实现。** 通过同一HttpGateway映射步行/骑行/驾车配置、路线几何和矩阵，使用当前已验证API单位与能力；路网时间未知明确unknown。入口由调用方指定，单个路线起终点已定义方向，不通过逆转线模拟相反交通。捕获限流、无覆盖和上游错误。
- [ ] **4. 验证通过。** 重跑同一命令，预期全部目标用例PASS；运行已有受影响契约回归。P13的live skip/blocked必须如实记录，不算PASS。
- [ ] **5. 提交并独立审查。** `git add <本任务实际变更文件>`，`git commit -m "feat: add directed ORS routes and matrices"`；PR列出验收证据、权利/覆盖限制与未启用能力。

### P08：路网可达范围与多圈层

**关联：** F-02/F-03；G-03/G-05；V-02/V-08；A03/A05。
**依赖：** P03/P07。
**Files：** src/geo_intelligence_core/providers/ors.py; src/geo_intelligence_core/catchments.py; tests/unit/test_catchments.py; tests/fixtures/ors/isochrones.json。

**Interfaces / 可见交付：** OrsRoutingProvider.catchments(CatchmentRequest,RequestContext)->Result[list[Catchment]]；每圈返回方向、模式、秒阈值、time和Region。输入direction=inbound/outbound，与depart_at/arrive_by分开。

**边界、资料与失败处理：** 5/10/15分钟仅测试示例，不是全行业默认。无声换直线范围是阻断级错误。

- [ ] **1. 写失败测试。** test_barrier：合成河流阻隔区不被circle替代。test_inbound：provider宣称支持并核对API映射才调用；不支持inbound直接unsupported，不能把outbound改标签。test_nested：300/600/900秒范围不嵌套则标partial/invalid上游结果，不能修成凸包。test_failure：provider失败data=null；本地circle只能新显式请求生成。test_invalid_polygon：坏几何拒绝并保留诊断。
- [ ] **2. 验证失败。** 运行 `python -m pytest tests/unit/test_catchments.py -q`；未实现阶段预期FAIL，确认失败源于缺失行为而非测试配置。
- [ ] **3. 实现。** 以P03验证供应商几何，保留多面/孔洞，阈值请求排序去重且保留实际参数。首批不实现自动采样矩阵推面；某来源不支持入向/到达时间就报告unsupported。圈层差集复用P03，叠加与方法元数据不丢失。
- [ ] **4. 验证通过。** 重跑同一命令，预期全部目标用例PASS；运行已有受影响契约回归。P13的live skip/blocked必须如实记录，不算PASS。
- [ ] **5. 提交并独立审查。** `git add <本任务实际变更文件>`，`git commit -m "feat: preserve direction and semantics in catchments"`；PR列出验收证据、权利/覆盖限制与未启用能力。

### P09：餐饮配置、T-01/T-02与主题执行

**关联：** F-13/F-11；T-01/T-02；G-04/G-06/G-10；V-01/V-02/V-03/V-05/V-07/V-08；A10。
**依赖：** P02/P05/P06/P08。
**Files：** src/geo_intelligence_core/analysis.py; src/geo_intelligence_core/data/profiles/food-service-v1.json; src/geo_intelligence_core/data/templates/{surroundings,venue-discovery,location-comparison}-v1.json; tests/unit/test_analysis.py; tests/contract/test_industry_scenarios.py; tests/fixtures/scenarios/{food-service,retail,education}.json。

**Interfaces / 可见交付：** analyze(AnalyzeRequest,ProviderRegistry,UsagePolicy,Budget)->Result[Analysis]。配置消费P02，调用单项端口；三模板的必需输入、可选主题遵守V1契约第4节。T-03 JSON此步可验证，比较执行在P11。

**边界、资料与失败处理：** 人口默认关闭且可选；企业topic仅企业地点；无完整企业名册、无班次、无实时空位、无诊断推理。

- [ ] **1. 写失败测试。** test_surroundings：只选places成功=>ok，追加disabled population_reference=>partial且population.data is None。test_required_preflight：T-02必需places未配置=>unconfigured且0网络。test_template_upgrade：v1快照有效参数不随v2默认改动。test_cross_industry：同入口/范围/类别机制跑餐厅商店学校，无必填restaurant字段。test_unsupported_time：给静态设施午间条件不得伪称当时营业/客流。
- [ ] **2. 验证失败。** 运行 `python -m pytest tests/unit/test_analysis.py tests/contract/test_industry_scenarios.py -q`；未实现阶段预期FAIL，确认失败源于缺失行为而非测试配置。
- [ ] **3. 实现。** 先预检，再按已选主题有界执行并保留每题状态；受同一总预算约束。模板不得塞竞争压力/统一半径；请求显式给范围。映射restaurant/cafe/bar/fast_food及takeaway限定语，支持未知/多标签。只交付餐饮生产配置；零售/教育是合成验证fixture。
- [ ] **4. 验证通过。** 重跑同一命令，预期全部目标用例PASS；运行已有受影响契约回归。P13的live skip/blocked必须如实记录，不算PASS。
- [ ] **5. 提交并独立审查。** `git add <本任务实际变更文件>`，`git commit -m "feat: compose neutral analyses with food-service templates"`；PR列出验收证据、权利/覆盖限制与未启用能力。

### P10：证据修正、合法快照与三语导出

**关联：** F-10/F-12；G-02/G-03/G-07/G-08/G-09/G-10；A09。
**依赖：** P09。
**Files：** src/geo_intelligence_core/evidence.py; src/geo_intelligence_core/export.py; src/geo_intelligence_core/data/locales/{de,zh-CN,en}.json; tests/unit/test_evidence.py; tests/unit/test_export.py; docs/usage/evidence.md。

**Interfaces / 可见交付：** apply_correction(Analysis,Correction,scope_token)->Result[Analysis]；snapshot(Analysis,purpose)->Result[Snapshot]；export_result(Snapshot,format,language,purpose)->Result[str]。合法存储与访问控制仍由调用方承担。

**边界、资料与失败处理：** 不做报告排版、地图UI、客户权限系统；私有资料不能落公共缓存。合法旧快照使用必须显式指定。

- [ ] **1. 写失败测试。** test_correction：correct必须提供同实体类型/身份的replacement，结果呈现新值且原记录不变；confirm/exclude不接受新值；修改source identity/rights被拒绝；错误scope拒绝，不修改共享事实。test_conflict：冲突保留两来源，不平均。test_rights：export denied字段不出现JSON/CSV/GeoJSON及摘要，未知权利同样不导出；删除造成不完整时有redactions。test_snapshot：相同保留内容同hash，配置升级不改历史。test_csv_formula：以=,+,-,@或控制字符起始的文本不能被表格执行。test_locales：三语言键集合一致、数字/来源一致，原名不翻造。
- [ ] **2. 验证失败。** 运行 `python -m pytest tests/unit/test_evidence.py tests/unit/test_export.py -q`；未实现阶段预期FAIL，确认失败源于缺失行为而非测试配置。
- [ ] **3. 实现。** 逐字段及派生来源检查用途/保存/导出权限，拒绝或脱敏时说明原因；快照规范化序列化并记录不可复现部分。摘要用确定性模板引用已存在事实，不接LLM。CSV规范引用和公式防护；GeoJSON只含合法图层与属性。没有完整权利时不能把原数据暗存快照。
- [ ] **4. 验证通过。** 重跑同一命令，预期全部目标用例PASS；运行已有受影响契约回归。P13的live skip/blocked必须如实记录，不算PASS。
- [ ] **5. 提交并独立审查。** `git add <本任务实际变更文件>`，`git commit -m "feat: preserve evidence history and rights-aware exports"`；PR列出验收证据、权利/覆盖限制与未启用能力。

### P11：同口径地点比较与T-03

**关联：** F-08；T-03；G-01/G-03/G-10；V-04/V-06；A10。
**依赖：** P03/P09/P10。
**Files：** src/geo_intelligence_core/comparison.py; src/geo_intelligence_core/analysis.py; tests/unit/test_comparison.py; tests/contract/test_comparison_scenarios.py。

**Interfaces / 可见交付：** compare(list[Analysis],metric_ids:list[str])->Result[Comparison]；T-03编排先收集单点结果再调用compare。行含location版本、metric、nullable value、unit、evidence和可比性原因。

**边界、资料与失败处理：** 不做投资排名；设施数量差值是检索资料差异，不代表经营好坏。

- [ ] **1. 写失败测试。** test_comparability：同类别映射/区域方法/年份/单位才算差值；一个数据年份不同=>相应差值null。test_missing：一地点失败不得当0或参加排名。test_union：相交范围覆盖去重，设施source_key只计一次。test_three_industries：餐厅/商店/学校能用同比较结构，无best_location/score字段。test_population_disabled：人口未启用不影响已选设施比较。
- [ ] **2. 验证失败。** 运行 `python -m pytest tests/unit/test_comparison.py tests/contract/test_comparison_scenarios.py -q`；未实现阶段预期FAIL，确认失败源于缺失行为而非测试配置。
- [ ] **3. 实现。** 以指标口径签名检查分类版本、来源覆盖、时间/参考年、范围类型/阈值、方法和单位；允许显示原值但禁止生成不可比差值。联合范围先union再统计实体，不相加重复计数；空白只能针对明确研究边界及已知覆盖。没有人口算法时不输出人口联合总数。
- [ ] **4. 验证通过。** 重跑同一命令，预期全部目标用例PASS；运行已有受影响契约回归。P13的live skip/blocked必须如实记录，不算PASS。
- [ ] **5. 提交并独立审查。** `git add <本任务实际变更文件>`，`git commit -m "feat: compare locations with explicit metric comparability"`；PR列出验收证据、权利/覆盖限制与未启用能力。

### P12：消费者契约示例与发布包验证

**关联：** F-12/F-13；G-01—G-10；T-01—T-03；V-01—V-08；A01/A09/A10。
**依赖：** P01—P11。
**Files：** examples/python/offline_analysis.py; examples/maplibre/README.md; tests/contract/test_consumer.py; tests/packaging/test_install.py; docs/usage/consumer-integration.md; docs/releases/0.1.0a1.md; CHANGELOG.md; .github/workflows/test.yml。

**Interfaces / 可见交付：** 示例只使用导出的公共API，消费固化schema和mock providers；执行三模板并导出证据。发行物为wheel/sdist，Git commit pin初期分发；不自动发布PyPI或修改其他仓库。

**边界、资料与失败处理：** 真实RestaurantTrafficDiagnosis接入另列E07，不能凭示例声称已接通；人口V-04此时仅验证通用模型和停用状态。

- [ ] **1. 写失败测试。** test_consumer：不import内部实现，基础manual确认、三模板mock、部分结果、导出往返成功。test_clean_install：干净Python3.12分别装core/geometry/providers及首批组合，无密钥禁网运行；未装统计/公交也能导入。test_no_bundled_secrets：wheel无真实数据/token/JAR。test_schema_compat：保存首个消费者golden fixtures，破坏字段触发失败。
- [ ] **2. 验证失败。** 运行 `python -m pytest tests/contract tests/packaging -q`；未实现阶段预期FAIL，确认失败源于缺失行为而非测试配置。
- [ ] **3. 实现。** 补公开API导出、README真实安装示例、版本政策、生成SBOM/许可证清单和实际依赖扫描结果；按目标平台实际安装验证锁/hash。MapLibre只写GeoJSON接入示例与归属/瓦片责任，不引入Node到核心。记录已知限制，版本标签/发布动作需后续明确授权。
- [ ] **4. 验证通过。** 重跑同一命令，预期全部目标用例PASS；运行已有受影响契约回归。P13的live skip/blocked必须如实记录，不算PASS。
- [ ] **5. 提交并独立审查。** `git add <本任务实际变更文件>`，`git commit -m "test: verify packaged consumer contracts and offline examples"`；PR列出验收证据、权利/覆盖限制与未启用能力。

### P13：受控现场验收与首版交付判定

**关联：** A01—A05/A09—A11；F-11/F-13。
**依赖：** P12；启用资料可在P04起收集。
**Files：** docs/verification/provider-activation.md; docs/verification/first-release.md; tests/integration/test_photon_live.py; tests/integration/test_ors_live.py; tests/integration/test_overpass_live.py; tests/performance/test_budget.py; docs/project/status.md。

**Interfaces / 可见交付：** 验收输入为具体版本wheel、受控实例许可、消费者实际调用需求和已批准预算；输出逐门pass/fail/blocked/not_applicable及原始证据位置。不得把mock成功写成真实质量达标。

**边界、资料与失败处理：** 本任务不自行购买服务、自建集群或部署。若提供者质量未通过，准确交付离线/预览版，不称生产就绪；替换来源按ADR另评估。

- [ ] **1. 写失败测试。** test_live_opt_in：无GEO_LIVE_TESTS=1或许可/密钥则skip且报告未验证；不是pass。德国标注样本至少覆盖城市/郊区/乡村/变音符/缺门牌/同名各类，记录候选命中、歧义和失败，不仅检查200。test_budget：代表区域并发回放记录calls、p50/p95、内存；超限拒绝且不会追加请求。
- [ ] **2. 验证失败。** 运行 `python -m pytest tests/integration tests/performance -q（仅显式配置获准live环境；否则离线记录blocked/skip）`；未实现阶段预期FAIL，确认失败源于缺失行为而非测试配置。
- [ ] **3. 实现。** 先把实际消费者期望、样本选择和成功门槛写入启用记录，再做有预算的验证，防止测后改指标。固定各源当前条款/配额/归属及允许用途，尤其ORS完整账户条款；不能取得时只阻塞该provider线上启用，离线核心可交付。A06/A08计算不适用，A07随E01启用。完成独立审查，修复后记录证据，不以CI=部署。
- [ ] **4. 验证通过。** 重跑同一命令，预期全部目标用例PASS；运行已有受影响契约回归。P13的live skip/blocked必须如实记录，不算PASS。
- [ ] **5. 提交并独立审查。** `git add <本任务实际变更文件>`，`git commit -m "docs: record first-release validation and remaining gates"`；PR列出验收证据、权利/覆盖限制与未启用能力。

### 公共测试断言示例（补充，非已存在测试）

这些断言分别放入上述拥有该行为的测试；`result`等值由该测试的明确输入和接口产生，不是共享全局变量。

| 任务 | 必须钉住的断言 |
|---|---|
| P01 | `assert result.data.version == 1`；`assert previous.version == 1 and updated.data.version == 2` |
| P02 | `assert over_limit.status == "invalid_input" and fake.calls == 0` |
| P03 | `assert abs(distance_m(Point(longitude=0, latitude=0), Point(longitude=1, latitude=0)) - 111319.49) <= 1` |
| P04 | `assert transport.calls == 2`（2次预算、连续429测试）；`assert private_cache_hit is None` |
| P05 | `assert len(result.data) == 2`；`assert timeout.status == "unavailable" and timeout.data is None` |
| P06 | `assert same_address.data.unique_count == 2`；`assert remark.status == "partial"` |
| P07 | `assert matrix.data.cells[0].duration_s == 600 and matrix.data.cells[1].duration_s == 900` |
| P08 | `assert unsupported_inbound.status == "unsupported" and gateway.calls == 0` |
| P09 | `assert selected_population.status == "partial"`；`assert selected_population.data.topic_results["population_reference"].data is None` |
| P10 | `assert forbidden_value not in exported.data`；`assert old_snapshot.canonical_hash == repeated_snapshot.canonical_hash` |
| P11 | `assert incompatible.data.rows[0].difference is None`（Comparison行定义显式包含nullable difference） |
| P12 | `assert subprocess_result.returncode == 0`（清洁环境只装core并禁网确认地点） |
| P13 | `assert measured_calls <= activation.max_calls`；没有live配置时验证报告为blocked/skip而非pass |

P12打包验证具体执行：
```bash
python -m build
python -m venv /tmp/geo-core-install-check
/tmp/geo-core-install-check/bin/python -m pip install dist/geo_intelligence_core-0.1.0a1-py3-none-any.whl
/tmp/geo-core-install-check/bin/python -c "import geo_intelligence_core"
python -m pytest tests/packaging tests/contract -q
```
wheel文件名在打包配置变更时按实际产物更新；安装阶段允许访问获准依赖源，运行时验证禁网。额外分别验证geometry/providers安装；核心测试不能因缺可选依赖失败。

## 4. 后续工作项与人口启用门

以下仍为明确保留的目标，不计入首版完成率。未来执行任一项时先复核其依赖和当前main，不重新默认启动全部扩展。按功能可独立提交PR；数据前提不满足时交付“未启用及原因”即可，不编造数据。
人口三层启用记录统一写入docs/decisions/population-value.md：实际使用者与决策问题、没有该数据的替代方案、数据/许可/更新时间、一次性接入与持续维护成本、计算费用和等待、核实/误差负担、可测收益、负责人结论(enable/defer/omit)及复查触发条件。没有证据不填虚假ROI数值。POP-03允许最终omit。

### E01：营业时间与实测观测

**排期与原因：** 正常后续；有使用者需要时实施。
**依赖：** P10。
**关联：** F-04/F-07；V-05；A07。
**Files：** src/geo_intelligence_core/temporal.py; src/geo_intelligence_core/models/observation.py; tests/unit/test_temporal.py; tests/unit/test_observation.py; requirements/temporal-py312.lock。
**Interfaces：** evaluate_hours(expression:str, at:datetime, timezone:str, holiday_region:str|None)->Result[str]（open/closed/unknown）；normalize_observation(Observation)->Result[Observation]。Observation包含point/region、start/end、timezone、direction、count_object(person/visit)、count nullable、missing_reason、method、dedupe及rights。

- [ ] **1. 确认启用前提。** 记录具体使用者、来源/权利和预算；缺失则维持disabled/unconfigured，不影响首批。
- [ ] **2. 写并运行失败测试。** opening_hours_py；跨夜Mo 22:00-02:00、Berlin春秋DST、州级PH、未知语法/假日上下文缺失=>unknown；无offset的重复本地时刻拒绝，不能猜。实测0保留，缺测null，人次不可转人数；观测时长不同直接比较拒绝，年人口不能变午间人流。时段/季节/活动标签支持描述，只有支持该条件的来源才用于筛选。 运行 `python -m pytest tests/unit/test_temporal.py tests/unit/test_observation.py -q`，尚未实现时应FAIL。
- [ ] **3. 实现最小能力。** 在所列文件实现上述接口，复用P01—P12契约/权利/预算；只有本任务需要的可选依赖才安装、锁定与扫描。
- [ ] **4. 验证与记录。** 同命令PASS，增加该能力的schema/三行业相关回归；对真实数据另记覆盖与性能，不用合成测试冒充现实验证。
- [ ] **5. 独立提交PR。** 仅包含该项及必要文档，更新能力清单/状态/发布说明；保留关闭路径。

### E02：历史变化与监测条件表达

**排期与原因：** 正常后续；先需要两份合法快照。
**依赖：** P10/P11；小时变化解释依赖E01。
**关联：** F-04/F-09/F-10。
**Files：** src/geo_intelligence_core/history.py; src/geo_intelligence_core/models/change.py; tests/unit/test_history.py。
**Interfaces：** compare_snapshots(before:Snapshot,after:Snapshot)->Result[list[Change]]；Change(kind,entity_ref,before,after,evidence_ids,verification)。kind区分source_record/method/verified_real_world；WatchSpec仅表达主题与条件。

- [ ] **1. 确认启用前提。** 记录具体使用者、来源/权利和预算；缺失则维持disabled/unconfigured，不影响首批。
- [ ] **2. 写并运行失败测试。** 同查询少1记录=>source_record_missing不是closed；方法/位置版本改变=>条件变化，不能报现实新增；key排序无变化；人工依据确认迁址后保留旧地址及确认引用。指标/交通/营业时间/统计更新均通过有类型指标比较，禁止JSON diff直接作现实结论。仅输出变化，不启动调度/通知。 运行 `python -m pytest tests/unit/test_history.py -q`，尚未实现时应FAIL。
- [ ] **3. 实现最小能力。** 在所列文件实现上述接口，复用P01—P12契约/权利/预算；只有本任务需要的可选依赖才安装、锁定与扫描。
- [ ] **4. 验证与记录。** 同命令PASS，增加该能力的schema/三行业相关回归；对真实数据另记覆盖与性能，不用合成测试冒充现实验证。
- [ ] **5. 独立提交PR。** 仅包含该项及必要文档，更新能力清单/状态/发布说明；保留关闭路径。

### E03：受支持地图链接与行政边界导入

**排期与原因：** 正常后续；地图平台/数据许可可用才启用相应输入。
**依赖：** P03/P05/P10。
**关联：** F-01/F-02。
**Files：** src/geo_intelligence_core/inputs/map_links.py; src/geo_intelligence_core/inputs/regions.py; tests/unit/test_inputs.py。
**Interfaces：** parse_map_link(url:str)->Result[Point]；import_region(document:dict,evidence:Evidence)->Result[Region]。第一版仅离线解析明确格式的坐标链接；短链和任意网页抓取unsupported。

- [ ] **1. 确认启用前提。** 记录具体使用者、来源/权利和预算；缺失则维持disabled/unconfigured，不影响首批。
- [ ] **2. 写并运行失败测试。** 白名单主机/路径显式坐标解析，重复参数、非数值、混淆主机和私网URL拒绝；不跟随短链接。行政GeoJSON带来源/CRS/年份/比例尺和rights；缺失元数据拒绝，边界附近提示精度限制；获取BKG等具体数据另记录许可，不暗中下载全国。 运行 `python -m pytest tests/unit/test_inputs.py -q`，尚未实现时应FAIL。
- [ ] **3. 实现最小能力。** 在所列文件实现上述接口，复用P01—P12契约/权利/预算；只有本任务需要的可选依赖才安装、锁定与扫描。
- [ ] **4. 验证与记录。** 同命令PASS，增加该能力的schema/三行业相关回归；对真实数据另记覆盖与性能，不用合成测试冒充现实验证。
- [ ] **5. 独立提交PR。** 仅包含该项及必要文档，更新能力清单/状态/发布说明；保留关闭路径。

### E04：企业资料深化与特殊交通事实

**排期与原因：** 数据条件阻塞；当前无已核实完整来源，先提供用户获准导入。
**依赖：** P06/P10；时间解释依赖E01。
**关联：** F-03/F-05/F-07。
**Files：** src/geo_intelligence_core/inputs/company.py; src/geo_intelligence_core/inputs/transport.py; tests/unit/test_enrichment.py; docs/operations/enrichment-sources.md。
**Interfaces：** import_company(records:list[dict],evidence:Evidence)->Result[list[CompanySite]]；import_transport(records:list[dict],evidence:Evidence)->Result[list[TransportFact]]。TransportFact含kind、value、unit、location、valid_period、measured_at、evidence。

- [ ] **1. 确认启用前提。** 记录具体使用者、来源/权利和预算；缺失则维持disabled/unconfigured，不影响首批。
- [ ] **2. 写并运行失败测试。** 总部员工500不分配给分店；注册地址不自动working_site；分店员工缺失为null；区间人数不造精确值。停车容量≠空位；过期实时空位不能展示当前；无障碍/施工/骑行限制需适用路段、方向和有效期；任何普通路线不等于儿童安全。企业行业构成与规模资料覆盖率分母明示。 运行 `python -m pytest tests/unit/test_enrichment.py -q`，尚未实现时应FAIL。
- [ ] **3. 实现最小能力。** 在所列文件实现上述接口，复用P01—P12契约/权利/预算；只有本任务需要的可选依赖才安装、锁定与扫描。
- [ ] **4. 验证与记录。** 同命令PASS，增加该能力的schema/三行业相关回归；对真实数据另记覆盖与性能，不用合成测试冒充现实验证。
- [ ] **5. 独立提交PR。** 仅包含该项及必要文档，更新能力清单/状态/发布说明；保留关闭路径。

### E05：可选PBF批量与疑似去重排序

**排期与原因：** 低优先级；受控Overpass实测不足才启用，两个子项可独立PR。
**依赖：** P06/P10。
**关联：** F-04/F-05；A04/A11。
**Files：** src/geo_intelligence_core/providers/pbf.py; src/geo_intelligence_core/dedupe.py; tests/unit/test_pbf.py; tests/unit/test_dedupe.py; requirements/{osm-import,dedupe}-py312.lock。
**Interfaces：** import_pbf(path:Path,query:PlaceQuery,evidence:Evidence)->Result[PlaceSet]；suggest_duplicates(places:list[Place])->Result[list[DuplicateCandidate]]。

- [ ] **1. 确认启用前提。** 记录具体使用者、来源/权利和预算；缺失则维持disabled/unconfigured，不影响首批。
- [ ] **2. 写并运行失败测试。** pyosmium最小区域合成PBF与HTTP归一结果一致；重复ID、越界、坏文件/超大小拒绝，无显式请求时不得下载。RapidFuzz仅相似排序，100分也不自动合并；同址不同店保留。数据文件不入git，合成fixtures可由测试生成，底层依赖单独锁与许可证审查。 运行 `python -m pytest tests/unit/test_pbf.py tests/unit/test_dedupe.py -q`，尚未实现时应FAIL。
- [ ] **3. 实现最小能力。** 在所列文件实现上述接口，复用P01—P12契约/权利/预算；只有本任务需要的可选依赖才安装、锁定与扫描。
- [ ] **4. 验证与记录。** 同命令PASS，增加该能力的schema/三行业相关回归；对真实数据另记覆盖与性能，不用合成测试冒充现实验证。
- [ ] **5. 独立提交PR。** 仅包含该项及必要文档，更新能力清单/状态/发布说明；保留关闭路径。

### E06：公交班次与独立公交可达分析

**排期与原因：** 条件扩展；非首批，不因人口需要启动。
**依赖：** P03/P04/P10；已有独立公交价值/预算/获准GTFS。
**关联：** F-02/F-03/F-07；V-02/V-05；A08/A11。
**Files：** src/geo_intelligence_core/transit/gtfs.py; src/geo_intelligence_core/transit/r5.py; tests/transit/test_gtfs.py; tests/transit/test_r5_contract.py; requirements/transit-py312.lock; docs/operations/transit-runtime.md。
**Interfaces：** validate_feed(path:Path,date:date)->Result[FeedRef]；travel_times(request:MatrixRequest,feed:FeedRef)->Result[TravelMatrix]。仅独立transit环境导入R5py；返回线的展示单独类型，不塞Region。

- [ ] **1. 确认启用前提。** 记录具体使用者、来源/权利和预算；缺失则维持disabled/unconfigured，不影响首批。
- [ ] **2. 写并运行失败测试。** 先用GTFS validator验证calendar/exception/25:00/agency_timezone/过期feed；缺覆盖unsupported，计划时刻不称实时。实测所锁R5py支持方向和时间语义；配套JAR固定URL/hash实际下载校验，按上游要求准备JDK，不任意换latest。矩阵分钟值2转120s；timedelta(120s)仍120s；NaN/no-path为null；Isochrones MultiLineString不能当Polygon。单独记录内存/时长/区域/目标点预算。 运行 `python -m pytest tests/transit -q（隔离且预置JAR/feed；常规core CI不安装JVM）`，尚未实现时应FAIL。
- [ ] **3. 实现最小能力。** 在所列文件实现上述接口，复用P01—P12契约/权利/预算；只有本任务需要的可选依赖才安装、锁定与扫描。
- [ ] **4. 验证与记录。** 同命令PASS，增加该能力的schema/三行业相关回归；对真实数据另记覆盖与性能，不用合成测试冒充现实验证。
- [ ] **5. 独立提交PR。** 仅包含该项及必要文档，更新能力清单/状态/发布说明；保留关闭路径。

### E07：真实消费者接入与是否服务化

**排期与原因：** 后续跨仓库任务；本计划不直接修改消费者。
**依赖：** P12/P13可用能力。
**关联：** F-12/F-13；A01/A09/A11。
**Files：** 本库 docs/usage/consumer-integration.md; tests/contract/test_consumer.py；消费者文件路径在读取其当前AGENTS/事实分支后确定，不虚构现有模块。
**Interfaces：** 先对RestaurantTrafficDiagnosis真实运行时/包分发/资料权利/案件隔离做接入核对，形成其独立实施PR；消费本库固定commit/tag的公共API，将Evidence映射为消费者来源记录。

- [ ] **1. 确认启用前提。** 记录具体使用者、来源/权利和预算；缺失则维持disabled/unconfigured，不影响首批。
- [ ] **2. 写并运行失败测试。** 验证同一地点重新确认使旧分析标过期而不抹历史；保存刷新后恢复；案件A不得读B资料；部分结果可解释；三语与地图归属保持；诊断证据须人工批准。本库没有restaurant_id。第二消费者使用同发布物后才评估HTTP服务/PostGIS/自建，不把服务化当必做阶段。 运行 `本库运行 python -m pytest tests/contract/test_consumer.py -q；消费者按其实际AGENTS规定测试并记录命令，不用虚假命令声称通过`，尚未实现时应FAIL。
- [ ] **3. 实现最小能力。** 在所列文件实现上述接口，复用P01—P12契约/权利/预算；只有本任务需要的可选依赖才安装、锁定与扫描。
- [ ] **4. 验证与记录。** 同命令PASS，增加该能力的schema/三行业相关回归；对真实数据另记覆盖与性能，不用合成测试冒充现实验证。
- [ ] **5. 独立提交PR。** 仅包含该项及必要文档，更新能力清单/状态/发布说明；保留关闭路径。

### POP-01：已有行政人口/用户统计引用

**排期与原因：** 可选低成本扩展，首批默认disabled，不必等待POP-02。
**依赖：** P10；成本收益记录通过。
**关联：** F-06；V-04/V-07。
**Files：** src/geo_intelligence_core/statistics/reference.py; tests/statistics/test_reference.py; docs/decisions/population-value.md。
**Interfaces：** reference_statistics(records:list[dict],evidence:Evidence)->Result[list[Metric]]；记录行政区域ID/边界年份、指标定义/分母、reference year、资料权利。

- [ ] **1. 确认启用前提。** 记录具体使用者、来源/权利和预算；缺失则维持disabled/unconfigured，不影响首批。
- [ ] **2. 写并运行失败测试。** 已有获准行政人数1000仅展示为该区域某年人口；禁止称门店步行人口；儿童人数不转招生需求，家庭数不转购物需求；缺失/保密不为0；无用户价值时决定保持disabled并无需安装统计依赖。 运行 `python -m pytest tests/statistics/test_reference.py -q`，尚未实现时应FAIL。
- [ ] **3. 实现最小能力。** 在所列文件实现上述接口，复用P01—P12契约/权利/预算；只有本任务需要的可选依赖才安装、锁定与扫描。
- [ ] **4. 验证与记录。** 同命令PASS，增加该能力的schema/三行业相关回归；对真实数据另记覆盖与性能，不用合成测试冒充现实验证。
- [ ] **5. 独立提交PR。** 仅包含该项及必要文档，更新能力清单/状态/发布说明；保留关闭路径。

### POP-02：自定义范围网格统计

**排期与原因：** 低优先级，允许长期不做。
**依赖：** P03/P10；独立成本收益通过及获准网格。
**关联：** F-06/F-08；V-04；A06/A11。
**Files：** src/geo_intelligence_core/statistics/grid.py; src/geo_intelligence_core/statistics/datasets.py; tests/statistics/test_grid.py; requirements/statistics-py312.lock; docs/decisions/population-value.md。
**Interfaces：** aggregate_grid(region:Region,dataset:DatasetRef,method:Literal['full_cells','centroid','area_weighted'])->Result[list[Metric]]；GeoPandas/pandas/pyogrio只在statistics extra安装。

- [ ] **1. 确认启用前提。** 记录具体使用者、来源/权利和预算；缺失则维持disabled/unconfigured，不影响首批。
- [ ] **2. 写并运行失败测试。** 原生网格两格人口100、200，完整第一格+半第二格面积估计为200并标estimated；质心法取舍按显式规则，不能声称等价。缺失/抑制格单独报告覆盖，不能算0；比率重新汇总分子/分母。重叠区域先union，仅计一次。拒绝不明CRS/年份/分配方法；EPSG:4326平方度不得当m²；跨年定义/边界不同不可比。扩展家庭、住房、年龄及就业/收入均需相应合法资料与同样口径。 运行 `python -m pytest tests/statistics/test_grid.py -q`，尚未实现时应FAIL。
- [ ] **3. 实现最小能力。** 在所列文件实现上述接口，复用P01—P12契约/权利/预算；只有本任务需要的可选依赖才安装、锁定与扫描。
- [ ] **4. 验证与记录。** 同命令PASS，增加该能力的schema/三行业相关回归；对真实数据另记覆盖与性能，不用合成测试冒充现实验证。
- [ ] **5. 独立提交PR。** 仅包含该项及必要文档，更新能力清单/状态/发布说明；保留关闭路径。

### POP-03：公交范围网格人口/经验证线转面

**排期与原因：** 最低优先级，首批明确不做，收益不足可永久不实现。
**依赖：** E06/POP-02；单独收益与误差评估通过。
**关联：** F-06/F-08；A06/A08/A11。
**Files：** src/geo_intelligence_core/statistics/transit_grid.py; tests/statistics/test_transit_grid.py; docs/decisions/population-value.md。
**Interfaces：** aggregate_reachable_grid(matrix:TravelMatrix,dataset:DatasetRef,threshold_s:int,sampling:SamplingSpec)->Result[list[Metric]]。SamplingSpec固定网格分辨率、代表点、时间窗、percentile、direction和depart/arrive语义。

- [ ] **1. 确认启用前提。** 记录具体使用者、来源/权利和预算；缺失则维持disabled/unconfigured，不影响首批。
- [ ] **2. 写并运行失败测试。** 优先明确网格代表点旅行时间筛选，不直接叠加Isochrones线。河流隔断、孔洞、离岛、采样疏密改变结果须可解释；无路径格不可等同无居民；记录分辨率敏感度及估计误差。只有另行验证闭合/拓扑/障碍/误差的转换才允许面；默认不提供线转面功能，禁止凸包替代。测试失败或价值不足关闭本能力，其他能力照常。 运行 `python -m pytest tests/statistics/test_transit_grid.py -q`，尚未实现时应FAIL。
- [ ] **3. 实现最小能力。** 在所列文件实现上述接口，复用P01—P12契约/权利/预算；只有本任务需要的可选依赖才安装、锁定与扫描。
- [ ] **4. 验证与记录。** 同命令PASS，增加该能力的schema/三行业相关回归；对真实数据另记覆盖与性能，不用合成测试冒充现实验证。
- [ ] **5. 独立提交PR。** 仅包含该项及必要文档，更新能力清单/状态/发布说明；保留关闭路径。

## 5. 决策记录与启动条件

| 事项 | 已定方案 | 在哪一步关闭剩余缺口 |
|---|---|---|
| 首批范围 | P01—P13；人口/公交引擎非必需 | 追踪表不得把整个F领域标已实现 |
| 生产调用预算 | 默认不联网；调用者显式提供总量/并发/范围/费用上限 | P04定义可验证约束；P13依据实际需求/账户条款记录具体值，缺失不启用 |
| SLO与地址质量 | 不捏造当前流量/命中率/延迟 | P13测试前登记消费者容忍度与人工样本判据，实测后给结论 |
| 开源精确版本 | 复用已选库，Python3.12先测 | P01及各extra引入任务实际解析/安装/锁hash/审计；有问题再按ADR替换 |
| ORS/Photon/Overpass实例 | 只接已获准配置，无默认demo | P13完整条款/配额/覆盖记录；受控公共实例也必须适用且可接受无SLA |
| 餐饮范围默认 | 不给全行业统一半径；请求明确范围 | P09用缺失范围=>invalid_input测试落实 |
| 真实消费者 | 本库示例与schema先行，commit pin | E07读取消费者事实分支再确定真实编辑点和运行时兼容 |
| POP-01/02/03 | 当前均不启用，分别条件/低/最低 | 各POP任务收益与数据门可选择defer/omit |
| 自建/数据库/HTTP服务 | 无首批需求 | E07只有真实跨消费者收益时另起ADR，非自动升级 |

## 6. 计划验收与执行交接

规划自检：任务无依赖环；F/G/T/V/A都有[追踪归属](../../plans/REQUIREMENTS_TRACEABILITY.md)；首版中只覆盖子集的F功能明确列出后续任务；旧路线图/契约/状态同步；公共函数命名与字段统一；五类高风险均有归属测试。
此文未运行任何软件测试或安装任何依赖。将来每个任务完成时，提交实际命令、结果、commit、审查结论与适用验收门，不能只勾选本文。

建议下一次从P01开始，一次完成一个可审查步骤；不要先把所有目录与空接口搭完。实施前由用户选择继续执行及执行方式；本次仅保存计划，不开始开发、合并或部署。
