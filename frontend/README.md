# SiningAI Frontend

Editorial-style React frontend for SiningAI, built with Vite + Tailwind.

## Quick start

```bash
cd frontend
npm install
npm run dev
```

Then open the URL Vite prints (default http://localhost:5173).

In a separate terminal, also run the agent:

```bash
# from siningai/ root, with venv active
adk api_server --allow_origins "*"
```

The frontend defaults to talking to `http://localhost:8000`. Change it via the
⚙ Settings panel (top-right of the masthead) — useful when you point at a
deployed Cloud Run URL later.

## Structure

```
src/
├── App.jsx                 root layout, two-column editorial grid
├── main.jsx                React entry
├── index.css               Tailwind + editorial base styles
├── lib/
│   ├── api.js              all ADK API calls (centralised)
│   └── stages.js           stage helpers (label/color)
├── components/
│   ├── layout/
│   │   ├── Masthead.jsx
│   │   └── SectionLabel.jsx
│   ├── gallery/
│   │   ├── Gallery.jsx
│   │   ├── PieceCard.jsx
│   │   ├── VersionTimeline.jsx
│   │   └── StageChip.jsx
│   ├── chat/
│   │   ├── Chat.jsx
│   │   ├── Message.jsx
│   │   ├── Composer.jsx
│   │   └── QuickActions.jsx
│   └── ui/
│       ├── ConnectionBanner.jsx
│       └── Settings.jsx
```

## Design notes

- **Palette:** paper white, near-black ink, terracotta accent. Color is rare on purpose.
- **Type:** Fraunces (display serif), Newsreader (body serif), Inter (UI sans),
  JetBrains Mono (metadata). Loaded via Google Fonts.
- **Editorial primitives:** `SectionLabel` (small-caps + hairline rule), `editorial-card`,
  `pull-rule`, `hairline`, `btn-primary`, `btn-ghost`, `field`, `smallcaps`. Reuse
  these instead of writing one-off Tailwind chains — they keep the visual language
  consistent.

## Building for deploy

```bash
npm run build         # → frontend/dist/
npm run preview       # local preview of the build
```

Drop the `dist/` folder onto Firebase Hosting, Vercel, or any static host.
