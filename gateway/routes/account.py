from identity.adapters.inbound.account import profile_payload, router
from identity.adapters.outbound.postgres import PostgresIdentityRepository

ensure_account_tables = PostgresIdentityRepository.ensure_tables

__all__ = ["router", "profile_payload", "ensure_account_tables"]
