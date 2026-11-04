# SECON 2027 执行侧独立验收状态

## 当前状态：必需 P0/P1 完成交付，条件 P2 未开展

更新日期：**2026-11-04**。本次状态覆盖正式 raw 分块归档干净恢复、两套
独立统计复核和 2.1.30 promotion fixtures 完成之后，最终 v3 稿件/PDF、可恢复包及精确远端发布核验均已完成。
**95 项逐一有结论：90 项已完成或边界已核，5 项条件未触发；不把未开展的硬件项目写成已验证，不宣称已经投稿。**
本文件只更新执行侧记录；监督方原 `secon2027_acceptance_matrix.md`、
冻结 method decision、contract、plan 和历史科学证据均不改写。

- **正式研究证据已完成：**唯一 frozen plan
  `5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0`，
  snapshot `63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee`，
  tested **2.1.29**。760/760 completed，0 failed、0 missing；480 main、120
  clean controls、160 extra deadline runs，38 case/arm groups 各保留 20 seeds
  2027100–2027119。方法/矩阵/统计未因正式结果改变，未追加或替换研究 seed。
- **审计和统计已完成：**全量保存源码审计、监督方 raw/exposure/statistics
  审查及执行侧独立 final statistics review 均有落盘证据。1,330 summary、
  90 metric contrasts、1,800 paired-seed effects 复核一致，74 undefined
  summary rows 保留 n=20。CI 是 10,000 次 seed-paired bootstrap 的描述性、
  未校正 95% 区间；没有显著性/非劣性/普遍获益结论。
- **原始归档恢复已完成：**11 块重组 SHA 与 whole archive 一致，14,667
  成员逐字节校验；全新恢复目录使用保存审计器得到 760/760 complete、全部
  760 audit workers exit 0。该恢复不产生新仿真。原始包可恢复不等于最终
  GitHub closeout、匿名 review artifact 或论文包已经发布。
- **版本和保全已核：**promotion 为 **2.1.30**，pre-promotion regression
  161 passed，post-promotion fixtures 34 passed。166 项 formal frozen
  inputs 中 165 项不变，仅 `VERSION` 改变；新增复现/诊断/绘图工具另列，
  不能把整个仓库称为只有 VERSION 变化。全部正式 manifests 仍是 tested
  2.1.29。ICC/imported-paper 182 项在 isolated 与 canonical 两处的 hash
  均未改变。固件仍为 0.1.4，未开展新板级/RF/功耗实验。
- **结果和边界已写入：**`docs/results/secon2027_evaluation.md` 已列全
  主比较、控制、稳健性、实际 CI 和不利结果；保留 S3 recovery 的确认率
  损失、deadline 10 s recovery=0、85 initial-path /87 all-kind /86
  DATA-only fault-exposure 人群及 4/3 跨界口径。原机制报告未改写。
  正式启动后的行政勘误仍按真实时序披露：43 completions 时暂停、全部
  20 seeds 已暴露、09:09:21 UTC 勘误晚于 09:06:36 UTC 首次启动。
- **最终论文已验：**v1十页草稿已被v3取代；最新PDF为9页IEEE10pt，
  SHA256 `e477617e417a5c089bfeac3f4725e40e54e39e666071a1711c5c0e0f749eb1fd`，186064B。三轮逐页视觉核验、26字体嵌入、27引用、
  匿名metadata/链接均通过；915MHz及无duty-cycle/LBT已明确。原始失败
  草稿和v2核验保留为历史，不是当前待办。
- **最终发布已验：**2.1.30artifact commit `e653315803c46abf80fb6d3476eee3b5f7fd34a4` 与认证GitHub远端一致。
  raw发布30e7bd42包含114个小分片；完整归档hash不变。最终analysis/paper包
  1230文件干净恢复通过，四份CSV和四张PNG重画后逐字节相同。文稿、数据、
  统计和seed不因传输重包装改变。最终文件和完整校验说明位于用户outputs。

本次新增的是文档状态核对：读取现有报告、日志、hash 和实体产物，不运行
模拟、重复研究 seeds、重跑全量审计或改写 frozen evidence。以下原历史
95 行表与时序完整保留；**尾部“完整 95 项最新状态映射”才是本次各 ID 的
当前判断**。历史段落中的“尚未冻结／待正式／无结果／push 待重试”只描述
其原写入时点，不构成当前待办或对已完成正式证据的否定。

## 历史记录（原文保留，状态按各段原时点解释）

核对日期：2026-11-04。时点：修复后 development pilot v2 已完整审计，
正式 760-run 候选尚未冻结；2.1.29 正在准备发布。
本文件是隔离执行副本的本地验收记录，**不覆盖、不改写监督方
`secon2027_acceptance_matrix.md` 的 95 项原要求或其判定**。
“开发已验”不代表正式实验或最终论文已完成。

本轮只读原要求、代码接口、现有计划/日志/审计/文稿，并核对已有分析文件
哈希；未运行仿真、重放研究 seed、修改代码、注册 cohort 或发布。
原始事件审计以已保存的审计报告及其源码身份为依据，本轮没有再扫描全部
72 个 run 的所有 RX/TX 账本。此前独立完成的确定性回归与矩阵静态核对
在下列证据中明确列出。

## 当前证据锚点

| 代号 | 已读取的证据及范围 |
| --- | --- |
| P | `secon2027_provenance/source_import.json`、历史 seed 库存、导入 commit `a0ee4ce7bb96592c57dc5f389cf4c1958bec0069`、checkpoint；488 项工作状态导入及保守历史 namespace 排除。 |
| T | `results/secon2027/gates/pilot-v2/frozen-test-command.json`、`frozen-tests.log`：保存源码 `ee890e25030782fc01208ee4ce1f20863c6ade5322ac954ad67ae48b594056a2`，tested VERSION 2.1.28，161 passed；含核心、runner、外部 registry、scenario、恢复、冻结 worker、分析器测试。 |
| V | `results/secon2027/gates/pilot-v2/audit.json`：72 completed、0 failed、0 missing，plan SHA `0c49a69a5c3725c9f72ff2e28ed870d10db1df7eec4319f6397097b84a2c85e7`；audit 文件 SHA `af181d12025fe8a89bb0b7b247e6a2b43aae1fc08fe1921ea788cba87b39b525`。 |
| X | `results/secon2027/analysis/development-pilot-v2/analysis.json`：complete，72 runs，n=3、small_sample_unstable=true；文件 SHA `ea55d1ca957806838b2ece6907d66a5bef07d238fa115520d0002400a02e8ca3`；本轮对其 22 个输出的大小和 SHA 逐一核对，零不符。 |
| R | `results/secon2027/gates/pilot-v2/resource-costs.json`：72 runs 累计 301.925714167 s，单 worker 最大 RSS 360251392 B，raw attempts 706194269 B；文件 SHA `04e8d527c0676770c65a678102d3b7c6a12c511e79a3eed76931bd04163404bc`。 |
| C | `secon2027_correctness.md`、`secon2027_algorithm_spec.md`、`secon2027_supervisor_recovery_branch_review.md`，以及 pilot-v2 的 recovery rejection red/green 日志：真实失效路由拒绝分支 NameError 已修；独立 missing/quarantined/new-generation/expired 负向和 READY 正向 fixture 验证。 |
| M | 聊天工作目录 `work/formal-matrix-candidate.json` 与 `work/formal-matrix-review.md`；静态核对 480 main +120 clean controls +160 deadline robustness=760，无重复 case/arm/seed，三项 control 仅差名称及对应开关。最新候选预算已经由 R 估算，仍待正式 gate/冻结。 |
| B | `secon2027_baseline_fidelity.md`、`secon2027_pilot_preflight.md`：四模型和官方产品边界、实际 default/matched 参数、common environment、结构替代路径和无源节点 oracle。 |
| A | `secon2027_analysis_spec.md`、分析器 18-test/实际重分析记录：完整账本重算、seed bootstrap、有效参数配对、undefined 保留、负载连线。较早 supervisor analysis 文档的 A4“待修”是历史版本状态，后续版本已有关闭记录。 |
| Q | P0-v3 的 142-test/21-run 审计、fixture 92000 确定性重放；P0 887-member archive 及 supervisor 干净恢复审计。它们不代替 pilot 或正式结果。 |
| F | pilot-v1 `incident.json`、incomplete-audit 和失败归档：48 complete /1 scientific-or-worker failure /23 unstarted，原源码/attempt 保留，未伪装基础设施重试。 |
| G | `docs/project-management/secon2027_release_map.md`：2.1.28 远端 commit `a64b2d92f2778089534700cbaa27d2ca453303ea` 已核；2.1.29 promoted regression 当前为 58 passed，commit/push/可恢复 pilot 包仍由根执行收尾。 |
| W | 独立 `paper/secon2027/` 当前为内部稿，方法 10 组公式，26 个已核验 citation keys；`secon2027_paper_blueprint.md`、`secon2027_claim_evidence.md`；无正式性能结论。 |
| O | `secon2027_official_requirements.md`、蓝图中 IEEE Conference Author Center AI policy 原文/URL/响应 hash；10pt、≤9 页包含全部内容、双盲，deadline 时区未自行推断。 |
| H | `docs/results/secon2027_firmware_validation.md`：固件仍 0.1.4，本轮无新固件/板级/RF/功耗实验，无官方产品硬件比较。 |

当前分析器实际运行环境是 **Python 3.9.6 / NumPy 1.26.4 /
Matplotlib 3.7.5**（X）。复现文档曾记录另一轮分析的
Python 3.14.8 / NumPy 2.5.3 / Matplotlib 3.11.2；最终文档须分阶段记载，
不能把后者写成当前 pilot 的环境。这里不将环境不同本身判为结果错误。

## 95 项执行状态映射

状态定义：**开发已验**＝当前保存源码/开发证据覆盖；**进行中**＝有证据但
最终闭环尚未完成；**待正式**＝需已冻结的正式数据；**待最终**＝需最新
交付物/发布/PDF；**条件未触发**＝已记录不适用依据，后续事实变化时复核；
**已限定**＝方法或主张边界已明确，最终文稿继续遵守；**已披露**＝未实施事项
及其边界已有明确记录，不能据此声称对应验证通过。
每个 ID 均保留，不以新增检查取代原验收要求。

| ID | 当前状态 | 已有证据／实质剩余项 |
| --- | --- | --- |
| A01 | 开发已验 | P：实际工作状态隔离导入；managed attachment 不成功已披露，不妨碍明确路径工作。 |
| A02 | 开发已验 | P/checkpoint 记录任务书、规划、交接及审查阅读；最终版本索引与当前状态同步。 |
| A03 | 进行中 | P 保留原资产和差异；最终 scoped commit 及 canonical/ICC 未改核对待交付。 |
| A04 | 进行中 | O 执行前规则和 IEEE AI 政策已核；最终 PDF/投稿候选规则复核待做。 |
| A05 | 进行中 | checkpoint 有 P0、429 恢复、pilot-v1 failure/v2 时间序列；需补 v2 完成和后续正式动作。 |
| A06 | 进行中 | Q→T/V/X 顺序有证据；方法 gate→正式冻结→验证→论文仍未完成。 |
| A07 | 进行中 | W 独立 SECON 项目已建立；最终 ICC 保全核对和候选 PDF 待验，无自动投稿动作。 |
| B01 | 开发已验 | T/V 保存实际完整源码；Q 已独立恢复；正式 snapshot/归档依后续计划。 |
| B02 | 开发已验 | P 全量历史库存及 0..999999 保守排除，旧 92200/92300 队列按已暴露处理。 |
| B03 | 进行中 | development registry/exposure 已落盘；新 validation cohort 必须在正式冻结前登记。 |
| B04 | 开发已验 | T 的跨 arm 首次暴露、身份/版本绑定测试；V 72 个完整计划键。 |
| B05 | 开发已验 | T 包含 external/CPR explicit-seed 负向测试；正式入口要求保存计划。 |
| B06 | 开发已验 | T 包含未 gated validation、cohort 变更和四模型完整 pilot gate 负向测试。 |
| B07 | 开发已验 | T 独占 key/输出前缀、不可覆盖测试；F 真实失败 attempt 保留。 |
| B08 | 开发已验 | T 部分导出/缺证据/空 inventory 被拒；V 完整原始包通过，正式包待逐 key 核对。 |
| B09 | 开发已验 | T 外部 registry/unknown-arm 不污染测试；V arm 身份吻合。 |
| B10 | 开发已验 | T schema/scenario 测试和 V 真实 S1/S2/S3 CLI 执行；M deadline 分支静态合法。 |
| B11 | 进行中 | 新合同审计 T/V 已验；历史合同/manifest 保留，最终复现包明确旧审计入口与冻结 source-root。 |
| B12 | 进行中 | T dead-process 恢复与拒绝 scientific reclassification；Q 干净解包审计通过；pilot/formal 新包恢复待最终。 |
| C01 | 开发已验 | C/T 冷启动/恢复回源、seen 过期、malformed path 在副作用前拒绝。 |
| C02 | 开发已验 | C/T 并发 ACK、旧 ACK 不回滚新路由、generation/revision 防旧 timeout。 |
| C03 | 开发已验 | C/T 错流/端点/path/sender/marker、未启动 stage、迟到与 replay 保留拒绝。 |
| C04 | 开发已验 | V/X 全 scheduled denominator；正式仍保留 no-start/drop/unreachable。 |
| C05 | 开发已验 | C/T/V request→commit→TX→RX→ACK 与 cutoff，未来预留不计 physical TX。 |
| C06 | 开发已验 | C/T committed 边界、decoded-check/success 分开；V/X 物理成本不反减。 |
| C07 | 开发已验 | C/T source stage 上界、timer ties；新增真实 stale-route recovery 拒绝回归覆盖原 pilot 缺陷。 |
| C08 | 开发已验 | T 容量/eviction、重复、计时边界 fixtures；开发真实零容量暴露不替代这些测试。 |
| C09 | 开发已验 | T 161 项冻结测试，Q 重放，V 完整修复后 pilot；正式依自身 snapshot。 |
| C10 | 开发已验 | F 原 v1 incomplete/failure 保留；Q/tested2.1.27、V/tested2.1.28 与 promotion 分开。 |
| D01 | 开发已验 | B/W 明示 MT-like/MC-like 与官方机制差异；正式图文继续使用模型标签。 |
| D02 | 待正式 | V/X 已有四模型 default pilot；M 规划完整正式 default 结果。 |
| D03 | 待正式 | B/M 匹配规则和实际参数已核；完整正式 matched 比较待执行。 |
| D04 | 开发已验 | B/T/V/X common environment/trace 身份和协议 draw 无关性；正式配对重复审计。 |
| D05 | 开发已验 | B/C/V 本地可见信息、全 wire ToA 和无 oracle；不声称真实产品 wire equivalence。 |
| D06 | 条件未触发 | M 未采用 common-ACK 或新强化基线；已有可选 variant 未冒充四主模型。 |
| D07 | 待正式 | C/M noackcancel 仅改 ACK 开关，capacity 保持；正式效果和原因暴露待出。 |
| D08 | 待正式 | C/M no-repeat nominal slot 已规格/测试；正式两场景消融待出。 |
| D09 | 待正式 | C/M no-recovery 保留 repeat；正式两场景消融待出。 |
| D10 | 条件未触发 | X 全 72 runs capacity_eviction_count=0，W 无全系统内存优势主张；若正式触发则按条件复核，不能静默省略。 |
| D11 | 待正式 | M 同 case CPR/control 三开关纯净且完整 20-seed 配对；尚未冻结或运行。 |
| E01 | 进行中 | V/R 成本完整；X 有真实 repeat/recovery/cancel，多跳/故障/压力独立机制解读待根合并。 |
| E02 | 进行中 | F/C 缺陷修复闭环；完整 pilot 的失败原因、保留 CPR/候选选择及 method gate 待签实证。 |
| E03 | 条件未触发 | 当前无额外新算法候选；一行 import 修复不伪装新研究方向。 |
| E04 | 待正式 | M/analysis policy 已静态核；method gate、正式 cohort、source/config/contract 一次性冻结待完成。 |
| E05 | 进行中 | R→M 预算已包含 760 runs、4 workers、2×余量；正式 gate 需保存计算与所选 n=20 依据。 |
| E06 | 待正式 | V/X 的 S1 是 development；正式稳定场景结果和无谓开销待报告。 |
| E07 | 待正式 | B/M 结构替代路径；X 有故障暴露，需正式 raw 证据解释实际路径与恢复。 |
| E08 | 待正式 | V/X S3 已实际执行；正式碰撞/半双工/排队/expiry/cancel 分解待出。 |
| E09 | 待正式 | 开发实际跳数由 X/机制报告提供；正式不得用 H=6 替代实际多跳分布。 |
| E10 | 待正式 | M 有 S2 matched deadline 10/30/60 的有限轴；160 新 robustness runs 待执行。 |
| E11 | 进行中 | M 明示 deadline 同时改变 drain/cutoff，其他输入固定；正式保留该解释。 |
| E12 | 进行中 | B/M/W PHY、全字节、捕获/半双工及无监管访问/RF 校准边界；最终配置表待定稿。 |
| E13 | 待正式 | F 已保留真实失败先例；正式全 key、失败/负结果及不调参边界待实际贯彻。 |
| F01 | 开发已验 | C/V/X 从 timestamp 重算两成功率；正式报告继续全 scheduled 分母。 |
| F02 | 开发已验 | A/V/X 物理 TX ledger 与 packet-kind×stage 加和；正式成本图待出。 |
| F03 | 开发已验 | A/X 零分母 undefined、成功流延迟带 unfinished；正式表/图待出。 |
| F04 | 进行中 | X physical stage/cancel/capacity 计数存在；正式解释须按 reason 区分拒绝，不按 action 名猜 deadline。 |
| F05 | 开发已验 | A/X seed 单位、paired effect、10k bootstrap；正式 n=20 仍无独立 packet 样本量声称。 |
| F06 | 已限定 | M/W 仅 descriptive unadjusted 95% intervals，不作 multiplicity-controlled significance 或 noninferiority。 |
| F07 | 待正式 | X 开发图可重画且本轮 22 文件 hash 验证；W 有 timing diagram；正式主图/消融/robustness/延迟成本图待完成。 |
| F08 | 待正式 | W claim register 已区分规格/测试/P0/pilot/正式；最终每条数值追溯链待填。 |
| G01 | 进行中 | checkpoint 实体已存在；需 current-state 摘要避免旧顶栏版本/状态误导。 |
| G02 | 进行中 | 合同实体已有；formal freeze 表、实际方法/样本量/场景标准及新源身份待更新。 |
| G03 | 进行中 | development registry 完整；正式 cohort/冻结/首次暴露记录待实际生成。 |
| G04 | 待正式 | M 为候选，尚非 repository 内冻结 experiment matrix/plan；最终允许等价路径但需导航。 |
| G05 | 开发已验 | B fidelity 文档已具备，正式保持来源与模型标签。 |
| G06 | 进行中 | C 规格完整，近期加入 stale-route 拒绝语义；最终锚定 formal snapshot。 |
| G07 | 待正式 | `docs/results/secon2027_evaluation.md` 在核对时尚不存在，需完整正式结果/负结果。 |
| G08 | 进行中 | W claim register 已建立；v2 完成状态和正式图→run→manifest→source 链待同步。 |
| G09 | 进行中 | Q 干净恢复及已有复现指南；补 V/formal 实际命令、每阶段依赖版本、耗时/空间、重算/重画和最新包恢复。 |
| G10 | 待最终 | `secon2027_submission_checklist.md` 尚不存在；最终匿名/格式/政策/PDF 检查须实测落盘。 |
| G11 | 已披露 | H 无新增固件/RF/功耗，不把旧 native/build 当新 RF 证明。 |
| G12 | 进行中 | G release map 存在；2.1.29/最终发布 append 实际回归、archive、commit 和远端 SHA。 |
| G13 | 进行中 | W 独立源码/10 方法公式/26 引文存在；results/abstract 仍内部稿，待正式数据。 |
| G14 | 进行中 | W 匿名 author/metadata 和无虚构 funding；最终导出后仍需文本/metadata/链接实际扫描。 |
| G15 | 待最终 | 无经最终内容绑定的导出 PDF 页数、字体及逐页视觉验收；内部编译不等于通过。 |
| G16 | 待最终 | 内部 recoverable archive 与匿名 review artifact 分开；正式包和公开/审稿链接去身份检查待完成。 |
| H01 | 进行中 | T 保存本轮 tested source，G 原始 import→一行修复范围清楚；正式轮次另存 snapshot。 |
| H02 | 进行中 | T/V 完成后才准备 2.1.29，58 promoted fixtures 已通过；最终轮次继续同样顺序。 |
| H03 | 开发已验 | G/Q/V/F tested 与 promoted 版本分开，未改旧 manifest；正式继续保留。 |
| H04 | 开发已验 | 2.1.29 promoted regression 58 passed，包含 fixture worker；没有通过重跑 validation 来升版。 |
| H05 | 待最终 | G 的 2.1.28 scoped commit 已有；2.1.29/最终提交及从 commit/独立包恢复的映射待核。 |
| H06 | 待最终 | 2.1.28 远端 SHA 已确认；2.1.29 和最终交付 push/远端 SHA 待实际记录。 |
| H07 | 进行中 | 既有分支/版本冲突检查和无 tag 声明保留；下一轮按实际结果记录，不覆盖历史发布。 |
| H08 | 已限定 | H 固件版本不变；G 披露 2.1.28 后发现缺陷，最终负结果措辞仍须准确。 |
| I01 | 条件未触发 | 本轮未承担固件变更/native/板级新 gate；历史问题由 H 明示。 |
| I02 | 条件未触发 | 本轮无 RF/功耗测量，且不以设备缺失阻断已授权仿真主线。 |
| I03 | 已限定 | B/H/W 无官方产品硬件、实物认证或电池续航优势主张。 |
| J01 | 进行中 | M 有实测预算和有限范围；持续按真实运行成本调整排期，不能删必需内容。 |
| J02 | 待最终 | 最终 source/version/commit+恢复包+远端 full SHA 未完成。 |
| J03 | 待正式 | 四模型 default/matched、120 controls、160 robustness 均需实际完成和审计。 |
| J04 | 待最终 | 正式原始证据→独立审计→统计/重画→主张链及失败记录尚未闭环。 |
| J05 | 待最终 | G01–G12 逐项实体内容收尾；H 披露已具备。 |
| J06 | 待最终 | 独立匿名、IEEE 10pt、≤9 页最新 PDF 与适用政策实际检查尚未完成。 |
| J07 | 待最终 | 最终说明须同时链接真实结果、未证明范围、候选 PDF、可恢复包和远端 SHA；不得将本阶段称整体完成。 |

## 正式 760-run 与论文之前的实质剩余工作

1. **开发决策与冻结。** 合并独立 pilot 机制报告，记录保留当前 CPR 的依据，
   对 S1/S2/S3 的实际多跳、故障、争用和动作暴露给出解释；冻结不据正式结果
   改动的场景/主张规则、n=20 精度与成本理由、分析和失败规则。候选应变为
   明确的 repository matrix、validation cohort、method gate 和唯一 formal plan。
2. **完整正式执行与审计。** 运行全部 760 预定键，保留失败和未完成项。
   不把 pilot、旧 ICC 或只完成的有利子集补成正式结果。审计通过后才能生成
   全量统计；三控制、两额外 deadline 点和两套主配置不能遗漏。
3. **完整分析与文稿证据。** 输出 default/matched 主比较、清洁消融、deadline
   稳健性、两点 load comparison、成功流延迟与失败比例、packet-kind×stage
   成本及原因诊断。以正式结果填写 evaluation/claim register/results/abstract，
   保留负结果和无收益条件；禁止把局部取消次数直接换算总网络因果节省。
4. **最终复现与发布。** 补实际版本/命令/依赖/资源/计划导航，保存全部原始事件、
   失败包、source snapshots、配置、分析源码和输入/输出 hashes；对最新包做
   干净恢复和原始重算/重画。限定 commit、验证远端 full SHA，并保证大原始包
   有明确可恢复位置；仅本地存在或一个 commit 名称不等于可恢复完整交付。
5. **最终 PDF。** 完成独立稿件后对同一最新导出文件保存源码/PDF hashes、
   编译日志、`pdfinfo`/`pdffonts`/`pdftotext` 或等效实测和逐页视觉检查。
   ≤9 页含引用/附录，IEEE 10pt，无遮挡/截断、可读图表、无身份泄漏。
   AI 披露准确反映实际系统/章节/程度；不填虚构 funding。ICC 是否实际提交及
   内容重叠、官方截止时区/注册细节在候选投稿检查中保留明确状态；没有自动 EDAS。

预算已从完整 pilot 改为测量驱动：预计串行 **3314.82 s**、raw **7.511 GB**；
四 worker 理想时间 **828.71 s** 只是无竞争估算。单 worker 实测峰值
360251392 B，四个峰值合计 1441005568 B，host 17179869184 B；候选规定
2×时间/存储余量、18 GiB raw cap。该预算包含 main/control/robustness，
不保证控制或不同 deadline 的实际成本严格线性，实际资源仍须记录。

## 拒绝原因和时序的最终验收口径

- `DROP_DEADLINE_INFEASIBLE` 是现有 action 枚举名称，不是对每次拒绝的
  原因证明。特别是 `reason=stale-route-generation` 可表示 route 缺失、
  QUARANTINED、generation 改变或到期，且当时仍可能有充分 deadline slack。
  报告应使用记录的 reason，并在必要时联结当时 cache 状态；它也不必立即
  终止整个 live flow。
- `repeat-deadline-infeasible`、`recovery-deadline-infeasible` 等真实预算拒绝
  与 `stale-route-generation`、`recovery-disabled`、`repeat-slot-not-elapsed`
  分开；不得把所有 protocol-no-start、所有 DROP action、所有未 ACK 流都
  分类成“时间不够”。请求表的聚合 status reason 不能替代 action 时间/阶段联结。
- request 的候选 `start` 非空不证明已发送；只有 started 状态、TX ID 和
  physical ledger 的一致联结才收费。commit 可以早于 reserved physical start，
  因而“ACK 在 start 前到达”也不证明仍可取消。
- destination delivery without timely ACK、无法交付 DATA、ACK 被拒绝、
  pending 未启动和队列拖延分别报告。只有具体 RX/ACK 证据可支持相应失效原因，
  不能从一次 missing ACK 推断其链路坏了或 route 已物理断开。

现有 X 汇总中，原始 72-run 计划合计有 662 次 physical source repeats、
538 次 physical source recoveries、234 次 ACK cancellation successes、
122 条初始 source path fault exposure（均有 hop-budget 内结构替代），
capacity evictions 为 0。这些仅用于证明开发诊断字段存在并有机制暴露；
default/matched 中的相同有效配置和相同三 seeds 会重复观察，不能把合计当
独立样本量或正式性能优势。最终机制解释以独立报告及正式事件为准。

结论：当前没有必要重开已关闭的核心实现修复或追加未触发的 RF/大规模扫描。
必需未完工作是正式冻结与全矩阵证据、完整论文/PDF、最终复现/发布及对应文档
内容闭环。只有这些适用项目完成，才可将整体任务标为完成。

## 追加：正式 v1 冻结后的独立静态核验

核验日期：2026-11-04，正式执行前。本节更新上文时点记录中的“尚未冻结”
事项，不将计划、构造器或通过测试写成已完成正式实验。采用只读
`verify_plan`、文件 SHA/大小、JSON 对照及不绑定 simulator 的协议构造器
核验；没有调用 `audit_plan`、解析 seeded environment、生成研究流量、运行
仿真或修改 registry/plan/gate/contract。

**判定：未发现阻止该冻结计划开始执行的实质问题。**

| 身份 | 独立重算/核对结果 |
| --- | --- |
| Formal plan | `results/secon2027/plans/formal-v1.json`；canonical plan SHA `5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0`。 |
| Saved source | `63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee`；166 个文件逐一 SHA/大小和完整 inventory 核对通过，tested VERSION 2.1.29。 |
| Matrix | `configs/secon2027/experiment_matrix.json` 与 plan 内嵌 matrix 完全相同，canonical SHA `3cc6bab3de7c7767c3fbf845deb156f945db13d98361f0dc5b7bf7e769cc6ea3`。 |
| Contract | 当前文件、保存源码、plan、gate、registry 均绑定 `0db4fc2e724f441e190693e3f8d37b7912e2d4baa5555515c6f132481f309eff`。 |
| Development gate | `development-method-freeze.json` 与 plan 内嵌 evidence 相同，status=passed、method_frozen=true；method decision SHA `5b842194f59719e47a42f79f24b03aafc0b92597d382907df01b3acdd32f59ba`、pilot mechanism report SHA `e2cbd45cad6581e62789064ac15cf5e17409e34b51c7ad509d32ac031afed02a` 与实际文件一致。 |
| Method continuity | gate 指定的 7 个方法文件在 checkout、formal snapshot、完成的 pilot-v2 snapshot 中各自 SHA 全部相同；没有新增策略或 pilot 后静默调参。 |
| Frozen tests | `results/secon2027/gates/formal-v1/frozen-test-command.json` 的 cwd/snapshot/exit 0 正确；日志为 **161 passed, 11 warnings in 14.26 s**。本轮只读取该结果，没有重跑测试。 |

Registry 核验时只有一个 active formal plan，760 个唯一 planned keys 与 plan
严格相同；20 个 seeds 正好是 2027100–2027119，全部 reserved，
first_run_at=null、execution_history 为空，760 个 formal run 目录均尚不存在。
与其他 cohort seeds 和历史排除区间无交集。这里记录的是核验当时的未暴露
状态，后续合法执行会更新 registry，不应把该历史记录当作实时状态。

全部 `(case, arm, seed)` 唯一，分组数量是 S1-default/matched 各 80、
S2-default 80、S2-matched 140、S3-default 80、S3-matched 140、
deadline 10/60 两组各 80，即 **480 主比较 +120 controls +160 robustness**。
六组主场景的 case/environment/deadline 与 pilot 一致，仅 S2/S3 matched
增加预定 controls。两组 robustness 与 S2-matched 的数值场景/环境一致，
仅标签和 deadline/drain 改变，30 s 参考直接使用 main S2-matched。

所有 case 构造器及所用 arm 参数验证通过。对 S2/S3 matched 分别解析实际
primitive protocol 参数，三 controls 相对 CPR-matched 均只差 `name` 和
对应 `cancel_on_ack`、`enable_repeat` 或 `enable_recovery` 的 true→false。
没有使用旧的 whole-ledger `nocancel`；不把相同 CPR/ME default/matched
当作 n=40。原有 nominal repeat slot、ACK-only-off capacity 保持语义仍由
相同源码和通过的冻结测试支撑。

合同的一次冻结节已明确前瞻条件：S1 实际 routed send 和至少两跳 accepted
ACK path；S2 实际 fault-edge intended-hop physical TX、active carried-path
intersection 及 ≤6-hop 结构替代；S3 各 seed 的 S3>S1 offered count 和各
regime 的 intended-hop collision/half-duplex 暴露。它们限制可写主张，
不排除或替换未达条件的 seeds。重复/恢复/取消组件零暴露仍报告其无暴露
限制；队列、容量零记录和 unknown peak occupancy 不被改写成饱和结论。
method decision 保留 S3 不利结果并选择固定 CPR 的权衡测量，未宣称拥塞
适应、普遍效率或真实产品优势。

样本量 n=20 已用有限描述性精度和实测成本说明；10,000 次 paired bootstrap、
95% unadjusted descriptive intervals、analysis-only seed 20271104、全部
失败/undefined 保留及无精度停止/替换规则与 matrix 一致。deadline 10/30/60
同时改变 drain/cutoff，两个负载点不建立 saturation threshold。4 workers、
2×余量、18 GiB/4 h envelope 和仅显式基础设施重试的边界均已保存。

因此 B03、E01/E02、E04/E05、G02/G03/G04 中的开发决策、登记及一次正式
冻结子项已闭环；其实际结果及其余待正式/待最终项目仍未完成。合同开头
的 development-draft 状态、旧候选静态报告的 not-freeze-ready 和 registry
顶层 reserved-before-freeze 是保留的早期状态文字；以同合同后附一次冻结节、
当前 gate 和 cohort 的 active plan 身份为准。该文字遗留不改变已核验的
授权/方法/键集合，不应为修饰状态文字重写已冻结合同或重新选择 seeds。

## 追加：正式启动后的行政勘误、暂停与同计划续跑

本节记录后续真实时间顺序，更新上一节“正式执行前”的时点状态。正式
执行已经开始，不能再把当前 cohort 称为未暴露，也不能声称合同开头的
文字在首次运行前已被更正。

1. Development gate 于 **2026-11-04T09:01:06.320060+00:00** 登记，原
   formal plan 于 **09:01:52.961637+00:00** 冻结，保存源码 161 tests 通过。
2. 第一个正式 key 于 **09:06:36.647153+00:00** 开始，晚于 gate 和 freeze。
3. 对合同旧 opening 的矛盾提出关注后，根执行停止新的 dispatch，向
   dispatcher parent PID 83150 发出 SIGTERM；四个在途 CLI workers
   正常收尾。暂停结算为 **43 completed、0 failed、717 unstarted**，
   **全部 20 seeds 2027100–2027119 均已 exposed**。
4. 于 **09:09:21.850292+00:00** 记录行政勘误及暂停清单，随后在
   `results/secon2027/gates/formal-v1/dispatch-resume-001/` 沿原计划续跑。
   已完成 keys 先验证并跳过，仅未完成 keys 产生新执行；本次续跑不是
   infrastructure retry，也不重新创建已完成 key 的科学 attempt。

勘误是 `docs/research/secon2027_formal_contract_erratum.md`，本轮读取时
SHA `24cb723f156e45e9ed44b1a9bbfb4f40346dbca8457a22803927216f1f0ea0e4`；
暂停清单是 `results/secon2027/gates/formal-v1/administrative-pause.json`，
SHA `84c11038a3f2aa59e46d4129c4b292a7a64a30f5e257a7ba129f6246093f603f`。
勘误承认它在执行后写入，保留原合同 bytes，明确后附一次正式冻结节是
适用的阶段规定；没有假称改写后的合同继续具有旧 hash。

只读复核确认原 contract SHA `0db4fc2e724f441e190693e3f8d37b7912e2d4baa5555515c6f132481f309eff`、
plan SHA `5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0`、
matrix SHA `3cc6bab3de7c7767c3fbf845deb156f945db13d98361f0dc5b7bf7e769cc6ea3`、
保存 source 身份及 7 个 method 文件 hash 均不变，gate 与 plan 内嵌 evidence
仍相同。暂停清单列出的 **43 个 completion 文件 hash 全部一致**，各 key
仍只有原 `attempt-001`。续跑 dispatch 指向相同 plan、无 `--retry` 标志；
首个已完成 key 的续跑日志为 `verified-existing`。

该次核验未读取或生成部分性能汇总，未运行仿真、改 seed/方法/参数/场景/
arms/统计或主张门槛，也未改变历史 manifest。未发现此次行政勘误引入
科学配置变化，不构成对已明确授权的同计划续跑的新增阻碍。最终复现包
及稿件须保留此时序与勘误，fresh 仅可描述首次执行前的登记状态。

发布状态在本轮仍单独记录：本地已存在 commit
`95eee87e7757bcd8316088fee2517bc6a796801d`（2.1.29），根执行报告 push
连接失败、待重试。本轮未取得该 commit 的远端 full SHA 验证，因此不将
本地提交写成已完成远端发布；后续以实际成功及远端核验记录更新。

## 完整 95 项最新状态映射

本表逐一对应监督矩阵的原 95 个 ID，不合并或删去条件项。状态含义：
**已验**表示本行规定范围有现存证据；**科研已验／待最终**表示科学部分
完成但稿件或发布关口未完成；**进行中／待最终**不算通过；**条件未触发**
须有明确依据，不能算成做过实验；**边界已披露**只确认没有越界主张。
硬件 P2、未采用的 optional variant 和未触发的 ledger-capacity sweep
分别列项。正式结果不要求所有比较获益，负结果保留是验收条件。

### 本次证据索引

| 代号 | 实体证据与已观察范围 |
| --- | --- |
| NF | `results/secon2027/plans/formal-v1.json`、`gates/development-method-freeze.json`、`configs/secon2027/experiment_matrix.json` 与 `seed_registry.json`；method decision SHA `5b842194f59719e47a42f79f24b03aafc0b92597d382907df01b3acdd32f59ba`、contract SHA `0db4fc2e724f441e190693e3f8d37b7912e2d4baa5555515c6f132481f309eff` 均保持原值；正式 freeze/首次暴露/行政勘误另有记录。 |
| NQ | `results/secon2027/gates/formal-v1/frozen-test-command.json` / `frozen-tests.log`（冻结源码 161 passed）；`audit.json`（760 complete）；`docs/research/secon2027_supervisor_formal_raw_review_verified.json`（完整 raw 独立核验，旧 checker ACK flags 的纠正链保留）。 |
| NS | `results/secon2027/analysis/formal-v1/analysis.json`、`runs.csv`、`summary.csv`、`paired_effects.csv` / `paired_seed_effects.csv`；`secon2027_supervisor_formal_statistics_review.md/.json` 与 `secon2027_final_statistics_review.md/.json`。全部 760 runs、38×20 seeds、1,330 summary /90 contrast /1,800 paired rows 一致；74 undefined 保留。原分析 Python 3.9.6 / NumPy 1.26.4 / Matplotlib 3.7.5；监督统计复核的 NumPy 2.5.3 单独记载。 |
| NE | `docs/results/secon2027_formal_mechanisms.md`（原 hash `2aa78f87bd03ec297931663c8b3328a468519643598009c9cdf5081faf777441`）、`gates/formal-v1/prospective-criteria-and-comparisons.json`、`decision-rejection-reasons.json`、`mechanism-resource-costs.json`；`secon2027_supervisor_formal_exposure_review.md/.json/.py` 及 `secon2027_supervisor_formal_s1_s3_exposure.json/.py`。六 scene gates 与六 control isolation/exposure gates 均有证据；gate pass 不表示性能受益。 |
| NA | `artifacts/secon2027/formal-v1-raw-evidence.parts.index.json`、11 parts、whole `.index.json`；`secon2027_supervisor_formal_archive_review.md/.json`。whole SHA `81776e12501e56945dd8aad6a37bb68e5f6e4b41d66c88ae041e7689e490d067`、475,828,160 B、14,667 members；从分块新建恢复目录，saved-source audit 760/760，审计前后文件不变。P0、失败 pilot v1、修复 pilot v2 和 pre-exposure archives 另保留。 |
| NP | `gates/formal-v1/closeout-tested-inputs.json`、`closeout-prepromotion-tests.json/.log`、`promoted-source-comparison.json`、`promoted-2.1.30-regression.json/.log`。pre 161 tests，post 34 fixtures；formal tested 2.1.29→promotion 2.1.30；166 formal inputs 仅 VERSION 改变，6 项 post-simulation utilities 单独列明。 |
| NI | `results/secon2027/gates/formal-v1/icc-preservation-check.json`：182 项 imported ICC/paper paths，两处均 unchanged，issues=[]。检查范围与源码导入清单绑定，不扩张为对所有 canonical 工作的声明。 |
| ND | `docs/results/secon2027_evaluation.md`：38 组 arm mean/CI、30 组 paired cells ×3 metrics、全 controls/robustness/secondary/成本/暴露/不利结果；`docs/research/secon2027_claim_evidence.md` 正由稿件任务完成最后正文与图表追溯同步。 |
| NW | `paper/secon2027/main.tex`、`methods.tex`、`evaluation.tex`、`controller_timing.tex`、`build_figures.py`、`FIGURES.md`；`figures/formal-v1/figure_manifest.json` 与 `formal-v2/figure_manifest.json` 都记录 complete 且绑定 formal plan/source。首轮正式 PDF v1 的 10 页由根/稿件任务报告；最终压缩稿及 PDF 验收尚未关闭，figure manifest 的 complete 仅表示数值图产物生成。 |
| NG | `docs/research/secon2027_checkpoint.md`、`docs/reproducibility/secon2027_reproduce.md`、`docs/project-management/secon2027_release_map.md`、`docs/research/secon2027_submission_checklist.md`。存在逐阶段导航；最终 PDF/analysis-paper 包/closeout commit/remote SHA 的完成事实仍待根执行落盘同步。 |
| NH | `docs/results/secon2027_firmware_validation.md`、`secon2027_baseline_fidelity.md`、`secon2027_official_requirements.md`。固件 0.1.4；未开展新板级/RF/功耗；模型保真度/PHY/访问约束和无硬件优势主张已明示。官方最终政策/匿名候选复核待同一最新 PDF 绑定。 |

下表仍可引用历史证据索引 P/T/V/X/R/C/B/A/Q/F/G/W/O/H；这些字母始终
对应前述历史记录中的原批次，不把旧测试数或 pilot n=3 移用于正式 n=20。
目录简写 `gates/...` 指 `results/secon2027/gates/...`；裸 `secon2027_*.md/.json`
研究报告指 `docs/research/` 内同名实体。当前没有修改 frozen method decision
或 contract 来修饰进度。

| ID | 本次当前状态 | 对应证据与具体边界／剩余项 |
| --- | --- | --- |

| A01 | 已验 | P：488 项真实工作状态导入、明确隔离 checkout 与来源映射；managed attachment 失败已披露，后续实验均使用明确隔离路径。 |
| A02 | 已验 | P/checkpoint 的任务书、根规划、交接、审查与固件文件读取记录保留；NF/NH/NG 将本轮适用边界与历史材料区分。 |
| A03 | 已验 | 限定提交已完成；全部新增对象均属于SECON任务，ICC182项原资产保持原hash；大归档分片与可恢复诊断包有明确映射。 |
| A04 | 已验 | 最终9页IEEE10pt匿名稿已实测；官方规则/IEEEAI披露复核完成。时区及未来EDAS注册细节仍不臆造，候选交付不等于提交。 |
| A05 | 已验 | checkpoint及release receipt已同步完整P0/pilot失败/冻结/行政勘误/760运行/PDF/小分片发布时序，所有早期条目标为历史。 |
| A06 | 已验 | 开发→一次冻结→完整正式证据→统计→真实PDF→精确远端发布全部闭环；post-starterratum及失败记录如实保留。 |
| A07 | 已验 | 独立SECON稿、ICC182项保全、匿名9页PDF及可恢复交付完成；无EDAS/付款/邮件动作。 |
| B01 | 已验 | NF/NQ 冻结 166 项实际源码、tested 2.1.29 及合同配置；NA 从 11 块恢复全部原始材料并使用包内保存源码完成 760 审计，不能仅以 Git HEAD 代替快照。 |
| B02 | 已验 | P 历史 581 结果/614 实际 seed/零解析错误和 0..999999 保守排除保留；92200/92300 等历史计划按已暴露处理，未重新命名为正式 fresh seeds。 |
| B03 | 已验 | NF registry 明确 development2027000–2027002 与 formal2027100–2027119；正式 cohort 在 first start 前登记并冻结，之后全部暴露，760 计划键完成状态有日志/manifest 支持。 |
| B04 | 已验 | T/NQ run-key/cohort 分离与首次 arm 暴露测试；NF760 唯一 case/arm/seed 键全部完成，预定配对保留，未增补未注册比较。 |
| B05 | 已验 | T/NQ 显式 cohort/seed 负向测试保留；外部 runner 不再凭历史默认启动，正式执行入口绑定唯一 saved plan。 |
| B06 | 已验 | T/NQ 未 gated validation、合同/源/配置/cohort 状态变更负向守卫通过；NF 正式 gate 及计划先于首次执行，行政勘误未更改科学守卫。 |
| B07 | 已验 | T 独占 key/不可覆盖/失败 attempt 测试；F 原 pilot 失败保留，NQ 正式 760 各原 attempt-001；43 完成 key 续跑 verified-existing，未覆盖或重跑。 |
| B08 | 已验 | NQ/NA760×18 必要 attempt 文件、166 snapshot 输入及 manifest 绑定核验；部分出口/缺文件/空 inventory 负向测试保留，完整 formal 审计为 complete。 |
| B09 | 已验 | T registry 隔离、unknown-arm 与异常负向测试；NF/NQ 每次实际 arm/variant 身份与计划/manifest 吻合，无临时全局 registry 篡改。 |
| B10 | 已验 | T schema/非法配置/CLI 测试，加 NF/NQ 真实 S1/S2/S3、三 controls 与 10/60s 全部 760 运行，稳健性不是只改 scenario 标签。 |
| B11 | 已验 | NF 新 SECON 合同驱动正式审计；NA 保存源码审计可在新 root 运行，P0/pilot 恢复与旧合同保留，各批次仍用自身冻结源，不追认旧结果。 |
| B12 | 已验 | 原始11片干净恢复14667成员及760保存审计通过；114新小片wholeSHA与原归档相同，已发布于30e7bd42…；中断恢复和科学失败不重分类的真实fixture覆盖保留。 |
| C01 | 已验 | C/NQ 源 FLOOD 回流、cold/recovery、seen 过期、malformed/loop 副作用前拒绝确定性回归；formal 代码绑定同一已测 snapshot。 |
| C02 | 已验 | C/NQ 合法并发 ACK 与共享缓存更新分离、同路径 revision、不同路径更新、旧 timeout 不破坏新确认的正负回归保留。 |
| C03 | 已验 | C/NQ flow/endpoints/path/sender/marker/生命周期/未启动 stage/迟到与 replay 拒绝测试；修复并发 ACK 未放开其他有效性条件。 |
| C04 | 已验 | NQ/NS 逐流重算 scheduled 分母，含 S3 六个 source-state refusals 与全部 no-start/unfinished；760run primary 计数和比例匹配，不按成功删流。 |
| C05 | 已验 | C/NQ/NS request→commit→physical TX→RX→ACK 一致；574,959 actual TX 的全 airtime 重算，future reservation 与未启动 request 不收费，started full frame 依 cutoff 计费。 |
| C06 | 已验 | C/NQ commitment 前后/同刻取消 fixtures；NE 成功 ACK 取消与 decoded checks/容量事件分开；NS 物理账本不反减已承诺或已发成本。 |
| C07 | 已验 | C/NQ 源 initial/repeat/recovery 上界、timer ties 和单次生命周期结束；真实 stale-route recovery 拒绝 NameError 已在新开发快照修复并验证，不把 action 枚举当 deadline 因果。 |
| C08 | 已验 | C/NQ 容量满额/eviction/重复与同刻 timer fixtures 已覆盖；NE 真实 formal 零 relay eviction 只是观测，不替代 fixture，也不证明 peak occupancy 小于 8。 |
| C09 | 已验 | Q 确定性重放、pilot/formal 各自 161 frozen tests；NPcloseout161 及 promotion34 fixtures 均有 command/cwd/exit0；未以新研究 seed 补升版验证。 |
| C10 | 已验 | F 旧 pilot-v1 48/1/23 与原源码/attempt 归档保留；formal 严格 tested 2.1.29，promotion 2.1.30 不改 manifest 或旧事件，不手工扣 TX/删坏流。 |
| D01 | 模型证据已验／边界明确 | B/NH 四模型默认和机制差异、上游 pins 与 wire/timer/cache 信息已记录；NW 继续称行为模型，正式数据不建立官方固件等价或优越性。 |
| D02 | 已验 | NF/NS/ND 三场景 default 四模型 240runs 完整，实际 parameters 和完整 20seed 均值/paired CIs 有记录；模型独立默认差异明确。 |
| D03 | 已验 | NF/B 匹配规则先冻结，NS/ND 三场景 matched 四模型 240runs 及实际参数完整；相同有效 CPR/ME 配置单列 n20，不合并成 n40。 |
| D04 | 已验 | NQ/NS 逐 pair 核 scheduled/topology/radio/pair-pool/environment hashes，协议随机数流边界经测试；相同外生输入不表示不同 TX 时刻看到完全相同干扰。 |
| D05 | 已验 | B/C/NQ 源节点仅用本地可见状态，无全局交付或未来故障 oracle；NS 完整 physical frame airtime 含 ACK/发现/重复，wire/PHY 模型限制已披露。 |
| D06 | 条件未触发 | NF 正式主模型和 controls 未采用新 common-ACK/强化保真度补充 variant；既有可选 variant 未冒充四个主模型，未新增必须完成的可选比较。 |
| D07 | 已验 | NF/NE 仅 ACK-off 控制保留 capacity policy；S2/S3 各 20seed，CPR 取消 204/685、disabled-control 取消 0、relay eviction0；NS 完整效果含 S3 负 ACK 点估计，未把次数乘 ToA 当净节省。 |
| D08 | 已验 | NF/C no-repeat 保留 nominal 观察 slot 且未虚构 repeat；NE 两场景 reference 均暴露、disabled repeat0，NS/ND 全部 40control runs 与 ACK/DATA/airtime CI 保留。 |
| D09 | 已验 | NF/C no-recovery 保留 repeat 并禁止 recovery 请求/启动；NE 禁用事件 0，NS/ND 两场景完整控制，S3 ACK −15.99pp 及 1.665airtime ratio 等不利结果保留。 |
| D10 | 条件未触发 | NE 正式全部 relay eviction/capacity cancel 为 0，未声称内存优势；S3 六个 source-state refusal 不等于 relay-ledger 容量暴露。未知 peak occupancy 明确，不据零 eviction 断言容量未满或最优。 |
| D11 | 已验 | NF 三项 clean toggles 与统计在首次 formal 前冻结；NS 全部六 control cells 仅 name 与预定开关不同，均 20 pairs；复用同一 S2/S3 主 CPR 而非重复独立样本。 |
| E01 | 已验 | V/X/R 完整 72-run pilot 含 repeat/recovery/cancel、真实资源成本；独立 pilot 机制报告与 NA 前序恢复证据保留，没有用机械 P0 替代机制 pilot。 |
| E02 | 已验 | F/C 真实实现缺陷诊断修复与 pilot-v2 闭环；NF method decision 保留 S3 不利开发观测，选择固定 CPR 权衡评价；方法 7 文件与完成 pilot 一致，未依 formal 结果选择候选。 |
| E03 | 条件未触发 | NF 未新增算法候选或新一轮策略搜索；缺失 import 最小修复不冒充新研究方向，正式结果后也未提出并验证救援候选。 |
| E04 | 已验（含勘误披露） | NF 一次性冻结 source/matrix/statistics/failure/claim gates，gate09:01:06→freeze09:01:52→first start09:06:36；09:09:21 行政 erratum 晚于暴露，原合同/方法不改。 |
| E05 | 已验 | NF 基于完整 pilot 估算 480+120+160、n20 精度/成本、4workers/2×余量/18GiB 与 4h；NE 实测 worker sum4423.192s、peak398,163,968B 与 raw7,098,305,927B，不把 sum 当并发 elapsed。 |
| E06 | 已验 | NS/ND 完整 S1 default/matched；NE 每 regime480 routed initial、526 多跳 ACK。对 ME ACK 差 CI 跨 0 且 airtime 更高，无谓开销保留，未要求 CPR 必须获益。 |
| E07 | 已验 | NE/S2 每 regime85active-initial-path crossings 全部有 pre80 同 path/generation ACK；159TX 跨 87all-kind flows，85subset24DATA/18ACK/61 无 DATA；DATA-only86 与跨界 4/3 明确，结构 6-hop 可达不等于 RF 成功。 |
| E08 | 已验 | NE 每 seed S3 offered count>S1，collision/halfduplex 及 queue/no-start/rejections 明确；六 source refusals 保留，zero relay eviction 不写成 queue 饱和或主因；NS/ND 负 ACK/高 cost 结果完整。 |
| E09 | 已验 | NE 实测 accepted ACK：S1 每 regime440 四跳/86 六跳，S3 为 703 四跳/478 六跳；S2 物理 forward/reverse 链核验，未以 H=6 替代实际多跳观测。 |
| E10 | 已验 | NF/NS 新增 10/60s 各 80runs 完成；30s 复用 main S2-matched，deadline 显示 240rows 但仅新增 160runs；10s recovery0 和对 MT DATA 负差保留。 |
| E11 | 已验（有限轴边界） | NF/ND deadline 与 drain/cutoff250/270/300s 同时改变，其他 frozen 输入固定；只连接 fault-free8/40 两个负载点，未推断连续曲线、saturation threshold 或新增跨 deadline 推断检验。 |
| E12 | 已验（模型边界） | 最终v3表II明确915MHz、SF7/BW125kHz等参数；局限明确无duty-cycle/LBT enforcement及无RF校准、器件能耗验证。与冻结模型一致。 |
| E13 | 已验 | NQ/NS760/760 全部保留，formal0fail 不抹去 F 真实历史 failure；负、零、undefined 和无暴露结果不筛除，无新 seed/调参/矩阵或统计规则变更。 |
| F01 | 已验 | NQ/NS 按 timestamps 重算 N、timely ACK 及 destination DATA；23,836ACK/32,925DATA 是全库存总数，不作为跨 case pooled performance 或独立样本量。 |
| F02 | 已验 | NS 全 physicalTX airtime 和 packet-kind×stage 加和核验；ND 三 stage 与 ACK 成本重构完整均值，取消请求未计 TX、无虚构分项 CI。 |
| F03 | 已验 | NS/ND 全部 38case/arm airtime-per-delivery 与 success-p95 附 unfinished fractions；74undefined summary 保留 n20 空值，无零分母删 seed，success-only 曲线不充当全体 delay guarantee。 |
| F04 | 已验 | NE/NS physicalrepeat/recovery、ACK checks/success、source 拒绝/relay 容量分开；stale-route-generation 与真正 budget 拒绝不同，未按 DROP 枚举或 missingACK 猜故障原因。 |
| F05 | 已验 | NS38 groups 各 20seed，600distinct pairs/90metric rows/1,800seed rows；10,000 paired bootstrap 与 geometric airtime ratios 独立重算匹配，packet/RX 机会不当独立样本。 |
| F06 | 边界已验 | NF/NS 预先规定 unadjusted descriptive95%intervals，无 multiplicity-controlled significance/noninferiority；跨 0/1 区间和负结果保留，不补设事后界值。 |
| F07 | 已验 | 四张formal-v2论文图的145来源行和16输出hash一致，全部图PDF字体嵌入；最终9页PDF已逐页视觉通过。图manifest及final_figures_review、final_pdf_review绑定。 |
| F08 | 已验 | 最终claim_evidence及final_paper_claims_review串联正文→图/CSV→run→manifest→冻结source；v3仅补915MHz/duty-cycle/LBT边界，数字及145来源行不变。 |
| G01 | 已验 | 最终checkpoint同步真实完成状态与source/plan/PDF/archive/release identities，早期记录完整保留。 |
| G02 | 已验（原文冻结） | NF 合同实体/一次正式冻结节及 hash 已绑定 plan/source/gate；post-start erratum 独立存在。原 developmentopening 作为历史不一致公开解释，不改合同 bytes 来消除矛盾。 |
| G03 | 已验 | NF registry 记录完整 formal 20 seeds、760 planned keys、首次暴露及完成状态；development/pilot 和 formal 用途分开，已暴露 seed 不重新标 fresh。 |
| G04 | 已验 | NF repo 内 experiment_matrix.json 与 plan 嵌入 matrix 一致，canonical SHA3cc6bab3de7c7767c3fbf845deb156f945db13d98361f0dc5b7bf7e769cc6ea3；等价导航在 NG 复现指南。 |
| G05 | 已验 | B/NH baseline_fidelity 实体及上游 pins/各模型机制/parameter 映射存在；model 限制未被 formal 结果覆盖或升格为官方固件验证。 |
| G06 | 已验 | C/NFalgorithm_spec 与 formal 源绑定，保留可取消 commit 边界、same-path revision、nominal slot 及 stale-route 拒绝语义；全系统内存/最优性不在证明范围。 |
| G07 | 已验 | ND `docs/results/secon2027_evaluation.md` 已完成；38means、30pairedcells 真实 CI、所有 controls/robustness/secondary/机制口径和不利结果均已表化并 CSV 回验。 |
| G08 | 已验 | claim_evidence已定稿并绑定manuscript_manifest和完整formal表，不再是待填支架；正式与历史/实现主张分开。 |
| G09 | 已验 | 最终复现指南列保存源审计/完整分析/图命令及所有依赖、资源、hash；raw干净恢复760通过，最终analysis/paper包1230文件恢复且四图来源CSV/PNG字节一致。 |
| G10 | 已验 | submission_checklist全部当前交付项均有实测记录；未来实际提交事项单列，未冒充EDAS已提交。 |
| G11 | 披露已验；实测未做 | NH 固件 validation 记录明确 0.1.4、无新增板级/RF/功耗；旧 native/build 不当新 RF 证据。必需披露已具备，条件 P2 未开展。 |
| G12 | 已验 | tested2.1.29→promoted2.1.30、161/34测试、165/166源比较、两个归档及精确远端artifact commite653315803c46abf80fb6d3476eee3b5f7fd34a4均记录。 |
| G13 | 已验 | 独立SECON完整稿件9页，27项真实文献、实际正式结果和负结果完整；manuscript_manifest绑定源文件、Tectonic0.17.0和PDF。 |
| G14 | 已验 | 同一v3PDF的text/metadata/annotations及6条公开产品文献链接均通过无身份扫描；无作者、单位、邮箱、私人仓库/机器路径或虚构资助。 |
| G15 | 已验 | 最终v3实测9Letter页、IEEE10pt、26字体全嵌入无Type3、27引用解析；全部页面视觉通过。v1十页失败保留，不冒充最终稿。 |
| G16 | 已验 | 匿名PDF独立导出；内部可恢复包可含机器路径与身份，并未冒充匿名review附件。PDF无身份链接，未自动公开匿名仓库或投稿。 |
| H01 | 已验 | NPcloseout-tested-inputs 列 tested 2.1.29 的 166 源与新增 post-simulation utilities；正式方法 snapshot 保持原值，根/稿件新增工具和文档范围另列。 |
| H02 | 已验（至 promotion 验证） | NF/NQ 正式冻结 161tests→760 仿真/audit/NS 分析在前；NP 再 161 pre-tests 通过后提升 2.1.30，post 34 fixtures 通过。此顺序不证明最终发布已经完成。 |
| H03 | 已验 | NP 明确 tested 2.1.29/promotion 2.1.30；165/166formal inputs 不变且仅 VERSION 变化，contract/hash/历史 manifest 不回写；整个 repo 新增工具不冒称 VERSION-only。 |
| H04 | 已验 | NPpromoted-2.1.30-regression 为 34 passed/exit0，controller/frozen-worker/analyzer 开发 fixtures；未重跑 formal 研究 seed 为升版改标签。 |
| H05 | 已验 | 限定artifact commite653315803c46abf80fb6d3476eee3b5f7fd34a4保留源码/工具/最终论文/诊断及三片analysis包；恢复1230文件和四图重画通过。 |
| H06 | 已验 | 官方认证GitHubref匹配artifact commite653315803c46abf80fb6d3476eee3b5f7fd34a4；raw30e7bd42另有精确SHA证据。发布非force，所有新blob/tree/commit身份核对。 |
| H07 | 已验 | 所有网络失败及成功transport日志保留；原local1e和11大片未丢弃，新114小片wholeSHA一致；无tag、merge或历史发布覆盖。 |
| H08 | 边界已验 | NH 固件仍 0.1.4；NP/ND 本轮是复现研究发布、保留 S3 负结果且不宣称普遍性能提升，tested/promotion 不混同；最终发布文案仍须遵守。 |
| I01 | 条件未触发（P2） | 本轮没有固件改动或新 native/板级 gate 承诺，NH 记录现有固件状态；未开展不等于通过实物验证，也不阻断已授权仿真主线。 |
| I02 | 条件未触发（P2） | 未开展 RF/功耗测量、无新设备数据；NH 明确披露，设备缺失未被用作省略必需仿真/控制/稳健性的理由。 |
| I03 | 边界已验 | B/NH/ND/NW 均限制为行为模型与模拟环境，无官方产品公平硬件比较、实物认证、电池寿命或 device-energy 优势结论。 |
| J01 | 已验／持续更新 | NF 预算来自完整 pilot 且含控制/稳健性/失败余量；NE 已给 actual worker/RSS/storage，不把内部日期或预算估算冒充完成。稿件/发布剩余工作按实际推进。 |
| J02 | 已验 | 测试源码/版本及raw恢复身份完备，最终2.1.30artifact commite653315803c46abf80fb6d3476eee3b5f7fd34a4已在远端核验。 |
| J03 | 已验 | NF/NQ/NS/ND 完整四主模型 default/matched、3 clean controls×2 场景、10/60s 有限 robustness 已完成；原合同/methoddecision 保持冻结，负结果全部保留。 |
| J04 | 已验 | 原始证据、独立审计、完整统计、最终claim链与9页PDF全部绑定；最终analysis/paper包d60a67eb…含1230文件，干净恢复及四图重画通过，失败历史保留。 |
| J05 | 已验 | 第11节必要文档全部存在并按最终source/PDF/归档/远端身份同步；独立review与当前执行结论分开保留。 |
| J06 | 已验 | v3匿名IEEE10pt九页PDF已由执行侧与监督方对同一SHA独立渲染检查；适用AI披露保留且不含身份。 |
| J07 | 已验 | 最终交付说明和文件索引包含完成范围、S2获益/S3失败边界、未开展RF、匿名PDF、两个可恢复包、tested/promoted映射和远端核验；无投稿成功声明。 |

### 最终关闭与未触发条件

必需科学证据、最终PDF、claim链、归档恢复/重画和artifact commit `e653315803c46abf80fb6d3476eee3b5f7fd34a4` 的远端验证均已完成。后续文档receipt提交不改变任何科学或PDF产物。D06/D10/E03/I01/I02五项条件未触发，仍明确保留，不算新增算法/容量优越性/硬件验证。没有研究seed重跑、结果筛选、旧manifest覆盖或自动EDAS动作。
