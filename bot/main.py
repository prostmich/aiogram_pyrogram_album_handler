import asyncio
from typing import List

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware
from expiringdict import ExpiringDict
from pyrogram import Client
from pyrogram import types as pyro_types

BOT_TOKEN = "BOT_TOKEN"
API_ID = 123
API_HASH = "CLIENT_API_HASH"


class BlockAlbumMiddleware(BaseMiddleware):
    # temporary dictionary with albums will expire in 5 seconds
    albums: ExpiringDict = ExpiringDict(max_len=10, max_age_seconds=5, items=None)

    async def on_process_message(self, message: types.Message, data: dict):
        if not message.media_group_id:
            return
        # if one of the elements has already been received
        if message.media_group_id in self.albums:
            raise CancelHandler()
        self.albums[message.media_group_id] = message.message_id
        client = message.bot.get("client")
        data["album"] = await client.get_media_group(message.chat.id, message.message_id)


async def handle_albums(message: types.Message, album: List[pyro_types.Message]):
    """
    This handler will get a list of all messages in the same media group.
    WARNING: the type of messages in the album is not "aiogram.types.Message", but "pyrogram.types.Message"
    """
    media_group = types.MediaGroup()
    for obj in album:
        file_id = obj[obj.media].file_id
        try:
            media_group.attach({"media": file_id, "type": obj.media})
        except ValueError:
            return await message.answer("This type of album is not supported by aiogram.")
    await message.answer_media_group(media_group)


async def main():
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher(bot)
    dp.middleware.setup(BlockAlbumMiddleware())
    dp.register_message_handler(handle_albums, is_media_group=True, content_types="any")
    client = Client("my_bot", bot_token=BOT_TOKEN, api_hash=API_HASH, api_id=API_ID)
    bot["client"] = client
    await client.start()
    await dp.start_polling()


asyncio.run(main())
