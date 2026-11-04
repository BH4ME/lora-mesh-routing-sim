# SECON 2027 P0 smoke v3：独立 raw 审计

审计日期：2026-11-04（Asia/Shanghai）。结论：**冻结计划的 21/21 run 在以下明确范围内通过机械完整性与原始账本重算；该结论不等于 P0/P1 全部完成，更不等于九页匿名 SECON 稿或整体研究目标完成。** 未发现本次检查范围内的数据缺失、哈希不一致、指标重算不一致、路径环或源发送预算越界。

本次仅以既有文件进行独立只读核验，未启动模拟器、未重放仿真、未选择或运行新 seed，未更改执行工作区。没有把现成 `audit_attempt` / `audit_plan` / `audit_artifacts` 的通过结果当作独立核验；先读冻结 schema、合同与小量 raw，再用 Python 标准库重新解析、联结和聚合。独立审计脚本与机器结果保存在本报告旁边，均不导入执行仓库模块。

## 锁定对象与证据身份

执行仓库：`/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo`。唯一被验收的计划为 [p0-smoke-v3.json](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/results/secon2027/plans/p0-smoke-v3.json)，stage=`development`，cohort=`secon2027-development-v1`，seed 为 2027000、2027001、2027002，7 arms × 3 seeds。版本为 **2.1.27**；未用可变工作区的后续源码替代冻结源码。

| 对象 | SHA-256 |
| --- | --- |
| plan 文件字节 | `409736b2bb18d5c241b2304d22596ed93be335902b8d2cb693e4a635cca7db73` |
| plan canonical 内容（去除自身 plan_sha256 字段） | `238973ce7c76a2317358cd2fa7e61acc2b7b0bf190192af7b731367cd3380ebd` |
| matrix canonical 内容 | `bb81ec400edbab5f2b6ebc1eb47d4f81907b366ff1f7a92964dcf591d3275988` |
| 源文件 inventory / snapshot ID | `e8d94c29b3797a55787ee8cc5a60c3d08b4949186f2250581ed36d851ef5b1a2` |
| snapshot.json 文件字节 | `748e736ba1eb2e66f66c63b815385ee7ad8304d2fedd64348579c28ea2646ff9` |
| 冻结 experiment contract 文件 | `b23e09f654646aadec3af45b2d65f8eda55cf9aee1b4762ab9656c69f6c15192` |
| 独立核验脚本 | `654e4aba58e3d2770200a71441d86bde5d14e39764e00d1b26cd999979e52002` |
| 独立核验 JSON 结果 | `33055cf89f87c03a3686806c7f1ebcad10b601d6dfd00353abd07b36deef322f` |

已逐一核对 snapshot 的 **165 个文件**字节数及 SHA-256，排除缓存目录后文件集合与 inventory 完全一致；重新计算 snapshot、matrix、plan 及 21 个 run key。每个 run 的 started spec、completion 中的 plan/source/version、manifest 中的源码文件哈希与冻结对象一致。每个 run 都仅有 `attempt-001`，均有状态 completed 的 completion 和 evidence manifest；21 个 completion 列出的 **357 个文件哈希**全部匹配，17 个必需文件/run 均存在。完整 run key、对应 completion 文件 SHA-256 和 attempt 列表见机器结果。

[独立核验脚本](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_smoke_raw_review.py)；[完整检查结果及 run identity](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_smoke_raw_review.json)。

## 从原始记录重算的范围

- **分母**：以 identities 的预定 application trace 为唯一 N；逐条联结 flow_id、src、dst、enqueue time 和 deadline。每 run 4 条，分别在 1/2/3/4 s 发送 5→9、9→5、10→14、14→10，deadline 为 enqueue+30 s。21 个 run 共 **84 个 run-flow 记录**，对应 12 个跨 arm 配对的 scheduled flow 实例；84 不是独立统计样本量。
- **deadline ACK / delivery**：32 条 accepted ACK 均联结到唯一物理 ACK TX、其 started request，以及源节点的 decoded RX；源/目的/flow、时间、reverse path、reverse hop 一致。destination delivery 则独立从 TX→decoded destination RX 重建最早可交付时刻，并与 flow 的 first_delivery_at 对照；已区分 Meshtastic-like 的 `DATA` flood 前缀路径与已知全路径的定向 DATA。全部 84 条 deadline 布尔值与 CSV 数值一致：**32 ACK、55 delivery**。缺失 ACK 或 delivery 的流仍在 N 中。
- **物理发送及成本**：1,543 条 request 中 1,399 条 started 与 1,399 条 TX 一一对应，余下 144 条均为 canceled，均无 tx_id。全部 TX 满足 start≤75 s（45 s generation+30 s drain），ToA>0 且 ToA=end−start；完整 modeled ToA 总和为 **115.317504 s**。CSV 的 tx_count、started_request_count、airtime、DATA/control/ACK 分区均重算匹配。未把取消请求计为物理 TX。
- **RX 完整性**：27,980 条 RX，即每个 TX 的 20 个接收节点（包括 sender 的 self 记录）齐全且无重复；全部 RX→TX request ID、flow、sender、packet kind、path、index、marker、时间匹配。interference_tx_ids 全部可找到物理 TX。此为记录联结核验，没有重新计算 PHY 解码概率、capture 或射频传播。
- **路径与源阶段上界**：全部 1,399 条 TX 路径均无重复节点，其中 CPR 家族为 656 条。四个 CPR arms 的 48 条流都有且仅有一条 `F_INITIAL` decision，各流源节点只有一次初始 FLOOD 物理发送；本批实际最大值为 1，未超过每阶段一次和每流最多 3 次的预算。55 条首交付路径为 4 hops（32 条）或 6 hops（23 条），并非仅有配置 hop limit。
- **消融**：三种消融在三个 seed 的 resolved parameters 中分别仅切换 cancel_on_ack、enable_repeat、enable_recovery（名称除外），其余参数一致。noackcancel 的三个 run 无 `cpr-cancel` / `cpr-cancel-check`；norepeat 未观察到 repeat DATA、norecovery 未观察到 recovery FLOOD。**后两项仅为本批未出现禁止阶段，不能证明其触发后的动态行为正确。**
- **ACK 取消的有限事件核验**：303 条 cancel-check 与 24 条 cancel action 均能联结到相应 relay 的 decoded ACK RX。24 条 cancel action 各自匹配一个相同 flow/relay/marker 的 FLOOD request，满足 request time≤cancel action time≤最终 status time，且该 request 为 canceled、没有物理 TX。request 的 status_at 是后续处理取消状态时刻，不能错误要求它等于 ACK action 的时刻。此检查未重演每一次取消资格判定或 commit/timer 同时刻竞态。

## 全部 run 的重算结果

以下数字用于核对账本；不做模型优劣排名、显著性或正式性能推断。N 固定为 4，ACK 和 delivery 两列均指 deadline 内计数。

| arm | seed | N | ACK | delivery | physical TX | airtime (s) | no-start requests |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho-cpr | 2027000 | 4 | 3 | 4 | 61 | 5.442816 | 10 |
| meshecho-cpr | 2027001 | 4 | 0 | 2 | 46 | 4.414976 | 8 |
| meshecho-cpr | 2027002 | 4 | 2 | 3 | 57 | 5.201152 | 12 |
| meshecho | 2027000 | 4 | 3 | 3 | 122 | 8.607232 | 0 |
| meshecho | 2027001 | 4 | 2 | 2 | 110 | 7.626240 | 0 |
| meshecho | 2027002 | 4 | 2 | 2 | 109 | 7.595264 | 0 |
| meshtastic | 2027000 | 4 | 2 | 4 | 67 | 6.145792 | 8 |
| meshtastic | 2027001 | 4 | 2 | 4 | 58 | 5.324288 | 13 |
| meshtastic | 2027002 | 4 | 1 | 2 | 53 | 5.056768 | 9 |
| meshcore | 2027000 | 4 | 1 | 1 | 84 | 5.458944 | 0 |
| meshcore | 2027001 | 4 | 0 | 0 | 70 | 4.359680 | 0 |
| meshcore | 2027002 | 4 | 1 | 1 | 70 | 4.590080 | 0 |
| meshecho-cpr-noackcancel | 2027000 | 4 | 1 | 4 | 57 | 5.339392 | 6 |
| meshecho-cpr-noackcancel | 2027001 | 4 | 0 | 2 | 46 | 4.414976 | 8 |
| meshecho-cpr-noackcancel | 2027002 | 4 | 2 | 3 | 61 | 5.622016 | 10 |
| meshecho-cpr-norepeat | 2027000 | 4 | 3 | 4 | 61 | 5.442816 | 10 |
| meshecho-cpr-norepeat | 2027001 | 4 | 0 | 2 | 46 | 4.414976 | 8 |
| meshecho-cpr-norepeat | 2027002 | 4 | 2 | 3 | 57 | 5.201152 | 12 |
| meshecho-cpr-norecovery | 2027000 | 4 | 3 | 4 | 61 | 5.442816 | 10 |
| meshecho-cpr-norecovery | 2027001 | 4 | 0 | 2 | 46 | 4.414976 | 8 |
| meshecho-cpr-norecovery | 2027002 | 4 | 2 | 3 | 57 | 5.201152 | 12 |

物理 packet kind 分区相加严格回到 1,399 TX 和 115.317504 s：

| packet kind | TX | airtime (s) |
| --- | ---: | ---: |
| FLOOD | 527 | 52.906752 |
| ACK | 208 | 12.331008 |
| RREQ | 374 | 22.869504 |
| RREP | 74 | 5.133824 |
| DATA | 196 | 20.151296 |
| FALLBACK | 20 | 1.925120 |

## 公共输入配对一致性

逐 seed 对比全部 7 arms 的 **完整已序列化内容**，不是只看 seed 或标签：20 个节点坐标与角色、endpoint pairs、4 条 application trace、radio 参数、190 个静态 shadowing edge 值、common environment 全部一致；case/topology/traffic/radio/pair/environment hash 标签也逐项相等，且 CSV 标签与 identities 一致。独立重算 trace、topology、radio、pair 和 case 的内容摘要匹配其声明值；JSON 另记录每个 seed 的 static-shadowing 和完整 common-environment 序列化内容摘要。

environment 身份标签的对比范围是三份已存对象之间的一致性；环境对象在输出时被四舍五入，因此这里不声称从 rounded raw 重新恢复其原始全精度 environment_sha256。冻结 `tools/secon2027_scenarios.py` 中 channel field 使用 `(seed,sender,receiver,time_bin)` 的 SHA-256，而不以协议事件数推进随机流；该代码只做静态阅读，没有重演全部 channel 抽样。公共环境相同不表示不同协议拥有相同干扰历史。

## 空数据、失败与本次验收边界

所有 21 个 run 已完成；本计划内没有执行失败 attempt、缺失 key 或重试。只审计 v3 的这 21 个 key，不对先前 v1/v2 或后续计划的失败归档作结论。raw 的不利结果没有被过滤：52/84 条流未获 deadline ACK，29/84 条流未获 deadline delivery；`meshcore/2027001` 的 N=4、ACK=0、delivery=0、TX=70、airtime=4.359680 s 完整保留，其 airtime-per-deadline-delivery CSV 单元格为空（undefined），不是 0。

以下空文件是实际保留的证据，不能误判为被遗漏，也不能用于声称事件已经发生：

| 文件 | 空文件数 | 解释 |
| --- | ---: | --- |
| evidence.acks.jsonl | 5 | 四个 CPR arms 的 seed 2027001，加 meshcore/2027001 均无 accepted ACK |
| evidence.actions.jsonl | 9 | 三个非 CPR arms × 三个 seed；这些 baseline 未输出 CPR action events |
| evidence.paired.csv | 21 | worker 每次只跑一个 arm；因此本审计直接跨 identities 重建配对 |
| stdout.log / stderr.log | 各 21 | 空日志仍存在并受 completion hash 保护 |

**机制暴露不足是本次最重要的局限。** 48 条 CPR 流全部为冷启动 `F_INITIAL`，没有缓存命中定向 D_INITIAL、D_REPEAT 或 F_RECOVERY；norepeat/norecovery 与 CPR 的结果相同源于未触发相应阶段。这批 smoke 可以验收完整账本、冷启动多跳、源端 ACK provenance 和已发生的有限 ACK 取消实例，但不能验收 repeat/recovery 效果、skip-repeat 时间预算、旧 epoch/marker 攻击性条件、容量溢出、定时器并列、commit 后取消和完整源 FSM。全批也没有 late ACK/delivery、in-flight cutoff 或 reserved future TX 的边界暴露；这些需要对应确定性 fixture 或后续合规计划的独立证据。

本审计没有重新推导每种报文的 wire-size ToA 公式，没有核验设备能耗，也没有进行硬件或 RF 测试；这里的“physical TX”仅指模拟器账本中已实际开始的发射。三个 development seeds 的 smoke 不是正式性能验证或未见 holdout。S1/S2/S3 pilot、全部 P0/P1 门槛、正式方法与矩阵冻结、正式结果及九页匿名 SECON 稿仍须各自完成并验收；不能以本报告将整体目标标为完成。
