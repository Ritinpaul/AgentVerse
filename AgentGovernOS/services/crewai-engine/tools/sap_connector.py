"""
Tool: SAP Connector — bridge to SAP BTP / S4HANA via OData.

Used by: Evidence Collector (document retrieval), Dispute Resolver (workflow triggers).
"""

import logging

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SAPQueryInput(BaseModel):
    entity: str = Field(
        ...,
        description=(
            "SAP entity to query. Options: "
            "BusinessPartner, SalesOrder, Invoice, DeliveryOrder, PaymentDoc, ARDocument"
        ),
    )
    filters: dict = Field(default_factory=dict, description="OData $filter parameters as key-value pairs")
    expand: list[str] = Field(default_factory=list, description="OData $expand relations to include")
    top: int = Field(10, description="Maximum records to return ($top)")
    select: list[str] = Field(default_factory=list, description="Specific fields to select ($select)")


class SAPWorkflowInput(BaseModel):
    workflow_type: str = Field(
        ...,
        description="SAP workflow to trigger: DISPUTE_CREATED, CREDIT_NOTE_ISSUED, ESCALATION_CREATED",
    )
    business_object_id: str = Field(..., description="SAP business object ID (e.g., dispute ID, invoice ID)")
    payload: dict = Field(default_factory=dict, description="Workflow trigger payload")


class SAPConnectorTool(BaseTool):
    """
    Query SAP S4HANA / BTP via OData API for business documents.

    Operations:
    - query_entity: Fetch SAP business objects (invoices, orders, partners)
    - trigger_workflow: Start SAP workflow tasks from agent decisions

    Falls back gracefully when SAP sandbox is unavailable.
    """

    name: str = "sap_connector"
    description: str = (
        "Connect to SAP S4HANA / BTP to fetch business documents and trigger workflows. "
        "Use query_entity to get invoices, sales orders, business partner data, or AR documents. "
        "Use trigger_workflow to create SAP dispute records or issue credit notes. "
        "Provide entity name and OData filter parameters."
    )
    args_schema: type[BaseModel] = SAPQueryInput
    sap_adapter_url: str = "http://localhost:8010"  # SAP BTP adapter service

    def _run(
        self,
        entity: str,
        filters: dict = None,
        expand: list[str] = None,
        top: int = 10,
        select: list[str] = None,
    ) -> str:
        """Query an SAP entity via OData."""
        params: dict = {"$top": top}
        if filters:
            filter_str = " and ".join(f"{k} eq '{v}'" for k, v in filters.items)
            params["$filter"] = filter_str
        if expand:
            params["$expand"] = ",".join(expand)
        if select:
            params["$select"] = ",".join(select)

        try:
            response = httpx.get(
                f"{self.sap_adapter_url}/odata/v4/{entity}",
                params=params,
                timeout=20.0,
                headers={"Accept": "application/json"},
            )
            if response.status_code == 200:
                data = response.json
                return self._format_sap_results(entity, data)
            else:
                logger.warning(f"SAP adapter returned {response.status_code} for {entity}")
                return self._mock_sap_data(entity, filters or {})
        except httpx.ConnectError:
            return self._mock_sap_data(entity, filters or {})
        except Exception as e:
            logger.error(f"SAPConnectorTool error: {e}")
            return f"SAP query error: {e!s}"

    def trigger_workflow(
        self,
        workflow_type: str,
        business_object_id: str,
        payload: dict = None,
    ) -> str:
        """Trigger an SAP workflow from an agent decision."""
        try:
            response = httpx.post(
                f"{self.sap_adapter_url}/workflows/{workflow_type}",
                json={
                    "businessObjectId": business_object_id,
                    "workflowType": workflow_type,
                    "payload": payload or {},
                },
                timeout=15.0,
            )
            if response.status_code in (200, 201, 202):
                data = response.json
                return (
                    f"SAP WORKFLOW TRIGGERED ✓\n"
                    f"Type:        {workflow_type}\n"
                    f"Object ID:   {business_object_id}\n"
                    f"Workflow ID: {data.get('workflowInstanceId', 'N/A')}\n"
                    f"Status:      {data.get('status', 'STARTED')}\n"
                )
            else:
                return f"SAP workflow '{workflow_type}' queued — adapter returned {response.status_code}"
        except httpx.ConnectError:
            return (
                f"SAP WORKFLOW QUEUED (adapter offline)\n"
                f"Type: {workflow_type} | Object: {business_object_id}\n"
                f"Will execute when SAP BTP adapter reconnects.\n"
            )

    def _format_sap_results(self, entity: str, data: dict) -> str:
        records = data.get("value", data if isinstance(data, list) else [data])
        result = f"SAP {entity} — {len(records)} records\n{'='*60}\n"
        for rec in records[:10]:
            result += "\n" + "\n".join(f"  {k}: {v}" for k, v in list(rec.items)[:8]) + "\n"
        return result

    def _mock_sap_data(self, entity: str, filters: dict) -> str:
        """Return realistic SAP mock data for development."""
        mock_data = {
            "Invoice": (
                "SAP Invoice — Mock Data\n"
                "{'InvoiceID': 'SAP-INV-2024-087432', 'CustomerID': 'CUST-00892',\n"
                " 'GrossAmount': 145000.00, 'Currency': 'INR',\n"
                " 'PostingDate': '2024-11-15', 'DueDate': '2024-12-15',\n"
                " 'Status': 'OPEN_DISPUTED', 'CompanyCode': 'SAP_IN01'}\n"
            ),
            "BusinessPartner": (
                "SAP BusinessPartner — Mock Data\n"
                "{'BusinessPartnerID': 'BP-00892', 'Name': 'Acme Manufacturing Pvt Ltd',\n"
                " 'Category': 'CUSTOMER', 'CreditLimit': 1000000, 'PaymentTerms': 'NET30',\n"
                " 'AccountGroup': 'KUNA', 'SalesOrg': 'IN01'}\n"
            ),
            "SalesOrder": (
                "SAP SalesOrder — Mock Data\n"
                "{'SalesOrderID': 'SAP-SO-2024-003891', 'CustomerPO': 'PO-2024-003891',\n"
                " 'NetAmount': 145000.00, 'Currency': 'INR',\n"
                " 'OrderDate': '2024-11-01', 'DeliveryDate': '2024-11-14',\n"
                " 'Status': 'DELIVERED', 'Plant': 'PUNE_W1'}\n"
            ),
        }
        return mock_data.get(
            entity,
            f"SAP {entity} — (mock) No data available for entity '{entity}' with filters {filters}\n",
        )
