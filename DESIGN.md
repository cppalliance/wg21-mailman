# WG21 Mailman - Design Tokens

Single source of truth for the visual language shared by Postorius and HyperKitty.
These tokens are implemented as CSS custom properties in `static_custom/wg21/css/theme.css`
and consumed by `components.css` and both apps' templates. If you change a value
here, update `theme.css` in the same commit (and vice versa).

## Color

Token values are authored in OKLCH; the original hex is kept in a trailing comment in `theme.css` (and listed here) for findability. For a translucent variant of a token, use relative color syntax to override just the alpha: `rgb(from var(--token) r g b / N%)` rather than baking alpha into the value.

### Brand

- `--wg21-navy: oklch(30.48% 0.074 264.66)` /* #1c2d54 */ - primary navy (navbar, primary buttons, table header, headings ink)
- `--wg21-navy-grad-top: oklch(30.06% 0.0558 264.92)` /* #202D4A */ - navbar gradient start
- `--wg21-navy-grad-bottom: oklch(30.06% 0.0558 264.92)` /* #202D4A */ - navbar gradient end
- `--wg21-gold: oklch(65.98% 0.1084 79.72)` /* #b58a3c */ - primary gold (frame borders, accents, eyebrow, active pill)
- `--wg21-gold-accent: oklch(76.65% 0.1387 91.06)` /* #D4AF37 */ - bright gold accent (active utility-bar link)
- `--wg21-gold-bright: oklch(70.59% 0.1116 86.16)` /* #bf9b46 */ - CTA "SIGN UP" fill / active utility-bar link
- `--wg21-gold-dark: oklch(54.61% 0.09 79.81)` /* #8c6a2c */ - gold hover / pressed; hover bg under `.wg21-btn--gold`
- `--wg21-gold-pale: oklch(82.36% 0.0653 86.27 / 0.549)` /* #D8C3958C */ - softened gold (alpha carried in the token) for the navbar wordmark
- `--wg21-black-bar: oklch(14.48% 0 none)` /* #0A0A0A */ - top utility bar background
- `--wg21-white: oklch(100% 0 none)` /* #FFFFFF */ - pure white (hover text on dark surfaces)



### Surfaces

- `--wg21-page-bg: oklch(100% 0 none)` /* #FFFFFF */ - app background outside cards
- `--wg21-marble: url("../img/marble-bg.png")` - hero/footer marble texture (delivered)
- `--wg21-surface: oklch(97.03% 0.007 88.64)` /* #f7f5f0 */ - near-white card/marble base color (fallback under marble)
- `--wg21-surface-white: oklch(100% 0 none)` /* #ffffff */ - plain white content panel



### Text

- `--wg21-ink: oklch(30.23% 0.0754 265.69)` /* #1C2C54 */ - primary heading/text navy
- `--wg21-body: oklch(0% 0 none)` /* #000000 */ - body copy
- `--wg21-muted: color-mix(in oklab, var(--wg21-body) 55%, transparent)` /* #0000008C */ - secondary/description text (body at ~55%)
- `--wg21-on-navy: oklch(100% 0 none)` /* #FFFFFF */ - text on navy surfaces
- `--wg21-on-navy-muted: oklch(76.95% 0.021 267.24)` /* #aeb4c2 */ - muted text/placeholder on navy (e.g. search field)
- `--wg21-on-black-bar: oklch(83.6% 0.0043 271.36)` /* #c8c9cc */ - text/links on the black utility bar
- `--wg21-on-gold: oklch(30.23% 0.0754 265.69)` /* #1C2C54 */ - text on gold surfaces



### Links / state

- `--wg21-link: oklch(47.78% 0.1208 251.01)` /* #1c5f9e */ - link color
- `--wg21-link-hover: oklch(65.98% 0.1084 79.72)` /* #b58a3c */ - link hover (gold)
- `--wg21-border: oklch(90.97% 0 none)` /* #E1E1E1 */ - subtle borders/dividers



### Semantic (Bootstrap alert/button mapping)

- `--wg21-success: oklch(47.46% 0.0998 147.7)` /* #2f6b3a */
- `--wg21-danger: oklch(48.53% 0.1319 25.58)` /* #9c3a36 */
- `--wg21-warning: oklch(56.55% 0.1203 67.39)` /* #a4660e */
- `--wg21-info: oklch(47.78% 0.1208 251.01)` /* #1c5f9e */



### Inputs on dark surfaces

- `--wg21-input-on-navy-bg: oklch(0% 0 none / 0.28)` /* rgba(0,0,0,0.28) */ - navbar search field background
- `--wg21-input-on-navy-border: oklch(100% 0 none / 0.18)` /* rgba(255,255,255,0.18) */ - navbar search field border



## Typography

Loaded via Google Fonts (CDN) in both base templates:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=DM+Serif+Text:ital@0;1&family=EB+Garamond:ital,wght@0,400..800;1,400..800&family=IBM+Plex+Mono:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;1,100;1,200;1,300;1,400;1,500;1,600;1,700&display=swap" rel="stylesheet">
```



### Families

- `--wg21-font-heading: "DM Serif Text", Georgia, serif` - large display titles
- `--wg21-font-serif: "EB Garamond", Georgia, serif` - table/column labels, eyebrows, serif accents
- `--wg21-font-body: "DM Sans", system-ui, sans-serif` - body, controls, descriptions
- `--wg21-font-mono: "IBM Plex Mono", ui-monospace, monospace` - navbar + black utility bar



### Scale

- `--wg21-fs-hero: 7.75rem` - hero title ("WG21.org Mailing Lists")
- `--wg21-fs-h1: 2rem`
- `--wg21-fs-h2: 1.5rem`
- `--wg21-fs-lead: 1.125rem` - hero subtitle
- `--wg21-fs-body: 1rem`
- `--wg21-fs-sm: 0.875rem`
- `--wg21-fs-eyebrow: 0.8125rem` - uppercase eyebrow / utility bar
- `--wg21-lh-tight: 1.1`
- `--wg21-lh-base: 1.5`
- `--wg21-tracking-eyebrow: 0.08em`



## Spacing

4px base scale.

- `--wg21-space-1: 0.25rem`
- `--wg21-space-2: 0.5rem`
- `--wg21-space-3: 0.75rem`
- `--wg21-space-4: 1rem`
- `--wg21-space-6: 1.5rem`
- `--wg21-space-8: 2rem`
- `--wg21-space-12: 3rem`
- `--wg21-container-max: 1920px`

