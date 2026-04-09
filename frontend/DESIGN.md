# Design System (DATON ESG)

## 1. Visual Theme & Atmosphere

The Daton ESG frontend follows an Apple-inspired interface direction:
reductive, product-led, and visually controlled. The UI must stay quiet so the
message, product value, and key actions remain central. Every visual decision
should support clarity and perceived precision.

The design system is implemented through Tailwind theme tokens and reinforced
in component composition.

### Core principles

- Minimalism in service of clarity, not decoration
- Large, compressed headlines with quiet supporting copy
- Broad black or soft-light fields with a single blue interactive accent
- No gradients, no textures, no decorative chrome
- Strong visual calm, especially in auth and dashboard flows

## 2. Tailwind Theme Tokens

These values are the current source of truth from
`frontend/tailwind.config.js`.

### Dark mode

- `darkMode: "class"`

### Colors

- `primary: #0673e0`
- `background-light: #f5f7f8`
- `background-dark: #0f1923`

### Typography

- `fontFamily.display: ["Inter", "sans-serif"]`

### Border radius

- `DEFAULT: 0.7rem` (`11.2px`)
- `lg: 1rem` (`16px`)
- `xl: 1.5rem` (`24px`)
- `full: 9999px`

## 3. Color Palette & Roles

### Primary surfaces

- **Black** (`#000000`): Hero sections, immersive product framing
- **Background Light** (`#f5f7f8`): Main light surfaces and form pages
- **Background Dark** (`#0f1923`): Deep dark UI surface when black is too stark
- **Near Black Text** (`#1d1d1f`): Primary text on light backgrounds
- **White** (`#ffffff`): Primary text on dark backgrounds

### Interactive colors

- **Primary Blue** (`#0673e0`): Primary CTA, focus ring, interactive emphasis
- **Link Blue** (`#0066cc`): Text links on light backgrounds
- **Bright Blue** (`#2997ff`): Text links on dark backgrounds

### Text colors

- **Primary Dark Text** (`#1d1d1f`)
- **Secondary Dark Text** (`rgba(0, 0, 0, 0.8)`)
- **Tertiary Dark Text** (`rgba(0, 0, 0, 0.48)`)
- **Muted Light Text** (`#86868b`)

### Supporting surfaces

- **Dark Surface 1** (`#272729`)
- **Dark Surface 2** (`#262628`)
- **Dark Surface 3** (`#28282a`)
- **Dark Surface 4** (`#2a2a2d`)
- **Dark Surface 5** (`#242426`)
- **Button Light** (`#fafafc`)
- **Overlay** (`rgba(210, 210, 215, 0.64)`)
- **White 32%** (`rgba(255, 255, 255, 0.32)`)

### Shadow

- `rgba(0, 0, 0, 0.22) 3px 5px 30px 0px`

## 4. Typography

### Primary font choice

- **Display and UI font**: `Inter, sans-serif`

The current implemented font token is `Inter`. Any future migration to a closer
SF Pro-like stack must be reflected first in Tailwind and then in this file.

### Typography hierarchy

| Role            | Font  | Size | Weight  | Line Height | Letter Spacing    |
| --------------- | ----- | ---- | ------- | ----------- | ----------------- |
| Display Hero    | Inter | 56px | 600     | 1.07        | -0.28px           |
| Section Heading | Inter | 40px | 600     | 1.10        | normal            |
| Tile Heading    | Inter | 28px | 400     | 1.14        | 0.196px           |
| Card Title      | Inter | 21px | 700     | 1.19        | 0.231px           |
| Sub-heading     | Inter | 21px | 400     | 1.19        | 0.231px           |
| Body            | Inter | 17px | 400     | 1.47        | -0.374px          |
| Body Emphasis   | Inter | 17px | 600     | 1.24        | -0.374px          |
| Button          | Inter | 17px | 400-500 | 1.00-1.40   | -0.01em to normal |
| Link            | Inter | 14px | 400-500 | 1.43        | -0.224px          |
| Caption         | Inter | 14px | 400     | 1.29        | -0.224px          |
| Micro           | Inter | 12px | 400-600 | 1.33        | -0.12px           |

### Typography rules

- Headlines must feel compressed and direct
- Body copy stays left-aligned
- Only hero blocks may center headlines
- Track text tightly; avoid loose spacing
- Avoid weights above `700`

## 5. Component Styling

### Buttons

#### Primary CTA

- Background: `primary` (`#0673e0`)
- Text: `#ffffff`
- Height: `48px`
- Radius: `DEFAULT` (`0.7rem`) or `lg` (`16px`) depending on button emphasis
- Hover: darker blue shift
- Focus: `ring-4` with `primary/20` or `primary/30`
- In authenticated app shells, all page-level action buttons must live in the
  shell header, positioned immediately to the left of the notifications button
- These actions are dynamic and must change according to the current page
- Action clusters may contain both primary and secondary buttons, but the most
  important step for the current page should remain visually dominant
- Page content areas and internal table toolbars must not duplicate these page
  actions when they already exist in the shell header
- Primary actions should use the shared `PrimaryBtn` component
- Disabled primary actions should keep the `PrimaryBtn` component and switch to
  the muted dark gray disabled state instead of introducing a separate button
  style

#### Pill links

- Transparent background
- Border radius: `full`
- Border: `1px solid currentColor`
- Use for lightweight secondary actions

#### Secondary action button

- Background: `#f5f7f8`
- Text: `#1d1d1f`
- Radius: `DEFAULT` (`0.7rem`)
- Hover: slightly darker neutral fill (`#e8e8ed`)
- Use the shared `SecondaryBtn` component for secondary action buttons such as
  `Editar` or `Cancelar`

### Inputs

- Height: `48px`
- Background: `#ffffff`
- Border: `1px solid #d2d2d7`
- Text: `#1d1d1f`
- Placeholder: `#86868b`
- Radius: `DEFAULT` (`0.7rem`)
- Focus:
  - border color: `primary`
  - ring: `4px primary/20`

### Cards and panels

- Border radius:
  - default compact cards: `DEFAULT` (`8px`)
  - larger panels/forms: `lg` (`16px`)
  - oversized feature panels: `xl` (`24px`)
- Borders should stay subtle or absent
- Shadows should remain soft and singular

### Navigation

- Dark translucent background
- Blur + saturation treatment
- White or softened white nav copy
- Compact vertical height

### App shell header

- Authenticated workspace pages use a shell header above the main content canvas
- The search bar belongs to this shell header
- Notifications and profile controls belong to this shell header
- Page-specific action buttons belong to this shell header and must appear
  immediately before notifications
- The shell header is the source of truth for page actions; content canvases may
  contain filters and supporting controls, but must not duplicate page action
  buttons already exposed in the shell

## 6. Layout Principles

### Split layouts

- Preferred for auth and high-focus onboarding pages
- Dark hero or value proposition on one side
- Light functional surface on the other side
- On mobile, collapse to a single light functional column

### Containers

- Max form width: around `380px`
- Center forms vertically where possible
- Use wide margins and strong empty space around auth surfaces

### Whitespace

- Keep broad breathing room around main card/form elements
- Separate sections with color fields rather than decorative separators

## 7. Border Radius Rules

These are the current official radius tokens:

- `rounded`: `11.2px`
- `rounded-lg`: `16px`
- `rounded-xl`: `24px`
- `rounded-full`: `9999px`

### Usage guidance

- Inputs: `rounded`
- Primary auth buttons: `rounded-lg`
- Basic cards: `rounded` or `rounded-lg`
- Pills and lightweight action links: `rounded-full`

## 8. Responsive Behavior

### Breakpoints

| Name          | Width       |
| ------------- | ----------- |
| Small Mobile  | <360px      |
| Mobile        | 360-480px   |
| Mobile Large  | 480-640px   |
| Tablet Small  | 640-834px   |
| Tablet        | 834-1024px  |
| Desktop Small | 1024-1070px |
| Desktop       | 1070-1440px |
| Large Desktop | >1440px     |

### Responsive rules

- Hero headlines scale from `56px` to `40px` to `28px`
- Split layouts collapse to one column on mobile
- Section color fields must remain intact at every breakpoint
- Image-led sections preserve silhouette and aspect ratio

## 9. Do and Don’t

### Do

- Use `primary` as the single action color
- Use `background-light` and black/dark surfaces for visual rhythm
- Keep forms clean and quiet
- Use `font-display` for headline moments
- Prefer `rounded-lg` for auth inputs and buttons

### Don’t

- Don’t add extra accent colors
- Don’t add gradients or textures
- Don’t use thick borders on surfaces
- Don’t use heavy multi-layer shadows
- Don’t center body text by default
- Don’t diverge from these tokens without updating this file first

## 10. Current Auth Screen Guidance

The login page should follow this structure:

- Split-screen layout on desktop
- Left side:
  - black hero surface
  - strong headline
  - short supporting statement
- Right side:
  - `background-light`
  - compact centered form
  - single primary CTA
  - lightweight secondary action below
- The `NEW_PASSWORD_REQUIRED` step must stay in the same card, inline, without
  modal or new route

## 11. Maintenance Rule

If Tailwind theme tokens change, this document must be updated in the same
change set where the config changes.
