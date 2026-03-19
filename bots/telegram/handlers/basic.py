from telegram import Update
from telegram.ext import ContextTypes


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Hyacine Gallery Bot 正在运行。")


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("pong")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "<b>命令列表：</b>\n"
        "/post &lt;url&gt; [#tag1 #tag2] — 导入并发布到频道\n"
        "/post &lt;url&gt; --no-post — 仅导入（不发布到频道）\n"
        "/post &lt;id&gt; — 将已有作品发布到频道\n"
        "/import &lt;url&gt; [#tag1 #tag2] — 仅导入（别名）\n"
        "/random — 随机获取一个作品\n"
        "/help — 显示此帮助信息"
    )
    if update.message:
        await update.message.reply_text(text, parse_mode="HTML")
