"""
DID Management Router

Handles creation, resolution, and key rotation for W3C Decentralized Identifiers (DIDs).
Provides the authoritative mapping between `did:nuuvixx:uuid` and an agent's cryptographic material.
"""

import uuid
from datetime import UTC, datetime

from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models import Agent, DIDDocument, DIDKey
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Try importing cryptography, fallback to mock generation for dev if missing
try:
    import base58
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

router = APIRouter(prefix="/identity/did", tags=["Identity"])


class DIDCreateRequest(BaseModel):
    agent_id: str


class DIDResponse(BaseModel):
    did: str
    document: dict
    active_keys: list[dict]


def generate_ed25519_keypair():
    """Generate an Ed25519 keypair and return multibase strings (base58btc)."""
    if not HAS_CRYPTO:
        # Mock key generation for environments missing 'cryptography' or 'base58'
        import secrets
        pub = f"z{secrets.token_hex(32)}"
        priv = f"z{secrets.token_hex(64)}"
        return pub, priv

    private_key = ed25519.Ed25519PrivateKey.generate
    public_key = private_key.public_key
    
    # Multibase requires a prefix. 'z' indicates base58btc.
    # The actual bytes include multicodec prefixes, but we simplify here for the demo.
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption
    )
    
    pub_mb = f"z{base58.b58encode(pub_bytes).decode('utf-8')}"
    priv_mb = f"z{base58.b58encode(priv_bytes).decode('utf-8')}"
    
    return pub_mb, priv_mb


def build_did_document(did: str, pub_mb: str) -> dict:
    return {
        "@context": [
            "https://www.w3.org/ns/did/v1",
            "https://w3id.org/security/suites/ed25519-2020/v1"
        ],
        "id": did,
        "verificationMethod": [{
            "id": f"{did}#keys-1",
            "type": "Ed25519VerificationKey2020",
            "controller": did,
            "publicKeyMultibase": pub_mb
        }],
        "authentication": [f"{did}#keys-1"],
        "assertionMethod": [f"{did}#keys-1"]
    }


@router.post("/create", response_model=DIDResponse, status_code=status.HTTP_201_CREATED)
async def create_did(req: DIDCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a W3C DID for an existing agent (or newly registered one)."""
    # Verify agent exists
    result = await db.execute(select(Agent).where(Agent.id == uuid.UUID(req.agent_id)))
    agent = result.scalar_one_or_none
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    # Check if DID already exists
    if agent.did and agent.did.startswith("did:nuuvixx:"):
        raise HTTPException(status_code=409, detail=f"Agent already has a DID: {agent.did}")

    # Generate keys and DID string
    did_str = f"did:nuuvixx:{agent.id}"
    pub_mb, priv_mb = generate_ed25519_keypair
    
    doc_json = build_did_document(did_str, pub_mb)
    
    # Store DID Document
    did_doc = DIDDocument(
        agent_id=agent.id,
        did=did_str,
        document_json=doc_json
    )
    db.add(did_doc)
    
    # Store DID Key
    did_key = DIDKey(
        did=did_str,
        key_type="Ed25519VerificationKey2020",
        public_key_multibase=pub_mb,
        private_key_multibase=priv_mb, # TODO: Store this securely via Vault API in production
        status="active"
    )
    db.add(did_key)
    
    # Update agent
    agent.did = did_str
    
    await db.commit
    
    return DIDResponse(
        did=did_str,
        document=doc_json,
        active_keys=[{
            "key_type": did_key.key_type,
            "public_key_multibase": did_key.public_key_multibase,
            "status": did_key.status
        }]
    )


@router.get("/{did}", response_model=DIDResponse)
async def resolve_did(did: str, db: AsyncSession = Depends(get_db)):
    """Resolve a DID to its DID Document (Universal Resolver implementation)."""
    result = await db.execute(select(DIDDocument).where(DIDDocument.did == did))
    doc = result.scalar_one_or_none
    
    if not doc:
        raise HTTPException(status_code=404, detail="DID not found")
        
    # Get active keys
    keys_result = await db.execute(select(DIDKey).where(DIDKey.did == did, DIDKey.status == "active"))
    active_keys = keys_result.scalars.all
    
    return DIDResponse(
        did=did,
        document=doc.document_json,
        active_keys=[{
            "key_type": k.key_type,
            "public_key_multibase": k.public_key_multibase,
            "status": k.status
        } for k in active_keys]
    )


@router.post("/{did}/rotate-key", response_model=DIDResponse)
async def rotate_did_key(did: str, db: AsyncSession = Depends(get_db)):
    """Rotate the cryptographic material for a DID."""
    result = await db.execute(select(DIDDocument).where(DIDDocument.did == did))
    doc = result.scalar_one_or_none
    
    if not doc:
        raise HTTPException(status_code=404, detail="DID not found")
        
    # Revoke old active keys
    keys_result = await db.execute(select(DIDKey).where(DIDKey.did == did, DIDKey.status == "active"))
    old_keys = keys_result.scalars.all
    now = datetime.now(UTC)
    for k in old_keys:
        k.status = "revoked"
        k.revoked_at = now
        
    # Generate new key
    pub_mb, priv_mb = generate_ed25519_keypair
    
    new_key = DIDKey(
        did=did,
        key_type="Ed25519VerificationKey2020",
        public_key_multibase=pub_mb,
        private_key_multibase=priv_mb,
        status="active"
    )
    db.add(new_key)
    
    # Update document
    doc_json = doc.document_json
    
    # Generate a unique key ID based on timestamp
    key_id = f"{did}#keys-{int(now.timestamp)}"
    
    doc_json["verificationMethod"] = [{
        "id": key_id,
        "type": "Ed25519VerificationKey2020",
        "controller": did,
        "publicKeyMultibase": pub_mb
    }]
    doc_json["authentication"] = [key_id]
    doc_json["assertionMethod"] = [key_id]
    
    doc.document_json = doc_json
    
    await db.commit
    
    return DIDResponse(
        did=did,
        document=doc_json,
        active_keys=[{
            "key_type": new_key.key_type,
            "public_key_multibase": new_key.public_key_multibase,
            "status": new_key.status
        }]
    )
