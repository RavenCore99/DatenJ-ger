---
name: DatenJäger Precision Desktop
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#434655'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#747686'
  outline-variant: '#c4c5d7'
  surface-tint: '#2151da'
  primary: '#0037b0'
  on-primary: '#ffffff'
  primary-container: '#1d4ed8'
  on-primary-container: '#cad3ff'
  inverse-primary: '#b7c4ff'
  secondary: '#006398'
  on-secondary: '#ffffff'
  secondary-container: '#5bb8fe'
  on-secondary-container: '#00476e'
  tertiary: '#3d445a'
  on-tertiary: '#ffffff'
  tertiary-container: '#545c72'
  on-tertiary-container: '#cdd5ef'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dce1ff'
  primary-fixed-dim: '#b7c4ff'
  on-primary-fixed: '#001551'
  on-primary-fixed-variant: '#0039b5'
  secondary-fixed: '#cce5ff'
  secondary-fixed-dim: '#93ccff'
  on-secondary-fixed: '#001d31'
  on-secondary-fixed-variant: '#004b73'
  tertiary-fixed: '#dae2fd'
  tertiary-fixed-dim: '#bec6e0'
  on-tertiary-fixed: '#131b2e'
  on-tertiary-fixed-variant: '#3f465c'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-hero:
    fontFamily: Space Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 52px
    letterSpacing: -0.04em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 38px
    letterSpacing: -0.03em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.02em
  headline-sm:
    fontFamily: Space Grotesk
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 22px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
  telemetry-mono:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.02em
  telemetry-code:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 0.75rem
  margin: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style

The design system establishes a high-performance native desktop environment blending surgical precision with breezy, atmospheric lightness. Tailored for data engineers, security researchers, and systems intelligence operators, the aesthetic synthesizes Scandinavian functional minimalism with electric cybernetic typography.

The interface evokes uncompromising trust, ultra-low latency, and clarity under heavy data loads. Rather than dense, dark-mode terminal tropes, it embraces an airy, crystalline light mode—illuminated by soft sky-blue tints, razor-thin borders, and high-contrast electric cobalt accents.

Key stylistic pillars:
- **Clean Technical Minimalism:** Ample breathing room, deliberate negative space, and rigid horizontal alignment.
- **Electric Accentuation:** High-potency cobalt blue anchors primary typography, brand display marks, and active states against luminous backdrops.
- **Mac-Native Desktop Craft:** Standardized window chrome, integrated telemetry footers, and compact split-pane navigation designed for continuous, all-day focus.

## Colors

The palette leverages a crisp, multi-tiered white and sky-blue architectural base, energized by hyper-saturated cobalt blues.

- **Primary Electric Cobalt (`#1d4ed8`, `#2563eb`):** Reserved for focal display typography, primary action glyphs, active navigation pills, and critical highlighted links.
- **Secondary Sky Teal (`#0284c7`):** Powers secondary interactive states, tool badges, and telemetry confirmations.
- **Tertiary Deep Navy (`#0f172a`, `#1e293b`):** Delivers clinical contrast for readable running body copy and complex data tables without introducing jarring pure blacks.
- **Neutral Blue-Slate (`#64748b`, `#94a3b8`):** Defines non-interactive metadata, subheadings, keybind badges, and muted states.

### Surface System
- `canvas-default`: `#ffffff` (Pure white for primary chat/content viewports)
- `canvas-subtle`: `#f8fafc` (Muted canvas and container fill)
- `canvas-sidebar`: `#f0f6ff` (Airy, sky-tinted sidebar and inactive window chrome)
- `border-subtle`: `#e2e8f0` (Baseline hairpins and split-view dividers)
- `border-accent`: `#bfdbfe` (Delicate sky-blue focus rings and highlighted cards)
- `status-success`: `#10b981` (Gateway ready and connection verified)
- `status-traffic-red`: `#ff5f56`
- `status-traffic-yellow`: `#ffbd2e`
- `status-traffic-green`: `#27c93f`

## Typography

The type ecosystem balances three distinct typographic voices:
1. **Space Grotesk (Brand & Headlines):** Imparts a modern, structural presence with distinct technical character. Display titles utilize bold weight with tight negative letter tracking (`-0.04em`) to mirror the impactful, geometric Hermes Agent visual lockup.
2. **Inter (Body & Controls):** Uncompromising clarity for rapid interface scanning, system controls, and contextual body copy. Set in standard letterform weights with balanced line heights.
3. **JetBrains Mono (Telemetry & Keybindings):** Monospaced precision for system state badges, AES-256 telemetry readouts, commit hashes, and keyboard shortcuts (`⌘ + N`).

## Layout & Spacing

The layout is built upon an application shell paradigm optimized for high-density desktop displays:

- **Mac Window Frame:** Bound by an outer rounded shell (radius `16px`) with native 3-button traffic light controls aligned at `x: 16px, y: 16px`.
- **Sidebar (Collapsible):** Fixed standard width of `240px` (contracting to `64px` icon-only or hidden). Uses `space-sm` padding for stacked nav items and `space-md` outer gutters.
- **Main Canvas:** A flexible viewport containing a top sticky sub-header (`48px` height) with dropdown breadcrumbs and global tool controls, an expandable middle workspace, and a bottom input/interaction dock.
- **Telemetry Status Strip:** Fixed `32px` bottom tray anchored at the bottom edge, spanning edge-to-edge. Dividers within use `0.5px` vertical hairline borders in `#e2e8f0` with `space-md` horizontal gaps between telemetry items.

## Elevation & Depth

This design system rejects deep, heavy skeuomorphic drop shadows in favor of ambient airiness and surgical flat delineation:

- **Tonal Separation:** Depth is primarily established through surface transitions: Sidebar `#f0f6ff` against Main Canvas `#ffffff`.
- **Micro-Shadows for Floating Prompts:** The central conversational action input bar and active floating context cards float above the viewport using an extra-diffused, cool-tinted shadow:
  `box-shadow: 0 4px 20px -2px rgba(37, 99, 235, 0.05), 0 2px 6px -1px rgba(15, 23, 42, 0.04);`
- **Hairline Outlines:** Surfaces are bounded by thin `1px` structural borders (`#e2e8f0` or translucent `#bfdbfe`), ensuring absolute clarity on Retina and 4K panels.
- **Subtle Backdrops:** Floating command palettes and popovers utilize `backdrop-filter: blur(12px)` over 90% opaque white backdrops.

## Shapes

The interface embraces a tailored rounded geometry (`roundedness: 2`), reflecting precision engineering with friendly ergonomics:

- **Main Window Enclosure:** `16px` outer border radius.
- **Sidebar Interactive Rows & List Selectors:** `8px` (`rounded-md`) for hover highlights and active states.
- **Floating Input Fields & Docks:** `12px` to `16px` pill-like soft rectangles with internal micro-actions.
- **Micro Badges & Telemetry Chips:** `4px` to `6px` for tags, version hashes, and keyboard glyph enclosures.
- **Round Action Nodes:** Fully circular (`rounded-full`) reserved strictly for microphone inputs, audio wave triggers, avatar badges, and status indicator pips.

## Components

### Buttons & Quick Actions
- **Primary:** High-saturation cobalt background (`#1d4ed8`), crisp white text (`#ffffff`), `rounded-md` (`8px`), font: `Inter` Medium (`13px`). Subtle hover brightening to `#2563eb`.
- **Secondary / Ghost:** Transparent surface with muted slate text (`#475569`). On hover, transitions to `#f0f6ff` with `#1d4ed8` icon and text tinting.
- **Circle Action Button:** Solid black (`#0f172a`) or electric blue pill-circle for submission triggers with centered micro-glyphs (such as waveform audio or prompt submit).

### Primary Input Bar
- Floating rounded vessel (`12px` radius) positioned at the bottom of the active viewport.
- Surface: Crisp `#ffffff` encapsulated by a `1px` border (`#e2e8f0`), transitioning on focus to an illuminated electric ring (`#bfdbfe`).
- Prepend: `+` action button in neutral slate.
- Append: Voice dictation waveform trigger and rounded submission control.

### Navigation List & Items
- Height: `36px` per item.
- Left-aligned icon (`18px`) followed by `label-md` (`13px`).
- Right-aligned monospaced keyboard shortcuts styled inside a micro-container (`#ffffff`, border `#e2e8f0`, radius `4px`).
- Active state: `#ffffff` or light sky `#dbeafe` tint with `#1d4ed8` high-weight text.

### Telemetry Bar & Status Chips
- Height: `32px`, border-top: `1px solid #e2e8f0`, background: `#ffffff`.
- Typography: `JetBrains Mono` at `11px`.
- Status indicators feature an active blinking or solid dot (`#10b981` green for gateway ready).
- Key telemetry clusters:
  - Left: Command symbol (`⌘`), Gateway ready icon, Agents, Cron job scheduler.
  - Right: Model runtime (`glm-5.1 ollama-cloud`), Version string in cobalt (`#1d4ed8`), Git hash (`79bfddd`).

### Cards & Tool Call Artifacts
- Base: Pure white card `#ffffff` nestled on subtle canvas `#f8fafc`.
- Header: Space Grotesk `headline-sm` accompanied by tool category pills.
- Border: `1px solid #e2e8f0`, elevating with a sky-blue accent line (`#bfdbfe`) during active agent processing.