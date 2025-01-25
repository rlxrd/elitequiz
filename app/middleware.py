from aiogram import BaseMiddleware
from aiogram.types import Message

from typing import Callable, Dict, Any, Awaitable

from app.database.requests import get_user


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        self.user = await get_user(event.from_user.id)
        data['user'] = self.user
        return await handler(event, data)
