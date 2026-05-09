Mutual Fund FAQ Assistant — Phase-wise Architecture
Companion design document to problemStatement.md. Goal: a facts-only, source-cited, RAG-based Q&A assistant for mutual fund schemes (Groww context). Iteration scope: the corpus is strictly the 5 Groww HDFC scheme URLs listed in Phase 0 — no other URLs are ingested or cited.

1. Architectural Principles
These principles drive every phase below:
Facts-over-Intelligence — retrieval grounds every answer; the Groq-hosted generation model only reformats retrieved facts (optional path; default remains extractive).
Single source of truth per answer — exactly one citation URL per response.
Closed corpus — only whitelisted official URLs are ingested; nothing else can leak in.
Refusal by default — advisory / opinion queries are deflected with a polite, educational redirect.
PII-free — no PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers are collected, logged, or processed.
Determinism > Creativity — low temperature, strict prompt contracts, hard answer-length caps (≤ 3 sentences).
Auditability — every response is traceable to a chunk, a document, a source URL, and a "last updated" timestamp.
3. Phase-wise Architecture
The build is structured in 6 phases, each phase producing a working, demoable artifact.

Phase 0 — Foundation & Governance (Day 0)
Purpose: lock down scope, sources, and guardrails before writing code.
Selected AMC: HDFC Mutual Fund (HDFC Asset Management Company Ltd.)
Selected Schemes (5, category-diverse) — these 5 Groww URLs are the entire corpus for this project. No other URLs are used.
#
Scheme
Category
Source URL (Groww)
1
HDFC Mid Cap Fund — Direct Growth
Mid Cap
https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
2
HDFC Equity Fund — Direct Growth
Flexi Cap
https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
3
HDFC Focused Fund — Direct Growth
Focused
https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth
4
HDFC ELSS Tax Saver — Direct Plan Growth
ELSS
https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
5
HDFC Large Cap Fund — Direct Growth
Large Cap
https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth

Scoping decision (overrides the generic “15–25 URLs” guideline in the problem statement): For this iteration, the corpus is strictly limited to the 5 Groww scheme pages above. No AMC PDFs (KIM/SID/factsheets), no AMFI pages, no SEBI pages, no AMC FAQ pages, and no other Groww pages are ingested or cited. Every fact the assistant returns must come from one of these 5 URLs, and every citation must be one of these 5 URLs — verbatim. This is enforced by sources.yaml and by the Phase 3 post-processor’s whitelist check.
Deliverables
AMC + 5 schemes locked (above).
sources.yaml containing exactly these 5 URLs (no more, no less).
Refusal taxonomy: intents to refuse (advice, comparison, prediction, recommendation).
PII deny-list and redaction regex set.
config/sources.yaml — final registry for this iteration
schemes:
  - id: hdfc_mid_cap
    name: HDFC Mid Cap Fund - Direct Growth
    category: Mid Cap
    sources:
      - url: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
        doc_type: Product_Page

  - id: hdfc_equity
    name: HDFC Equity Fund - Direct Growth
    category: Flexi Cap
    sources:
      - url: https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
        doc_type: Product_Page

  - id: hdfc_focused
    name: HDFC Focused Fund - Direct Growth
    category: Focused
    sources:
      - url: https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth
        doc_type: Product_Page

  - id: hdfc_elss
    name: HDFC ELSS Tax Saver - Direct Plan Growth
    category: ELSS
    sources:
      - url: https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
        doc_type: Product_Page

  - id: hdfc_large_cap
    name: HDFC Large Cap Fund - Direct Growth
    category: Large Cap
    sources:
      - url: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
        doc_type: Product_Page

# Hard rule: any URL not present in this file MUST NOT appear in any answer.
# CI compliance gate (Phase 5) fails the build if a generated answer cites a URL
# outside this list.

Citation rule (enforced by Phase 3 post-processor):
The cited URL must be exactly one of the 5 URLs above (string-equal match against sources.yaml).
If no chunk from these 5 URLs supports the query at the confidence threshold → respond “I don’t have a verified answer for that. Please refer to the official scheme page: <best-matching scheme URL from the 5>.”
For refusals of advisory/comparison/prediction queries → the “educational link” returned is the Groww scheme page most relevant to the query (or a generic one of the 5 if no scheme is detected). No off-corpus link (AMFI/SEBI/etc.) is ever returned.
What the assistant explicitly cannot answer in this iteration (because the supporting source is not in the corpus):
Tax-statement / capital-gains download walkthroughs (AMC help pages not ingested).
Deep regulatory definitions sourced from AMFI/SEBI explainers.
Anything sourced from KIM/SID PDFs that isn’t already surfaced on the Groww product page.
For these, the assistant returns the “I don’t have a verified answer” response with the relevant Groww scheme link.
Components
config/sources.yaml — the 5-URL registry above; metadata: {scheme_id, doc_type, last_updated, content_hash}.
config/refusal_intents.yaml — patterns + canned refusal copy (educational link is always one of the 5 Groww URLs).
config/disclaimer.txt — “Facts-only. No investment advice.”
Exit criteria:
sources.yaml contains exactly 5 entries — the 5 Groww URLs above — and nothing else.
A reviewer can diff the URL list against the problem statement and confirm 1:1 match.
Refusal copy and “I don’t know” copy never reference any URL outside the 5.

Phase 1 — Ingestion & Corpus Build (Offline Pipeline)
Purpose: convert the 5 whitelisted Groww URLs into a clean, chunked, embedded, queryable corpus.
Scheduled refresh (latest data): use a GitHub Actions workflow with on: schedule: (and optionally workflow_dispatch for manual runs). Each run executes the Phase 1 toolchain (1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7) so the corpus and index stay aligned with live Groww pages without a dedicated VM cron. Committing refreshed data/ is optional (many teams upload artifacts from the workflow instead). Details under Sub-phase 1.7 below.

Phase 1 is broken into 7 sub-phases, each independently demoable. Each sub-phase has a single, narrow contract — its inputs, outputs, code module, and exit criteria are below. Implementation order is strictly 1.1 → 1.7; later sub-phases consume the outputs of earlier ones.

### Sub-phase 1.1 — URL Ingestion & Scraping
**Objective**: Pull the 5 Groww HTML pages and persist raw snapshots with comprehensive error handling and ETag support.

**Inputs**:
- config/sources.yaml (the 5 URLs from Phase 0)
- Previous ETag cache for conditional requests
- Robots.txt compliance rules

**Outputs**:
- data/raw/<scheme_id>/<timestamp>.html (raw HTML content)
- data/raw/<scheme_id>/<timestamp>.json (metadata: {url, fetched_at, http_status, etag, content_hash_raw, fetcher_kind})
- ETag cache file for next run
- Fetch health report per URL

**Dependencies**:
- httpx for HTTP requests with ETag support
- playwright for JavaScript-rendered content fallback
- robots.txt parser for compliance checking
- hashlib for content hash generation

**Risks**:
- Network timeouts and connection failures
- Rate limiting from target servers
- Robots.txt disallowance
- JavaScript-rendered content requiring browser fallback
- Content quality issues (too short, missing keywords)
- ETag validation failures
- Redirect loops and URL changes

**Validation Strategy**:
- Minimum content length thresholds (>1000 bytes)
- Must-have keyword presence ("mutual fund", "HDFC", "fund")
- HTTP status code validation (200-299 range)
- Content hash consistency checks
- Robots.txt compliance verification
- ETag validation for conditional requests

### Sub-phase 1.2 — HTML Cleaning & Normalization
**Objective**: Convert raw HTML to structured text with section anchors and normalized encoding.

**Inputs**:
- Raw HTML files from sub-phase 1.1
- Section extraction rules and CSS/XPath selectors
- Must-have anchor definitions (Expense Ratio, Exit Load, etc.)

**Outputs**:
- data/processed/<scheme_id>/extracted.json with structured sections
- Section presence validation report
- Extraction health status (ok/degraded)
- Metadata: scheme_id, source_url, fetched_at, sections array

**Dependencies**:
- trafilatura for main content extraction
- BeautifulSoup for targeted element extraction
- CSS/XPath selector library
- Table parsing for structured data
- Image alt-text extraction for riskometer

**Risks**:
- Missing must-have sections
- JavaScript-rendered content not captured
- Image-only information without alt text
- Dynamic content loading delays
- HTML structure changes breaking selectors
- Encoding issues with special characters
- Table parsing failures for numerical data

**Validation Strategy**:
- Must-have anchor presence validation (≥4 of 7 required)
- Section content length validation
- Extraction completeness checks
- Structure validation against expected schema
- Health scoring based on section coverage
- Cross-scheme consistency validation

### Sub-phase 1.3 — Structured Mutual Fund Metadata Extraction
**Objective**: Extract and normalize mutual fund-specific metadata with proper data typing and validation.

**Inputs**:
- Extracted JSON from sub-phase 1.2
- Mutual fund data schema definitions
- Field mapping and transformation rules
- Volatile field identification rules

**Outputs**:
- data/processed/<scheme_id>/metadata.json with structured MF data
- Field-level validation reports
- Data type normalization results
- Volatile vs stable field separation

**Dependencies**:
- Schema validation library (pydantic)
- Data transformation utilities
- Financial data parsers (percentages, currency, dates)
- Field mapping configurations
- Data quality validation frameworks

**Risks**:
- Incorrect data type parsing (strings vs numbers)
- Currency format inconsistencies (Rs. vs ₹ vs INR)
- Percentage format variations (1.11% vs 1.11)
- Date format inconsistencies across schemes
- Missing or null critical fields
- Numerical precision loss in parsing
- Field mapping errors between schemes

**Validation Strategy**:
- Schema validation against defined data models
- Data type consistency checks
- Range validation for numerical fields
- Format validation for dates, currency, percentages
- Cross-field consistency validation
- Mandatory field presence checks
- Data quality scoring and reporting

### Sub-phase 1.4 — Chunking Strategy
**Objective**: Split cleaned content into section-aware retrieval units with proper metadata and size optimization.

**Inputs**:
- Cleaned JSON from sub-phase 1.3
- Chunking parameters (soft cap: 250, hard cap: 400, overlap: 30)
- Section boundary detection rules
- Metadata preservation requirements

**Outputs**:
- data/processed/<scheme_id>/chunks.jsonl (one JSON per line)
- Chunk metadata: chunk_id, scheme_id, section, content_hash, etc.
- Chunking statistics report (count, size distribution)
- Section coverage validation report

**Dependencies**:
- Text segmentation library (sentence boundaries)
- UUID generation for chunk IDs
- JSON streaming for large datasets
- Token counting utilities
- Section detection algorithms

**Risks**:
- Over-chunking creating too many small pieces
- Under-chunking leaving large unusable chunks
- Cross-section bleeding causing context confusion
- Mid-sentence splits breaking semantic meaning
- Numeric fact separation (₹14,615.19 Cr split)
- Section metadata loss during chunking
- Inconsistent chunk sizes across sections

**Validation Strategy**:
- Chunk size distribution analysis (5-12 chunks per scheme)
- Section完整性验证 (all sections covered)
- No cross-section chunk validation
- Numeric fact integrity checks
- Metadata completeness validation
- Chunk boundary quality assessment
- Token count validation per chunk

### Sub-phase 1.5 — Embedding Generation
**Objective**: Generate dense vector representations for chunks with model versioning and quality validation.

**Inputs**:
- Chunks from sub-phase 1.4
- Embedding model configuration (bge-small-en, 384 dimensions)
- Batch processing parameters
- Model version and compatibility requirements

**Outputs**:
- data/index/embeddings.parquet (chunk_id, embedding[float32])
- embedder.json (model: "bge-small-en", version: "1.5", dim: 384)
- Embedding quality report (success rate, dimension validation)
- Processing statistics (timing, batch sizes)

**Dependencies**:
- sentence-transformers library
- PyTorch for model inference
- ChromaDB for vector storage
- Parquet file handling
- GPU/CPU detection and optimization

**Risks**:
- Model loading failures or corruption
- Insufficient memory for batch processing
- Embedding dimension mismatches
- Model version incompatibility
- Quality degradation in embeddings
- Processing timeouts for large batches
- Vector corruption during storage

**Validation Strategy**:
- Embedding dimension validation (384 for all chunks)
- Model version compatibility checks
- Vector quality assessment (similarity sanity checks)
- Round-trip validation (save → load → compare)
- Batch processing success rate monitoring
- Memory usage validation during processing
- Storage integrity verification

### Sub-phase 1.6 — Vector DB Persistence
**Objective**: Build and persist dense vector and sparse BM25 indexes with atomic operations and versioning.

**Inputs**:
- Chunks from sub-phase 1.4
- Embeddings from sub-phase 1.5
- Index configuration and parameters
- Storage path and versioning requirements

**Outputs**:
- data/index/chroma/ (ChromaDB collection with vectors and metadata)
- data/index/bm25.pkl (sparse keyword index)
- data/index/chunks.jsonl (canonical chunk store)
- data/index/manifest.json (build metadata, statistics)
- Index health and validation report

**Dependencies**:
- ChromaDB for vector storage and retrieval
- rank-bm25 for sparse indexing
- Atomic file operations for index swapping
- JSON and parquet file handling
- Index validation and verification tools

**Risks**:
- Index corruption during build process
- Insufficient disk space for large indexes
- Concurrent access conflicts during updates
- Vector index version incompatibility
- BM25 index building failures
- Metadata inconsistency between indexes
- Atomic swap operation failures

**Validation Strategy**:
- Index integrity validation and checksums
- Query capability testing with sample queries
- Metadata consistency checks between vector and sparse indexes
- Atomic swap success verification
- Storage space and permission validation
- Cross-index consistency validation
- Performance benchmarking for query speeds

### Sub-phase 1.7 — Scheduler & Automated Refresh Pipeline
**Objective**: Orchestrate the complete ingestion pipeline with GitHub Actions scheduling, incremental updates, and automated health monitoring.

**Inputs**:
- GitHub Actions workflow configuration
- Sources configuration from Phase 0
- Previous run metadata and content hashes
- Pipeline orchestration parameters
- Incremental update thresholds

**Outputs**:
- data/index/refresh_log.jsonl (run history, timings, outcomes)
- data/index/manifest.json (build metadata, statistics, version info)
- Health monitoring reports and automated alerts
- Drift detection notifications with change analysis
- Pipeline success/failure status per run
- Automated index updates and rollbacks
- GitHub Actions workflow artifacts

**Dependencies**:
- GitHub Actions for automated scheduling (cron triggers)
- Pipeline orchestration framework with incremental logic
- Content hash comparison utilities for change detection
- Health monitoring and alerting via GitHub Actions
- Atomic index management with versioning
- Error handling and recovery mechanisms
- Slack/email notification integration for failures

**Risks**:
- GitHub Actions workflow failures or missed runs
- Content drift causing excessive full rebuilds
- Index corruption during atomic updates
- Health monitoring blind spots in distributed runs
- Rollback failures during pipeline issues
- Resource exhaustion in GitHub Actions runners
- External dependency failures (API rate limits, network issues)
- Notification system failures for critical alerts

**Validation Strategy**:
- Pipeline end-to-end success validation with artifact verification
- Content hash drift detection with configurable thresholds
- Health check validation for all pipeline components
- Index integrity post-build verification with checksums
- GitHub Actions execution monitoring and alerting
- Rollback capability testing and validation in staging
- Resource usage monitoring within GitHub Actions limits
- Notification system testing and validation
- Incremental update efficiency metrics and optimization

Phase 2 — Retrieval Layer
Purpose: given a user query, surface the minimum set of chunks needed to answer factually with optimal precision and recall for mutual fund data.

Pipeline
Query
  │
  ├─► Query Normalizer  (NFKC, lowercase, collapse whitespace; MF tokens like ELSS/SIP/NAV/AUM; numerical token extraction)
  │
  ├─► Scheme Resolver   (NER-lite: longest substring match on scheme name + aliases from ``sources.yaml``; confidence scoring)
  │
  ├─► Hybrid Retriever
  │     ├─ Dense (same HF model as Phase 1.5; query = normalized text, or scheme_name then blank line then query when resolver hits — aligns with chunk embedding shape)
  │     ├─ Sparse (BM25, same tokenization as Phase 1.6 index)
  │     └─ Metadata Filter (scheme_id, section, doc_type filters)
  │     → Adaptive Weighted Reciprocal Rank Fusion → fused top‑10
  │       • **Dynamic Weighting**: Numeric-heavy queries (digits / ``₹`` / ``%``) increase sparse weight (0.6) vs dense (0.4)
  │       • **Semantic Queries**: Conceptual questions increase dense weight (0.7) vs sparse (0.3)
  │       • **Small Corpus Optimization**: For ~35 chunks, use ``min(20, n_candidates)`` per channel
  │
  ├─► Section-Aware Scoring  — light score boost when query keywords match a chunk's ``section`` (e.g. "exit load" → *Exit Load and Tax* +0.2)
  │
  ├─► Cross-Encoder Re-ranker  (default: ``BAAI/bge-reranker-base``) → top‑3 passages from fused results
  │
  ├─► Confidence Scoring  — Multi-factor confidence calculation based on retrieval quality, query type, and rerank scores
  │
  └─► Result Filter  — Minimum score threshold, duplicate removal, and whitelist URL enforcement
  │
Filters applied before retrieval (when detectable):
scheme_id = <resolved scheme> → intersect hybrid candidate lists with chunks for that scheme only. Adaptive filtering: if no results, relax scheme filter and search full corpus.
doc_type = Product_Page (only doc type in the corpus for this iteration).
section = <specific section> → filter results by section when query contains section-specific keywords.
Implementation: retrieval.hybrid_retriever — HybridRetriever loads IndexHandle + Embedder + CrossEncoder; CLI python -m retrieval.hybrid_retriever "your question".
Exit criteria: top-1 chunk contains the gold answer for ≥ 85% of a 30-question mutual fund eval set; average retrieval time < 100ms; confidence score correlation > 0.7 with human judgments.

Phase 3 — Reasoning & Guardrails (Orchestrator)
Purpose: turn a query + retrieved chunks into a compliant, ≤ 3-sentence answer — or a refusal — with URL policy enforced before anything is returned.

Generation stack: Groq LLM via OpenAI-compatible Chat Completions API (pip install "mf-faq[groq]", env GROQ_API_KEY). Default behavior: use_groq=None (auto) — Groq runs when GROQ_API_KEY is set; use use_groq=False or unset the key to stay extractive-only. Embeddings for retrieval stay as in Phase 1.5 (sentence-transformers and optionally OpenAI embeddings — unchanged).

Strict Rules (Non-negotiable):
- **Low Confidence Handling**: If answer confidence is low (< 0.3), explicitly state "information is unavailable"
- **No Hallucination**: Do NOT hallucinate financial information - all answers must be grounded in retrieved context
- **URL Policy**: Do NOT attach URLs unnecessarily - only one whitelisted URL per factual answer
- **PII Protection**: Do NOT expose personal/sensitive information detected in user queries
- **Grounded Responses**: Responses must remain grounded in retrieved context only
- **Citation Support**: Add citation support for retrieved chunks with source attribution
- **Environment Variables**: Use .env file for API key configuration (GROQ_API_KEY)

URL Policy (non-negotiable):
Situation
URLs in the assistant reply
PII detected in the user message (PAN, Aadhaar, email, phone, OTP, etc.)
None — use the locked pii_block template only.
Insufficient evidence / low confidence / empty retrieval ("don't know" path)
None — use dont_know_without_link only (ask user to name a scheme; no Groww link).
Non-factual intent (advisory / comparison / prediction refusal)
At most one — matching scheme's Groww URL from sources.yaml, or the first scheme's URL if none resolved.
Successful factual answer from retrieved chunks
Exactly one — citation source_url from the top chunk (must be on the whitelist).

Decision flow
               ┌──────────────────────────┐
                │   Incoming user query    │
                └────────────┬─────────────┘
                             ▼
                ┌──────────────────────────┐
        ┌──No──┤   PII detected?          │
        │      └────────────┬─────────────┘
        │                   │ Yes
        │                   ▼
        │      pii_block template — NO URL
        ▼
 ┌───────────────────────────────────────┐
 │  Intent Classifier                    │
 │  {factual | advisory | comparison |   │
 │   prediction}                         │
 └───────────┬─────────────┬─────────────┘
             │ factual     │ advisory / comparison / prediction
             ▼             ▼
   ┌─────────────────┐  ┌──────────────────────────────┐
   │ Retriever       │  │ Refusal Composer             │
   │ (Phase 2)       │  │ • polite; facts-only policy  │
   └────────┬────────┘  │ • exactly ONE Groww URL from   │
            ▼           │   whitelist (scheme match or │
   ┌─────────────────┐  │   default first scheme)      │
   │ Confidence ≥ τ ?│  └──────────────────────────────┘
   │ & hits non-empty│
   └──┬───────────┬──┘
   No │           │ Yes
      ▼           ▼
 dont_know      Groq or extractive body from top chunk
 _without_link  (≤ 3 sentences) + Source: URL +
 — NO URL       Last updated from sources: <date>
                 │
                 ▼
              Post-Processor
              • sentence count; banned tokens
              • exactly one whitelisted URL OR zero (see table above)
              • defensive PII scan on draft output

Generator contract
Extractive (default): build the body from the top reranked chunk only: first ≤ 3 sentences, strip any URLs embedded in chunk text so the reply does not accidentally contain extra links.
Groq (optional): Orchestrator(..., use_groq=None) (auto: Groq if GROQ_API_KEY is set), or use_groq=True to force the Groq path when a key is present, or use_groq=False for extractive-only (package extra [groq]). The model returns answer body only; Source and Last updated lines are appended in code so exactly one whitelist URL appears. On API/import failure or empty body → extractive fallback.
Groq governance: low temperature; same URL rules as extractive — no URL on PII block or don’t-know; exactly one whitelisted URL on successful factual answers; refusals keep one educational URL.
Hard post-checks (deterministic, non-LLM):
Route-aware URL count: PII and insufficient-evidence replies must contain zero http(s) URLs. Factual answers must contain exactly one URL, and it must appear in sources.yaml.
Sentence count ≤ 3 for the factual body (before the Source: line).
No banned tokens in the full draft (e.g., "recommend", "should invest", "better than", "will outperform").
Footer present on successful factual path: Last updated from sources: <YYYY-MM-DD>.
If post-checks fail on an otherwise retrieved answer → fall back to safe template with one whitelisted link (safe_template).
Exit criteria: 100% of generated answers respect the URL policy above on the eval set; 0 hallucinated or extra URLs on factual paths.

Phase 4 — User Interface (Minimal Web App)
Purpose: give a clean, trustworthy surface to the assistant.
Layout
┌──────────────────────────────────────────────────────────────┐
│  Mutual Fund FAQ Assistant                                   │
│  Facts-only. No investment advice.            [disclaimer]   │
├──────────────────────────────────────────────────────────────┤
│  Welcome! Ask a factual question about <AMC> schemes.        │
│                                                              │
│  Try one of these:                                           │
│   • What is the expense ratio of <Scheme A>?                 │
│   • What is the exit load of <Scheme B>?                     │
│   • What is the lock-in period for an ELSS fund?             │
├──────────────────────────────────────────────────────────────┤
│  [  type your question…                                ] [→] │
├──────────────────────────────────────────────────────────────┤
│  Answer area                                                 │
│  ─ short answer (≤3 sentences)                               │
│  ─ Source: <single link>                                     │
│  ─ Last updated from sources: <date>                         │
└──────────────────────────────────────────────────────────────┘

Stack: FastAPI in mf_faq.ui exposes POST /ask, GET /meta, GET /health, and serves a minimal static SPA from mf_faq/ui/static/ at / (same-origin fetch). No login, no cookies beyond session, no analytics that capture query text with PII.
UI rules
Disclaimer always visible.
Submit button disabled while a query is in flight.
Answer area renders the citation as a clickable link with rel="noopener nofollow".
"Copy answer" optional; "Share" deliberately omitted to discourage misuse.
Exit criteria: end-to-end demo: type question → get compliant answer with link + date.

Phase 5 — Evaluation, Compliance & Observability
Purpose: prove the system is accurate, safe, and stays that way.
5a. Evaluation harness
Suite
What it checks
Pass bar
Factual Q&A (30+ Qs)
Exact-match / numeric tolerance vs gold answer
≥ 90%
Citation correctness
Cited URL actually contains the fact
100%
Refusal suite (15+ Qs)
Advice/comparison/prediction queries get refused with educational link
100%
Out-of-corpus
Query about unknown scheme → "I don't have a verified answer"
100%
PII probes
Inputs with PAN/Aadhaar/email are rejected/redacted
100%
Length & format
≤ 3 sentences, 1 citation, footer present
100%

Tooling: a YAML test set + a small pytest runner that calls the API and asserts.
5b. Compliance checks (CI gate)
Every URL in any answer ∈ sources.yaml.
No banned advisory tokens in any answer.
No PII tokens stored in logs (log-line scanner).
5c. Observability
Structured logs: {request_id, intent, retrieved_chunk_ids, confidence, post_check_passed, latency_ms}.
No raw queries with PII persisted; queries are hashed for analytics.
Dashboard (lightweight): refusal rate, "I don't know" rate, top schemes asked about, ingestion freshness.
5d. Operational runbook
Source change detection → alert when any of the 5 Groww URLs 404s or content hash drifts > X%.
Weekly re-index job; manual override flag per source.
Exit criteria: all eval suites green in CI; runbook published.

4. Component Inventory (Cross-Phase)
Layer
Component
Responsibility
Phase
Governance
sources.yaml
Whitelist of allowed URLs
0
Governance
refusal_intents.yaml
Refusal patterns + canned copy
0
Ingestion
Fetcher
HTTP/PDF download, ETag/hash tracking
1
Ingestion
Extractor + Cleaner
HTML/PDF → clean text, table-aware
1
Ingestion
Chunker
Heading-aware semantic chunking
1
Ingestion
Embedder
Vector generation
1
Storage
Vector store
Dense ANN search (FAISS/Chroma)
1–2
Storage
Keyword index
BM25
1–2
Storage
Metadata store
Chunk metadata, source registry
1–2
Retrieval
Query normalizer
Acronym expansion, lowercase
2
Retrieval
Scheme resolver
Detect scheme to filter metadata
2
Retrieval
Hybrid retriever
Dense + BM25 + RRF
2
Retrieval
Re-ranker
Cross-encoder for precision
2
Orchestrator
PII guard
Reject inputs containing PII
3
Orchestrator
Intent classifier
factual vs advisory vs comparison etc.
3
Orchestrator
Confidence gate
Trigger "I don't know" on low retrieval score
3
Generation
Groq LLM caller
Templated, low-temp chat completion (optional vs extractive)
3
Generation
Post-processor
Length, citation, banned-token, PII checks
3
Generation
Refusal composer
Polite refusal + educational link
3
UI
FastAPI /ask API
JSON query → orchestrator result + structured logs
4
UI
Static SPA + CSS/JS
Welcome, examples, disclaimer, answer view, copy
4
Quality
Eval harness
Factual + refusal + format + PII suites
5
Quality
Compliance CI gate
Whitelist + banned-token + PII log scan
5
Ops
Refresh scheduler
GitHub Actions schedule (cron) + optional workflow_dispatch; nightly/weekly re-ingest + diff detection
1, 5
Ops
Observability
Structured, PII-free logs + dashboard
5


5. Data Flow — Single Query End-to-End
1. User types: "What is the exit load of HDFC Equity Fund Direct Growth?"
2. UI → POST /ask {query}
3. PII guard           → clean
4. Intent classifier   → factual
5. Query normalizer    → "what is the exit load of hdfc equity fund direct growth"
6. Scheme resolver     → scheme_id = hdfc_equity
7. Hybrid retriever    → top-10 chunks from
                         https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
8. Re-ranker           → top-1 chunk: "Scheme Details / Exit Load" section
9. Confidence gate     → score 0.82 ≥ τ → proceed
10. Groq generator (or extractive) → ≤3 sentence answer using only that chunk
11. Post-processor     → length OK, 1 URL OK, URL ∈ 5-URL whitelist OK,
                         no banned tokens, footer appended
12. Response:
    "HDFC Equity Fund Direct Growth charges an exit load of 1% if units are
     redeemed within 1 year of allotment; no exit load applies thereafter.
     Source: https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
     Last updated from sources: 2026-04-15"
13. Logs: {request_id, intent=factual, scheme_id=hdfc_equity,
          chunk_ids=[...], conf=0.82, checks=passed, latency_ms=740}
          (no raw query stored)


6. Risks & Mitigations
Risk
Mitigation
Groww updates a page → stale answer
Content-hash diff in nightly job; bump last_updated; alert if drift big
Groq model hallucinates a number
Numeric values must appear verbatim in retrieved chunk (regex check)
Groq model emits a non-whitelisted URL
Post-processor rejects + falls back to safe template
User asks for advice
Intent classifier + refusal composer (link = matching Groww scheme URL)
User pastes PAN/Aadhaar/email/phone
PII guard rejects request before retrieval; never logged
Ambiguous scheme name
Scheme resolver asks clarifying question (still facts-only, no opinions)
Performance/return question
Redirect to the relevant Groww scheme URL; never compute or compare returns
Low-confidence retrieval
"I don't have a verified answer" + matching Groww scheme URL
Fact only present in KIM/SID (off-corpus)
Return "I don't have a verified answer" + matching Groww scheme URL


7. Phase Roadmap (Suggested Timeline)
Phase
Outcome
Indicative effort
0
Sources whitelisted, refusal taxonomy ready
0.5 day
1
Corpus ingested + indexed
1.5 days
2
Hybrid retrieval + reranker working
1 day
3
Orchestrator + guardrails + generator
1.5 days
4
Minimal UI wired end-to-end
0.5 day
5
Eval suites + CI gates + observability
1 day


8. Alignment to Problem Statement
Requirement (from problemStatement.md)
Where addressed / iteration scope
Curated corpus
Phase 0 — corpus is exactly the 5 Groww HDFC scheme URLs (locked in sources.yaml)
3–5 schemes, category diversity
Phase 0 — 5 schemes: Mid Cap, Flexi Cap, Focused, ELSS, Large Cap
≤ 3 sentences, exactly 1 citation
Phase 3 (prompt contract + deterministic post-checks)
Footer “Last updated from sources: ”
Phase 3 (post-processor)
Refuse advisory queries with educational link
Phase 3 — link returned is the matching Groww scheme URL (one of the 5)
Welcome msg, 3 examples, visible disclaimer
Phase 4 (UI)
No PII collection/storage
Phase 3 (PII guard) + Phase 5 (log scanner)
Source restriction
Phase 0 — sources.yaml contains only the 5 Groww URLs; Phase 5 CI fails on any other URL in output
Performance queries
Phase 3 — redirect to the relevant Groww scheme URL; no returns computation/comparison
Accuracy + auditability
Phase 5 (eval suites + structured PII-free logs)
Statement / capital-gains / KIM-only facts
Out of scope this iteration — assistant returns “I don’t have a verified answer” + Groww URL


Disclaimer Snippet (used in UI and every refusal):
Facts-only. No investment advice.

## 9. Detailed Strategy Sections

### 9.1 Ingestion Strategy

#### 9.1.1 Source Management
- **Whitelist Enforcement**: Only the 5 specified Groww URLs are permitted in `sources.yaml`
- **Change Detection**: Content hash comparison with volatile field exclusion
- **Robots.txt Compliance**: Automated checking before each fetch cycle
- **ETag Support**: Conditional requests to minimize bandwidth and server load

#### 9.1.2 Content Extraction Pipeline
1. **Primary Extraction**: trafilatura for main content extraction
2. **Fallback Rendering**: Playwright headless browser for JavaScript-heavy pages
3. **Targeted Parsing**: BeautifulSoup for specific data tables and structured content
4. **Quality Assurance**: Must-have anchor validation per scheme

#### 9.1.3 Data Cleaning & Normalization
- **Boilerplate Removal**: Standard disclaimers, promotional content, navigation elements
- **Unicode Normalization**: NFKC form for consistent tokenization
- **Currency Standardization**: Rs., INR, ₹ → ₹
- **Volatile Field Handling**: NAV, AUM, dates excluded from stable content hash
- **PII Redaction**: Phone numbers, emails, addresses automatically detected and removed

#### 9.1.4 Refresh Scheduling
- **GitHub Actions**: Nightly cron jobs with manual dispatch capability
- **Incremental Updates**: Only re-process content with changed stable hash
- **Drift Detection**: Alert on significant content changes across multiple URLs
- **Atomic Updates**: Staging directory with atomic swap to prevent partial states

### 9.2 Chunking Strategy

#### 9.2.1 Section-Aware Chunking
- **Primary Rule**: One section = one chunk (no cross-section chunks)
- **Section Boundaries**: Strict adherence to HTML headings and semantic structure
- **Content Preservation**: Never split mid-sentence or mid-numeric-fact
- **Atomic Units**: Table rows and list items kept together

#### 9.2.2 Size Management
- **Soft Cap**: 250 tokens per chunk
- **Hard Cap**: 400 tokens per chunk (rare, only for long sections)
- **Overlap**: 30 tokens for long sections requiring splits
- **Minimum Size**: 5 tokens (smaller chunks discarded)

#### 9.2.3 Metadata Enrichment
- **Section Source**: HTML section vs meta description tracking
- **Scheme Context**: Scheme name and category for filtering
- **Content Hashes**: Both volatile and stable hash versions
- **Provenance**: Complete URL and timestamp tracking

#### 9.2.4 Expected Output
- **Volume**: ~7 chunks per scheme → ~35 total chunks
- **Sections**: Fund Details, Minimum Investments, Fund Manager, Fund House, Exit Load and Tax, About, Riskometer
- **Distribution**: Most chunks < 100 tokens, only About section ~200 tokens

### 9.3 Embedding Strategy

#### 9.3.1 Model Selection
- **Primary**: bge-small-en via sentence-transformers (384 dimensions)
- **Alternative**: text-embedding-3-small via OpenAI API (configurable)
- **Version Control**: Model version stored alongside embeddings
- **Compatibility Checks**: Reject mismatched model versions during loading

#### 9.3.2 Text Preparation
- **Scheme Context**: `f"{scheme_name}\n\n{text}"` for disambiguation
- **Transient Prepending**: Scheme name added only during embedding, not stored
- **Tokenization**: Consistent with retrieval tokenization
- **Normalization**: Same cleaning pipeline as chunk text

#### 9.3.3 Storage & Management
- **Vector Database**: ChromaDB for persistent storage and retrieval
- **Metadata Storage**: Chunk metadata stored alongside vectors
- **Batch Processing**: Efficient batch embedding generation
- **Quality Assurance**: Dimension validation and similarity checks

#### 9.3.4 Performance Optimization
- **Caching**: Embedding results cached to avoid recomputation
- **Batching**: Optimal batch sizes for API efficiency
- **Memory Management**: Streaming processing for large corpora
- **Index Optimization**: ChromaDB index tuning for fast retrieval

### 9.4 Retrieval Strategy

#### 9.4.1 Hybrid Approach
- **Dense Retrieval**: Semantic similarity using embeddings
- **Sparse Retrieval**: Exact keyword matching using BM25
- **Reciprocal Rank Fusion**: Weighted combination of both approaches
- **Dynamic Weighting**: Numeric-heavy queries favor sparse retrieval

#### 9.4.2 Query Processing Pipeline
1. **Normalization**: NFKC, lowercase, whitespace collapse
2. **Token Expansion**: MF-specific acronyms (ELSS, SIP, NAV, AUM)
3. **Scheme Resolution**: NER-lite for scheme name detection
4. **Intent Classification**: Factual vs advisory vs comparison
5. **Filter Application**: Scheme-based and doc_type filtering

#### 9.4.3 Ranking & Reranking
- **Initial Retrieval**: Top-20 candidates from each approach
- **Fusion**: Weighted Reciprocal Rank Fusion for combined ranking
- **Reranking**: Cross-encoder (BAAI/bge-reranker-base) for top-3 selection
- **Confidence Scoring**: Margin-based confidence calculation

#### 9.4.4 Optimization Techniques
- **Scheme Filtering**: Pre-filter by resolved scheme when possible
- **Section Boosting**: Score boost for section-matching chunks
- **Query Adaptation**: Different strategies for numeric vs semantic queries
- **Result Diversity**: Ensure coverage across relevant sections

### 9.5 Hallucination Prevention

#### 9.5.1 Source Grounding
- **Single Source Policy**: Every answer cites exactly one URL from whitelist
- **Chunk-Based Generation**: Answers built only from retrieved chunks
- **Verbatim Extraction**: Numeric values must appear exactly in source
- **URL Validation**: Post-processor validates all URLs against whitelist

#### 9.5.2 Generation Constraints
- **Length Limits**: Maximum 3 sentences for factual answers
- **Banned Tokens**: Prohibited advisory language automatically filtered
- **Template Fallbacks**: Safe templates when generation fails
- **Extractive Priority**: Default to extractive synthesis over generative

#### 9.5.3 Validation Layers
- **Pre-Generation**: Input validation and intent classification
- **During Generation**: Real-time monitoring for policy violations
- **Post-Generation**: Comprehensive validation before response
- **Quality Checks**: Answer relevance and source verification

#### 9.5.4 Error Handling
- **Graceful Degradation**: Fallback to safer responses on errors
- **Retry Logic**: Multiple attempts with different strategies
- **User Communication**: Clear error messages and next steps
- **Logging**: Comprehensive error tracking for improvement

### 9.6 Unknown-Answer Handling

#### 9.6.1 Detection Mechanisms
- **Confidence Thresholds**: Minimum confidence scores for answers
- **Empty Retrieval**: No relevant chunks found above threshold
- **Content Gaps**: Missing information for specific query types
- **Source Limitations**: Information not present in allowed sources

#### 9.6.2 Response Strategies
- **Standard Refusal**: "I don't have a verified answer for that."
- **Scheme Guidance**: Direct users to relevant scheme pages
- **Educational Links**: Provide learning resources when appropriate
- **Clarification Requests**: Ask for more specific information

#### 9.6.3 User Experience
- **Helpful Alternatives**: Suggest related topics that can be answered
- **Clear Communication**: Explain why information isn't available
- **Resource Direction**: Point to official sources for additional research
- **Feedback Loop**: Collect user needs for future corpus expansion

#### 9.6.4 Continuous Improvement
- **Gap Analysis**: Track common unanswered questions
- **Source Evaluation**: Consider adding new sources for gaps
- **Query Analysis**: Understand user intent patterns
- **System Tuning**: Adjust confidence thresholds based on performance

### 9.7 Privacy Handling

#### 9.7.1 PII Detection & Prevention
- **Input Scanning**: Real-time PII detection in user queries
- **Pattern Matching**: Regex patterns for PAN, Aadhaar, email, phone
- **Redaction Policies**: Automatic redaction of detected PII
- **Rejection Strategy**: Block queries containing sensitive information

#### 9.7.2 Data Protection
- **No Storage**: PII never stored in logs or databases
- **Hashed Analytics**: Query hashing for usage analytics
- **Secure Transmission**: HTTPS for all API communications
- **Memory Management**: Immediate clearing of sensitive data

#### 9.7.3 Compliance & Governance
- **Privacy by Design**: Privacy considerations in all system components
- **Regular Audits**: Automated scanning for PII leaks
- **Policy Enforcement**: Strict adherence to privacy policies
- **User Trust**: Transparent privacy practices and disclosures

#### 9.7.4 Monitoring & Alerting
- **PII Detection**: Real-time alerts for potential PII in logs
- **Compliance Checks**: Automated validation of privacy rules
- **Incident Response**: Quick response to privacy incidents
- **Continuous Monitoring**: Ongoing privacy compliance verification

### 9.8 API/Backend Architecture

#### 9.8.1 Service Design
- **FastAPI Backend**: Modern async web framework for API endpoints
- **Modular Structure**: Separate modules for ingestion, retrieval, generation
- **Dependency Injection**: Clean separation of concerns
- **Configuration Management**: Environment-based configuration

#### 9.8.2 API Endpoints
- **POST /ask**: Main question-answering endpoint
- **GET /meta**: System metadata and status information
- **GET /health**: Health check for monitoring systems
- **GET /metrics**: Performance and usage metrics

#### 9.8.3 Data Flow Architecture
```
User Query → FastAPI → PII Guard → Intent Classifier → 
Retrieval Pipeline → Generation → Post-Processor → Response
```

#### 9.8.4 Performance & Scalability
- **Async Processing**: Non-blocking request handling
- **Connection Pooling**: Efficient database connections
- **Caching Layers**: Redis for frequent queries and results
- **Rate Limiting**: Protection against abuse and overload

#### 9.8.5 Error Handling & Resilience
- **Circuit Breakers**: Prevent cascade failures
- **Retry Logic**: Exponential backoff for transient failures
- **Graceful Degradation**: Reduced functionality during issues
- **Comprehensive Logging**: Structured logging for debugging

### 9.9 Frontend Architecture

#### 9.9.1 Technology Stack
- **React**: Modern UI framework for interactive interface
- **TypeScript**: Type-safe development for better reliability
- **Tailwind CSS**: Utility-first CSS framework for styling
- **Vite**: Fast build tool and development server

#### 9.9.2 Component Structure
- **Header**: Branding, navigation, and disclaimer
- **QueryInput**: User input field with validation
- **AnswerDisplay**: Response rendering with citations
- **Examples**: Suggested questions for user guidance
- **LoadingStates**: Visual feedback during processing

#### 9.9.3 State Management
- **Local State**: Component-level state for UI interactions
- **Query History**: Session-based question/answer tracking
- **Error Handling**: User-friendly error messages and recovery
- **Accessibility**: ARIA labels and keyboard navigation

#### 9.9.4 User Experience Design
- **Responsive Design**: Mobile-friendly interface
- **Loading Indicators**: Clear feedback during processing
- **Error Messages**: Helpful error communication
- **Copy Functionality**: Easy answer copying for users

#### 9.9.5 Performance Optimization
- **Code Splitting**: Lazy loading for better initial load
- **Image Optimization**: Efficient image handling
- **Caching Strategy**: Browser caching for static assets
- **Bundle Analysis**: Regular bundle size optimization

### 9.10 Deployment Approach

#### 9.10.1 Architecture Overview
- **Backend-First**: Deploy and test backend independently
- **Frontend Independence**: Separate frontend deployment
- **Database Separation**: Independent database deployment
- **Monitoring Integration**: Comprehensive observability

#### 9.10.2 Backend Deployment
- **Containerization**: Docker containers for consistent deployment
- **Orchestration**: Kubernetes for container management
- **Environment Management**: Separate dev, staging, production environments
- **Health Checks**: Automated health monitoring and alerts

#### 9.10.3 Frontend Deployment
- **Static Hosting**: CDN-based static asset hosting
- **CI/CD Pipeline**: Automated testing and deployment
- **Environment Configuration**: Environment-specific API endpoints
- **Performance Monitoring**: Real user monitoring (RUM)

#### 9.10.4 Database Deployment
- **ChromaDB**: Vector database for semantic search
- **Backup Strategy**: Regular database backups and recovery
- **Scaling Strategy**: Horizontal scaling for high availability
- **Security**: Network isolation and access controls

#### 9.10.5 Infrastructure Management
- **Infrastructure as Code**: Terraform for reproducible infrastructure
- **Monitoring Stack**: Prometheus, Grafana for system monitoring
- **Log Aggregation**: Centralized logging with ELK stack
- **Security Scanning**: Automated vulnerability scanning

#### 9.10.6 CI/CD Pipeline
- **GitHub Actions**: Automated testing and deployment
- **Multi-Stage Pipeline**: Build, test, deploy stages
- **Rollback Strategy**: Automated rollback on deployment failures
- **Environment Promotion**: Progressive deployment through environments

#### 9.10.7 Operational Considerations
- **Monitoring**: Real-time system health and performance monitoring
- **Alerting**: Proactive alerting for system issues
- **Disaster Recovery**: Backup and recovery procedures
- **Maintenance**: Regular system updates and maintenance windows
