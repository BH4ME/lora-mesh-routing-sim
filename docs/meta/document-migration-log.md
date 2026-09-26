# Document Migration Log

Date: 2026-05-10

Purpose: clean the repository root and group Markdown documents by purpose while
preserving Git history where possible.

## Current Layout

- `README.md`: root project entry point.
- `docs/README.md`: documentation index.
- `docs/research/`: current research and conference-facing plans.
- `docs/reference/`: glossary, formulas, and stable reference material.
- `docs/results/`: human-readable result summaries and experiment notes.
- `docs/firmware/`: firmware protocol and build notes.
- `docs/project-history/`: working findings and progress logs.
- `docs/project-management/`: active project planning documents.
- `docs/meta/`: documentation-maintenance records.
- `archive/research-drafts/`: older research drafts kept for traceability.

## Path Changes

| Old Path | New Path | Reason |
| --- | --- | --- |
| `docs/conference-research-plan.md` | `docs/research/conference-research-plan.md` | Current research plan belongs under research docs. |
| `docs/terminology-and-formulas.md` | `docs/reference/terminology-and-formulas.md` | Stable formulas and terminology belong under reference docs. |
| `docs/ei-mesh-research-plan.md` | `archive/research-drafts/ei-mesh-research-plan.md` | Older draft preserved but removed from current docs. |
| `results/three_protocol_comparison.md` | `docs/results/three_protocol_comparison.md` | Result narrative belongs in docs, raw CSV/TXT stays in results. |
| `results/calm_experiment_notes.md` | `docs/results/calm_experiment_notes.md` | Experiment interpretation belongs in docs. |
| `results/prior_model_comparison_summary.md` | `docs/results/prior_model_comparison_summary.md` | Model comparison summary belongs in docs. |
| `firmware/esp32_smart_calm/README.md` | `docs/firmware/esp32_smart_calm.md` | Firmware documentation centralized under docs. |
| `findings.md` | `docs/project-history/findings.md` | Working findings moved out of root. |
| `progress.md` | `docs/project-history/progress.md` | Progress log moved out of root. |
| `task_plan.md` | `docs/project-management/task_plan.md` | Active plan moved out of root. |

## Deletion Policy

No useful Markdown content was permanently deleted in this cleanup. Documents
that were no longer part of the current narrative were moved into `archive/` so
they remain recoverable through the filesystem and Git history.
