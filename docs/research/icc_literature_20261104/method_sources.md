# 有限重传、相关丢包与配对仿真来源

核验日期：2026-11-04。以下三项用于正文；被引数为 OpenAlex 当次响应的索引计数，不是全库完整统计。Crossref/DOI 用于核对出版身份，摘要内容用于限定引用论断；未声称已读到全部全文。

## liu2004truncated

- Q. Liu, S. Zhou, G. B. Giannakis, “Cross-Layer Combining of Adaptive Modulation and Coding With Truncated ARQ Over Wireless Links,” IEEE Transactions on Wireless Communications, 3(5), 1746–1755, 2004.
- DOI：https://doi.org/10.1109/TWC.2004.833474。
- Crossref 元数据：`truncated_crossref_search.json` 首项；OpenAlex：`truncated_openalex.json`，W2151222548，cited_by_count=932。
- 已读：OpenAlex 收录的论文摘要。摘要明确将有限 ARQ 和 AMC 结合，在时延和误差约束下研究频谱效率，并指出增加重传次数的收益递减。
- 使用位置：CPR 的有限重试/截止预算小节。建议表述：Limited-retry designs study a delay--reliability trade-off; CPR instead keeps the PHY fixed and budgets one repeat plus a recovery flood using scheduled start times.
- 限制：不能声称该文证明本文跨多跳恢复预算或ACK取消规则；不能引用其数值作为LoRa性能。
- 元数据差异：OpenAlex 给出的展开姓名与可靠作者元数据不一致，正式文稿使用 Crossref 核实的 Q. Liu、S. Zhou、G. B. Giannakis，不采用索引推断的展开姓名。

## srinivasan2008beta

- K. Srinivasan, M. A. Kazandjieva, S. Agarwal, P. Levis, “The β-factor: Measuring Wireless Link Burstiness,” Proc. ACM SenSys, 29–42, 2008.
- DOI：https://doi.org/10.1145/1460412.1460416。
- 元数据：`bursty_exact_crossref.json`（主标题和副标题分字段）；摘要与被引记录：`bursty_exact_openalex.json`，W2047282676，cited_by_count=305。
- 已读：索引摘要。802.15.4 三个测试床显示中等质量链路的突发性；评估β如何影响丢包后的等待与协议传输成本，也检查了802.11b轨迹。
- 使用位置：条件成功概率和不假设重传独立的说明。
- 拟表述：Measurements on low-power wireless links demonstrate bursty reception; this motivates retaining failure-history conditioning rather than assuming independent retries.
- 限制：这是一般无线网络的动机证据，不能把其中实测改善百分比转移到LoRa，也不证明当前LoRa衰落模型已校准。

## glasserman1992crn

- P. Glasserman and D. D. Yao, “Some Guidelines and Guarantees for Common Random Numbers,” Management Science, 38(6), 884–908, 1992.
- DOI：https://doi.org/10.1287/mnsc.38.6.884。
- 出版社提交摘要和元数据：`paired_crossref_verified.json`；OpenAlex：`paired_openalex.json`，W2171554447，cited_by_count=188。
- 已读：Crossref的出版方摘要及OpenAlex同文摘要。论文研究CRN比较随机系统及其方差收益条件，强调单调性、连续性与事件时序；并非无条件保证。
- 使用位置：seed-paired uncertainty 方法。建议表述：Common-scenario comparisons are motivated by variance-reduction methods, but coupling benefits depend on the system; we estimate the variance of observed paired seed differences.
- 限制：相同seed/工作负载不等于两个协议事件流逐一共用所有随机变量；不得声称已满足其最优性条件。

## 未纳入

- Lin/Costello/Miller 1984 ARQ综述真实（DOI 10.1109/MCOM.1984.1091865，OpenAlex967次），但与已选有限ARQ论断重复，本轮不为数量额外引用。
- 对错误检索结果及未读全文不纳入文稿。IEEE/INFORMS全文未成功打开不影响已核实出版身份，但记录访问层级为摘要。

## 被引关系复核

`method_routing_citation_examples.json` 保存三篇方法文献与三篇路由文献的具体引用关系查询；`etx_dsr_citation_examples.json` 保存另外两篇。核对返回的 `referenced_works` 中包含目标 OpenAlex ID。

Trickle 查询有一条明显不合理记录（1996年的无关社会科学题名指向2004年的Trickle），已标记为索引错误并排除，不作为佐证。保留另一条2004年 Contiki 论文的合理引用记录。索引被引数只能作为数据库快照，不能当作零错误的全网引用总数，也没有冒充逐篇打开被引论文参考文献列表。
