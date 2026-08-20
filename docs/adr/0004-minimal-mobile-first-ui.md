# ADR-0004: Minimal mobile-first UI direction

- **Status**: Accepted
- **Date**: 2026-08-20

## Context

The room-screen prototype explored a decorative "toy tabletop" visual language: chunky shapes, bright per-player colors, rotated cards, and grid-based responsive layouts. The MVP's priority is a working full-stack app running locally in Docker; visual polish is not. A second prototype pass replaced it with a stripped-down, function-first theme.

Two concrete problems drove the change:

- The prototype used CSS grid for layout, which fought the viewport on small screens (unpredictable scaling, zoom-out behavior on phones).
- The original `index.html` lacked a viewport meta tag, so mobile browsers rendered a scaled-out desktop layout.

## Decision

The UI follows a single minimal direction:

- **Function over form**: white/gray surfaces, one blue accent (`#2563eb`), system font stack, 1px borders, no shadows, no decorative shapes or rotations.
- **Tailwind CSS v4** for all styling, expressed as utility classes directly in components — no custom CSS files, no design tokens to maintain.
- **Flexbox only** — CSS grid is banned from the UI.
- **Mobile-first**: single-column layouts built for small screens; desktop is the enhancement, not the base.
- **Flat-stack navigation**: a single home hub (join by code, recent sessions, create, leaderboard); detail screens push onto a stack with browser back-button support via `history.pushState`. No tab bar.
- **Hand-rolled router** — no routing dependency; screens are switched in `main.tsx` by pathname.

## Consequences

- New screens are cheap to add: a component with Tailwind classes plus a route entry.
- Layout regressions are guarded by source-level tests (no grid, viewport meta, Tailwind wiring).
- The prototype playground (`room-prototype.tsx`, variants B/C) was removed; variant A became the production session screen.
- Visual identity is intentionally plain; if a branded look is wanted later, it is a theming pass on top of the same structure.

## Alternatives considered

- **CSS grid for responsive layouts** — rejected: caused scaling/responsiveness problems on mobile viewports.
- **Component library (e.g. daisyUI)** — rejected: adds a dependency and a look we would have to strip down anyway.
- **Tab-bar navigation** — rejected: more chrome than an MVP needs; the session screen should stay full-screen during live play.