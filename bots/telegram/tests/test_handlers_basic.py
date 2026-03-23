"""Tests for basic command handlers (/start, /ping, /help)."""

from handlers.basic import help_command, ping_command, start_command


async def test_start_command(mock_update, mock_context):
    await start_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_once()
    text = mock_update.message.reply_text.call_args[0][0]
    assert "正在运行" in text


async def test_ping_command(mock_update, mock_context):
    await ping_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_once_with("pong")


async def test_help_command(mock_update, mock_context):
    await help_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_once()
    call_kwargs = mock_update.message.reply_text.call_args
    assert call_kwargs.kwargs.get("parse_mode") == "HTML"
    text = call_kwargs[0][0]
    assert "/random" in text
    assert "/post" in text
