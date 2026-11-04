# ICC PDF 与仓库代码、组网逻辑审查

日期：2026-11-04。范围：只读核对现有 PDF、当前 TeX、Python 仿真实现及已有实验数据；不改论文或协议实现。

## 审查对象与进度

- 主要 PDF：`paper/icc2027/icc2027_lora_mesh.pdf`。
- 对应当前源文件：`paper/icc2027/icc2027_lora_mesh.tex`。
- 已确认 PDF 共 7 页，创建于 2026-10-13 10:34；文件内容与当前源文件存在差异，不能将源文件的编译成功当作该 PDF 正确的证明。
- 临时提取文本和页图：`/tmp/icc-pdf-code-review.OmacCG/`。
- [完成] PDF 版本与全部 7 页渲染检查。
- [完成] 冷启动、路由缓存、重试、恢复与 ACK/中继抑制代码对照。
- [完成] 三基线公式、参数与组网公平性检查。
- [完成] 指标定义、数据来源、统计区间和结论强度检查。
- [完成] 合并有代码证据的问题，区分旧 PDF 问题和当前源文件仍有的问题，并给出修正优先级。

## 边界

审查的完成意味着提供有出处的问题与结论，不代表修复论文、完成固件或证明实际射频性能。保留种子不重新仿真。

## 版本与基础核验

- PDF SHA-256：`271fec311b6f5e5f88ed46a890dbd4988d4d3ac555c1e028b9f42febecd9fee0`。
- 当前 TeX SHA-256：`cee23822ce7e04ff033e9dd558b55e5687879465570ab2f5ae38cbf30afb0248`。
- 已渲染并逐页检查全部 7 页。第 4 页 Table I 压缩到单栏后字体极小，第 6 页图 1 和 Table II 同样难读；第 7 页右栏空置。页数是实测 7 页，但本次不根据未核实的 ICC 年度页数政策断言超限。
- 旧 PDF 式 (3) 将旧 MeshEcho 置信度写成一次性瓶颈减惩罚；实际逐跳传递并重复扣惩罚。当前 TeX 的递推式已修正。
- 旧 PDF 式 (5) 混同请求承诺时刻与排队后空中发送时刻，还为 MT 引入实现没有的 deadline 门控；当前 TeX 已分开定义。
- 旧 PDF 式 (7)/(8)/(11) 让 RREP 成本乘 discovery-success 指示量，漏掉已发送但未成功回到源的 RREP；当前 TeX 已把实际 RREQ/RREP 独立计费。

## 总体判断

当前磁盘 PDF 需要实质修改后再作为投稿稿件。问题不只是排版：旧 PDF 有公式及实现说明错误；当前 Python 仿真代码还存在洪泛回源再次转发、并发 ACK 被路由代次误拒两项组网问题。重新导出当前 TeX 可以解决前一类中的大部分文字与公式错误，但不能解决后一类算法问题。

本次是针对代码一致性、网络事件逻辑和实验可解释性的审查，不估算中稿概率。没有编辑论文、修改协议、重新仿真、推送或投稿。

## 已确认的优点与可信部分

1. 四协议 20 种子、80 行运行结果可追溯到现有 CSV；ACK/目的端 PDR、空口时间、TX 能量、TX 次数及当前源中的增益、配对区间能与数据对应。
2. 拓扑、应用流量、无线电参数和通信对身份有配对记录，未发现把不同负载的结果直接拼表；不完整 RX 记录计数为零。
3. 源端 ACK 包有请求 ID、端点、路径、上一跳、marker 与生命周期检查；抑制用的是实际解码 ACK，未发现以全局“目的端已收到”标志直接取消中继的捷径。
4. 当前 TeX 已披露 named-product 基线是行为模型，结果不是官方固件实测。当前源中的条件概率链、成本互斥记账和 commit/air-start 区分比磁盘 PDF 严谨。

这些核验只能说明表中数字忠实反映当前实现，不能证明实现已经满足论文宣称的全部不变量。

## W1：洪泛回源后再次发送，形成重复节点路径（重大，当前仍存在）

源状态机最多作一次 F_RECOVERY 决策，与“源节点实际最多发三个 DATA/FLOOD”不是同一性质。现有日志里前者成立，后者不成立。

在 [CPR 接收 FLOOD 的代码](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/lora_mesh_sim.py:4398) 中，先调用父类 `_on_flood()`，后检查 `packet.origin != receiver`、`receiver not in packet.path`。这些检查只决定是否登记 ACK 取消账目，不能撤销父类已经排队的转发。[父类](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/lora_mesh_sim.py:3719) 会直接把 receiver 追加到 path。unicast [初始洪泛](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/lora_mesh_sim.py:4057) 与 [恢复洪泛](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/lora_mesh_sim.py:4169) 注入时又没有登记源 seen key。

现有冻结日志中，seed 92304、flow 10、源节点 9 的全部源 DATA/FLOOD 如下，截止时间为 87.916909978309 秒：

| TX ID | 时间（s） | 类型 / marker | 路径 |
|---|---:|---|---|
| 19 | 57.916909978309 | DATA / initial | `[9,2]` |
| 22 | 58.315901978309 | DATA / repeat=1 | `[9,2]` |
| 25 | 58.714893978309 | FLOOD / recovery=2 | `[9]` |
| 44 | 60.957082304726 | FLOOD / recovery=2 | `[9,5,9]` |

证据：[transmissions.jsonl 第 1535 行](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/results/meshecho_cpr_holdout_92300_92319_20261006.transmissions.jsonl:1535)，其余三条为 1538、1541、1560 行。四次均在 deadline 前，不包含 ACK。

全体 CPR 668 个流的源 DATA/FLOOD 次数分布为：1 次 635 流、2 次 12 流、3 次 11 流、4 次 10 流。21 次恢复决策对应 31 次源 marker=2 FLOOD；84 个 F_INITIAL 中也有 7 个流发生第二次源洪泛。总计 19 条实际 TX 携带重复节点路径。冷启动实例在同一日志第 1221、1225 行，路径从 `[17]` 变成 `[17,16,17]`。

论文影响：PDF 第 5–6 页的有界源动作及无环路径解释需要限定；当前 [TeX 的 source 上限](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/paper/icc2027/icc2027_lora_mesh.tex:480) 若解释为源无线电实际发包数，也不成立。第四次发送是回流副本转发，不是第二次控制器恢复决策；不能混淆两者，也不能仅重命名变量而忽略回流缺陷。TTL 有界，因此本次没有声称存在无限循环。

建议：在任何转发副作用前验证路径与源回流；初始/恢复注入时登记相应 seen key。覆盖回源、含环路径、过期 seen 与每阶段转发去重测试，再重新评估修改后的版本。旧日志已把这些 TX 计入成本，不能手工扣除并假装得到修复后结果。

## W2：正常 ACK 更新路径代次，误拒并发流的合法 ACK（重大，当前仍存在）

[每个被接受的 ACK](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/lora_mesh_sim.py:4545) 都调用 `install_route()`，即使路径不变。[安装函数](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/meshecho_drc.py:248) 无条件递增 generation，而 [另一个流的 ACK 校验](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/lora_mesh_sim.py:4347) 要求原 generation/epoch 等于当前值。

主审与独立检查均调用生产 `on_ack()` 完成最小复现：两个消息在 t=1 从节点 0 发往 1，deadline=31，路径 `(0,1)`。第一条 ACK 在 t=2 接受；第二条 ACK 在 t=3 到达，身份、路径和发送记录都正确，却被拒为 `stale-route-generation`。

| 初始分支 | 第一条 ACK | 第二条 ACK 在第一次更新前 | 更新后拒绝原因 | 代次 |
|---|---|---|---|---|
| F_INITIAL | 接受，2.0 s | 可接受 | stale-route-generation | 0 → 1 |
| R_INITIAL | 接受，2.0 s | 可接受 | stale-route-generation | 1 → 2 |

这次复现没有调用 `Simulator.run()`，没有信道随机数或新实验。它证明两个合法并发消息会因共享缓存更新相互干扰；没有量化此问题对现有整组 PDR 的具体贡献。

PDF 第 6 页式 (28) 与当前 [TeX 路由更新式](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/paper/icc2027/icc2027_lora_mesh.tex:392) 都表达了这一过严规则。因此它不是仅靠改写说明可消除的错误。

建议：将“确认当前应用消息”与“允许更新共享路由缓存”分开；同路径的有效刷新应避免无条件制造新路径代次。晚到但属于在途流的有效 ACK 可以确认该流，同时禁止它覆盖更新的不同路径。修复时仍需保留重放、端点、marker 和 deadline 校验，并验证并发 ACK、不同路径替换及旧流 deadline 的交互。

## W3：六跳只是上限，现有成功样本主要是单跳（重大证据缺口）

对 [ACK 日志](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/results/meshecho_cpr_holdout_92300_92319_20261006.acks.jsonl) 过滤 CPR、accepted=true、in_deadline=true，并按 `(seed,flow_id)` 去重：656 条成功确认对应 656 个唯一流，跳数为：

| 跳数 | 成功确认流数 | 占比 |
|---:|---:|---:|
| 1 | 624 | 95.12% |
| 2 | 17 | 2.59% |
| 3 | 15 | 2.29% |
| 4–6 | 0 | 0% |

此统计描述成功确认路径，不把失败流的路径强行归类，也不声称网络只能形成三跳。PDF 和当前源虽然写了 20 个节点、六跳上限，却没有报告实际跳数构成。它们支持这个以单跳为主的场景，尚不足以证明深多跳的可靠性、ACK 返回与恢复开销优势。

建议：先披露真实跳数分布；后续用不能直接通信的源/目的对、强制 2/3/4/6 跳拓扑和有替代路径的网状拓扑，分跳数报告 DATA PDR、ACK PDR、延迟、重试、恢复和空口时间。当前源“需要更多 route depths”这一限制仍应保留。

## W4：旧 PDF 的数学与实现说明错误（多数已在当前 TeX 修正）

| PDF 位置 | 问题与反例 | 当前源状态 / 建议 |
|---|---|---|
| p2 式 (3) | 把旧 ME 置信度写成 `min(c_h)-λ·1{H≥2}`。实际是逐跳继承并扣惩罚；3 跳都为 0.9、λ=0.025 时代码为 0.85，旧式为 0.875。代码见 `lora_mesh_sim.py:2601`、`:2739`。 | TeX :223 已改为递推式。 |
| p2 式 (5)、p3 式 (9)，p5 式 (22)/(24) | 把 request commitment 与未来 air start 混为一谈。请求在 κ=1 处理、无线电到 5 才空闲，3 秒来的 ACK/duplicate 无法取消已经 committed 的包。实际 `begin_transmission` 在 :1149 计算未来 start，:1184 当场 committed。 | TeX :264、:376、:443 已区分；旧 PDF 必须更新。 |
| p2 式 (5) | 给 MT 加上 `t<D_i` 的转发门控，但该基线没有 CPR 的 deadline admission。deadline 是成功率统计窗口，迟到发送仍计成本。继承的 `on_tx_request` :1510 原样返回包。 | TeX :274–284 已修。 |
| p3 式 (7)/(8)/(11)，p4 式 (16) | discovery success `d` 乘 RREP 成本，漏掉已经发送但没有返回源的 RREP。应为 `A_Q+A_S+d A_D`。 | TeX :334 已独立计 RREQ/RREP 成本。 |
| p5 式 (26) | 把边际 ACK 失败率与 DATA 失败率再次相乘。DATA 未到已经意味着该次 ACK 不成功；a0=d0=0.5、重试必送达时，旧式得 0.75，正确结果为 1。 | TeX :508–557 用完整历史条件概率链与 `E^A⊆E^D` 修正。表中 PDR 来自事件日志，不由旧错式计算。 |
| p6 式 (30) | 将“没被 ACK 取消”直接当成“一定发送”，遗漏 duplicate suppression、容量淘汰等其他阻止发送的条件。 | TeX :600 引入 `z_v^0`，仅声称固定局部事件轨迹上的取消账目。 |
| p3 两种 source routing 共用 first-valid-RREP 规则的说明 | ME 默认收集 2 秒后按 confidence/跳数选路，MC 默认窗口为 0、第一请求即回复。 | 当前源已分开描述。 |

当前源中的 `B_R/B_F` 与实现的 ToA/等待项结构一致，但这些预算没有约束任意中继排队；当前源称为“本地调度预算”适当，旧 PDF 的端到端保守上界措辞过强。

## W5：参数与计数口径（旧 PDF 错误和当前证据边界）

PDF 第 6 页实验段把 TTL=600 秒、洪泛 base/jitter=0.45/0.65 秒写得像公共参数。实际 CPR/ME 用这些设置；MT 为 0.75/0.75 秒加 SNR 罚项；MC TTL=300 秒、发现洪泛为 0.5/0.7 秒。当前 TeX :633–641 已列明差异。300 秒和 600 秒都长于 270 秒的运行窗口，不能据此断言 TTL 差异导致本次收益；转发时延和发现逻辑仍需匹配敏感性分析。

PDF Table II 的 `RX attempts` 使用了全部 receiver ledger 记录数，包含每次发射的一条 `reason=self`。代码 [try_receive](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/lora_mesh_sim.py:1291) 对发射节点自身只登记排除记录后返回。旧表 1633、3130、6365、3062 因而恰等于 TX 均值乘 20，并非真实解码尝试数；排除 self 后为 1551.35、2973.50、6046.75、2908.90。当前源已删除这列。

PDF 式 (31)–(33) 的 suppressed-forwards/duplicate-RX 比率也不等于 ACK 取消收益。MT [计数点](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/lora_mesh_sim.py:1652) 没检查 committed，可能在发送已不可撤销后增加 suppressed counter；CPR 的 ACK 取消另外记为 `cpr-cancel`。当前源已正确说明两者不同。

已有 CPR actions 中 ACK 取消事件共 1606 次：初始洪泛 1444 次、恢复洪泛 162 次。应区分这两类；不能把所有节省都归为“恢复洪泛”的收益，也不能把事件数直接视为因果节约的全网 airtime。已有 no-cancel 控制可以用于后续消融分析，但修复实现后需重新验证，容量淘汰等设置也应一致。

TX 能量使用 `3.3×0.12×A=0.396A`，与 CSV 一致，只是发射 airtime 的线性换算；不能作为独立测得的电池寿命结论。

## W6：对照强度和外推范围

当前四臂是简化行为模型。MC 基线依赖显式 RREQ/RREP，而文中也承认官方产品具有 initial DATA flood / delivery report 学路机制；MT 较新的 next-hop learning 不在该 arm 中。仓库已有 [MeshtasticCommonAck](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/lora_mesh_sim.py:2004) 和 [MeshCoreCommonAck](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/lora_mesh_sim.py:2196) 等更接近 DATA-first/ACK-learned 过程的对照，不在当前四臂矩阵中。

对论文最强的替代解释是：部分收益可能来自比较对象的 discovery/ACK 信息和转发计时差异，而不是 CPR 独有机制。现有配对控制了拓扑与业务，但没有排除这一解释。当前源已限定为 `-like` 仿真模型，这个限定必要；若要扩大到现代产品组网优势，需要补强匹配配置及共同 ACK 信息的对照。

## W7：排版可读性

全部 7 页已转成 PNG 检查。第 4 页 Table I 被整体缩到单栏，字极小；第 6 页图 1 的三面板和 Table II 也过度缩小。第 7 页右栏为空。未发现缺页或空白替代图，但读者难以正常阅读关键对比。

建议重新导出当前源后，再核实表格分栏、图字号、参考文献完整性和当年具体页数规则。本次没有编译另一份 PDF，也没有把当前源的编译成功当作新 PDF 的视觉验收。

## 证据与复核方式

- PDF：Poppler `pdfinfo` 确认 7 页；`pdftotext -layout` 提取；`pdftoppm -r 105 -png` 渲染全部页并逐页检查。
- 独立只读检查覆盖 CPR 状态机、基线和统计/PHY 三部分。主审重新执行并发 `on_ack()` 反例，并独立汇总源发送次数、含环 TX、ACK 跳数、取消类型和四臂均值。
- 冻结 manifest 中 `lora_mesh_sim.py`、`meshecho_cpr.py`、`meshecho_drc.py`、`tools/run_cpr_experiment.py` 四个 SHA-256 均与当前代码匹配。
- 冻结详细日志中的 CPR 20 个 seed 行与 [四臂运行数据](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/results/meshecho_four_protocol_comparison_92300_92319_20261012_rerun.runs.csv) 的 CPR 行相符：仅忽略 split 标签，数值容差为 1e-12，无剩余差异。故日志中的回流现象与论文采用的 CPR 数值有直接关联。
- 旧 20261006 external-comparison 数据只有三臂，包含 legacy ME 的完整四臂证据来自 20261012 文件。未混淆二者。
- 本次没有修改 `.tex`、`.pdf` 或 Python/C++ 实现，没有运行新随机仿真、重跑保留种子或进行射频硬件验证。C++ 固件测试结果没有被用来替代 Python 仿真证据。

## 建议修正顺序

1. 先修回流/路径校验和并发 ACK 生命周期，分别验证对应确定性反例及邻近边界，避免通过放宽所有校验掩盖问题。
2. 冻结修复后的实现，再按明确实验计划更新数据；旧结果保留为旧版本记录，不直接作为修复后协议结果。
3. 报告实际跳数，补深多跳和匹配基线；把源 FSM 动作数、源实际 TX 次数、全网 TX 次数分别统计。
4. 更新公式与文本，导出与当前源对应的 PDF，并做最终版式与页数检查。

审查结论：有问题。最优先处理的是当前组网实现的两项缺陷及多跳证据不足，之后同步 PDF。四臂数值本身与现有实现日志一致，不应把本次发现误说成所有数据被算错。
