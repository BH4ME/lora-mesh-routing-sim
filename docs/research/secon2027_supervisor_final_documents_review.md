# SECON 2027 最终文档与论文源码独立复核

读取完成时间：2026-11-04T10:17:19.071829+00:00。执行树：`/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo`。

范围：G01–G06、G10–G14、G16、I01–I03、J01；G13 数学/引用/匿名源码。只读执行树；只将本报告和 JSON 写入 canonical。没有新检索、改稿、编译、仿真或测试。PDF 逐页、字体、元数据由 root 对最终导出文件验收。

**结论：8 项通过、6 项待最终闭环、2 项条件不适用。未发现需要改算法、重跑研究种子或更换文献的实质问题。G13 的通过严格限于下列源码快照；不是最终 PDF 验收。**

| ID | 状态 | 证据与剩余事项 |
| --- | --- | --- |
| G01 | 待验 | 当前18:06顶栏已将正式760 runs与旧历史段区分，保存快照/版本/命令/事故/下一动作；但仍含promoted fixture71995、push73342、clean restore等运行中状态。最终交付须更新已退出会话、当前HEAD/远端、最终PDF/包与下一动作。 |
| G02 | 通过 | 冻结合同实际SHA与formal plan一致；正式节包括问题、指标、760键、20 seeds、三场景、controls、deadline/drain轴、bootstrap、失败/负结果/资源规则。先冻结后执行时序成立；开头过期文字由保留原字节的事后勘误透明解释，不能改写原合同。 |
| G03 | 通过 | registry机器记录20个formal seeds全部exposed；760 planned keys与plan严格相等，760 started+760 completed历史，760产物路径，无development seed重叠。顶层frozen-before-exposure是历史冻结事件，非声称当前未暴露。完整原始审计复用已通过独立报告。 |
| G04 | 通过 | 实体matrix与plan内嵌matrix逐对象相等；38 cells各20键，480 main+120 controls+160额外deadline，30s复用S2-matched；schema/arms/环境/统计/预算/失败规则齐全。 |
| G05 | 通过 | 四模型机制/参数/default与matched/ACK/重传/缓存/帧长/信息可见性/遗漏项明确。Meshtastic和MeshCore官方release/commit/file hashes已记录；承认官方retry与learning而模型省略，不冒称产品性能。 |
| G06 | 通过 | 规格A1–A12给出本地输入、state/FSM、wire/ToA、commit/start、预算/上界假设、缓存并发、clean controls、状态容量和O(NK)扫描边界；23个具名测试在formal saved source均存在。主要预算/取消规则抽读代码匹配。规格主文锚定早期snapshot并记录import修复；最终formal继承关系由冻结审查/plan成立，建议追加formal snapshot导航但勿改冻结来源。 |
| G10 | 待验 | 官方规则/未知时区与注册节点/未提交/作者信息/AI声明边界已记录；checklist仍把已完成760、analysis、raw restore列未完成，最终PDF页数/字体/视觉/匿名/标题一致与closeoutSHA待root绑定实测。不能以编译成功替代。 |
| G11 | 通过 | 独立固件状态文件明确未做新native/board/RF/功耗，本轮无已识别多节点或仪器；保留0.1.4和历史未解问题，不用旧build/native证明Python/RF等价。满足披露。 |
| G12 | 待验 | release map真实区分tested2.1.27/2.1.28/2.1.29与promoted2.1.28/2.1.29/2.1.30；记录失败pilot和两次已验证发布。第三轮研究数据/166输入映射/parts commit已记，但最终closeout commit与远端SHA尚未在本文件闭环。 |
| G13 | 通过 | 仅本次读取的源码快照通过：独立SECON主文/六章节/向量时序图/4组结果图/Bib与生成器齐全；11组编号公式与规格/已冻结统计口径一致，27项文献全部正文实引，38次条目引用，无孤立/未定义/重复key，无MASS/虚构RF。保留高负载negative result及baseline fidelity限制。最终PDF由root另验。 |
| G14 | 待验 | 源码匿名子项通过：Anonymous authors、空pdfauthor、无姓名/学校/邮箱/用户目录/作者仓库链接；私有作者说明在内部checklist为Zu Gao/Zhi Quan/Shenzhen University，无无外部资助句。AI-assistance的Acknowledgment段不含身份。完整条目仍需root对同一最新PDF文本/元数据/注释/链接实查。 |
| G16 | 待验 | 内部可恢复包和匿名审稿材料的分离策略已写明；raw11parts/全包/14667成员/760 saved-source audit已有独立恢复证据。最终analysis/paper包与可恢复发布位置、PDF可见链接和匿名artifact实际边界待closeout；不能将内部含身份路径的raw包直接称匿名材料。 |
| I01 | 不适用 | 条件P2本轮未承担新固件变更/native/板级gate；仅保留历史记录并明确非当前验证，不阻断仿真主线。 |
| I02 | 不适用 | 本轮没有RF或功耗实测，故节点/天线/仪器/功耗实验验收不适用，论文如实披露。 |
| I03 | 通过 | 论文/方法/fidelity/firmware状态均区分行为模型、Python仿真、历史原型和官方产品；未声称RF认证、真实产品公平硬件性能或整机电池优势。 |
| J01 | 待验 | pilot实测驱动760-run预算与2倍余量已完成；正式实测4423.191694785 summed worker seconds、最大RSS398163968B、raw7098305927B、archive475828160B及恢复570.836s已记。剩余PDF/最终包/上传/复核的耗时和磁盘预算/关键路径尚应在最终checkpoint明确，保留全部必需项，不扩展可选RF/扫描。 |

## 数学、文献与匿名源码复核

- 11 组编号公式：deadline/两成功率、全物理发送成本、完整wire长度、commit/start、route/flood admission budgets、fits、source-stage上界、off-path ACK取消、seed配对差值/几何airtime比值。预算明确只是本地估计，不声称端到端保证；source三次上界不外推为全网三次；未把相关重传视作独立成功乘积。
- 条件规则、禁止初始flood后自动重复恢复、READY/generation检查、no-repeat nominal slot、ACK确认和cache mutation分开、过时timeout不覆盖新确认、off-path及未commit取消，与规格和代码抽读相符。23个具名回归测试在formal snapshot均存在；测试实际通过证据复用冻结审查。
- 27个Bib键均正文引用，共38次条目引用；无未引用/未定义/重复键。24项学术文献与原已核验ICC条目字节相同；两项旧官方文档中MeshCore改为pin版本，新增Meshtastic官方pinned源码，共3项官方文档/源码。没有引用未发表MASS。
- 正文保留S3负结果、行为模型省略官方重试/学习、未RF校准、仅descriptive unadjusted CI等边界。来源不替CPR自定义公式或硬件证据背书。
- 源码扫描姓名、Shenzhen、BH4ME、本地用户路径、邮箱和未资助句无命中；作者只在内部submission checklist。AI披露段虽名Acknowledgment，但不含个人/单位/资助身份；最终PDF仍待实际扫描。

## 冻结与当前运行记录

- 合同实体SHA：`0db4fc2e724f441e190693e3f8d37b7912e2d4baa5555515c6f132481f309eff`，与formal plan绑定一致。
- Plan逻辑SHA：`5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0`；source身份：`63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee`，tested2.1.29。
- Registry20 seeds 2027100–2027119均exposed；760planned keys等于plan，history恰为760 started/760 completed。相同seed对应其余预定arms未被错误阻断，未合并default/matched为n40。
- 合同开头development文字是已公开记录的历史编辑矛盾，事后erratum日期与首次运行/43完成的次序如实记录。本次不改冻结合同。

## 读取时实体文件 SHA-256

以下主要文件及所有纸稿/图表资产的完整SHA、字节数、mtime在同名JSON中。文件继续编辑时，以hash区分审核对象。

| 文件 | SHA-256 |
| --- | --- |
| `docs/research/secon2027_checkpoint.md` | `262a35f97304c7d5839a50c37dc388ecb27c2af5dae09a6b941141261d92377c` |
| `docs/research/secon2027_algorithm_spec.md` | `977c3ffef6c63642f2c7c0b6c7346489d2677b6b288b67653b8f7e672bb0fe30` |
| `docs/research/secon2027_baseline_fidelity.md` | `72be01ff3ec42ba2797847f453e9debfa113df2cfa555cd117842b1f8ea69775` |
| `docs/research/secon2027_submission_checklist.md` | `b8251db93690f450a951f90a42e531585e8f58ad4ea01c0c6719232505e3e142` |
| `docs/project-management/secon2027_release_map.md` | `a3097345ec1fd6df6fda34580c7b0a8f70a43fd712511fbbed7d0668726f306d` |
| `configs/secon2027/seed_registry.json` | `2b15e5ad71a34f08780817e5a0191d1124b09d0c08711350e006d27d88a60923` |
| `configs/secon2027/experiment_matrix.json` | `8cc1d79ddb1a91007bd124c1c1fa43f74b667657b024521882dde1fabcd034a0` |
| `paper/secon2027/main.tex` | `48d3d1c2ec8f4cbf81cbfb48ff270ed7ed38d4ff1f88bc7294715462325d9b14` |
| `paper/secon2027/methods.tex` | `3f83c893cba6defd213de5cbe01ab54af615cc00e98eeb8cc7bb277a481ed5be` |
| `paper/secon2027/evaluation.tex` | `5937712fcce08e2d10c02f90689518064e4b9a565f2499e5f06b76f6001ff19d` |
| `paper/secon2027/results.tex` | `bdf6253411123237995935b0f3a7780fd7743dc4e75a428d4a4c9786146dff3b` |
| `paper/secon2027/references.bib` | `b16a95a04468dcdb20749564c218ec130956b8575064bd761c526bf990a6e6d3` |

## 最终收尾要求

1. 用最终状态更新checkpoint与submission checklist；保留历史正文但明确最新导航，移除当前摘要中已退出会话的“运行中”误导。
2. root将最终PDF源文件/导出文件hash、编译、页数、字体、逐页可读性、匿名文本/metadata/链接检查落盘，才能关闭G10/G14及另行负责的G15。
3. 绑定最终analysis/paper可恢复包、限定提交和成功push后的远端fullSHA；不能仅凭raw分片本地commit或旧2.1.29发布关闭G12/G16。
4. 最终checkpoint补剩余PDF/打包/上传/核验时间与磁盘预算，完成J01；不为修饰文档改冻结科学输入或重跑正式数据。

读取期间变化文件：docs/research/secon2027_claim_evidence.md, paper/secon2027/FIGURES.md。本报告不覆盖写入之后的新版本。
