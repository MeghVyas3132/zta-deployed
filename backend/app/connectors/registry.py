from __future__ import annotations

from app.connectors.mock_claims import mock_claims_connector
from app.schemas.pipeline import CompiledQueryPlan


class ConnectorRegistry:
    def get(self, plan: CompiledQueryPlan):
        # All queries execute against the trusted claim store seeded from IPEDS CSV data.
        if plan.source_type in {"ipeds_claims", "mock_claims"}:
            return mock_claims_connector
        return mock_claims_connector


connector_registry = ConnectorRegistry()
