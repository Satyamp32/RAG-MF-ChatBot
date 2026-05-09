# Edge Cases Analysis - Mutual Fund FAQ Assistant

## Overview
This document catalogs all identified edge cases across the system lifecycle, categorized by phase and component. Each edge case includes detection mechanisms, mitigation strategies, and fallback behaviors.

## Phase 1 - Ingestion Edge Cases

### EC-1.1: Robots.txt Disallowed
**Description**: Target URLs become disallowed in robots.txt after initial ingestion.
**Detection**: Check robots.txt before each scheduled fetch; parse Disallow directives.
**Mitigation**: Abort ingestion run, raise governance alert, retry next scheduled run.
**Fallback**: Continue serving from last known good index.

### EC-1.2: HTTP 429 Rate Limiting
**Description**: Groww implements rate limiting during bulk fetching.
**Detection**: HTTP 429 response with Retry-After header.
**Mitigation**: Exponential backoff with jitter, respect Retry-After header.
**Fallback**: Skip current URL, continue with others, alert on completion.

### EC-1.3: ETag/Cache Validation Failure
**Description**: ETag validation fails but content hasn't changed.
**Detection**: 304 response but content hash differs from stored version.
**Mitigation**: Force refetch, log inconsistency, update content hash.
**Fallback**: Use newer content, flag for manual review.

### EC-1.4: JavaScript-Rendered Content
**Description**: Critical content only loads after JavaScript execution.
**Detection**: Extracted text length < threshold OR missing must-have anchors.
**Mitigation**: Auto-fallback to Playwright headless browser with desktop viewport.
**Fallback**: Mark extraction_health=degraded, continue with partial content.

### EC-1.5: Dynamic Content Loading
**Description**: Content loads via AJAX/XHR after initial page load.
**Detection**: Missing sections that should be present based on page structure.
**Mitigation**: Wait for network idle, auto-expand accordions, retry extraction.
**Fallback**: Extract available static content, flag missing dynamic sections.

### EC-1.6: Volatile Field Changes
**Description**: NAV/AUM values change frequently causing unnecessary re-indexing.
**Detection**: Content hash changes due to date/time or numeric values.
**Mitigation**: Strip volatile fields before computing stable_content_hash.
**Fallback**: Use stable hash for index decisions, volatile fields for display only.

### EC-1.7: Image-Only Information
**Description**: Critical information exists only as images (e.g., riskometer).
**Detection**: Missing text content for expected sections, presence of SVG/img tags.
**Mitigation**: Extract alt text, aria-label, or adjacent captions; no OCR.
**Fallback**: Mark section as not-extracted, continue with other sections.

### EC-1.8: Near-Duplicate Boilerplate
**Description**: Similar text across schemes causes vector clustering issues.
**Detection**: High similarity scores between chunks from different schemes.
**Mitigation**: Transiently prepend scheme_name during embedding, not in stored text.
**Fallback**: Use BM25 for exact matches, vectors for semantic context.

### EC-1.9: Cross-Section Content Bleed
**Description**: Content spans multiple sections causing retrieval ambiguity.
**Detection**: Section boundaries unclear, content length exceeds expected limits.
**Mitigation**: Strict section-based chunking, no cross-section chunks.
**Fallback**: Split at sentence boundaries, preserve section metadata.

### EC-1.10: URL Redirects
**Description**: Whitelisted URLs redirect to new locations.
**Detection**: HTTP 301/302 responses with Location header.
**Mitigation**: Do not auto-follow; raise governance alert for manual review.
**Fallback**: Continue with last known good URL until manually updated.

### EC-1.11: Index Corruption
**Description**: Vector index or BM25 index becomes corrupted during build.
**Detection**: Index load failures, inconsistent chunk counts.
**Mitigation**: Atomic build with staging directory, validation before swap.
**Fallback**: Revert to previous index, rebuild from scratch if needed.

### EC-1.12: PII in Source Content
**Description**: Source pages contain phone numbers, emails, or other PII.
**Detection**: Regex patterns for phone, email, address patterns in extracted text.
**Mitigation**: Redact PII during cleaning phase, log redaction count.
**Fallback**: Skip chunks with excessive PII, flag for manual review.

## Phase 2 - Retrieval Edge Cases

### EC-2.1: Ambiguous Scheme Names
**Description**: User query mentions partial or ambiguous scheme names.
**Detection**: Multiple scheme matches with similar confidence scores.
**Mitigation**: Return clarifying question asking for specific scheme name.
**Fallback**: Search across all schemes, return results with scheme disambiguation.

### EC-2.2: Mixed Intent Queries
**Description**: Query contains both factual and advisory components.
**Detection**: Presence of advisory keywords alongside factual terms.
**Mitigation**: Classify as advisory, return refusal with educational link.
**Fallback**: Extract factual component if clearly separable, answer that part.

### EC-2.3: Numeric Precision Issues
**Description**: Query asks for exact numbers but retrieval finds approximate values.
**Detection**: Mismatch between queried numeric format and retrieved format.
**Mitigation**: Prefer exact matches via BM25 for numeric-heavy queries.
**Fallback**: Return "I don't have exact information" with relevant scheme link.

### EC-2.4: Cross-Scheme Comparisons
**Description**: User asks to compare features across different schemes.
**Detection**: Multiple scheme names in query with comparison keywords.
**Mitigation**: Classify as comparison intent, return refusal with educational link.
**Fallback**: Provide individual scheme facts if requested separately.

### EC-2.5: Wrong Section Retrieval
**Description**: Retrieved chunk comes from wrong section for the query.
**Detection**: Query keywords don't match chunk section metadata.
**Mitigation**: Boost scores for section-matching chunks during reranking.
**Fallback**: Return "I don't have verified information" with relevant scheme link.

### EC-2.6: Empty Retrieval Results
**Description**: No chunks meet minimum confidence threshold.
**Detection**: All retrieval scores below confidence threshold τ.
**Mitigation**: Return "I don't have a verified answer" without URL.
**Fallback**: Suggest checking specific scheme page manually.

### EC-2.7: Tokenization Mismatches
**Description**: Query tokens don't match chunk tokens due to formatting differences.
**Detection**: Low BM25 scores despite semantic similarity.
**Mitigation**: Aggressive normalization, acronym expansion, synonym mapping.
**Fallback**: Rely more heavily on vector similarity.

## Phase 3 - Generation Edge Cases

### EC-3.1: Groq API Unavailable
**Description**: Groq API returns errors or timeouts during generation.
**Detection**: API exceptions, timeout errors, rate limiting.
**Mitigation**: Automatic fallback to extractive synthesis.
**Fallback**: Return template-based response with source link.

### EC-3.2: Hallucinated Citations
**Description**: LLM generates URLs not present in the retrieved chunks.
**Detection**: Post-processor checks URLs against whitelist.
**Mitigation**: Reject response, fall back to extractive answer.
**Fallback**: Use safe template with correct source URL.

### EC-3.3: Banned Token Generation
**Description**: LLM generates advisory language despite constraints.
**Detection**: Regex scan for banned tokens ("recommend", "should invest", etc.).
**Mitigation**: Reject response, fall back to extractive answer.
**Fallback**: Use refusal template with educational link.

### EC-3.4: Length Violations
**Description**: Generated response exceeds 3-sentence limit.
**Detection**: Sentence count check in post-processor.
**Mitigation**: Truncate to first 3 sentences, check completeness.
**Fallback**: Use extractive synthesis with length control.

### EC-3.5: PII in Generated Response
**Description**: LLM inadvertently includes PII from training data.
**Detection**: PII scan on generated text before returning.
**Mitigation**: Redact PII, regenerate response.
**Fallback**: Use template-based response without LLM.

### EC-3.6: Confidence Score Manipulation
**Description**: Retrieval confidence scores are artificially high/low.
**Detection**: Statistical analysis of score distributions.
**Mitigation**: Dynamic threshold adjustment based on score percentiles.
**Fallback**: Use conservative fixed threshold.

## Phase 4 - UI Edge Cases

### EC-4.1: Network Timeouts
**Description**: API requests timeout due to slow responses.
**Detection**: Request timeout errors.
**Mitigation**: Implement client-side timeout with retry logic.
**Fallback**: Show "Service temporarily unavailable" message.

### EC-4.2: Malformed User Input
**Description**: User submits empty or extremely long queries.
**Detection**: Input validation on client and server side.
**Mitigation**: Client-side validation with helpful error messages.
**Fallback**: Server-side rejection with appropriate error codes.

### EC-4.3: Browser Compatibility
**Description**: UI breaks on older browsers or different devices.
**Detection**: Browser feature detection, error monitoring.
**Mitigation**: Progressive enhancement, graceful degradation.
**Fallback**: Basic HTML version without advanced features.

### EC-4.4: Accessibility Issues
**Description**: Screen readers or keyboard navigation fail.
**Detection**: Accessibility testing, user feedback.
**Mitigation**: ARIA labels, keyboard navigation, semantic HTML.
**Fallback**: Text-only interface option.

## Phase 5 - Operations Edge Cases

### EC-5.1: Source URL Changes
**Description**: Groww changes URL structure without redirects.
**Detection**: 404 errors on whitelisted URLs.
**Mitigation**: Alert operators, manual URL update in sources.yaml.
**Fallback**: Continue serving from last known good index.

### EC-5.2: Content Drift Detection
**Description**: Source content changes significantly between updates.
**Detection**: Content hash differences exceeding threshold.
**Mitigation**: Alert operators, freeze index if multiple URLs drift.
**Fallback**: Use previous index until manual review.

### EC-5.3: CI Pipeline Failures
**Description**: Automated tests fail due to external dependencies.
**Detection**: Test failures in GitHub Actions.
**Mitigation**: Retry with exponential backoff, isolate flaky tests.
**Fallback**: Manual intervention required.

### EC-5.4: Resource Exhaustion
**Description**: Memory or CPU limits exceeded during processing.
**Detection**: System monitoring, OOM errors.
**Mitigation**: Resource limits, batch processing, graceful degradation.
**Fallback**: Skip problematic URLs, continue with others.

### EC-5.5: Log PII Leaks
**Description**: PII accidentally logged in structured logs.
**Detection**: Log scanning for PII patterns.
**Mitigation**: Hash queries before logging, redaction filters.
**Fallback**: Disable logging until fixed.

### EC-5.6: Evaluation Suite Drift
**Description**: Gold answers become outdated as source content changes.
**Detection**: Evaluation failures due to changed facts.
**Mitigation**: Update gold answers with new source content.
**Fallback**: Temporarily disable failing tests.

### EC-5.7: Scheduled Job Failures
**Description**: GitHub Actions workflow fails due to service issues.
**Detection**: Workflow run failures, timeout errors.
**Mitigation**: Retry logic, manual workflow_dispatch trigger.
**Fallback**: Manual execution until automation restored.

### EC-5.8: Index Version Mismatch
**Description**: Embedding model version doesn't match index version.
**Detection**: Version check during index loading.
**Mitigation**: Reject mismatched versions, force rebuild.
**Fallback**: Continue with previous compatible version.

## Cross-Cutting Edge Cases

### EC-X.1: Concurrent Modifications
**Description**: Multiple processes try to modify index simultaneously.
**Detection**: File locking errors, race conditions.
**Mitigation**: File-based locks, atomic operations, queue serialization.
**Fallback**: Retry with backoff, last-writer-wins with timestamp.

### EC-X.2: Data Consistency
**Description**: Chunks, embeddings, and indexes become out of sync.
**Detection**: Manifest validation, checksum mismatches.
**Mitigation**: Transaction-like operations, rollback capability.
**Fallback**: Rebuild from source data.

### EC-X.3: Security Vulnerabilities
**Description**: Dependencies have known security issues.
**Detection**: Automated security scanning, vulnerability databases.
**Mitigation**: Regular dependency updates, security patches.
**Fallback**: Disable affected features until fixed.

### EC-X.4: Performance Degradation
**Description**: System response times increase over time.
**Detection**: Performance monitoring, latency tracking.
**Mitigation**: Query optimization, caching, resource scaling.
**Fallback**: Simplified responses, reduced functionality.

## Edge Case Mitigation Strategies

### Detection Mechanisms
1. **Health Checks**: Regular validation of all system components
2. **Monitoring**: Real-time alerts for anomalies and failures
3. **Testing**: Comprehensive test suites covering edge cases
4. **Logging**: Structured logging with PII protection
5. **Validation**: Input/output validation at all boundaries

### Response Strategies
1. **Graceful Degradation**: Continue operation with reduced functionality
2. **Fail-Safe Defaults**: Conservative behavior when uncertain
3. **User Communication**: Clear error messages and next steps
4. **Automated Recovery**: Self-healing mechanisms where possible
5. **Manual Intervention**: Clear escalation paths for critical issues

### Prevention Measures
1. **Defensive Programming**: Assume failures can occur
2. **Rate Limiting**: Protect against abuse and overload
3. **Circuit Breakers**: Prevent cascade failures
4. **Idempotent Operations**: Safe retry mechanisms
5. **Comprehensive Testing**: Cover edge cases in automated tests

## Monitoring and Alerting

### Key Metrics
- Ingestion success/failure rates
- Retrieval confidence distributions
- Response generation success rates
- UI error rates and user feedback
- System performance and resource usage

### Alert Thresholds
- >5% ingestion failure rate
- >10% low-confidence retrievals
- >1% generation failures
- Any PII detection in logs
- >2x response time degradation

### Escalation Procedures
1. **Level 1**: Automated recovery attempts
2. **Level 2**: Alert on-call engineer
3. **Level 3**: Manual intervention required
4. **Level 4**: Service outage notification

This edge case analysis ensures the system remains robust, compliant, and user-friendly even when encountering unexpected scenarios or failures.
