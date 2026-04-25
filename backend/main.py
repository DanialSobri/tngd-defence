import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

# When Nginx serves the app under /api (proxy_pass strips /api), set ROOT_PATH=/api
# so Swagger/ReDoc load OpenAPI from /api/openapi.json instead of /openapi.json.
_root_path = os.getenv("ROOT_PATH", "").strip().rstrip("/")

app = FastAPI(
    title="TNG Shield Risk API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    root_path=_root_path,
)
RULES_PATH = Path(__file__).with_name("rules.txt")


class RiskScoreRequest(BaseModel):
    transaction_id: str | None = None
    transaction: dict[str, Any] = Field(
        default_factory=dict,
        description="Transaction details such as amount, merchant, channel, geo, time.",
    )
    customer_profile: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional customer profile, behavior summary, or KYC metadata.",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional additional context (device, recent activity, etc).",
    )
    use_sc_investor_alert_check: bool = Field(
        default=True,
        description="If true, fetch SC Malaysia InvestorAlert records by merchant name.",
    )


class RiskScoreResponse(BaseModel):
    transaction_id: str | None = None
    risk_score: int
    risk_level: str
    decision_band: str | None = None
    action: str | None = None
    reasons: list[str]
    signal_breakdown: dict[str, int] | None = None
    recommendation: str
    model_raw_text: str


def _get_qwen_config() -> tuple[str, str, str]:
    api_key = os.getenv("QWEN_API_KEY", "")
    base_url = os.getenv(
        "QWEN_BASE_URL",
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )
    model = os.getenv("QWEN_MODEL", "qwen3-vl-plus-2025-12-19")
    return api_key, base_url.rstrip("/"), model


def _build_prompt(payload: RiskScoreRequest) -> str:
    return (
        "You are a fraud/risk scoring assistant for digital wallet transactions.\n"
        "Assess risk and return ONLY valid JSON object with this shape:\n"
        "{"
        '"risk_score": <int 0-100>, '
        '"risk_level": "LOW|MEDIUM|HIGH|CRITICAL", '
        '"reasons": ["..."], '
        '"recommendation": "..."'
        "}\n\n"
        f"Transaction ID: {payload.transaction_id}\n"
        f"Transaction:\n{json.dumps(payload.transaction, ensure_ascii=True, indent=2)}\n\n"
        f"Customer Profile:\n{json.dumps(payload.customer_profile, ensure_ascii=True, indent=2)}\n\n"
        f"Context:\n{json.dumps(payload.context, ensure_ascii=True, indent=2)}"
    )


def _load_rules_text() -> str:
    try:
        return RULES_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _build_system_prompt() -> str:
    rules_text = _load_rules_text()
    base = (
        "You are a precise risk analysis assistant for digital wallet transactions. "
        "Always return strict JSON only."
    )
    if not rules_text:
        return base
    return f"{base}\n\nFollow this policy and output contract exactly:\n{rules_text}"


def _fetch_sc_investor_alerts(merchant_name: str, limit: int = 10) -> list[dict[str, Any]]:
    if not merchant_name.strip():
        return []

    url = "https://investmentcheckerapi.sc.com.my/InvestorAlert"
    params = {
        "_key": merchant_name,
        "_page": 1,
        "_limit": limit,
        "_sort": "",
        "_order": "",
    }
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
    except requests.RequestException:
        return []

    data = response.json()
    return data if isinstance(data, list) else []


def _enrich_context_with_sc_check(payload: RiskScoreRequest) -> RiskScoreRequest:
    if not payload.use_sc_investor_alert_check:
        return payload

    merchant_name = str(payload.transaction.get("merchant_name", "")).strip()
    if not merchant_name:
        return payload

    investor_alert_matches = _fetch_sc_investor_alerts(merchant_name)

    merged_context = dict(payload.context)
    merged_context["sc_investor_alert_query"] = merchant_name
    merged_context["sc_investor_alert_matches"] = investor_alert_matches

    return payload.model_copy(update={"context": merged_context})


def _call_qwen_chat_completion(
    prompt: str, system_prompt: str = "You are a helpful assistant."
) -> str:
    api_key, base_url, model = _get_qwen_config()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Missing QWEN_API_KEY environment variable.",
        )

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to call Qwen chat completion: {exc}",
        ) from exc

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise HTTPException(status_code=502, detail="Qwen response has no choices.")

    message = choices[0].get("message", {})
    content = message.get("content")
    if not content:
        raise HTTPException(status_code=502, detail="Qwen response content is empty.")

    return str(content)


def _safe_parse_risk_json(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    raise HTTPException(
        status_code=502,
        detail="Unable to parse model output as JSON risk response.",
    )


def _normalize_risk_result(
    transaction_id: str | None, result: dict[str, Any], model_raw_text: str
) -> RiskScoreResponse:
    risk_score = int(result.get("risk_score", result.get("trust_score", 50)))
    risk_score = max(0, min(100, risk_score))
    risk_level = str(result.get("risk_level", "MEDIUM")).upper()
    decision_band = (
        str(result.get("decision_band")).upper() if result.get("decision_band") is not None else None
    )
    action = str(result.get("action")).upper() if result.get("action") is not None else None
    reasons_raw = result.get("reasons", [])
    reasons = [str(item) for item in reasons_raw] if isinstance(reasons_raw, list) else []
    signal_breakdown_raw = result.get("signal_breakdown")
    signal_breakdown: dict[str, int] | None = None
    if isinstance(signal_breakdown_raw, dict):
        signal_breakdown = {}
        for key, value in signal_breakdown_raw.items():
            try:
                signal_breakdown[str(key)] = int(value)
            except (TypeError, ValueError):
                continue
    recommendation = str(result.get("recommendation", "Review transaction details."))

    return RiskScoreResponse(
        transaction_id=transaction_id,
        risk_score=risk_score,
        risk_level=risk_level,
        decision_band=decision_band,
        action=action,
        reasons=reasons,
        signal_breakdown=signal_breakdown,
        recommendation=recommendation,
        model_raw_text=model_raw_text,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run-risk-score", response_model=RiskScoreResponse)
def run_risk_score(payload: RiskScoreRequest) -> RiskScoreResponse:
    enriched_payload = _enrich_context_with_sc_check(payload)
    prompt = _build_prompt(enriched_payload)
    model_raw_text = _call_qwen_chat_completion(prompt, system_prompt=_build_system_prompt())
    parsed = _safe_parse_risk_json(model_raw_text)
    return _normalize_risk_result(enriched_payload.transaction_id, parsed, model_raw_text)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        root_path=_root_path,
    )
