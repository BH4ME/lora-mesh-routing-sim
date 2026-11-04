# Pilot v2 S2：独立 raw 机制暴露审计

日期：2026-11-04。**S2 全部 24/24 run 已完成；本次独立联结未发现范围内的不一致。S2 已有真实的预热路径故障交集、故障边失败、repeat/recovery 和 6-hop 绕行交付证据；暴露强度在 seeds、端点与协议之间不同。** 这只是 development 场景与证据核验，不是性能优势、RF 或完整项目验收。

本次不调用现成 analyzer/audit 器，不导入或运行模拟器、测试、研究 seed 或 RNG，不重跑任何 run，不改执行工作区。只读取完成后的 raw，并在 canonical docs 中保存审计脚本、JSON 与本报告。报告主张针对本次冻结对象，不跟随执行线程的后续修改。

## 身份与范围

- 执行仓库：`/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo`。
- 计划：`results/secon2027/plans/development-pilot-v2.json`。
- plan 文件 SHA-256：`cf30790288c060f93302eeefc5a9e3535533d2ada9d02d2ded80bd6768c0aff0`。
- canonical plan_sha256：`0c49a69a5c3725c9f72ff2e28ed870d10db1df7eec4319f6397097b84a2c85e7`。
- 源 snapshot：`ee890e25030782fc01208ee4ce1f20863c6ade5322ac954ad67ae48b594056a2`；tested version：`2.1.28`。
- development seeds：2027000、2027001、2027002。S2-default 与 S2-matched 各 4 个模型 × 3 seeds，共 24 run；各只有 attempt-001 completion。
- 24 completion 的身份和 408 个列出的 artifact hash 已核对。独立重建 9,943 TX→request、198,860 RX→TX、453 accepted ACK→源 RX/TX，以及 824 flow 的最早交付；其中 548 条已交付 flow 的每个路径 hop 均能由时序一致的 decoded RX 链支持。134 条 CPR accepted ACK 同时与 cache-update action 一致。没有以 action request 计数替代 physical repeat/recovery。

[原始逐 flow 审计 JSON](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_pilot_v2_s2_details.json)（SHA-256 `036ad608dea03902bd8a4e85860dfe26fbaf6ddb40ace582ae2667e170d66f74`）与[审计脚本](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_pilot_v2_s2_details.py)（SHA-256 `004642d2c6ff541f83d25f09db0b4e5614000e709b7bf21491390c67711678e1`）保留完整 run key、completion hash、ACK/cache path、故障 TX/RX ID 和每跳交付链。

## S2 场景到底暴露了什么

故障窗口为 **[80,160) s**，边 (7,8)、(12,13) 增加 80 dB 衰减。独立按声明的 5×4 网格做无随机 BFS：四个端点对在故障前均为 4 hops，移除两边后的最短路径均为 6 hops，等于配置的 hop budget。结构存在绕行只说明候选图，不保证路由缓存、物理传播或交付。

已存 identities 的完整 application trace、nodes、radio、common environment 与 static shadowing，逐 seed 在 8 个 S2 arm/regime 组合中一致。每 run 的 N 按 seed 为 **36、28、39**；故障前 enqueue 数为 **12、9、17**，窗口内 enqueue 数为 **12、11、7**。这些是实际 raw 中的业务，不是从 rate 参数推测。全批共 824 个 run-flow 记录，其中 240 个在故障窗口内入队，285 个生命周期与窗口有正长度交集；同一 seed 跨 arm/regime 重复出现，不能把它们作为 824 个独立样本。

全批窗口内初始 source DATA 携带完整路由的 flow 为 159，其中 **122 条携带路径跨故障边**，119 条还能在故障前找到相同端点与相同路径的 accepted ACK。存在完整路径交集仍不代表该包真的到达故障边：可能在更早 hop 失败。另行按指定下一跳联结物理 TX/RX 后，共观察 **130 次故障边 designated RX，全部失败**，均为 DATA（120 `prr_fail`，10 `capture_collision`）；另有 290 次 flood/broadcast 在故障边两端的邻居接收机会，全部失败，未冒称指定转发。这些原因标签是模拟器记录，不是“80 dB 是唯一失败原因”的反事实因果证明。

**CPR 的缓存确认链更强，但并不均匀。** 仅计 S2-default 三个 seed，故障前分别 10/6/6 个 accepted ACK，覆盖 4/3/2 个端点对。故障窗口内初始 DATA 全路径跨故障边的 flow 分别 **5/5/1**；全部 11 条都能向前联结到故障前同路径、同 route generation 的 accepted ACK/cache-update action。各 seed 故障边指定 DATA RX 失败分别 8/9/2 次；窗口内实际 source repeat 为 8/8/2，recovery FLOOD 为 5/8/1。matched CPR 同有效参数的三份独立 run 得到相同计数；下述汇总不把它们当额外独立 evidence。

对于 ME/MC，accepted ACK 可证明该路径此前完成过，随后 source DATA 的完整路径可证明实际复用；raw 没有 CPR 式完整 cache-install action，因此不从 ACK 单独断言某一时刻的全部 cache 状态。MT-like 每流 DATA managed flood，没有可复用 source-route cache；它的故障前 ACK 路径只能叫成功路径，不能称“预热缓存”。

## 全部 run 的范围计数

`前 ACK`=80 s 前 accepted ACK 数；`初始跨边`=source 初始完整 DATA 的 start 在 [80,160) 且路径含故障边；`指定失败`=故障边指定下一跳 RX 失败；repeat/recovery 均为 source 实际物理发送且 start 在窗口内；`6-hop`=首交付在窗口内、完整路径 6 hops 且避开两故障边；`链条`=同 flow 观察到故障边指定失败，之后 marker=2 recovery 路径首次交付。最后一列不要求源端最终收到 ACK，ACK 和 delivery 仍分开记录。

| regime | 模型 | seed | N | 窗口入队 | 前 ACK | 初始跨边 | 指定失败 | repeat / recovery | 6-hop | 链条 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default | CPR | 2027000 | 36 | 12 | 10 | 5 | 8 | 8 / 5 | 7 | 1 |
| default | CPR | 2027001 | 28 | 11 | 6 | 5 | 9 | 8 / 8 | 6 | 4 |
| default | CPR | 2027002 | 39 | 7 | 6 | 1 | 2 | 2 / 1 | 3 | 0 |
| default | ME | 2027000 | 36 | 12 | 10 | 12 | 11 | 0 / 0 | 0 | 0 |
| default | ME | 2027001 | 28 | 11 | 8 | 11 | 10 | 0 / 0 | 0 | 0 |
| default | ME | 2027002 | 39 | 7 | 7 | 4 | 4 | 0 / 0 | 3 | 0 |
| default | MT-like | 2027000 | 36 | 12 | 6 | 0 | 0 | 0 / 0 | 5 | 0 |
| default | MT-like | 2027001 | 28 | 11 | 5 | 0 | 0 | 0 / 0 | 6 | 0 |
| default | MT-like | 2027002 | 39 | 7 | 6 | 0 | 0 | 0 / 0 | 2 | 0 |
| default | MC-like | 2027000 | 36 | 12 | 9 | 9 | 8 | 0 / 0 | 2 | 0 |
| default | MC-like | 2027001 | 28 | 11 | 5 | 11 | 10 | 0 / 0 | 0 | 0 |
| default | MC-like | 2027002 | 39 | 7 | 5 | 2 | 2 | 0 / 0 | 2 | 0 |
| matched | CPR | 2027000 | 36 | 12 | 10 | 5 | 8 | 8 / 5 | 7 | 1 |
| matched | CPR | 2027001 | 28 | 11 | 6 | 5 | 9 | 8 / 8 | 6 | 4 |
| matched | CPR | 2027002 | 39 | 7 | 6 | 1 | 2 | 2 / 1 | 3 | 0 |
| matched | ME | 2027000 | 36 | 12 | 10 | 12 | 11 | 0 / 0 | 0 | 0 |
| matched | ME | 2027001 | 28 | 11 | 8 | 11 | 10 | 0 / 0 | 0 | 0 |
| matched | ME | 2027002 | 39 | 7 | 7 | 4 | 4 | 0 / 0 | 3 | 0 |
| matched | MT-like | 2027000 | 36 | 12 | 6 | 0 | 0 | 0 / 0 | 6 | 0 |
| matched | MT-like | 2027001 | 28 | 11 | 3 | 0 | 0 | 0 / 0 | 8 | 0 |
| matched | MT-like | 2027002 | 39 | 7 | 5 | 0 | 0 | 0 / 0 | 1 | 0 |
| matched | MC-like | 2027000 | 36 | 12 | 7 | 9 | 8 | 0 / 0 | 3 | 0 |
| matched | MC-like | 2027001 | 28 | 11 | 6 | 11 | 10 | 0 / 0 | 0 | 0 |
| matched | MC-like | 2027002 | 39 | 7 | 8 | 4 | 4 | 0 / 0 | 4 | 0 |

CPR 的 default 三 seeds 共 16 个窗口内 6-hop 首交付，其中 **5 条 flow** 有“实际故障边失败→recovery→6-hop 首交付”的完整可观察链；同有效参数 matched CPR 重复观察到这 5 条，因此全 24 run 计数为 10。其余 6-hop 交付可能来自初始 flood、既有 6-hop 绕行缓存或没有实际触达故障边的 routed failure，不能全部算故障恢复成功。全协议/regime 合计 77 个窗口内 6-hop 首交付也不是 CPR 恢复次数。

## 五条 CPR default 可追溯实例

| seed | flow | 初始已确认路径 | 故障边失败 TX IDs | repeat / recovery source TX IDs | 首交付路径 | 交付时间(s) | ACK 时间(s) |
| --- | ---: | --- | --- | --- | --- | ---: | --- |
| 2027000 | 13 | 5→6→7→8→9 | 165 | [166] / [167] | 5→0→1→2→3→8→9 | 88.402658 | 88.803554 |
| 2027001 | 11 | 10→11→12→13→14 | 119, 123 | [121] / [125] | 10→11→12→17→18→19→14 | 105.510360 | 105.911256 |
| 2027001 | 13 | 5→6→7→8→9 | 157, 160 | [158] / [161] | 5→6→7→2→3→8→9 | 123.794360 | 无 ACK（保留） |
| 2027001 | 14 | 9→8→7→6→5 | 167 | [171] / [174] | 9→4→3→2→1→0→5 | 127.090007 | 127.490903 |
| 2027001 | 17 | 5→6→7→8→9 | 225, 232 | [230] / [235] | 5→6→7→2→3→4→9 | 142.182360 | 142.583256 |

例如 seed2027000/flow13：先前 flow5、9 的 ACK 确认 generation2 路径 5→6→7→8→9；81.704474 s 初始 source DATA TX163，故障边 7→8 的 TX165/RX3289 在 81.909786 s 失败；source repeat TX166，recovery TX167；6-hop 路径 5→0→1→2→3→8→9 的最终 TX177/RX3530 在 88.402658 s 完成交付，88.803554 s 源接受 ACK。JSON 还保存这条交付的全部六个 TX/RX hop。

反例也保留：seed2027001/flow13 在 123.794360 s 经 recovery 6-hop 成功交付，但没有 accepted ACK；不能把它合并成源端确认成功。seed2027002 只有 1 条窗口内初始完整 DATA 跨故障边，虽有 3 条 6-hop 首交付，却没有满足上述完整故障边失败→recovery 首交付链的 flow。该弱暴露 seed 保留，不能用更有利 seed 替换。

## 限制与结论边界

预热路径可能已绕开故障边。例如 CPR/seed2027000 的第一个 ACK 路径是 5→6→1→2→3→4→9；第一个 10→14 ACK 路径也是 6-hop 下外圈。后来部分路径改为跨边 4-hop，所以既不能因最初绕行就断言 S2 没有效，也不能因配置直线路径跨边就把所有流标为有效故障暴露。

本次没有重算 PHY、反事实无故障结果或重新验证每条 cache 状态机转换。结构 BFS、完整携带路径交集、真正故障边指定 RX、source recovery、destination delivery、source ACK 是不同层证据，报告与 JSON 分别保留。S2 的关键机制在这批 development raw 中确有实际暴露，暴露不足/失败/无 ACK 的流同样保留；不得据此宣称统计显著优势、正式验证完成、真实固件/RF 或整体 SECON 交付完成。
