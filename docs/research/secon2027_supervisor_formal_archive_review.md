**SECON 2027 formal v1：分块归档独立恢复验收**

2026-11-04，Asia/Shanghai。**通过：11 个分块逐一校验成功，按索引顺序重组后的 whole SHA 与未拆原归档一致；全部 14,667 个成员的哈希、字节数、精确文件清单和安全路径检查通过。在全新临时目录恢复后，保存源码 `audit_plan` 完成 760/760 run，failed=[]、missing=[]，760 个 `_audit_worker` 均返回 0。** 审计后所有恢复文件和执行树归档材料均保持哈希不变。已按授权清理本次临时恢复目录与重组文件，保留完整指纹、命令、日志和可复核 wrapper 源码。

| 核验对象 | 独立观察结果 |
| --- | --- |
| 执行树归档目录 | `/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/artifacts/secon2027` |
| 分块索引 | `formal-v1-raw-evidence.parts.index.json` |
| 分块索引 SHA-256 | `bc9d34574666a5185d51a9b3b87e976eff508b12c7bedaa0951abc228699d407` |
| 完整索引 | `formal-v1-raw-evidence.index.json` |
| 完整索引 SHA-256 | `d4d9999156a4ac24b36d7ae82c87c7d614051d1b3dbe33c781280d1f4affab4f` |
| 分块 | `formal-v1-raw-evidence.tar.gz.part-001` 至 `part-011`，11/11 通过 |
| 重组 whole SHA-256 | `81776e12501e56945dd8aad6a37bb68e5f6e4b41d66c88ae041e7689e490d067` |
| 重组 bytes | 475,828,160 |
| tar 成员数 / 普通文件 / 目录项 | 14,667 / 14,667 / 0 |
| 恢复文件 bytes | 7,104,348,257 |
| 成员清单指纹（规范化 path→bytes/SHA 映射） | `b53ea117836972bfd9edbc3993898b19104ef229c4b44b01b91d403552cf7a7c` |
| canonical plan_sha256 | `5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0` |
| plan 文件 SHA-256 | `e738c34f726718027c46ff832aea8ca1bb095fa1e4a9cb5c8d25f271012e4052` |
| source snapshot | `63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee` |
| tested version | `2.1.29` |
| 冻结 contract SHA-256 | `0db4fc2e724f441e190693e3f8d37b7912e2d4baa5555515c6f132481f309eff` |
| 保存 audit 模块 SHA-256 | `6908c859bade6aec9aebf8f9231c76ae5aebdd347d9791d3ddda47f5ceebbb51` |
| 与先前已验证 raw 审查的 completion 哈希联结 | 760/760 一致 |
| 保存源码 audit 耗时 | 570.836 s |

开始时检查到可用空间 **31,784,865,792 bytes**；重组归档加解压文件需要 7,580,176,417 bytes，再保留 2 GiB，空间门槛共 9,727,660,065 bytes，满足后才开始恢复。两个 index 的共有字段和完整 files 映射逐项一致。没有将 index 中 `all_members_verified` 声明当作核验结果。

分块顺序严格使用索引列表，另行检查唯一文件名、001–011 顺序及磁盘分块精确清单。前十块各 47,185,920 bytes，最后一块 3,968,960 bytes。逐块实际 bytes/SHA 均与索引相等；拼接时独立计算 whole SHA，再重新读取落盘的重组文件核对，最后只读对照未拆原 `formal-v1-raw-evidence.tar.gz`。**恢复来源是这次由分块重组出的文件**，原归档没有被用来填补分块或恢复目录。

逐个读取 tar 成员，要求路径相对、规范化、不含 `..` 且不重复；拒绝 symlink、hardlink 与特殊文件，只允许普通文件/目录。每个文件必须在索引中，流式计算实际字节数和哈希后写入原本为空的临时目录，再从磁盘重新读取核对。所有 14,667 文件与索引精确对应，无缺失、额外文件、链接、特殊成员或目录项。完整成员映射的规范化 SHA 与 index 的映射指纹一致。

恢复计划绑定当前 formal-v1 snapshot 和 tested version 2.1.29。所有 760 completion SHA 还与 [已验证的独立 raw 审查 JSON](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_formal_raw_review_verified.json) 一致；引用的 JSON SHA 为 `9dadbb649d49e3d62b6a8ba556a21f00cbd36407a4b430d92d6ce6733685907a`。它是已完成 raw 审查的身份对照，本次没有重做其独立逐 RX 统计，也没有改变原审查保留的假设纠正记录。

调用时先导入恢复出的冻结 `source/tools/secon2027_experiment.py`，再显式传入恢复的归档根目录：

```python
module.audit_plan(
    restored_root / "results/secon2027/plans/formal-v1.json",
    restored_root,
)
```

保存脚本的默认 `ROOT` 是 snapshot/source，因此没有直接借用其 CLI 默认根目录。wrapper 位于 snapshot 外，路径先经 `resolve()` 消除 macOS `/var` 与 `/private/var` 别名差异，且设置 `PYTHONDONTWRITEBYTECODE=1`。包装器只允许调用保存脚本的 `_audit_worker --attempt <恢复目录内路径>`，逐次记录完整命令、cwd、返回码、耗时、stdout/stderr 及其哈希。审计未读取执行树 run 作为恢复回退，也未导入执行树实时源码替代冻结源码。

静态调用链为 `audit_plan→verify_plan/audit_attempt→_audit_worker→verify_snapshot/audit_artifacts/audit_bundle`，不进入模拟、实验运行或 seed 状态修改。独立范围检查还确认：760×18=13,680 项必要 attempt 文件在 index 中，166 项 snapshot 源文件清单完整，760 manifest 的 contract 引用均为相对路径，8,360 项 source hash 绑定与 snapshot index 一致。依赖为标准库及归档源码（包括 Unix `fcntl`），未安装科学库。全量保存审计最终返回 `complete`，expected=completed=760，无失败或缺失。

审计结束后，重新检查恢复目录的精确文件集合及全部 14,667 文件 bytes/SHA，均未改变，也没有生成 `__pycache__` 等额外文件。随后重新核验执行树的两个 index、11 个分块和未拆原归档，其哈希均与本次开始时相同。

本次临时目录为 `/private/var/folders/hl/vl6nk1r117n72pf41vjt8pz80000gn/T/secon2027-supervisor-formal-archive-bno54j7o`，仅由本审查创建；完成全部核验后已删除该目录内的恢复树、重组归档及临时 wrapper。释放文件内容名义总量 **7,580,176,417 bytes（约 7.58 GB）**；执行树原始材料没有删除或修改。删除后已确认临时目录不存在。完整 wrapper 源码、runner SHA、14,667 成员校验标记、11 块校验标记、760 次 worker 完整记录和 `audit_plan` 返回值均保留在下面的 canonical JSON，临时目录的移除不影响复核记录。

[完整验收 JSON](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_formal_archive_review.json) 的 SHA-256 为 `8730d7a9f389e33e1031b8d087cac9465443fbc3a6a933980ed8c39631cd9275`。本结果支持“当前正式 raw 分块归档完整、可独立重组并干净恢复、保存审计能复核全部 760 run”。它没有增加实验样本、重新暴露研究 seed，也不等同于统计结论、RF、投稿稿或整体 SECON 验收。
