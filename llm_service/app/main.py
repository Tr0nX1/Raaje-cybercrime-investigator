from fastapi import FastAPI, Request

from app.config.settings import generate_request_id, get_settings
from app.routes.audit import router as audit_router

settings = get_settings()

app = FastAPI(
    title="Local LLM Auditor Service",
    version="1.0.0",
    description=(
        "Local-first FastAPI microservice for transaction correction using Ollama. "
        "Run with `uvicorn app.main:app --reload` from the llm_service directory."
    ),
)

app.include_router(audit_router)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request.state.request_id = generate_request_id()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {
        "service": settings.service_name,
        "message": "LLM auditor service is running.",
    }
