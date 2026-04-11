from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from handlers.artwork import import_command, post_command, random_command, search_command
from handlers.basic import help_command, ping_command, start_command
from handlers.original import TELEGRAM_SYSTEM_USER_ID, channel_post_handler
from handlers.photo import callback_handler, photo_handler
from handlers.settings import settings_command


def register_handlers(app: Application) -> None:  # type: ignore[type-arg]
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("random", random_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("post", post_command))
    app.add_handler(CommandHandler("import", import_command))
    app.add_handler(CommandHandler("settings", settings_command))

    # 监听评论群中频道帖子通知（来自系统用户 777000），自动回复原图（无压缩）
    app.add_handler(
        MessageHandler(
            filters.FORWARDED & filters.PHOTO & filters.User(TELEGRAM_SYSTEM_USER_ID),
            channel_post_handler,
            block=False,
        )
    )

    # 图片消息处理（搜图 + 转发提取 + 溯源），排除系统用户
    app.add_handler(
        MessageHandler(
            filters.PHOTO & ~filters.ChatType.CHANNEL & ~filters.User(TELEGRAM_SYSTEM_USER_ID),
            photo_handler,
        )
    )
    # InlineKeyboard 回调处理
    app.add_handler(CallbackQueryHandler(callback_handler))
