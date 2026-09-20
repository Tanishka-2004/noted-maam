"""
Distributed Tracing Context Manager

Provides request-scoped tracing context variables to satisfy the Telemetry Contract,
enabling trace propagation (Trace ID, Span ID, Parent Span ID) across HTTP gateways,
outbox event records, and asynchronous background worker execution loops.
"""
import uuid
from contextvars import ContextVar
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Request-scoped distributed tracing ContextVars
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
span_id_var: ContextVar[Optional[str]] = ContextVar("span_id", default=None)
parent_span_id_var: ContextVar[Optional[str]] = ContextVar("parent_span_id", default=None)


class TraceContextManager:
    """Encapsulates context-scoped distributed trace identifiers."""

    @staticmethod
    def set_trace_context(trace_id: str, span_id: str, parent_span_id: Optional[str] = None) -> None:
        trace_id_var.set(trace_id)
        span_id_var.set(span_id)
        parent_span_id_var.set(parent_span_id)

    @staticmethod
    def get_trace_id() -> Optional[str]:
        return trace_id_var.get()

    @staticmethod
    def get_span_id() -> Optional[str]:
        return span_id_var.get()

    @staticmethod
    def get_parent_span_id() -> Optional[str]:
        return parent_span_id_var.get()

    @staticmethod
    def get_context_dict() -> dict:
        return {
            "trace_id": trace_id_var.get(),
            "span_id": span_id_var.get(),
            "parent_span_id": parent_span_id_var.get()
        }

    @staticmethod
    def clear_trace_context() -> None:
        trace_id_var.set(None)
        span_id_var.set(None)
        parent_span_id_var.set(None)


class TracingMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware executing telemetry propagation and tracing context injection."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Extract headers from tracing contract if present, otherwise generate new trace
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        parent_span_id = request.headers.get("X-Span-ID") or request.headers.get("X-Parent-Span-ID")
        span_id = str(uuid.uuid4())

        # Bind context scoped vars
        TraceContextManager.set_trace_context(trace_id, span_id, parent_span_id)

        try:
            response = await call_next(request)
            
            # Inject headers back into response for clients
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Span-ID"] = span_id
            if parent_span_id:
                response.headers["X-Parent-Span-ID"] = parent_span_id
                
            return response
        finally:
            # Prevent context leaks
            TraceContextManager.clear_trace_context()
