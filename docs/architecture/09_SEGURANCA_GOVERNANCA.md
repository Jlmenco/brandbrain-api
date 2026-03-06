# Segurança, Governança e Compliance

## Regras de segurança
1) Tokens OAuth criptografados (KMS/Secret Manager).
2) Separação por centro de custo: tokens, posts, leads e métricas isolados.
3) RBAC:
   - Owner: tudo
   - Admin: tudo no org
   - Editor: criar/editar/submeter/aprovar conteúdos (configurável)
   - Viewer: apenas leitura
4) Auditoria:
   - Toda ação relevante gera audit_logs
5) Conteúdo e compliance:
   - Filtro de palavras proibidas
   - Detecção de promessas absolutas (ex.: “garantido”, “milagre”, “100%”)
   - Bloqueio de política/religião se configurado
6) Human-in-the-loop default ON.
7) Autopost (se existir) deve ser feature com:
   - Limites rígidos
   - Allowlist de temas
   - Revisão periódica

## Observabilidade
- Logs estruturados (json)
- Sentry para exceções
- Métricas de jobs (sucesso/falha)

## LGPD
- Leads e dados pessoais: consentimento, retenção, exportação e delete.
- Minimização: coletar apenas o necessário.
