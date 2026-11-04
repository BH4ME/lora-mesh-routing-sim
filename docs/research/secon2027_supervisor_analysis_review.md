# SECON 2027 分析器监督审查

审查日期：2026-11-04（Asia/Shanghai）。范围：分析器、人工统计测试与实验契约。此报告是分析器阶段审查，不表示 P0/P1、正式实验或匿名 SECON 稿已经完成。

## 版本与边界

- 被审查执行副本：`/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo`。
- Git HEAD：`a0ee4ce7bb96592c57dc5f389cf4c1958bec0069`。分析器和相关文件尚未提交，不能仅用 HEAD 标识本次版本。
- 首次完整检查的 `tools/analyze_secon2027.py` SHA-256：`f489eae9cc81066f523fce11800c5dfdf1e3288c8e277fa824841dadc9d3220e`。
- 对应 `tests/test_secon_analysis.py` SHA-256：`ea777744854f201aa62f4b6f24628d494c7a36756fd96c02f51ffb7c50a5ad44`。
- 契约 `docs/research/secon2027_experiment_contract.md` SHA-256：`b23e09f654646aadec3af45b2d65f8eda55cf9aee1b4762ab9656c69f6c15192`。
- 统计说明 `docs/research/secon2027_analysis_spec.md` SHA-256：`843fd44365cb6835f3b0a4c0d2c3ab91238a14c7e8b51dfb0079c2877bb804c0`。
- 上游 `tools/secon2027_experiment.py` SHA-256：`6908c859bade6aec9aebf8f9231c76ae5aebdd347d9791d3ddda47f5ceebbb51`。
- 审查期间执行方继续开发；第二次观察分析器 SHA-256 为 `d617736b3b98b4d91fe6d57e644a73b70e85bc76efb4c9f8d973b0af646048bd`，测试 SHA-256 为 `9681ceeff7163f691fe71509e92e67b3ef424bfddf05c6c0d9337346b869cdfa`。以下问题在该第二版本仍存在，原版与第二版行号均注明。

未修改执行副本中的源码、配置或证据。只运行纯分析单元测试、人工数据分析、临时目录绘图，以及读取已有 smoke JSONL 后调用 `summarize_run`；未调用 simulator 的 `run`/`run_matrix`，未冻结配置或运行任何研究 seed。本审查唯一负责的持久文件是本报告。

## 结论与真实反例

核心物理成本、全 scheduled 分母、零交付保留、seed 级配对和描述性区间语义符合契约。发现四项需修正的分析或声明问题，其中前两项已可由现有 smoke 原始证据直接观察，后两项由合法参数的纯分析 fixture 证实。现有主指标的数值正确性不应因辅助字段缺陷被笼统否定；未完成的 P1 实验、图表覆盖和论文工作也不作为代码缺陷。

### A1：初始 R/F 机制计数使用了错误的导出枚举

位置：首版 `analyze_secon2027.py:311–312`；第二版 `:323–324`。`initial_routed_flow_count` 比较 `initial_action == "R"`，`initial_flood_flow_count` 比较 `"F"`。

实际 flow JSONL 的字段来自 `tools/run_cpr_experiment.py:347` 的 `decision.action`。生产者在 `lora_mesh_sim.py:4062,4083` 写入的是 `R_INITIAL` / `F_INITIAL`，不是控制器内部 `flow.initial_action` 的 R/F。测试 fixture 在 `tests/test_secon_analysis.py:16–20` 填写 R/F，因此未覆盖真实导出格式。

读取既有三份 CPR smoke 证据、仅调用 `summarize_run` 的结果：

| seed | run_key | JSONL 初始动作 | 分析器 initial_flood_flow_count | 正确计数 |
| --- | --- | --- | --- | --- |
| 2027000 | `db03eb720995f17ddb82b6d25c2e6c62614b62c10695f0211099c0c96e717b92` | 4 × F_INITIAL | 0 | 4 |
| 2027001 | `7727c70d5ccb20f4f0f06a1f829e032c77506b9f467878691e439297fe197eed` | 4 × F_INITIAL | 0 | 4 |
| 2027002 | `834508465bb2ca9267117eebd7692f82fc68c7ab3ccaffcc83e7da5288139107` | 4 × F_INITIAL | 0 | 4 |

证据路径统一为 `results/secon2027/runs/<run_key>/attempt-001/evidence.flows.jsonl`。seed 2027000 同一次分析仍正确得到 61 个物理 TX，但两个初始机制计数都为 0。

影响：冷启动/缓存路径选择机制的汇总误报；不改变重建的 scheduled 分母、ACK/交付 PDR 或总 airtime。应按导出 schema 计数，使用真实 R_INITIAL/F_INITIAL fixture 验证，并重新生成受影响的分析输出；不需要因此重跑模拟。

### A2：RREP 的指定下一跳被归入 other_listener

位置：首版 `analyze_secon2027.py:271–278`；第二版 `:283–290`。角色分支处理了 ACK 和 DATA，却没有 RREP。路由回复在 `lora_mesh_sim.py:1965–1971,2646–2649` 按 `path[path_index + 1]` 接收及推进。

真实反例：已有 MeshCore smoke run `0d4c60a5c908c3de67d448aa4982c7791e2a75d4f3dbf0d258033b0f9ade5df0`，seed 2027000，attempt-001。物理 `tx_id=28` 是 RREP，`sender=5`，`path=[5,6,7,8,9]`，`path_index=0`；`rx_attempt_id=547` 在 receiver 6 成功解码，应归 `designated_next_hop`。

该 run 中从 TX/RX 原始路径独立计数得到 10 个 RREP 指定下一跳接收机会；分析器的 RREP 汇总却只有 other_listener/self，没有 designated_next_hop。输出为 other_listener 的 success=28、capture_collision=42、half_duplex=4、prr_fail=116，以及 self=10。

影响：路由发现回复的目标接收与旁听损失诊断混淆；不改变总 airtime、PDR 或 RX 总数。应依据 RREP 的实际路径语义分类并增加包含目标与旁听节点的回归 fixture。

### A3：消融对比未核验参考 CPR 的非消融参数一致

位置：首版 `analyze_secon2027.py:354–376`；第二版 `:369–391`。代码仅在同 case 中选择唯一 `protocol="meshecho-cpr"`，再以 `meshecho-cpr-` 前缀把其他臂标为 ablation；没有检查两臂参数。

反例：同 case、同 seeds 与相同五项外生哈希，参考 CPR 为 `flood_base_delay_s=0.45`，norepeat 为 `flood_base_delay_s=9.0`。两项参数均通过 `validate_parameters`，`aggregate_runs` 仍产出 ACK 差、交付差和 airtime log ratio 共三个 `comparison_kind="ablation"` 结果。额外改变定时参数后的对比不能解释为只关闭 repeat 的效应。

这不是被上游拒绝的非法输入：`validate_matrix` 的 `:118–121` 仅检查参数是字典；freeze 的 `:226–227` 逐臂验证合法性；audit_attempt 的 `:366–373` 仅将每臂证据与自身 spec 对照。对 `development_smoke.json` 的内存副本作以上修改，纯校验结果为 `validate_matrix=PASS`、`validate_parameters_all=PASS`、`generate_runs=21`，没有调用 freeze 或模拟。

现有 smoke 的参数均为 `{}`，本反例不意味着已有 smoke 消融配置不匹配。应验证每个消融与参考 CPR 的有效非消融参数一致，或把非等价参数对比明确分类为复合参数比较。需要覆盖参数差异拒绝和等效默认值处理的测试。

### A4：负载曲线可把不同臂参数连接并宣称其余配置固定

位置：第二版 `analyze_secon2027.py:539` 的 family hash 没有 arm 配置，`:550–552` 仅按 protocol 取第一行，`:555` 连线，`:558` 声明其余配置固定（首版相应为 `:524,535–537,540,543`）。

纯 `make_plots` fixture 在同 plan 中设置 low/S1/default 使用 CPR arm `flood_base_delay_s=0.45`、负载 4；high/S3/default 使用另一 CPR arm `flood_base_delay_s=9.0`、负载 20；其余 case、环境、deadline 字段相同，case.arms 分别选择对应的 CPR。实际生成了临时 PDF/SVG，并捕获到以下绘图调用：

```json
[
  {"x":[4.0,20.0],"y":[0.8,0.4],"label":"CPR"},
  {"x":[4.0,20.0],"y":[2.0,4.0],"label":"CPR"}
]
```

轴标题为 `default`，图标题为 `Declared load points with all other configuration fields fixed`。因此图中效应混合了负载与定时参数变化。作为反对照，仅把 high.configuration 改为 matched 后，负载曲线不生成，捕获的负载连线数为 0；default/matched 的隔离本身是有效的。

影响仅限具备此配置结构的负载曲线；当前 smoke 无该类曲线。应把有效 arm 参数身份纳入匹配并按正确 arm 选点，不以 protocol 的第一行代替配置匹配。这是实际生成错误连接的反例，不是因 P1 图尚未完成而提出的缺陷。

## 已通过的语义检查

以下行号对应首版 SHA `f489eae…`，第二版仅有相关位置平移。

| 核查项 | 结论与依据 |
| --- | --- |
| 物理 TX 而非 legacy 预留计费 | `:187–212` 使用唯一 tx_id 的 transmission JSONL，逐帧 `end-start` 与 toa_s 对照，再与 tx_ledger_airtime_s / started_request_count 对照。测试故意设置 legacy_reserved/旧别名为 9999/999，得到物理 5 秒/4 TX。 |
| 完整 ToA 与截止 | 已启动但截止时仍在空中的帧按完整 ToA 计费；未来 start 拒绝；canceled/queued request 不作为 TX。上游 frozen event audit 补充 request–TX–RX–ACK 联结。 |
| packet-kind × stage 互斥 | 每 TX 只进入一个二元 cell。RREQ/RREP=discovery、CPR marker=initial/repeat/recovery、legacy FALLBACK=fallback。成本表各 seed 的零出现也进入均值分母，分区总和检查通过。 |
| 全 scheduled 分母 | `:222–245,291–300` 对每一条 flow 重建 timely ACK/delivery；分母为完整 flows。上游 `audit_bundle:578–598` 将 flow 身份和数目与 application_trace 对齐，阻止遗漏 no-start 等流。 |
| ACK 与交付分开 | 分别重建两个 deadline 指标、延迟和 unfinished fraction；记录 destination delivery 但无 timely ACK 的流，不混同两者。 |
| 零交付成本 | 0 timely delivery 保留 `airtime_per_timely_delivery_s=None`，JSON null/CSV 空值；bootstrap 不丢弃 undefined seed，整个 all-seed estimand 为 undefined 并记录 undefined_n。 |
| 延迟与失败比例 | seed 内成功流 p50/p95；没有成功则 undefined；CDF 明示 pooled descriptive success-only，同时显示完整 scheduled 人口的 unfinished fraction。未把 packet 当推断样本。 |
| seed 级配对 | `:337–378` 每 plan/case/arm 恰好全体计划 seeds；跨臂五项外生哈希一致。可靠性先逐 seed CPR−control，再等权求均值；airtime 使用逐 seed log ratio 后求均值，非 pooled ratio。 |
| 场景、default/matched 与源版本边界 | plan_hash/case_id/arm_id 分组防止跨 plan 或 case 汇总。直接测试 default/matched 负载曲线隔离有效。A3/A4 指出的是非消融参数与负载 arm 匹配的额外缺口。 |
| 分析 RNG | `:333–334,583–589` 根据 analysis_seed 和 plan/case 派生 NumPy RNG，仅用于 10,000 次 bootstrap；不调用模拟器或注册 cohort。模拟 seed 只是配对标签。 |
| 描述性与多重比较 | 结果字段、图标题、analysis.json 和说明均标 descriptive/unadjusted；n<10 标不稳定，单 seed 无 CI；不作显著性、非劣效或多重比较受控声明。 |
| 不完整计划 | audit_plan 先检查完整性；任何 planned key 缺失/失败则只写 inventory 与 incomplete report，不输出选择性 performance aggregate；已存在输出目录拒绝覆盖。 |

## 验证记录与后续状态

首版运行 `python3 -m unittest tests.test_secon_analysis -v`：11 项通过，3.546 秒；其中完整 pipeline 只使用临时合成事件，生成真实 PDF/SVG。额外对 A1/A2 读取已存在 smoke 证据，未运行仿真；A3 使用内存 fixture；A4 使用自动清理临时目录生成图表。

以上测试通过不消除 A1–A4，因为原测试没有涵盖真实动作枚举、RREP 接收角色、消融参数不等价及跨负载 arm 参数变化。根监督线程已收到 A1–A3；A4 的实际绘图反例在本报告落盘时补报。执行方修复后需按新 SHA 定向复核并追加关闭记录；在看到修复和验证前，本报告不把这些问题标为已解决。

正式矩阵、P1 结果覆盖、论文结论与匿名性不在本次完成声明内。

## 2026-11-04 定向修复复核：A1–A3 关闭，A4 待修

此次复核的分析器 SHA-256 为 `2ad0248bf4dfd3a7f00cf67c1038b08f0602088ecd6e13376351cea65966fe00`，测试 SHA-256 为 `0e5a17c34931b366e98dcb5d53225291b86056f5c07e415fc956ad3ae35e0c39`。以下关闭仅针对该版本的分析器修复，不宣称已经替换所有既有分析输出。

- **A1 已关闭。** `:325–326` 现按导出字段 `R_INITIAL/F_INITIAL` 计数。再次读取前述三个 CPR smoke 原始证据、调用 `summarize_run`，每个 seed 都得到 `initial_flood_flow_count=4`，与各自 4 条 F_INITIAL 一致。新增生产格式 fixture 同时核查 R_INITIAL 与 F_INITIAL。
- **A2 已关闭。** `:289–290` 把 RREP 与 DATA 的 `path_index+1` 指定下一跳纳入分类，并保留 ACK 的反向索引语义。前述 MeshCore run 的原反例重新计算得到 RREP 指定下一跳 10 次，与原始 TX/RX 独立计数相等。测试同时覆盖目标、旁听和 ACK。
- **A3 已关闭。** `comparison_policy:354–386` 使用身份文件的实际附着前解析参数；`:425` 应用分类，`:666` 加载参数。原 `.45 vs 9.0` 反例经过 `aggregate_runs` 输出三个 `mixed-policy`，记录 `unexpected_parameter_fields=["flood_base_delay_s"]`，保留全部 6 个 paired seed 行。使用实际 `build_protocol` 解析但不构造模拟器，norepeat `{}` 与显式 `{"flood_base_delay_s":0.45}` 的参数完全一致，均分类 ablation。noackcancel 仅改变名称与 cancel_on_ack 时为 ablation。nocancel 实际关闭 cancel_on_ack、relay_ledger_enabled 和 evict_pending_on_capacity，分类 component-policy，带有 `legacy-nocancel-disables-whole-ledger-policy` 理由，不混入 ACK-only 消融面板。
- **A4 仍待修。** 本次读取时 `:576` 的 family hash 仍不含有效 arm 配置，`:587–592` 仍按 protocol 选第一行并连接，原问题尚未关闭。未重复运行该已知未修反例，也未忙轮询；等待根监督通知修复后，复核不同参数、等价默认参数及同协议多 arm 边界。

执行 `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_secon_analysis -v`：15 项通过，3.880 秒。此次没有研究仿真、没有新 seed、没有执行副本源码修改；新增验证仅为纯分析和读取既有 raw。
