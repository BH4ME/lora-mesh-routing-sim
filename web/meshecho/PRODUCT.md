# Product

## Register

product

## Users

MeshEcho Web is for firmware developers, radio experimenters, and field operators who need to prepare LoRa mesh hardware from a browser. They may be at a bench with USB serial access, in a field kit with limited network access, or reviewing firmware releases before flashing a real ESP32 radio.

## Product Purpose

MeshEcho Web gives the MeshEcho firmware project a single browser surface for project orientation, firmware flashing, device configuration, and release inspection. Success means a user can identify the right hardware target, understand whether artifacts are safe to flash, connect over the available transport, send configuration commands, and read device output without needing a separate desktop utility.

## Brand Personality

Technical, composed, field-ready. The interface should feel like a trustworthy radio operations console: dense enough for real work, calm enough to avoid mistakes, and specific about hardware state.

## Anti-references

Avoid generic SaaS landing-page tropes, decorative sci-fi panels that make controls harder to scan, copied Meshtastic visual identity or source structure, and marketing copy that hides the actual hardware workflow. The UI should not look like a demo wallpaper with buttons placed on top of it.

## Design Principles

- Put the device workflow first: target, artifact state, connection, command, and logs must stay easy to find.
- Make risk visible before action: flashing, erase mode, placeholder artifacts, and unsupported targets need plain status cues.
- Preserve technical trust: use exact target names, protocol names, checksums, transport limits, and firmware states.
- Keep brand expression useful: visual identity should clarify signal, route, and device state, not decorate around them.
- Design for interrupted work: field users should be able to return to the page and quickly recover context.

## Accessibility & Inclusion

Aim for WCAG AA contrast across text, controls, focus states, and status colors. Do not rely on color alone for success, warning, or blocked states. Respect reduced motion preferences and keep controls usable on narrow screens and touch devices.
