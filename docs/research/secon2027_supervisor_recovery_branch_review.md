# SECON 2027：recovery stale-route 分支独立复核

日期：2026-11-04（Asia/Shanghai）。结论：**已独立复现旧源码的真实 `NameError: CprDecision`，并在修复源码上用同一确定性 fixture 验证关闭。** route 缺失、QUARANTINED、generation 改变和 route 到期四条拒绝路径均正确保留 `protocol-no-start` request，不新增 TX/airtime；READY 正向 recovery 仍工作。本结论只关闭这项分支异常及所列账本不变量，不代表 pilot、正式研究矩阵、P0/P1 或稿件整体完成。

未修改执行工作区，未重跑 pilot 或研究 seed。独立 fixture 使用仓库既有 `tests/test_secon_cpr_correctness.py` 的五节点、fixture seed **23** 构造，只直接调用初发、repeat、recovery 的 production 方法；强制将 `Simulator.run` 替换为报错函数，实际调用数为 **0**。因此它是定向状态/账本 fixture，不是新研究仿真、性能样本或随机 seed 扩展。未运行执行方另加的完整事件循环测试；只静态检查其测试内容，独立通过证据来自本报告附带 fixture。

## 真实失败及其不可变证据

失败计划：[development-pilot-v1.json](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/results/secon2027/plans/development-pilot-v1.json)，plan SHA-256=`3729b05d983845dda0ecca1804f1b4307c2e5869402656a5896ec32e91c1232f`，matrix SHA-256=`40ec39e456999ff749c594ad1ae19cb6dc7cfc4f15b5e81a2264ab2480122e28`，tested version=`2.1.28`，source snapshot=`b212b2f0e56920646581d2e2561247caf284d0815b5260c78cd404c5334fae81`。run 为 `S3-default / meshecho-cpr / seed 2027000`，run key=`79351a989e26b20a449f1d5522fa2303ad7b9ad2a181ecd5c58bc7c54a1a6577`，attempt=`attempt-001`。

[stderr.log](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/results/secon2027/runs/79351a989e26b20a449f1d5522fa2303ad7b9ad2a181ecd5c58bc7c54a1a6577/attempt-001/stderr.log) 记录的实际调用链（省略目录前缀）：

```text
secon2027_experiment.py:524 worker
→ run_cpr_experiment.py:607 run_matrix
→ run_cpr_experiment.py:439 run_one / sim.run(cutoff)
→ lora_mesh_sim.py:1456 run / begin_transmission
→ run_cpr_experiment.py:196 begin_transmission
→ lora_mesh_sim.py:1163 begin_transmission / protocol.on_tx_request
→ lora_mesh_sim.py:4000 on_tx_request / _cpr_start_recovery
→ lora_mesh_sim.py:4193 _cpr_start_recovery
  decision = CprDecision(...)
NameError: name 'CprDecision' is not defined
```

失败时间 `2026-11-04T08:35:46.068227+00:00`；外层 `failure.json` 的 kind=`scientific-or-worker`、status=`failed`，worker return code=1。该 attempt 保留 started、worker_runtime、stdout/stderr 和 failure；没有 completion，也没有 raw evidence 导出，不能把其部分执行当完整数据。检查 pilot-v1 的固定 72 keys 时，状态为 **48 completed、1 failed、23 unstarted**（S1/S2 四 case 各 12 completed，S3 未形成完整矩阵）。这是失败发生后的状态快照，不是后续计划状态。

| 失败证据文件 | SHA-256 |
| --- | --- |
| started.json | `0f641c5d4089ae9e9c40d78ae54135323b2979a563036b19520a1338d4b7c461` |
| stderr.log | `47452f236f4278332c5547af8565d57aebe981f0c4b9206ae27c556d093fdedf` |
| failure.json | `906680626e4be16645dbef0031c3a9f79393ff98fe24702a8ab2c12c6c9e9f61` |

## 修复内容与源码身份

比较旧冻结 snapshot 与修复工作区，`lora_mesh_sim.py` 的全部差异只有 import 列表新增一行 `CprDecision`；没有改变 route_valid 判定、recovery 预算、action reason 或计费逻辑。

| 文件 | 旧 SHA-256 | 新 SHA-256 |
| --- | --- | --- |
| lora_mesh_sim.py | `7c4fcef35eb91054df775f05ed07154f097d5e0b5ea798a6313983bbebcb86fb` | `e80beb763e3f63bccfc13d15a27275de432138f6774e56d3649c9f8bc43f4d01` |
| meshecho_cpr.py | `c7e24fdfdbbdf5b27d2da5dba7ced73ba6d8c2a3178d3197bb202b5409067d8e` | `c7e24fdfdbbdf5b27d2da5dba7ced73ba6d8c2a3178d3197bb202b5409067d8e` |
| meshecho_drc.py | `db1fca8012eb1225c7a77385d2b121be5c04c4bf99264e4ceec4b0acc907019e` | `db1fca8012eb1225c7a77385d2b121be5c04c4bf99264e4ceec4b0acc907019e` |

执行方另在 `tests/test_meshecho_cpr_controller.py` 添加 53 行 concurrent-timeout regression，检查 warmup ACK 后，旧流 timeout 隔离共享路线，新流 repeat 已启动但 recovery 必须拒绝；新测试文件 hash=`ed029a67a85bc1ecb88a8144054397a323a452b2b8e2d7e0e4fe3d2ee9f127fc`。本审查没有以执行方自报 green 代替独立 fixture 验证。

## 独立 red / green 结果

每个 case 从同一既有 fixture 开始：安装 `(0,4)` READY route，在 t=1 物理初发 DATA，在 t=2 物理 repeat DATA，在 t=3 请求 recovery。随后分别移除 route、调用既有 miss 转 QUARANTINED、安装新 generation 路线、将 route 设为恰在 t=3 到期；READY case 不改 route。四个负向 case 都已通过正常 recovery guard，命中目标 `route_valid=false` 分支，而非早期 return。

| case | 旧源码 | 修复后 request | 最终 physical TX | airtime (s) | recovery_started_at |
| --- | --- | --- | ---: | ---: | --- |
| missing | NameError | protocol-no-start | 2 | 0.195072 | 未开始 |
| quarantined | NameError | protocol-no-start | 2 | 0.195072 | 未开始 |
| new-generation | NameError | protocol-no-start | 2 | 0.195072 | 未开始 |
| expired | NameError | protocol-no-start | 2 | 0.195072 | 未开始 |
| ready | 正常 | started | 3 | 0.287488 | 3.0 |

旧源码四个负向 case 均抛相同 `NameError`，request 留在 scheduled，尚未形成正常拒绝。修复后独立断言包括：

- 原两条 TX 对象、TX count=2 和完整 airtime=0.195072 s 不变；recovery 的 pending 未 commit，`tx_id/end/ToA` 为空或未设，`recovery_started_at/recovery_route_epoch` 仍为空，无假 FLOOD 计费。
- 三条 request 全部保留；第三条为 `protocol-no-start`，`no_start_reason=protocol-hook`。flow 的 metric entry、无 ACK/无 delivery 的失败结果保留；source action 仍为 R_REPEAT，没有错误变为 F_RECOVERY。
- action event 确实记录 `reason=stale-route-generation`。随后直接处理 deadline 并 finalize request ledger，拒绝 request 的全部内容仍保持不变；policy active-flow 可退休，但 metric flow 仍保留在分母。
- new-generation case 在旧流 deadline 后仍保留新路线 `(0,2,4)`、READY 和 miss_streak=0，没有用旧流失败污染新缓存。
- READY 正向 case 仍只新增一次 FLOOD marker=2，记录 request started / TX id=3 / recovery_started_at=3.0。该对照排除了“总是拒绝所有 recovery”造成的伪通过。

独立脚本初次检查内存 request 的 `toa_s` 字段用了直接索引；非发送 request 在内存中并无此字段，导致审计脚本自身 `KeyError`。已改为 `.get()` 检查缺失/None，并用最终同一脚本重跑旧/新源码。此调整没有修改产品源码，也没有把该 schema 差异误报为产品缺陷。

## 口径与覆盖边界

当前拒绝 action 名仍为 **`DROP_DEADLINE_INFEASIBLE`**，但 reason 是 **`stale-route-generation`**；本 fixture 的 deadline 仍有余量，因此不能按 action 名称把这些拒绝统计成 deadline infeasible。报告/分析应按 reason 区分。request 的 `start` 是候选提交/判定时刻，即使非空也不等于物理开始；只有 status/tx_id 与 TX ledger 联结可决定是否收费。本次不擅改已有策略或 action 命名。

覆盖了目标分支四种 route-invalid 条件、请求到物理发送的拒绝传播、deadline 保留和 newer-generation 保护，以及 READY 正向对照。未重演真实研究流量、完整并发调度、RF/RX、ACK 到达竞争或所有 packet path；这组 fixture 不能说明新的 S3 pilot 会全部成功，更不能产生性能结论。旧失败记录和旧 snapshot 必须保留，修复后研究运行应使用新的 source/config/plan 身份，不能覆盖失败 attempt 或用新源码补写旧 snapshot 的结果。

证据：[fixture 脚本](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_recovery_branch_fixture.py)（SHA-256 `ded4534b90a60f4a4b995fa7c6e9d38f68541700726a8e69fcea8b9e42aa63f7`）、[旧源码结果及完整 traceback](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_recovery_branch_old.json)、[修复源码结果](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_recovery_branch_fixed.json)。
