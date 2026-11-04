# SECON runner 独立审查（进行中）

日期：2026-11-04。执行工作区：`/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo`。

只读审查了正在开发的 `tools/secon2027_experiment.py`，SHA-256 `716addfc6a943c2e355aebb535205c8791f37a1cd0bb88f9c9b313e698855a0f`。该文件仍在实现，以下是此快照中的反例，不代表最终代码状态。没有运行研究仿真，没有消耗新 seed，没有编辑执行工作区。

## 必须修复：完成记录没有绑定对应的计划 run

`audit_plan()` 遍历冻结计划的每个 run key，但对找到的 completion 只比较 `source_snapshot` 和 `plan_sha256`，没有比较记录的 `run_key` 与该目录/计划的 `spec["run_key"]`。同一计划各协议共享 snapshot/plan，所以 A 的 completion 放入 B 的目录，也会计为 B 完成。`execute_one()` 的 existing-completion 返回路径同样只调用 `audit_attempt()`，未绑定当前 spec。

`audit_attempt()` 仅遍历 completion 自报的 `files`，没有要求必需的 flow/action/request/TX/RX/ACK/manifest/started/worker audit 等证据集合。`files={}` 的 completed 记录会通过；这不能支撑任务书 B08/G09/J04 的完整证据结论。

已执行一个纯临时目录、无仿真的反例：

1. 构造两个已计划 run key，`arm-A-key` 与 `arm-B-key`，共同 snapshot/plan hash。
2. 在两者的 `attempt-001/completion.json` 中放同一份 A 的记录（`run_key=arm-A-key`），且 `files={}`，没有任何原始事件文件。
3. 在测试中将 `verify_plan` 替换为返回该已验证计划，只隔离被测 `audit_plan` 的后置绑定逻辑；不声称这是完整 CLI 集成测试。
4. 调用 `audit_plan()`，实测返回 `status=complete`，`completed=2`。审查前后源文件 SHA 相同。

修复应同时覆盖：expected run key/seed/arm/case/config/source/plan 的一致性；started spec、completion 和原始 manifest/row 的关联；必需文件集合及其 hash；恢复已完成 run 时也使用同样校验。以“交换两组真实完成包”“删掉必需证据/置空清单”的回归测试证明拒绝，而不是只给 JSON 增加字段。

## 后续待核验（尚不判定为已复现缺陷）

- 执行中断后遗留的 `.lock` 和 started-only attempt 的恢复途径，应先核对真实 PID/进程状态，再保留失败记录并按显式基础设施重试规则恢复；不能仅删除锁或静默重跑。
- 验证 gate 和冻结计划的身份/源码/配置绑定，以及冻结后拒绝额外 arm/config，需以集成负向测试核验。
- 最终验收还需读取原始事件重算指标；当前完成标记或其内嵌审计摘要不能独立证明全部协议事件正确。
