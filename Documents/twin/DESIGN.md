---
name: ME-DT Presentation
description: Thesis slide deck for the Mythos-Enhanced Digital Twin framework — five layers, nine attacks, one argument.
colors:
  bg: "#f5f5f0"
  surface: "#ecece6"
  border: "#c8c8c0"
  text: "#0a0a0a"
  muted: "#767670"
  alert-red: "#e63946"
  water-teal: "#2dd4bf"
  power-amber: "#ffc840"
  traffic-violet: "#a855f7"
typography:
  display:
    fontFamily: "'DM Sans', sans-serif"
    fontSize: "clamp(2.5rem, 7vw, 6.5rem)"
    fontWeight: 800
    lineHeight: 1.04
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "'DM Sans', sans-serif"
    fontSize: "clamp(1.4rem, 3vw, 2.8rem)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.025em"
  title:
    fontFamily: "'DM Sans', sans-serif"
    fontSize: "clamp(0.9rem, 1.6vw, 1.3rem)"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "'DM Sans', sans-serif"
    fontSize: "clamp(0.75rem, 1.4vw, 1rem)"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "'DM Mono', monospace"
    fontSize: "clamp(9px, 1.1vw, 11px)"
    fontWeight: 600
    letterSpacing: "0.18em"
rounded:
  none: "0px"
  sm: "2px"
  pill: "20px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "14px"
  section: "clamp(1.5rem, 4vw, 3rem)"
components:
  card:
    backgroundColor: "#ffffff"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "clamp(0.8rem, 2vw, 1.4rem)"
  card-hover:
    backgroundColor: "#ffffff"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "clamp(0.8rem, 2vw, 1.4rem)"
  badge-alert:
    backgroundColor: "#f9e6e7"
    textColor: "{colors.alert-red}"
    rounded: "{rounded.pill}"
    padding: "4px 12px"
  badge-neutral:
    backgroundColor: "rgba(10,10,10,0.06)"
    textColor: "{colors.muted}"
    rounded: "{rounded.pill}"
    padding: "4px 12px"
  layer-bar:
    backgroundColor: "#ffffff"
    textColor: "{colors.text}"
    rounded: "{rounded.none}"
    padding: "clamp(8px, 1.5vh, 14px) clamp(14px, 2.5vw, 24px)"
  nav-arrow:
    backgroundColor: "rgba(255,255,255,0.92)"
    textColor: "{colors.muted}"
    rounded: "{rounded.pill}"
    size: "36px"
---

# Design System: ME-DT Presentation

## 1. Overview

**Creative North Star: "The Calibrated Observer"**

This is a scientist's instrument panel brought to the page. Every element earns its place through function. The background is warm archive paper with a faint 40x40px crosshatch grid — the kind that appears on engineering graph paper and oscilloscope screens — present but never distracting. Surfaces are white lifted from that ground. The single accent, Alert Red, is reserved for what demands attention: active threats, confirmed detections, the live progress bar, and the active navigation dot. Everything else runs in warm grays and near-black ink.

The presentation is not performing. It is demonstrating. The design philosophy follows the thesis argument: show the evidence, let it speak, do not dress it up. Each slide has a single primary claim delivered by a tightly-kerned headline. Supporting material is typographically smaller, structurally subordinate. The argument advances in straight lines; the layout follows.

This system explicitly rejects the aesthetics of startup pitch decks: urgency cliches, large metric callout boxes, confetti transitions, and gradient-soaked hero sections. It equally rejects the theatrical dark-mode aesthetic that reaches for neon glows or excessive terminal chrome used decoratively. The subject matter is serious; the design matches that register.

**Key Characteristics:**
- Warm off-white ground with engineering graph-paper grid at 3.2% opacity
- One accent color (Alert Red, #e63946) at strict 10% or less surface coverage
- Three domain viz colors (water, power, traffic) appear only inside SVG diagrams and data bars, never as UI decoration
- Flat surfaces at rest; mechanical-click offset shadow on hover
- DM Sans for all prose hierarchy; DM Mono for all labels, measurements, and identifiers
- All motion uses `cubic-bezier(.16,1,.3,1)` (ease-out-expo); no bounce, no elastic

## 2. Colors: The Signal Palette

A restrained palette where warmth comes from the ground and precision comes from the ink. The single accent fires only at signal strength.

### Primary
- **Alert Signal** (`#e63946`): The one deliberate accent. Used for: the progress bar, active navigation dot, the ME-DT architecture layer highlight, alert-state rings, and TTD bar chart segments where ME-DT outperforms baselines. At 10% or less surface coverage on any given slide. Its rarity is the point — when it appears, something matters.

### Neutral
- **Deep Ink** (`#0a0a0a`): Body text, headlines, strong borders on hover states, the divider bar under headlines. Near-black, not pure black — warm toward the paper ground.
- **Calibrated Gray** (`#767670`): All secondary labels, sub-headings, monospaced readouts, muted descriptive text. The mid-tone that separates hierarchy levels without creating contrast noise.
- **Instrument Border** (`#c8c8c0`): Card edges, layer bar borders, slide nav dot rings. Present but unobtrusive.
- **Antique Surface** (`#ecece6`): Secondary surfaces such as bar track backgrounds. One step darker than the ground.
- **Warm Archive White** (`#f5f5f0`): The slide ground. Not white — warm with a faint yellow-beige cast. Cards and layer bars lift from this as pure white (#fff), creating a subtle surface hierarchy without shadows.

### Domain Signals (data-viz only — never UI decoration)
- **Water Teal** (`#2dd4bf`): WNTR and water network domain. Appears inside SVG node diagrams and bar chart segments only.
- **Power Amber** (`#ffc840`): pandapower and power grid domain. Same restriction.
- **Traffic Violet** (`#a855f7`): Synthetic traffic subsystem. Same restriction. Always accompanied by the "SYNTHETIC" label where it appears in context.

### Named Rules
**The One Signal Rule.** Alert Red is used on 10% or less of any slide surface. Adding a second accent, increasing its coverage, or applying it decoratively violates the rule. When the red fires, it must mean something.

**The Domain Containment Rule.** Water Teal, Power Amber, and Traffic Violet are semantic data signals, not palette colors. They do not appear on slide backgrounds, card borders, heading accents, or any UI surface outside SVG diagrams and data bar segments.

## 3. Typography

**Display Font:** DM Sans (Google Fonts, preloaded)
**Label/Mono Font:** DM Mono (Google Fonts, preloaded)

**Character:** DM Sans at heavy weights has the compressed authority of a well-typeset academic figure caption — compact, legible at distance, undecorated. DM Mono grounds every label, readout, and identifier in the register of instrumentation: the numbers look like they came off a measuring device. The pairing works because both share the same optical weight center and neither competes for personality.

### Hierarchy
- **Display** (800 weight, clamp(2.5rem, 7vw, 6.5rem), line-height 1.04, tracking -0.03em): Title and closing slide H1 only. The tightest tracking in the system.
- **Headline** (700 weight, clamp(1.4rem, 3vw, 2.8rem), line-height 1.1, tracking -0.025em): Each slide's primary claim. One per slide.
- **Title** (600 weight, clamp(0.9rem, 1.6vw, 1.3rem)): Card headings and domain sub-labels. Clearly subordinate to Headline.
- **Body** (400 weight, clamp(0.75rem, 1.4vw, 1rem), line-height 1.6, max 52ch): Descriptive text on two-column slides and card body copy. Line length capped at 52ch in the current implementation; on single-column text blocks 65ch is the ceiling.
- **Label** (DM Mono, 600 weight, clamp(9px, 1.1vw, 11px), tracking 0.18em, uppercase): Slide category labels, card-head classifications, nav counter. The only element using uppercase with wide tracking.

### Named Rules
**The Single Sans Rule.** DM Sans covers every prose role from Display down to Body. No secondary serif, no condensed variant. Hierarchy is expressed through scale and weight alone.

**The Mono Discipline Rule.** DM Mono appears only where the content is a measurement, a classification label, an identifier, or code. It does not appear in prose. Its monospaced character signals "this is a reading off an instrument."

## 4. Elevation

This system is flat by default. Surfaces carry no ambient shadow; the paper ground and white card surfaces are differentiated by lightness alone. The only shadow in the system fires as a state response to hover interaction.

### Shadow Vocabulary
- **Mechanical Click** (`box-shadow: 3px 3px 0 rgba(0,0,0,0.1)` combined with `transform: translate(-1px, -1px)`): Applied to cards, layer bars, and action elements on hover. The directional offset and simultaneous translate create the physical sensation of pressing a key cap — the card moves toward the cursor and the shadow appears behind it. Not ambient, not diffuse. Zero blur radius. Structural and deliberate.
- **Alert Pulse** (animated `box-shadow: 0 0 0 16px rgba(230,57,70,0)` via `pulseRing` keyframe): Applied to threat-tier rings at QUARANTINE level only. The expanding-then-fading ring is the visual equivalent of a heartbeat monitor alarm. Used precisely once per semantic context.

### Named Rules
**The Flat-By-Default Rule.** Surfaces at rest carry no shadow. Elevation is earned by state, not assumed as decoration.

**The Click-Not-Float Rule.** The Mechanical Click shadow is an offset stroke with zero blur: `3px 3px 0`. If the shadow has a blur radius greater than 0, it is the wrong effect and changes the semantics from mechanical to floating.

## 5. Components

### Slides (Signature Component)
Each slide is a full-viewport centered container with overflow hidden. Content is flex-column, vertically and horizontally centered. Padding scales from 1.5rem to 3.5rem with the viewport. Slides transition with opacity and translateY(28px) using ease-out-expo over 520ms — appearing to rise into place, departing by rising away. A staggered reveal system (`data-r` attributes) orchestrates content elements at 70ms intervals.

### Layer Bars
Three-column grid (layer number, layer name, technology stack). White background, 1px border, no radius. Hover triggers Mechanical Click. A shimmer sweep (`::before` pseudo-element, 450ms) crosses the bar on hover — a scan-line effect evoking signal acquisition. The AI layer (L4) renders its name and border accent in Alert Red.

### Cards
White background, 1px `--border` edge, 2px radius (the minimum rounding to prevent sharp corners from reading as errors). Hover triggers Mechanical Click. Internal padding scales with viewport. Cards do not nest; nested cards are prohibited.

### Badges and Chips
Two variants: Alert (light red tint background, Alert Red border and text) and Neutral (dark 6% tint, muted border and text). Pill radius (20px). Mono font, uppercase, tight tracking. Used in the title slide as framework classifiers only.

### Tier Rings
Fixed-size circles (clamp(48px, 7vw, 70px)) with 3px colored border. Four tiers: NONE (muted gray), MONITOR, SANDBOX (both near-black), QUARANTINE (Alert Red with Alert Pulse). The ring is the status indicator; the border color is the threat level; the pulse is the alarm.

### Navigation System
Progress bar (top, 2px, Alert Red) advances with each slide. Navigation dots (bottom center, 7px circles): inactive = Instrument Border; active = Alert Red at 1.4x scale. Arrow buttons (bottom right, 36px circles, 92% white background): muted default, border and text shift to Alert Red on hover. Slide counter (top right, DM Mono 9-11px, muted) shows `N / TOTAL`. Quiet and functional.

## 6. Do's and Don'ts

### Do:
- **Do** use Alert Red for one purpose per slide: the active nav dot, the architecture layer highlight, the progress bar, or a data signal — never stacked roles on the same screen.
- **Do** express hierarchy through scale and weight contrast with a ratio of at least 1.25 between adjacent typographic levels.
- **Do** keep the Mechanical Click shadow at exactly `3px 3px 0 rgba(0,0,0,0.1)` with zero blur radius. The zero-blur is the semantics.
- **Do** use DM Mono for every label, counter, classification tag, and domain readout. The mono register signals measurement.
- **Do** keep domain colors (Water Teal, Power Amber, Traffic Violet) inside SVG diagram boundaries and bar chart segments only.
- **Do** honor `prefers-reduced-motion` — all animations are already gated. Keep them gated on every new animation added.
- **Do** maintain 52ch maximum line length on body text within slide columns. Examiners read at distance on a projected screen.
- **Do** keep the engineering grid background at exactly `rgba(0,0,0,0.032)` opacity. Higher opacity turns a calibration aid into wallpaper.

### Don't:
- **Don't** use `border-left` or `border-right` greater than 1px as a colored accent stripe on any card, list item, or callout. This is the most frequent violation in the current codebase (`.l1-.l4` layer bars, inline-style card callouts in S2 and S12). Rewrite with full borders, background tints, or leading numbered identifiers instead.
- **Don't** add a second accent color to any slide. The palette is Restrained by design. A second accent is noise, not emphasis.
- **Don't** apply domain viz colors (teal, amber, violet) to UI elements: borders, button backgrounds, heading colors, badge tints. They are semantic data signals, not palette options.
- **Don't** use the generic slide-template vocabulary: bullet-point lists without visual hierarchy, uniform card grids where every card is identical in size and weight, clip-art icons.
- **Don't** use gradient text (background-clip: text with a gradient fill). Any emphasis that requires gradient text can be expressed through weight or scale.
- **Don't** use modal dialogs. The attack console opens as an overlay panel. Maintain that pattern for any new interactive layer.
- **Don't** introduce bounce or elastic easing curves. Every transition uses `cubic-bezier(.16,1,.3,1)`. Bouncy motion registers as playful in a room that expects rigor.
- **Don't** apply glassmorphism (backdrop-filter blur with semi-transparent surfaces) as decoration anywhere in the presentation layer.
