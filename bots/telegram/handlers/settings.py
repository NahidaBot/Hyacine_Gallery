"""Bot 设置面板 — /settings 命令 + InlineKeyboard 交互。"""

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from handlers.artwork import _get_client, _is_admin

logger = logging.getLogger(__name__)

# 设置项定义：(key, 显示名, 描述, 默认值)
SETTING_DEFS: list[tuple[str, str, str, str]] = [
    ("auto_import_url", "自动导入链接", "转发带链接消息时自动导入并发布", "false"),
    ("auto_import_search", "自动导入搜图", "外部搜图命中时自动导入最佳结果并发布", "false"),
]

# callback_data 前缀
_CB_PREFIX = "set:"


def is_setting_enabled(settings: dict[str, str], key: str, default: str = "false") -> bool:
    """检查某个布尔型设置是否开启。供其他 handler 模块调用。"""
    return settings.get(key, default).lower() == "true"


def _toggle_label(enabled: bool) -> str:
    return "✅ 开" if enabled else "❌ 关"


def build_settings_keyboard(settings: dict[str, str]) -> InlineKeyboardMarkup:
    """根据当前设置生成 InlineKeyboard。"""
    buttons: list[list[InlineKeyboardButton]] = []
    for key, name, _desc, default in SETTING_DEFS:
        enabled = is_setting_enabled(settings, key, default)
        label = f"{name}: {_toggle_label(enabled)}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"{_CB_PREFIX}{key}")])
    buttons.append([InlineKeyboardButton("关闭面板", callback_data="set:close")])
    return InlineKeyboardMarkup(buttons)


def build_settings_text(settings: dict[str, str]) -> str:
    """生成设置面板的文本说明。"""
    lines = ["<b>Bot 设置</b>\n"]
    for key, name, desc, default in SETTING_DEFS:
        enabled = is_setting_enabled(settings, key, default)
        lines.append(f"{_toggle_label(enabled)} <b>{name}</b> — {desc}")
    return "\n".join(lines)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /settings — 显示设置面板。"""
    if not update.message or not update.effective_user:
        return

    if not await _is_admin(update.effective_user.id, context):
        await update.message.reply_text("权限不足。")
        return

    settings = context.bot_data.get("bot_settings", {})
    await update.message.reply_text(
        build_settings_text(settings),
        parse_mode="HTML",
        reply_markup=build_settings_keyboard(settings),
    )


async def settings_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """处理 set: 开头的回调。返回 True 表示已处理。"""
    query = update.callback_query
    if not query or not query.data or not query.data.startswith(_CB_PREFIX):
        return False

    await query.answer()
    key = query.data.removeprefix(_CB_PREFIX)

    if key == "close":
        await query.edit_message_reply_markup(reply_markup=None)
        return True

    # 检查权限
    user_id = query.from_user.id if query.from_user else None
    if not await _is_admin(user_id, context):
        await query.answer("权限不足。", show_alert=True)
        return True

    # 验证 key 合法
    valid_keys = {k for k, *_ in SETTING_DEFS}
    if key not in valid_keys:
        return True

    # 切换值
    settings: dict[str, str] = context.bot_data.get("bot_settings", {})
    default = next((d for k, _, _, d in SETTING_DEFS if k == key), "false")
    current = is_setting_enabled(settings, key, default)
    new_value = "false" if current else "true"

    # 持久化到后端
    client = _get_client(context)
    try:
        await client.update_bot_settings({key: new_value})
    except Exception:
        logger.exception("保存设置失败: %s=%s", key, new_value)
        await query.answer("保存失败，请稍后重试。", show_alert=True)
        return True

    # 更新本地缓存
    settings[key] = new_value
    context.bot_data["bot_settings"] = settings

    # 刷新面板
    await query.edit_message_text(
        build_settings_text(settings),
        parse_mode="HTML",
        reply_markup=build_settings_keyboard(settings),
    )
    return True
