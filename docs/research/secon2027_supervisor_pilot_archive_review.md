**SECON 2027 pilot v2：归档独立恢复验收**

2026-11-04，Asia/Shanghai。**通过：归档 SHA-256、精确成员清单和全部 1,517 个成员哈希均一致；在全新临时目录恢复后，仅调用归档保存源码的 `audit_plan`，72/72 run 完整，failed=0、missing=0。** 每个保存源码 `_audit_worker` 均返回 0。审计结束后，恢复目录全部文件哈希和精确清单仍未改变。本次只验收归档完整性与独立恢复能力，不重复此前 raw 统计重建，也不表示正式实验、RF 或整体项目完成。

| 身份与核验项目 | 独立观察结果 |
| --- | --- |
| 归档 | `/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/artifacts/secon2027/pilot-v2-tested-2.1.28-evidence.tar.gz` |
| 相邻索引 | `/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo/artifacts/secon2027/pilot-v2-tested-2.1.28-evidence.index.json` |
| 归档 SHA-256 | `81e7222145e1689dc7dfeeff96264e57d33f250b5fb05a436fd2ec9e0a6df2b4` |
| 索引 SHA-256 | `3568aff6048d4181ecca95aa9dbe727d67500cdd283b2a32f0491c8c376cb0f1` |
| 压缩 bytes | 48,442,357 |
| 精确 tar 成员数 / 普通文件 / 目录项 | 1517 / 1517 / 0 |
| 恢复文件 bytes | 714,132,393 |
| canonical plan_sha256 | `0c49a69a5c3725c9f72ff2e28ed870d10db1df7eec4319f6397097b84a2c85e7` |
| plan 文件 SHA-256 | `cf30790288c060f93302eeefc5a9e3535533d2ada9d02d2ded80bd6768c0aff0` |
| source snapshot | `ee890e25030782fc01208ee4ce1f20863c6ade5322ac954ad67ae48b594056a2` |
| tested version | `2.1.28` |
| 保存的 audit 模块 SHA-256 | `6908c859bade6aec9aebf8f9231c76ae5aebdd347d9791d3ddda47f5ceebbb51` |
| 独立 raw 审查 completion SHA 再联结 | 72/72 一致 |
| 保存源码 `audit_plan` | `complete`，expected=72、completed=72、failed=[]、missing=[] |
| 保存 `_audit_worker` 退出状态 | 72/72 为 0 |
| 保存源码 audit 耗时 | 103.268 s |

首先独立计算压缩文件 SHA 和大小，与相邻 index 声明比较，未依赖索引中的 `all_members_verified` 布尔值。读取 tar 后检查唯一、相对、不含 `..` 的成员路径，仅允许普通文件/目录，拒绝 links 和特殊成员，并比较文件集合与索引集合完全相等。逐成员流式计算实际 bytes/SHA，再写入原本为空的临时目录，重新读取磁盘文件核对哈希；1517/1517 通过。无目录项、重复项、缺失项或额外文件。

本次成功恢复目录为 `/private/var/folders/hl/vl6nk1r117n72pf41vjt8pz80000gn/T/secon2027-supervisor-pilot-archive-vsikbie2/restored`。归档中的计划与 index 的 plan/snapshot 身份一致；所有 72 completion SHA 还与先前独立 raw 审查 JSON 一致，未借用执行工作区现存 run。调用入口采用 `importlib` 导入**恢复出的冻结源码**，再显式传入恢复的归档根目录：

```python
module.audit_plan(
    restored_root / "results/secon2027/plans/development-pilot-v2.json",
    restored_root,
)
```

不能直接对 snapshot/source 下的脚本使用其默认 CLI `audit` 根目录，因为脚本的 `ROOT` 指向保存源码而非归档根；上面的显式 root 是保存接口支持的恢复方式，没有修改源码。设置 `PYTHONDONTWRITEBYTECODE=1`，wrapper 留在 snapshot/source 之外；每个内部子进程被包装器限制为该保存脚本的 `_audit_worker --attempt <恢复目录内路径>`，并记录命令、cwd、退出码、耗时及 stdout/stderr 哈希。72 个子进程均成功，未运行 `simulate`、`run`、freeze、业务生成、测试或新研究 seed。

静态独立调用链审查确认，`audit_plan→verify_plan/audit_attempt→_audit_worker→audit_artifacts/audit_bundle` 读取既有证据，不进入模拟执行或 seed 状态变更路径。依赖为 Python 标准库（含 Unix `fcntl`）；72 manifest 的 contract 引用及 plan 中 snapshot/registry/contract 引用均为相对路径。历史 runtime 记录中的原机器路径仍作为 provenance 字符串保留，没有成为本次审计的外部文件依赖。

归档根部的报告/contract 属于归档时的文档封装，可能晚于 tested snapshot；本次 `verify_plan` 实际核对的是冻结 snapshot 内 contract（SHA `b23e09f654646aadec3af45b2d65f8eda55cf9aee1b4762ab9656c69f6c15192`）以及保存的源码/版本，并未用顶层后续文档替换已测试方法身份。

审计结束后，重新检查恢复目录所有 1,517 文件的 bytes/SHA 和精确文件集合，均与 index 保持一致；没有生成 `__pycache__` 或其他额外文件。原归档与 index 的前后哈希也一致。仅修改 canonical 审查输出和本任务新建临时目录，没有改执行仓库，也没有复制执行工作区中缺失的材料来帮助恢复。

首次尝试在任何 `_audit_worker` 启动前，被审查 wrapper 的路径字符串比较拦截：macOS 把 `/var` 解析为 `/private/var`，两种拼写指向同一目录。该次归档/成员/72 completion 验证已通过，失败属于审查包装器，不属于归档。随后仅将 wrapper 工作路径正规化，在第二个全新空目录重新恢复并完整通过；首次错误与 runner SHA 保存在 JSON 的 `harness_attempts`，未删除失败记录。首份冗余解压树已清理，成功恢复目录保留供复核。

详细证据见 [secon2027_supervisor_pilot_archive_review.json](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_pilot_archive_review.json)（SHA-256 `3cc170654dfcc10c3e9667e13ae068bd3e5b6caed894ceb409ef6dd391e4574f`），其中包含全部成员路径、字节数、实际哈希、恢复及审计后核验标记、72 次 audit worker 命令与返回状态、完整 `audit_plan` 返回值。此前机制与负结果仍以 [pilot v2 独立 raw 审查](/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_pilot_v2_raw_review.md) 为准；本次归档通过没有增加独立实验样本或改变其结论。
