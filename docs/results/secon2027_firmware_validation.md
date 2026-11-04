# SECON firmware and RF status

No new firmware modification, board flash, RF measurement or power measurement is included in this SECON simulation study. The imported prototype remains version0.1.4. Historical native/board build records and unresolved firmware lifecycle cases are retained in `docs/research/meshecho_firmware_upgrade_handoff_20261013.md`; they are not proof of current Python/RF equivalence.

Hardware is conditional P2. This task has no identified connected multi-node RF setup or measurement apparatus; simulation proceeds with this explicit limitation. Simulator SF7 settings differ from historical firmware defaults, so neither binary compilation nor old native tests establish physical PDR or battery life. No official Meshtastic/MeshCore firmware was benchmarked.
