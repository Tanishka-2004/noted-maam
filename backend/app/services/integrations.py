"""
External Integrations Adapter & Router Services

Implements integration adapters (Mock, Slack, Webhook) and configuration router
mappings verifying capabilities and generating HMAC verification signatures.
"""
import hmac
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import httpx

from app.models.meeting import IntegrationConfig

logger = logging.getLogger(__name__)


class IntegrationAdapter(ABC):
    @abstractmethod
    async def dispatch(self, payload: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Transmits payload data to target workspaces, returning response metadata."""
        pass


class MockIntegrationAdapter(IntegrationAdapter):
    """Simple simulator for logging dispatches."""

    async def dispatch(self, payload: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Mock Integration dispatched: payload={payload}, config={config}")
        return {"status": "dispatched", "provider": "mock"}


class SlackAdapter(IntegrationAdapter):
    """Simulates Slack workspace web API requests."""

    async def dispatch(self, payload: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        channel = config.get("channel", "#general")
        token = config.get("token")
        
        if not token:
            raise ValueError("Slack token is missing from config credentials")

        # Simulate channel posting API request
        logger.info(f"Slack Notification sent to channel {channel}. Token length={len(token)}")
        return {
            "status": "delivered",
            "provider": "slack",
            "channel": channel,
            "simulated_message_id": "slack_msg_102938"
        }


class GenericWebhookAdapter(IntegrationAdapter):
    """Dispatches HTTP POST payloads containing HMAC signatures verifying authenticity."""

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.client = client or httpx.AsyncClient()

    async def dispatch(self, payload: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        url = config.get("url")
        secret = config.get("secret", "default_webhook_secret")

        if not url:
            raise ValueError("Webhook target URL is missing from config credentials")

        body_str = json.dumps(payload, sort_keys=True)
        
        # Calculate HMAC SHA256 Signature header
        signature = hmac.new(
            secret.encode("utf-8"),
            body_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Noted-Signature": signature
        }

        try:
            # Execute actual HTTP POST dispatch request
            response = await self.client.post(url, content=body_str, headers=headers, timeout=5.0)
            
            # Log metrics inside worker
            return {
                "status": "delivered" if response.status_code < 300 else "failed",
                "provider": "webhook",
                "http_status": response.status_code,
                "response_body": response.text[:200]
            }
        except httpx.RequestError as e:
            # Capture network errors as retryable exceptions
            raise e


# ============================================================
# Integration Router Service
# ============================================================

class IntegrationRouterService:
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._adapters: Dict[str, IntegrationAdapter] = {
            "mock": MockIntegrationAdapter(),
            "slack": SlackAdapter(),
            "webhook": GenericWebhookAdapter(client=client)
        }

    async def route_dispatch(self, config: IntegrationConfig, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Resolves target adapter and triggers dispatch execution."""
        provider = config.provider.lower()
        adapter = self._adapters.get(provider)
        
        if not adapter:
            raise ValueError(f"Unsupported integrations provider mapping: {provider}")

        # Execute payload transmission
        return await adapter.dispatch(payload, config.credentials_encrypted)
