# Cypress E2E — AgroPS

## Requisitos

- Node + pnpm
- Frontend en `http://localhost:5173` (Vite)

## Comandos

```bash
# UI interactiva
pnpm cy:open

# Headless (levanta Vite automáticamente)
pnpm test:e2e

# Solo runner (si ya tienes `pnpm dev`)
pnpm cy:run
```

Las pruebas del panel autenticado **no** dependen del backend real: interceptan
`/api/v1/**` y usan un JWT stub en `localStorage`.
