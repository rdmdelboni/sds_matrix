"""LLM clients: local OpenAI-compatible server (Ollama/LM Studio) and Gemini online search."""

from __future__ import annotations

import json
from typing import Dict, Optional, cast

import httpx

from openai import OpenAI

from ..utils.config import GEMINI_CONFIG, GROK_CONFIG, LM_STUDIO_CONFIG, TAVILY_CONFIG
from ..utils.logger import logger


DEFAULT_SYSTEM_PROMPT = (
    "Voce e um assistente especialista em ler Fichas de Dados de Seguranca (FDS) de "
    "produtos quimicos. Responda sempre em JSON com os campos "
    '{"value": "...", "confidence": 0.0-1.0, "context": "..."} e nunca invente dados.'
)


class LMStudioClient:
    """Wrapper for sending prompts to the local OpenAI-compatible server (Ollama/LM Studio)."""

    def __init__(self) -> None:
        self.config = LM_STUDIO_CONFIG
        self.client = OpenAI(
            base_url=str(self.config["base_url"]),
            api_key="not-needed",
        )
        self.model = cast(str, self.config["model"])  # type: ignore[assignment]

    def extract_field(
        self,
        *,
        field_name: str,
        prompt_template: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, object]:
        """Send a prompt and parse the JSON result."""
        prompt = prompt_template.strip()
        logger.info("Consulting LLM for %s", field_name)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=float(cast(float, self.config["temperature"])),
                max_tokens=int(cast(int, self.config["max_tokens"])),
                timeout=int(cast(int, self.config["timeout"])),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("LLM call failed for %s: %s", field_name, exc)
            return {"value": "ERRO", "confidence": 0.0, "context": str(exc)}

        raw_content = (response.choices[0].message.content or "").strip()
        logger.debug("LLM response for %s: %s", field_name, raw_content)

        try:
            parsed = json.loads(raw_content)
            if not isinstance(parsed, dict):
                raise ValueError("Resposta nao e um objeto JSON.")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Invalid JSON for %s: %s", field_name, exc)
            parsed = {"value": raw_content, "confidence": 0.4, "context": ""}

        parsed.setdefault("value", "NAO ENCONTRADO")
        parsed.setdefault("confidence", 0.0)
        parsed.setdefault("context", "")
        return parsed

    def test_connection(self) -> bool:
        """Send a simple test message to validate connectivity."""
        try:
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=4,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("LLM connection failed: %s", exc)
            return False

    def search_online_for_missing_fields(
        self,
        *,
        product_name: Optional[str] = None,
        cas_number: Optional[str] = None,
        un_number: Optional[str] = None,
        missing_fields: list[str],
    ) -> Dict[str, Dict[str, object]]:
        """Search online for missing field values using web-enhanced LLM.
        
        Args:
            product_name: Known product name
            cas_number: Known CAS number
            un_number: Known UN number
            missing_fields: List of field names that need values
            
        Returns:
            Dictionary mapping field names to extracted data
        """
        identifiers = []
        if product_name:
            identifiers.append(f"Produto: {product_name}")
        if cas_number:
            identifiers.append(f"CAS: {cas_number}")
        if un_number:
            identifiers.append(f"ONU: {un_number}")
        
        if not identifiers:
            logger.warning("No identifiers provided for online search")
            return {}
        
        identifier_text = ", ".join(identifiers)
        fields_text = ", ".join(missing_fields)
        
        prompt = f"""Preciso encontrar informacoes sobre um produto quimico.
Identifiers conhecidos: {identifier_text}

Por favor, pesquise online e retorne as seguintes informacoes faltantes: {fields_text}

Retorne um JSON com este formato:
{{
    "campo1": {{"value": "valor encontrado", "confidence": 0.0-1.0, "source": "fonte da informacao"}},
    "campo2": {{"value": "valor encontrado", "confidence": 0.0-1.0, "source": "fonte da informacao"}}
}}

Se nao encontrar algum campo, use "NAO ENCONTRADO" como value e confidence 0.0."""

        system_prompt = (
            "Voce e um assistente especializado em buscar informacoes sobre produtos quimicos. "
            "Use suas capacidades de busca online para encontrar dados precisos em bases como "
            "PubChem, ChemSpider, fichas de seguranca oficiais, e sites de fabricantes. "
            "Sempre cite a fonte das informacoes e indique o nivel de confianca."
        )

        logger.info("Searching online for missing fields: %s", missing_fields)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=2000,
                timeout=int(cast(int, self.config["timeout"])),
            )
            
            raw_content = (response.choices[0].message.content or "").strip()
            logger.debug("Online search response: %s", raw_content)
            
            # Parse JSON response
            if raw_content.startswith("```json"):
                raw_content = raw_content.split("```json")[1].split("```")[0].strip()
            elif raw_content.startswith("```"):
                raw_content = raw_content.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(raw_content)
            if not isinstance(parsed, dict):
                raise ValueError("Response is not a JSON object")
            
            # Validate and normalize response
            results = {}
            for field_name in missing_fields:
                if field_name in parsed and isinstance(parsed[field_name], dict):
                    field_data = parsed[field_name]
                    results[field_name] = {
                        "value": field_data.get("value", "NAO ENCONTRADO"),
                        "confidence": float(field_data.get("confidence", 0.0)),
                        "context": field_data.get("source", "Online search"),
                    }
                else:
                    results[field_name] = {
                        "value": "NAO ENCONTRADO",
                        "confidence": 0.0,
                        "context": "Not found in online search",
                    }
            
            logger.info("Online search completed for %d fields", len(results))
            return results
            
        except Exception as exc:  # noqa: BLE001
            logger.error("Online search failed: %s", exc)
            return {
                field: {"value": "ERRO", "confidence": 0.0, "context": str(exc)}
                for field in missing_fields
            }


class GeminiClient:
    """Client for Google's Generative Language API (Gemini) used for online search."""

    def __init__(self) -> None:
        self.api_key = str(GEMINI_CONFIG.get("api_key", ""))
        self.model = str(GEMINI_CONFIG.get("model", "gemini-2.0-flash"))
        self.base_url = str(GEMINI_CONFIG.get("base_url", "https://generativelanguage.googleapis.com"))
        self.timeout = int(cast(int, GEMINI_CONFIG.get("timeout", 60)))

    def _endpoint(self) -> str:
        return f"{self.base_url}/v1beta/models/{self.model}:generateContent"

    def test_connection(self) -> bool:
        """Lightweight call to verify that the API key is present."""
        return bool(self.api_key)

    def _post(self, prompt: str) -> str:
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                    ]
                }
            ]
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(self._endpoint(), params=params, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Gemini request failed: {exc}") from exc

        # Extract text from candidates
        try:
            candidates = data.get("candidates", [])
            first = candidates[0]
            parts = first.get("content", {}).get("parts", [])
            texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
            response_text = "\n".join(t for t in texts if t)
            return response_text.strip()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Unexpected Gemini response schema: {data}") from exc

    def search_online_for_missing_fields(
        self,
        *,
        product_name: Optional[str] = None,
        cas_number: Optional[str] = None,
        un_number: Optional[str] = None,
        missing_fields: list[str],
    ) -> Dict[str, Dict[str, object]]:
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not set; skipping Gemini online search")
            return {field: {"value": "NAO ENCONTRADO", "confidence": 0.0, "context": "Gemini disabled"} for field in missing_fields}

        identifiers = []
        if product_name:
            identifiers.append(f"Produto: {product_name}")
        if cas_number:
            identifiers.append(f"CAS: {cas_number}")
        if un_number:
            identifiers.append(f"ONU: {un_number}")

        if not identifiers:
            logger.warning("No identifiers provided for online search")
            return {}

        identifier_text = ", ".join(identifiers)
        fields_text = ", ".join(missing_fields)

        prompt = f"""Atue como um especialista em Fichas de Dados de Segurança e bases químicas (PubChem, ChemSpider, fabricantes).
Tenho estes identificadores: {identifier_text}
Preciso encontrar os seguintes campos faltantes: {fields_text}

Responda estritamente em JSON com este formato, sem comentários ou texto fora do JSON:
{{
  "campo1": {{"value": "valor", "confidence": 0.0-1.0, "source": "url ou fonte"}},
  "campo2": {{"value": "valor", "confidence": 0.0-1.0, "source": "url ou fonte"}}
}}
Se algum campo nao for encontrado com confianca, use value="NAO ENCONTRADO" e confidence=0.0.
"""

        logger.info("Gemini: searching online for fields: %s", missing_fields)
        try:
            raw_text = self._post(prompt)
            logger.debug("Gemini raw response: %s", raw_text)

            # Extract JSON if fenced
            content = raw_text.strip()
            if content.startswith("```json"):
                content = content.split("```json", 1)[1].split("```", 1)[0].strip()
            elif content.startswith("```"):
                content = content.split("```", 1)[1].split("```", 1)[0].strip()

            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ValueError("Gemini response is not a JSON object")

            results: Dict[str, Dict[str, object]] = {}
            for field_name in missing_fields:
                entry = parsed.get(field_name, {}) if isinstance(parsed.get(field_name, {}), dict) else {}
                results[field_name] = {
                    "value": entry.get("value", "NAO ENCONTRADO"),
                    "confidence": float(entry.get("confidence", 0.0) or 0.0),
                    "context": entry.get("source", "Gemini online search"),
                }

            logger.info("Gemini online search completed for %d fields", len(results))
            return results
        except Exception as exc:  # noqa: BLE001
            logger.error("Gemini online search failed: %s", exc)
            return {field: {"value": "ERRO", "confidence": 0.0, "context": str(exc)} for field in missing_fields}


class GrokClient:
    """Client for xAI's Grok API used for online search."""

    def __init__(self) -> None:
        self.api_key = str(GROK_CONFIG.get("api_key", ""))
        self.model = str(GROK_CONFIG.get("model", "grok-beta"))
        self.base_url = str(GROK_CONFIG.get("base_url", "https://api.x.ai/v1"))
        self.timeout = int(cast(int, GROK_CONFIG.get("timeout", 60)))

    def _endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

    def test_connection(self) -> bool:
        """Lightweight call to verify that the API key is present."""
        return bool(self.api_key)

    def _post(self, prompt: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(self._endpoint(), headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Grok request failed: {exc}") from exc

        # Extract text from response
        try:
            choices = data.get("choices", [])
            first = choices[0]
            message = first.get("message", {})
            response_text = message.get("content", "")
            return response_text.strip()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Unexpected Grok response schema: {data}") from exc

    def search_online_for_missing_fields(
        self,
        *,
        product_name: Optional[str] = None,
        cas_number: Optional[str] = None,
        un_number: Optional[str] = None,
        missing_fields: list[str],
    ) -> Dict[str, Dict[str, object]]:
        if not self.api_key:
            logger.warning("GROK_API_KEY not set; skipping Grok online search")
            return {field: {"value": "NAO ENCONTRADO", "confidence": 0.0, "context": "Grok disabled"} for field in missing_fields}

        identifiers = []
        if product_name:
            identifiers.append(f"Produto: {product_name}")
        if cas_number:
            identifiers.append(f"CAS: {cas_number}")
        if un_number:
            identifiers.append(f"ONU: {un_number}")

        if not identifiers:
            logger.warning("No identifiers provided for online search")
            return {}

        identifier_text = ", ".join(identifiers)
        fields_text = ", ".join(missing_fields)

        prompt = f"""Atue como um especialista em Fichas de Dados de Segurança e bases químicas (PubChem, ChemSpider, fabricantes).
Tenho estes identificadores: {identifier_text}
Preciso encontrar os seguintes campos faltantes: {fields_text}

Responda estritamente em JSON com este formato, sem comentários ou texto fora do JSON:
{{
  "campo1": {{"value": "valor", "confidence": 0.0-1.0, "source": "url ou fonte"}},
  "campo2": {{"value": "valor", "confidence": 0.0-1.0, "source": "url ou fonte"}}
}}
Se algum campo nao for encontrado com confianca, use value="NAO ENCONTRADO" e confidence=0.0.
"""

        logger.info("Grok: searching online for fields: %s", missing_fields)
        try:
            raw_text = self._post(prompt)
            logger.debug("Grok raw response: %s", raw_text)

            # Extract JSON if fenced
            content = raw_text.strip()
            if content.startswith("```json"):
                content = content.split("```json", 1)[1].split("```", 1)[0].strip()
            elif content.startswith("```"):
                content = content.split("```", 1)[1].split("```", 1)[0].strip()

            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ValueError("Grok response is not a JSON object")

            results: Dict[str, Dict[str, object]] = {}
            for field_name in missing_fields:
                entry = parsed.get(field_name, {}) if isinstance(parsed.get(field_name, {}), dict) else {}
                results[field_name] = {
                    "value": entry.get("value", "NAO ENCONTRADO"),
                    "confidence": float(entry.get("confidence", 0.0) or 0.0),
                    "context": entry.get("source", "Grok online search"),
                }

            logger.info("Grok online search completed for %d fields", len(results))
            return results
        except Exception as exc:  # noqa: BLE001
            logger.error("Grok online search failed: %s", exc)
            return {field: {"value": "ERRO", "confidence": 0.0, "context": str(exc)} for field in missing_fields}


class TavilyClient:
    """Client for Tavily AI research API used for online search with local LLM."""

    def __init__(self) -> None:
        self.api_key = str(TAVILY_CONFIG.get("api_key", ""))
        self.base_url = str(TAVILY_CONFIG.get("base_url", "https://api.tavily.com"))
        self.timeout = int(cast(int, TAVILY_CONFIG.get("timeout", 60)))

    def _endpoint(self) -> str:
        return f"{self.base_url}/search"

    def test_connection(self) -> bool:
        """Lightweight call to verify that the API key is present."""
        return bool(self.api_key)

    def _search(self, query: str) -> Dict[str, object]:
        """Execute a search query using Tavily API."""
        headers = {"Content-Type": "application/json"}
        payload = {
            "api_key": self.api_key,
            "query": query,
            "topic": "science",  # Focus on scientific/technical content
            "max_results": 5,
            "search_depth": "advanced",  # Advanced search for better results
            "include_answer": True,
            "include_raw_content": False,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(self._endpoint(), headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
                return cast(Dict[str, object], data)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Tavily search failed: {exc}") from exc

    def search_online_for_missing_fields(
        self,
        *,
        product_name: Optional[str] = None,
        cas_number: Optional[str] = None,
        un_number: Optional[str] = None,
        missing_fields: list[str],
    ) -> Dict[str, Dict[str, object]]:
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not set; skipping Tavily online search")
            return {field: {"value": "NAO ENCONTRADO", "confidence": 0.0, "context": "Tavily disabled"} for field in missing_fields}

        identifiers = []
        if product_name:
            identifiers.append(product_name)
        if cas_number:
            identifiers.append(f"CAS {cas_number}")
        if un_number:
            identifiers.append(f"UN {un_number}")

        if not identifiers:
            logger.warning("No identifiers provided for online search")
            return {}

        identifier_text = " ".join(identifiers)
        results: Dict[str, Dict[str, object]] = {}

        # Search for each missing field
        for field_name in missing_fields:
            logger.info("Tavily: searching for field '%s' with identifiers: %s", field_name, identifier_text)

            try:
                # Build field-specific search query
                field_translations = {
                    "numero_cas": "CAS number",
                    "numero_onu": "UN number",
                    "nome_produto": "product name",
                    "fabricante": "manufacturer",
                    "classificacao_onu": "UN classification hazard",
                    "grupo_embalagem": "packing group",
                    "incompatibilidades": "chemical incompatibilities",
                }
                field_display = field_translations.get(field_name, field_name)
                query = f"{identifier_text} {field_display} chemical product safety data"

                search_result = self._search(query)

                # Extract answer from Tavily if available
                answer = search_result.get("answer", "")
                results_list = search_result.get("results", [])

                if answer:
                    results[field_name] = {
                        "value": answer.strip(),
                        "confidence": 0.8,
                        "context": "Tavily online search",
                    }
                elif results_list and len(results_list) > 0:
                    # Use first search result's content as fallback
                    first_result = results_list[0]
                    content = first_result.get("content", "") or first_result.get("snippet", "")
                    if content:
                        results[field_name] = {
                            "value": content.strip()[:500],  # Limit to 500 chars
                            "confidence": 0.6,
                            "context": f"Tavily: {first_result.get('title', 'Search result')}",
                        }
                    else:
                        results[field_name] = {
                            "value": "NAO ENCONTRADO",
                            "confidence": 0.0,
                            "context": "Tavily search returned no usable content",
                        }
                else:
                    results[field_name] = {
                        "value": "NAO ENCONTRADO",
                        "confidence": 0.0,
                        "context": "Tavily search returned no results",
                    }

                logger.debug("Tavily result for %s: %s", field_name, results[field_name])

            except Exception as exc:  # noqa: BLE001
                logger.error("Tavily search failed for field %s: %s", field_name, exc)
                results[field_name] = {
                    "value": "ERRO",
                    "confidence": 0.0,
                    "context": f"Tavily error: {str(exc)}",
                }

        logger.info("Tavily online search completed for %d fields", len(results))
        return results
