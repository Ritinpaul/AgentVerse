"""
SPIFFE / SPIRE Integration

Generates and validates SPIFFE IDs (spiffe://nuuvixx.com/agent/{uuid})
and manages integration with the SPIRE server for X.509 SVID issuing.
"""

import uuid
from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

TRUST_DOMAIN = "nuuvixx.com"

def generate_spiffe_id(agent_id: str | uuid.UUID) -> str:
    """Generate a valid SPIFFE ID string for an agent."""
    return f"spiffe://{TRUST_DOMAIN}/agent/{agent_id!s}"


def mock_generate_svid(agent_id: str | uuid.UUID):
    """
    Mock implementation of a SPIRE server call to get an X.509 SVID.
    In production, this would use the SPIRE Workload API (gRPC).
    """
    spiffe_id = generate_spiffe_id(agent_id)
    
    # Generate an ephemeral keypair for the agent's workload
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Generate self-signed cert simulating an SVID
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Nuuvixx"),
        x509.NameAttribute(NameOID.COMMON_NAME, spiffe_id),
    ])
    
    cert = x509.CertificateBuilder.subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key
    ).serial_number(
        x509.random_serial_number
    ).not_valid_before(
        datetime.now(UTC)
    ).not_valid_after(
        datetime.now(UTC) + timedelta(days=1)
    ).add_extension(
        x509.SubjectAlternativeName([x509.UniformResourceIdentifier(spiffe_id)]),
        critical=False,
    ).sign(private_key, hashes.SHA256)
    
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption
    ).decode('utf-8')
    
    return {
        "spiffe_id": spiffe_id,
        "svid_cert": cert_pem,
        "svid_key": key_pem,
        "expires_at": cert.not_valid_after.isoformat
    }
