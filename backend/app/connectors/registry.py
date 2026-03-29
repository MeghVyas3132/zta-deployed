from __future__ import annotations

from app.connectors.mock_claims import mock_claims_connector
from app.schemas.pipeline import CompiledQueryPlan


class ConnectorRegistry:
    def get(self, plan: CompiledQueryPlan):
        # Both seeded IPEDS data and legacy demos execute against the same trusted claim store.
        if plan.source_type in {"ipeds_claims", "mock_claims"}:
            return mock_claims_connector
        return mock_claims_connector


connector_registry = ConnectorRegistry()
