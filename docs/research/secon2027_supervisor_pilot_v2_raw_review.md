**SECON 2027 development pilot v2：独立 raw 审查**

2026-11-04，Asia/Shanghai。**预定 72/72 run 均有唯一 attempt-001 completion，零 failure；本次独立重建及身份/哈希核对未发现范围内不一致。** S1 有实际多跳与冷/已确认路由选择；S2 有实际缓存路径故障交集、指定接收失败和恢复绕行链；S3 有碰撞、源排队、取消和源状态容量丢弃。**S3 的 CPR 及时 ACK 低于 legacy ME 与 MC-like，空口占用更高，不能概括为 CPR 整体胜出。** 这是一批已暴露 seed 的 development 诊断，既不是正式 cohort 或 holdout，也不表示消融、RF、全部 P0/P1、匿名投稿稿或整体项目完成。

审查对象为 `/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo` 中 `results/secon2027/plans/development-pilot-v2.json` 绑定的完成证据。所有审计脚本与报告只写入 canonical `docs/research`；没有修改执行仓库，没有运行/重放模拟器、研究 seed 或随机过程。本次主审计为独立 stdlib 脚本，不导入仓库实现，不调用现成 analyzer/audit CLI 代替重建；执行方的 worker audit 只作为哈希绑定 artifact，不作为重建结果的依据。

| 冻结身份 | 值 |
| --- | --- |
| plan 文件 SHA-256 | `cf30790288c060f93302eeefc5a9e3535533d2ada9d02d2ded80bd6768c0aff0` |
| canonical plan_sha256 | `0c49a69a5c3725c9f72ff2e28ed870d10db1df7eec4319f6397097b84a2c85e7` |
| matrix_sha256 | `1db1e67465ae0d35d45a161d6ca4b6a225395741bcf5c30903e1e8ff77d17919` |
| source snapshot | `ee890e25030782fc01208ee4ce1f20863c6ade5322ac954ad67ae48b594056a2` |
| contract SHA-256 | `b23e09f654646aadec3af45b2d65f8eda55cf9aee1b4762ab9656c69f6c15192` |
| tested version / frozen_at | `2.1.28` / `2026-11-04T08:42:54.923644+00:00` |
| cohort / seeds | `secon2027-development-v1` / `2027000, 2027001, 2027002` |

72 个 run key 与 completion SHA、逐项检查次数、逐 run 失败流 ID、分母/指标/packet-kind 成本、请求状态与 RX 原因均见 [secon2027_supervisor_pilot_v2_raw_review.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_pilot_v2_raw_review.json)；复核入口为 [secon2027_supervisor_pilot_v2_raw_review.py](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_pilot_v2_raw_review.py)。JSON 状态为 `passed`，`issues=[]`。核对了冻结 snapshot 全部 166 文件及精确清单，和 72 completion 列出的 1,224 artifact hashes。审计脚本 SHA-256 为 `5809d69a1fa7a65b76dbbb4ef545d8e789bf16a7e7dafe503f65b5f9d6705301`，JSON SHA-256 为 `ba7f556a78091f9ae1b4fc37c89236e129a2ed39363265d24139a3e9d80c3871`。

旧 `development-pilot-v1` 在完成 48 run 后触发 recovery 分支的 `CprDecision` NameError。旧失败与旧冻结对象仍保留，未把那 48 个结果拼入本批分母。修复仅补 import 后有独立分支 fixture 证据，见 [secon2027_supervisor_recovery_branch_review.md](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_recovery_branch_review.md)。v2 使用新计划、新 snapshot 重新物理跑满 72 keys；本审查未以旧批或 fixture 代替其完整 raw。

**重建口径与记录完整性。** N 来自 frozen application trace，逐 flow 与登记记录联结，包含无请求、无发送、失败和无 ACK 流。delivery 从正确目的端 decoded DATA/FLOOD 的物理 RX 重建最早到达，ACK 从 accepted event 联结对应 ACK request→TX→源端 decoded RX，并分别与 enqueue+30 s deadline 比较。TX 必须来自 `started` request，airtime 求和全部已开始物理 TX 的 `toa_s`，包含 DATA/FLOOD、ACK 及基线发现控制包；未把请求次数当成 TX，也未用截断在观察窗内的占用替代完整包 airtime。

| 全 72 run 账本量（含两个 regime 的重复有效配置） | 数量 |
| --- | ---: |
| scheduled run-flow 记录 N | 5,448 |
| 及时 source ACK / destination delivery | 2,233 / 3,137 |
| 物理 TX / 完整 airtime | 57,887 / 5,225.924352 s |
| request / started / no-start | 62,270 / 57,887 / 4,383 |
| RX 记录 / action 记录 | 1,157,740 / 23,172 |
| accepted / rejected ACK event | 2,233 / 0 |
| 首交付 4-hop / 6-hop | 1,661 / 1,476 |

每个完成 TX 均有 20 个 receiver 记录（含 self），RX→TX、TX→request、干扰 TX 引用及记录数量全部一致。总计 4,383 个 no-start 中，4,361 为 `canceled-before-start`，22 为 `protocol-hook`；它们留在 request 账本，未给物理 TX 增加虚假 airtime。所有传输路径均无节点重复；全批首交付只观察到 4/6 hops，实际多跳不依赖配置标签推断。S2 的额外逐跳链核验覆盖全部 548 条已交付 run-flow；主审计其他场景核验终端 RX、携带路径和 hop 数，未声称对其每条路线另做完整路径链重放。

全部 5,448 flows 的 CSV PDR、请求/发送数量、ACK/delivery、airtime 与物理分类已逐 run 对齐。没有晚到 ACK 或 delivery。额外 [secon2027_supervisor_pilot_v2_cutoff_exposure.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_pilot_v2_cutoff_exposure.json) 从全 57,887 TX 独立检查 270 s cutoff，in-flight 与 future-start 都为 0；因此本批没有暴露这些边界，不能单凭零计数验收边界处理。72 个 `paired.csv`、72 个 stdout、72 个 stderr 以及 54 个非 CPR `actions.jsonl` 为空且被保留；本批没有空 ACK 文件。未删除失败流、零计数、空文件或弱暴露 seed。

**配对和参数。** 六个 case（S1/S2/S3 × default/matched），每个四 arms × 三 seeds，共 72 次物理运行；8 个 arm ID 仅对应四个实现。逐 case/seed 对四 arms 的完整 application trace、nodes、pairs、radio、static shadowing 和 common environment 做内容相等检查；同 scenario/seed 的 default/matched 公共输入也一致。因此这里的配对有已存原始外生输入内容依据，不只依靠 seed 相同。S1/S2 每 run 的 N 依 seed 为 36/28/39，S3 为 160/167/148。不能把 flow、RX opportunities 或重复 regime 当成独立统计重复。

| 实现 | default → matched 实际参数变化 |
| --- | --- |
| CPR / legacy ME | TTL=600、base=0.45、jitter=0.65 已相同，有效配置不变 |
| MT-like | base 0.75→0.45，jitter 0.75→0.65 |
| MC-like | TTL 300→600，base 0.5→0.45，jitter 0.7→0.65 |

全部 36 default/matched 对的 resolved 参数均与声明覆盖一致。CPR 与 legacy ME 在两个 regime 的逐 seed 主指标、物理数量与机制计数相同；这些重复有效配置已物理完成并保留，但没有增加独立 replication。匹配没有抹去不同实现的 SNR 延迟、发现方式及 ACK 语义；MT-like、MC-like 不是未经限定的真实固件性能替代。

**CPR 机制确实被触发。** 下表是 default 每场景三个 seed 的总计；matched CPR 完全相同。`冷 flood` 的严格含义是 `no-feasible-confirmed-route` 导致初始 flood，可能是尚无缓存、失效或无可用已确认路线，不把所有次数说成系统首次冷启动。`已确认初发` 是实际 source DATA；repeat/recovery 也只统计真实 source TX。4/6-hop 列是目的端首交付数量。

| 场景 | N | 冷 flood | 已确认初发 | 初始 DROP | repeat | recovery | ACK 取消成功 | 4 / 6-hop delivery |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S1 | 103 | 32 | 71 | 0 | 22 | 11 | 16 | 60 / 32 |
| S2 | 103 | 43 | 60 | 0 | 27 | 17 | 21 | 36 / 41 |
| S3 | 475 | 119 | 351 | 5 | 282 | 241 | 80 | 140 / 141 |

全 18 个 CPR run 有 2,552 次 source 阶段物理发送，包括 662 repeat 和 538 recovery；每 flow 每阶段至多一次，源发送总数不超过三次，每次 recovery 均在同 flow 的真实 repeat 之后。234 个 ACK 取消成功逐一关联 decoded ACK 接收，并找到保留的 canceled request 且无 TX。`cpr-cancel-check` 的其余检查不是成功取消，也不能把全协议 4,361 个 canceled requests 都算作 CPR ACK 取消收益。未做 noackcancel/norepeat/norecovery 消融，故这些是机制暴露与账本一致性，不能据此隔离各机制的性能贡献。

CPR 导出的通用 `route_cache_hits/misses` 在 18 run 全为 0，而 action/TX 明确显示已有确认路径的 routed 初发；本报告使用 action/ACK/物理路径证据，不把这些通用零计数解读为“没有热路由”。这是导出计数适用范围的限制。

**S2 的真实故障暴露。** 完整独立结果见 [secon2027_supervisor_pilot_v2_s2_details.md](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_pilot_v2_s2_details.md) 和 [secon2027_supervisor_pilot_v2_s2_details.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_pilot_v2_s2_details.json)。故障为 [80,160) s 在边 (7,8)、(12,13) 加 80 dB；移除两边的结构最短路由 4 变 6 hops，只是预算内候选图，不自动说明缓存或交付。每 run 窗口内实际 enqueue 依 seed 为 12/11/7，前窗为 12/9/17。全 24 S2 run 的 408 artifact hashes、9,943 TX、198,860 RX、453 accepted ACK 和 548 个逐跳物理 delivery chains 均一致。

CPR default 故障前 accepted ACK 为 10/6/6，覆盖端点对 4/3/2；窗口内初始完整 source DATA 真正跨故障边的 flow 为 **5/5/1**，11 条均能追溯至故障前同路径、同 generation 的 ACK/cache-update。指定故障边 DATA RX 失败为 8/9/2，窗口内实际 repeat 为 8/8/2、recovery 为 5/8/1。三 seed 共观察 **5 条“故障边指定失败→recovery→6-hop 首交付”链**；其中 seed2027001/flow13 交付成功却没有源 ACK，仍计入 delivery 而不计入 ACK。matched CPR 再现相同五条，不能据此声称十个独立实例。

全 24 S2 run 有 130 次故障边指定 DATA RX，全部失败（120 `prr_fail`、10 `capture_collision`）；另外的广播邻居接收机会单独记录。全协议/regime 的 77 个窗口内 6-hop 首交付不全是 CPR recovery。部分预热路径原已走 6-hop 外圈避开故障边；seed2027002 只有一条窗口初始跨边路径且没有满足上述完整恢复链的 flow。已有缓存、携带路径交集、实际故障边失败、recovery、delivery 与 ACK 都分别保留；不能因结构路径跨边就断言所有流被断路，也不把模拟器失败标签当成唯一因果归因。弱暴露 seed 没有被换掉。

**S3 压力和负结果。** 以下为 default CPR 三 seed 指定下一跳 RX 统计，包含 DATA 和 ACK；它衡量接收机会，不能当成独立 packet 或统计样本。

| 场景 | success | capture_collision | half_duplex | prr_fail |
| --- | ---: | ---: | ---: | ---: |
| S1 | 776 | 27 | 1 | 16 |
| S2 | 689 | 27 | 1 | 26 |
| S3 | 2477 | 471 | 129 | 36 |

S3 确有更多碰撞和半双工失败。源请求占位记录的排队补充见 [secon2027_supervisor_pilot_v2_source_pressure.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_pilot_v2_source_pressure.json)：S1/S2 的源 placeholder wait 全为 0；S3 三 seed 有正等待的请求为 15/9/16，最大等待 0.106244/0.109869/0.103125 s，均值（含零等待）0.002307/0.000956/0.002989 s。全 request 的 `queue_wait_s` 还包含协议有意 forwarding backoff，不能把其均值全说成射频拥塞排队。

**relay ledger capacity eviction 全为 0，但 source active-state capacity 并非零暴露。** S3 CPR seed2027000 有 5 条 `state-capacity-drop`（flows 91–95），均已 scheduled/registered、request=0、TX=0、无 delivery/ACK，仍保留在 N=160；matched 相同五条不是另五个独立负例。S3 每 regime 还有 11 个 stale-route protocol-no-start（逐 seed 3/6/2），其中 7 个是 recovery 决策（1/5/1）。修复后的批次真实经过该分支而没有 NameError。其 action 名 `DROP_DEADLINE_INFEASIBLE` 与 `reason=stale-route-generation` 存在语义不齐；本报告按 reason 分类，不把它错误计作 deadline infeasibility，也不隐藏无发送结果。

下表呈现全部 24 个 scenario/regime/protocol 组。N、ACK、delivery 是三个 seed 的计数总和；两项 PDR 是先求每 seed 的率、再对三个 seed 等权平均，**不是 pooled PDR**。airtime/TX 为每 run 的 seed 均值，airtime 覆盖该 run 全部物理包。数值仅是 n=3、已暴露 development seeds 的描述，未作正式推断或统计显著性主张；72 条精确行及失败列表在主 JSON。

| 场景 | regime | 实现 | ΣN | ΣACK | Σdelivery | mean ACK PDR | mean delivery PDR | mean airtime(s) | mean TX |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S1 | default | CPR | 103 | 80 | 92 | 77.71% | 89.52% | 38.926080 | 435.00 |
| S1 | default | legacy ME | 103 | 73 | 81 | 70.62% | 78.68% | 31.135744 | 390.67 |
| S1 | default | MT-like | 103 | 54 | 86 | 53.22% | 84.30% | 47.087104 | 514.00 |
| S1 | default | MC-like | 103 | 65 | 75 | 62.97% | 72.81% | 30.322176 | 399.33 |
| S1 | matched | CPR | 103 | 80 | 92 | 77.71% | 89.52% | 38.926080 | 435.00 |
| S1 | matched | legacy ME | 103 | 73 | 81 | 70.62% | 78.68% | 31.135744 | 390.67 |
| S1 | matched | MT-like | 103 | 44 | 85 | 43.11% | 82.70% | 47.712000 | 515.00 |
| S1 | matched | MC-like | 103 | 76 | 83 | 72.92% | 80.39% | 28.292779 | 365.33 |
| S2 | default | CPR | 103 | 67 | 77 | 64.97% | 74.66% | 42.870784 | 464.00 |
| S2 | default | legacy ME | 103 | 59 | 63 | 56.55% | 60.38% | 28.180053 | 351.67 |
| S2 | default | MT-like | 103 | 42 | 73 | 42.12% | 70.89% | 44.501419 | 480.33 |
| S2 | default | MC-like | 103 | 53 | 60 | 50.49% | 57.02% | 29.046613 | 376.67 |
| S2 | matched | CPR | 103 | 67 | 77 | 64.97% | 74.66% | 42.870784 | 464.00 |
| S2 | matched | legacy ME | 103 | 59 | 63 | 56.55% | 60.38% | 28.180053 | 351.67 |
| S2 | matched | MT-like | 103 | 46 | 71 | 45.63% | 69.66% | 45.752405 | 493.67 |
| S2 | matched | MC-like | 103 | 60 | 64 | 56.81% | 60.97% | 26.026411 | 332.33 |
| S3 | default | CPR | 475 | 156 | 281 | 32.62% | 59.12% | 211.926528 | 2191.33 |
| S3 | default | legacy ME | 475 | 179 | 201 | 37.69% | 42.28% | 95.758677 | 1084.00 |
| S3 | default | MT-like | 475 | 95 | 268 | 20.07% | 56.51% | 186.590464 | 1982.33 |
| S3 | default | MC-like | 475 | 202 | 224 | 42.72% | 47.35% | 85.279061 | 1021.33 |
| S3 | matched | CPR | 475 | 156 | 281 | 32.62% | 59.12% | 211.926528 | 2191.33 |
| S3 | matched | legacy ME | 475 | 179 | 201 | 37.69% | 42.28% | 95.758677 | 1084.00 |
| S3 | matched | MT-like | 475 | 97 | 254 | 20.55% | 53.47% | 186.440619 | 1977.00 |
| S3 | matched | MC-like | 475 | 171 | 204 | 36.13% | 43.03% | 87.328000 | 1005.00 |

S3 default CPR 的及时 ACK 为 **32.62%**，低于 legacy ME 的 **37.69%** 和 MC-like 的 **42.72%**；其平均 airtime **211.926528 s**，分别高于 **95.758677 s** 和 **85.279061 s**。matched 下 CPR ACK 也低于 MC-like 的 36.13%，且成本更高。CPR 的 S3 delivery 为 59.12%，高于这些比较对象，但“已交付而无源确认”不能与及时 ACK 合并成同一成功指标。S1/S2 有较高描述性 CPR reliability 的同时，也付出相对 legacy/MC 更高 airtime；没有据此宣称 Pareto/整体优势。

当前证据支持“该冻结 pilot 已完整运行且关键机制有实际暴露，范围内 raw 与指标一致”。仍未支持三项机制消融效果、正式统计结论、新鲜验证 cohort、真实固件/RF、deadline/cutoff 边界的本批暴露，或整体 SECON 验收。后续 development 决策应保留旧失败、S3 负结果和 S2 弱暴露，不能通过删 seed、混合 v1/v2 或重复 regime 扩大成功样本。
