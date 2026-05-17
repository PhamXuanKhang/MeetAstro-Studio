# Cool Technical AI Design System

> A reusable UI style guide for a composed, high-density AI/developer tool interface. Use it to recreate the same visual language in another product without depending on this repository's internal file structure.

---

## 1. Product UI identity

This design system uses a cool, technical, AI/developer-tool interface language:

- **Dashboard app:** Linear/Vercel-inspired productivity dashboard with cool blue-tinted surfaces, translucent sidebars, compact controls, Material Symbols icons, and indigo brand accents.
- **Landing page:** dark developer SaaS landing page with midnight surfaces, indigo CTA treatment, controlled glow effects, and dense feature cards.
- **Docs site:** GitBook/Nextra-like documentation UI using Inter, white panels, sticky sidebars, right TOC, and indigo accent links.

### Similar market references

- **Linear / Vercel / Raycast:** dense navigation, crisp borders, compact controls, calm technical hierarchy.
- **Claude desktop/web:** subdued cards, soft grid background, AI assistant product rhythm.
- **macOS utilities:** traffic-light motif, translucent/vibrancy panels, compact page headers.
- **GitBook / Nextra docs:** sticky docs header, left navigation, article body, right “On this page” TOC, markdown-first structure.
- **Developer SaaS landing pages:** dark hero, indigo CTA, controlled glow blobs, feature-card grid.

---

## 2. Typography

### Dashboard / login / main app

| Token | Value |
|---|---|
| Primary font | `Inter`, `-apple-system`, `BlinkMacSystemFont`, `SF Pro Text`, `SF Pro Display`, `system-ui`, `sans-serif` |
| Body rendering | antialiased, grayscale smoothing |
| Icon font | `Material Symbols Outlined` |
| Monospace | `JetBrains Mono`, `ui-monospace`, system monospace for inline command/code surfaces |

#### Main app type scale

| Use | Classes / value | Notes |
|---|---|---|
| Page title desktop | `text-2xl font-semibold tracking-tight` | Dashboard header titles |
| Page title mobile | `text-base font-semibold tracking-tight` | Dashboard header titles on small screens |
| Sidebar product name | `text-lg font-semibold tracking-tight` | Logo block |
| Sidebar nav label | `text-[13px] font-medium` | Compact navigation |
| Section eyebrow | `text-xs font-semibold uppercase tracking-wider` | Sidebar section labels |
| Button text | `text-xs` / `text-sm`, `font-semibold` | By button size |
| Card title | `font-semibold` | Usually `text-text-main` |
| Card subtitle | `text-sm text-text-muted` | Secondary explanatory copy |
| Input text | `text-[16px] sm:text-sm` | 16px on mobile prevents iOS zoom |
| Badge text | `text-[10px]` / `text-xs` / `text-sm`, `font-semibold` | By badge size |
| Toast text | `text-xs` | Compact notification system |

### Landing page

| Use | Classes / value |
|---|---|
| Hero heading | `text-5xl md:text-7xl font-black leading-[1.1] tracking-tight` |
| Hero accent span | `text-[#a5b4fc]` |
| Hero description | `text-lg md:text-xl text-gray-400 font-light` |
| Section heading | `text-3xl md:text-4xl font-bold` |
| Feature title | `text-lg font-bold` |
| Feature copy | `text-sm text-gray-400 leading-relaxed` |
| Nav links | `text-sm font-medium` |

### Docs site

| Use | CSS / classes |
|---|---|
| Body | `Inter`, `system-ui`, `-apple-system`, `sans-serif` |
| Markdown h1 | `2.5rem`, `font-weight: 800`, `line-height: 1.2`, color `#4648d4` |
| Markdown h2 | `2rem`, `font-weight: 700`, black, bottom border `#E5E7EB` |
| Markdown h3 | `1.5rem`, `font-weight: 600`, black |
| Markdown paragraph | `1.125rem`, `line-height: 1.75`, color `#6B7280` |
| Markdown list item | `1.125rem`, `line-height: 1.75`, color `#6B7280` |
| Inline code | monospace, `0.875em`, indigo text |

---

## 3. Color system

### 3.1 Dashboard brand palette

The main app defines its palette in CSS variables and Tailwind theme aliases.

| Token | Light value | Dark value | Usage |
|---|---:|---:|---|
| `brand-50` | `#eef2ff` | `#eef2ff` | pale indigo tint |
| `brand-100` | `#e1e0ff` | `#e1e0ff` | pale indigo tint |
| `brand-200` | `#c0c1ff` | `#c0c1ff` | soft indigo tint |
| `brand-300` | `#a5b4fc` | `#a5b4fc` | dark-mode brand text |
| `brand-400` | `#818cf8` | `#818cf8` | hover/accent |
| `brand-500` | `#4648d4` | `#818cf8` | primary brand |
| `brand-600` | `#3f42c6` | `#a5b4fc` | primary hover |
| `brand-700` | `#2f2ebe` | `#c0c1ff` | logo gradient end |
| `brand-800` | `#1e1b8f` | `#1e1b8f` | deep brand |
| `brand-900` | `#07006c` | `#07006c` | deepest brand |
| `primary` | `brand-500` | `brand-400` | legacy alias |
| `primary-hover` | `brand-600` | `brand-300` | hover alias |

### 3.2 Dashboard semantic surfaces

| Token | Light | Dark | Usage |
|---|---:|---:|---|
| `bg` | `#f8f9ff` | `#020617` | app background |
| `bg-alt` | `#eff4ff` | `#0f172a` | hero gradient / sections |
| `surface` | `#ffffff` | `#111827` | cards, modals, header surfaces |
| `surface-2` | `#eff4ff` | `#1e293b` | secondary controls, hover bg |
| `surface-3` | `#e5eeff` | `#273449` | disabled controls, toggle off |
| `sidebar` | `rgba(248,249,255,.82)` | `rgba(15,23,42,.82)` | sidebar base |
| `border` | `#c7cfe3` | `#263348` | standard borders |
| `border-subtle` | `#dce4f4` | `#1e293b` | card/sidebar subtle borders |
| `text-main` | `#0b1c30` | `#eaf1ff` | primary text |
| `text-muted` | `#565e74` | `#a8b3c7` | secondary text |
| `text-subtle` | `#767586` | `#7d8aa3` | tertiary text |

### 3.3 Status colors

| Token | Light | Dark | Usage |
|---|---:|---:|---|
| `danger` | `#ba1a1a` | `#f87171` | destructive states |
| `success` | `#059669` | `#34d399` | success states |
| `warning` | `#d97706` | `#fbbf24` | warnings |
| `info` | `#0058be` | `#38bdf8` | information |

Toast and badge variants use Tailwind color families: green, red, amber/yellow, blue, plus brand.

### 3.4 Landing palette

| Token | Value | Usage |
|---|---:|---|
| Landing background | `#020617` | fixed nav, dark page base |
| Landing panel | `#0f172a` / `rgba(15,23,42,.72)` | feature cards, secondary buttons |
| Landing border | `rgba(148,163,184,.18)` | nav/card borders |
| Landing primary | `#818cf8` | CTA, hero accent, live badge |
| Landing primary hover | `#a5b4fc` | CTA hover |
| Landing CTA text | `#ffffff` | text on indigo buttons |
| Landing text | `#eaf1ff` | primary dark-page text |
| Landing muted text | `#a8b3c7` | nav/body muted copy |
| Landing glow | `rgba(129,140,248,.18-.28)` | controlled CTA/hero glow |
| Hero blob | `#818cf8 / 18%` | blurred radial glow |

Feature cards add category colors: indigo, sky, emerald, amber, violet, blue, slate, fuchsia.

### 3.5 Docs palette

| Token | Value | Usage |
|---|---:|---|
| Docs app bg | `#f8f9ff` | page background |
| Docs header/sidebar bg | `#ffffff` / `white/80` | docs chrome |
| Docs accent | `#4648d4` | logo accent, links, active nav, h1 |
| Docs accent hover | `#3f42c6` | CTA hover |
| Docs text | `#000000` | h2/h3/strong/logo text |
| Docs muted | `#6B7280` | paragraphs, list items |
| Docs subtle | Tailwind gray-500/600/700 | nav/modal labels |
| Docs border | `#E5E7EB`, `gray-200` | dividers |
| Docs code bg | `#F1F5F9` | pre and inline code |
| Docs scrollbar thumb | `#CBD5E1` | docs scrollbar |

---

## 4. Radius, shadows, elevation

### Radius tokens

| Token | Value | Usage |
|---|---:|---|
| `radius-brand` | `8px` | buttons, inputs, icon containers, modal close buttons |
| `radius-brand-lg` | `14px` | cards, modals |
| Button small | `6px` | `Button size="sm"` |
| Button md/lg | `8px` | `Button size="md|lg"` |
| Card / modal | `14px` | main app card shell |
| Badge / chip | `4px`; optional `9999px` for live/status pills | technical labels and optional status badges |
| Landing card | `12px` / `rounded-xl` | feature cards |
| Landing buttons | `8px` / `rounded-lg` | CTA and secondary buttons |
| Docs controls | `8px` / `rounded-lg` | nav items, buttons |
| Docs language modal | `12px` / `rounded-xl` | language selector dialog |

### Shadows

| Token | Value / class | Usage |
|---|---|---|
| `shadow-soft` | `0 1px 2px 0 rgba(15,23,42,.05)` light; stronger black in dark | default cards |
| `shadow-card-hover` | `0 1px 2px rgba(15,23,42,.06)` | precision hover shadow |
| `shadow-elevated` | `0 4px 14px rgba(15,23,42,.08)` | elevated panels |
| `shadow-elev` | low blur precision shadow; stronger black in dark | modals/elevated cards |
| `shadow-focus` | `0 0 0 3px rgba(70,72,212,.14)` light; `0 0 0 3px rgba(129,140,248,.22)` dark | focus treatment |
| Landing CTA | controlled indigo glow `rgba(129,140,248,.18-.28)` | dark CTA |
| Docs modal | Tailwind `shadow-2xl` | language switcher |

---

## 5. Spacing system

The UI primarily uses Tailwind spacing. Keep values exact when recreating components.

| Token | Tailwind | px | Usage |
|---|---:|---:|---|
| `xs` | `1` | 4 | tight nav gaps, small controls |
| `sm` | `2` | 8 | icon gaps, compact padding |
| `md` | `3` | 12 | nav item x padding, card rows |
| `lg` | `4` | 16 | header padding, sidebar nav padding |
| `xl` | `6` | 24 | modal/card body, landing x padding |
| `2xl` | `8` | 32 | login header gap, large card padding |
| Dashboard page mobile | `p-6` | 24 | main content container |
| Dashboard page desktop | `lg:p-10` | 40 | main content container |
| Dashboard max width | `max-w-7xl` | 80rem | main page content |
| Sidebar width | `w-72` | 288 | dashboard sidebar |
| Docs sidebar width | `w-64` | 256 | docs left/right chrome |
| Docs article padding | `px-4 sm:px-6 py-8` | 16/24 x, 32 y | markdown article |
| Docs article width | `max-w-4xl` | 56rem | docs body |
| Landing section y | `py-24` | 96 | standard landing sections |
| Landing hero top/bottom | `pt-32 pb-20` | 128/80 | hero |

---

## 6. Icon systems

### Dashboard and landing

- Uses **Material Symbols Outlined** via text ligatures.
- Default icon size in buttons: `text-[18px]`.
- Dashboard page header icons: `text-xl lg:text-2xl`, color `text-primary`.
- Sidebar icons: `text-[18px]`, active state adds `fill-1`.
- Logo icon: `hub` inside a `size-9` or `size-8` rounded gradient square.
- Loading icon: `progress_activity` with `animate-spin`.

Important Material Symbols used:

`hub`, `api`, `dns`, `layers`, `bar_chart`, `data_usage`, `security`, `terminal`, `perm_media`, `lan`, `extension`, `translate`, `settings`, `power_settings_new`, `close`, `menu`, `search`, `expand_more`, `chevron_right`, `person`, `rocket_launch`, `code`, `open_in_new`, `link`, `bolt`, `shield_with_heart`, `monitoring`, `key`, `cloud_sync`, `dashboard`.

### Docs site

- Uses **lucide-react** icons.
- Standard nav icon size: `w-4 h-4`.
- Header mobile menu icon: `w-6 h-6`.
- Modal close icon: `w-5 h-5`.
- Markdown headings map known page titles and leading emoji to lucide icons.

Important lucide icons:

`ExternalLink`, `Menu`, `X`, `Globe`, `List`, `BookOpen`, `Rocket`, `Terminal`, `Monitor`, `HelpCircle`, `MessageCircle`, `Layers`, `Plug`, `Cloud`, `Zap`, `Wallet`, `Gift`, `GitBranch`, `BarChart3`, `Code2`, `Sparkles`, `Server`, `CheckCircle`, `AlertTriangle`, `Lightbulb`, `Package`, `Link2`, `Target`, `Heart`, `Home`, `Wrench`, `Search`, `Container`.

### Traffic-light motif

Used in dashboard sidebar and modal headers:

| Dot | Value |
|---|---:|
| Red | `#FF5F56` |
| Yellow | `#FFBD2E` |
| Green | `#27C93F` |
| Size | `12px` (`w-3 h-3`) |
| Gap | `8px` (`gap-2`) |

---

## 7. Layout systems

### 7.1 Dashboard app shell

- Root: `flex h-screen w-full overflow-hidden bg-bg`.
- Sidebar desktop: visible from `lg`, `w-72`, full height, fixed left column.
- Sidebar mobile: fixed drawer `inset-y-0 left-0 z-50`, slides with `translate-x-0` / `-translate-x-full`, duration `300ms`.
- Mobile overlay: fixed `inset-0 z-40 bg-black/20`.
- Main: `flex flex-col flex-1 h-full min-w-0 relative isolate`.
- Background: absolute `landing-grid` overlay behind content.
- Header: shrink fixed-height top band with translucent surface on mobile; transparent on desktop.
- Content: `flex-1 overflow-y-auto custom-scrollbar`, default `p-6 lg:p-10`.
- Default content wrapper: `max-w-7xl mx-auto`.
- Special chat route removes padding and becomes full-height flex.

### 7.2 Dashboard sidebar

- Width: `288px`.
- Surface: `bg-vibrancy backdrop-blur-xl`, border right `border-border-subtle`.
- Top traffic lights: `px-6 pt-5 pb-2`.
- Logo block: `px-6 py-4`, `gap-2`.
- Logo icon: `size-9 rounded-[8px] bg-gradient-to-br from-brand-500 to-brand-700 shadow-card-hover`.
- Nav container: `px-4 py-2 space-y-0.5 overflow-y-auto custom-scrollbar`.
- Main nav item: `flex items-center gap-3 px-3 py-1 rounded-lg`.
- Active nav: `bg-primary/10 text-primary`.
- Inactive nav: `text-text-muted hover:bg-surface-2 hover:text-text-main`.
- Footer: `p-3 border-t border-border-subtle` with full-width shutdown button.

### 7.3 Dashboard header

- Container: `px-4 lg:px-8 pt-3 pb-2 border-b border-border-subtle`.
- Mobile background: `bg-surface/60 backdrop-blur-xl`.
- Desktop background: `lg:bg-transparent lg:backdrop-blur-none`.
- Left: mobile menu button and page title/breadcrumbs.
- Right actions: search, theme toggle, header menu, optional OIDC identity pill.
- Breadcrumb separator: Material `chevron_right`, muted.
- OIDC pill: `rounded-full border border-border bg-surface/70 px-3 py-1.5 text-xs`.

### 7.4 Login page

- Root: `min-h-screen flex items-center justify-center bg-bg p-4 relative overflow-hidden`.
- Background: `landing-grid absolute inset-0`.
- Form shell: `relative z-10 w-full max-w-md`.
- Brand heading: `text-3xl font-bold text-primary mb-2`.
- Login card: standard `Card`.
- Form stack: `flex flex-col gap-4`.

### 7.5 Landing page

- Fixed nav: `fixed top-0 z-50 w-full bg-[#020617]/80 backdrop-blur-md border-b border-slate-400/20`.
- Nav inner: `max-w-7xl mx-auto px-6 h-16 flex items-center justify-between`.
- Hero: `relative pt-32 pb-20 px-6 min-h-[90vh] flex flex-col items-center justify-center overflow-hidden`.
- Hero glow: absolute `1000px × 500px`, `#818cf8/18%`, `rounded-full`, `blur-[120px]`.
- Hero content: `max-w-4xl`, centered, `gap-8`.
- Feature section: `py-24 px-6`, inner `max-w-7xl mx-auto`.
- Feature grid: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4`.

### 7.6 Docs site

- Root docs layout: `min-h-screen flex flex-col bg-[#f8f9ff]`.
- Header: sticky `top-0 z-50 h-16 border-b bg-white/80 backdrop-blur-sm`.
- Left docs sidebar: visible `lg`, `w-64`, sticky `top-16`, height `calc(100vh - 4rem)`.
- Main content: flex-1, `min-w-0`, article `max-w-4xl mx-auto px-4 sm:px-6 py-8`.
- Right TOC: visible `xl`, `w-64`, sticky `top-16`, border-left.
- Mobile docs menu: overlay black `rgba(0,0,0,.5)`, drawer `280px`, white, slide-in-left `0.3s`.

---

## 8. Component specifications

### Button — dashboard

Base:

- `inline-flex items-center justify-center gap-2`
- `font-semibold`
- `transition-all duration-150 ease-out`
- `cursor-pointer`
- Active press: subtle color/brightness shift only; avoid scale-down for the cooler technical feel
- Disabled: `opacity-50`, `cursor-not-allowed`, no active scale

Sizes:

| Size | Height | Padding | Text | Radius |
|---|---:|---:|---:|---:|
| `sm` | `h-7` | `px-3` | `text-xs` | `6px` |
| `md` | `h-9` | `px-4` | `text-sm` | `8px` |
| `lg` | `h-11` | `px-6` | `text-sm` | `8px` |

Variants:

| Variant | Classes |
|---|---|
| `primary` | `bg-brand-500 hover:bg-brand-600 text-white shadow-sm` |
| `secondary` | `bg-surface hover:bg-surface-2 text-text-main border border-border` |
| `outline` | `border border-border text-text-main hover:bg-surface-2 hover:border-brand-500/40` |
| `ghost` | `text-text-muted hover:bg-surface-2 hover:text-text-main` |
| `danger` | `bg-red-700 hover:bg-red-800 text-white shadow-sm` |
| `success` | `bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm` |

### Button — landing

Primary CTA:

- Height `48px` (`h-12`)
- Padding `px-8`
- Radius `rounded-lg`
- Background `#818cf8`, hover `#a5b4fc`
- Text white, `text-base font-bold`
- Shadow controlled indigo glow `0 0 18px rgba(129,140,248,.24)`, hover slightly stronger
- Icon gap `gap-2`

Secondary dark button:

- Height `48px`, `px-8`, `rounded-lg`
- Border `rgba(148,163,184,.28)`
- Background `#0f172a`, hover `#1e293b`
- Text white, `font-bold`

### Card

Base card:

- `bg-surface border border-border-subtle rounded-[14px]`
- Default shadow: `shadow-[var(--shadow-soft)]`
- Elevated: `shadow-[var(--shadow-elev)]`
- Hover: `hover:shadow-[var(--shadow-card-hover)] hover:border-brand-500/30 transition-all cursor-pointer`

Padding variants:

| Variant | Class |
|---|---|
| `none` | none |
| `xs` | `p-3` |
| `sm` | `p-4` |
| `md` | `p-6` |
| `lg` | `p-8` |

Card header:

- `flex items-center justify-between mb-4`
- Icon container: `p-2 rounded-[8px] bg-bg text-text-muted`
- Icon size: `text-[20px]`

Subcomponents:

- `Card.Section`: `p-4 rounded-[8px] bg-bg border border-border-subtle`
- `Card.Row`: `p-3 -mx-3 border-b border-border-subtle hover:bg-surface-2/50`
- `Card.ListItem`: grouped row with actions hidden until hover.

### Input

- Wrapper: `flex flex-col gap-1.5`
- Label: `text-sm font-medium text-text-main`
- Required star: `text-red-500 ml-1`
- Input: `w-full py-2.5 px-3 text-[16px] sm:text-sm`
- Surface: `bg-surface rounded-[8px] border border-border`
- Placeholder: `placeholder-text-muted/70`
- Focus: no outline, `focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500/40`
- Icon left: absolute left, `pl-3`, icon `text-[20px]`, input `pl-10`
- Error: `ring-1 ring-red-500`, `border-red-500/40`, error copy `text-xs text-red-500`
- Hint: `text-xs text-text-muted`

### Select

Matches `Input` styling:

- `py-2.5 px-3 pr-10`
- `appearance-none`
- Right icon: Material `expand_more`, `text-[20px]`, `pr-3`
- Native option colors are explicitly fixed for dark mode using `color-scheme: dark` and dark surface/text values.

### Toggle

Base:

- Wrapper: `flex items-center gap-3`
- Track: `rounded-full transition-colors duration-200 ease-in-out`
- Focus: `focus:ring-2 focus:ring-brand-500/30`
- On: `bg-brand-500`
- Off: `bg-surface-3`
- Thumb: white, rounded-full, `shadow-sm`, transition transform.

Sizes:

| Size | Track | Thumb | On translate |
|---|---|---|---|
| `sm` | `w-8 h-4` | `size-3` | `translate-x-4` |
| `md` | `w-11 h-6` | `size-5` | `translate-x-5` |
| `lg` | `w-14 h-7` | `size-6` | `translate-x-7` |

### Badge

Base:

- `inline-flex items-center gap-1.5 rounded-[4px] font-semibold`
- Use rectangular chips by default for technical labels; reserve `rounded-full` for live/status pills where the softer status language is useful.

Variants:

| Variant | Classes |
|---|---|
| `default` | `bg-surface-2 text-text-muted` |
| `primary` | `bg-brand-500/10 text-brand-600 dark:text-brand-300 border border-brand-500/20` |
| `success` | `bg-green-500/10 text-green-600 dark:text-green-400` |
| `warning` | `bg-yellow-500/10 text-yellow-600 dark:text-yellow-400` |
| `error` | `bg-red-500/10 text-red-600 dark:text-red-400` |
| `info` | `bg-blue-500/10 text-blue-600 dark:text-blue-400` |

Sizes:

| Size | Classes |
|---|---|
| `sm` | `px-2 py-0.5 text-[10px]` |
| `md` | `px-2.5 py-1 text-xs` |
| `lg` | `px-3 py-1.5 text-sm` |

Optional dot: `size-1.5 rounded-full`, color follows variant.

### Modal

- Root: fixed full viewport, `z-50`, centered, `p-4`.
- Overlay: `absolute inset-0 bg-black/50 backdrop-blur-[2px] fade-in`.
- Panel: `relative w-full bg-surface border border-border-subtle rounded-[14px] shadow-[var(--shadow-elev)] fade-in`.
- Sizes: `sm max-w-sm`, `md max-w-md`, `lg max-w-lg`, `xl max-w-xl`, `full max-w-4xl`.
- Header: `p-2 border-b border-border-subtle`, optional traffic lights.
- Body: `p-6 max-h-[calc(85vh-100px)] overflow-y-auto custom-scrollbar`.
- Footer: `p-6 border-t border-border-subtle`, actions right-aligned with `gap-3`.
- Close button: `p-1.5 rounded-[8px] text-text-muted hover:bg-surface-2 hover:text-text-main`.

### Toast notification

- Container: fixed `top-4 right-4 z-[80]`, width `min(92vw, 380px)`, column `gap-2`.
- Toast shell: `rounded-lg border px-3 py-2 shadow-lg backdrop-blur-sm`.
- Layout: `flex items-start gap-2`.
- Icon: `text-[18px] leading-5`.
- Title: `text-xs font-semibold mb-0.5`.
- Message: `text-xs whitespace-pre-wrap break-words`.

Variant styles:

| Type | Wrapper | Icon |
|---|---|---|
| success | `border-green-500/30 bg-green-500/10 text-green-600 dark:text-green-400` | `check_circle` |
| error | `border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400` | `error` |
| warning | `border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400` | `warning` |
| info | `border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400` | `info` |

### Docs markdown content

- `h1`: indigo, large, icon-capable, flex aligned center.
- `h2`: black with bottom border and padding-bottom.
- `h3`: black, medium heading.
- `p`, `li`: large readable text, muted gray, `line-height: 1.75`.
- Links: indigo, underlined, hover opacity `0.8`.
- Blockquote: left border `4px solid #4648d4`, italic muted text.
- `pre`: `#F1F5F9`, `border-radius: 8px`, `padding: 1rem`, horizontal scroll.
- Inline code: `#F1F5F9` background, indigo text, `4px` radius.
- Heading anchors offset for sticky header: `scroll-margin-top: 5rem`.

### Docs navigation items

- Sidebar section button: `text-sm font-semibold text-gray-900`, hover indigo.
- Section icon: lucide `w-4 h-4`.
- Item link: `flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors`.
- Active item: `bg-[#4648d4]/10 text-[#4648d4] font-medium`.
- Inactive item: `text-gray-600 hover:bg-gray-100 hover:text-gray-900`.
- TOC active item: indigo + `font-medium`; nested h3 adds `pl-4`.

### Language switcher — docs

Trigger:

- `flex items-center gap-1.5 px-2.5 py-1.5 text-sm`
- `text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200`

Modal:

- Overlay: `fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 p-4`.
- Panel: `bg-white rounded-xl shadow-2xl max-w-md w-full max-h-[80vh] overflow-hidden`.
- Header: `p-4 border-b border-gray-200`.
- Language row: `w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left`.
- Active row: `bg-[#4648d4]/10 text-[#4648d4] font-medium`.

---

## 9. Backgrounds, animations, and effects

### Dashboard backgrounds

- Base body: `background-color: var(--color-bg)`.
- Main background overlay: `.landing-grid`, 40px grid using brand accent at low opacity.
- Dot grid page background: radial brand glows at 15%/20% and 85%/80%.
- Dark mode increases radial glow opacity slightly.

### Vibrancy

`.bg-vibrancy`:

- `backdrop-filter: blur(20px)`.
- Light: `rgba(248,249,255,.82)`.
- Dark: `rgba(15,23,42,.82)`.

### Animations

| Name | Duration | Usage |
|---|---:|---|
| `spin` | `1s linear infinite` | loading icon |
| `pulse` | `2s cubic-bezier(.4,0,.6,1) infinite` | live dots |
| `border-glow` | `2s ease-in-out infinite` | glowing borders |
| `fade-in` | `0.2s ease-out` | overlays/modals |
| `slide-in-right` | `0.25s cubic-bezier(.22,1,.36,1)` | entering panels |
| `slide-in-top` | `0.18s cubic-bezier(.22,1,.36,1)` | dropdowns |
| `pulseGlow` | `3s ease-in-out infinite` | soft glow elements |
| `ctaShimmer` | `2.8s ease-in-out infinite` | CTA shimmer pseudo-element |
| `ctaGlowPulse` | `2.4s ease-in-out infinite` | CTA glow pulse |
| Docs `fadeIn` | `0.2s ease-out` | mobile overlay |
| Docs `slideInLeft` | `0.3s ease-out` | mobile docs drawer |

### Scrollbars

Dashboard `.custom-scrollbar`:

- Width `6px`.
- Thumb `rgba(156,163,175,.3)`, radius `20px`.
- Hover thumb `var(--color-primary)`.

Dashboard `.scroll-thin-x`:

- Height `3px`.
- Thumb `rgba(70,72,212,.55)`.

Docs scrollbar:

- Width/height `8px`.
- Thumb `#CBD5E1`, radius `4px`.
- Hover thumb `#4648d4`.

---

## 10. Design rules for future UI

1. **Dashboard UI must use CSS theme tokens**, not hardcoded brand colors, unless matching an existing special case.
2. **Primary dashboard action color is `brand-500` / `primary` (`#4648d4`)**; hover is `brand-600`.
3. **Use `14px` cards/modals, `8px` controls, and `4px` technical chips** to preserve structure while making the UI sharper.
4. **Keep dashboard controls compact**: sidebar nav uses `py-1`, header actions are small, card density is moderate.
5. **Use Material Symbols in the app and landing; use lucide-react only in docs.** Do not mix icon systems within a single surface.
6. **Use translucent/vibrancy panels for shell chrome**: sidebar and mobile header should feel glassy, not flat.
7. **Landing page may hardcode its darker midnight palette** because it intentionally differs from the dashboard theme.
8. **Docs site uses the same indigo accent family as the dashboard** to keep the cool technical brand consistent.
9. **Mobile input font size must stay at 16px** before `sm` to avoid iOS zoom.
10. **Preserve active-state language**: active nav items are brand-tinted backgrounds with brand text, not filled brand buttons.
11. **Use grid/glow backgrounds subtly**. The grid opacity must remain low and decorative.
12. **Avoid heavy shadows**. Prefer crisp borders, `border-subtle`, low-alpha brand borders, and precision elevation.

---

## 11. Implementation checklist for reuse

Use this checklist when recreating the same UI style in another application:

- Load Inter as the primary font and Material Symbols Outlined for dashboard/landing icons.
- Define the dashboard color variables from sections 3.1–3.3 before building components.
- Configure Tailwind or equivalent utility tokens for brand colors, semantic surfaces, radii, and shadows.
- Build the app shell first: full-height layout, 288px translucent sidebar, mobile drawer, sticky/top header, and low-opacity grid background.
- Recreate core primitives before page-specific UI: Button, Card, Input, Select, Toggle, Badge, Modal, Toast.
- Keep dashboard UI token-driven; avoid hardcoded colors except traffic-light dots and documented special cases.
- Treat landing pages as a separate dark theme using section 3.4 values and explicit indigo CTA styling.
- Treat docs pages as a separate light documentation theme using section 3.5 values, sticky sidebars, right TOC, and markdown styles.
- Preserve component density: compact nav rows, small header actions, 14px card radius, 8px control radius, 4px technical chips, and subtle borders.
- Validate both light and dark dashboard modes, mobile sidebar behavior, docs mobile drawer behavior, focus rings, hover states, and scrollbar styling.

## 12. Page templates

Use these templates to compose new screens while preserving the same visual rhythm.

### 12.1 Dashboard overview page

Structure:

1. Page header from the shared dashboard shell.
2. Optional intro row: title, short muted description, primary action on the right.
3. KPI grid: `grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4`.
4. Main content: `grid grid-cols-1 xl:grid-cols-[2fr_1fr] gap-6` when a secondary panel is needed.
5. Primary card: table, chart, activity feed, or list.
6. Secondary card: health/status summary, quick actions, or compact metadata.

Recommended card anatomy:

- Header: icon container + title/subtitle on the left, action button or badge on the right.
- Body rows: `Card.Row` density, subtle dividers, muted secondary text.
- Empty state: centered icon, concise title, muted description, optional primary CTA.

### 12.2 Dashboard settings/form page

Structure:

1. `max-w-4xl` content column inside the default dashboard content wrapper.
2. Stacked cards with `space-y-6`.
3. Each card owns one settings group.
4. Form fields use `grid grid-cols-1 md:grid-cols-2 gap-4` when fields are short; use one column for long text or complex controls.
5. Footer actions are right-aligned with `gap-3`; destructive actions stay visually separated or use `danger` variant.

Recommended pattern:

- Card title + subtitle explain the setting group.
- Inputs use labels, hints, and explicit error text.
- Toggles align label/copy on the left and switch on the right.
- Save buttons use `primary`; cancel/reset uses `ghost` or `outline`.

### 12.3 Dashboard table/list page

Structure:

1. Header row with search/filter controls and primary action.
2. Optional filter chips using `Badge` variants.
3. Card containing a responsive table or row list.
4. Row hover uses `hover:bg-surface-2/50`, not strong filled backgrounds.
5. Row actions appear on hover when possible to reduce visual noise.

Table/list style:

- Header labels: `text-xs font-semibold uppercase tracking-wider text-text-muted`.
- Primary row text: `text-sm font-medium text-text-main`.
- Secondary row text: `text-xs text-text-muted`.
- Status values use badges with optional dots.
- Empty rows never leave a blank card; show an empty state.

### 12.4 Login/auth page

Structure:

1. Full viewport centered root: `min-h-screen flex items-center justify-center bg-bg p-4 relative overflow-hidden`.
2. Low-opacity `landing-grid` background layer.
3. Form shell: `relative z-10 w-full max-w-md`.
4. Brand heading: large, centered, brand-colored.
5. Standard card containing form stack.

Auth pages should feel quieter than dashboard pages: fewer actions, one primary path, precision card elevation, and no dense navigation.

### 12.5 Landing page

Recommended section order:

1. Fixed translucent dark nav.
2. Hero with large bold heading, indigo accent span, muted description, version/live badge, primary CTA, secondary CTA.
3. Feature grid with 4-column desktop layout.
4. How-it-works or architecture section using dark cards and subtle borders.
5. Integration/tooling section if relevant.
6. Final CTA band with indigo button and controlled glow treatment.
7. Footer with muted links.

Landing pages may use stronger contrast, glow, and hardcoded dark palette values than dashboard pages.

### 12.6 Docs article page

Structure:

1. Sticky docs header.
2. Left sidebar navigation on desktop.
3. Center article column `max-w-4xl`.
4. Right TOC on wide screens.
5. Mobile drawer for navigation.

Article rhythm:

- One `h1` at the top with optional icon.
- `h2` sections separated by top margin and bottom border.
- Paragraph/list text stays larger and more readable than dashboard copy.
- Code blocks use light slate backgrounds and horizontal scroll.

---

## 13. State examples

### 13.1 Loading states

- Buttons replace the left icon with Material `progress_activity` and `animate-spin`.
- Cards may show skeleton rows using `bg-surface-2`, rounded blocks, and subtle pulse.
- Full-page loading should stay centered inside the content region, not the entire browser viewport if the dashboard shell is visible.
- Keep loading copy short: `Loading...`, `Syncing...`, `Checking status...`.

### 13.2 Empty states

Use this pattern inside cards or full page content:

- Icon: Material symbol, `text-3xl` or `text-4xl`, `text-text-muted`.
- Title: `text-sm font-semibold text-text-main`.
- Description: `text-sm text-text-muted max-w-sm`.
- Optional CTA: small or medium `Button`, usually `primary` if it creates the first item.
- Container: `flex flex-col items-center justify-center text-center py-10 px-6`.
- Keep icon treatment muted and geometric; avoid decorative illustration unless the page is explicitly marketing-oriented.

### 13.3 Error states

- Inline field errors use red ring/border and `text-xs text-red-500` copy.
- Card-level errors use a soft red tinted surface: `bg-red-500/10 border-red-500/30 text-red-600 dark:text-red-400`.
- Toast errors use the documented toast variant with Material `error`.
- Error copy should explain what failed and offer one next action when possible.

### 13.4 Disabled states

- Disabled buttons: `opacity-50 cursor-not-allowed`, no active scale.
- Disabled inputs: `opacity-50 cursor-not-allowed`.
- Disabled cards/actions should avoid hover shadows and hover color changes.
- Use disabled states only when the action is temporarily unavailable; use hidden actions when the user should not see the option.

### 13.5 Hover and active states

- Dashboard hover surfaces use `surface-2` or low-alpha brand borders.
- Active navigation uses brand-tinted background + brand text: `bg-primary/10 text-primary`.
- Primary buttons darken on hover; do not add large gradients.
- Card hover may add precision shadow and low-alpha brand border.
- Press feedback is subtle scale only on clickable controls: `active:scale-[0.97]`.

### 13.6 Selected/current states

- Selected rows or nav items should use tinted backgrounds, not solid brand fills.
- Selected badges use `primary` badge treatment.
- Current docs TOC item uses indigo text and medium weight.
- Current sidebar section can combine active text color with filled Material icon variation.

### 13.7 Focus states

- Keyboard focus uses brand-tinted ring: `focus:ring-2 focus:ring-brand-500/30`.
- Inputs may also change border to `border-brand-500/40`.
- Focus states must remain visible in both light and dark mode.
- Avoid browser-default blue outlines unless they are intentionally restyled.

---

## 14. Asset and setup requirements

### 14.1 Fonts

Load Inter as the primary UI font with weights 300–900. Load JetBrains Mono for code snippets, technical readouts, and AI thinking states. Use these fallbacks:

```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'SF Pro Display', system-ui, sans-serif;
```

Dashboard and landing icons require Material Symbols Outlined:

```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" />
```

Docs icons use lucide-style outline icons. Keep them visually consistent at `w-4 h-4` for navigation and `w-5 h-5` to `w-6 h-6` for controls.

### 14.2 Minimum CSS variable skeleton

```css
:root {
  --color-brand-50: #eef2ff;
  --color-brand-100: #e1e0ff;
  --color-brand-200: #c0c1ff;
  --color-brand-300: #a5b4fc;
  --color-brand-400: #818cf8;
  --color-brand-500: #4648d4;
  --color-brand-600: #3f42c6;
  --color-brand-700: #2f2ebe;
  --color-brand-800: #1e1b8f;
  --color-brand-900: #07006c;
  --color-primary: var(--color-brand-500);
  --color-primary-hover: var(--color-brand-600);
  --color-bg: #f8f9ff;
  --color-bg-alt: #eff4ff;
  --color-surface: #ffffff;
  --color-surface-2: #eff4ff;
  --color-surface-3: #e5eeff;
  --color-border: #c7cfe3;
  --color-border-subtle: #dce4f4;
  --color-text-main: #0b1c30;
  --color-text-muted: #565e74;
  --color-text-subtle: #767586;
  --radius-brand: 8px;
  --radius-brand-lg: 14px;
  --radius-chip: 4px;
  --shadow-soft: 0 1px 2px 0 rgba(15,23,42,0.05);
  --shadow-card-hover: 0 1px 2px rgba(15,23,42,0.06);
  --shadow-elev: 0 4px 14px rgba(15,23,42,0.08);
  --color-sidebar: rgba(248, 249, 255, 0.82);
}

.dark {
  --color-bg: #020617;
  --color-bg-alt: #0f172a;
  --color-surface: #111827;
  --color-surface-2: #1e293b;
  --color-surface-3: #273449;
  --color-border: #263348;
  --color-border-subtle: #1e293b;
  --color-text-main: #eaf1ff;
  --color-text-muted: #a8b3c7;
  --color-text-subtle: #7d8aa3;
  --color-primary: #818cf8;
  --color-primary-hover: #a5b4fc;
  --shadow-soft: 0 1px 2px 0 rgba(0,0,0,0.28);
  --shadow-card-hover: 0 1px 2px rgba(0,0,0,0.32);
  --shadow-elev: 0 14px 40px rgba(0,0,0,0.38);
  --shadow-focus: 0 0 0 3px rgba(129, 140, 248, 0.22);
  --color-sidebar: rgba(15, 23, 42, 0.82);
}
```

### 14.3 Required utility CSS

```css
body {
  background-color: var(--color-bg);
  color: var(--color-text-main);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'SF Pro Display', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.bg-vibrancy {
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  background: var(--color-sidebar);
}

.landing-grid {
  background-image:
    linear-gradient(to right, var(--color-brand-500) 1px, transparent 1px),
    linear-gradient(to bottom, var(--color-brand-500) 1px, transparent 1px);
  background-size: 40px 40px;
  opacity: 0.08;
}

.dark .landing-grid {
  opacity: 0.04;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgba(156,163,175,0.3);
  border-radius: 20px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: var(--color-primary);
}
```

### 14.4 Minimal Tailwind token mapping

Map these names before implementing components:

| Utility token | CSS variable |
|---|---|
| `brand-50` … `brand-900` | brand scale variables |
| `primary` | `--color-primary` |
| `primary-hover` | `--color-primary-hover` |
| `bg` | `--color-bg` |
| `bg-alt` | `--color-bg-alt` |
| `surface` | `--color-surface` |
| `surface-2` | `--color-surface-2` |
| `surface-3` | `--color-surface-3` |
| `border` | `--color-border` |
| `border-subtle` | `--color-border-subtle` |
| `text-main` | `--color-text-main` |
| `text-muted` | `--color-text-muted` |
| `text-subtle` | `--color-text-subtle` |
| `sidebar` | `--color-sidebar` |

### 14.5 Quality bar before calling the style complete

- Dashboard light and dark mode both match the token values.
- Sidebar width, density, and active states match sections 7.1–7.3.
- Buttons, inputs, cards, badges, modals, and toasts match section 8.
- Landing page uses the separate midnight palette and controlled indigo CTA glow.
- Docs page uses the separate indigo accent and markdown typography.
- Mobile layouts include sidebar/drawer behavior and keep inputs at 16px before `sm`.
- Keyboard focus rings are visible and brand-tinted.
- No internal repository file paths are required to understand or apply the design system.

---

### 14.6 Opacity-variant CSS equivalents

Component specs use Tailwind opacity modifier syntax (e.g. `bg-primary/10`).
In vanilla CSS or non-Tailwind environments, use `color-mix()`:

| Tailwind token       | CSS equivalent                                          |
|----------------------|----------------------------------------------------------|
| bg-primary/10        | color-mix(in srgb, var(--color-primary) 10%, transparent) |
| bg-primary/12        | color-mix(in srgb, var(--color-primary) 12%, transparent) |
| border-primary/20    | color-mix(in srgb, var(--color-primary) 20%, transparent) |
| border-primary/30    | color-mix(in srgb, var(--color-primary) 30%, transparent) |
| border-primary/40    | color-mix(in srgb, var(--color-primary) 40%, transparent) |
| ring-primary/30      | same as border-primary/30 for box-shadow usage           |
| bg-black/50          | rgba(0, 0, 0, 0.5)                                      |
| bg-surface-2/50      | color-mix(in srgb, var(--color-surface-2) 50%, transparent) |

For IE/older browser fallback, pre-compute static rgba values using the
resolved hex of the token at the time of build.

## 15. Verification notes

The current document preserves the existing dashboard shell, sidebar, core dashboard primitives, landing navigation/hero, and docs layout/markdown structure while shifting the visual language from friendly warm utility UI to cool technical AI/developer-tool UI. It is detailed enough to use as a cross-app implementation blueprint because it specifies visual tokens, layout rules, component states, responsive behavior, icon systems, effects, page templates, setup requirements, and a reuse checklist without requiring internal source-file references. Opacity-modifier notation (/10, /30) throughout this document assumes a Tailwind-compatible build. See Section 14.6 for vanilla CSS equivalents.
