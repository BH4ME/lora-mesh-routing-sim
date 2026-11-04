# MeshEcho-SR 新核心仿真 runner 审计

日期：2026-10-05

状态：只读审计记录。此次审计没有运行 494xx、47xxx 或 48xxx 种子，也没有修改论文、`VERSION` 或 GitHub。

## 审计范围

本记录核对了：

- 通用矩阵 runner：`tools/run_sr_experiment.py`；
- 当前 DCB 分阶段 runner：`tools/run_dcb_experiment.py`；
- 494xx 预期使用的同前缀诊断工具：`tools/diagnose_matched_d_trigger.py`；
- 事件、物理 TX、接收碰撞和截止时间的底层实现：`lora_mesh_sim.py`；
- 相关设计约束：`docs/research/meshecho_d_trigger_matched_branch_design.md`。

目标不是判断算法优劣，而是判断新核心仿真结果能否被第三方从归档证据重新计算。结论是：当前代码足以做开发前的诊断，但还不足以支撑新核心的冻结、ICC 结果或 holdout 声明。

## 已有能力

### 通用 runner

`run_sr_experiment.py:2026-2401` 已保存每个 seed/协议的流结果、动作日志和 deadline PDR；`run_sr_experiment.py:2404-2606` 会按 case/seed 配对，并拒绝 application trace、case hash 或 deadline 不一致的比较。`run_sr_experiment.py:2817-3008` 使用不可覆盖的 artifact 路径、源文件哈希和 artifact 哈希。

这能证明“各 arm 使用了相同的声明流量配置”，但默认通用 runner 不保存逐 TX 物理档案；它主要依赖聚合 metrics。

### DCB runner

`run_dcb_experiment.py:79-98` 将已提交物理 TX 与 request time 关联；`run_dcb_experiment.py:100-126` 可从已启动 TX 重算 queue wait；`run_dcb_experiment.py:1142-1182` 重算 TX ToA、windowed cost、queue wait 和 TX energy，并在 `run_dcb_experiment.py:1123-1125` 检查各 seed 的 paired trace。`run_dcb_experiment.py:967-1029` 保存 `runs/flows/actions/transmissions/tx_requests/state/paired` 及哈希清单。

这部分是可以复用的基础，但它的 `tx_requests.jsonl` 实际上只包含已经启动的 TX（`DcbRecordingSimulator.committed_tx_requests`），不能证明没有启动、被取消、被 guard 拒绝或在 run cutoff 后仍排队的 request。

### 494xx matched-D 工具

`tools/diagnose_matched_d_trigger.py:165-264` 记录了较完整的 target 前缀：源端状态、协议状态、事件队列、metrics、RNG 状态、节点/无线参数和 TX prefix；`400-495` 从同一 reference replay 打开 D/R/F 分支，并检查每个分支的 `prefix_match`；`553-593` 检查 target/arm 完整性；`596-664` 使用严格 smoke/exploratory seed 列表、源哈希和不可覆盖 artifact。

它还用角色/flow/link/attempt ordinal 组织 common-random-number 接收抽样（`130-140`），方向是对的。但这是 target-only 诊断，不是新在线核心的全策略 runner，且其证据面仍低于设计文档要求。

## 发现与严重性

### P1：request、physical start、no-start 没有闭合账本

`MatchedSimulator.schedule`（`tools/diagnose_matched_d_trigger.py:99-110`）只在内存中收集 `tx_requests`；`write_artifacts`（`596-664`）没有把它写入结果。`begin_transmission`（`112-128`）只记录失败调用，成功 request 没有 request id、request time 或 queue wait；`raw_physical_tx`（`467-472`）只有已启动 TX。因而无法区分：

- request 从未被处理；
- request 被取消；
- `can_start_at` 拒绝；
- request 已排队但 run cutoff 前未启动；
- request 启动后跨过应用 deadline。

DCB runner 只修复了“已启动 TX 的 request time”这一窄项，同样没有完整的 no-start 账本。

**最低改造：**在 simulator/recorder 层给每个 `transmit_later` request 分配稳定 `request_id`，保存 `requested_at`、event order、sender、flow、packet identity、guard/deadline；在处理时写入唯一终态 `started|canceled|guard_rejected|not_processed_by_cutoff`。对 `started` 必须保存 `tx_id/start/end/queue_wait_s`，并由审计器验证一对一 join、`start >= requested_at`、ToA 和 cutoff 分类。结果至少新增 `requests.jsonl`（或等价字段）及 no-start/deadline-censoring 汇总。

### P1：没有逐接收尝试的 collision/half-duplex/随机失败证据

底层 `Simulator.try_receive`（`lora_mesh_sim.py:1086-1122`）只更新 `rx_fail`/`collision_fail` 并返回 `None`；`MatchedSimulator` 只负责替换随机流（`130-140`），没有保存每个 `(tx_id, receiver)` 的尝试、干扰集合、半双工拒绝、capture 判定、SINR/PRR 或成功/失败原因。`raw_physical_tx` 加上一个聚合 `collision_fail` 数字不足以重算 target window 的碰撞差异，也不足以证明 ACK/反馈是物理接收而不是动作日志。

已有 `tools/diagnose_source_branches.py:69-120` 的 `collision_failures` 钩子可作为起点，但它只保存碰撞子集，不是完整的 receive-attempt ledger。

**最低改造：**保存 `rx_attempts.jsonl`（或每 run 嵌入同等档案），每条至少包含 `tx_id`、receiver、flow、role/attempt ordinal、TX start/end、结果原因（`self|half_duplex|capture_collision|prr_fail|success`）、干扰 TX ids、signal/SINR、是否在目标窗口。审计器应从该档案重算 `rx_success/rx_fail/collision_fail`、ACK 物理 decode 和按窗口计数；不得只接受动作日志中的 ACK 事件。

### P1：截止时间与队列证据仍不能覆盖 target 的所有情况

matched-D 的 `run_trace`（`425-486`）正确计算了 `[target enqueue, enqueue+30s]` 的 `network_window_airtime_s`，也保存了 full-run airtime；但它没有保存 target-flow 的 post-deadline TX、跨 cutoff TX、窗口内 `end > deadline` 的 censoring、late ACK/delivery 标志或未启动 request。`flow_record` 没有显式的 `deadline_at`，`accepted_ack_at`/`first_delivery_at` 也没有通过 artifact audit 重算。通用 runner 的 manifest 明确把所有 start 在 `[0,630]` 的网络 TX 纳入 cost（`run_sr_experiment.py:2850-2874`），因此它不能直接替代 target 的 per-flow deadline estimand。

**最低改造：**每条 flow/target 记录 `enqueued_at`、`deadline_at`、`ack_at`、`delivery_at`、`ack_by_deadline`、`delivery_by_deadline`、`late_ack`、`late_delivery`；每条 TX 记录 `before_deadline|post_deadline|post_cutoff` 和 `end_after_deadline`。分别报告 target-window、target-flow full-run、post-deadline spillover、network full-run、TX energy，以及声明 cutoff 后的 RX energy；审计器从 request/TX/flow 档案重算这些字段。

### P1：同前缀检查尚未达到“完整、可复核”的强度

当前 `run_trace` 会在内存中比较 reference 与每个分支的完整 `prefix` 字典（`420-424`），这是有价值的 fail-fast 检查；但落盘只有 `pre_app_prefix_sha256`，没有单独保存每个 arm 的 prefix payload 或 topology/pair-pool hash。`_normal(PendingSend)`（`31-40`）只留下 `canceled/committed/has_guard`，丢弃 request identity、guard 的可审计语义；`_prefix` 也没有显式保存 `reception_ordinals`、jitter ordinals、完整 event tie-order 记录。`run_trace` 重新 `sorted(..., key=lambda item: item[0])`（`406`），等时 app event 的 tie order 没有进入 `scheduled_trace` 元组。

此外，分支验证只检查 `source_tokens` 和 `last_discovery_at` 是否 equalized（`442-449`），没有检查完整 source ledger（`source_app_count/send_times/pending_discovery/route state`）是否按预声明规则一致。

**最低改造：**

1. 给 application event 保存稳定 ordinal，并将 `(time, ordinal, src, dst, flow_id)` 纳入 trace/hash；冻结 `tx_end -> protocol/app -> tx_request` 的同时间优先级。
2. 对每个 target 保存 reference prefix payload/hash、节点坐标/链路 shadowing hash、radio/config hash、事件队列和随机流/ordinal state；分支审计必须重算并逐项比较，而不是只信布尔值。
3. 明确定义 equalized post-decision ledger，至少覆盖 source token、discovery timestamp、send history、app count、pending discovery、route/feedback/recovery generations；审计器要求 D/R/F 和新核心控制臂在该字段集合上相等。
4. 将 prefix mismatch、request ledger mismatch、topology/trace mismatch 视为整个 target 无效，不把该 target 记为失败 outcome。

### P1：494xx 工具不是新核心的全策略 runner

`MatchedDCBProtocol` 固定继承 `MeshEchoDCB`（`143-163`），只允许 target-only `D/R/F` override；它没有注册新的在线 MeshEcho-SR 核心、same-wire no-change 控制、简单恢复控制或 development/holdout gate。`49400/49401--49440` 只是 draft exploratory cohort（`523-524`），manifest 没有 project gate，也没有 action/path divergence、paired endpoint noninferiority 或 cost margin 的预声明验证。

**最低改造：**在 `run_sr_experiment.py`/专用新 runner 中注册真正的新核心 protocol arm，并至少同时运行：旧 MeshEcho-SR/DCB reference、新核心、same-wire/no-change 控制、简单 F/R/D 或 recovery control。固定 development seed 列表、独立 holdout seed 列表、预算/截止时间和 exposure floor；只有在开发集通过预声明的 ACK、delivery、charged network cost 和实际物理 action/path divergence gates 后，才允许打开 holdout。494xx 诊断可保留为机制工具，不能充当全策略结果。

### P2：物理 ACK/feedback 的证据链不完整

matched-D 的 `flow.acked_at` 来自 simulator 的协议接收回调，但 `run_trace` 没有把成功 ACK 的 TX hop、receiver、`RxInfo` 或 request/flow/path identity 保存到 artifact。因而不能像 DCB runner 的 `_invalid_accepted_ack_count`（`765-838`）那样独立验证“accepted ACK 由正确物理链产生”。新核心如果依赖目的端反馈或 relay ACK，必须要求 accepted feedback 与 `rx_attempts` 的成功记录、ACK TX 路径、deadline 和 generation 一一对应。

### P2：结果清单缺少版本/运行时身份

matched-D `source_hashes`（`525-540`）和 DCB `input_hashes`（`192-203`）覆盖源文件、设计文档和测试，但都没有把根目录 `VERSION`、Git commit、Python 版本、依赖锁定信息和 artifact schema version 写进 manifest。当前 `VERSION` 为 `2.1.26`，但 494xx manifest 不会记录它，因此仅凭结果目录无法证明该结果对应哪个版本号。

**最低改造：**manifest 增加 `schema`、`sim_version`（读取 `VERSION`）、`git_revision`（若可得）、`python_version`、依赖/命令参数、protocol/core contract hash、seed split、case/radio/topology hash、prerequisite manifest hash、完整 artifact inventory（文件大小和 SHA-256）、记录计数和 `created_at`。将 `VERSION` 加入冻结 source/input hash；写入时禁止覆盖，审计时逐项重算。

### P2：拓扑与 pair-pool 只由 seed 间接推导

494xx traces 只保存 scheduled app tuples 和 trace hash（`487-495`,`635-638`），没有保存生成节点坐标、link shadowing、connected-multihop pair pool/筛选结果。相同 seed 在当前实现中应可重建，但第三方无法从结果目录独立确认拓扑输入没有被悄悄改变，尤其是新核心需要 holdout 复现时。

**最低改造：**每个 seed 保存 topology/pair-pool artifact 或其规范化 hash，并把 node generation、pair-selection RNG stream、pair list、traffic RNG stream 写入 manifest；审计器重建并比较。无 eligible target/无 exposure 的 seed 也必须留有一条 run record，不能只在 target 文件中出现。

### P2：schema 与计数清单不足以防止“部分成功”被误读

494xx manifest 有 `target_count/branch_count/evidence_count` 和四个 artifact hash，但没有声明每个 target 应有的 arm 集合、no-target seed 数、no-start/censored 计数、RX-attempt 计数或分支失败原因。冷 D 目标合法地缺少 R 臂（`563-580`），但顶层 `arms` 仍固定写成 `D/R/F`（`650-652`），容易在汇总时把冷目标的缺失 R 误读为 runner 丢失。

**最低改造：**manifest 明确 `arm_set_by_target`、cold/aging counts、zero-target seeds、invalid-target counts（必须为 0 才能出结果）、request/status/RX/TX record counts，以及 schema required fields；汇总器必须拒绝“部分 arm”或将其标为不可比较，而不是静默删行。

## 最小改造清单（按执行顺序）

以下是使“新核心算法仿真”达到可审计的最小闭环，不要求重写已有 PHY 或旧 baseline：

1. **核心 arm 接入。**实现并注册真正的新 `MeshEcho-SR` source/feedback/recovery controller；保留旧 SR/DCB、same-wire/no-change、简单 F/R/D 或 recovery controls。为每个 arm 写 source hash 和 contract hash。
2. **统一物理 recorder。**把 request ledger、started TX、no-start 终态和 queue wait 放进同一个 recorder；新旧 arm 使用同一 hook，不能只给候选 arm 加特殊日志。
3. **接收尝试 ledger。**逐 `(tx, receiver)` 保存成功/失败原因、collision/half-duplex/capture、干扰和 role/ordinal；由该 ledger 重算 aggregate RX/collision/ACK evidence。
4. **严格 paired input。**保存并校验带 tie ordinal 的 application trace、case/radio/topology/pair-pool hash、完整 event order；每个 seed 的所有 arm 必须一一对应。
5. **严格 prefix/ledger gate。**494xx target diagnostic 若继续使用，补齐 prefix mutable state、RNG/CRN ordinals、request queue 和 equalized source ledger；prefix mismatch 整个 target 作废。它仍不能替代全策略 runner。
6. **deadline/cost gate。**分离 target-window、per-flow post-deadline、post-cutoff、full-run TX/RX energy；保存 late/no-start/censored counts，并重算 ACK/delivery/ToA/energy。
7. **版本与清单。**manifest 写入 `VERSION`、Git revision、runtime/dependencies、contract/source hashes、seed split、prerequisite manifest、schema version、artifact inventory/counts；所有输出禁止覆盖并提供只读 audit CLI。
8. **阶段门。**只在 smoke（机械、非性能）通过后运行 development；development 预先冻结 gates 和参数，development manifest hash 作为 holdout 前置；holdout 完成后才改论文、VERSION、GitHub 或 EDAS。

## 结论

当前 494xx 工具的同前缀和 CRN 方向可以保留，但它的证据还不足以让新算法结果进入 ICC 论文。最小可接受路径是“复用 simulator/PHY 与旧 baseline，补齐统一 request/RX/deadline recorder，接入真正新核心的全策略矩阵，再用带版本和清单的 development/holdout runner 重算所有 primary metrics”。在上述 P1 项完成前，任何 494xx 数值都只能是探索性机制证据，不能作为中稿率或 ICC 中稿依据。

