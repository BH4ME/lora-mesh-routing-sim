# ICC LoRa 多跳/mesh 文献核验与正文插入建议

核查日期：2026-11-04。本文件由 AI 辅助检索、读取摘要/全文及人工式逐条核对生成；不是系统综述。仅编辑本研究记录目录，未改主 TeX/Bib。

## 方法与核验边界

从已有候选 DOI 和 Crossref 关键词检索出发，核实 Crossref 的作者、标题、venue、年份、页码；随后读取 OpenAlex 的重建摘要。Cotrim 2020 另读取 PMC 开放全文的分类与拓扑章节。每次网络请求 timeout=22 s。保留原始 JSON、可读全文/页面及访问结果。

8 篇推荐文献均有正被引计数，且通过 OpenAlex `filter=cites:W...` 取得真实 citing-work 记录；这里核验的是数据库引用关系，并未逐一打开 citing paper 的参考文献列表。计数不是 Google Scholar 计数，也不是录用概率指标。`cited_by_count` 与 cites 检索结果总数偶有差异，以下分别记录，不混为同一统计口径。

本机当前网络下：Crossref/OpenAlex 可访问；Cotrim PMC 全文 HTTP 200；ACM 返回403；UMS高校作者PDF返回401；UPCommons返回418；IEEE PDF返回418或页面202空正文；KU Leuven跳转搜索应用外壳。未确认当前网络是否经深圳大学订阅/代理，因此不声称“校内可访问全文”。访问实测详见 multihop_access_checks*.json。

## 推荐文献一览

| Cite key | 年份 / venue | OpenAlex cited_by_count | cites 查询记录总数 | Crossref is-referenced-by-count |
|---|---|---:|---:|---:|
| `wong2024multihop` | 2024 / ACM Computing Surveys | 64 | 62 | 64 |
| `cotrim2020lorawanmesh` | 2020 / Sensors | 137 | 135 | 120 |
| `pueyo2024minimalistic` | 2024 / IEEE Access | 15 | 14 | 11 |
| `sole2022implementation` | 2022 / IEEE Access | 47 | 47 | 44 |
| `zhu2019improving` | 2019 / IEEE Access | 107 | 106 | 98 |
| `ahmar2022smarthop` | 2022 / 2022 18th International Conference on Distributed Computing in Sensor Systems (DCOSS) | 12 | 12 | 10 |
| `feng2022cost` | 2022 / IEEE INFOCOM 2022 - IEEE Conference on Computer Communications Workshops (INFOCOM WKSHPS) | 12 | 12 | 10 |
| `tian2023lorahop` | 2023 / IEEE Internet of Things Journal | 34 | 33 | 34 |

## 1. Multi-Hop and Mesh for LoRa Networks: Recent Advancements, Issues, and Recommended Applications

**作者：** Andrew Wei-Loong Wong; Say Leng Goh; Mohammad Kamrul Hasan; Salmah Fattah.

**出处：** ACM Computing Surveys, vol. 56, no. 6, pp. 1-43, 2024. DOI: [10.1145/3638241](https://doi.org/10.1145/3638241).

**用途优先级：** 高：近年综述、定位创新边界.

**读取与证据：** 已读 Crossref 出版商提供的摘要，OpenAlex 摘要一致；未取得全文。 评述2015–2023年的LoRa多跳/mesh仿真与实测研究，并按能耗、并发接入/占空比、路由、安全分类；路由分类含proactive/reactive/hybrid。

**元数据/计数来源：** [Crossref](https://api.crossref.org/works/10.1145/3638241)；[OpenAlex](https://api.openalex.org/works/W4390002238)；获取日期2026-11-04。

**正文插入位置：** Related Work第一段后；Introduction的multihop背景句也可引用。

```latex
Recent surveys organize LoRa mesh research around routing, energy use, concurrent access, and duty-cycle constraints, with both simulation and deployment evidence represented~\cite{wong2024multihop}.
```

**不能外推：** 只支持领域分类与研究范围；不证明CPR首次提出ACK恢复，也不证明reactive在所有配置下优于proactive。OpenAlex year=2023与Crossref冲突，采用Crossref正式线上2024-01-22 /卷期2024-06-30。

**已核验被引记录举例：**

- LoRa Communication for Agriculture 4.0: Opportunities, Challenges, and Future Directions — 2024; https://doi.org/10.1109/jiot.2024.3486369
- Federated Learning With Small and Large Models With Privacy-Preserving Data Space for Holographic Internet of Things in Consumer Electronics — 2025; https://doi.org/10.1109/tce.2025.3573033

**原始摘要证据：** multihop_openalex_10.1145_3638241.json；已读范围与适用论断见本节。

## 2. LoRaWAN Mesh Networks: A Review and Classification of Multihop Communication

**作者：** Jeferson Rodrigues Cotrim; João Henrique Kleinschmidt.

**出处：** Sensors, vol. 20, no. 15, pp. 4273, 2020. DOI: [10.3390/s20154273](https://doi.org/10.3390/s20154273).

**用途优先级：** 高：LoRa与LoRaWAN、多跳角色区分.

**读取与证据：** 已读Crossref摘要及PMC全文的多跳方案、relay/router分类、拓扑章节。 传统LoRaWAN为single-hop star-of-stars；综述按中间设备功能、技术特点、拓扑分类多跳方案。全文区分relay-device、relay-gateway、router-device，说明不能把不同架构的mesh直接视为同一系统。

**元数据/计数来源：** [Crossref](https://api.crossref.org/works/10.3390/s20154273)；[OpenAlex](https://api.openalex.org/works/W3046834032)；获取日期2026-11-04。

**正文插入位置：** Introduction中说明LoRa substrate和Related Work第一段；用于限定baseline并非LoRaWAN标准扩展。

```latex
Multihop LoRaWAN proposals differ in the functions assigned to intermediate devices and in whether relaying occurs among end devices or gateways~\cite{cotrim2020lorawanmesh}.
```

**不能外推：** 不把所有LoRa mesh当作LoRaWAN；未直接阅读LoRaBlink原始文献，不能把综述转述当作LoRaBlink全文证据。

**已核验被引记录举例：**

- A Survey on LoRa for Smart Agriculture: Current Trends and Future Perspectives — 2022; https://doi.org/10.1109/jiot.2022.3230505
- Recent Advances in LoRa: A Comprehensive Survey — 2022; https://doi.org/10.1145/3543856

**原始摘要证据：** multihop_openalex_10.3390_s20154273.json；已读范围与适用论断见本节。

## 3. A Minimalistic Distance-Vector Routing Protocol for LoRa Mesh Networks

**作者：** Roger Pueyo Centelles; Roc Meseguer; Fèlix Freitag; Roger Baig Viñas; Leandro Navarro.

**出处：** IEEE Access, vol. 12, pp. 128941-128962, 2024. DOI: [10.1109/access.2024.3443605](https://doi.org/10.1109/access.2024.3443605).

**用途优先级：** 最高：路由度量、ToA、公平仿真最接近.

**读取与证据：** 已读OpenAlex完整摘要；出版社和UPCommons全文请求均被拒，未读全文。 提出minimalistic distance-vector routing及ToA metric；在FLoRa/OMNeT++中评估不同拓扑、负载、多SF配置的PDR/吞吐/延迟；多SF收益依赖负载和异构性，尤其饱和时吞吐变化明显。

**元数据/计数来源：** [Crossref](https://api.crossref.org/works/10.1109/access.2024.3443605)；[OpenAlex](https://api.openalex.org/works/W3197897949)；获取日期2026-11-04。

**正文插入位置：** Related Work新增route metric段；Common path and physical cost引出airtime accounting前。

```latex
Pueyo Centelles et al. evaluate a minimalistic distance-vector protocol with a time-on-air metric in FLoRa/OMNeT++, showing that routing and multi-SF performance depend on topology and traffic load~\cite{pueyo2024minimalistic}.
```

**不能外推：** 不能据该文证明本稿SF7配置覆盖所有LoRa设置，也不能把其ToA路由度量等同CPR的实际发送airtime记账。

**已核验被引记录举例：**

- Mobility-Aware LoRa Protocol for Reliable IoT Communications — 2025; https://doi.org/10.1109/access.2025.3649413
- Demo: Edge Federated Learning over a LoRa Mesh Network — 2024; https://doi.org/10.1109/sec62691.2024.00061

**原始摘要证据：** multihop_openalex_10.1109_ACCESS.2024.3443605.json；已读范围与适用论断见本节。

## 4. Implementation of a LoRa Mesh Library

**作者：** Joan Miquel Solé; Roger Pueyo Centelles; Fèlix Freitag; Roc Meseguer.

**出处：** IEEE Access, vol. 10, pp. 113158-113171, 2022. DOI: [10.1109/access.2022.3217215](https://doi.org/10.1109/access.2022.3217215).

**用途优先级：** 高：实物mesh、主动路由对照.

**读取与证据：** 已读OpenAlex完整摘要；UPCommons和IEEE PDF均返回418，未取得全文。 实现proactive routing的LoRa mesh library，通过邻居routing messages维护各节点routing table；在ESP32+single-channel LoRa的embedded boards测试，不要求LoRaWAN gateway。

**元数据/计数来源：** [Crossref](https://api.crossref.org/works/10.1109/access.2022.3217215)；[OpenAlex](https://api.openalex.org/works/W4312791581)；获取日期2026-11-04。

**正文插入位置：** Related Work：Meshtastic/MeshCore产品介绍之前的academic mesh implementation段；Scope用于解释实物验证尚缺。

```latex
Sol\'e et al. implement proactive LoRa mesh routing with neighbor routing messages and test the library on ESP32 boards equipped with single-channel LoRa radios~\cite{sole2022implementation}.
```

**不能外推：** 此为独立学术library，不是Meshtastic或MeshCore官方固件；摘要无可复核具体PDR，不附会数值；其硬件测试不代表本稿已有硬件证据。

**已核验被引记录举例：**

- Embedded federated learning over a LoRa mesh network — 2023; https://doi.org/10.1016/j.pmcj.2023.101819
- AlLoRa: Empowering environmental intelligence through an advanced LoRa-based IoT solution — 2024; https://doi.org/10.1016/j.comcom.2024.02.014

**原始摘要证据：** multihop_openalex_10.1109_ACCESS.2022.3217215.json；已读范围与适用论断见本节。

## 5. Improving the Capacity of a Mesh LoRa Network by Spreading-Factor-Based Network Clustering

**作者：** Guibing Zhu; Chun-Hao Liao; Theerat Sakdejayont; I-Wei Lai; Yoshiaki Narusue; Hiroyuki Morikawa.

**出处：** IEEE Access, vol. 7, pp. 21584-21596, 2019. DOI: [10.1109/access.2019.2898239](https://doi.org/10.1109/access.2019.2898239).

**用途优先级：** 中高：早期重要多SF airtime/容量工作.

**读取与证据：** 已读OpenAlex完整摘要；IEEE页面返回202空正文，未取得全文。 tree-based spreading-factor clustering将traffic分至不同SF子网，在保证连接性的同时平衡airtime及减少hop count；用仿真评估性能，另做real-chip experiment验证并行传输可行性。

**元数据/计数来源：** [Crossref](https://api.crossref.org/works/10.1109/access.2019.2898239)；[OpenAlex](https://api.openalex.org/works/W2913709008)；获取日期2026-11-04。

**正文插入位置：** Related Work的airtime/多SF段；Common path and physical cost的ToA动机；Limitations固定SF7之后。

```latex
Zhu et al. combine spreading-factor clustering with airtime balancing in multihop LoRa, evaluating network performance in simulation and parallel transmission feasibility on real radios~\cite{zhu2019improving}.
```

**不能外推：** 只支持SF/airtime设计与其证据类型，不能证明不同SF完全正交，也不证明其测试优于CPR或CPR优于它。2019为8篇中唯一2020以前的关键工作。

**已核验被引记录举例：**

- A Survey on Scalable LoRaWAN for Massive IoT: Recent Advances, Potentials, and Challenges — 2023; https://doi.org/10.1109/comst.2023.3274934
- A Survey on LoRaWAN Technology: Recent Trends, Opportunities, Simulation Tools and Future Directions — 2022; https://doi.org/10.3390/electronics11010164

**原始摘要证据：** multihop_openalex_10.1109_ACCESS.2019.2898239.json；已读范围与适用论断见本节。

## 6. Smart-Hop: Low-Latency Multi-hop Networking for LoRa

**作者：** Absar-Ul-Haque Ahmar; Wouter Joosen; Danny Hughes.

**出处：** 2022 18th International Conference on Distributed Computing in Sensor Systems (DCOSS), pp. 17-20, 2022. DOI: [10.1109/dcoss54816.2022.00014](https://doi.org/10.1109/dcoss54816.2022.00014).

**用途优先级：** 高：低开销多跳与延迟问题.

**读取与证据：** 已读OpenAlex完整摘要；KU Leuven链接返回搜索应用外壳，不能视为已读取论文全文。 Smart-Hop将multi-hop MAC与low-overhead routing结合，利用SF造成的range差异，减少高SF终端以降低data extraction时间，同时保持最高SF可达范围。

**元数据/计数来源：** [Crossref](https://api.crossref.org/works/10.1109/dcoss54816.2022.00014)；[OpenAlex](https://api.openalex.org/works/W4297818341)；获取日期2026-11-04。

**正文插入位置：** Related Work低延迟多跳段；CPR的duration budget前可对比研究对象。

```latex
Smart-Hop couples low-overhead multihop routing with spreading-factor-dependent range selection to reduce data-extraction latency~\cite{ahmar2022smarthop}.
```

**不能外推：** 摘要未说明本次可核实的具体实测数字，不能额外声称某PDR提升或相同deadline保证；其MAC/SF机制不同于本稿fixed-SF recovery。

**已核验被引记录举例：**

- Multi-Hop and Mesh for LoRa Networks: Recent Advancements, Issues, and Recommended Applications — 2023; https://doi.org/10.1145/3638241
- LoRaHop: Multihop Support for LoRaWAN Uplink and Downlink Messaging — 2023; https://doi.org/10.1109/jiot.2023.3263630

**原始摘要证据：** multihop_openalex_10.1109_DCOSS54816.2022.00014.json；已读范围与适用论断见本节。

## 7. Cost Effective Routing in Large-scale Multi-hop LoRa Networks

**作者：** Silin Feng; Jiajun Chen; Zhiwei Zhao.

**出处：** IEEE INFOCOM 2022 - IEEE Conference on Computer Communications Workshops (INFOCOM WKSHPS), pp. 1-6, 2022. DOI: [10.1109/infocomwkshps54753.2022.9798302](https://doi.org/10.1109/infocomwkshps54753.2022.9798302).

**用途优先级：** 中高：低成本覆盖、能耗路由.

**读取与证据：** 已读OpenAlex完整摘要；Crossref元数据和发表venue已核实，未读全文。 MLoRa是network-layer multi-hop routing方案，针对单跳覆盖、增加gateway的部署成本和节点耗能不均问题，以低成本覆盖及更低、更均衡能耗为目标。

**元数据/计数来源：** [Crossref](https://api.crossref.org/works/10.1109/infocomwkshps54753.2022.9798302)；[OpenAlex](https://api.openalex.org/works/W4283212624)；获取日期2026-11-04。

**正文插入位置：** Related Work的cost/energy-aware routing段，可与Smart-Hop并列。

```latex
MLoRa studies multihop routing for cost-effective coverage and balanced energy consumption, illustrating objectives beyond packet delivery alone~\cite{feng2022cost}.
```

**不能外推：** 发表在IEEE INFOCOM Workshops，绝不可写成INFOCOM main conference。摘要不足以判断所有模拟/实测设置，故不补写实验规模或具体百分比。

**已核验被引记录举例：**

- Multi-Hop and Mesh for LoRa Networks: Recent Advancements, Issues, and Recommended Applications — 2023; https://doi.org/10.1145/3638241
- A One-Way Time Synchronization Scheme for Practical Energy-Efficient LoRa Network Based on Reverse Asymmetric Framework — 2023; https://doi.org/10.1109/tcomm.2023.3305515

**原始摘要证据：** multihop_cost_routing_openalex.json；已读范围与适用论断见本节。

## 8. LoRaHop: Multihop Support for LoRaWAN Uplink and Downlink Messaging

**作者：** Pei Tian; Carlo Alberto Boano; Xiaoyuan Ma; Jianming Wei.

**出处：** IEEE Internet of Things Journal, vol. 10, no. 17, pp. 15376-15392, 2023. DOI: [10.1109/jiot.2023.3263630](https://doi.org/10.1109/jiot.2023.3263630).

**用途优先级：** 最高：可靠性、多跳上下行、真实设备部署.

**读取与证据：** 已读OpenAlex完整摘要并核对Crossref作者/卷期/页码；本轮未获得全文。 LoRaHop让LoRaWAN end-devices形成mesh并relay双向traffic；采用concurrent transmissions和rendezvous机制；在off-the-shelf端设备实现并与commercial gateways/network servers互通，室外testbed评估。

**元数据/计数来源：** [Crossref](https://api.crossref.org/works/10.1109/jiot.2023.3263630)；[OpenAlex](https://api.openalex.org/works/W4361987105)；获取日期2026-11-04。

**正文插入位置：** Related Work的academic mesh段，在产品机制之前；Scope and limitations实物验证句可引用。

```latex
LoRaHop adds mesh-based uplink and downlink relaying to LoRaWAN through concurrent transmissions and rendezvous mechanisms, and evaluates an implementation on an outdoor testbed with commercial infrastructure interoperability~\cite{tian2023lorahop}.
```

**不能外推：** LoRaHop是面向gateway的LoRaWAN扩展，不能视为本稿任意peer-to-peer场景的直接同条件基线。摘要的up-to可靠性/能耗数字没有转移到本稿，不证明CPR的ACK取消公式。

**已核验被引记录举例：**

- A survey on massive IoT for water distribution systems: Challenges, simulation tools, and guidelines for large-scale deployment — 2024; https://doi.org/10.1016/j.adhoc.2024.103714
- AlLoRa: Empowering environmental intelligence through an advanced LoRa-based IoT solution — 2024; https://doi.org/10.1016/j.comcom.2024.02.014

**原始摘要证据：** multihop_lorahop_openalex.json；已读范围与适用论断见本节。

## 建议整合成正文的短段落

保留对 Meshtastic/MeshCore 官方文档的引用。下列学术文献用于说明邻近方法与评估证据，不替代官方行为定义。可以择5–8篇分布引用，避免单句堆8个编号：

```latex
Multihop LoRa proposals span relay- and router-based architectures,
with distinct energy, access, and routing constraints~\cite{cotrim2020lorawanmesh,wong2024multihop}.
Smart-Hop couples low-overhead routing with spreading-factor-dependent
range selection~\cite{ahmar2022smarthop}, while MLoRa targets
cost-effective coverage and balanced energy use~\cite{feng2022cost}.
Airtime-aware alternatives include spreading-factor clustering~\cite{zhu2019improving}
and distance-vector routing evaluated with a time-on-air metric in
FLoRa/OMNeT++~\cite{pueyo2024minimalistic}.
Hardware-oriented studies include an ESP32 LoRa mesh library with
proactive neighbor updates~\cite{sole2022implementation} and LoRaHop's
outdoor evaluation of uplink/downlink relaying over LoRaWAN~\cite{tian2023lorahop}.
The present study instead isolates source recovery and pending-relay
ACK cancellation under a common packet-level simulator; its current
results do not constitute hardware or firmware validation.
```

## 两个新增 BibTeX 条目（供主审使用，本文件不改 Bib）

```bibtex
@inproceedings{feng2022cost,
  author = {Feng, Silin and Chen, Jiajun and Zhao, Zhiwei},
  title = {Cost Effective Routing in Large-scale Multi-hop {LoRa} Networks},
  booktitle = {IEEE INFOCOM 2022 - IEEE Conference on Computer Communications Workshops (INFOCOM WKSHPS)},
  pages = {1--6},
  year = {2022},
  doi = {10.1109/INFOCOMWKSHPS54753.2022.9798302}
}
@article{tian2023lorahop,
  author = {Tian, Pei and Boano, Carlo Alberto and Ma, Xiaoyuan and Wei, Jianming},
  title = {{LoRaHop}: Multihop Support for {LoRaWAN} Uplink and Downlink Messaging},
  journal = {IEEE Internet of Things Journal},
  volume = {10},
  number = {17},
  pages = {15376--15392},
  year = {2023},
  doi = {10.1109/JIOT.2023.3263630}
}
```

## 已检索但本轮不推荐据其具体方法加引用

- MRT-LoRa：DOI10.1016/j.comcom.2022.12.013；Crossref核实 Leonardi / Lo Bello / Patti, Computer Communications 199,72–86,2023；Elsevier API也核实2023-02-01，OpenAlex却标2022。OpenAlex计数50 / Crossref48，但本轮未取得摘要/全文，ScienceDirect403，Elsevier只返回元数据。不能凭题目写TDMA/时限保证等具体方法论断。
- Osorio 2020 / Centelles 2021：均已核实元数据和摘要，可作背景备选；为减少重复综述，推荐清单优先加入LoRaHop和MLoRa原创研究。
- LoRaBlink：目前仅在Cotrim全文中读到二手介绍，未核验原论文，不作为本轮原始方法证据。

没有任何文献被用来证明CPR特定公式、修复已发现实现缺陷或支撑未经运行的新性能数字。
