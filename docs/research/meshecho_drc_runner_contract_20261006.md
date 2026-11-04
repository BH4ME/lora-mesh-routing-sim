# MeshEcho-DRC 实验 Runner 最小契约审计

日期：2026-10-06  
状态：只读审计；本次没有运行任何保留 seed，也没有修改 `VERSION`、论文、GitHub 或 EDAS。

## 结论

当前 `tools/run_sr_experiment.py` 可以复用为 DRC 的矩阵外壳，但不能直接
作为 DRC 的证据 runner。它已经能按 seed/protocol 保存 `runs.csv`、
`flows.jsonl`、`actions.jsonl`，检查 case/trace/deadline 配对，并写入源文件
哈希（`run_sr_experiment.py:2026-2401,2404-2606,2817-3008`）。但是 DRC
的关键决策发生在**实际物理 TX 开始前**，而现有底层接口没有把 request、
queue、no-start、逐接收失败原因和 ACK 物理来源闭合成可重算账本。因此，
在补齐以下契约前，不能把 `MeshEchoUGR` 或任何 DRC 原型结果写入 ICC 结果。

## 当前可复用接口与缺口

### 矩阵、deadline 和 paired 输入

- `run_matrix()` 接受 `case`、`protocols`、`seeds`、`deadline_s`，逐 seed/协议
  调用 `run_one_sr()`，最后调用 `summarize_paired()`。这适合作为 DRC 的
  外层 API。
- `run_one_sr()` 在 `sim.run(case.duration_s + deadline_s)` 后，从
  `metrics.flows` 生成 `deadline_at`、`ack_by_deadline`、
  `delivery_by_deadline` 和 late 标志（`run_sr_experiment.py:2111-2200`）。
  这些字段应保留，但必须由落盘的 request/TX/RX/ACK 记录独立重算，不能只
  信 metrics 或 action log。
- 当前 scheduled trace 是排序后的 `(time, src, dst, flow_id)`，没有稳定的
  application ordinal；同一时间的 app event 可能无法从 artifact 重建原始
  tie-order。DRC 必须使用 `(time, ordinal, src, dst, flow_id)`，并将其哈希
  写入 manifest。
- `summarize_paired()` 目前检查 case hash、scheduled trace hash、flow 数和
  deadline 相同，但不检查 topology/pair pool、radio 配置、event tie-order、
  request/RX schema 或完整 source state。因此这些哈希必须成为配对前置条件。

### 物理 TX request/start/no-start

底层调用链是 `Simulator.transmit_later()` -> `schedule("tx_request")` ->
`begin_transmission()`（`lora_mesh_sim.py:1022-1045`）。`PendingSend` 只有
`canceled`、`committed` 和可选 `can_start_at`（`lora_mesh_sim.py:377-382`）。
现有 `RecordingSimulator` 只在成功 start 后保存 `Transmission`
（`tools/run_sr_experiment.py:94-107`）；即使 `can_start_at` 拒绝，也没有
稳定 request identity 或拒绝原因。DCB runner 保存了已提交 TX 的
`request_time`，但仍没有完整的未启动请求记录（`tools/run_dcb_experiment.py:79-98`）。

DRC 必须在 simulator/recorder 层增加统一 request ledger，而不是给 DRC
单独打补丁。最小接口和字段如下：

```text
tx_request_id                 # simulator 单调递增、跨 arm 仅作本 run identity
requested_at, event_ordinal   # request 产生时间和稳定事件顺序
sender, flow_id, deadline_at
packet_kind, protocol, request_id, repair_index, path, path_index
action, route_generation, guard_generation
status                        # started | canceled | guard_rejected |
                              # not_processed_by_cutoff | state_capacity_drop
status_at, status_reason
tx_id, start, end, toa_s       # 仅 started 必须存在
queue_wait_s                  # started: start - requested_at
deadline_class                # before_deadline | post_deadline | no_start
cutoff_class                  # before_cutoff | post_cutoff
```

建议在 `transmit_later()` 分配 `tx_request_id` 并写 request；在
`begin_transmission()` 统一调用 `on_tx_start` 或 `on_tx_reject`。run drain
结束时，所有仍在事件队列中的 request 必须转为
`not_processed_by_cutoff`，不能静默消失。每个 `started` request 必须与一条
`Transmission` 一对一 join，并由审计器重算 `toa_s = end - start`、
`queue_wait_s` 和 packet ToA。`can_start_at` 的 false、显式取消、源端容量
不足和 deadline admission 失败必须是不同 reason，不能合并为“失败”。

### deadline、flow 和实际动作

每个 scheduled unicast 都必须进入 all-scheduled denominator，即使 DRC 因
容量或 deadline 不发包。flow record 最少增加：

```text
enqueued_at, deadline_at
initial_decision_at, initial_action, decision_reason
commit_at, initial_physical_start, initial_request_id
recovery_state, recovery_request_id, recovery_physical_start
accepted_ack_at, first_delivery_at
ack_by_deadline, delivery_by_deadline, late_ack, late_delivery
no_start_count, no_start_reasons[]
state_capacity_drop, deadline_infeasible
```

动作日志只能解释控制器的选择；真正的 `initial_action`/`recovery_state` 必须
能与 request status 和 physical TX join。一个在 deadline 前 request、但因
queue delay 在 deadline 后开始的 TX，要保留完整 airtime，并同时标成
`post_deadline`；不能把它从成本中删掉。结果至少分别报告：

1. 全网络窗口内（`start <= duration + deadline`）的完整 packet ToA；
2. 每个 flow 的 deadline 内 ACK/delivery；
3. post-deadline spillover、post-cutoff request 和 no-start 数；
4. 从同一 TX ledger 重算的 TX energy。

### ACK provenance 和 RX evidence

`Simulator.try_receive()` 当前只返回 `RxInfo` 或 `None`，并聚合更新
`rx_fail/collision_fail`（`lora_mesh_sim.py:1097-1133`）；这不足以证明一个
source ACK 是真实无线接收。DRC 的每个 `(tx_id, receiver)` 必须保存一条
`rx_attempt`：

```text
rx_attempt_id, tx_id, receiver, sender, flow_id, request_id
packet_kind, repair_index, path, path_index, start, end
signal_dbm, snr_db, sinr_db, interference_tx_ids
reason                         # success | half_duplex | capture_collision |
                               # prr_fail | self | invalid_path
decoded, in_deadline, role, attempt_ordinal
```

审计器应从该表重算 success/fail/collision、ACK hop failures 和窗口分类。
每一个被控制器接受的 ACK/feedback 还必须有独立的 provenance record：

```text
ack_event_id, flow_id, source, destination, ack_tx_id
ack_rx_attempt_id, reverse_path, reverse_hop, repair_index
ack_rx_at, deadline_at, route_generation, accepted, rejection_reason
```

`accepted == true` 只有在 `ack_rx_attempt_id` 对应 `reason=success`、接收者
是当前 source、ACK path/flow/request/generation 相符且 `ack_rx_at <= deadline_at`
时才成立。route commit 必须引用这条 accepted ACK；destination delivery
本身不能替代 source ACK。晚到 ACK、重复 ACK、旧 generation ACK 和没有物理
RX 对应的 action event 都必须保留并标为 rejected/late，而不是删除。

## DRC 矩阵和 paired seed manifest

DRC 不应复用现有 SR/MAG/LPR 常量后隐式出现。建议在 runner 中增加独立的
`DRC_PROTOCOLS` 和 `DRC_SPLITS`，最小矩阵固定为：

```text
meshecho-drc                  # 新核心
meshecho-drc-same-wire        # 同 wire、禁用 DRC 选择性分支的控制
meshecho-drc-fixed-f          # 同预算的简单 F recovery control
meshecho-sr                   # 原始 MeshEcho-SR reference
```

具体控制名称可以由核心设计最终冻结，但在 smoke 前必须固定 arm 顺序、wire
字段、max_hops、deadline、ACK guard、F budget 和 state cap。每个 split 应有
单独的、不与历史 4001--4040、470xx/480xx 等 cohort 重叠的 seed manifest：

```json
{
  "schema": "meshecho-drc-evidence-v1",
  "core_contract_sha256": "...",
  "source_sha256": {"lora_mesh_sim.py": "...", "tools/run_sr_experiment.py": "..."},
  "sim_version": "VERSION 内容",
  "git_revision": "commit 或明确 dirty 标记",
  "python_version": "...",
  "case_sha256": "...",
  "radio_sha256": "...",
  "topology_pair_pool_sha256_by_seed": {"seed": "..."},
  "application_trace_sha256_by_seed": {"seed": "..."},
  "application_trace_schema": "time+ordinal+src+dst+flow_id",
  "seed_split": "drc-development | drc-holdout",
  "seeds": ["预冻结整数列表"],
  "protocols": ["预冻结 arm 列表"],
  "deadline_s": 30.0,
  "prerequisite_manifest_sha256": "...",
  "artifacts": {"runs": {"sha256": "...", "records": 0}, "flows": {},
                "requests": {}, "transmissions": {}, "rx_attempts": {},
                "acks": {}, "actions": {}, "paired": {}},
  "counts": {"scheduled_flows": 0, "no_start": 0, "deadline_censored": 0,
             "rx_attempts": 0, "accepted_acks": 0, "invalid_records": 0},
  "gates": {"mechanical_smoke": false, "development": false, "holdout": false}
}
```

开发集 manifest 必须在 holdout 前通过只读审计，并以完整 manifest hash 作为
holdout 的 prerequisite；holdout runner 拒绝任何 source/core/case/radio/
trace/schema 变化。每个 seed 每个 arm 必须恰好一行 run、一套 flow/request/
TX/RX/ACK/action records；缺 arm、零目标 seed、invalid record、prefix/hash
不一致都应 fail closed，而不是从汇总中静默删掉。

## 建议的最小实施顺序

1. 先在 simulator 加 request、TX start/no-start 和 RX-attempt recorder，写
   RED tests 验证取消、guard reject、queue wait、same-time deadline。
2. 在不跑保留 seed 的情况下，把 DRC 和四 arm 适配到 `run_matrix()`；让
   `write_artifacts()` 写 requests/transmissions/rx_attempts/acks 及新 manifest，
   再写独立 audit 函数逐项重算。
3. 用一个新的机械 smoke seed 验证 schema、paired trace、物理 TX/ACK join，
   只检查证据闭合，不看性能决定参数。
4. 冻结 development/holdout seed、控制和 gates；development 通过后才可打开
   untouched holdout。两阶段都通过后，才允许按真实结果大改 ICC 论文、版本号
   或发布 GitHub。

## 不应作出的结论

当前 UGR 注册（`lora_mesh_sim.py:74-79,7412-7420`）和普通 SR runner 的
`flows/actions` 落盘，不等于 DRC 已接入，也不等于 ACK provenance 或 no-start
证据已闭合。本审计没有运行仿真，不能支持中稿率、算法优势、硬件验证或 ICC
投稿结论。
