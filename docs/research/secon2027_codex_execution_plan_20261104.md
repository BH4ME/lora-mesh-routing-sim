# MeshEcho-CPR 面向 SECON 2027 的升级执行任务书

编制日期：2026-11-04（北京时间）。适用仓库：`lora_mesh_current_version_v2`。

**文档用途：交给另一个 Codex 按阶段执行代码、实验、文档和论文升级。本文是执行计划，不能作为这些升级已经完成的证明。** 本次编制仅核对现有资料及官方要求，未运行新仿真、修复固件、修改论文、升版或推送 GitHub。

建议主线：保留 MeshEcho-CPR 已有状态机，先修复证据链和基线可比性，再用消融和多场景实验决定是否需要新增算法。优先完成一篇边界清楚、结果可复现的协议论文；不能承诺中稿率，也不能把新增公式数量当作创新。

## 1. 可直接复制给 Codex 的启动提示词

```text
请执行这份任务书：
/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_codex_execution_plan_20261104.md

目标是在 SECON 2027 截止前，把现有 MeshEcho-CPR 升级为具有公平四协议
比较、可解释消融、多场景证据和可复现产物的投稿候选版本。

先读取本任务书、task_plan.md、findings.md、progress.md，以及本任务书
列出的当前合同和固件交接。核对实际源码、版本、Git 状态；不要把旧目录、
旧 PDF、历史已暴露 seeds 或无效结果当作最新证据。

按 P0 → P1 → 论文收敛执行。先建立证据设施和种子登记，再跑 pilot，
冻结实验矩阵后才开展正式比较。日常可逆工作自主推进，不要每改一处
就再次问我是否继续。硬件、付费资源或确实缺少的信息才需要向我确认。

保留当前 ICC 稿，SECON 稿放在独立目录。现有基线必须明确称为
Meshtastic-like / MeshCore-like，除非完成了对应官方固件的实测或等价性验证。

每完成一轮代码修改及对应测试、仿真验证，仓库版本递增一次并上传 GitHub；
遵守任务书中的冻结源码、结果版本映射和限定文件提交流程。不要修改历史
manifest，不要覆盖历史结果，不要提交无关改动，不要用反复试新种子挑好结果。

每个里程碑及上下文接近压缩时，把进度、命令、产物、失败原因和下一步写入
docs/research/secon2027_checkpoint.md；恢复后先读它再继续。

最终交付代码、完整实验与审计包、结果图表、必需文档、9 页以内的匿名 SECON
PDF 和投稿检查表。先完成可审阅材料；本任务书不要求自动操作 EDAS、缴费
或发送邮件。不得编造硬件实验、数据、参考文献、录用概率或投稿成功状态。
```

## 2. SECON 官方边界及项目时间目标

以下为 2026-11-04 核查结果；未来实际执行及投稿前各复核一次，记录变更。

| 项目 | 已核查要求 |
| --- | --- |
| 会议 | IEEE SECON 2027，2027-05-05～07，葡萄牙里斯本 |
| 全文截止 | **2026-11-30**；官网未注明截止时区，不能自行写成 AoE |
| 摘要／注册截止 | 所查页面未单列日期；不得据此假定与全文截止一定相同 |
| 通知／终稿 | 2027-02-15／2027-03-15 |
| 页数 | **最多 9 页，包括图、参考文献和附录** |
| 格式与审稿 | 标准 IEEE conference、10pt、双盲 |
| 投稿 | PDF，通过官方 EDAS 入口；PDF 标题与 EDAS 标题完全一致 |
| 作者元数据 | EDAS 列出全体作者；官网规定 registration deadline 后不得更改作者名单 |

官方来源：

- [Call for Papers](https://secon2027.ieee-secon.org/call-papers)
- [Authors](https://secon2027.ieee-secon.org/authors)
- [Submission Guidelines](https://secon2027.ieee-secon.org/submission-guidelines)
- [会议主页](https://secon2027.ieee-secon.org/)
- [官方 EDAS 入口](https://edas.info/N35491)

所查页面未发现统一强制实物实验、artifact 提交或补充材料要求，也未发现 SECON 专属 AI 披露细则。这不等于实践验证不重要，也不等于无需遵守适用的 IEEE 总政策。投稿检查阶段查明当时规则，不自行假设。

**内部目标：11 月 28 日前完成可上传 PDF 和检查表。** 截止时区及注册节点未明，不能安排到 11 月 30 日最后一刻。附录也计入 9 页，不能用附录规避篇幅限制。

## 3. 当前仓库与证据盘点

### 3.1 正确工作目录

- Canonical 根目录：`/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2`
- GitHub：`https://github.com/BH4ME/lora-mesh-routing-sim.git`
- 本次核查：根 `VERSION` 为 `2.1.27`，`firmware/meshecho_cpr/VERSION` 为 `0.1.4`。
- `/Users/bh4me_macair/Documents/Codex/lora_mesh` 是另一个目录，不能混用其代码或结果。
- 工作树有大量既有修改和未跟踪文件。先保存状态清单；禁止 `git reset --hard`、`git clean` 或直接 `git add .`。版本以实际文件和发布记录为准，不能由旧 `build-*` 文件夹名推断。

| 已存在文件 | 作用／注意事项 |
| --- | --- |
| `meshecho_cpr.py` | 恢复决策、流生命周期、有界 ACK 中继账本 |
| `lora_mesh_sim.py` | 真实模拟器及协议集成入口；不是 `simulator.py` |
| `meshecho_drc.py`、`meshecho_utility.py` | 关联依赖，检查修改影响 |
| `tools/run_cpr_experiment.py` | 内部实验、完整事件产物及审计入口 |
| `tools/run_cpr_external_comparison.py` | CPR／旧 MeshEcho／MT-like／MC-like 比较 |
| `tools/audit_cpr_population.py` | 历史固定 cohort 审计，不能直接代表新 SECON 合同 |
| `paper/icc2027/icc2027_lora_mesh.tex` | 当前 ICC 源文件，保留；磁盘旧 PDF 不一定等于最新编辑器预览 |
| `docs/research/meshecho_cpr_population_contract_20261006.md` | 历史内部实验合同，保留历史含义 |
| `docs/research/meshecho_cpr_protocol_comparison_contract_20261006.md` | 历史外部比较约定 |
| `docs/research/meshecho_firmware_upgrade_handoff_20261013.md` | 固件未完工作及验证状态 |
| `docs/results/meshecho_four_protocol_comparison_20261012.md` | 已有完整四协议结果解释 |

### 3.2 已有算法及性能证据

当前 CPR 的主流程：确认路径初发 → 最多一次同路径重试 → 最多一次满足截止期条件的恢复洪泛；匹配 ACK 可取消尚未承诺发送的中继。必须对照代码说明“请求、承诺、物理开始发送”三个事件，不能把排队请求算成已发包。

现有完整四协议数据前缀：

```text
results/meshecho_four_protocol_comparison_92300_92319_20261012_rerun
```

对应 `.runs.csv`、`.paired.csv`、`.summary.csv`。该包包含 80 runs、60 paired comparisons，历史均值如下，仅作为已有锚点：

| 模型 | Deadline ACK PDR | Destination PDR | 全网 TX airtime |
| --- | ---: | ---: | ---: |
| MeshEcho-CPR | 0.9829 | 0.9984 | 6.290 s |
| Legacy MeshEcho | 0.9477 | 0.9616 | 10.231 s |
| Meshtastic-like | 0.9405 | 0.9886 | 29.257 s |
| MeshCore-like | 0.9328 | 0.9451 | 9.896 s |

证据边界：20 节点、3000 m 方形、240 s 流量＋30 s drain、8 flows/min、4 对端点、SF7、125 kHz、32 B、17 dBm、6 dB block fading 每 60 s 更新、最多 6 hops、30 s deadline。是**一个场景、20 个已暴露种子、行为级模型比较**，不能推导出普遍优于真实产品。

10 月 6 日 external-comparison 包只有三个协议，不能单独证明四协议结果。以下无效目录不得参与论文汇总：

```text
results/invalid_cpr_multihop_ack_20261006/
results/invalid_cpr_path_audit_20261006/
```

## 4. 执行顺序与验收关口

| 阶段 | 必须完成的工作 | 进入下一阶段的条件 |
| --- | --- | --- |
| P0-A | 资产清单、冻结源码、统一 seed 登记 | 能说明每个结果对应哪份代码、场景和种子状态 |
| P0-B | runner 完整证据、防覆盖、正确性审计 | smoke／开发批次证据完整；无结果口径错误 |
| P1-A | 四协议机制映射、公平配置、消融定义 | 比较对象与参数真实；不混淆两个机制的效果 |
| P1-B | development pilot、失败诊断、候选算法选择，随后冻结方法和矩阵 | 选定机制有本地可实现规格；样本量、参数及统计方案在正式验证前确定 |
| P1-C | 冻结后的正式比较、消融与统计 | 全部预定场景完整报告，含失败和负结果；不再据此调参选算法 |
| P1-D | 图表、复现文档、独立匿名 SECON 稿 | 结论可逐项追溯，PDF 与官方规则一致 |
| P2 | 硬件验证或更大规模扩展 | 资源允许且不挤占必需关口；未完成则如实披露 |

**验收分开看：**正确性与可复现性必须通过；性能不显著或部分场景输给基线，是有效研究结果，不允许删掉这些场景或伪造“全通过”。若缺乏足够研究贡献，交付真实结果和延期建议，不能靠措辞包装成可录用结论。

## 5. P0：先补实验基础设施与正确性

### 5.1 源码、种子和结果不可混用

1. 记录 Git HEAD、工作树差异、未跟踪依赖、环境版本、合同 hash 与实际源码 hash。工作树不干净时，仅记录 HEAD 不足以复现；冻结快照必须包含本次执行使用的修改和未跟踪源码。
2. 扫描历史合同、authorization JSON、结果及 handoff，创建统一种子登记簿。`92200–92219`、`92300–92319` 已暴露；历史另有关闭或预留区间及部分暴露记录，不能随手选择旧范围。本文不预分配未经核查的新 seed 数值。
3. 种子登记至少包含 cohort ID、seed 列表、用途、场景、源码／配置版本、reserved/running/exposed/retired 状态、首次运行时间、产物和批准它的实验合同。development 和最终验证 cohort 分开。
4. 验证集在方法、参数、场景和统计方案冻结后执行。看过验证结果再调算法，旧验证集即转为已暴露证据；若需要新确认，应重新登记并说明原因。不能连续换验证集直到结果满意。
5. 原始产物不可覆盖。失败批次保留运行清单、日志和失败原因；重跑产生新 run ID，不能静默补写或只留下成功样本。

登记粒度要支持配对实验：cohort 暴露状态与具体运行状态分开。按 `cohort + frozen-config + arm + seed` 建立计划 run key、锁和完成记录；同一已注册 cohort 必须允许所有预定场景／协议／消融依次跑完。第一个 arm 使 seed 变为 exposed，不应阻止其余已冻结 arms；它禁止的是把这些数据重新称为未见数据，或据此添加未经预注册的新比较。失败重试另有 attempt ID，并遵守预定失败处理规则。

### 5.2 Runner 必修项

- 外部 runner 当前不传 seed 时默认使用 `92300–92319`；改为要求显式 cohort／seed，不提供会误用历史数据的默认值。
- 当前 `--split holdout` 只是标签。补真实守卫：检查 cohort 及计划 run key 状态、合同、冻结源码及 development gate，再允许启动；并发启动时避免同一 run key 重复执行，并允许完成同 cohort 内其余预定 runs。
- 外部 runner 当前仅导出三个 CSV。复用或重构内部完整证据出口，保留 flow/action/request/transmission/RX/ACK JSONL、manifest、场景、种子、参数、依赖版本与数据 hash。
- 外部 CSV 增加防覆盖保护；manifest 在产物写入完整后才标记 completed。部分失败不能被汇总成完整批次。
- 外部 runner 目前临时修改全局 `CPR_PROTOCOLS`；改为显式协议 registry，避免并行、重复调用和异常退出改变其他实验行为。
- 增加可配置场景／矩阵能力。当前 `smoke`、`exposure` 固定 profile 不足以直接执行第 7 节矩阵。新 CLI 必须有 `--help`、配置 schema 和冻结后的真实命令；不要在报告里写尚未实现的命令为“已执行”。
- 新建 SECON 合同驱动审计，不修改旧合同来追认新种子；保留旧审计可在历史快照运行的能力。

### 5.3 最低正确性检查

在扩展性能实验前，用针对性测试验证：

- scheduled flows 全部进入分母；deadline、drain、drop 与未完成流的归属一致。
- 每次真实 TX 唯一；flow/request/TX/RX/ACK 的关联完整；未发送请求与真正取消成功分开。
- ACK 的 flow 身份、epoch／marker／generation 匹配；过期或不同流 ACK 不得结束当前流。
- 只取消尚可取消的 pending relay；不能从 airtime 账本中扣掉已经开始的发送。
- 重试／恢复次数上界、deadline 可行性和单次生命周期结束一致；不发生重复完成。
- 高负载下有界 ledger 溢出、淘汰和重复洪泛处理确定；包括计时相撞与晚 ACK。
- 相同配置及外生 trace 可复现；断点恢复不会重复计数或遗漏失败运行。

已有相关测试入口（本任务书未执行；启动后确认 Python 环境／依赖）：

```bash
cd /Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2
python3 -m pytest tests/test_meshecho_cpr.py tests/test_meshecho_cpr_controller.py tests/test_cpr_experiment.py tests/test_cpr_external_comparison.py tests/test_common_ack_baselines.py
```

后续按改动影响增加有价值的机制／证据测试，不写只复制实现逻辑的测试，也不为纯文档改动跑完整仿真。

## 6. P1：公平四协议比较与机制消融

### 6.1 基线要回答“到底比较了什么”

四个主模型：MeshEcho-CPR、Legacy MeshEcho、Meshtastic-like、MeshCore-like。

创建 baseline fidelity 表：上游官方版本／commit、来源链接、路由／洪泛机制、ACK 语义、重试、去重、缓存、超时、发现包、帧长、信息可见性及未建模行为。现有 MC-like 使用 RREQ/RREP 与缓存 source route，不能等同于官方完整 flood／delivery-report 路径学习。若修改为更忠实的模型，保留旧模型名称与历史数据，另给新 variant ID。

分两类实验并分别解释：

1. **所实现模型的默认配置比较**：保留并披露各模型自身默认参数，评价整体行为；不能称为真实产品原生固件测评。
2. **可比机制配置比较**：固定 PHY、业务、deadline、可见信息和计费口径；对于具有同等含义的 timer／cache／预算，在公平预定规则下匹配。无法匹配的差异明确保留，不能把不同协议强改成同一个协议。

目前 MT 的 base/jitter 为 0.75/0.75 s；MC 的 TTL 为 300 s、discovery base/jitter 为 0.5/0.7 s、首回复收集窗口为 0；ME／CPR 的 TTL 为 600 s、flood base/jitter 为 0.45/0.65 s。**同一个 CprCase 不代表所有协议参数相同**：runner 传入 calm 参数，并不自动覆盖 MT／MC 的独立默认值。

已有 `meshtastic-common-ack`、`meshcore-common-ack` 可用于相同 ACK 语义的补充分析；仍是 product-inspired 模型，必须说明它们与原模型差别，不能替换后仍沿用产品名称而不披露。

共同要求：冻结拓扑、业务到达和外生信道／故障 trace；仅“使用相同 seed”不足以保证不同协议消耗随机数后仍经历相同环境。应分离 topology、traffic、channel 和 protocol randomness，或预生成共同环境轨迹。所有方案都支付实际发送的 DATA／ACK／发现／重复包 airtime；协议只能使用运行时本地可获得的信息。

### 6.2 消融先拆清楚再跑

现成 `meshecho-cpr-nocancel` 同时关闭 ACK 取消和 ledger enrollment／容量淘汰取消：`lora_mesh_sim.py` 中 `evict_pending` 与 `cancel_on_ack` 耦合，`meshecho_cpr.py` 的容量淘汰可取消未 committed 的 pending。因此不能直接写成“仅去掉 ACK overhearing”的纯单因素实验。

| 消融目标 | 实施要求 |
| --- | --- |
| ACK 取消的贡献 | 先记录 capacity eviction 暴露；若非零，分离 ACK-only 与 capacity-only 开关，或明确称“整个有界中继取消组件”的消融 |
| 同路径 repeat 的贡献 | 在同一 source FSM、wire 格式与预算口径下关闭 repeat，明确后续 recovery 的时刻如何定义 |
| recovery 的贡献 | 在同一 CPR 机制上关闭 recovery，保留其他状态与计费；不能直接把不同的旧 DRC 当作单因素对照 |
| ledger 容量影响 | 仅在确有暴露或声称内存优势时做容量敏感性；报告淘汰率及可靠性代价 |

实现哪些额外控制，由代码审计后冻结。要在论文里说明禁用一个动作后释放的时间／预算如何处理；若无法保持独立，就称为策略比较，不声称纯因果分离。

## 7. P1：分阶段实验矩阵与成本控制

**以下数值是 pilot 起点和预算建议，不是已执行配置。** 在 development pilot 后一次性冻结正式矩阵、场景有效性标准、样本量和时间／存储预算。不要看完正式结果再改标准。

### 7.1 必做场景

| 场景 | 研究问题与建议起点 | 必须记录的机制暴露 |
| --- | --- | --- |
| S1 稳态／低争用 | 从现有 20 节点配置开始，低到中等业务，检验 CPR 是否有无谓开销 | cached／cold-start 比例、平均跳数、重复与取消次数 |
| S2 路径失效但存在替代路径 | 公共外生链路变化或预定故障轨迹；检查恢复是否有效；源节点不可读取故障 oracle | 真正开始的 repeat／recovery、替代路径可达性、ACK 丢失与 DATA 丢失 |
| S3 高负载争用 | 从相同拓扑提高到达率，覆盖碰撞与队列压力；失败也完整记录 | 实际 TX、碰撞／忙信道、排队／过期、ledger eviction、取消成功率 |

环境可达性分析只能用于预定的场景描述／分层，不能让它成为 CPR 独享信息，也不能事后删除不可达样本来提高 PDR。

| 批次 | 建议规模 | 执行原则 |
| --- | --- | --- |
| Pilot | 2–3 个新 development seeds，anchor＋stress，四模型 | 估计单 run 时间、峰值内存、JSONL 体积，确认机制真的触发 |
| 主比较 | 3 场景 × 4 模型 × 20 seeds＝240 runs | 20 只是起始预算；在 pilot 后按所需精度和成本冻结，不保证统计功效 |
| 机制消融 | 预定 2 场景 × 最多 3 个额外控制 × 20 seeds≈120 新 runs | 可复用完全相同快照／配置／seed 下的 CPR，避免为复用而篡改数据 |
| 最小稳健性补充 | 预定 1–2 个有限轴；优先规模／密度或 deadline | 按剩余预算开展，不能把未跑项目写成完成 |

默认配置与匹配配置若各跑一套，会增加 runs，必须单独列入预算，不能藏在“240 runs”内。若需单列 capacity 控制，也要增加预算。优先保证主比较及关键消融，禁止直接铺开无耗时估计的全笛卡尔积。

Pilot 后用实际测量估算：总串行时间≈各配置预计 runs × 对应平均运行时间，存储≈对应平均产物体积 × runs，并留出失败重跑和审计余量；并行度依据实测内存设定，不按 CPU 核数盲目启动。

### 7.2 可选敏感性及建模完整性

- **规模／密度**：例如 20／40／80 节点；明确固定面积还是固定密度、固定总流量还是每节点流量，避免同时变化后无法解释。
- **deadline**：例如 10／30／60 s；同步检查队列、drain 和动作预算，报告无法在期限内完成的流。
- **缓存与持续时间**：当前 240 s 短于 300／600 s TTL。声称研究缓存过期时，必须延长 horizon 或控制初始 cache age，并报告实际过期数。
- **信道／拓扑**：至少说明理想化假设和多跳分布；若声称一般稳健性，补另一类拓扑／信道条件。研究 mobility 时才引入并验证移动模型，不为凑变量随意增加。
- **PHY**：SF7／SF9 等改变会联动 ToA、接收灵敏度和可达性；固定并披露 BW／CR／功率／完整帧字节数。说明 capture、半双工、CAD、干扰等是否建模及其局限。
- **频段与访问约束**：说明目标地区／频段及 duty-cycle、LBT 等约束的适用性和实现范围；未实现不能宣称法规条件下实测可用。

## 8. 指标、统计和图表

### 8.1 统一指标定义

对每个 seed／场景，以全部预定业务流数 N 为共同分母，至少报告：

- 按 deadline 获得有效 ACK 的流数／N；目的节点成功收到的独立流数／N。明确第二项是否同样受 deadline 限制，同时保留历史口径，不能悄悄改名。
- 全网所有已物理开始发送帧的 airtime 之和 A。DATA／ACK／发现属于包类型，repeat／recovery 属于阶段；用“包类型 × 阶段”二维表分类，或分别展示两套可各自加总至 A 的分解，不能把两种维度混加、重复计费。
- 每个按时成功交付流的 airtime：A／按时独立交付数。分母为 0 时标记未定义并报告失败数，不能填 0 或删样本。
- 成功流的延迟分布／分位数，同时报告未完成比例，避免仅画成功者 CDF 造成误导。
- 实际启动的重试／恢复、取消请求／成功取消、容量淘汰、route hit／miss 和失效原因分布。

现有 TX energy 只是 airtime 乘固定发射功率，与 airtime 同比例；可作为 TX-only 估算，但不能包装成独立能耗实验证据，更不能称整机续航。

### 8.2 预先冻结统计方案

以 **seed 为配对单位**，不是把同一网络中的每个 packet 当独立样本。为主要比较预先指定主指标、效应量、95% CI 方法和比较族；例如对 per-seed 差值使用预定的配对 bootstrap，保存抽样设置。若用 t 区间或其他方法，要说明适用性并保持一致。

非劣性边界应由应用需求或可解释的工程容忍度确定。旧内部审计使用 −5 个百分点、110% airtime 等门槛，不应自动沿用为 SECON 新结论。存在多个确认性检验时预先指定多重比较控制；未校正区间明确标为描述性。报告效应与不确定性，不能只写 p 值，也不要求所有场景都显著。

遇到运行失败：按预定规则处理并保留日志，不能删去困难 seed。若结果暴露程序错误，作废受影响批次并说明；修复后形成新的快照与批次，不继续沿用错误结果支持新算法。

### 8.3 最小图表集合

1. 状态机／时序图：初发、repeat、recovery、ACK 取消和 deadline。
2. 四模型机制与基线差异表。
3. 三场景主结果：可靠性和 airtime 并列，带配对统计不确定性；保留旧柱图作为历史锚点时明确标注历史数据。
4. 机制消融图：按实际启用组件标注，不把 ledger 全组件效果写成 ACK-only 效果。
5. 一张负载或规模曲线，以及一张必要的延迟／机制成本分解图；按信息密度合并。

图全部由已审计 CSV／JSONL 生成，保存脚本和数据引用。正文、表、图统一数字精度；禁止手工改图使结果更好看。

## 9. 算法要不要重写：用诊断决定

默认不推倒重写。**本节在 development 阶段完成，先于方法／矩阵冻结和正式验证。** 先回答：失败主要来自不可达、过期缓存、DATA 碰撞、ACK 丢失，还是拥塞？CPR 的 repeat 和 recovery 各自解决了什么，又花了多少 airtime？

最多选一个有证据支持的新方向，避免截止前同时堆叠机制：

| 诊断发现 | 可评估的升级候选 | 使用限制及验证 |
| --- | --- | --- |
| 稳态时无必要恢复多 | 依据本地路径年龄／ACK 历史调整 repeat／recovery 时间预算 | 不得使用未来信道或全局成功标签；与固定策略消融 |
| 高负载下无效重复多 | 基于本地队列／可观测信道忙状态的有限退避或准入 | 计入额外等待和业务拒绝；不能通过减少分母提高 PDR |
| 多条已确认路径可用且同路重试低效 | 评估已确认备选路径选择 | 计入路径学习、维护、帧长和内存；不能免费获得备选路线 |

每个新候选先写状态转移、输入可见性、计时／预算、不变量和复杂度，再实现与旧 CPR 同条件比较。若 candidate 经开发实验不值得保留，记录淘汰原因并回到原 CPR；不能为了显得“创新”必然保留。

数学内容建议围绕四件事展开：问题目标（可靠性约束下控制 airtime）、阶段状态转移、deadline 可行性、取消前后成本与上界。可以定义 A＝ΣToA(started frame)，并明确重试／恢复次数的有限上界；阶段成功存在相关性时使用条件概率，不能把各次成功简单当作独立事件相乘。若需要上界或定理，逐条列假设，不能把仿真曲线称为证明。

正式验证结果用于评价已冻结方法，不用于默认继续调参。若它暴露必须处理的错误或新的研究问题，明确结束或作废受影响轮次，登记下一轮研究问题、variant、开发／确认边界，再安排新实验；不能静默循环到满意为止。任何算法变更都需要更新公式／代码映射、适用的新实验批次和版本映射；旧代码数据不得直接改标签支持新算法。

## 10. 固件与实物：单列验证分支

**SECON 所查规则未统一强制实物；对于本论文，实物主要用于验证仿真假设及实现可行性。** 没有设备时可以继续完成仿真主线，但正文必须说明未做 RF 实测。

当前固件不能称为完成：版本 `0.1.4`；曾有 core／lifecycle 17/17 standalone 通过记录，但完整 native 最终回归和板级 gate 尚未闭环。交接中仍有 `testRuntimeAlternatePathFloodDuplicateCancelsPendingRelay` RED、DATA 去重、晚到冷启动 ACK 不得覆盖较新路线、旧流 deadline 不得删除同 generation 刚刷新路线等问题。

实际环境在 `firmware/meshecho_cpr/platformio.ini`：

```bash
cd /Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/firmware/meshecho_cpr
pio test -e native
pio run -e esp32dev_sx1262
pio run -e esp32dev_sx127x
pio run -e nrf52840_sx1262
```

这些是后续验证命令，本次未执行。nRF 板型／引脚是示例，需对应真实板确认。固件默认 SF9／CR7 与历史论文 SF7 配置不同，必须对齐后再比较。三板编译通过不等于无线 PDR 验证。

如果设备现成且时间允许，建议最小实践包：6–12 个节点、2–4 跳、固定布局下的稳态／路径阻断／高争用三个条件；先做小 pilot，再固定每条件业务量、独立重复次数及执行顺序。记录板型、天线、固件 commit、RF 参数、节点位置、时钟／日志对齐、真实 TX／RX、ACK 和故障操作。节点规模只是建议，不是官方要求。

优先验证仿真到固件的 preflight／commit／air-start 语义、取消时机和 ToA；受控阻断须作用于各方案的相同条件。若仅完成 CPR 原型，明确它验证实现可行性，不声称完成与官方 Meshtastic／MeshCore 的硬件公平性能对比。功耗只有接入测量仪器并覆盖 TX／RX／idle 等状态才可称实测整机功耗。

## 11. 需要补的文档与产物

下表都是**计划创建或补充**，本任务书不代表它们已经存在。文档保持简洁，但必须能驱动命令执行和追溯结论。

| 优先级 | 建议路径 | 必须包含的内容 |
| --- | --- | --- |
| P0 | `docs/research/secon2027_checkpoint.md` | 当前任务、快照／版本、已做与未做、命令、产物、错误、下一条动作 |
| P0 | `docs/research/secon2027_experiment_contract.md` | 问题、主指标、场景、样本量、冻结时间、统计方法、失败规则与验收标准 |
| P0 | `configs/secon2027/seed_registry.json` | 历史排除与新 cohort 状态；机器可检查，不能只有口头 holdout 标签 |
| P0 | `configs/secon2027/experiment_matrix.json` | 明确 arms、配置、seed cohort、trace、预算和输出 ID；先实现 schema |
| P1 | `docs/research/secon2027_baseline_fidelity.md` | 四模型／官方机制映射、版本来源、简化、参数与匹配规则 |
| P1 | `docs/research/secon2027_algorithm_spec.md` | 状态机、可见信息、公式到函数／测试映射、wire／时序／复杂度与消融 |
| P1 | `docs/results/secon2027_evaluation.md` | 所有预定结果、CI、消融、敏感性、失败案例与结论边界 |
| P1 | `docs/research/secon2027_claim_evidence.md` | 每项论文主张→图表→run ID→manifest→源码快照，区分历史与新证据 |
| P1 | `docs/reproducibility/secon2027_reproduce.md` | 环境安装、真实运行命令、耗时／空间、校验与从原始产物重画图 |
| P1 | `docs/research/secon2027_submission_checklist.md` | 匿名、页数、格式、引文、标题／作者元数据与适用政策复核 |
| 按实际 | `docs/results/secon2027_firmware_validation.md` | native／板级／RF 分别记录；没有实物就写未验证及原因 |
| 每轮 | `docs/project-management/secon2027_release_map.md` | tested version／snapshot → 数据 → promoted version／commit／tag／push 验证 |

建议新增产物目录：`results/secon2027/<run_id>/`、`paper/secon2027/`。实现时若沿用既有命名体系，可以调整路径，但必须更新本表和复现说明。大型事件日志使用可恢复的归档及 hash；根据 GitHub 限制选择适当存储，不能只上传图片而丢失原始证据。

## 12. SECON 论文的修改方向

创建独立的 `paper/secon2027/`，保留现有 ICC 源文件。使用会议官方链接提供的模板／标准 IEEE conference 10pt；不要手改边距、行距、字号来塞内容。

推荐叙事：LoRa mesh 在确认路径失效／争用下的可靠交付成本问题 → 有限次数、截止期约束的 CPR → ACK 取消的边界 → 四模型与机制消融 → 多场景收益及失败区域。保留 Meshtastic-like、MeshCore-like 和旧 MeshEcho 的明确对比。

建议篇幅预算（合计约 8.8 页，实际以编译 PDF 为准）：标题摘要引言 0.9；相关工作 0.6；模型指标 0.8；方法和必要数学 1.7；实验方法 0.8；结果消融敏感性 2.3；局限结论 0.7；参考文献 1.0。

相关工作补真实已发表的 LoRa mesh／多跳 LPWAN、受控洪泛、路由恢复、ACK suppression／opportunistic forwarding 文献；核查题名、作者、年份、DOI 和与贡献的关系。官方产品文档用于描述协议，不能代替学术相关工作。不要引用未发表的 MASS 稿，也不能构造不存在的文献。

匿名审稿 PDF 不放作者姓名、单位、邮箱、致谢及可直接识别作者的仓库链接／PDF 元数据；自引按正常第三人称处理。保留准确私有作者记录：Zu Gao、Zhi Quan，深圳大学；最终作者名单及顺序以已确认记录为准。不要恢复中文姓名，不要增加“无外部资助”声明。公开匿名 artifact 的处理方式需按当年规则确认。

完成后编译检查，再实际检查导出 PDF 的 9 页限制、双栏排版、图字号、引用、字体和匿名元数据。编译成功不等于版式检查完成；不得交付磁盘旧 PDF 冒充新稿。

## 13. 版本递增、GitHub 与审计一致性

执行用户偏好：**一轮代码修改＋相应测试和仿真验证完成后，版本递增一次并上传 GitHub。** 一轮是一个可审计的改动集合，不是每改一行、每跑一个 seed 就升版；单纯写文档也不凭空制造算法版本。

特别注意：现有 `_source_hashes()` 包括 `VERSION` 和合同；`audit_artifacts()` 会对照当前版本／hash。仿真后直接改 VERSION，再用当前树审计旧数据，会产生版本不一致。这不是可忽略的检查噪声。

每轮执行以下顺序：

1. 记录起始版本和本轮文件范围，保存实际测试源码快照（包含必要的未提交／未跟踪依赖），计算 hash；保持历史证据目录不变。
2. 在冻结快照上做必要测试及本轮开发／验证批次；产物如实记录测试时版本、快照、合同和环境。先完成正确性审计。
3. 验收完成后递增 patch 版本，例如起始确为 `2.1.27` 且无发布冲突时，下一轮升为 `2.1.28`。核对现有远端版本／tag，不能覆盖已有发布。固件自身变更时同步维护它的独立版本映射。
4. release map 明确记录：研究结果由 tested-version＋snapshot 产生，发布版本仅新增了哪些元数据。旧 manifest 不重写；历史审计在旧冻结 source-root 上执行。若新增审计器支持显式 source-root，要验证它确实核对该快照全部依赖。
5. 升版后用开发／回归用例做必要 smoke，确认发布快照和导入版本正常。**不得为了改 VERSION 重跑未见验证集，也不得把旧数据标称为新版本重新测得。** 若除版本元数据外还改变了算法、参数或物理模型，必须按新方法重新验证。
6. 审阅限定文件 diff；仅提交本轮所需改动和依赖。确保从提交恢复的代码等于声称已验证的快照；若缺未跟踪依赖，先补齐，不能创建不可复现 release。禁止顺手提交已有无关改动。
7. 按当前授权 push 至 origin 的适当工作分支；记录本地 commit 和远端确认的 SHA。创建 tag 前检查冲突。上传失败如实记录错误，不宣称上传成功，也不要自动合并无关分支。

性能没有达到预期，但实验完整且代码正确，可发布清楚标注的研究版本；不能称性能升级成功。正确性失败时保留开发记录，不提升为已验证发布。可重复上传的原始实验和匿名审稿 artifact 分开管理，防止稿内链接泄露身份。

## 14. 上下文压缩与任务恢复

自动压缩未必提前通知，因此每完成一个阶段或长时间运行前后主动更新 checkpoint，不能等到最后一刻。

`docs/research/secon2027_checkpoint.md` 使用以下模板：

```markdown
# SECON 2027 执行检查点
- 更新时间／时区：
- 当前真实目标与用户最新要求：
- canonical 路径、分支、HEAD、工作树状态：
- 仓库／固件版本，冻结源码与合同 hash：
- 本轮修改文件与已有无关改动：
- 已完成任务及证据路径：
- 未完成任务／失败原因：
- 已执行完整命令、退出码、运行中进程／会话：
- seed cohort 状态、已暴露范围、不可重用范围：
- manifest／审计报告／图表／PDF 路径及 hash：
- GitHub push 结果及远端 SHA：
- 下一条具体动作／命令：
- 尚需用户提供的信息（仅确实缺失时）：
```

恢复顺序：先读本任务书、checkpoint 和三份根规划文件，再核对实际 Git、文件、进程与种子状态；继续未完成步骤，不重复已完成仿真、不覆盖结果、不把“计划”误读为“完成”。同一任务的历史授权和用户偏好继续有效。

## 15. 11 月内的建议排期与最终交付

| 北京日期 | 目标 | 不能遗漏的输出 |
| --- | --- | --- |
| 11/04–11/07 | P0、基线审计、需求冻结准备 | 源快照、seed registry、完整证据 runner、正确性报告 |
| 11/08–11/11 | 开发 pilot、机制暴露与候选选择，随后冻结方法／合同 | 运行成本、统计方案、场景与样本量、消融定义；来不及验证的新算法不进入正式批次 |
| 11/12–11/18 | 已冻结方法的主比较、消融、有限稳健性 | 原始事件、manifest、审计、全场景结果；不得依据正式结果更换算法 |
| 11/19–11/23 | 结果收敛、必要修复、可选硬件 | 诚实结论、局限、图表、claim-evidence；重大算法改动需重估时间 |
| 11/24–11/27 | 独立 SECON 稿、复现检查 | 9 页匿名 PDF、真实引用、从冻结快照重建的检查记录 |
| 11/28 | 内部可上传状态 | 最终检查表、文件 hash、作者元数据记录和 GitHub 发布映射 |
| 11/30 | 官方全文截止日期 | 提交前复核官方时区和系统节点；不留到最后一刻 |

若实际启动晚于以上日期，先重新估算预算，保留 P0、主要比较、关键消融和论文检查，缩减可选扫描。硬件不足、结果不理想或时间不足都应明确报告，不能伪造完成状态。

最终交付清单：

- [ ] 可恢复的代码快照、对应版本、限定范围提交和确认的 GitHub SHA。
- [ ] 四协议真实机制／参数映射；默认与匹配配置的明确区分。
- [ ] 已冻结合同、seed 登记、主比较、关键消融与预定稳健性结果。
- [ ] 全部原始证据、manifest、正确性审计、失败记录和统计不确定性。
- [ ] 可重画图表及每项论文结论的证据链接。
- [ ] 第 11 节所列必要文档；硬件报告明确已做／未做。
- [ ] 独立、匿名、最多 9 页且经过 PDF 实际检查的 SECON 稿。
- [ ] 简洁的完成说明：改了什么、证明了什么、仍未证明什么、下一步。

本计划的价值是把已有单场景结果提升为可检验、可解释、可复现的研究。是否投稿以及最终结论，必须依据执行后得到的真实证据。
