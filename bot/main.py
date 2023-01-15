import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Type, Union

from aiogram import BaseMiddleware, Bot, Dispatcher, F, types
from aiogram.types import (
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Update,
)
from cachetools import TTLCache
from pyrogram import Client
from pyrogram import types as pyro_types

BOT_TOKEN = "BOT_TOKEN"
API_ID = 123
API_HASH = "CLIENT_API_HASH"


class BlockAlbumMiddleware(BaseMiddleware):
    # temporary dictionary with albums will expire in 5 seconds
    albums = TTLCache(maxsize=10, ttl=5)

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, types.Message) or not event.media_group_id:
            return
        # if one of the elements has already been received
        if event.media_group_id in self.albums:
            return
        self.albums[event.media_group_id] = event.message_id
        data["album"] = await data["client"].get_media_group(
            event.chat.id, event.message_id
        )
        return await handler(event, data)


def _get_input_media_cls(
    media_type: str,
) -> Union[
    Type[InputMediaPhoto],
    Type[InputMediaVideo],
    Type[InputMediaAudio],
    Type[InputMediaDocument],
]:
    if media_type == "photo":
        return InputMediaPhoto
    elif media_type == "video":
        return InputMediaVideo
    elif media_type == "audio":
        return InputMediaAudio
    elif media_type == "document":
        return InputMediaDocument
    raise ValueError("Unsupported media type")


async def handle_albums(message: types.Message, album: List[pyro_types.Message]):
    """
    This handler will get a list of all messages in the same media group.
    WARNING: the type of messages on the album is not "aiogram.types.Message", but "pyrogram.types.Message"
    """
    media_group = []
    for obj in album:
        media_type = str(obj.media.value)
        file_id = getattr(obj, media_type).file_id
        input_media_cls = _get_input_media_cls(media_type)
        media_group.append(input_media_cls(media=file_id))
    await message.answer_media_group(media_group)


async def main():
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.message.outer_middleware.register(BlockAlbumMiddleware())
    dp.message.register(handle_albums, F.media_group_id)
    client = Client("my_bot", bot_token=BOT_TOKEN, api_hash=API_HASH, api_id=API_ID)
    await client.start()
    await dp.start_polling(bot, client=client)


asyncio.run(main())
