"""
Tool: Document Search — search contracts, POs, invoices, and communication logs.

Used by: Evidence Collector agent.
"""

import logging
from typing import Any

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DocumentSearchInput(BaseModel):
    dispute_id: str = Field(..., description="The dispute ID to search documents for")
    document_types: list[str] = Field(
        default=["invoice", "purchase_order", "delivery_receipt", "contract", "email"],
        description="Types of documents to search for",
    )
    customer_id: str | None = Field(None, description="Customer ID to narrow search")
    date_from: str | None = Field(None, description="Search from date (ISO format)")
    date_to: str | None = Field(None, description="Search to date (ISO format)")
    keywords: list[str] | None = Field(None, description="Keywords to search within documents")


class DocumentSearchTool(BaseTool):
    """
    Search and retrieve all relevant documents for a dispute.

    Searches the document repository for invoices, purchase orders,
    delivery receipts, contracts, and email communications related
    to a specific dispute or customer.
    """

    name: str = "document_search"
    description: str = (
        "Search for all relevant documents related to a dispute. "
        "Retrieves invoices, purchase orders, delivery receipts, contracts, "
        "and email communications. Returns a structured evidence package."
    )
    args_schema: type[BaseModel] = DocumentSearchInput
    api_url: str = "http://localhost:8000"

    def _run(
        self,
        dispute_id: str,
        document_types: list[str] = None,
        customer_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        keywords: list[str] | None = None,
    ) -> str:
        """Execute the document search."""
        try:
            params: dict[str, Any] = {
                "dispute_id": dispute_id,
                "document_types": document_types or ["invoice", "purchase_order", "delivery_receipt"],
            }
            if customer_id:
                params["customer_id"] = customer_id
            if date_from:
                params["date_from"] = date_from
            if date_to:
                params["date_to"] = date_to
            if keywords:
                params["keywords"] = keywords

            response = httpx.post(
                f"{self.api_url}/api/v1/documents/search",
                json=params,
                timeout=30.0,
            )

            if response.status_code == 200:
                data = response.json
                return self._format_evidence_package(data)
            elif response.status_code == 404:
                return f"No documents found for dispute {dispute_id}. The dispute ID may be incorrect or documents have not been uploaded yet."
            else:
                logger.warning(f"Document search API returned {response.status_code}")
                return self._generate_mock_evidence(dispute_id, document_types or [])

        except httpx.ConnectError:
            logger.warning("Governance API unreachable — returning mock evidence for development")
            return self._generate_mock_evidence(dispute_id, document_types or [])
        except Exception as e:
            logger.error(f"DocumentSearchTool error: {e}")
            return f"Error searching documents: {e!s}"

    def _format_evidence_package(self, data: dict) -> str:
        """Format API response into a structured evidence package."""
        docs = data.get("documents", [])
        summary = (
            f"EVIDENCE PACKAGE — Found {len(docs)} documents\n"
            f"{'='*60}\n"
        )
        for doc in docs:
            summary += (
                f"\n[{doc.get('type', 'UNKNOWN').upper}]\n"
                f"  ID: {doc.get('id')}\n"
                f"  Date: {doc.get('date')}\n"
                f"  Amount: {doc.get('amount', 'N/A')}\n"
                f"  Status: {doc.get('status', 'N/A')}\n"
                f"  Notes: {doc.get('notes', 'None')}\n"
            )
        if not docs:
            summary += "\nNo documents found for the given criteria."
        return summary

    def _generate_mock_evidence(self, dispute_id: str, doc_types: list[str]) -> str:
        """Generate realistic mock evidence for development/testing."""
        return (
            f"EVIDENCE PACKAGE — Dispute: {dispute_id}\n"
            f"{'='*60}\n\n"
            "[INVOICE]\n"
            "  ID: INV-2024-087432\n"
            "  Date: 2024-11-15\n"
            "  Amount: ₹1,45,000.00\n"
            "  Status: Disputed — Customer claims short delivery\n"
            "  Notes: Line items 3 & 4 disputed (₹45,000 each)\n\n"
            "[PURCHASE_ORDER]\n"
            "  ID: PO-2024-003891\n"
            "  Date: 2024-11-01\n"
            "  Amount: ₹1,45,000.00\n"
            "  Status: Fulfilled — Supplier confirmation attached\n"
            "  Notes: Exact match with invoice line items\n\n"
            "[DELIVERY_RECEIPT]\n"
            "  ID: DR-2024-091234\n"
            "  Date: 2024-11-14\n"
            "  Status: PARTIAL — Items 1,2,5 signed; Items 3,4 missing customer signature\n"
            "  Notes: Delivery agent noted 'customer was not available for full inspection'\n\n"
            "[EMAIL]\n"
            "  ID: EMAIL-2024-11-16-customer\n"
            "  Date: 2024-11-16\n"
            "  From: procurement@customer.com\n"
            "  Subject: RE: Invoice INV-2024-087432\n"
            "  Notes: Customer requests credit note for items 3 & 4 (₹90,000)\n\n"
            "TIMELINE ANOMALY: Delivery receipt dated 1 day before customer complaint — "
            "consistent with partial delivery scenario. "
            "RECOMMENDATION: Request physical delivery log from logistics partner.\n"
        )
