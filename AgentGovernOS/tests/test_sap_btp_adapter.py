"""
Tests for — SAP BTP Adapter

Covers:
- SAP CloudEvent model validation
- Event type mapping (7 event types)
- Verdict-to-SAP-workflow translation
- Adapter endpoints (health, root, supported events)
- Batch evaluation
- Mock end-to-end flow
"""

import pytest
import uuid
import importlib.util
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import httpx

try:
    adapter_main_path = Path(__file__).resolve().parents[1] / "services" / "sap-btp-adapter" / "main.py"
    spec = importlib.util.spec_from_file_location("sap_btp_adapter_main", adapter_main_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load adapter module from {adapter_main_path}")

    sap_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sap_module)

    app = sap_module.app
    map_sap_event_to_action = sap_module.map_sap_event_to_action
    verdict_to_sap_workflow = sap_module.verdict_to_sap_workflow
    SAP_EVENT_MAP = sap_module.SAP_EVENT_MAP
    SAPCloudEvent = sap_module.SAPCloudEvent

    from httpx import ASGITransport, AsyncClient
except (ImportError, ModuleNotFoundError) as _e:
    pytest.skip(
        f"SAP BTP adapter tests skipped — missing dependency: {_e}. "
        "Run inside Docker with crewai installed to execute these tests.",
        allow_module_level=True,
    )


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def finance_event -> SAPCloudEvent:
    return SAPCloudEvent(
        specversion="1.0",
        id=str(uuid.uuid4()),
        source="/sap/s4hana-prod/purchaseorder",
        type="sap.s4.beh.purchaseorder.v1.PurchaseOrder.Created.v1",
        sap_source_system="S4H-PROD-001",
        data={
            "PurchaseOrder": "PO-TEST-001",
            "Supplier": "VENDOR-TEST-001",
            "NetAmount": 45000,
            "DocumentCurrency": "INR",
        },
    )


@pytest.fixture
def large_finance_event -> SAPCloudEvent:
    return SAPCloudEvent(
        specversion="1.0",
        id=str(uuid.uuid4()),
        source="/sap/s4hana-prod/purchaseorder",
        type="sap.s4.beh.purchaseorder.v1.PurchaseOrder.Created.v1",
        sap_source_system="S4H-PROD-001",
        data={
            "NetAmount": 500000,
            "DocumentCurrency": "INR",
        },
    )


@pytest.fixture
def hr_event -> SAPCloudEvent:
    return SAPCloudEvent(
        specversion="1.0",
        id=str(uuid.uuid4()),
        source="/sap/successfactors/employee",
        type="sap.s4.beh.employee.v1.Employee.Onboarded.v1",
        sap_source_system="SF-PROD-001",
        data={"EmployeeId": "EMP-TEST-001", "Department": "Engineering"},
    )


@pytest.fixture
def sales_event -> SAPCloudEvent:
    return SAPCloudEvent(
        specversion="1.0",
        id=str(uuid.uuid4()),
        source="/sap/s4hana-prod/salesorder",
        type="sap.s4.beh.salesorder.v1.SalesOrder.Created.v1",
        sap_source_system="S4H-PROD-001",
        data={
            "SalesOrder": "SO-TEST-001",
            "TotalNetAmount": 12000,
            "TransactionCurrency": "INR",
        },
    )


@pytest.fixture
def iot_alert_event -> SAPCloudEvent:
    return SAPCloudEvent(
        specversion="1.0",
        id=str(uuid.uuid4()),
        source="/sap/btp/alert-notification",
        type="com.sap.alert.notification.v1.AlertNotification.Triggered.v1",
        sap_source_system="EDGE-CLUSTER-A",
        data={"thresholdValue": 92.7, "alertType": "THRESHOLD_BREACH"},
    )


@pytest.fixture
def unknown_event -> SAPCloudEvent:
    return SAPCloudEvent(
        specversion="1.0",
        id=str(uuid.uuid4()),
        source="/sap/unknown",
        type="com.sap.unknown.event.type",
        data={"someField": "value"},
    )


# ─── Unit Tests: Event Mapping ──────────────────────────────────────────────────

class TestSAPEventMapping:
    def test_finance_event_maps_correctly(self, finance_event):
        action = map_sap_event_to_action(finance_event)
        assert action["action_type"] == "approve_purchase"
        assert action["agent_role"] == "fi_analyst"
        assert action["amount"] == 45000.0
        assert action["currency"] == "INR"

    def test_hr_event_maps_correctly(self, hr_event):
        action = map_sap_event_to_action(hr_event)
        assert action["action_type"] == "access_pii"
        assert action["agent_role"] == "hr_bot"
        assert action["amount"] == 0.0  # No amount for HR events

    def test_sales_event_maps_correctly(self, sales_event):
        action = map_sap_event_to_action(sales_event)
        assert action["action_type"] == "issue_discount"
        assert action["agent_role"] == "sales_rep"
        assert action["amount"] == 12000.0

    def test_iot_alert_event_maps_correctly(self, iot_alert_event):
        action = map_sap_event_to_action(iot_alert_event)
        assert action["action_type"] == "threshold_breach"
        assert action["agent_role"] == "edge_sensor"

    def test_unknown_event_uses_fallback(self, unknown_event):
        action = map_sap_event_to_action(unknown_event)
        assert action["action_type"] == "unknown_event_action"
        assert action["agent_role"] == "unregistered_agent"

    def test_large_amount_is_parsed(self, large_finance_event):
        action = map_sap_event_to_action(large_finance_event)
        assert action["amount"] == 500000.0

    def test_sap_metadata_is_preserved(self, finance_event):
        action = map_sap_event_to_action(finance_event)
        assert action["sap_source"] == finance_event.source
        assert action["sap_event_type"] == finance_event.type

    def test_all_7_event_types_are_supported(self):
        assert len(SAP_EVENT_MAP) >= 7

    def test_missing_amount_field_defaults_to_zero(self):
        event = SAPCloudEvent(
            specversion="1.0",
            id=str(uuid.uuid4()),
            source="/sap/s4hana/purchaseorder",
            type="sap.s4.beh.purchaseorder.v1.PurchaseOrder.Created.v1",
            data={"SomethingElse": "value"},  # No NetAmount
        )
        action = map_sap_event_to_action(event)
        assert action["amount"] == 0.0


# ─── Unit Tests: Verdict Mapping ───────────────────────────────────────────────

class TestVerdictMapping:
    def test_approve_maps_to_sap_approve(self):
        result = verdict_to_sap_workflow("approve", "All policies passed")
        assert result["workflow_decision"] == "APPROVE"
        assert result["requires_human_review"] is False
        assert result["escalation_contact"] is None

    def test_block_maps_to_sap_reject(self):
        result = verdict_to_sap_workflow("block", "Critical policy violation")
        assert result["workflow_decision"] == "REJECT"
        assert result["requires_human_review"] is True
        assert result["escalation_contact"] is not None

    def test_escalate_maps_to_sap_delegate(self):
        result = verdict_to_sap_workflow("escalate", "Exceeds authority limit")
        assert result["workflow_decision"] == "DELEGATE"
        assert result["requires_human_review"] is True
        assert result["escalation_contact"] is not None

    def test_verdict_is_case_insensitive(self):
        result_upper = verdict_to_sap_workflow("APPROVE", "")
        result_lower = verdict_to_sap_workflow("approve", "")
        assert result_upper["workflow_decision"] == result_lower["workflow_decision"]


# ─── Integration Tests: API Endpoints ─────────────────────────────────────────

@pytest.mark.asyncio
class TestSAPAdapterEndpoints:
    async def test_root_endpoint(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "AgentGovern OS — SAP BTP Adapter"
        assert "supported_event_types" in data

    async def test_supported_events_endpoint(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/sap/events/supported")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 7
        assert len(data["events"]) == data["count"]

    async def test_health_endpoint_structure(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "governance_api" in data

    @patch("main.find_or_create_agent_for_role")
    @patch("main.httpx.AsyncClient")
    async def test_evaluate_without_governance_api_returns_block(self, mock_client_cls, mock_find_agent):
        """When governance API is unreachable AND no agent found, returns BLOCK (zero-trust)."""
        mock_find_agent.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/sap/governance/evaluate",
                json={
                    "specversion": "1.0",
                    "id": str(uuid.uuid4()),
                    "source": "/sap/test",
                    "type": "sap.s4.beh.purchaseorder.v1.PurchaseOrder.Created.v1",
                    "data": {"NetAmount": 50000, "DocumentCurrency": "INR"},
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["verdict"] == "BLOCK"
        assert data["requires_human_review"] is True

    async def test_supported_events_has_required_fields(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/sap/events/supported")
        data = resp.json()
        for event in data["events"]:
            assert "type" in event
            assert "action_type" in event
            assert "agent_role" in event
            assert "has_amount" in event


# ─── Tests: SAPCloudEvent Model Validation ─────────────────────────────────────

class TestSAPCloudEventModel:
    def test_event_requires_source(self):
        with pytest.raises(Exception):
            SAPCloudEvent(
                type="sap.s4.beh.purchaseorder.v1.PurchaseOrder.Created.v1",
                data={},
            )

    def test_event_requires_type(self):
        with pytest.raises(Exception):
            SAPCloudEvent(
                source="/sap/test",
                data={},
            )

    def test_event_auto_generates_id(self):
        event = SAPCloudEvent(source="/sap/test", type="com.test.event", data={})
        assert event.id is not None
        assert len(event.id) > 0

    def test_event_defaults_to_specversion_1(self):
        event = SAPCloudEvent(source="/sap/test", type="com.test.event", data={})
        assert event.specversion == "1.0"

    def test_event_handles_empty_data(self):
        event = SAPCloudEvent(source="/sap/test", type="com.test.event", data={})
        action = map_sap_event_to_action(event)
        assert action["amount"] == 0.0
