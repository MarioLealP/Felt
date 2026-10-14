---
name: Midnight Companion
colors:
  surface: '#00132e'
  surface-dim: '#00132e'
  surface-bright: '#003972'
  surface-container-lowest: '#000e25'
  surface-container-low: '#001b3d'
  surface-container: '#001f44'
  surface-container-high: '#002957'
  surface-container-highest: '#00346a'
  on-surface: '#d6e3ff'
  on-surface-variant: '#e0bec2'
  inverse-surface: '#d6e3ff'
  inverse-on-surface: '#003062'
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
  background: '#00132e'
  on-background: '#d6e3ff'
  surface-variant: '#00346a'
typography:
  display-lg:
    fontFamily: Epilogue
    fontSize: 36px
    fontWeight: '800'
    lineHeight: 44px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Epilogue
    fontSize: 28px
    fontWeight: '800'
    lineHeight: 36px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Epilogue
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 34px
  headline-md:
    fontFamily: Epilogue
    fontSize: 20px
    fontWeight: '700'
    lineHeight: 28px
  body-lg:
    fontFamily: Nunito Sans
    fontSize: 17px
    fontWeight: '500'
    lineHeight: 26px
  body-md:
    fontFamily: Nunito Sans
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-sm:
    fontFamily: Nunito Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  diary-entry:
    fontFamily: Literata
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 28px
    letterSpacing: 0.01em
  label-lg:
    fontFamily: Rubik
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.02em
  label-md:
    fontFamily: Rubik
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.04em
  label-sm:
    fontFamily: Rubik
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
  gutter: 1rem
  gutter-lg: 1.5rem
  margin: 1rem
  margin-md: 1.5rem
  margin-lg: 2.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.25rem
---

## Brand & Style

This design system delivers an intimate, tactile companion experience reminiscent of a cosy late-night gacha café or an in-game anime smartphone OS. The personality is warm, domestic, and quietly playful—anchored by an irreverent, teasing companion who resides in your pocket and desktop space. 

The aesthetic rejects sterile corporate SaaS conventions (no generic blur gradients, no neon glows, no left-border accent lines). Instead, it draws from **tactile skeuomorphic craft** combined with **Japanese pop-editorial print styling**:
- **Layered Paper & Scrapbook Ephemera:** Crisp paper card layers, washi tape bindings, metallic pushpins, lined notebook rules, and playful die-cut sticker stamps.
- **Deep Midnight Palette:** Dark, cosy room tones evoke 2:00 AM lamp-lit conversations with zero eye strain.
- **Micro-chunky Geometry:** Solid shapes with deliberate substance, plush pill-shaped triggers, and tactile press states that mimic physical handheld console cartridges and memo pads.

## Colors

The palette models a quiet, moonlit bedroom lit by warm lamps and soft screen glare.

- **Primary (`#DA4167` - Raspberry):** Reserved for unread pings, urgent indicators, active toggle pills, and high-energy interactive triggers.
- **Secondary (`#7A9B76` - Sage Green):** Reflects the companion's signature knit hoodie; used for ambient status badges, dialogue chips, foliage accents, and calm state confirmations.
- **Tertiary (`#F78764` - Salmon):** Applied strictly to tactile physical metaphors—translucent washi tape strips, pinned bookmarks, sticky note highlights, and playful reaction hearts.
- **Neutral Night Tiers (`#083D77` Navy base, accented by `#0B192C` Deep Abyss, `#062244` Midnight Slate, and `#122842` Elevated Slate):** Creates atmospheric depth without pitch-black harshness.
- **Surface Papers (`#F5F0F6` Lilac-White):** Forms real-world paper surfaces, journal inserts, note tags, and high-legibility typographic elements contrasting against dark containers.

## Typography

Typography establishes an intimate, conversational hierarchy through three distinct structural weights:

- **Display & Headlines (`Epilogue`):** Heavy, rounded geometric letterforms provide the chunky, playful cadence of Japanese pop banners and game titles.
- **Body Text (`Nunito Sans`):** Soft terminal curves that maintain exceptional readability on deep navy grounds while preserving a friendly, personal warmth.
- **Handwritten / Diary Notes (`Literata` / Editorial Serif Accent):** Used for personal scrapbook introspections, companion sticky notes, and margin scribbles to evoke physical paper journal pages.
- **Labels & Micro-UI (`Rubik`):** Sturdy, pill-friendly geometric forms for rapid recognition in badges, control buttons, status labels, and bottom navigation.

## Layout & Spacing

The layout operates on an 8pt base grid structured like a dedicated companion console.

- **Mobile Viewport (Core):** Single-column fluid view locked between `margin: 1rem` side boundaries. Vertical breathing room is tuned for thumb reach, anchored by a bottom dock navigation bar.
- **Tablet / Split Shell (600px - 1024px):** Two unequal columns (35% left companion viewport, 65% right interactive canvas: Notes, Chat, or Diary scrapbook).
- **Desktop Canvas (> 1024px):** Fixed-width central viewport (maximum `1200px`) centered on an atmospheric night desk background. Left column hosts the companion room stage; right area hosts the multi-pane journal and chat console with `gutter: 1.5rem`.
- **Rhythm Rules:** Stacked chat bubbles and diary cards strictly observe `space-sm` for clustered exchanges and `space-lg` between distinct timeline blocks.

## Elevation & Depth

Visual hierarchy does not use soft diffuse lighting or neon glows. Instead, it relies on **tactile paper planes and offset solid drop-depths**:

- **Layer 0 (Canvas):** Deep Navy backdrop (`#0B192C` to `#083D77`) with subtle vertical desk grain.
- **Layer 1 (Recessed Well / Hub):** `#062244` with a 1px solid stroke of `#122842`, housing chat timelines and feed modules.
- **Layer 2 (Paper & Memo Surfaces):** Lilac-white (`#F5F0F6`) and Muted Sage tint cards resting on a crisp, hard-edged physical shadow: `2px 3px 0px rgba(6, 34, 68, 0.85)`.
- **Layer 3 (Overlay Sticky Notes & Tape):** Rotated between -1.5deg and 1.5deg with an offset shadow: `3px 4px 0px rgba(0, 0, 0, 0.45)`. Semitransparent salmon washi tape accents (`rgba(247, 135, 100, 0.85)`) overlap outer edges.
- **Layer 4 (Modals, Popovers & Warning Lamp Cards):** Elevated panels surrounded by a deep midnight scrim, using a 2px border of `#DA4167` or `#7A9B76` and a crisp `4px 6px 0px #062244` offset backing.

## Shapes

The geometry is chunky, rounded, and physical (`roundedness: 2` = 0.5rem base, with 1rem `rounded-lg` and 1.5rem `rounded-xl`).

- **Cards & Scrapbook Mats:** Defined by `1rem` corner radii, evoking die-cut stationery and rounded acrylic photo holders.
- **Interactive Controls & Chips:** Fully pill-shaped (`9999px`) to create an approachable tactile button feel.
- **Chat Bubbles:** Asymmetrical radii (`1rem` on three corners, `0.25rem` on the speaking anchor tip).
- **Washi Tape Elements:** Rectangular strips with textured notched vertical edges, angled across paper corners.

## Components

### 1. Bottom Quick-Reach Navigation Dock
- **Architecture:** Floating rounded pill dock elevated above bottom screen edges. Deep midnight background (`#062244`) with a 1.5px border of `#122842`.
- **Items:** Chat, Feed/Notes, **Room (Center Focal)**, Alerts, Diary.
- **Center Focal ("Room"):** Enlarged floating circular button overlapping the dock top edge by 12px. Bordered in Sage Green (`#7A9B76`) with a plush bounce on tap.
- **Active State:** Raspberry background pill (`#DA4167`) with high-contrast Lilac-White icon. Unread counts appear as mini pill badges at the top right of icons.

### 2. Tactile Sticky Notes & Paper Cards
- **Surfaces:** Lilac-white `#F5F0F6` or pale cream surfaces with faint horizontal ruled lines (`rgba(8, 61, 119, 0.08)`).
- **Adornments:** Centered semi-translucent Salmon (`#F78764`) washi tape strip on the top edge, or an enameled metallic pushpin icon with an offset dark cast shadow.
- **Rotation:** Organic subtle tilt (-1° to +1.2°) applied to cards in feed views.

### 3. Cosy Dialogue & Commentary Bubbles
- **Companion (Felt):** Left-aligned card in Sage Green tone (`#7A9B76` surface or Lilac-White with Sage 2px border). Accompanied by a mini smug/winking companion portrait badge resting on the upper-left crest.
- **User Message:** Right-aligned `#083D77` container with crisp `#122842` stroke and Lilac-White typography.

### 4. Warning Lamp Alert Card
- **Structure:** Solid `#0B192C` container with an emergency accent strip of Raspberry (`#DA4167`) at the top edge.
- **Indicator:** An illustrated retro desk warning lamp icon that transitions between warm amber glow (warning) and pulsing raspberry (urgent).
- **Actions:** Dual pill buttons—an outline secondary action ("Handled") and a filled Raspberry primary action ("Ask Felt").

### 5. Diary & Scrapbook Pages
- **Layout:** Notebook-bound sheet motif with circular binder punch-holes down the left gutter.
- **Content:** Lined text regions with handwritten styling (`Literata`), accompanied by collector sticker stamps and a corner pin/veto toggle button.

### 6. Messenger Audio Waveform Bar
- **Input Field:** Rounded pill shell with an integrated mic trigger.
- **Hold-to-Talk State:** Expands into a dynamic Sage-to-Raspberry bar graph waveform that scales with mic sensitivity, providing tactile audio feedback while recording.

### 7. Buttons & Badges
- **Buttons:** Chunky pills with a 2px offset solid drop-depth that depresses flush (`translate(1px, 2px)`) on active press.
- **Badges:** Compact capsules with uppercase `label-sm` typography and high-contrast tinted fills.