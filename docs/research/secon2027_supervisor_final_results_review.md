# SECON 2027 最终结果与证据链审查
审查时间：2026-11-04T10:23:26.817244+00:00
执行树：`/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo`

**结论：23项通过、1项不适用（E03），无未关闭问题。** 数值/来源未发现差异；初读E12的915 MHz与duty-cycle/LBT披露缺口已由执行方修订，并按新hash完整重读关闭。报告仅绑定下列所读hash，论文后续编辑需定点复核。

本次只读复用已通过的冻结、verified原始、统计、暴露和归档恢复审查；没有运行模拟、新seed、原分析器、bootstrap、CI或再次完整raw/归档恢复。只新增本MD/JSON，不改执行树或95项主矩阵。图视觉与最终PDF由root另验。

| ID | 状态 | 具体证据 | 差异／边界 |
| --- | --- | --- | --- |
| E01 | 通过 | 复用 formal_freeze_review：纠正开发 pilot-v2 完成72/72，三场景×两regime×四模型，真实repeat/recovery/cancel、失败及wall/RSS/raw已审；当前 claim_evidence/reproduce 明确pilot仅开发。 | 未重跑开发数据。 |
| E02 | 通过 | 复用冻结审查与 secon2027_method_decision.md：正式前据完整pilot诊断选择保留fixed CPR；负载下负结果、失败分解及资源约束保留。 | 未据正式结果调整算法或选择新seed。 |
| E03 | 不适用 | 正式前选择保留纠正后的fixed CPR，没有新增算法候选；拥塞自适应仅在discussion列为未测未来工作。 |  |
| E04 | 通过 | formal_freeze_review 的18项链检查已过；09:01:52Z冻结760键，09:06:36Z首次正式启动。evaluation/claim_evidence保留09:09:21Z、43个完成run后的行政erratum。 | 原冻结合同字节不改，不能称为曝光前措辞修订。 |
| E05 | 通过 | 已审760键/38组每组20seed全部单attempt完成。mechanism-resource-costs.json：4423.191694785 worker-s，max20.901047375s，RSS398163968B，raw7098305927B，event7052691761B；与evaluation/reproduce一致，低于冻结18GiB预算。 | worker wall总和不是四并发历时；审计/分析/归档额外成本已声明。 |
| E06 | 通过 | main_results_source.csv的48行覆盖全部六case×四模型×两指标。S1 CPR N648/每regime、480routed/168cold、135repeat/91recovery、205ACK取消及4/6hop ACK均沿用独立暴露审查；正文保留相对ME不确定的确认收益与较高成本。 |  |
| E07 | 通过 | 独立S2暴露审查全部20seed有效：85初始路径交故障、159实际故障边TX/87flow、替代结构、恢复DATA/ACK链；正文严格区分85/87、保留648全分母；methods禁future-fault/global-reachability/delivery oracle。 | 86/3历史DATA-only与87/4全部包类型已明确区分；机制关联不当作消融因果效应。 |
| E08 | 通过 | 独立S1/S3暴露审查及全量文档：S3 N3059、1890repeat/1597recovery、3228collision/887half-duplex、6源容量拒绝、52protocol-no-start；队列均值与零relay eviction/容量取消如实披露。 | 不将零eviction视为无压力，不声称峰值occupancy或饱和阈值。 |
| E09 | 通过 | S1 ACK526（4hop440/6hop86），S3 ACK1181（4hop703/6hop478）；S2独立审查保留成功/失败流路径与完整forward/reverse链；prospective_scene_criteria全部六项通过。 | 实际多跳证据独立于H=6上限；默认/匹配重复记录不扩大n。 |
| E10 | 通过 | 160附加10/60s runs齐全，30s复用S2-matched。robustness_source.csv40行覆盖四模型、10/30/60s deadline及8/40两负载；全部n20，所有不确定性和负结果保留。 |  |
| E11 | 通过 | evaluation/results/FIGURES/reproduce明确deadline与drain联合变化、240s生成期及250/270/300s截止；无跨deadline推断。负载曲线仅两观测点；无TTL过期、广泛拓扑/信道泛化或饱和主张。 | 10s的99次recovery-deadline-infeasible与stale-route-generation原因分开，当前记录实体匹配。 |
| E12 | 通过 | 初读发现论文缺915MHz和明确duty-cycle/LBT说明；执行方修订后完整重读evaluation.tex/discussion.tex。evaluation.tex:73现明确915 MHz、SF7/BW125k/CR4/5/17dBm/capture/payload；discussion.tex:24–27明确无duty-cycle/LBT enforcement及CAD边界。methods保留完整wire/ToA/物理成本，正文仅限定合成模型。 | 缺口已定点关闭；最终evaluation hash def6effdf145a7fcf2a357c1402fdd1234bc6aff9da7167fccb146b0fd47aa33、discussion hash e4f0d786fa87a8f3b7177b80bb173b001c3bb5b2bb2758c20a09ceaf795036b9。无地区法规合规或RF实测主张。 |
| E13 | 通过 | 正式760/760、0失败/缺失、38×20完整；pilot-v1 48complete/1failed/23unstarted、纠正v2另snapshot、43完成后的同计划恢复均透明保留。全文突出S3不利结果。 | 复用verified原始审查；原39条ACK checker误报及修正链保留，未声称重跑纠正后的完整raw checker。 |
| F01 | 通过 | 复用verified_raw_review与formal_statistics_review：全部scheduled N、timely accepted ACK和destination DATA独立重算；正文Eq.outcomes一致，源拒绝/未启动/失败均不删。 |  |
| F02 | 通过 | 物理TX成本复用独立raw审查；formal-v2成本来源21行按kind×stage互斥，S1/S2/S3分别精确加回33.79041280000038/40.55121920000039/207.06675199999935s。 | ACK/relay及失败发送收费；只显示组件均值，不编组件CI。 |
| F03 | 通过 | 正文同时呈现seed及时成功p95及全分母unfinished，单位及时DATA成本；正文相关值逐精度与summary一致。evaluation完整38组latency表190标量匹配。 | 74全未定义summary行仍保留；本cohort没有零及时交付run，未声称覆盖不存在的极端输入。 |
| F04 | 通过 | repeat/recovery/取消/容量/route等诊断沿用120个CPR run的独立暴露审查；既有统计审查对其余导出诊断完成聚合/CI检查。正文明确source refusal与relay eviction不同，并分辨实际启动与request。 | 不声称所有诊断在本次重新raw重构；airtime不等同设备能耗，取消次数不直接换算净因果节省。 |
| F05 | 通过 | formal_statistics_review：760run、1330summary、90paired effects、1800seed metric pairs与10k case-scoped bootstrap独立重构通过；正文162标量、文档853标量按显示精度匹配。 | seed为单位，n20；默认/匹配不拼n40，airtime为exp(mean(log paired ratios))。 |
| F06 | 通过 | 冻结统计、evaluation/results各caption与claim_evidence均明示descriptive/unadjusted95%；保留跨0/1区间。 | 无确认性多重比较、非劣性/等价或历史阈值沿用主张。 |
| F07 | 通过 | methods实际input controller_timing，evaluation有四模型表；results引用四个实际formal-v2 PDF。145来源行逐字段等于已审CSV，7输入/16输出/生成脚本hash全符，4图覆盖main/六消融/deadline及load/latency+unfinished+cost。 | 本项仅覆盖图表实体、范围、数值及来源；最终版面/字体/视觉由root另验，不以本报告替代。 |
| F08 | 通过 | claim_evidence的E1–E8逐条列正文位置与CSV exact selectors/暴露证据；M1–M11绑定实现/测试与边界。formal-v2 source→analysis hash→case/arm/20seed run_key→completion/manifest→snapshot链有实体；copied canonical六JSON逐hash相等。 | 历史P0/pilot/erratum/旧图明确标签；ICC数字不作本轮证据，S3负结果与未证明范围显式。915MHz披露修订及关闭单列E12。 |
| G07 | 通过 | docs/results/secon2027_evaluation.md包含38组完整均值/CI、30比较、38组latency、3组成本及全暴露/限制。自动解析109个数值表行853标量与summary/paired/cost表逐显示精度一致。 | 当前源hash限定；无仅保留最好场景。 |
| G08 | 通过 | docs/research/secon2027_claim_evidence.md实际存在；完整F08链、支持范围、审计范围、未证明项与历史失败/更正均明确；正式关键hash匹配当前实体。 | 文献/匿名/PDF与远端发布最终核验由对应主审承担，本项不代替那些验收。 |
| G09 | 通过 | reproduce有Python3.9.6/NumPy1.26.4/Matplotlib3.7.5/pytest8.4.2、显式root的saved audit/analysis/plot命令、resource与snapshot/index/parts还原流程；正式archive review实体现有且hash与canonical一致。 | 复用已完成clean restore：11parts、475828160B、14667文件、7104348257还原B；saved audit760/760、0failed/missing、570.835824s、760completion与prior相符、还原文件不变。本次仅验索引hash与11part存在/大小，不重复还原或raw全审。 |

## 本轮直接核对

- 正文72组、162个数值，与已审summary/paired表逐显示精度匹配；不重新估计CI。
- evaluation文档38均值行、30配对行、38延迟行、3成本行，共853个标量逐精度匹配。
- formal-v2：7项输入、16项输出及生成脚本hash全符；48+12+40+45=145来源行与原CSV逐字段完全相同。真实4个PDF、4个SVG、4个PNG、4个source CSV均存在。
- 成本21个kind×stage来源行分别加回S1/S2/S3的33.79041280000038、40.55121920000039、207.06675199999935s；六场景claim gate与六消融isolation/exposure gate均有实体通过。
- 10s的99条recovery-deadline-infeasible记录确实存在；stale-route-generation没有混算。
- 六份复用canonical review JSON副本逐hash相等；归档两索引hash与既有恢复审查相符，11parts实体和大小存在。clean restore的760/760通过记录真实，不以文档声明代替。

## 所读文件指纹

| 路径（相对执行树） | SHA-256 | bytes |
| --- | --- | ---: |
| `paper/secon2027/results.tex` | `bdf6253411123237995935b0f3a7780fd7743dc4e75a428d4a4c9786146dff3b` | 9719 |
| `paper/secon2027/evaluation.tex` | `def6effdf145a7fcf2a357c1402fdd1234bc6aff9da7167fccb146b0fd47aa33` | 8897 |
| `paper/secon2027/discussion.tex` | `e4f0d786fa87a8f3b7177b80bb173b001c3bb5b2bb2758c20a09ceaf795036b9` | 2424 |
| `paper/secon2027/methods.tex` | `3f83c893cba6defd213de5cbe01ab54af615cc00e98eeb8cc7bb277a481ed5be` | 11240 |
| `paper/secon2027/controller_timing.tex` | `8a6eaafdd952c738870da86386d0a371d45062e5629785198476897f00406bf7` | 3303 |
| `paper/secon2027/main.tex` | `48d3d1c2ec8f4cbf81cbfb48ff270ed7ed38d4ff1f88bc7294715462325d9b14` | 2834 |
| `paper/secon2027/build_figures.py` | `b92f5156cf976da71cc3513f0b472359cf212b1e54a3726bc48ac739bea75b9a` | 24190 |
| `paper/secon2027/FIGURES.md` | `a0079fe89091081b24393a2c2da15bbc68b955914fb86a5f9536e353bafbb33b` | 3987 |
| `paper/secon2027/figures/formal-v2/figure_manifest.json` | `f03046d53e9e8f5c08abf1d0727e8953cffa33d7887810d41668a59addd247af` | 5678 |
| `docs/results/secon2027_evaluation.md` | `cff27af5d3f6c597544f58dcb9c3a7dbb932b0e1b35ff150eab112057a2e7921` | 32529 |
| `docs/research/secon2027_claim_evidence.md` | `a4be5d0ce2d18ab323adb165b3f8c5fb0e801e8d15725b8c870ab810e0485ee8` | 15516 |
| `docs/reproducibility/secon2027_reproduce.md` | `d5b08dcc5210e5a8fe4d0d4929aa30f81742d7c730bdc540342daff9bbf50250` | 21048 |
| `docs/research/secon2027_method_decision.md` | `5b842194f59719e47a42f79f24b03aafc0b92597d382907df01b3acdd32f59ba` | 6075 |
| `docs/research/secon2027_formal_contract_erratum.md` | `24cb723f156e45e9ed44b1a9bbfb4f40346dbca8457a22803927216f1f0ea0e4` | 3233 |
| `docs/results/secon2027_formal_mechanisms.md` | `2aa78f87bd03ec297931663c8b3328a468519643598009c9cdf5081faf777441` | 14188 |
| `results/secon2027/plans/formal-v1.json` | `e738c34f726718027c46ff832aea8ca1bb095fa1e4a9cb5c8d25f271012e4052` | 1614177 |
| `results/secon2027/analysis/formal-v1/analysis.json` | `8ab85b0313dd99b499947b3c481bd16ab96a0ca0418dae522699de7f659156ef` | 302868 |
| `results/secon2027/analysis/formal-v1/runs.csv` | `95e8f0cfded9eedd2c3235e5a2e3f092ff768161bfa3cc24bdb69540b36da425` | 1024270 |
| `results/secon2027/analysis/formal-v1/summary.csv` | `748639f4a1559dbd1a922d53e93bc2717882e927386d5ee40c6c1e8d73cff639` | 368130 |
| `results/secon2027/analysis/formal-v1/paired_effects.csv` | `30323f08da14bef59b8c2e78b52dd27de74f3719a1028e691c07bfdf47c34aa3` | 156464 |
| `results/secon2027/analysis/formal-v1/paired_seed_effects.csv` | `7a2198f566b5541c6a50b935f64646b2362c218ce30b5079979792400dbb01e7` | 2944653 |
| `results/secon2027/analysis/formal-v1/cost_summary.csv` | `e8e9a92be26f6136157dcb9e04c26152129d110d5f614a3ae3b1847023cae671` | 30179 |
| `results/secon2027/gates/formal-v1/decision-rejection-reasons.json` | `bfc1fc41671cca9d00b2045ccc46fc6cb5c6a2d6faf45b92c74071534127fbcb` | 4452 |
| `results/secon2027/gates/formal-v1/mechanism-resource-costs.json` | `7281095cd9e9fffc8b90879e9fb221501c903599740cb2253d945debdb81bdc8` | 13842 |
| `results/secon2027/gates/formal-v1/prospective-criteria-and-comparisons.json` | `5e2c696579ddb07554c1d9601a44a10fa9de301670df0f150367c30c27162ec9` | 612323 |
| `artifacts/secon2027/formal-v1-raw-evidence.parts.index.json` | `bc9d34574666a5185d51a9b3b87e976eff508b12c7bedaa0951abc228699d407` | 3517714 |
| `artifacts/secon2027/formal-v1-raw-evidence.index.json` | `d4d9999156a4ac24b36d7ae82c87c7d614051d1b3dbe33c781280d1f4affab4f` | 3515572 |
| `artifacts/secon2027/reproduction_helpers/restore_evidence.py` | `097f5025efb52c863437a8e76fd3a7daa3a9a0120cfaadd084b1531d6720b312` | 1300 |
| `docs/research/secon2027_supervisor_formal_freeze_review.json` | `e3b222528e64d31e9139bbf54562e1d147a29c0b833801f360ad4d74518b5ea8` | 25630 |
| `docs/research/secon2027_supervisor_formal_exposure_review.json` | `1cec389f560eabcbf2c6c41da8af8cbeacfc6f53950d3314849d2a309b0446c2` | 2651876 |
| `docs/research/secon2027_supervisor_formal_s1_s3_exposure.json` | `d182c299c2eb8b51ad0a2db815e447400061ff4fd596a23bbb2e07f34e0875d6` | 508878 |
| `docs/research/secon2027_supervisor_formal_statistics_review.json` | `6aa0894375cbcb78e489eaed547a62680774ccb21a4e385e580f03173324196d` | 545725 |
| `docs/research/secon2027_supervisor_formal_archive_review.json` | `8730d7a9f389e33e1031b8d087cac9465443fbc3a6a933980ed8c39631cd9275` | 6510792 |
| `docs/research/secon2027_supervisor_formal_raw_review_verified.json` | `9dadbb649d49e3d62b6a8ba556a21f00cbd36407a4b430d92d6ce6733685907a` | 6243496 |

初读至写报告的四个重点文件变化：`{"paper/secon2027/evaluation.tex": {"initial": "5937712fcce08e2d10c02f90689518064e4b9a565f2499e5f06b76f6001ff19d", "final": "def6effdf145a7fcf2a357c1402fdd1234bc6aff9da7167fccb146b0fd47aa33"}, "paper/secon2027/discussion.tex": {"initial": "e50f0e968c410f89f78e7361092d0ac896528c654ba76a22e72239e0c666dc92", "final": "e4f0d786fa87a8f3b7177b80bb173b001c3bb5b2bb2758c20a09ceaf795036b9"}}`。

详细逐项状态、检查计数与范围在相邻JSON。本报告不代表视觉、匿名、文献、远端发布或提交最终验收。
