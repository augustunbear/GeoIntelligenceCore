# GeoIntelligenceCore project status

Updated: 2026-11-04.

- **Decision confirmed**: independent shared private repository `augustunbear/GeoIntelligenceCore`, separate from RestaurantTrafficDiagnosis.
- **Delivered**: initial documentation-only foundation: README, contributor instructions, architecture, ADR, open-source inventory, provider/data handling policy, draft contract, roadmap.
- **Not delivered**: Python package, source code integrations, runtime GIS APIs, CI, tests, releases, hosted infrastructure or consumer wiring. Do not claim otherwise.
- **Known risks**: German address match and POI coverage unverified; public OSM API operational restrictions; commercial geodata redistribution; PostGIS availability in target Neon not checked; census grids are historical.
- **Design baseline in this branch**: complete functional design F-01–F-13, shared rules G-01–G-10, food-service templates T-01–T-03, cross-industry scenarios V-01–V-08, ADR-0002 and planning handoff. This describes intended behavior, not implemented functionality.
- **Next task**: use docs/plans/IMPLEMENTATION_PLANNING_HANDOFF.md to generate a step-by-step implementation plan; map every requirement to an acceptance scenario and explicitly scoped work item. Reconcile the earlier roadmap and contract draft. Verify providers and rights before adopting them; do not start implementation merely because design documents exist.
- **Consumer boundary**: RestaurantTrafficDiagnosis retains consultant UI, case isolation, domain-specific reasons and evidence approval. GeoIntelligenceCore provides geospatial facts only.

## Open-source selection research (2026-11-04, this branch)

- Recorded 31 candidate projects, source-backed per-function selections, ADR-0003 and integration blueprint A01–A11.
- New findings: HeiGIT routing hostname migration; current ORS forum evidence says CC-BY-SA 4.0; OTP legacy TravelTime removal; R5py uses a paired JAR and emits isochrone lines.
- Research is desk verification only. No install, live-data quality benchmark, performance test, complete security scan or deployment has been performed.
- Current full ORS account terms/quotas were not readable through retrieval. Production activation requires those records and a permitted endpoint; no unlimited public-service dependency is approved.
- Next: generate detailed implementation steps using F/G/T/V requirements and A01–A11 gates, not a new unbounded library survey.

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
