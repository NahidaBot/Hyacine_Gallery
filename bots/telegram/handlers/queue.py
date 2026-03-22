"""Bot 队列处理 job — 定时从发布队列取出条目并发布到 Telegram 频道。"""

import logging
import time

from telegram.ext import ContextTypes

from handlers.artwork import _get_client, _log_post, _resolve_target_channel, post_to_channel

logger = logging.getLogger(__name__)

_DEFAULT_QUEUE_INTERVAL = 7200  # 默认间隔 120 分钟（秒）


async def process_post_queue(context: ContextTypes.DEFAULT_TYPE) -> None:
    """定时 job：从队列取下一条 pending 条目，发布到频道。

    每 60 秒执行一次，内部通过 queue_interval_minutes 控制实际发布间隔。
    通过 bot_settings 缓存（每 60 秒由 refresh_bot_settings job 更新）
    读取配置，无需额外 DB 查询。
    """
    bot_settings_cache: dict[str, str] = context.bot_data.get("bot_settings", {})

    # 检查队列开关
    if bot_settings_cache.get("queue_enabled", "true").lower() != "true":
        logger.debug("发布队列已禁用，跳过本次轮询")
        return

    # 检查发布间隔：距上次队列发布不足 interval 则跳过
    interval_seconds = int(bot_settings_cache.get("queue_interval_minutes", "120")) * 60
    if interval_seconds <= 0:
        interval_seconds = _DEFAULT_QUEUE_INTERVAL
    last_queue_post_time: float = context.bot_data.get("last_queue_post_time", 0.0)
    if (time.time() - last_queue_post_time) < interval_seconds:
        logger.debug("距上次队列发布不足 %d 秒，跳过", interval_seconds)
        return

    client = _get_client(context)

    # 检查每日上限
    daily_limit = int(bot_settings_cache.get("queue_daily_limit", "0"))
    if daily_limit > 0:
        try:
            today_count = await client.get_today_post_count()
            if today_count >= daily_limit:
                logger.debug("今日发布已达上限 %d/%d，跳过", today_count, daily_limit)
                return
        except Exception:
            logger.warning("获取今日发布计数失败，继续处理", exc_info=True)

    # 取下一条 pending 条目
    item = await client.pop_queue_item()
    if item is None:
        logger.debug("队列为空，无待发布条目")
        return

    logger.info("处理队列条目 #%d，作品 #%d", item.id, item.artwork_id)

    # 获取作品信息
    artwork = await client.get_artwork(item.artwork_id)
    if artwork is None:
        logger.warning("队列条目 #%d 对应作品 #%d 不存在，标记为失败", item.id, item.artwork_id)
        await client.mark_queue_failed(item.id, "作品不存在")
        return

    # 解析目标频道：若队列条目指定了 channel_id 则直接使用，否则通过路由规则确定
    channel_id = item.channel_id or await _resolve_target_channel(context, artwork)
    if not channel_id:
        logger.warning("队列条目 #%d 无可用频道，标记为失败", item.id)
        await client.mark_queue_failed(item.id, "无可用发布频道")
        return

    # 发布到频道
    try:
        result = await post_to_channel(context, artwork, channel_id)
    except Exception as e:
        logger.error("队列条目 #%d 发布失败：%s", item.id, e, exc_info=True)
        await client.mark_queue_failed(item.id, str(e))
        return

    if result is None:
        await client.mark_queue_failed(item.id, "发布返回空结果")
        return

    # 标记完成并记录日志
    await client.mark_queue_done(item.id)
    await _log_post(context, artwork, result, posted_by="queue")
    context.bot_data["last_queue_post_time"] = time.time()
    logger.info("队列条目 #%d 发布成功：%s", item.id, result.message_link)
