from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from identity.adapters.outbound.argon2_hasher import Argon2PasswordHasher
from identity.adapters.outbound.jwt_signer import JwtTokenSigner
from identity.adapters.outbound.postgres import PostgresIdentityRepository
from identity.application.account import AccountService
from identity.application.auth import (
    AuthenticateUser,
    GetMe,
    ListMyRoles,
    ListRoles,
    ListUsers,
    LoginUser,
    LogoutUser,
    RegisterUser,
)


@dataclass
class IdentityContainer:
    hasher: Argon2PasswordHasher
    signer: JwtTokenSigner
    repo: PostgresIdentityRepository
    register: RegisterUser
    login: LoginUser
    logout: LogoutUser
    authenticate: AuthenticateUser
    me: GetMe
    list_users: ListUsers
    list_roles: ListRoles
    my_roles: ListMyRoles
    account: AccountService


def build_identity_container(db: AsyncSession) -> IdentityContainer:
    hasher = Argon2PasswordHasher()
    signer = JwtTokenSigner()
    repo = PostgresIdentityRepository(db)
    return IdentityContainer(
        hasher=hasher,
        signer=signer,
        repo=repo,
        register=RegisterUser(repo, hasher),
        login=LoginUser(repo, hasher, signer),
        logout=LogoutUser(repo, signer),
        authenticate=AuthenticateUser(repo, repo, signer),
        me=GetMe(repo, repo),
        list_users=ListUsers(repo),
        list_roles=ListRoles(repo),
        my_roles=ListMyRoles(repo),
        account=AccountService(repo, repo, signer),
    )
