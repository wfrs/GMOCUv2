# GMOCU Frontend

React + TypeScript + Vite frontend for GMOCU.

## Stack

- React
- TypeScript
- Vite
- ESLint

## Environment

Install dependencies:

```bash
npm ci
```

## Development

Run the dev server:

```bash
npm run dev
```

Default URL:

- `http://localhost:5173`

The frontend expects the backend API at `/api` and is intended to run against the FastAPI backend in `../backend`.

## Checks

Lint:

```bash
npm run lint
```

Production build:

```bash
npm run build
```

## Notes

- The favicon is served from `public/favicon.ico`.
- The browser title and in-app version badge are populated from the backend health endpoint at runtime.
- The current main app shell lives in `src/App.tsx`.
