from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from chat.adapters.outbound.postgres import PostgresConversationRepository


@dataclass
class ChatContainer:
    conversations: PostgresConversationRepository


def build_chat_container(db: AsyncSession) -> ChatContainer:
    return ChatContainer(conversations=PostgresConversationRepository(db))
