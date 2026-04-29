from fastapi import APIRouter, Depends, Request

from app.config.settings import Settings, get_settings
from app.models.request_models import AuditTransactionRequest
from app.models.response_models import AuditHealthResponse, AuditResponse, ModelsResponse
from app.services.llm_engine import OllamaLLMEngine

router = APIRouter(tags=["audit"])


def get_engine(settings: Settings = Depends(get_settings)) -> OllamaLLMEngine:
    return OllamaLLMEngine(settings)


@router.get("/health", response_model=AuditHealthResponse, tags=["system"])
async def health_check(
    request: Request,
    engine: OllamaLLMEngine = Depends(get_engine),
    settings: Settings = Depends(get_settings),
) -> AuditHealthResponse:
    ollama_status = await engine.health_check()
    return AuditHealthResponse(
        service=settings.service_name,
        status="ok",
        default_model=settings.ollama_model,
        ollama=ollama_status,
        request_id=getattr(request.state, "request_id", ""),
    )


@router.get("/models", response_model=ModelsResponse, tags=["system"])
async def list_models(
    request: Request,
    engine: OllamaLLMEngine = Depends(get_engine),
    settings: Settings = Depends(get_settings),
) -> ModelsResponse:
    models = await engine.list_models()
    return ModelsResponse(
        default_model=settings.ollama_model,
        configured_base_url=settings.ollama_base_url,
        installed_models=models,
        request_id=getattr(request.state, "request_id", ""),
    )


@router.post("/audit/transaction", response_model=AuditResponse)
async def audit_transaction(
    payload: AuditTransactionRequest,
    request: Request,
    engine: OllamaLLMEngine = Depends(get_engine),
) -> AuditResponse:
    request_id = getattr(request.state, "request_id", "")
    return await engine.audit_transaction(payload.transaction, request_id=request_id)
