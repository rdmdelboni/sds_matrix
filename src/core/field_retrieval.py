"""Per-field web retrieval queries for chemical SDS enrichment.

This module builds specialized queries per field and uses the configured
online search client (e.g. SearXNGClient) to fetch snippets. It stores
intermediate results directly in the database prior to LLM refinement.

Design goals:
  - One query list per field (synonym / multilingual variants)
  - Early high-confidence fills reduce LLM token usage
  - Distinguish retrieval-origin context for provenance
  - Cache results to avoid redundant searches
"""
from __future__ import annotations

import random
import time
from collections.abc import Iterable
from dataclasses import dataclass

from ..database.duckdb_manager import DuckDBManager
from ..utils.config import (
    CONFIDENCE_SUFFICIENCY_THRESHOLD,
    CONFIDENCE_THRESHOLD_LOW,
    CRAWL_TEXT_MAX_CHARS,
    FIELD_SEARCH_BACKOFF_BASE,
    FIELD_SEARCH_MAX_ATTEMPTS,
    MAX_CRAWL_PAGES_PER_FIELD,
)
from ..utils.logger import logger
from .field_cache import get_field_cache
from .searxng_client import SearXNGClient  # Primary provider
from .validator import validate_field


@dataclass(slots=True)
class RetrievalResult:
    field_name: str
    value: str
    confidence: float
    source: str

class FieldQueryBuilder:
    """Generate multiple query candidates for a field.

    Identifiers may include product name, CAS number, UN number.
    """

    @staticmethod
    def build(
        field_name: str,
        *,
        product: str | None,
        cas: str | None,
        un: str | None,
    ) -> list[str]:
        base_terms: list[str] = []
        if product:
            base_terms.append(product)
        if cas:
            base_terms.append(f"CAS {cas}")
        if un:
            base_terms.append(f"UN {un}")
        identifiers = " ".join(t for t in base_terms if t).strip()

        # Field-specific expansions
        if field_name == "numero_cas":
            extras = [
                "CAS number",
                "chemical abstract service",
                "CAS registry",
            ]
        elif field_name == "numero_onu":
            extras = ["UN number", "UN ID", "numero ONU"]
        elif field_name == "classificacao_onu":
            extras = [
                "UN hazard class",
                "classe ONU",
                "hazard classification",
            ]
        elif field_name == "grupo_embalagem":
            extras = [
                "packing group",
                "grupo de embalagem",
                "UN packing group",
            ]
        elif field_name == "incompatibilidades":
            extras = [
                "incompatibilities",
                "storage incompatibilities",
                "incompatible materials",
            ]
        elif field_name == "fabricante":
            extras = ["manufacturer", "fabricante", "supplier"]
        elif field_name == "nome_produto":
            extras = ["product name", "nome do produto", "trade name"]
        else:
            extras = [field_name]

        queries: list[str] = []
        for extra in extras:
            if identifiers:
                queries.append(f"{identifiers} {extra} safety data sheet")
                queries.append(f"{identifiers} {extra} SDS")
            else:
                queries.append(f"{extra} safety data sheet")
        # Deduplicate while preserving order
        seen = set()
        deduped: list[str] = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                deduped.append(q)
        return deduped[:6]  # cap variants

class FieldRetriever:
    """Execute per-field retrieval, store intermediate extractions."""

    def __init__(
        self, db: DuckDBManager, search_client: SearXNGClient
    ) -> None:
        self.db = db
        self.search = search_client
        self.cache = get_field_cache()

    def retrieve_missing_fields(
        self,
        document_id: int,
        missing_fields: Iterable[str],
        known: dict[str, str],
    ) -> dict[str, RetrievalResult]:
        results: dict[str, RetrievalResult] = {}
        product = known.get("nome_produto")
        cas = known.get("numero_cas")
        un = known.get("numero_onu")

        for field in missing_fields:
            # Check cache first
            cached = self.cache.get(
                field_name=field,
                product_name=product,
                cas_number=cas,
                un_number=un,
            )
            if cached and cached.confidence >= CONFIDENCE_THRESHOLD_LOW:
                logger.info(
                    "Using cached value for %s (conf=%.2f, age=%.1fh)",
                    field,
                    cached.confidence,
                    (time.time() - cached.cached_at) / 3600,
                )
                results[field] = RetrievalResult(
                    field_name=field,
                    value=cached.value,
                    confidence=cached.confidence,
                    source=cached.source,
                )
                # Store cached result in DB
                status, message = validate_field(
                    field,
                    {
                        "value": cached.value,
                        "confidence": cached.confidence,
                    },
                )
                self.db.store_extraction(
                    document_id=document_id,
                    field_name=field,
                    value=cached.value,
                    confidence=cached.confidence,
                    context=f"cached:{cached.source}",
                    validation_status=status,
                    validation_message=message,
                    source_urls=cached.source_urls,
                )
                continue

            try:
                queries = FieldQueryBuilder.build(
                    field, product=product, cas=cas, un=un
                )
                best_snippet = ""
                best_source = ""
                best_conf = 0.0

                for attempt in range(FIELD_SEARCH_MAX_ATTEMPTS):
                    # Shuffle queries after first attempt to vary ordering
                    if attempt > 0:
                        random.shuffle(queries)
                        logger.debug(
                            "Field %s attempt %d/%d - retrying queries",
                            field,
                            attempt + 1,
                            FIELD_SEARCH_MAX_ATTEMPTS,
                        )

                    for q in queries:
                        try:
                            search_hits = self.search._search_with_retry(
                                q, num_results=2
                            )
                        except Exception as exc:  # noqa: BLE001
                            logger.debug(
                                "Search failed for %s q='%s' (attempt %d): %s",
                                field,
                                q[:60],
                                attempt + 1,
                                exc,
                            )
                            continue
                        for hit in search_hits:
                            snippet = (hit.get("snippet") or "").strip()
                            if not snippet:
                                continue
                            # Simple scoring: length + keyword presence
                            score: float = float(len(snippet))
                            if field in snippet.lower():
                                score *= 1.1
                            if score > best_conf:
                                best_conf = score
                                best_snippet = snippet[:800]
                                best_source = hit.get("url", "")
                        if best_conf > 900:  # early exit if very good
                            break

                    # Optional crawling for richer context if still weak
                    # Only crawl if explicitly enabled (IP ban prevention)
                    from ..utils.config import CRAWL4AI_ENABLED

                    if (
                        best_conf < 400
                        and CRAWL4AI_ENABLED
                        and hasattr(self.search, "_crawl_url")
                        and MAX_CRAWL_PAGES_PER_FIELD > 0
                    ):
                        crawled_count = 0
                        for q in queries:
                            if crawled_count >= MAX_CRAWL_PAGES_PER_FIELD:
                                break
                            try:
                                hits = self.search._search_with_retry(
                                    q, num_results=1
                                )
                            except Exception:  # noqa: BLE001
                                continue
                            if not hits:
                                continue
                            url = hits[0].get("url", "")
                            title = hits[0].get("title", "")
                            if not url:
                                continue
                            try:
                                page_text = self.search._crawl_url(url)
                            except Exception:  # noqa: BLE001
                                page_text = ""
                            if not page_text:
                                continue
                            crawled_count += 1
                            # Persist raw page content
                            self.db.store_crawled_page(
                                url=url,
                                document_id=document_id,
                                field_name=field,
                                title=title or field,
                                content=page_text[:CRAWL_TEXT_MAX_CHARS],
                                status="ok",
                            )
                            # Extract focused snippet around field keyword
                            lowered = page_text.lower()
                            token = field.lower()
                            if token in lowered:
                                idx = lowered.find(token)
                                window = 400
                                start = max(0, idx - window)
                                end = min(len(page_text), idx + window)
                                focused = page_text[start:end].strip()
                                if (
                                    focused
                                    and len(focused) > len(best_snippet)
                                ):
                                    best_snippet = focused[:800]
                                    best_conf = len(focused)
                                    best_source = url

                    # Decide whether to retry field-level
                    sufficient = best_conf >= CONFIDENCE_SUFFICIENCY_THRESHOLD or best_snippet
                    last_attempt = attempt == FIELD_SEARCH_MAX_ATTEMPTS - 1
                    if sufficient or last_attempt:
                        break

                    # Backoff before next attempt (exponential with jitter)
                    backoff = FIELD_SEARCH_BACKOFF_BASE * (2**attempt)
                    jitter = backoff * random.uniform(-0.15, 0.15)
                    sleep_time = max(0.05, backoff + jitter)
                    logger.debug(
                        (
                            "Field %s insufficient (conf=%.1f). Backoff %.2fs"
                        ),
                        field,
                        best_conf,
                        sleep_time,
                    )
                    time.sleep(sleep_time)

                if best_snippet:
                    # Normalize score to 0..1 (rough heuristic)
                    norm_conf = min(0.95, 0.4 + best_conf / 2500)
                    results[field] = RetrievalResult(
                        field_name=field,
                        value=best_snippet,
                        confidence=norm_conf,
                        source=best_source or "search",
                    )
                else:
                    results[field] = RetrievalResult(
                        field_name=field,
                        value="NAO ENCONTRADO",
                        confidence=0.0,
                        source="search",
                    )

                # Persist immediately if above low threshold
                rr = results[field]
                if rr.confidence >= CONFIDENCE_THRESHOLD_LOW:
                    status, message = validate_field(
                        field,
                        {
                            "value": rr.value,
                            "confidence": rr.confidence,
                        },
                    )
                    source_urls = [rr.source] if rr.source else []
                    self.db.store_extraction(
                        document_id=document_id,
                        field_name=field,
                        value=rr.value,
                        confidence=rr.confidence,
                        context=f"retrieval:{rr.source}",
                        validation_status=status,
                        validation_message=message,
                        source_urls=source_urls,
                    )
                    # Cache the result for future use
                    self.cache.put(
                        field_name=field,
                        value=rr.value,
                        confidence=rr.confidence,
                        source=rr.source,
                        source_urls=source_urls,
                        product_name=product,
                        cas_number=cas,
                        un_number=un,
                    )
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Field retrieval error for %s: %s",
                    field,
                    exc,
                )
        return results

__all__ = ["FieldRetriever", "FieldQueryBuilder", "RetrievalResult"]
