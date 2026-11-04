# SECON 2027 最终基础证据复核

复核时间：2026-11-04T10:30:16.921716+00:00。范围仅canonical95项矩阵中的A01–A07、B01–B12、C01–C10、D01–D11，共40项。状态：通过34，不完整4，条件不适用2。

本轮不改执行树或主矩阵，不重跑760正式仿真/全量审计，也不重复已成功的161测试。复用已保存的冻结测试、正式raw/暴露/统计及完整归档恢复证据；另外在独立临时目录完成29项CLI、冻结守卫及真实进程锁/恢复检查，全部通过，零仿真、零新研究seed。

真实恢复补测终止的是持有生产锁并写入部分attempt记录的进程，恢复时使用真实PID与ps检查；没有启动科学_worker，也没有声称attempt-002仿真完成。最终PDF、最终closeout提交/远端SHA与可获取归档的综合验收仍由根监督完成。

正式身份：plan `5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0`；snapshot `63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee`；tested2.1.29，当前VERSION2.1.30仅按已保存promotion映射解释。完整正式归档已在新空目录恢复14667成员/7104348257字节，并用包内保存源码审计760/760、零失败/缺失；本轮不重复该恢复。

## 逐项状态

| ID | 状态 | 已证明 | 剩余边界 | 当前证据索引 |
| --- | --- | --- | --- | --- |
| A01 | 通过 | 488项canonical实际工作状态导入独立Git副本；485逐字一致，3份规划保留原文完整后缀；初始导入a0ee4ce7bb96592c57dc5f389cf4c1958bec0069。应用managed附加失败已披露，不影响明确绝对路径的独立副本。 | — | `import_review`, `import_ledger`, `original_status`, `checkpoint` |
| A02 | 通过 | 根监督从原执行turn读取真实成功工具记录：完整新handoff、任务书、ICC代码审查、三份根规划、两项合同和完整固件handoff均有commandID/cwd/exit0；原导入ledger绑定实际文件版本/hash。新规划明确覆盖历史范围，旧目录和历史结果边界保留。 | 原始读取证据由根监督从read_thread提取，本分审核对其保存记录及导入身份；不是事后补造执行时间或把复制当读取。 | `original_reads`, `import_ledger`, `import_review`, `checkpoint`, `task_plan`, `progress`, `findings` |
| A03 | 不完整 | 原始tracked/untracked清单与488项导入保留；182项ICC/paper资产在两树的已保存核对无差异，冻结166输入除VERSION外匹配；无破坏性清理或资产丢失反例。 | 最终限定closeout提交、最终源树状态与最终提交内容对照仍需根监督合并验收；本报告不将预发布审查称为最终发布完成。 | `original_status`, `import_review`, `preservation`, `release_review` |
| A04 | 不完整 | 已保存四个官方URL、2026-11-04访问时段、逐响应hash与规则摘录；9页含全部内容、10pt、双盲明确，时区/注册节点未知未被编造。已有最终PDF分审证据。 | 当前checklist仍列最终PDF/政策/披露核对未闭环；最终候选规则及同一最新PDF的综合关口由根监督验收，不在本分审替代。 | `official`, `checklist`, `pdf_review` |
| A05 | 不完整 | 时间序列记录P0、失败pilot、修复pilot、冻结、行政暂停43键、同计划恢复及760完成；原记录与freeze/raw证据链一致。 | checkpoint最新18:06条目仍称promoted fixture检查、clean restore和push进行中，已落后于后续独立证据；最终命令/退出码/产物/远端状态与下一动作需收尾更新。 | `checkpoint`, `pause`, `freeze_review`, `raw_review` |
| A06 | 通过 | P0-v3 21、纠正pilot-v2 72、正式161测试及门控先于760正式执行。gate09:01:06Z→freeze09:01:52Z→first start09:06:36Z；09:09:21Z行政勘误如实位于曝光后，同计划恢复未调方法/换seed。 | — | `freeze_review`, `pause`, `tests_command`, `tests_log`, `raw_review`, `archive_review` |
| A07 | 通过 | SECON稿位于独立paper/secon2027，182项ICC/paper资产已核查保留；checklist明确候选材料及未执行EDAS、付款、邮件，未把论文产物称为已投稿。 | 通过范围为隔离和行为边界，不表示投稿、最终PDF或最终发布完成。 | `paper`, `preservation`, `checklist`, `documents_review` |
| B01 | 通过 | 正式166文件源码snapshot含未跟踪依赖、VERSION、合同、schema、依赖/环境，全部正式key绑定；完整原始归档在新空目录还原14667成员/7104348257字节，并从保存源码审计760/760完成，零失败/缺失。 | 本项证明本地可恢复；最终远端发布单列B12。 | `snapshot_descriptor`, `formal_plan`, `archive_review`, `archive_explanation`, `requirements`, `import_ledger` |
| B02 | 通过 | 581历史结果/614实际seed/零解析错误，合同与authorization来源/行/hash登记；除92200/92300外的关闭、预留及暴露区间均覆盖，保守排除0..999999。 | — | `historical_inventory`, `legacy_registry_import`, `registry`, `import_review` |
| B03 | 通过 | development2027000–2027002与validation2027100–2027119分离；冻结前正式无历史重叠，注册计划/source/config/seed状态/首次执行及artifact可联结。正式20seed现已暴露而非仍未见。 | — | `registry`, `freeze_review`, `pause`, `formal_plan`, `raw_review` |
| B04 | 通过 | 760唯一cohort/config/source/case/arm/seed键与登记集合一致；实际两arm冻结worker测试证明首arm暴露后另arm继续，重复completed只核验跳过。临时副本实际verify_plan拒绝未登记key，execute_one拒绝计划外spec。 | — | `runner`, `test_secon_frozen_worker`, `test_secon_orchestration_review`, `formal_plan`, `freeze_review`, `raw_review`, `tests_log` |
| B05 | 通过 | external --seed为required且没有隐式历史seed；本轮真实help、缺seed退出2且目录零变化。registered入口从matrix显式cohort/seeds及--plan绑定，真实缺cohort/缺seeds退出1、缺plan退出2且无仿真产物；正式有效计划已有760成功运行。 | — | `external`, `runner`, `test_cpr_external_comparison`, `formal_plan`, `tests_log` |
| B06 | 通过 | 补充使用正式metadata的临时副本，无模拟调用：无合同、源码/配置篡改、missing/failed gate、method未冻结/源码不符、retired/wrong-purpose/seed-state、未注册plan/key均拒绝；registry不变、无新计划/运行产物。完整合法计划可verify；真实正式运行正例由既有760证据支持。 | — | `runner`, `snapshot_descriptor`, `formal_plan`, `test_secon_experiment`, `test_secon_orchestration_review`, `tests_log`, `raw_review` |
| B07 | 通过 | 新增两个真实进程在共同启动屏障后争同一生产run_lock：一方获得、一方拒绝，正常释放无残留。冻结测试包含重复输出拒绝、真实双线程exporter仅一完成、partial写失败保留；真实SIGKILL持锁fixture恢复保留原started/runtime/stdout并归档旧锁，后续可重新获得锁。正式760每键仅一完成attempt且旧43completion未变。 | 真实终止fixture没有启动科学_worker，也未声称新attempt-002仿真完成；失败重试选择策略和科学错误不可重分类另由现有回归覆盖。 | `runner`, `test_secon_experiment`, `test_cpr_experiment`, `test_secon_frozen_worker`, `pause`, `raw_review`, `tests_log` |
| B08 | 通过 | 正式760全部必需raw文件及completion哈希/身份联结通过，空清单/缺RX/互换arm包均拒绝。已执行161测试内的writer故障注入在flows后actions失败，manifest标failed、partial保留且不能覆盖/审计为completed；生产completion仅在完整审计后原子排他写入。 | — | `raw_review`, `archive_review`, `runner`, `test_cpr_experiment`, `test_secon_orchestration_review`, `tests_log` |
| B09 | 通过 | MappingProxyType显式registry，external传EXTERNAL_REGISTRY而不临时改全局。重复/未知arm异常/写入TypeError回归和真实多进程正式运行保留arm身份；760 manifest及控制开关独立一致。 | — | `cpr_runner`, `external`, `test_cpr_external_comparison`, `test_secon_frozen_worker`, `raw_review`, `tests_log` |
| B10 | 通过 | closed schema/非法字段/非法配置/unknownarm/ungatedvalidation回归在161测试内；本轮保存真实registered freeze/run/help输出。真实执行矩阵覆盖S1/S2/S3×default/matched及160 deadline/drain稳健性，非更换smoke名称。 | — | `schema`, `runner`, `scenario`, `test_secon_experiment`, `test_secon_scenarios`, `test_secon_orchestration_review`, `formal_plan`, `raw_review`, `tests_log` |
| B11 | 通过 | SECON audit_bundle按冻结spec/合同独立核验；源码/配置/数据tamper、无物理ACK/目的交付/错包身份均有负向测试。历史合同文件保留，默认历史合同API及显式source_root闭包正负测试均纳入161；源码snapshot保留全部旧合同依赖，使用对应保存源码审计机制可用。 | 不把本次SECON通过追认历史缺陷数据；本轮未重审全部October原始批次，也不声称当前审计器可迁移所有历史schema。 | `runner`, `cpr_runner`, `historical_contract`, `snapshot_descriptor`, `test_cpr_experiment`, `test_secon_orchestration_review`, `test_secon_frozen_worker`, `tests_log`, `raw_review` |
| B12 | 不完整 | 行政暂停43完成键原hash保留并verified-existing，最终760无缺失/重复；真实OS终止fixture恢复保留partial/failure/锁且无静默补样。P0、pilot、正式全包均已独立空目录恢复；正式11分片整体SHA81776e12501e56945dd8aad6a37bb68e5f6e4b41d66c88ae041e7689e490d067，14667成员、包内审计760/760。 | 最终远端提交/位置以及可获取分片的验证由根监督闭环；当前本地全包恢复已通过，不据此声称远端下载恢复成功。 | `pause`, `raw_review`, `archive_review`, `pilot_archive_review`, `p0_archive_review`, `reproduce`, `release_review` |
| C01 | 通过 | 真实接收入口的源回流在seen过期后仍拒绝，冷/恢复FLOOD注入seen；含环/错sender/path先校验再产生副作用。161冻结回归与正式逐流源阶段界/事件审查均通过。 | — | `simulator`, `cpr`, `test_secon_cpr_correctness`, `core_review`, `algorithm_review`, `tests_log`, `raw_review` |
| C02 | 通过 | 并发冷/路由流ACK各自确认与共享缓存刷新分离；合法旧ACK不回滚较新异路；confirmation_revision使旧deadline不损坏较新同路径刷新，包括同刻ACK。原监督反例修复后直接调用通过，相关回归纳入161冻结。 | — | `simulator`, `drc`, `test_secon_cpr_correctness`, `test_meshecho_cpr_controller`, `core_review`, `tests_log` |
| C03 | 通过 | flow/端点/path/物理sender/marker/epoch/generation/deadline检查保留；过期与重放不二次完成。正式760 ACK联结重算23836接受/78拒绝，manifest只计accepted，原监督计数断言错误已透明更正。 | — | `test_secon_cpr_correctness`, `test_meshecho_cpr_controller`, `core_review`, `tests_log`, `raw_review`, `raw_explanation` |
| C04 | 通过 | 正式51145 scheduled流实例逐ID联结application trace，容量拒绝/未发/失败均留分母；deadline ACK与destination delivery分别重算，future reservation/cutoff边界回归保留，不能把跨arm汇总当独立样本量。 | — | `cpr_runner`, `runner`, `test_cpr_experiment`, `test_secon_orchestration_review`, `raw_review`, `tests_log` |
| C05 | 通过 | 正式574959唯一物理TX及request/TX/RX/ACK关联通过；未来排队预留与真实air-start分离，TX-onlyairtime51774.079744s按实际截止内发射重算。t9预约t20/cutoff10反例纳入冻结测试，不将未来承诺虚算air cost。 | — | `cpr_runner`, `test_cpr_experiment`, `environment_review`, `tests_log`, `raw_review` |
| C06 | 通过 | 取消仅匹配可取消中继，commit后不改成cancel且成本保留；重复FLOOD、同刻ACK/timeout及请求/成功取消分开。已执行纯controller/真实接收回归与正式所有取消/物理airtime核验一致。 | — | `cpr`, `test_meshecho_cpr`, `test_meshecho_cpr_controller`, `test_secon_cpr_correctness`, `algorithm_review`, `tests_log`, `raw_review` |
| C07 | 通过 | initial/repeat/recovery动作、commit/start及fits/deadline生命周期按规格有界；同时ACK/timeout仅终结一次，cold仅初始FLOOD。正式source-stage界全部通过，no-repeat2758 nominal-slot记录逐条重构wire/ToA与请求/真实开始顺序。 | — | `algorithm`, `algorithm_review`, `test_meshecho_cpr`, `test_meshecho_cpr_controller`, `test_secon_cpr_correctness`, `tests_log`, `raw_review` |
| C08 | 通过 | 可控ledger容量测试实际触发eviction并保护committed；noackcancel仍保留容量行为；重复FLOOD只取消同一未commit阶段，同刻timer与晚ACK确定。正式零relay eviction与source capacity拒绝分别报告，不把容量行为算ACK效果。 | — | `cpr`, `test_meshecho_cpr`, `test_secon_cpr_correctness`, `core_review`, `algorithm_review`, `exposure_review`, `raw_review`, `tests_log` |
| C09 | 通过 | 保存的正式snapshot命令/环境/exit0与日志161passed、11warnings、14.26s绑定13测试模块，当前这些模块逐hash仍等于正式冻结文件。既有fixture92000重放row/flows/actions/requests/TX/RX/ACK/identity完全一致，正式同源场景重复测试亦在161内。本分审未重跑测试套件/仿真。 | — | `tests_command`, `tests_log`, `snapshot_descriptor`, `determinism`, `test_secon_scenarios`, `closeout_tests`, `closeout_inputs` |
| C10 | 通过 | 旧ICC结果保留历史身份；pilot-v1因实现缺陷48完成/1失败/23未启动，以incident和原snapshot保留，不做infrastructure重试；修复后pilot-v2另snapshot完成72，formal另冻结760。原始manifest未重标版本/扣TX/删坏流，正式完整事件审查独立覆盖全部key。 | 旧2.1.28发布对该恢复拒绝分支未获验证的限制仍明确披露。 | `pilot_incident`, `release_map`, `import_review`, `preservation`, `pilot_archive_review`, `raw_review`, `paper` |
| D01 | 通过 | 四主模型mapping、默认/匹配参数及全部frame/ACK/发现/重试简化有明示；MT上游54e0d8d0…、MCFAQ81dbae59…固定引用。fidelity和论文源码使用-like/behavioral models，列官方遗漏并限制产品性能主张。 | 本项采用已有源码文档审查；最终PDF视觉/匿名验收仍归根监督。 | `fidelity`, `documents_review`, `paper`, `algorithm_review` |
| D02 | 通过 | default-family三场景四模型完整实际结果，manifest导出生效参数且MC/MT各默认值明确；正式完整raw与配对统计审查支持，未凭同一CprCase虚称全部参数相同。 | — | `fidelity`, `formal_plan`, `raw_review`, `statistics_review`, `environment_review` |
| D03 | 通过 | 机制匹配规则验证前冻结，PHY/业务/deadline/计费共同；可匹配timer/cache参数及不匹配行为明确。matched独立结果全在760；CPR/ME相同有效配置的default/matched不合并成n40。 | — | `fidelity`, `formal_plan`, `freeze_review`, `raw_review`, `statistics_review`, `environment_review` |
| D04 | 通过 | 外生topology/traffic/radio/time-channel/fault身份跨arm逐case/seed全匹配；独立业务/阴影/哈希信道场不随协议随机数消耗移位。已记录额外消费100个协议随机数和查询后相同信道不变的确定性接口核对。 | — | `scenario`, `environment_review`, `test_secon_scenarios`, `tests_log`, `raw_review` |
| D05 | 通过 | 协议使用本地可见信息，结构故障诊断不回传给源，不读取未来故障/远端交付oracle；DATA/ACK/RREQ/RREP/repeat按真实物理TX全计费。wire108组合/ToA320组合局部核对与正式跨arm完整账目支持。 | — | `fidelity`, `algorithm`, `algorithm_review`, `environment_review`, `raw_review`, `exposure_review` |
| D06 | 条件不适用 | 本轮正式760仅四主模型及三个已清晰命名的纯CPR控制，没有将common-ACK/强化基线作为正式模型或替换旧MC-like。文档区分补充common-ACK策略；此可选variant触发条件未成立。 | — | `fidelity`, `formal_plan`, `raw_review`, `documents_review` |
| D07 | 通过 | 纯noackcancel只关闭ACK中继取消，保留ledger/容量取消/源ACK及source-request取消。S2/S3matched各20seed与CPR仅toggle和名称不同，禁用事件均0；CPR参考实际成功ACK取消204/685。正式relay capacity eviction均0，与源容量拒绝分开；图文没有将整个取消组件误称ACK单因素。 | — | `algorithm`, `test_secon_cpr_correctness`, `raw_review`, `mechanisms`, `statistics_review`, `tests_log`, `paper` |
| D08 | 通过 | norepeat使用同一source FSM/wire和物理计费，预先声明保留名义观察slot后才可recovery，不制造repeat request/TX。S2/S3matched×20真实控制结果完整，禁用repeat事件0，参考repeat实际182/1890；2758 routed-initial控制slot记录重构确认时序及marked frame ToA。 | — | `algorithm`, `algorithm_review`, `test_secon_cpr_correctness`, `raw_review`, `mechanisms`, `formal_plan`, `statistics_review`, `tests_log` |
| D09 | 通过 | norecovery保留initial/repeat及其准入，禁止recovery请求/物理发送；真实S2/S3matched×20控制已执行，禁用recovery事件0，参考实际recovery142/1597。未以旧DRC替代该对照。 | — | `algorithm`, `test_secon_cpr_correctness`, `raw_review`, `mechanisms`, `formal_plan`, `statistics_review`, `tests_log` |
| D10 | 条件不适用 | 预定正式研究未选择容量扫描；完整正式relay-ledger capacity eviction为0，未作内存收益/最优容量主张，因此该条件性敏感性分支未触发。source-state refusals另计；确切peak occupancy未记录，零eviction不能推出occupancy从未达到8。 | 不据零eviction宣称容量已验证，也不在已曝光后新增容量轴。 | `algorithm`, `raw_review`, `exposure_review`, `mechanisms`, `formal_plan`, `paper` |
| D11 | 通过 | 三纯控制×S2/S3matched×20=120冻结keys，CPR参考复用原相同case/config/source/cohort/seed的主比较行。逐seed resolved参数仅指定toggle和名称不同；全部控制/参考原始hash与合法复用身份由独立raw审查验证，未改旧数据凑配对。 | — | `formal_plan`, `freeze_review`, `raw_review`, `mechanisms`, `statistics_review`, `algorithm` |

证据索引的完整路径、当前SHA-256见下表；逐项JSON同时内嵌对应文件hash、精确函数/测试行号及补测名称。核心正确性C01–C09引用的13测试文件均逐hash匹配正式snapshot，原保存命令exit0，日志161 passed、11 warnings、14.26s。

## 新补充验证

| 检查 | 结果 |
| --- | --- |
| `external-help` | 通过；exit 0 |
| `external-missing-seed` | 通过；exit 2 |
| `registered-help` | 通过；exit 0 |
| `registered-freeze-help` | 通过；exit 0 |
| `registered-run-help` | 通过；exit 0 |
| `registered-recover-help` | 通过；exit 0 |
| `registered-missing-plan` | 通过；exit 2 |
| `registered-missing-cohort` | 通过；exit 1 |
| `registered-missing-seeds` | 通过；exit 1 |
| `valid-frozen-plan-verifies` | 通过 |
| `missing-contract` | 通过 |
| `unfrozen-source` | 通过 |
| `unfrozen-configuration` | 通过 |
| `retired-cohort` | 通过 |
| `wrong-cohort-purpose` | 通过 |
| `invalid-seed-state` | 通过 |
| `unregistered-plan` | 通过 |
| `unregistered-run` | 通过 |
| `execute-one-unplanned-spec` | 通过 |
| `missing-development-gate` | 通过 |
| `missing-development-gate-no-registration` | 通过 |
| `failed-development-gate` | 通过 |
| `failed-development-gate-no-registration` | 通过 |
| `unfrozen-method` | 通过 |
| `unfrozen-method-no-registration` | 通过 |
| `unfrozen-method-source` | 通过 |
| `unfrozen-method-source-no-registration` | 通过 |
| `two-process-same-key-exclusive` | 通过 |
| `real-killed-owner-recovery` | 通过；exit -9 |

所有CLI命令、cwd、stdout/stderr、退出码和前后目录hash，守卫异常/零run产物，两个进程PID/响应/锁hash，SIGKILL退出码及保留partial证据hash，以及完整可复核checker源码均嵌入配套JSON。

补测原始结果SHA-256：`7e4089f385a16e74a2df8dadad2cb1750ac5da7aaccf570d6718c4ccac95f27f`。补测checkerSHA-256：`bbb3674cb21cc7f6f16eb70a1b55f851fd12086052c025c2c502b579c93a5727`。研究仿真调用数0。临时副本只使用已有正式metadata进行拒绝/锁测试，不把它登记为新research run。

## 当前证据hash

| 索引 | 当前文件 | SHA-256 |
| --- | --- | --- |
| `import_review` | [secon2027_source_import_review.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_source_import_review.json) | `affaa79d662890ae0750ebb18ed9928f5d4a88807dd4f33de1425c16a82b653f` |
| `core_review` | [secon2027_supervisor_core_review.md](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_core_review.md) | `7f53e1fe9938f0c23efb4ac712f12cc837eff88a262a85c2d5939cd2787287ea` |
| `environment_review` | [secon2027_supervisor_environment_review.md](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_environment_review.md) | `bad5600f6a752ce61151c5b5131ac2d285d6b75388e283a887ab15adac3155ca` |
| `runner_review` | [secon2027_supervisor_runner_review.md](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_runner_review.md) | `ee99e60b2bddce9c74366784e6231b21bf03ad62712b9f6a27eef13518df6f68` |
| `algorithm_review` | [secon2027_supervisor_algorithm_spec_review.md](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_algorithm_spec_review.md) | `b66a377abe91de1aa9d5c01cfbd7dc05f53fb3c37e377fd2f5f1b3367f94698a` |
| `freeze_review` | [secon2027_supervisor_formal_freeze_review.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_formal_freeze_review.json) | `e3b222528e64d31e9139bbf54562e1d147a29c0b833801f360ad4d74518b5ea8` |
| `raw_review` | [secon2027_supervisor_formal_raw_review_verified.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_formal_raw_review_verified.json) | `9dadbb649d49e3d62b6a8ba556a21f00cbd36407a4b430d92d6ce6733685907a` |
| `raw_explanation` | [secon2027_supervisor_formal_raw_review.md](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_formal_raw_review.md) | `54079ff32382070f524a4f99607f876b75ca23e11c8f44546258c7a720982e87` |
| `exposure_review` | [secon2027_supervisor_formal_exposure_review.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_formal_exposure_review.json) | `1cec389f560eabcbf2c6c41da8af8cbeacfc6f53950d3314849d2a309b0446c2` |
| `statistics_review` | [secon2027_supervisor_formal_statistics_review.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_formal_statistics_review.json) | `6aa0894375cbcb78e489eaed547a62680774ccb21a4e385e580f03173324196d` |
| `archive_review` | [secon2027_supervisor_formal_archive_review.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_formal_archive_review.json) | `8730d7a9f389e33e1031b8d087cac9465443fbc3a6a933980ed8c39631cd9275` |
| `archive_explanation` | [secon2027_supervisor_formal_archive_review.md](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_formal_archive_review.md) | `000f39dc0671c164685e573a61a1a821bc917428995ee74869ff5744d6471846` |
| `pilot_archive_review` | [secon2027_supervisor_pilot_archive_review.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_pilot_archive_review.json) | `3cc170654dfcc10c3e9667e13ae068bd3e5b6caed894ceb409ef6dd391e4574f` |
| `p0_archive_review` | [secon2027_supervisor_archive_restore.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_archive_restore.json) | `213c475838dc6d13693b18d03f54cccfc6ed9608966272b5f34dc620027fcbe4` |
| `documents_review` | [secon2027_supervisor_final_documents_review.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_final_documents_review.json) | `7263a726528218fdee990e5786300a99aec028d786e1f462d3d801b6b28cac9c` |
| `release_review` | [secon2027_supervisor_final_release_review.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_final_release_review.json) | `c6de4b94c8c3ffa0156c6b26c723018bd50a7aceea430f1f6d5930cbec41acfa` |
| `figures_review` | [secon2027_supervisor_final_figures_review.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_final_figures_review.json) | `7ed4cd26d2bb3f46e47513230dc2d0cfad6e4c965784da3f4f824964666ca2b7` |
| `pdf_review` | [secon2027_supervisor_final_pdf_review.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_final_pdf_review.json) | `4ae88bfc9a4db115dd8b4dad8bc26199f5ce1b9a72c232662b0e86a1f79e0128` |
| `original_reads` | [secon2027_supervisor_original_reads.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_original_reads.json) | `3997d144ab27b5938c43c15a8f88de96df5815b700dba8c0393a02ae91499b67` |
| `import_ledger` | [source_import.json](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/docs/research/secon2027_provenance/source_import.json) | `37620cff8b20821f882f678166cd625eb665d903d40d86c3ff4aab923c7eba63` |
| `original_status` | [original_status.txt](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/docs/research/secon2027_provenance/original_status.txt) | `68c6595cdeb5e205cb955a3f62f5d7bf0b72df879fed174a71498aef3d2c46ff` |
| `historical_inventory` | [historical_seed_inventory.json](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/docs/research/secon2027_provenance/historical_seed_inventory.json) | `7fb7feba9c27189a6ebed58bff8a1e4faf5e2d42eaa1ae78705504f78e626df0` |
| `legacy_registry_import` | [legacy_registry_import.json](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/docs/research/secon2027_provenance/legacy_registry_import.json) | `bda4e2062acc2dad43ebf47a0064b3271211f25314d81f0e483eb985eb313de4` |
| `checkpoint` | [secon2027_checkpoint.md](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/docs/research/secon2027_checkpoint.md) | `262a35f97304c7d5839a50c37dc388ecb27c2af5dae09a6b941141261d92377c` |
| `official` | [secon2027_official_requirements.md](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/docs/research/secon2027_official_requirements.md) | `426743c4ac6be6bd7fe0aeb35d428381a41f81f0b14b96ea7eb84bc613178e0a` |
| `checklist` | [secon2027_submission_checklist.md](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/docs/research/secon2027_submission_checklist.md) | `b8251db93690f450a951f90a42e531585e8f58ad4ea01c0c6719232505e3e142` |
| `fidelity` | [secon2027_baseline_fidelity.md](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/docs/research/secon2027_baseline_fidelity.md) | `72be01ff3ec42ba2797847f453e9debfa113df2cfa555cd117842b1f8ea69775` |
| `algorithm` | [secon2027_algorithm_spec.md](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/docs/research/secon2027_algorithm_spec.md) | `977c3ffef6c63642f2c7c0b6c7346489d2677b6b288b67653b8f7e672bb0fe30` |
| `reproduce` | [secon2027_reproduce.md](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/docs/reproducibility/secon2027_reproduce.md) | `d5b08dcc5210e5a8fe4d0d4929aa30f81742d7c730bdc540342daff9bbf50250` |
| `task_plan` | [task_plan.md](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/task_plan.md) | `7566850d7a70b1ebd823bba5a469fb361fee69f0f4d7484ff9ed19e2f7cedbeb` |
| `progress` | [progress.md](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/progress.md) | `d413d562df8518ad90faca4980b15f33ff7e0a71a4d9be2288df826d6fafe1e1` |
| `findings` | [findings.md](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/findings.md) | `6f57fb56ced671ebaa5397f1f5b0930ab87ea509e4474aabfe6688afde712c4e` |
| `registry` | [seed_registry.json](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/configs/secon2027/seed_registry.json) | `2b15e5ad71a34f08780817e5a0191d1124b09d0c08711350e006d27d88a60923` |
| `schema` | [matrix.schema.json](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/configs/secon2027/matrix.schema.json) | `374206bf05090bfcba70932ae0103ae0b4975b12af2212c2c4cbc4ccaf57f436` |
| `formal_plan` | [formal-v1.json](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/results/secon2027/plans/formal-v1.json) | `e738c34f726718027c46ff832aea8ca1bb095fa1e4a9cb5c8d25f271012e4052` |
| `tests_command` | [frozen-test-command.json](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/results/secon2027/gates/formal-v1/frozen-test-command.json) | `1a12635df587fe5972122e9c32614abd72defd80ba6ad7a871eb131cbb994d8e` |
| `tests_log` | [frozen-tests.log](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/results/secon2027/gates/formal-v1/frozen-tests.log) | `3aae292eb2fe70143cb8f20d4a9cf5ef5d18755c31f564b7fb0171c5a4200e08` |
| `closeout_tests` | [closeout-prepromotion-tests.json](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/results/secon2027/gates/formal-v1/closeout-prepromotion-tests.json) | `b6ddcd2188e0cdfbb718aad64870387652be57c91bc4e76e0f2f7a172a042bc2` |
| `closeout_inputs` | [closeout-tested-inputs.json](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/results/secon2027/gates/formal-v1/closeout-tested-inputs.json) | `20195ffc0a15e8885e26053e7b9938dc1a29dc0416ccdd2a17dd5506cd06ca6a` |
| `preservation` | [icc-preservation-check.json](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/results/secon2027/gates/formal-v1/icc-preservation-check.json) | `f8f9aed78bfcc1a779abc6761a3803368cf61647592e85d3e8e33563e0bc7c50` |
| `pause` | [administrative-pause.json](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/results/secon2027/gates/formal-v1/administrative-pause.json) | `84c11038a3f2aa59e46d4129c4b292a7a64a30f5e257a7ba129f6246093f603f` |
| `determinism` | [deterministic-replay.json](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/results/secon2027/gates/p0-v3/deterministic-replay.json) | `469b10febbcf05c024be0b3caf25b8de9d79421e132f2b840b51b37c1fcb7704` |
| `runner` | [secon2027_experiment.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tools/secon2027_experiment.py) | `6908c859bade6aec9aebf8f9231c76ae5aebdd347d9791d3ddda47f5ceebbb51` |
| `cpr_runner` | [run_cpr_experiment.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tools/run_cpr_experiment.py) | `d43dcfa30eda47af2a40e99f429f21b5815c6fac97d6e90d161a37b63b96019f` |
| `external` | [run_cpr_external_comparison.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tools/run_cpr_external_comparison.py) | `c4c1a38fe9393296392cb1cffa7f2958a46e4cba77aa5cf64a9a4beea5e73443` |
| `scenario` | [secon2027_scenarios.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tools/secon2027_scenarios.py) | `d83ebbf9f57a448c220a32f452f3e6e9bffe4a40580acd6f6e11909ddc25d061` |
| `simulator` | [lora_mesh_sim.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/lora_mesh_sim.py) | `e80beb763e3f63bccfc13d15a27275de432138f6774e56d3649c9f8bc43f4d01` |
| `cpr` | [meshecho_cpr.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/meshecho_cpr.py) | `c7e24fdfdbbdf5b27d2da5dba7ced73ba6d8c2a3178d3197bb202b5409067d8e` |
| `drc` | [meshecho_drc.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/meshecho_drc.py) | `db1fca8012eb1225c7a77385d2b121be5c04c4bf99264e4ceec4b0acc907019e` |
| `version` | [VERSION](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/VERSION) | `dcf91fe3646ed2f0eb3f3a33c37e4477b8089c2198d87b9665690bebb06950d0` |
| `requirements` | [requirements.txt](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/requirements.txt) | `161921405bccbde3032c9026394689d2ab1b0011f057304e1a738e455e8c877f` |
| `paper` | [main.tex](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/paper/secon2027/main.tex) | `48d3d1c2ec8f4cbf81cbfb48ff270ed7ed38d4ff1f88bc7294715462325d9b14` |
| `pilot_incident` | [incident.json](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/results/secon2027/gates/pilot-v1/incident.json) | `fea89706823a66f05380b94bb69f15113b816fa7b8b63fda8ab372f4e17c3c60` |
| `release_map` | [secon2027_release_map.md](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/docs/project-management/secon2027_release_map.md) | `a3097345ec1fd6df6fda34580c7b0a8f70a43fd712511fbbed7d0668726f306d` |
| `mechanisms` | [secon2027_formal_mechanisms.md](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/docs/results/secon2027_formal_mechanisms.md) | `2aa78f87bd03ec297931663c8b3328a468519643598009c9cdf5081faf777441` |
| `test_meshecho_cpr` | [test_meshecho_cpr.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tests/test_meshecho_cpr.py) | `d51272066cc5f69ab80fe6871e16aa4dd240aa7323490df8e99b8ce25149a689` |
| `test_meshecho_cpr_controller` | [test_meshecho_cpr_controller.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tests/test_meshecho_cpr_controller.py) | `ed029a67a85bc1ecb88a8144054397a323a452b2b8e2d7e0e4fe3d2ee9f127fc` |
| `test_meshecho_drc` | [test_meshecho_drc.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tests/test_meshecho_drc.py) | `c7cc07a0b6849fca0afcbf7acecc1d1c9bd7d0177f9383063488a94d0f123821` |
| `test_meshecho_drc_controller` | [test_meshecho_drc_controller.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tests/test_meshecho_drc_controller.py) | `cccceb95c1713881fb679dc5265bd03a5a72cf4800959aa93ed926fb52bfb784` |
| `test_cpr_experiment` | [test_cpr_experiment.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tests/test_cpr_experiment.py) | `88dbfc23796c4793fa013fc38e8691c4d7cb1fcbcd49210c944fcaae8c306b83` |
| `test_cpr_external_comparison` | [test_cpr_external_comparison.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tests/test_cpr_external_comparison.py) | `85b7d2105f242275101fecadc9e302d4a6204f2de4668e1f0ef2107442cc4363` |
| `test_common_ack_baselines` | [test_common_ack_baselines.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tests/test_common_ack_baselines.py) | `aee9e3f139cb0b592bb4b7d365a8b0f59d76b1d3827ca3572bd99dfd0e2c8ad6` |
| `test_secon_cpr_correctness` | [test_secon_cpr_correctness.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tests/test_secon_cpr_correctness.py) | `704ba2e50a28d4e2fede8d7b1fa788fd08ba6e519a6b12f76c648f813244d18c` |
| `test_secon_experiment` | [test_secon_experiment.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tests/test_secon_experiment.py) | `81e14482965795720e43005f920b3cddceb9b8b19acbbbc7ca623a3e8af5c6ac` |
| `test_secon_scenarios` | [test_secon_scenarios.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tests/test_secon_scenarios.py) | `2262eadbcdd357d572138487b33d9bbf4f4759faceec1de9cb60062eb6a5b047` |
| `test_secon_orchestration_review` | [test_secon_orchestration_review.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tests/test_secon_orchestration_review.py) | `d553466584878a1ab8befc48539765597dab803a93502c9bf9f14283d24008d1` |
| `test_secon_frozen_worker` | [test_secon_frozen_worker.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tests/test_secon_frozen_worker.py) | `b46cd2651599c86149a63c953e800191040222b0463e2f28a07943c9b8e23af9` |
| `test_secon_analysis` | [test_secon_analysis.py](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/tests/test_secon_analysis.py) | `d9b44b32550ba43cd37d473c32c2c6d31aa1b3eed97845fbafc033b4cf5234f9` |
| `snapshot_descriptor` | [snapshot.json](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/results/secon2027/snapshots/63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee/snapshot.json) | `4bffa2f4964086a553d9f6280cd371e8299a9b7a90baeeb11f47d53657de226e` |
| `frozen_contract` | [secon2027_experiment_contract.md](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/results/secon2027/snapshots/63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee/source/docs/research/secon2027_experiment_contract.md) | `0db4fc2e724f441e190693e3f8d37b7912e2d4baa5555515c6f132481f309eff` |
| `historical_contract` | [meshecho_cpr_smoke_contract_20261006.md](/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/docs/research/meshecho_cpr_smoke_contract_20261006.md) | `361e1f039371bf7cdba539c051688a2423e675be06df04d35c2d57604aed5f2b` |
| `matrix` | [secon2027_acceptance_matrix.md](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_acceptance_matrix.md) | `289d14c05216e243e19d9fa49baf418a756b243aa391bb151a1acb0c1771d529` |

主矩阵读取SHA-256：`289d14c05216e243e19d9fa49baf418a756b243aa391bb151a1acb0c1771d529`；本分审未修改主矩阵。历史raw审查的39项ACK断言差异属于审查脚本错误，已通过保留原记录及760个ACK定向复核关闭；本报告引用verified JSON，未把旧保留报告的discrepancies当作当前模拟器缺陷。

A02已由原执行turn的成功工具读取记录与source-import身份闭环；A03/A04/A05/B12为最终收尾链仍需根监督并入。未发现需要新研究seed、算法修改或重跑正式实验的基础证据反例。

补测临时副本已清理，完整checker源码/命令/输出仍保存在JSON；最终结构核查确认40个准确ID、72项当前证据hash、29项补测及13个冻结测试文件身份全部匹配。
