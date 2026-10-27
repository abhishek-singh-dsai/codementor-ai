"""FastAPI backend for CodeMentor AI.

Start with: python -m uvicorn main:app --reload
Open the generated API docs at http://127.0.0.1:8000/docs.
"""

from typing import Annotated, Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from ai_engine import (
    AIProviderError,
    ConfigurationError,
    configured_model,
    debug_code,
    explain_code,
    generate_code,
)

Language = Literal["Python", "JavaScript", "Java", "C++", "Ruby", "Go"]
Level = Literal["Beginner", "Intermediate", "Advanced"]
Topic = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=1000)]
SourceCode = Annotated[str, StringConstraints(min_length=3, max_length=15000)]

app = FastAPI(
    title="CodeMentor AI API",
    version="1.0.0",
    description="Explain coding concepts, review supplied code, and generate learning examples.",
)


class TeachingRequest(BaseModel):
    """Input schema shared by explanation and code generation."""

    model_config = ConfigDict(extra="forbid")
    language: Language
    topic: Topic
    level: Level


class DebugRequest(BaseModel):
    """Review actual submitted code, with optional problem context."""

    model_config = ConfigDict(extra="forbid")
    language: Language
    code: SourceCode
    context: str = Field(default="", max_length=1000)

    @field_validator("code")
    @classmethod
    def source_code_not_blank(cls, code: str) -> str:
        if not code.strip():
            raise ValueError("Code must not be blank.")
        return code  # Preserve indentation, which matters in languages like Python.


class AIResponse(BaseModel):
    response: str


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(_request: Request, _exc: ConfigurationError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "AI provider is not configured. Check the server environment."},
    )


@app.exception_handler(AIProviderError)
async def provider_error_handler(_request: Request, _exc: AIProviderError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"detail": "AI provider request failed. Please try again later."},
    )


@app.get("/", tags=["System"])
def index() -> dict[str, str]:
    return {"service": "CodeMentor AI", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    # Checks only that the local application is running, not the upstream provider.
    return {"status": "ok", "model": configured_model()}


@app.post("/explain", response_model=AIResponse, tags=["AI"])
def explain(data: TeachingRequest) -> AIResponse:
    return AIResponse(response=explain_code(data.language, data.topic, data.level))


@app.post("/debug", response_model=AIResponse, tags=["AI"])
def debug(data: DebugRequest) -> AIResponse:
    return AIResponse(response=debug_code(data.language, data.code, data.context))


@app.post("/generate", response_model=AIResponse, tags=["AI"])
def generate(data: TeachingRequest) -> AIResponse:
    return AIResponse(response=generate_code(data.language, data.topic, data.level))
