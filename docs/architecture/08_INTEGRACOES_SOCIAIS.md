# Integrações Sociais (MVP)

## Princípio
Usar APENAS integrações oficiais (OAuth + APIs). Onde não for possível publicar, gerar Draft e exportar.

## Meta (Instagram/Facebook)
- Facebook Graph API
- Requisitos: conta business, permissões, páginas, IG conectado
- Ações: publicar, coletar métricas (e agendar se permitido no setup)

## LinkedIn
- Publicação em Page (quando o app tiver permissões adequadas)
- Para perfil pessoal: evitar automação; preferir draft + 1 clique manual

## Outros (Fase 2)
- X/Twitter, TikTok, YouTube: verificar limites e permissões por API

## Regras para evitar bloqueios
- Rate limiting por provider
- Rotina de refresh token
- Health check de conexão
- Logs de erro por provider e circuito de retry
