# SECON 共同环境、参数与场景监督审查

日期：2026-11-04（Asia/Shanghai）。审查对象为隔离执行副本 `/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo`。本报告写在 canonical 仓库，未修改执行副本。

## 结论与范围

共同外生环境的设计及所检查生产接口成立：业务到达、静态阴影、时间衰落和定向链路时间信道场不依赖协议发送次数；匹配基线参数确实进入转发延时计算。未发现按结果重选拓扑、端点或排除失败流的逻辑。

独立复现过一个统计字段口径问题：旧 `Metrics.summarize()` 把截止之后才开始的已承诺无线电排队预留计入 TX/ACK/airtime；runner 的 `tx_ledger_*` 已正确排除这些预留。执行方随后修复了 runner 的普通物理字段别名并保留显式 `legacy_reserved_*`，根代理独立运行两个边界回归，均通过。本项在 SECON runner 导出层关闭，不代表旧 `Metrics` 的内部预留计数语义改变。

S1/S2/S3 数值矩阵、实际机制暴露诊断与正式冻结仍在开发中。此状态与合同的 Pending 一致，不应记作已完成实验，也不据此宣称实现有一个已确认的性能缺陷。需要在 pilot/正式场景验收时继续检查。

本审查只读源码和配置，并调用确定性构造、排程、信道查询与局部接口；只使用已有 fixture seed 92000，未调用 `Simulator.run()`、`run_one()`、`run_matrix()`，未执行研究仿真或新 seed。没有验证 RF、真实固件、完整模拟器正确性或最终投稿稿。本次子代理只读复核 S2/S3 定义，未修改文件或运行仿真。

## 读取版本

执行方仍在并行开发，以下为本审查读取/结束时的 SHA-256，不是正式实验冻结，也不能用代替最终 snapshot。

| 文件（执行副本相对路径） | SHA-256 |
| --- | --- |
| `tools/secon2027_scenarios.py` | `d83ebbf9f57a448c220a32f452f3e6e9bffe4a40580acd6f6e11909ddc25d061` |
| `tools/run_cpr_experiment.py` | `d43dcfa30eda47af2a40e99f429f21b5815c6fac97d6e90d161a37b63b96019f` |
| `tools/run_drc_experiment.py` | `e1ac79e951f1aeca9b85cee9c893d513e05b5c9600f2dd3c9eef29d078810d8f` |
| `lora_mesh_sim.py` | `7c4fcef35eb91054df775f05ed07154f097d5e0b5ea798a6313983bbebcb86fb` |
| `tests/test_secon_scenarios.py` | `2262eadbcdd357d572138487b33d9bbf4f4759faceec1de9cb60062eb6a5b047` |
| `configs/secon2027/development_smoke.json` | `d25f9c8b504c9c0326480fdb59215b33c78764e1afb86520e73982bac65a7eef` |
| `tools/secon2027_experiment.py`（结束时） | `6175ff21005bc9ce0b1634ca535ef915dc55637262bed80c3109ba8bd8f0a315` |

orchestration 文件在读取期间由 `1466805be39f425e03d7f218b65d58fe46bae9e61645ce5ea318927c6bf11fb1` 变为表中 hash；其完整 runner 身份与恢复审查由根代理另外负责。本报告不把局部读到的 orchestration 内容当完整最终验收。

## E1：共同环境与业务 trace

生产路径及证据如下：

- `secon2027_scenarios.py:48` 使用 `Random("secon-grid-positions-v1:{seed}")` 生成位置；端点由配置给出，未读取性能结果后过滤。
- `secon2027_scenarios.py:101` 的信道均匀数只由 seed、发送端、接收端及时间 bin 哈希产生，不含协议、TX ID 或查询序号。协议改变自己的发送时刻时可以遇到不同信道值，这是共同时间场的正确语义。
- `lora_mesh_sim.py:931` 在初始化一次性使用独立 RNG 生成静态阴影；`:1036` 的时间衰落由 seed、无向链路和时间块决定。`_RecordingSimulator.channel_uniform()` 将正常逐次 RX 抽样替换为公共场，`rx_power_dbm()` 加入同一故障时间表。
- `run_drc_experiment.py:252` 的业务排程使用独立 `Random(seed + 10000)`；`run_cpr_experiment.py:420` 在运行前保存完整 trace。`_flow_rows()` 遍历每条 trace，不按是否发包/成功过滤。多臂 `run_matrix()` 检查 topology/trace/radio/pairs/environment 身份，并导出各臂生效参数。

独立无事件运行核查：构造 20 节点、4 对端点、240 s、全网 8 次/分钟、SF7、2 dB 静态阴影和 6 dB 时间衰落的 fixture；对四个主协议，分别使用无故障与 90–180 s 两条边增加 80 dB 的环境。仅调用初始化、`_schedule_traffic()`、`_trace_from_events()` 和场查询，结果为：

| 8 个构造共同结果 | 值 |
| --- | --- |
| trace 条数 | 22 |
| trace SHA-256 | `f25c0bb885f30aa70f3f3fb82e8ea95ba4b77ff6512e0ae51154793a030dbab9` |
| 静态 shadow 表 SHA-256 | `829ce9bc52f493d3c9d65e13f22b33ea1da3c7f9e578b67ddd0b438b2960565b` |
| 定向 7→8、t=100 信道样本 | `0.030559269286431934` |
| 7–8、t=100 时间衰落 | `-4.20809295081077 dB` |

每次额外消费 100 个协议随机数并查询另外 100 个链路时间点后，同一信道查询结果保持不变。故障表改变 attenuation，但不移位业务到达、shadow 或信道创新。这是接口配对证据，不是性能结果。

## E2：参数覆盖进入实际决策

`run_cpr_experiment.py:362` 验证参数键、协议支持属性、有限数值及边界；`:407` 构造协议后、绑定模拟器前应用覆盖，再将简单属性作为 resolved 参数导出。`run_matrix():617` 为各臂保存生效值。

直接调用生产延时函数、恢复同一协议 RNG 状态作确定性核查：

| 协议 | 覆盖 | 默认延时 | 覆盖后延时 |
| --- | --- | ---: | ---: |
| Meshtastic-like | `base_delay_s=.45, jitter_s=.65` | 0.771054145963 s | 0.468246926501 s |
| MeshCore-like | `flood_base_delay_s=.45, flood_jitter_s=.65, route_ttl_s=600` | 0.519650536232 s | 0.468246926501 s |

MT 调用 `managed_delay()`，使用 router 角色和高 SNR；MC 调用 `flood_delay()`。MC 缓存写入读取 `self.route_ttl_s`（`lora_mesh_sim.py:1978`），生效值确为 600。没有把不存在的 MT `flood_base_delay_s` 当作有效覆盖。

此匹配只统一基础延时、jitter 宽度和适用 TTL；MT 的 SNR 罚项、MC 的发现逻辑等仍不同，不能称为所有参数/行为一致。现有 fidelity 文档已说明该边界。

## E3：截止后的预留计数——反例及修复

原反例直接构造 `_RecordingSimulator`（2 节点、SF7、fixture seed 92000），令 `sim.now=9`、节点 0 的 `tx_available_at=20`，分别为 DATA 和 ACK 调用 `transmit_later()`、`begin_transmission()`；随后读取截止为 10 的旧 metrics 与 `tx_history` 的 `start<=10` 子集。无需执行事件循环。

| 量 | 旧 Metrics 预留口径 | 截止内物理 TX |
| --- | ---: | ---: |
| TX 数 | 2 | 0 |
| ACK TX 数 | 1 | 0 |
| airtime | 0.148992 s | 0 s |
| 已预留开始时刻 | 20 s、20.097536 s | 无 |

根在执行方修改前已接收此反例。原始 `tx_ledger_airtime_s` / `started_request_count` 本来就按 cutoff 正确筛选，因此这不是该主指标凭空多计两次 TX，而是同一导出行普通名称与物理名称混用的风险。

当前 `run_cpr_experiment.py:480`–`:512` 将旧值保存为 `legacy_reserved_*`，从物理 transmission 表重建 TX/DATA/control/ACK、airtime、TX energy、RREQ/RREP、busy-time 等公开别名；`:1153` 起 artifact audit 检查这些别名与物理 ledger 一致。修复还为无成功 flow 的每成功交付成本保留 null，而非假造零成本。

根代理独立验证命令（由根实际执行，本审查代理未重复运行）：

```sh
/usr/bin/python3 -m pytest -p no:cacheprovider tests/test_cpr_experiment.py -k 't9_queue_reserved_until_t20 or cutoff_preserves_future_queue' -q
```

根回报结果：`2 passed`。本项 runner 导出修复已关闭。底层 `Metrics` 继续记录预留行为，其他没有使用此 SECON runner 的旧脚本仍不得直接把旧字段当截止内物理发射计数；这属于范围说明，不扩展本次修复任务。

## E4：S2 替代路径与 S3 负载待验收内容

当前仅发现 `development_smoke.json`，其目的为机械 smoke；合同明确三场景数值和 keys Pending。不能把测试 fixture 当成已经冻结/运行的 S2。

S2 fixture 在 `tests/test_secon_scenarios.py:9` 声明 90–180 s 对 `[7,8]`、`[12,13]` 增加 80 dB；结构最短路由 4 跳变 6 跳后恢复。可审查绕行示例为 `5→0→1→2→3→4→9` 和 `10→15→16→17→18→19→14`。`shortest_hops():109` 只做离线结构诊断，未提供给协议。目前它只在测试调用，生产报告尚未统计实际旧路径命中故障边、故障期间活跃流、替代结构可达和 repeat/recovery/ACK 暴露。

正式证据需要这些实际计数，因为预先缓存的路径可能本来绕开故障边；结构上存在故障和绕行并不能保证发生了缓存路径失效。保留零暴露和失败流，不能依照暴露或成功率筛掉样本。大衰减也不等于随机 PHY 下接收概率数学上严格为零，图模型应继续表述为结构诊断。

S3 数值未落盘。目前实现 `rate_per_min` 是全网总到达率，通信对按轮转分配，t=1 强制首条业务，其后间隔为指数分布；不能描述为每个节点/每对端点独立 Poisson 到达。`fixed-once` 根本不使用 rate，现有 smoke 不能仅修改 rate 变成高负载实验。后续 pilot 要明确 `pair_schedule`、全网 rate、pair count、generation horizon、deadline/drain；若希望解释单纯负载效应，S3 与 S1 保持其余环境和 PHY 一致。

这些是后续 pilot/冻结的验收项，本审查未擅自替执行方选数值、生成研究结果或启动 cohort。

## 交接

本独立审查完成。根可继续监督 P0 机械 smoke、pilot 数值冻结与暴露诊断。不要把当前接口核查、根的两项回归通过或结构 fixture 当成三场景性能评估或全部 SECON P0/P1 完成。
