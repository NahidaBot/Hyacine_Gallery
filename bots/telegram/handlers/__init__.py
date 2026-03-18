from telegram.ext import Application, CommandHandler

from handlers.artwork import import_command, post_command, random_command
from handlers.basic import help_command, ping_command, start_command


def register_handlers(app: Application) -> None:  # type: ignore[type-arg]
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("random", random_command))
    app.add_handler(CommandHandler("post", post_command))
    app.add_handler(CommandHandler("import", import_command))
