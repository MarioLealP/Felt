---
name: Nocturnal Atelier
colors:
  surface: '#00132c'
  surface-dim: '#00132c'
  surface-bright: '#283a54'
  surface-container-lowest: '#000e23'
  surface-container-low: '#071c35'
  surface-container: '#0c2039'
  surface-container-high: '#182b44'
  surface-container-highest: '#233550'
  on-surface: '#d4e3ff'
  on-surface-variant: '#e0bec2'
  inverse-surface: '#d4e3ff'
  inverse-on-surface: '#1e314b'
  outline: '#a7898d'
  outline-variant: '#594044'
  surface-tint: '#ffb2bd'
  primary: '#ffb2bd'
  on-primary: '#670024'
  primary-container: '#f7577c'
  on-primary-container: '#5a001f'
  inverse-primary: '#b3224c'
  secondary: '#add0a7'
  on-secondary: '#1a371a'
  secondary-container: '#304e2f'
  on-secondary-container: '#9cbe97'
  tertiary: '#ffb59e'
  on-tertiary: '#5e1700'
  tertiary-container: '#dd7351'
  on-tertiary-container: '#531300'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffd9dd'
  primary-fixed-dim: '#ffb2bd'
  on-primary-fixed: '#400013'
  on-primary-fixed-variant: '#900036'
  secondary-fixed: '#c8ecc2'
  secondary-fixed-dim: '#add0a7'
  on-secondary-fixed: '#042107'
  on-secondary-fixed-variant: '#304e2f'
  tertiary-fixed: '#ffdbd0'
  tertiary-fixed-dim: '#ffb59e'
  on-tertiary-fixed: '#3a0a00'
  on-tertiary-fixed-variant: '#7e2c10'
  background: '#00132c'
  on-background: '#d4e3ff'
  surface-variant: '#233550'
typography:
  display-lg:
    fontFamily: Mochiy Pop One
    fontSize: 32px
    fontWeight: '400'
    lineHeight: 40px
  headline-lg:
    fontFamily: Mochiy Pop One
    fontSize: 22px
    fontWeight: '400'
    lineHeight: 30px
  headline-md:
    fontFamily: Mochiy Pop One
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 26px
  title-md:
    fontFamily: Zen Maru Gothic
    fontSize: 16px
    fontWeight: '700'
    lineHeight: 24px
  body-lg:
    fontFamily: Zen Maru Gothic
    fontSize: 15px
    fontWeight: '500'
    lineHeight: 24px
  body-md:
    fontFamily: Zen Maru Gothic
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  body-diary:
    fontFamily: Klee One
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 26px
  label-md:
    fontFamily: Zen Maru Gothic
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.04em
  label-sm:
    fontFamily: Zen Maru Gothic
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.06em
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
  space-md: 0.875rem
  space-lg: 1.25rem
  space-xl: 1.75rem
---

## Brand & Style

This design system crafts an intimate, tactile desktop sanctuary centered on an anime companion living directly on the user's workspace. It rejects the sterile, homogenized look of SaaS dashboards, corporate glassy overlays, and soulless modern gradients. Instead, it evokes the sensory warmth of a late-night study room: physical stationery, washi tape swatches, matte paper sticky notes, and the cozy narrative pacing of an interactive visual novel.

The personality balances quiet nocturnal comfort with expressive whimsy. The UI should make users feel accompanied rather than managed. Every surface behaves like physical material pinned or rested over a dark midnight canvas. In place of standard Unicode emojis, communication is driven by Japanese kaomoji (`( *´꒳\`*)`, `(｡•̀ᴗ-)✧`), hand-drawn micro-glyphs, and embroidered status patches.

## Colors

The palette simulates a softly lit desk in the dead of night, accented by colorful desk stationary, fabrics, and companion elements:

- **Canvas & Backgrounds**:
  - Root Desktop Void: `#051A33` (deepest nocturnal ground)
  - Surface Tier 1 (Window & Shell Panes): `#082245`
  - Surface Tier 2 (Panels, Drawers, Companion Stage): `#0B2C56`
  - Surface Headers & Anchors: `#083D77` (dense, grounding Navy)
  - Surface Paper / Light Layer (Stationery Notes, Pinned Slips): `#F5F0F6` (Lilac-White)
- **Accents & Personality**:
  - **Raspberry** (`#DA4167`): High-intensity focal point for vital alerts, unread counters, urgent pings, and companion affinity hearts.
  - **Sage** (`#7A9B76`): Calming, comforting signature hue reminiscent of the companion's oversized hoodie. Used for status indicators, peaceful tags, active dialogue selections, and soft highlights.
  - **Salmon** (`#F78764`): Warm physical stationery hue used for faux washi tape headers, pinned bookmark strips, and cheerful stickers.
- **Borders & Dividers**:
  - Dark Structural Border: `#133863`
  - Tactile Muted Sage Line: `rgba(122, 155, 118, 0.35)`
  - Paper Edge Inset: `rgba(8, 61, 119, 0.12)`

## Typography

The typographic hierarchy establishes clear structural emotional roles:

- **Display & Section Titles (`Mochiy Pop One`)**: Plump, chubby, character-driven letterforms for panel window titles, dialogue header names, and milestone achievements. Used sparingly to avoid visual fatigue.
- **Interface & Dialogue System (`Zen Maru Gothic`)**: Rounded Japanese gothic styling brings softness without sacrificing UI legibility. Serves as the primary operational voice for buttons, list items, menus, and system status readouts.
- **Notes, Companion Diary & Letters (`Klee One`)**: Evocative, delicate penmanship. Reserved strictly for companion thought bubbles, saved sticky memos, diary entries, personal letters, and intimate handwritten marginalia.

## Layout & Spacing

Because this interface operates as an ambient desktop companion and floating widget suite, layout revolves around modular floating palettes, HUD docks, and docked memo panels rather than static browser full-bleed layouts.

- **Modular Paneling**: Fixed-width floating windows (280px to 380px) and expandable bottom/side dock drawers.
- **Rhythm**: Compact 4px base step (`0.25rem`), prioritizing snug, organized containment over cavernous empty space.
- **Companion Proximity**: Dialogue panels maintain tight contextual anchoring (`space-sm` to `space-md`) relative to the companion's desktop sprite or avatar position.

## Elevation & Depth

No blur or glassmorphism is permitted. Surfaces gain depth through physical stacking metaphors, hard-edged paper offsets, and deep nocturnal shadows:

- **Base Void (`#051A33`)**: Desktop ambient root.
- **Layer 1 Shell (`#082245`)**: Structured window frame with a crisp 1.5px solid border in `#133863` and a grounded shadow: `0 4px 16px rgba(2, 10, 20, 0.65)`.
- **Layer 2 Interior Card (`#0B2C56`)**: Inset containers with subtle top-highlight borders (`1px solid rgba(122, 155, 118, 0.2)`).
- **Physical Stationery Overlay (`#F5F0F6`)**: Matte paper memos and prompt slips. They cast a sharp, tight drop shadow (`0 3px 0 rgba(8, 34, 69, 0.45)`) that simulates physical paper lying flat against dark cloth.
- **Washi Tape Elements**: Tilted strips (`-1deg` to `1.5deg` rotation) overlaying corners of cards with a translucent tint (`rgba(247, 135, 100, 0.85)`), featuring serrated edge masks.

## Shapes

The geometry balances soft hand-cut corners with organic charm:

- **Windows & Outer Panels**: Rounded corners (`0.75rem` / 12px) give shells a soft toy-box contour.
- **Inner Stationery & Slips**: Gentler corners (`0.375rem` / 6px) to emulate index cards and small paper swatches.
- **Washi Strips & Tape Tags**: Sharper profiles (`2px`) with semi-notched zigzag or clipped vertical boundaries.
- **Pill Counters & Badges**: Fully rounded capsules for unread badges, kaomoji mood chips, and affinity status gauges.

## Components

### Buttons
- **Primary (Companion Action / Urgent)**: `#DA4167` fill with `#F5F0F6` text, bold `Zen Maru Gothic`. Box shadow has a 2px downward paper-press offset: `0 3px 0 #9E2644`. On active click, transitions down `2px` with zero shadow to mimic a mechanical stamp.
- **Secondary (Cozy / Dialogue)**: `#0B2C56` base with a 1.5px `#7A9B76` border and `#F5F0F6` text. Hover shifts background to `#7A9B76` with `#051A33` text.
- **Ghost / Minor**: Clear background, `#7A9B76` text, soft hover outline with kaomoji prefix.

### Chips & Washi Badges
- **Status Chips**: Capsule-shaped pill badges (`#083D77`) with a solid 6px indicator dot in Sage (`#7A9B76`) or Raspberry (`#DA4167`).
- **Washi Tape Tags**: `#F78764` fill with slightly irregular padding (e.g. 2px top, 10px sides), uppercase micro-labels in `#051A33`, angled `transform: rotate(-1.5deg)` anchored across the top edge of cards.

### Cards & Notes
- **Dialogue / Interaction Box**: Deep `#082245` background with Navy `#083D77` speaker tag bar. Companion avatar sits nestled slightly breaking the top-left boundary.
- **Sticky Memo / Diary Card**: `#F5F0F6` paper tone, text in dark `#082245` using `Klee One`. Never use vertical accent-strip borders on the left side; instead, use a faux Salmon tape strip pinned across the top center.

### Inputs & Text Areas
- Nocturnal inset wells (`#051A33`) framed by a subtle 1px border (`#133863`). Focused state switches border to `#7A9B76` with an inner glow of `inset 0 1px 3px rgba(0,0,0,0.5)`. Caret color is vibrant `#DA4167`. Placeholder text in muted dusty lavender (`rgba(245, 240, 246, 0.4)`).

### Checkboxes & Radios
- **Checkbox**: Soft rounded squares (`4px` radius) with `#0B2C56` background and `#7A9B76` border. Checked state renders a bold Raspberry (`#DA4167`) checkmark glyph or heart stamp.
- **Radio Buttons**: Concentric circles; selected state features an inner solid dot of `#F78764`.

### Lists & Dialogue Choices
- Interactive options are styled as notebook tabs or sticker choices. Hovering shifts the item rightwards by 4px accompanied by a small custom glyph indicator (`✦` or `(｡•̀ᴗ-)`). Dividers between items use dashed, hand-stitched strokes (`1px dashed rgba(122, 155, 118, 0.25)`).