# 免费优先试用增量 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在每天几次至几十次查询的受控试用中，使用免费公共来源取得经过验证的地理事实，并保持未来切换服务的低成本。

**Architecture:** 继续按 Python 依赖安装，沿用 LocationResolver / PlaceProvider / RoutingProvider 和 HttpGateway。核心提供实例配置、适配与可测试预算接口；调用方负责日额度持久化、页面交互、密钥及案件权限。不为此库增加独立 HTTP 服务或 Cloud Run 部署。

**Tech Stack:** 沿用 Python 3.12、Pydantic、HTTPX 和现有 geometry/providers extras；不为低量试用新增数据库、Redis、JVM 或 GIS 集群。

**Spec:** [免费优先方案](../../operations/free-first-providers.md)、[原始实施计划](2026-11-04-core-implementation.md)、[来源启用记录](../../verification/provider-activation.md)。

基线：main `b7fb468b1122260251b5ef051a1a5fc9219e1878`，PR #22 已合并。本文是 P04/P13/E07 的增量执行计划，不重做 P01–P13，也不把新增计划当作已实现。P01–P12 已有离线交付；P13 仅预检与阻塞记录；真实服务测量 runner 尚未实现。PR #22 已完成零费用/免密钥配置验证及 Photon 同协议切换回归，不能据此声明来源已启用。当前 OrsRoutingProvider._preflight 仍固定 api.heigit.org、限定路径并强制 credential_handle；ORS 自建切换是 FF-03 待实现项，不能宣称所有适配器已经只改 URL 即可。E07 真实进展必须在 RestaurantTrafficDiagnosis 当前事实分支核对，不能从本库推断。

## Global Constraints

- 首选 Photon `https://photon.komoot.io`、Overpass `https://overpass.private.coffee`、ORS Standard `https://api.heigit.org/openrouteservice`；前两项无账号密钥，ORS 需要免费 key。依据及限制见 Spec，不采购订阅。
- 公共条款允许用途时，不额外要求逐家申请书面许可；账号配额仅适用于有账号的服务。没有公开数值限额时记录未知及本地限额，不虚构供应商额度。
- 保留默认不联网；只有显式选择试用配置并调用时才允许请求。网络导入副作用、自动付费回退、轮换公共端点规避限流均禁止。
- 试用起始建议：每来源每日 50 次 HTTP 尝试、每运行最多 5 次、每来源并发 1、费用预算 0；这是本地可调整策略，不是供应商承诺，也不是已实现的跨进程限额。一次用户查询可能发出多个请求。
- 不增加独立部署、云运行配置或服务上线验收。保留第三方实例调用配置、依赖安装验证、数据权利与真实质量验收，它们是作为库调用的必要条件。
- 不改变通用核心、餐饮模板及零售/教育通用性约束；人口保持可选低优先级，不引入 R5py 人口计算。
- 每项功能分支、失败用例先行、离线回归、独立审查；现场请求只能在样本、阈值、实例和有限预算明确后执行。

## Review Focus

1. 无 key 的公共服务与必须有 key 的 ORS 不得混淆：FF-01 验证。
2. 重试、重启、多 worker 或多个 key 不能重置应用日额度：FF-02 验证。
3. URL 前缀、认证及缓存实例身份变化不能泄漏密钥或复用旧实例结果：FF-03 验证。
4. 200/空结果/超时不能代替真实覆盖与准确性：FF-04 验证。
5. ORS 缺 key、资料缺失、实例切换不能阻塞全部主题或破坏旧案件证据：FF-05 验证。

## 顺序、仓库与完成判据

| 顺序 | 工作项 | 执行仓库 | 状态与独立交付 |
| --- | --- | --- | --- |
| 1 | FF-01 免费试用配置入口 | GeoIntelligenceCore | PR #24 已合并 main；离线构造既有适配器，不代表现场启用 |
| 2 | FF-02 跨请求预算接入契约 | 本库定义契约/示例；调用方实现持久化 | 功能分支实现合成共享存储契约/示例；实际持久化与跨 worker 验证仍由调用方完成 |
| 3 | FF-03 同协议切换验收 | GeoIntelligenceCore | 部分已有；Photon 已测，补 Overpass/ORS、认证隔离与实例身份 |
| 4 | FF-04 分来源现场验证 | GeoIntelligenceCore | 待做；先实现可测 runner，再分别验证免费来源 |
| 5 | FF-05 E07 免费来源交接与实际启用 | 本库交接；RestaurantTrafficDiagnosis 接入 | 待核对调用方现状后补差，不重复已完成 E07 |

依赖：FF-01 → FF-02/FF-03 → FF-04 → FF-05 的对应来源启用。FF-05 的离线接入与 UI 检查可提前。Photon/Overpass 验证不等待 ORS 账号；ORS 被阻塞时交付明确禁用路线的受控试用。

## FF-01：可显式选择的免费配置入口

**Files:** 新建 `src/geo_intelligence_core/providers/trial.py`、`examples/python/free_trial.py`、`tests/unit/test_trial.py`；按需修改 `providers/__init__.py`；更新 `docs/operations/free-first-providers.md`。

**Interfaces:** 新增 `TrialSettings`（Pydantic 配置模型）和 `build_trial_provider(settings: TrialSettings, *, budget: Budget, headers: dict[str, str] | None = None) -> LocationResolver | PlaceProvider | RoutingProvider`。配置包括 protocol（photon/overpass/ors）、唯一 instance_id、endpoint、UsagePolicy、认证要求与能力声明；沿用现有 ProviderConfig 和既有适配器，认证值只在 headers 运行时注入。构造不得联网。每个实例一个 gateway，调用方可注入共享 Budget。

- [x] 写 `test_trial_defaults_and_opt_in`：未显式调用不出网；三个模板的地址/路径前缀正确；有明确的 5 次运行上限、并发 1 和零费用；日额度标为需 FF-02 注入，而非假装内存已持久化。
- [x] 写 `test_auth_and_zero_cost`：Photon/Overpass 无 key 可构造；已知 hosted ORS 缺 key 阻止请求；自建无 key 配置需明确声明（ORS 实际支持待 FF-03，FF-01 不假装已支持）；非零单价在零费用配置下不能发起调用，密钥不出现在序列化配置/异常中。
- [x] 运行 `python -m pytest tests/unit/test_trial.py -q`，确认新行为未实现时失败；随后实现上述模型/工厂及离线可执行示例。条款/价格/归属引用随实例配置，User-Agent 支持应用名与公开联系地址；未知缓存/导出权利仍关闭。
- [x] 同命令通过，并运行 `python -m pytest tests/integration/test_live_gate_config.py tests/contract/test_consumer.py -q`；示例默认 dry-run，缺 ORS key 不影响其他实例。
- [x] 独立 PR，注明新接口/配置字段与适配器的对应关系，不声称在线已可用。

## FF-02：有限预算与调用方日额度

**Files:** 修改 `docs/operations/provider-activation.md`、`docs/usage/consumer-integration.md`；新增 `tests/contract/test_shared_budget.py`、`examples/python/shared_budget.py`；仅在契约测试发现缺口时修改 `providers/http.py` / `providers/budget.py`，不预先重写网关。

**Interfaces:** 复用 `Budget.reserve(provider_id: str, calls: int, estimated_cost: Decimal) -> bool` 与 `Budget.record(provider_id: str, actual_cost: Decimal) -> None`。调用方为每个运行构造绑定 run_id 的预算对象，底层按稳定来源额度域共享存储，原子执行“每运行 5 次 + 每来源每日 50 次 + 金额 0”。并发 1 另由调用方共享锁/信号量包住该来源的执行并在 finally 释放；Budget.reserve 本身不承担并发槽释放。按 UTC 日重置，重试、重定向均记尝试。凭据轮换不改变同一额度域，实例别名不能产生新额度。持久化用调用方已有存储；本库测试用合成存储与可控时钟，不新增基础设施。

- [x] 写 `test_shared_last_slot` / `test_retry_counts`：两个 gateway 竞争每日最后 1 次仅一条请求出网，429 重试消耗额度，费用预算不能静默提高。
- [x] 写 `test_restart_and_utc_reset` / `test_store_unavailable`：重建调用对象仍保留已用量，跨 UTC 日按规则重置；预算存储失效必须停止请求且显式说明原因。测试对象须模拟同一存储被两个对象原子访问，不用单个进程计数器冒充跨 worker 证明。补 `test_shared_concurrency_release`：两个 gateway 的请求实际重叠时并发始终为 1，成功/异常/超时/取消后均释放共享槽；已消耗的尝试额度不退回。
- [x] 先运行 `python -m pytest tests/contract/test_shared_budget.py -q` 观察失败，再补示例与契约；调用方负责防抖/重复点击防护，来源限额不足时等待或返回明确状态，不自动换端点。
- [x] 同命令通过，运行 `python -m pytest tests/unit/test_http_policy.py tests/performance/test_budget.py -q`。文档分开“本库契约已验证”和“真实存储跨 worker 验证待调用方完成”。
- [x] 独立 PR；FF-05 在调用方验证真实存储，不因此给 GeoIntelligenceCore 新增数据库。

## FF-03：免费、付费、自建的切换契约

**Files:** 扩充 `tests/unit/test_photon.py`、`tests/unit/test_overpass.py`、`tests/unit/test_ors_routes.py`、`tests/unit/test_catchments.py`、`tests/unit/test_http_policy.py`；更新 `docs/operations/free-first-providers.md`；修改 `src/geo_intelligence_core/providers/ors.py` 的固定域名/路径/认证预检并补 FF-01 工厂；需要显式实例认证字段时修改 `models/policy.py`，保持既有 hosted 默认行为。

**Interfaces:** 保持既有三类 port 和 Result 不变。切换只更改 instance_id、base URL、认证 headers、能力和限额/权利引用；注册到原 capability_id。保存的实例来源标识与缓存键必须变化；历史快照不改写。不同协议通过新增 adapter，不承诺只改 URL。ORS 将硬编码主机/路径改为显式获准实例配置，认证要求独立于费用；已知 HeiGIT hosted 必须有凭据，其他实例仅显式允许无认证。仍由 HttpGateway 校验 HTTPS、origin allowlist、DNS 与重定向，不能用放宽 SSRF 代替兼容自建。

- [ ] 保留 PR #22 已有 Photon search/reverse 回归；新增 Overpass query、ORS route/matrix/catchments 的公共/带认证/自建 HTTPS 前缀参数化测试，断言参数、单位、方向和结果结构一致。
- [ ] 新增 `test_credentials_isolated_between_instances` / `test_instance_cache_identity`：A 的 key 不发给 B，切换实例后旧缓存不命中，429 不触发付费端点；私网/IP/非 HTTPS 仍被既有策略拒绝。
- [ ] 运行上述六个测试文件，先确认新增用例能暴露缺口；仅修复缺口，不更换已工作的协议实现。
- [ ] 运行 `python -m pytest tests/unit tests/contract -q`，记录所有实例为 synthetic；如需私网自建访问，单列后续受审策略扩展，不解除 SSRF 防护。
- [ ] 独立 PR；不需要购买账号或真实自建服务器即可完成此项。

## FF-04：补齐 P13 runner，分别验证免费来源

**Files:** 修改 `tests/integration/live_gate.py`、`test_photon_live.py`、`test_overpass_live.py`、`test_ors_live.py`；新建 `tests/integration/live_measurements.py` 和 `tests/unit/test_live_measurements.py`；更新 `docs/verification/provider-activation.md`、`first-release.md` 与 `docs/project/status.md`。

**Interfaces:** 新增 `async measure_cases(cases: list[dict], *, invoke, clock) -> dict` 测量帮助函数，invoke 接收一条已预先标注的 case 并返回 Result。报告记录样本引用、calls、各状态/质量、p50/p95、峰值内存、版本/实例/权利/预算及逐门 pass/fail/blocked；不同类型来源各自有断言，不共用一个准确率掩盖差异。原始资料仅在许可允许时保存，报告脱敏。

- [ ] 离线失败测试：用合成 invoke 验证错误候选、歧义、空结果、超时、partial、无路线、超预算均不能误判 pass。阈值和样本必须在请求前冻结，缺失即 blocked；live 无 opt-in 一律 skip。
- [ ] 运行 `python -m pytest tests/unit/test_live_measurements.py tests/integration/test_live_gate_config.py -q`，失败后实现帮助函数及三个真实 adapter runner，替换当前无条件 pytest.fail 占位。保存“runner 已实现”与“现场通过”两个独立状态。
- [ ] 同命令通过并独立审查 runner；准备获准公共地址样本与预先人工标注的匹配/精度期望。Photon 覆盖城市/郊区/乡村/变音符/缺门牌/同名；Overpass 预定小范围类别与独立参考；ORS 验证方向、无路线、矩阵和范围。每次分批不超过 5 次，跨批/当天共享预算。
- [ ] 按来源单独运行，例如 `GEO_LIVE_TESTS=1 GEO_LIVE_ACTIVATION_FILE=/secure/activation.json python -m pytest tests/integration/test_photon_live.py -q`；Overpass/ORS 分别选对应文件。未注册 ORS 时只阻塞 ORS；公共服务无需虚构 credential_env。完整账号条款仍只适用于 ORS；公开条款足以许可的服务不索取额外书面许可。
- [ ] 记录真实测量、阈值和结果，small sample 的 p95 仅描述该批样本，不当作 SLA；不通过时保留手工/离线路径。无获准样本或 key 时，提交已完成 runner 与 blocked 原因，不标整项现场通过。独立 PR。

## FF-05：E07 交接与调用方实际启用

**Files:** 本库修改 `docs/usage/consumer-integration.md`、`docs/project/status.md`，补 `tests/contract/test_consumer.py`（如接口有变化）；调用方文件在读取其当前 development、AGENTS、状态与最近 PR 后确定，不虚构路径。

**Interfaces:** 本库交付固定 commit/包、FF-01 配置示例、FF-02 Budget 接口、FF-04 每来源测量结论。RestaurantTrafficDiagnosis 通过原公共 API 取地理事实；UI/来源记录/案件权限/密钥保存/日预算归调用方。

- [ ] 核对 E07 已合并代码，只列差异；无需重复开发已存在的顾问流程。没有已验证消费者状态时，交接表标“待调用方核对”，不得写未集成或已集成的绝对结论。
- [ ] 在调用方先写失败测试：Photon/Overpass 可单独开启、ORS 无 key 只禁路线；预算跨运行/重启/worker 生效；重复点击不刷额度；429/超时可重试或手工处理，不填零。
- [ ] 接入已验证来源及实际存储预算；保留案件隔离、人工批准、来源归属、三语提示和过期快照规则。运行调用方实际测试命令并记录，不用本库 mock 代替验证。
- [ ] 核验切换同协议实例不改诊断逻辑、旧证据不覆盖；仅启用 FF-04 已通过的能力。按已有消费者流程交付，不在本计划增加独立核心部署或 Cloud Run 上线任务。
- [ ] 分仓库 PR，回写交接证据；无真实调用方访问条件时只完成本库交接，清楚标记剩余项。

## 人工事项与可延后内容

| 事项 | 是否必须现在人工做 | 不具备时 |
| --- | --- | --- |
| Photon / Private.coffee 购买、注册、申请 key | 不需要 | 自动完成配置与离线测试即可 |
| ORS 免费账号、邮箱验证、取得 key 并存入调用方 secret | 开启 ORS 时由账号所有者做 | 仅路线/等时圈保持 unconfigured |
| 代表样本、使用目的和人工匹配/质量判据 | 现场验证前由负责人确认；已有获准材料可复用 | runner 可先完成，实测 blocked |
| 付费订阅或自建服务器 | 当前不需要 | 免费能力继续试用；量大/质量不足再单独决策 |
| 人口分析、公交/JVM、独立服务部署 | 当前不需要 | 维持原 POP/E06 延后范围 |

完成定义：所选来源有可追溯试用结论、实际调用方限额和明确关闭路径；未选来源允许 disabled。发布包、生产可用与消费者已接入各自凭证据标记，计划文件更新本身不改变任何验收门状态。
