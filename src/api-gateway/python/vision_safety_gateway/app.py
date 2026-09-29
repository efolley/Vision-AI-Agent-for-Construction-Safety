from __future__ import annotations

import base64

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
from vision_safety_ingestion import IngestionError, IngestionService

from vision_safety_core.gateway import GatewayError, IdempotencyService, JwtVerifier, RateLimiter


class Submission(BaseModel): filename: str; content_type: str; content_base64: str
def create_app(*, verifier: JwtVerifier, limiter: RateLimiter, idempotency: IdempotencyService, ingestion: IngestionService) -> FastAPI:
    app=FastAPI(title="Vision Safety API Gateway")
    @app.post("/v1/tenants/{tenant_id}/inspections")
    def submit(tenant_id: str, body: Submission, request: Request, authorization: str=Header(default=""), idempotency_key: str=Header(default="")) -> dict[str, str]:
        try: principal=verifier.verify(authorization.removeprefix("Bearer "))
        except GatewayError as error: raise HTTPException(401, str(error)) from error
        if principal.tenant_id != tenant_id: raise HTTPException(403, "Tenant access denied")
        if not limiter.allow(tenant_id): raise HTTPException(429, "Rate limit exceeded")
        if not idempotency_key or not idempotency.claim(tenant_id, idempotency_key): raise HTTPException(409, "Duplicate or missing idempotency key")
        try: content=base64.b64decode(body.content_base64, validate=True); inspection_id=ingestion.create_inspection(tenant_id=tenant_id, trace_id=request.headers.get("x-trace-id", "generated-trace"), filename=body.filename, content_type=body.content_type, content=content)
        except (ValueError, IngestionError) as error: raise HTTPException(400, str(error)) from error
        return {"inspection_id": inspection_id, "status": "queued"}
    return app
