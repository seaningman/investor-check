# Cala (cala.ai) — Visual Identity

Taken from the cala.ai page source, stylesheet and image assets on 15 November 2026.

## Design style

- **Warm and paper-like.** Dark brown on beige, with no pure white page and no pure black text.
- **Handmade.** A brush-painted logo, black marker doodles and hand-drawn strikethrough lines.
- **Editorial.** Large, light serif headlines with a lot of space around them.
- **Flat.** No gradients, glows or glass effects; colour is used in solid blocks.
- **Soft.** Rounded corners throughout.
- **Playful accents.** Bright blue, yellow, orange and pink appear sparingly against the neutral base.

The overall effect is deliberately unlike the dark, neon look common to AI infrastructure brands.

## Colour palette

Values come from the site's CSS variables. Hex values marked ≈ are converted from `oklch`.

### Base

| Role | Name | Value |
| :- | :- | :- |
| Page background | beige | `#f6e8cd` |
| Card background | beige-50 | `#fcf8f0` |
| Hover / accent surface | beige-200 | `#f1dbb7` |
| Text, primary buttons | brown-900 | `oklch(32% .015 54.05)` ≈ `#39312c` |
| Text on primary buttons | beige-50 | `#fcf8f0` |
| Borders, inputs, muted text | brown-500 | `oklch(62.4% .028 52.01)` ≈ `#968378` |
| Darkest brown | brown | `#2e2723` |

### Accents

| Name | Main | Ramp (light → dark) |
| :- | :- | :- |
| Blue | `#30bfff` | `#dff2ff` `#b8e7ff` `#78d5ff` `#30bfff` `#06a8f1` `#0086ce` `#006ba7` |
| Yellow | `#ffc234` | `#fff3c6` `#ffe488` `#ffd14a` `#ffc234` |
| Pink | `#e1bee6` | `#efdcf2` `#e1bee6` `#ba72c3` `#9f53a6` |
| Orange | `#fb6f3f` | — |

## Typography

| Use | Typeface | Foundry |
| :- | :- | :- |
| Headlines | Tiempos Headline Light | Klim Type Foundry |
| Body and interface | KMR Waldenburg, regular and italic | KMR Studio |
| Display accents | ABC Stefan, Simple and Bubble cuts | Dinamo |
| Code | System monospace | — |

- Headlines are set large (up to 4.5rem) with tight line height (1 to 1.2).
- Weights stay light to medium (400 to 500); there is no heavy bold.
- All three brand typefaces are commercial and need a licence. Free near-matches: a light transitional serif such as Source Serif or Newsreader for headlines, and a plain grotesque such as Inter for body.

## Logo

- **Symbol:** two nested "C"-shaped strokes painted with a dry brush, with visible bristle texture.
- **Wordmark:** "cala" in lowercase, in a high-contrast serif.
- **Colour:** dark warm brown on a light background, single colour only.
- **Favicon:** the brush symbol alone.
- **Files:** `https://cala.ai/assets/logo-BdVDbwHk.png` (transparent background), `https://cala.ai/favicon.png`.

## Illustration

- Black marker line drawings with an uneven, hand-drawn stroke and no fill: a smiling robot with heart eyes, a funnel, a plug, a graph.
- Hand-drawn lines that cross out a word, used in the "Cala is ~~clutter~~ clarity" headlines.

## Shape and layout

- Corner radius: 0.625rem base, 1rem and 1.5rem on larger cards.
- Borders are thin and brown (`brown-500`) rather than grey.
- Spacing is built on a 0.25rem unit.
- Content sits in centred columns between 24rem and 72rem wide.
