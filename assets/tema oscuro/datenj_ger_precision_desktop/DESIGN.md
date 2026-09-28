---
name: DatenJäger Precision Desktop
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#c3c6d7'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#8d90a0'
  outline-variant: '#434655'
  surface-tint: '#b4c5ff'
  primary: '#b4c5ff'
  on-primary: '#002a78'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#0053db'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#adc6ff'
  on-tertiary: '#002e6a'
  tertiary-container: '#0f69dc'
  on-tertiary-container: '#edf0ff'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#d8e2ff'
  tertiary-fixed-dim: '#adc6ff'
  on-tertiary-fixed: '#001a42'
  on-tertiary-fixed-variant: '#004395'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
  traffic-close: '#ff5f56'
  traffic-minimize: '#ffbd2e'
  traffic-expand: '#27c93f'
  surface-glass-light: rgba(248, 250, 252, 0.82)
  surface-glass-dark: rgba(15, 23, 42, 0.78)
  border-subtle-light: '#e2e8f0'
  border-subtle-dark: rgba(255, 255, 255, 0.08)
  canvas-paper: '#f8fafc'
  canvas-cosmic: '#0b0f19'
  status-verified: '#10b981'
typography:
  display-hero:
    fontFamily: Space Grotesk
    fontSize: 44px
    fontWeight: '700'
    lineHeight: 52px
    letterSpacing: -0.03em
  display-hero-mobile:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Manrope
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  body-sm:
    fontFamily: Manrope
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: -0.01em
  label-badge:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.02em
  caption-mono:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '400'
    lineHeight: 14px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  margin: 1.25rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.875rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style

The design system blends tactical data intelligence with macOS-grade desktop craftsmanship. Built for high-leverage data operations, secure vault governance, and intelligence workflows, it evokes an atmosphere of sovereign control, cryptographic precision, and unhurried editorial clarity.

The visual language draws from **High-End Desktop Minimalism** and **Technical Glassmorphism**:
- **Tactical Translucency:** Frosted multi-layered sidebars, clean window title chrome, and floating HUD controls that anchor the user into an Electron-driven workspace.
- **Vibrant Cryptographic Accents:** Electric cobalt blue functions as the primary visual anchor across displays, complemented by deep space darks and verified emerald badges signaling cryptographic integrity (e.g. AES-256-GCM).
- **Hybrid Editorial Engineering:** Subtle neoclassical, high-impact titling paired with utilitarian monoespaced and humanist sans-serif metadata, maintaining high legibility during dense analytical tasks.

## Colors

The palette establishes high chromatic tension between deep void-like backdrops, frosted structural planes, and an electric signature blue.

- **Primary Electric Blue (`#2563eb`, `#3b82f6`):** Used for primary command triggers, active session highlights, focal branding typography, and focal interaction states.
- **Neutral Deep Cosmic (`#0f172a`, `#0b0f19`):** The primary canvas in dark mode, reflecting the emblematic dark navy circle of the brand identity while eliminating ocular fatigue.
- **Secondary Emerald Verified (`#10b981`):** Reserved exclusively for cryptographic health indicators, secure ledger syncs, and AES-256-GCM hardware confirmations.
- **Subtle Glass & Paper:** In light mode or dual-pane contexts, surfaces utilize frosted paper whites (`#f8fafc`, `#f1f5f9`) bounded by hairline borders (`#e2e8f0` in light, `rgba(255, 255, 255, 0.08)` in dark).
- **Desktop Window Chrome:** System traffic lights follow Apple human interface norms (`#ff5f56`, `#ffbd2e`, `#27c93f`) with 12px dimensions and micro-stroke insets.

## Typography

The typographic hierarchy bridges high-tech data tooling and editorial balance:

- **Display & Section Headers (`Space Grotesk`):** Technical, angular, and authoritative. Used for primary app heroes, brand signatures, modal titles, and section dividers.
- **Interface & Operational Reading (`Manrope`):** Balanced, clean humanist geometric sans-serif ensuring effortless comprehension across dense multi-column tables, logs, and prompt chats.
- **Terminal & Telemetry Metadata (`JetBrains Mono`):** Dedicated to cryptographic hashes, AES-256 keys, model runtime counters, bottom status telemetry, keyboard shortcuts, and code blocks.

## Layout & Spacing

The layout is built for native multi-pane desktop containment in Electron with React:

- **Frame Architecture:**
  - **Window Titlebar / Traffic Control Zone:** 44px fixed height with inline window controls (`-webkit-app-region: drag`), document breadcrumb, and top-right global actions.
  - **Collapsible Master Sidebar:** Fixed standard width of 240px (compacts to 64px or icon rail). Houses workspace switchers, primary modules, and session navigators.
  - **Central Stage / Canvas:** Fluid canvas with strict centered max-width (768px for conversational/query flows; 100% fluid for tabular data inspect views).
  - **Floating Command Island:** Floating bottom input docking 24px above the bottom bar, spanning 720px max width.
  - **Telemetry Status Strip:** 28px bottom status bar displaying engine health, cryptographic modes, model routing, and git hashes.
- **Responsive Adaptations:**
  - On narrow desktop windows (<900px), the sidebar auto-folds into a slide-over drawer and the bottom status bar truncates secondary hashes to prioritize cryptographic connectivity indicators.

## Elevation & Depth

Visual hierarchy leverages hardware-accelerated translucent planes rather than heavy drop shadows:

1. **Backing Window Canvas (Level 0):** Deep cosmic slate `#0b0f19` or muted crisp parchment `#f8fafc`.
2. **Sidebar & Structural Dividers (Level 1):** Semi-transparent frosted surface (`backdrop-blur-xl bg-slate-900/60` or `bg-slate-50/80`) bounded by 1px hairline borders (`rgba(255, 255, 255, 0.07)` or `#e2e8f0`).
3. **Floating HUD Controls & Command Bar (Level 2):** Layered above the stage with `backdrop-blur-md`, subtle inner white highlight (`inset 0 1px 0 0 rgba(255, 255, 255, 0.1)`), and an ambient soft shadow (`0 12px 32px -8px rgba(0, 0, 0, 0.35)`).
4. **Contextual Flyouts, Menus & Tooltips (Level 3):** Crisp solid glass popovers with 1px border perimeter and swift ease-out micro-transitions (150ms).

## Shapes

The design system maintains a refined balance between soft modern curves and engineering ergonomics:

- **Standard Elements (0.5rem / 8px):** Buttons, navigation pill items, code inspector containers, and input fields.
- **Window Shell & Floating Cards (0.75rem - 1rem / 12px - 16px):** Outer window container (macOS radius), floating prompt island, and primary modular cards.
- **Status Pills & Keyboard Badges (9999px / Pill):** Status indicators, shortcut badges (e.g. `⌘K`, `⇧N`), and telemetry chips.

## Components

### Window Chrome & Traffic Controls
- Three 12px circular buttons aligned horizontally with 8px gaps (`#ff5f56`, `#ffbd2e`, `#27c93f`), featuring subtle inset stroke on hover with symbol glyphs (+, -, ×).
- Titlebar displays active session name with breadcrumbs in `Manrope` 13px medium, accompanied by quick-switch chevrons.

### Sidebar Navigation & Items
- Sidebar items feature 8px corner radius, 8px vertical padding, 12px horizontal padding.
- Active items use a translucent electric tint (`bg-blue-600/10 text-blue-500 font-medium` in dark mode; `bg-blue-50 text-blue-700` in light mode).
- Inline shortcut badges rendered in `JetBrains Mono` with soft hairline border.

### Floating Command Bar / Search Input
- Centered dock with 14px corner radius, floating 24px above bottom status.
- Left-aligned action toggle (`+` attachment or mode switcher), fluid prompt text entry, right-aligned mic / audio trigger, and primary execution button styled in solid electric blue (`#2563eb`).

### Badges & Telemetry Strip
- 28px height, flex-row items spaced with delicate pipe dividers (`|` or subtle dots).
- Security tags display an emerald beacon dot (`w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981]`) followed by `AES-256-GCM` or `Gateway ready`.
- Model & runtime counters formatted strictly in `JetBrains Mono` 11px.

### Buttons & Quick Actions
- **Primary:** Solid `#2563eb` with crisp white text, micro top-edge bevel via inner shadow, hover transition to `#1d4ed8`.
- **Ghost / Tooling:** Transparent background with subtle hover fill (`hover:bg-white/5` dark, `hover:bg-slate-200/50` light).
- **Icon Action Buttons:** Fixed 32x32px or 28x28px targets with centered 16px vector icons.