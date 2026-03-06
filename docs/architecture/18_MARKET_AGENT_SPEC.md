# Market Intelligence Agent - Spec

## Objetivo
Agente de análise de mercado que:
- Monitora tendências e tópicos por nicho/marca
- Observa concorrentes/referências (lista configurável)
- Produz achados (findings) com fontes e datas
- Produz brief semanal por centro de custo e também um brief macro do Grupo
- Gera Content Briefs prontos para alimentar o Marketing Agent (posts)

## Princípios (guardrails)
- Nada de scraping agressivo/logins indevidos.
- Preferir fontes públicas (RSS, Trends, relatórios, páginas públicas).
- Toda afirmação factual deve ter: fonte + data + trecho resumido.
- Separar "FATO" vs "INFERÊNCIA" e incluir score de confiança.

## Entradas
- orgId
- ccId (opcional)
- lista de termos de interesse (keywords)
- lista de concorrentes/referências
- região/idioma (pt-BR, Brasil)
- frequência de coleta (daily) e consolidação (weekly)

## Saídas
1) Market Findings (diários):
- título
- resumo
- tags
- fonte (url), data, contexto
- confiança (0-1)

2) Weekly Market Brief (semanal):
- Top 5 tendências
- Top 5 perguntas do público
- 5 ideias de conteúdo
- 3 oportunidades de campanha
- 3 riscos / tópicos a evitar
- referências (lista de fontes)

3) Content Briefs (para posts):
- Tema
- Tese
- 3 argumentos
- 1 dado/estatística (com fonte)
- CTA sugerido
- Formato por canal

## Endpoints (API)
- POST /agent/market/run            # roda coleta e gera findings
- POST /agent/market/weekly-brief   # consolida semana
- GET  /market/findings?ccId=&from=&to=
- GET  /market/briefs?ccId=&week=
- POST /market/sources              # cadastrar fontes por cc
- POST /market/competitors          # cadastrar concorrentes por cc
