# RAG Data Plane — Spec

## Objetivo
Gerenciar conhecimento corporativo com:
- ingestão de documentos
- versionamento
- chunking + embeddings
- indexação em vector store
- retrieval com citações (proveniência)
- controle de acesso por tenant/centro
- LGPD/retention

## Pipeline
1) Ingest (upload/conector)
2) Normalize (texto + metadados)
3) Classify (tipo de doc)
4) Chunk (regras por tipo)
5) Embed (AI Gateway)
6) Index (vector DB)
7) Retrieve (hybrid search)
8) Grounded Answer (com citações e trechos)

## Entidades sugeridas (DB)
### documents
- id
- org_id
- cost_center_id (nullable)   # null => doc corporativo
- title
- source_type: upload | connector
- source_uri
- doc_type: brand | legal | product | faq | crisis | research | other
- tags (jsonb)
- version (int)
- checksum
- status: active | archived
- created_at

### document_chunks
- id
- document_id
- chunk_index
- content (text)
- content_hash
- metadata (jsonb)            # page, heading etc.
- embedding (vector)          # pgvector ou external store ref
- created_at

### retrieval_logs
- id
- org_id
- cost_center_id (nullable)
- query
- filters (jsonb)
- top_k
- results (jsonb)             # chunk ids + scores
- created_at

## Vector Store opções
- MVP/SaaS: Postgres + pgvector
- Enterprise: Milvus/Weaviate/Pinecone (depende do modo)

## API sugerida
- POST /knowledge/documents (upload + metadata)
- GET  /knowledge/documents?ccId=&type=&tag=
- POST /knowledge/reindex?documentId=
- POST /knowledge/query
Body: { query, ccId, filters, top_k, require_citations=true }
Returns: answer + citations + chunk excerpts

## Regras de resposta
- Sem fonte -> “Não encontrei evidência suficiente nos documentos”
- Sempre retornar citações (document_id + trecho + score)
