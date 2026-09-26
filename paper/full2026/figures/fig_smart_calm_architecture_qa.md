# Figure QA Notes

## Figure Contract

- Core conclusion: Smart-CALM keeps the LoRa mesh forwarding plane simple and places adaptation in a compact ACK-aware profile selector.
- Figure archetype: schematic-led composite.
- Backend: Python/matplotlib only.
- Final size: double-column width, 183 mm by 104 mm.
- Panel map:
  - a: ACK-aware forwarding plane with DATA, fallback, and ACK semantics.
  - b: local signal bucketing, tabular policy, reward logic, and Q update.
  - c: closed-loop profile selection that rewrites data-plane redundancy parameters.
- Statistics needed: none; this is a mechanism schematic.
- Source data needed: none; the figure is protocol structure, not a quantitative plot.
- Reviewer risk: avoid implying hardware validation; the figure shows the simulated/proposed mechanism.

## Export Bundle

- `fig_smart_calm_architecture.py`: source script.
- `fig_smart_calm_architecture.svg`: editable vector output.
- `fig_smart_calm_architecture.pdf`: LaTeX-ready vector output.
- `fig_smart_calm_architecture.tiff`: 600 dpi raster output.
- `fig_smart_calm_architecture.png`: preview output.
