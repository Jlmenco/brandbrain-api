# Connectors & Ingestion — Spec

## Objetivo
Permitir ingestão de conhecimento corporativo via:
- Upload manual (MVP)
- Google Drive/Docs (fase 2)
- Confluence/Notion (fase 2/3)
- SharePoint (enterprise)

## Conector: Upload manual (MVP)
- Endpoint: POST /knowledge/documents (multipart)
- Metadados: ccId, doc_type, tags, data_classification, shareable

## Conector: Google Drive/Docs
- OAuth + scopes mínimos
- Indexar:
  - Docs (texto)
  - PDFs
  - Pastas selecionadas
- Sincronização:
  - full sync inicial
  - incremental (por modifiedTime)
- Guardar:
  - drive_file_id
  - version
  - checksum

## Conector: Confluence/Notion/SharePoint
- Similar:
  - selecionar spaces/pages
  - extrair conteúdo
  - versionar e reindexar

## Jobs
- ingestion_jobs (fila)
- reindex_jobs

## LGPD/Retention
- apagar documento -> apagar chunks e embeddings
- exportar logs de acesso se solicitado
