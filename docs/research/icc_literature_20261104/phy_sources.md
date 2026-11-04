# ICC LoRa PHY、空口时间、碰撞与仿真文献核验

核验日期：2026-11-04（Asia/Shanghai）。作者/题名/年份/卷页/DOI 实际查询 Crossref；摘要、开放全文位置、被引数实际查询 OpenAlex，并对下表注明的开放全文做内容检查。配套机器可读记录见 [phy_sources.json](phy_sources.json)。本任务不修改主 TeX/Bib，不新跑仿真。

## 结论及可直接使用的引用位置

1. 当前 `eq:lora-toa` 的直接已发表出处可以使用 **Augustin et al. 2016，第 3.2–3.3 节、式 (1)–(3)**。已读取 Europe PMC 全文 XML，不能将该标准 ToA 式作为本论文新推导。它的变量编码与当前稿不同，但式子等价：其 `CR=4/(4+n)` 对应当前整数编码率索引 `CR=n`；其 header 开启参数 `H=20` 对应当前 `IH=0`；其 `DE=2` 对应当前布尔 `DE=1`。当前公式使用 `28-20 IH`，等价于文献的 `8+H`。两个版本均包含向上取整。
2. 当前 `eq:wire-length` 的自定义 mesh header 字节数不是 Augustin 或 Semtech 的协议格式，应保留为本文实现定义；可引用文献支持“完整 PHY payload 决定 ToA”，不能让引用看起来证明自定义 10-byte base、path ID 编码或 marker 字节。
3. 当前 `eq:path-reliability` 后讨论“实际接收由 fading/capture/interference 决定”可引用 **To & Duda 2018、Rahmadhani & Kuipers 2018**。这些文献支持采用物理接收/捕获模型，不证明本文模拟器已经过测量校准。独立跳乘积仍是本文说明性近似，而不是这两篇文献给出的 mesh 公式。
4. Related Work/limitations 可用 **Bor et al. 2016、Georgiou & Raza 2017** 说明 air load、capture、配置、密度影响容量，不可把单网关容量公式或密度数字移植到 20-node mesh。
5. **Croce et al. 2018** 支持“不同 SF 不完全正交”。当前测试全部 SF7，它适合放到多 SF 扩展/模型局限中，不应声称本次四协议实验已测得 inter-SF 效应。
6. **Van den Abeele et al. 2017** 支持区分 DATA 到达与确认成功、并显式计入 ACK/control traffic 的必要性。其 ACK 容量瓶颈是 LoRaWAN gateway downlink/RX windows/duty cycle 场景，不能据此证明 CPR 多跳 ACK 的具体收益。
7. **Heusse et al. 2023** 补足多重碰撞与累计干扰的较近期分析。可引用它说明“噪声成功、捕获成功与干扰功率和的依赖需要谨慎建模”，但除非代码确实实现该模型，不可写成本文使用/复现了其模型。

建议可插入的英文表述（按实际篇幅选择，不必全放）：

```latex
The symbol duration and payload-symbol count follow the standard
LoRa airtime model \cite{augustin2016study}; our routing fields determine
the PHY payload length supplied to that model.

Measurement-informed LoRa models account for reception timing and
capture rather than treating every overlap as a loss
\cite{bor2016scale,to2018lorans3,rahmadhani2018collide}.

Prior scalability studies show that airtime, interference and radio
parameter allocation jointly affect capacity
\cite{bor2016scale,georgiou2017scale}; their single-hop gateway results
do not establish the scalability of the present mesh policy.

LoRaWAN studies distinguish received data from confirmed transactions
because acknowledgement traffic consumes constrained downlink resources
\cite{vandenabeele2017scalability}. Here we report destination reception
and source confirmation separately, under the mesh's own ACK model.

Different spreading factors are only quasi-orthogonal
\cite{croce2018orthogonality}, and multiple-interferer capture models
can depend on aggregate interference and its dependence on noise
\cite{heusse2023aloha}. Our fixed-SF evaluation does not validate these
broader operating regimes.
```

## 元数据与被引数

下列数值是 **2026-11-04 查询时** 各数据库自己的索引计数，不能称为 Google Scholar 被引数，也不用于保证质量/中稿率。Crossref `is-referenced-by-count` 与 OpenAlex `cited_by_count` 的覆盖面不同，数值不一致是正常现象。JSON 保留各篇 API 地址，可复查。

| 文献 | 正式发表位置 | OpenAlex | Crossref | 实际阅读范围 |
|---|---|---:|---:|---|
| Augustin et al., 2016 | Sensors 16(9), article 1466 | 1500 | 1375 | 摘要；全文 XML，重点 §§3.2–3.4、4.2、5.2 |
| To & Duda, 2018 | IEEE ICC 2018, pp. 1–7 | 160 | 124 | OpenAlex 完整摘要；未取得全文 |
| Bor et al., 2016 | ACM MSWiM 2016, pp. 59–67 | 838 | 713 | 摘要；作者仓库修正版全文，重点 §§3.2–3.3、4、第一页修正说明 |
| Georgiou & Raza, 2017 | IEEE WCL 6(2), pp. 162–165 | 731 | 664 | 摘要；arXiv v2 全文，重点 §§II–V |
| Croce et al., 2018 | IEEE Communications Letters 22(4), pp. 796–799 | 394 | 382 | OpenAlex 完整摘要；未取得全文 |
| Rahmadhani & Kuipers, 2018 | ACM WiNTECH 2018, pp. 89–97 | 85 | 76 | OpenAlex 完整摘要；未取得全文 |
| Van den Abeele et al., 2017 | IEEE IoT Journal 4(6), pp. 2186–2198 | 349 | 317 | 摘要；arXiv 作者稿全文，重点 §§II、IV–VIII |
| Heusse et al., 2023 | IEEE IoT Journal 10(20), pp. 17824–17838 | 19 | 20 | OpenAlex 完整摘要；HAL 全文请求返回挑战页，未读取全文 |

### 1. Augustin et al. — 保留并用于 ToA

**完整元数据：** Aloÿs Augustin, Jiazi Yi, Thomas Clausen, and William Townsley, “A Study of LoRa: Long Range & Low Power Networks for the Internet of Things,” *Sensors*, vol. 16, no. 9, article 1466, 2016. DOI: [10.3390/s16091466](https://doi.org/10.3390/s16091466).

- [Crossref 实测元数据](https://api.crossref.org/works/10.3390/s16091466)；[OpenAlex W2520480241](https://api.openalex.org/works/W2520480241)。
- [已读取全文 XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC5038744/fullTextXML)；[出版社页面](https://www.mdpi.com/1424-8220/16/9/1466)。
- 证据：§3.2 式 (1) 为 `T_s=2^SF/BW`；§3.3 明确式 (3) 给出 payload symbol 数，并要求加上 preamble symbol 数计算完整包时长；§4.2 指出 MAC header 会占用容量。
- 具体支持：`eq:lora-toa` 的 symbol time、payload-symbol quantization、header/CRC/DE/coding rate 参数；Introduction 的低速/远距 LoRa 背景。
- 边界：标准 LoRa PHY 的表达可用于 mesh，但 LoRaWAN MAC 的 13–28-byte header、网关接收窗口和单跳容量结果不能替代本文自定义 wire-length 定义。本文 6-dB block fading、每 60 s 刷新也不是由此文献标定。
- 现有参考文献的 DOI/年份/作者顺序正确。1466 是 article number，写 `Art. no. 1466` 比 `p. 1466` 更清楚。

### 2. To & Duda — 保留，真正发表于 ICC 主会

**完整元数据：** Thanh-Hai To and Andrzej Duda, “Simulation of LoRa in NS-3: Improving LoRa Performance with CSMA,” in *2018 IEEE International Conference on Communications (ICC)*, 2018, pp. 1–7. DOI: [10.1109/ICC.2018.8422800](https://doi.org/10.1109/ICC.2018.8422800).

- [Crossref](https://api.crossref.org/works/10.1109/ICC.2018.8422800)；[OpenAlex W2884228260](https://api.openalex.org/works/W2884228260)；[IEEE](https://ieeexplore.ieee.org/document/8422800/)。
- 摘要原文支持：“the module correctly represents the capture effect that lowers the packet drop rate due to collisions”；作者将 ns-3 结果与 testbed 和其他测量结果对照。
- 具体支持：Related Work 的 LoRa packet-level/capture-aware simulation 方法先例；物理接收不宜简化为“所有重叠都丢包”。
- 边界：论文研究 LoRa/LoRaWAN CSMA，不是 CPR、Meshtastic 或 MeshCore。不能据其验证工作声称本文 Python simulator 已验证；也不能根据摘要把 CSMA 的监管例外推广到全部地区/配置。只读了摘要，不为正文特定参数/门限背书。
- 现有 ICC 文献条目的题名、作者、年份、页码和 DOI 均正确。

### 3. Bor et al. — 仿真与捕获依据，注意作者修正版

**完整元数据：** Martin C. Bor, Utz Roedig, Thiemo Voigt, and Juan M. Alonso, “Do LoRa Low-Power Wide-Area Networks Scale?,” in *Proceedings of the 19th ACM International Conference on Modeling, Analysis and Simulation of Wireless and Mobile Systems (MSWiM)*, 2016, pp. 59–67. DOI: [10.1145/2988287.2989163](https://doi.org/10.1145/2988287.2989163).

- [Crossref](https://api.crossref.org/works/10.1145/2988287.2989163)；[OpenAlex W2525332113](https://api.openalex.org/works/W2525332113)；[作者仓库记录](https://eprints.lancs.ac.uk/id/eprint/81674/)。
- [已读取的正确修正版 PDF](https://eprints.lancs.ac.uk/id/eprint/81674/13/lora_scalability_r338.pdf)。
- 全文 §3.3 指出碰撞结果取决于 carrier frequency、SF、power、timing；§4 将测量得到的模型用于 LoRaSim，并比较配置/airtime 对容量的影响。
- 具体支持：捕获/碰撞建模需要接收功率与时间信息；用空口时长而非仅包数核算通信开销；网络负载和 PHY 参数共同影响容量。
- **版本核验发现：** OpenAlex 摘要仍写 `120 nodes per 3.8 ha`；作者修正版首页写 `64 nodes per 3.8 ha`，并明确脚注说明已修复“已碰撞包被误标为未碰撞”的 simulator bug，所有图和数字已更新。建议本稿只引用机制和方法，不搬用该密度数字。
- **错误链接排除：** OpenAlex 指向的 `.../7/Adding_an_electronic_thesis_5.3.3.pdf` 实际是博士论文上传指南，已经打开确认并排除，不能当作此论文全文。
- 边界：单跳 sink-based LPWAN 和当时的正交性假设；不证明 mesh scalability，不作为强 inter-SF 正交假设的依据（应配合 Croce）。

### 4. Georgiou & Raza — 负载/干扰扩展性动机

**完整元数据：** Orestis Georgiou and Usman Raza, “Low Power Wide Area Network Analysis: Can LoRa Scale?,” *IEEE Wireless Communications Letters*, vol. 6, no. 2, pp. 162–165, 2017. DOI: [10.1109/LWC.2016.2647247](https://doi.org/10.1109/LWC.2016.2647247).

- [Crossref](https://api.crossref.org/works/10.1109/LWC.2016.2647247)；[OpenAlex W2537187694](https://api.openalex.org/works/W2537187694)；[已读取 arXiv 作者稿 v2](https://arxiv.org/pdf/1610.04793)。
- 摘要和全文明确研究 **single gateway LoRa network**；将 SNR outage 和 co-SF interference outage 分开分析；在其假设下覆盖概率随 end-device 数增长而指数下降。
- 具体支持：Related Work 的干扰/密度限制；limitations 中说明需要更多负载与密度测试。文中的 `T_s=2^SF/BW` 也与标准 symbol time 一致，但 ToA 主引用仍建议 Augustin。
- 边界：单网关、Poisson 空间模型、特定 fading/ALOHA/duty-cycle 假设；其 strongest/co-SF interference 模型不是本文路由可靠性乘积的推导。全文结论自己讨论累计干扰假设若失效，结果会偏乐观；不应将它用于证明 cumulative interference 可忽略。
- 年份用 **2017**：DOI 包含 2016 不等于最终卷期年份。

### 5. Croce et al. — SF 不完全正交

**完整元数据：** Daniele Croce, Michele Gucciardo, Stefano Mangione, Giuseppe Santaromita, and Ilenia Tinnirello, “Impact of LoRa Imperfect Orthogonality: Analysis of Link-Level Performance,” *IEEE Communications Letters*, vol. 22, no. 4, pp. 796–799, 2018. DOI: [10.1109/LCOMM.2018.2797057](https://doi.org/10.1109/LCOMM.2018.2797057).

- [Crossref](https://api.crossref.org/works/10.1109/LCOMM.2018.2797057)；[OpenAlex W2792195154](https://api.openalex.org/works/W2792195154)；[IEEE](https://ieeexplore.ieee.org/document/8267219/)。
- 摘要证据：不同 SF 的包在干扰接收功率足够强时仍可造成丢包；作者使用 commercial devices 与 SDR 实验验证。
- 具体支持：模型需要说明 inter-SF interference 假设；扩展多 SF 不能默认无碰撞。
- 边界：仅全文摘要核验，不从记忆填写具体 SIR 矩阵数值。当前稿是 SF7 单 SF 测试，不能把此文献变成对本次 inter-SF 效应的证据。
- 不混同其 2017 Springer 会议章 *Impact of Spreading Factor Imperfect Orthogonality in LoRa Communications*，那篇作者列表/DOI不同；这里选择 2018 journal article。

### 6. Rahmadhani & Kuipers — 捕获与应用端实际接收

**完整元数据：** Andri Rahmadhani and Fernando Kuipers, “When LoRaWAN Frames Collide,” in *Proceedings of the 12th International Workshop on Wireless Network Testbeds, Experimental Evaluation & Characterization (WiNTECH)*, 2018, pp. 89–97. DOI: [10.1145/3267204.3267212](https://doi.org/10.1145/3267204.3267212).

- [Crossref](https://api.crossref.org/works/10.1145/3267204.3267212)；[OpenAlex W2896332706](https://api.openalex.org/works/W2896332706)；[ACM](https://dl.acm.org/doi/10.1145/3267204.3267212)。
- 摘要证据：通过 experiments 调查 LoRaWAN frame collisions/capture；关注 application 正确接收，并考虑 multi-gateway、multi-provider 和 dense 场景。
- 具体支持：捕获效果和应用交付指标不能仅由粗粒度 gateway 接收假设代替；为 physical reception ledger 提供实验方法背景。
- 边界：这是 **WiNTECH workshop**，与 MobiCom 2018 联办，不能写成 MobiCom 主会论文。其 application reception 不等于本稿 source-confirmed ACK PDR。只读摘要，不引用具体 capture timing/门限数值。

### 7. Van den Abeele et al. — ACK/downlink 开销与 ns-3

**完整元数据：** Floris Van den Abeele, Jetmir Haxhibeqiri, Ingrid Moerman, and Jeroen Hoebeke, “Scalability Analysis of Large-Scale LoRaWAN Networks in ns-3,” *IEEE Internet of Things Journal*, vol. 4, no. 6, pp. 2186–2198, 2017. DOI: [10.1109/JIOT.2017.2768498](https://doi.org/10.1109/JIOT.2017.2768498).

- [Crossref](https://api.crossref.org/works/10.1109/JIOT.2017.2768498)；[OpenAlex W2614897509](https://api.openalex.org/works/W2614897509)；[已读取作者稿](https://arxiv.org/pdf/1705.05899)。
- 摘要：构造 baseband BER-derived error/interference model，并用于含双向流量的 multi-channel/multi-SF/multi-gateway LoRaWAN ns-3；downstream traffic 对 confirmed upstream delivery 有不利影响。
- 全文 §§VII–VIII 说明有限 gateway downlink capacity 降低 confirmed upstream delivery；§VI 明确“没有 ACK 不必然意味着链路质量下降”，并指出 ACK/control duty-cycle 瓶颈。
- 具体支持：为 `p^D` 与 `p^A` 分开报告、control/ACK airtime 不被省略提供背景。可讨论将 ACK absence 直接当成 forward-link failure 的局限。
- 边界：星形 LoRaWAN Class A receive windows 和网关 duty cycle 机制；本稿是 mesh reverse-path ACK，不可直接借用该论文的容量数值或声称机制相同。读到的 arXiv 作者稿有 LaTeX placeholder 页眉，不影响以 Crossref 正式卷页为出版元数据。

### 8. Heusse, Caillouet & Duda — 多重碰撞模型的较新证据

**完整元数据：** Martin Heusse, Christelle Caillouet, and Andrzej Duda, “Performance of Unslotted ALOHA With Capture and Multiple Collisions in LoRaWAN,” *IEEE Internet of Things Journal*, vol. 10, no. 20, pp. 17824–17838, 2023. DOI: [10.1109/JIOT.2023.3280393](https://doi.org/10.1109/JIOT.2023.3280393).

- [Crossref](https://api.crossref.org/works/10.1109/JIOT.2023.3280393)；[OpenAlex W4378421950](https://api.openalex.org/works/W4378421950)；[HAL 记录](https://hal.science/hal-04119710)。
- 摘要明确两点：考虑“overcoming ambient noise”和“dominating colliding frames”之间的依赖；存在多碰撞帧时考虑干扰功率之和，并讨论 inter-SF/near–far interference。
- 具体支持：避免将 packet reception 无条件拆成独立 noise-success × collision-success；模型局限中说明多干扰源累积和相对功率的重要性。
- 边界：LoRaWAN cell、ALOHA、ECC 与 transmission-parameter allocation；并非多跳 CPR 验证。仅摘要已读，HAL document URL 本次返回挑战页，未把它当作论文全文，也不引用其具体推导编号或编码率结论到本稿。

## Semtech 官方 ToA 技术来源：已定位，全文未验证

官方产品页 [SX1276](https://www.semtech.com/products/wireless-rf/lora-connect/sx1276) 已实际读取，其 datasheet 列表给出 **“SX1276-7-8-9 Datasheet”, release date 2020-05-26**，链接为：

https://semtech.my.salesforce.com/sfc/p/E0000000JelG/a/2R0000001Rbr/6EfVZUorrpoKFfvaF_Fkpgp5kzjiNyiAbqcpqh9qSjE

旧 `https://www.semtech.com/uploads/documents/sx1276_77_78_79.pdf` 当前跳转到 “Document Has Moved”。新 Salesforce 链接在本次读取返回 HTML document viewer，不是 PDF。**未读取官方手册正文，不能声称核验了其具体 section/page/revision。** 本轮不为此延迟主稿：已有 Augustin 全文式 (1)–(3) 可作为 `eq:lora-toa` 的真实已发表出处。若以后引用 Semtech，应标明 corporate datasheet/technical document，不能计作第九篇学术论文。

## 核验限制与不应增加的主张

- 八篇均通过真实 API 检索确认出版记录；并非所有全文都已读取，阅读范围在上表逐项列明。
- 这里没有论文能证明本稿 `6-dB block fading every 60 s` 的现场代表性、20-node case 的广泛性、CPR 自定义 wire layout 或源端/relay 状态机的正确性。
- 不应以堆砌 citation 替代该稿已发现的 source-return forwarding、concurrent ACK-generation 等实现问题的修复/再评估。
- 图表、仿真数字和所有 CPR-specific identities 仍须由本仓库证据支持；上述文献是物理层/建模依据及相关工作，不是外部认证。
