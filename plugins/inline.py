# file: plugins/inline.py
"""
Inline query handler with a persistent channel URL button and a clean reply markup.
- Fixes broken string ("Search again") that was split across lines.
- Ensures InlineKeyboardMarkup is returned correctly.
- Temporarily forces cache_time=0 in query.answer for testing to bypass Telegram inline cache.
  Set FORCE_FRESH_CACHE = False once verified.
"""

import logging
from pyrogram import Client, emoji, filters  # filters may be used elsewhere
from pyrogram.errors.exceptions.bad_request_400 import QueryIdInvalid
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultCachedDocument,
    InlineQuery,
)
from database.ia_filterdb import get_search_results
from utils import is_subscribed, get_size, temp
from info import CACHE_TIME, AUTH_USERS, AUTH_CHANNEL, CUSTOM_FILE_CAPTION

logger = logging.getLogger(__name__)

# When AUTH gating exists, default cache_time is already 0 in original code.
cache_time = 0 if AUTH_USERS or AUTH_CHANNEL else CACHE_TIME

# Toggle this to True while testing to bypass Telegram's inline cache.
FORCE_FRESH_CACHE = True


async def inline_users(query: InlineQuery):
    if AUTH_USERS:
        if query.from_user and query.from_user.id in AUTH_USERS:
            return True
        else:
            return False
    if query.from_user and query.from_user.id not in temp.BANNED_USERS:
        return True
    return False


@Client.on_inline_query()
async def answer(bot, query):
    """Show search results for a given inline query"""

    if not await inline_users(query):
        await query.answer(
            results=[],
            cache_time=0,
            switch_pm_text="okDa",
            switch_pm_parameter="hehe",
        )
        return

    if AUTH_CHANNEL and not await is_subscribed(bot, query):
        await query.answer(
            results=[],
            cache_time=0,
            switch_pm_text="You have to subscribe my channel to use the bot",
            switch_pm_parameter="subscribe",
        )
        return

    results = []

    if "|" in query.query:
        string, file_type = query.query.split("|", maxsplit=1)
        string = string.strip()
        file_type = file_type.strip().lower()
    else:
        string = query.query.strip()
        file_type = None

    offset = int(query.offset or 0)
    reply_markup = get_reply_markup(query=string)

    files, next_offset, total = await get_search_results(
        string,
        file_type=file_type,
        max_results=10,
        offset=offset,
    )

    for file in files:
        title = file.file_name
        size = get_size(file.file_size)
        f_caption = file.caption

        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(
                    file_name="" if title is None else title,
                    file_size="" if size is None else size,
                    file_caption="" if f_caption is None else f_caption,
                )
            except Exception as e:
                logger.exception(e)
                # keep original caption on format error
                f_caption = f_caption

        if f_caption is None:
            f_caption = f"{file.file_name}"

        results.append(
            InlineQueryResultCachedDocument(
                title=file.file_name,
                document_file_id=file.file_id,
                caption=f_caption,
                description=f"Size: {get_size(file.file_size)}\nType: {file.file_type}",
                reply_markup=reply_markup,
            )
        )

    if results:
        switch_pm_text = f"{emoji.FILE_FOLDER} Results - {total}"
        if string:
            switch_pm_text += f" for {string}"
        try:
            await query.answer(
                results=results,
                is_personal=True,
                cache_time=0 if FORCE_FRESH_CACHE else cache_time,  # why: bypass cache while testing
                switch_pm_text=switch_pm_text,
                switch_pm_parameter="start",
                next_offset=str(next_offset),
            )
        except QueryIdInvalid:
            pass
        except Exception as e:
            logging.exception(str(e))
    else:
        switch_pm_text = f"{emoji.CROSS_MARK} No results"
        if string:
            switch_pm_text += f' for "{string}"'

        await query.answer(
            results=[],
            is_personal=True,
            cache_time=0 if FORCE_FRESH_CACHE else cache_time,
            switch_pm_text=switch_pm_text,
            switch_pm_parameter="okay",
        )


def get_reply_markup(query: str) -> InlineKeyboardMarkup:
    """Build per-result inline keyboard.
    Contains a persistent channel URL button + a search-again helper.
    """
    buttons = [
        [
            InlineKeyboardButton(
                "📚 HD MOVIES HUB 📚",
                url="https://t.me/+KJHSwIdswKUwZjU1",  # replace with your channel if needed
            )
        ],
        [
            InlineKeyboardButton(
                "Search again", switch_inline_query_current_chat=query
            )
        ],
    ]
    return InlineKeyboardMarkup(buttons)
                
    




