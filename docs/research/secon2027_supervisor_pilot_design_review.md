# SECON 2027 development pilot：独立设计审查

日期：2026-11-04（Asia/Shanghai）。结论：**当前 72-run pilot 的静态配置与场景实现未发现阻断性错误；可作为 development 诊断设计，不构成场景实际暴露、消融效果或正式性能的验收。** S1/S3 有正确的负载差异，S2 的预定故障与端点最短路径存在交集且保留预算内绕行。实际预热成功、缓存路径穿越故障、repeat/recovery 与高争用是否发生，须待合法冻结后的 pilot raw 证据确认。

审查对象为执行仓库 `/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo` 的 `configs/secon2027/development_pilot.json` 与相关生产源码。该配置仍是 development 草案；本次查看计划目录只有 smoke v1/v2/v3，没有该 pilot 的 frozen plan。执行线程仍在工作，因此以下 SHA-256 标识本次读到的内容，不替代后续冻结 snapshot。本审查没有运行模拟器、测试、RNG、application trace 生成或任何 seed；只做 JSON 解析、源码阅读、确定性图搜索和数值代数，不修改执行区。另有子代理独立检查身份和参数映射，结论一致。

## 场景设计检查

| 项目 | S1 | S2 | S3 |
| --- | --- | --- | --- |
| generation / drain | 240 s / 30 s | 240 s / 30 s | 240 s / 30 s |
| application deadline | 30 s | 30 s | 30 s |
| schedule | 首条固定于 1 s，后续指数间隔 | 同 S1 | 同 S1 |
| 总 offered rate | 8 flows/min | 8 flows/min | 40 flows/min |
| 理论期望 scheduled N | 32.8667 | 32.8667 | 160.3333 |
| 公共拓扑 | 20-node、5×4 grid、1 km 间距 | 同 S1 | 同 S1 |
| 预定故障 | 无 | [80,160) s，对 (7,8)、(12,13) 加 80 dB | 无 |
| structural shortest hops | 四端点对均 4 | 故障前/后 4，故障期 6 | 四端点对均 4 |

所有 case 都是 `pair_schedule="poisson"`，不是 fixed-once。`tools/run_drc_experiment.py:252` 的实际实现为一个总到达流，`mean_interval=60/rate_per_min`，端点对按 round robin 分配；因此 8/40 是全网络总速率，不是每对独立 8/40。每对的间隔是四个全局指数间隔之和，不能把它写成四个相互独立的 Poisson 过程。首条固定在 1 s，所以期望 N 为 `1+(240−1)×rate/60`；这仅为解析期望，没有生成本次三 seed 的真实 trace。

S1 与 S3 除 case key 和 rate 外，其余 case/env/deadline 完全相同；S3 的可变到达速率确为 S1 的 5 倍。实现的指数间隔参数真正读取这个 rate，不存在仅改标签而仍固定四条流的缺陷。但“负载提高”不自动等于“已出现高争用/容量溢出”；需要 raw RX collision、排队/no-start、取消、ledger eviction 等输出证实。若 eviction 为 0，应如实保留 0，不能据此声称验证了容量压力。

S1 使用固定端点 5↔9、10↔14；图最短距离为四条 neighbor edges。共同损耗对 neighbor 加 20 dB、nonneighbor 加 80 dB，并非在接近完美的一跳网络上改变 hop-limit 标签。以无阴影/衰落的中心点代数检查，1 km neighbor 接收功率约 −117.17 dBm、4 km 端点直连约 −193.73 dBm（相同 17 dBm TX、915 MHz、path-loss exponent 2.75）；这解释了有意构造的多跳条件，不是 RF 标定或实测可达性证明。静态图也不是 PHY 的硬删除图：radio 仍使用概率接收，实际 hop 分布必须从完成的 DATA/RX 或 ACK 路径提取。

## S2：预热、失效交集与替代路径

配置 `[80,160)` 位于 240 s generation 中部，前后各约 80 s 都有正常 offered traffic。按总 Poisson 参数，故障前 [1,80) 的理论 offered 数期望为 11.5333（含首条），故障期 [80,160) 为 10.6667，恢复后 [160,240) 为 10.6667；四 endpoint pairs 循环发送，所以有重复业务和缓存建立的机会。缓存 TTL 为 300/600 s，长度本身不会令 80 s 之前刚建立的路线在故障开始时自然过期。

独立按配置生成无随机性的 5×4 邻接图并做 BFS，结果如下。列出的路径是图论示例，**不是预言模拟器会选中的预热路线**。

| 端点 | 故障前唯一 4-hop 最短路径 | 交叉故障边 | 故障期可用 6-hop 示例 |
| --- | --- | --- | --- |
| 5→9 | 5–6–7–8–9 | 7–8 | 5–0–1–2–3–4–9 |
| 9→5 | 9–8–7–6–5 | 7–8 | 9–4–3–2–1–0–5 |
| 10→14 | 10–11–12–13–14 | 12–13 | 10–11–12–17–18–13–14 |
| 14→10 | 14–13–12–11–10 | 12–13 | 14–13–18–17–12–11–10 |

两条故障边均为合法 neighbor edges；移除它们不会把四个端点对断开，绕行长度恰好等于 `CprCase.max_hops=6`。`attenuation_db()` 在半开时间区间对这两条无向边追加 80 dB；其他边不受这项故障影响。`shortest_hops()` 用 ≥60 dB 故障作为结构删除阈值，因此上述结构结果与设计口径一致。具体 packet 的干扰、衰落、排队和 deadline 仍可能使这条结构替代路径不可用，不能把 6≤max_hops 当作成功恢复证明。

**S2 目前没有确定性的预热流段或预装缓存，也没有保证每对在 80 s 前得到 source ACK。** 普通业务提供预热机会，初始发现可能失败，也可能学到已避开故障边的 6-hop 路线。此点是设计暴露边界，不是“缺少正式数据所以代码有 bug”。若执行方称该配置已保证“暖缓存路径被切断”，该表述应改为“预定故障候选，实际失效交集待 pilot 诊断”。不能按将来的好坏结果挑 seed 或换故障边来掩盖零暴露；任何 development 修订应另行记录/冻结。

现有 analyzer 分别输出 fault-period enqueued、active、初发早于故障窗口的 active flow、以及初始源 DATA carried path 与当时 active fault 的交集。这是恰当的口径区分；前两类不能替代后一类。其 `source_path_fault_edges` 检查仅覆盖**初始源 DATA 发送时刻**；跨故障边但初发在 80 s 之前、之后才在中途遇到故障的流不会进入该窄字段。它已有宽时间重叠字段，故这不是字段实现与文档不一致；要声称实际边故障造成 DATA/ACK 失败，还应联结故障时刻的指定下一跳 TX/RX，而非只用最早源 TX 的静态全路径。没有这种证据时只能报告 exposure/overlap。

**结构最短路径与故障边相交，不等于运行时已经缓存的实际路径与故障边相交。** pilot 后应逐端点/seed 统计故障前最后一条有效缓存路径及其确认 ACK/有效期，检查该路径是否包含故障边；再统计故障期间 scheduled/active 流、destination delivery 与 source ACK、实际开始的 repeat/recovery、实际绕行路径及其 hops。没有缓存、缓存已失效、原路已避开故障、零交付或无可用绕行均应保留为零/失败/对应分类，不能从矩阵或分母删除。

S1 与 S2 的 traffic/PHY/environment 除 fault schedule 与标签完全相同，且独立业务 RNG 不读取 protocol 或 case key；这有利于同 seed 对照。公共 temporal fading 为 2 dB、60 s block，在 60/120/180 s 改变，S2 故障则在 80/160 s 切换。不能把所有故障期间的接收失败都因果归于人为故障；同 seed S1 是必要的描述性参照。

## seed、default/matched 与消融身份

配置 stage 明确为 `development`，cohort 为 `secon2027-development-v1`，只包含已用于 smoke 的 2027000、2027001、2027002。registry purpose 为 development，cohort/三 seed state 均 exposed，首次运行记录为 `2026-11-04T07:47:24.226591+00:00`。重复使用没有将它们变成新鲜 validation；analysis seed 20271104 仅用于重采样，也不是新增 simulator seed。

矩阵有 **8 个 arm ID、4 个 protocol 实现、6 个 case**；每 case 指定四 arms，故共 `6×4×3=72` run，不是 6×8×3。default 与 matched 两个 case 的公共输入相同、key 不同；run key 绑定完整 matrix hash、snapshot、case_id、arm_id、seed。worker 按基础 protocol 构建实例并传入相应 parameters，runner 在构造 simulator 前逐项验证、设置属性并导出 resolved parameters。没有发现参数被静默忽略或不同 regime 串列。

| 模型 | default → matched 的真实变化 |
| --- | --- |
| MeshEcho-CPR | TTL 600、base 0.45、jitter 0.65 已相同；有效配置不变 |
| legacy MeshEcho | TTL 600、base 0.45、jitter 0.65 已相同；有效配置不变 |
| Meshtastic-like | base 0.75→0.45、jitter 0.75→0.65 |
| MeshCore-like | TTL 300→600、base 0.5→0.45、jitter 0.7→0.65 |

matching 保留机制身份、SNR 延迟函数、discovery policy 和 ACK 语义，不能把 base/jitter 相等说成所有 forwarding delay 或真实固件都相等。CPR/legacy 两个 regime 的重复有效配置是明示设计，不是新的独立样本；当前矩阵仍计划物理跑满 72 次，没有把它们隐式 alias。以后若节省重复运行，应按合同建立 hash-checked alias，不能直接漏掉 key。

raw `protocol` 仍为基础实现名称（例如 matched 的 raw 仍写 `meshecho-cpr`），regime/arm_id 要从 frozen spec 联结；analyzer 当前按 plan/case/arm 分组并补入 configuration，做法正确。不得把不同 case 的 raw CSV 只按 protocol 拼接后误称为一个实验。

**此 72-run pilot 没有 noackcancel、norepeat、norecovery arms。** 这与合同预定的四模型 default/matched 72-run pilot 一致，不是漏跑已声明 pilot 消融。但 smoke 中 repeat/recovery 尚未暴露，所以不能把 smoke 加本 pilot 称作已完成三项消融效果验证。正式矩阵前应明确三项消融的 case/seed/参数和 skip-repeat 时间预算；`-matched` 是参数匹配对照，不是这些机制消融。

## 实际发现与继续门槛

本次没有确认的代码或数值配置阻断项。需保留的限制是：S2 只有预热机会、没有已保证的暖路径故障；S3 只有更高 offered rate、没有已观察的高争用；pilot 本身不含三项机制消融。这些不能被包装成已通过的机制验收，也不能因尚无结果而记为模拟器 bug。

合法冻结后的 pilot 应保留所有预定 72 keys 及失败/零暴露，报告 S1 的冷/热路线选择及实际 hop 分布、S2 的故障期间业务与**实际缓存路线/故障边交集**和预算内替代路径、S3 的碰撞/排队/取消/容量暴露。若指标为零或场景暴露不足，应直接标出；是否修订 development 场景属于后续记录化研究决策。它仍不能取代正式 cohort、方法与矩阵冻结、正式推断、RF 验证、全部 P0/P1 或九页匿名投稿稿的独立验收。

## 本次读取内容的哈希

| 文件（执行仓库相对路径） | SHA-256 |
| --- | --- |
| `configs/secon2027/development_pilot.json` | `8e91e49204b33cff34c77bd1fc1620e8fc1ee10b4fcc32d2227a199a21cedd2e` |
| `configs/secon2027/seed_registry.json` | `4eaee1c7f296734dd74664eeff257a67c072ab6fd00f926933ce95e1c2598ae3` |
| `tools/secon2027_scenarios.py` | `d83ebbf9f57a448c220a32f452f3e6e9bffe4a40580acd6f6e11909ddc25d061` |
| `tools/run_drc_experiment.py` | `e1ac79e951f1aeca9b85cee9c893d513e05b5c9600f2dd3c9eef29d078810d8f` |
| `tools/run_cpr_experiment.py` | `d43dcfa30eda47af2a40e99f429f21b5815c6fac97d6e90d161a37b63b96019f` |
| `tools/secon2027_experiment.py` | `6908c859bade6aec9aebf8f9231c76ae5aebdd347d9791d3ddda47f5ceebbb51` |
| `tools/analyze_secon2027.py` | `7fd757a780e9725bd3d1992790eaad4a6cc3be7b48f7adcce674a729990eeb54` |
| `lora_mesh_sim.py` | `7c4fcef35eb91054df775f05ed07154f097d5e0b5ea798a6313983bbebcb86fb` |
| `docs/research/secon2027_baseline_fidelity.md` | `68538ad6bd3461f935ce9d3e34c3917148ccf61051d1b0a0b2ca963dfbe08d55` |
| `docs/research/secon2027_experiment_contract.md` | `b23e09f654646aadec3af45b2d65f8eda55cf9aee1b4762ab9656c69f6c15192` |

辅助身份记录：[secon2027_supervisor_pilot_design_review.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_pilot_design_review.json)。关键实现位置：[`_schedule_traffic`](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tools/run_drc_experiment.py:252)、[环境故障与信道](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tools/secon2027_scenarios.py:91)、[worker 参数交接](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tools/secon2027_experiment.py:524)、[resolved parameter 应用](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tools/run_cpr_experiment.py:407)、[窄/宽故障暴露定义](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tools/analyze_secon2027.py:250)。
