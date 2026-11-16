---
version: alpha
name: Food Intelligence
description: Evidence-led packaged-food analysis with a warm, precise consumer decision-support interface.
colors:
  primary: "#234B39"
  deep: "#172C28"
  sage: "#DDE8D9"
  soft: "#EAF0E8"
  ivory: "#F8F6EF"
  text: "#202B25"
  muted: "#5F6961"
  border: "#E5E8E1"
  warning: "#E9A65B"
  danger: "#D96B63"
typography:
  sans:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
  display:
    fontFamily: "Manrope, Inter, ui-sans-serif, system-ui, sans-serif"
  data:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
rounded:
  control: "0.75rem"
  card: "1.125rem"
  pill: "9999px"
spacing:
  content-max: "80rem"
  section-gap: "1.5rem"
components:
  app-shell: { navigation: "deep forest sidebar; responsive mobile drawer" }
  card: { surface: "white on warm ivory", border: "subtle", radius: "card" }
  button: { primary: "forest fill", secondary: "white outline", focus: "visible forest ring" }
  field: { surface: "white", border: "line", focus: "visible forest ring" }
  evidence: { declared: "sage", derived: "blue", interpreted: "amber", verified: "green", unknown: "neutral" }
  chart: { palette: "forest, sage, amber, restrained semantic red" }
---

# Food Intelligence Design System

## Overview

### Creative North Star

The interface should feel like a food-label inspection desk: warm paper, clear type, structured evidence, and calm analytical instruments. The distinctive signature is the evidence trail attached to product details: a value is always shown with its source state and missing information stays visibly missing.

### Product context and register

- **Audience and primary job:** People comparing Indian packaged-food labels who need to understand product identity, ingredients, nutrition, claims, and available prices.
- **Target market(s) and evidence:** India is the product's stated context and the supported product categories, INR pricing, Open Food Facts usage, FSSAI references, and English India locale appear in repository documentation and API behavior.
- **Locale(s) and language policy:** English (`en-IN`) currently. Use Indian number and currency conventions where applicable; do not imply localization beyond the implemented language.
- **Usage scene:** Desktop and mobile browser use while checking a package, saved product page, or analysis report.
- **Register:** Hybrid. The public home page is editorial and explanatory; application routes are task-oriented product UI.
- **Memorable signature:** Field-level evidence labels and an explicit provenance trail.
- **Restraint:** Reports, forms, comparisons, and analytics favor legibility and trustworthy data over decoration.
- **Anti-references:** Generic admin templates, retailer storefronts, fabricated product imagery, and medical-looking diagnostic interfaces.
- **Token ownership/runtime mapping:** Runtime CSS tokens in `web/src/app/globals.css` are canonical. This document mirrors them; update both when changing shared visual decisions.

## Colors

Forest `#234B39` anchors actions, deep forest `#172C28` anchors navigation, and ivory `#F8F6EF` warms the canvas. Sage `#DDE8D9` and soft green `#EAF0E8` mark supportive evidence surfaces. Text uses `#202B25`; muted text uses the darker accessible `#5F6961`; borders use `#E5E8E1`. Amber `#E9A65B` signals a recoverable caution, and red `#D96B63` signals an error or potential inconsistency. The color alone never carries a status: labels and icons accompany it.

## Typography

Inter is the body and data face; Manrope is reserved for headings. Use tabular numerals for scores, nutrient amounts, timestamps, and prices. Preserve natural sentence case in labels and actions. System UI fallbacks keep the interface readable when remote font loading is unavailable.

## Layout

Application screens use a centered content area up to 80rem inside a responsive shell. Desktop uses a collapsible deep-forest sidebar; mobile uses a top bar and navigation drawer. Cards and section gaps follow the existing 18px card radius and 24px rhythm. Dense comparisons scroll horizontally inside their own region rather than widening the page. Reserve space for async states and product imagery.

## Elevation & Depth

Hierarchy comes primarily from paper-like white surfaces, subtle borders, and restrained shadows. Use blur only for sticky navigation surfaces. Avoid glass effects and stacked shadows on analytical content.

## Shapes

Controls use 12px corners, cards use 18px corners, and status badges use pill shapes. The icon family is the repository's custom, consistent outline SVG set in `web/src/components/icons.tsx`; keep icon-only actions named for assistive technology.

## Components

### Foundational visual states

Controls need clear hover, focus-visible, selected, disabled, busy, warning, and error states. Loading surfaces use stable skeleton geometry or a labeled spinner. Respect `prefers-reduced-motion`.

### Buttons and actions

Use solid forest for the primary action, white bordered buttons for secondary actions, and text links for low-emphasis navigation. A busy action keeps its original footprint and has a perceivable status.

### Navigation and data display

The landing page header and application sidebar are deliberate register variants. Product lists, comparison tables, charts, evidence badges, and score indicators reuse shared primitives. Charts need titles, units or meaningful descriptions, and a text fallback when data is unavailable.

### Forms and overlays

Inputs use shared field styling and explicit labels. URL, saved-page, image, and manual-entry flows remain separate and honest about persistence and verification. Uploads explain accepted file types and size limits. Mobile navigation behaves as an accessible modal drawer. Errors stay inline with a next step.

### Iconography

Use the local outline SVG icon set. Keep icons small and optically aligned; text labels remain on primary actions.

### Motion

Use short transitions for hover and state changes only. Disable nonessential motion for reduced-motion users. Do not animate analytical charts to imply significance.

### Content and data visualization

Use plain, non-clinical language. Distinguish total pack price from normalized unit price. Label demo records as synthetic. Never imply ML, verification, image validation, retailer authorization, or healthier outcomes beyond current evidence. Keep missing values unknown.

## Do's and Don'ts

- **Do:** Show provenance and evidence state beside a claim or value.
- **Do:** Use API data for product counts and distributions; show an honest empty or unavailable state when data is absent.
- **Don't:** Add stock product imagery or fabricated real-product statistics.
- **Don't:** Present deterministic scores as medical assessments or trained-model predictions.
