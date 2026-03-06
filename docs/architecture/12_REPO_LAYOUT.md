# Layout de Repositório (sugestão)

repo/
  apps/
    web/                # Next.js
    api/                # FastAPI ou NestJS
    worker/             # Jobs/queue
  packages/
    shared/             # DTOs, types, utils
  infra/
    terraform/          # opcional
    docker/
  docs/
    (estes .md)
  scripts/
    seed/
    migrations/

## Observação
- Se preferir monorepo: turborepo (JS) ou poetry workspace (Python).
- CI/CD: GitHub Actions (build/test/lint/deploy).
