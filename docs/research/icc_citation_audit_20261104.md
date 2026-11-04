# ICC 参考文献与正文引用核验表

核验日期：2026-11-04。当前稿由 5 项扩充到 26 项：23 篇学术论文、1 篇经典路由书章、2 项官方项目文档。所有条目均在正文以 `\cite{...}` 实际使用；未使用 `\nocite`。

## 如何核验

- 出版身份：逐项对照 Crossref、出版社/会议或作者记录，检查题名、作者、DOI、年份、卷期和页码。
- 论断依据：阅读摘要或相关全文段落；全文和摘要的阅读范围在分项报告中明确区分。
- 被引情况：24项学术来源均有 OpenAlex 非零被引记录，并取得至少一条合理的具体 citing-work 关系。这里验证的是数据库关系，不声称逐一读取所有施引论文的参考文献页。
- 引用用途：每项都对应本文中的具体背景、方法、公式解释或适用边界；外部论文不替CPR自己的实现或仿真结果背书。

下表计数是 OpenAlex 在核验日返回的索引快照，包含覆盖差异与可能噪声，不是Google Scholar总数，也不是质量/中稿概率指标。Trickle查询中的一条明显年代错误记录已排除，保留合理的Contiki引用关系。

## 正文引用清单

| 编号 | 来源 | 正文用途 | OpenAlex被引快照 |
|---:|---|---|---:|
| 1 | [A Study of LoRa: Long Range & Low Power Networks for the Internet of Things](https://doi.org/10.3390/s16091466) | LoRa背景、标准符号数/ToA公式（eq:lora-toa） | 1500 |
| 2 | [Do LoRa Low-Power Wide-Area Networks Scale?](https://doi.org/10.1145/2988287.2989163) | 空口占用、并发与扩展性背景 | 838 |
| 3 | [Low Power Wide Area Network Analysis: Can LoRa Scale?](https://doi.org/10.1109/lwc.2016.2647247) | 负载/干扰与单网关容量研究边界 | 731 |
| 4 | [Multi-Hop and Mesh for LoRa Networks: Recent Advancements, Issues, and Recommended Applications](https://doi.org/10.1145/3638241) | 多跳/mesh研究分类与定位 | 64 |
| 5 | [LoRaWAN Mesh Networks: A Review and Classification of Multihop Communication](https://doi.org/10.3390/s20154273) | relay/router架构区分 | 137 |
| 6 | [A high-throughput path metric for multi-hop wireless routing](https://doi.org/10.1145/938985.939000) | DATA/ACK双向损失及ETX定义 | 3383 |
| 7 | [Impact of LoRa Imperfect Orthogonality: Analysis of Link-Level Performance](https://doi.org/10.1109/lcomm.2018.2797057) | 不同SF不完全正交；固定SF7局限 | 394 |
| 8 | [When LoRaWAN Frames Collide](https://doi.org/10.1145/3267204.3267212) | 并发帧碰撞与捕获实验背景 | 85 |
| 9 | [Performance of Unslotted ALOHA With Capture and Multiple Collisions in LoRaWAN](https://doi.org/10.1109/jiot.2023.3280393) | 多个干扰帧与接收模型边界 | 19 |
| 10 | [Simulation of LoRa in NS-3: Improving LoRa Performance with CSMA](https://doi.org/10.1109/icc.2018.8422800) | LoRa仿真/CSMA方法先例，不能代替本模拟器校准 | 160 |
| 11 | [Scalability Analysis of Large-Scale LoRaWAN Networks in ns-3](https://doi.org/10.1109/jiot.2017.2768498) | ACK/downlink成本与确认成功率 | 349 |
| 12 | [Smart-Hop: Low-Latency Multi-hop Networking for LoRa](https://doi.org/10.1109/dcoss54816.2022.00014) | 低开销多跳、SF选择与延迟目标 | 12 |
| 13 | [Cost Effective Routing in Large-scale Multi-hop LoRa Networks](https://doi.org/10.1109/infocomwkshps54753.2022.9798302) | 低成本覆盖与能耗均衡的不同目标 | 12 |
| 14 | [Improving the Capacity of a Mesh LoRa Network by Spreading-Factor-Based Network Clustering](https://doi.org/10.1109/access.2019.2898239) | SF聚类及airtime平衡 | 107 |
| 15 | [A Minimalistic Distance-Vector Routing Protocol for LoRa Mesh Networks](https://doi.org/10.1109/access.2024.3443605) | ToA路由度量与距离向量方法 | 15 |
| 16 | [Implementation of a LoRa Mesh Library](https://doi.org/10.1109/access.2022.3217215) | ESP32上主动mesh协议实现 | 47 |
| 17 | [LoRaHop: Multihop Support for LoRaWAN Uplink and Downlink Messaging](https://doi.org/10.1109/jiot.2023.3263630) | 双向LoRaWAN mesh与室外实现证据 | 34 |
| 18 | [Dynamic Source Routing in Ad Hoc Wireless Networks](https://doi.org/10.1007/978-0-585-29603-6_5) | 源路由、发现与复用的先行方法 | 8554 |
| 19 | [The broadcast storm problem in a mobile ad hoc network](https://doi.org/10.1145/313451.313525) | 洪泛冗余、竞争与碰撞 | 3162 |
| 20 | [Trickle: a self-regulating algorithm for code propagation and maintenance in wireless sensor networks](https://openalex.org/W2058632086) | 监听一致信息后抑制的先行机制 | 1150 |
| 21 | [ExOR](https://doi.org/10.1145/1080091.1080108) | 机会转发/ACK协调的先行机制 | 1356 |
| 22 | [Meshtastic mesh algorithm](https://meshtastic.org/docs/overview/mesh-algo/) | 产品机制与简化模拟基线边界 | 不适用 |
| 23 | [MeshCore FAQ](https://github.com/meshcore-dev/MeshCore/blob/main/docs/faq.md) | 路径学习、重试与flood fallback的产品文档 | 不适用 |
| 24 | [Cross-Layer Combining of Adaptive Modulation and Coding With Truncated ARQ Over Wireless Links](https://doi.org/10.1109/twc.2004.833474) | 有限ARQ的时延/可靠性取舍；非CPR预算出处 | 932 |
| 25 | [The β-factor](https://doi.org/10.1145/1460412.1460416) | 突发丢包动机；条件重试不假定独立 | 305 |
| 26 | [Some Guidelines and Guarantees for Common Random Numbers](https://doi.org/10.1287/mnsc.38.6.884) | 共同场景仿真的方差减少方法及条件 | 188 |

## 访问与误引防护

- IEEE Xplore本轮访问出现空响应/访问限制，不能据此认定已通过深圳大学机构订阅获取全文。开放作者稿、机构库、PMC与索引摘要实际可用。
- Meshtastic官网本轮重取超时，保留先前已核验文档和原访问日期；MeshCore官方FAQ本轮成功读取。两项均不冒充论文。
- MLoRa标注为IEEE INFOCOM **Workshops**；When LoRaWAN Frames Collide标注为ACM **WiNTECH workshop**。
- Trickle未核实到DOI，留空；不编造标识符。Wong使用正式2024年出版信息。
- Bor修正版与旧索引摘要的容量数字不同，本文仅引用方法背景，不搬用有版本冲突的密度数值。
- LoRa空口时间表达式引用Augustin全文式(1)–(3)；自定义wire header、CPR状态机、预算系数和本文恒等式仍归于本文实现/推导。

## 可追溯材料

- [PHY核验](icc_literature_20261104/phy_sources.md)
- [多跳方法核验](icc_literature_20261104/multihop_sources.md)
- [路由与抑制核验](icc_literature_20261104/routing_sources.md)
- [有限重传、突发丢包与配对方法核验](icc_literature_20261104/method_sources.md)

## 最终检查

- 当前TeX有26个唯一正文引用键、37次条目引用；文末26项和Bib文件26项与首次引用顺序完全一致。
- 23个DOI与核实来源逐项匹配；Trickle无已核实DOI，2个官方项目文档不用论文DOI。
- 无未定义文献、无未引用的文末条目、无重复标签、无nocite。作者仍为Zu Gao、Zhi Quan。
- 36组编号公式和既有结果图与本轮修改前逐字一致；本次补的是出处、相关工作和归因解释，不修改公式或实验值。
- 内置 `compile_latex_document` 编译同一TeX成功；定向 `git diff --check` 通过。未另行导出PDF或宣称页数/视觉版式验收。
- 修改位置：[当前论文](../../paper/icc2027/icc2027_lora_mesh.tex)、[BibTeX文献库](../../paper/icc2027/references.bib)。
