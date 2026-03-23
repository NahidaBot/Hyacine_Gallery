"""测试 Bot 管理 API 路由。"""

import pytest


@pytest.mark.asyncio
async def test_create_post_log(app_client, sample_artwork):
    """POST /api/admin/bot/post-logs 应创建发布日志。"""
    resp = await app_client.post(
        "/api/admin/bot/post-logs",
        json={
            "artwork_id": sample_artwork.id,
            "bot_platform": "telegram",
            "channel_id": "-100999",
            "message_id": "42",
            "posted_by": "test",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["artwork_id"] == sample_artwork.id
    assert body["channel_id"] == "-100999"


@pytest.mark.asyncio
async def test_list_post_logs(app_client, sample_post_log):
    """GET /api/admin/bot/post-logs 应返回发布日志列表。"""
    resp = await app_client.get("/api/admin/bot/post-logs")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_list_channels(app_client, sample_channel):
    """GET /api/admin/bot/channels 应返回频道列表。"""
    resp = await app_client.get("/api/admin/bot/channels")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert body[0]["channel_id"] == "-1001234567890"


@pytest.mark.asyncio
async def test_create_channel(app_client):
    """POST /api/admin/bot/channels 应创建频道。"""
    resp = await app_client.post(
        "/api/admin/bot/channels",
        json={
            "platform": "telegram",
            "channel_id": "-100new",
            "name": "New Channel",
            "is_default": False,
            "priority": 10,
            "conditions": {},
            "enabled": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["channel_id"] == "-100new"
    assert body["name"] == "New Channel"


@pytest.mark.asyncio
async def test_update_channel(app_client, sample_channel):
    """PUT /api/admin/bot/channels/{id} 应更新频道。"""
    resp = await app_client.put(
        f"/api/admin/bot/channels/{sample_channel.id}",
        json={"name": "Updated Channel"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Channel"


@pytest.mark.asyncio
async def test_delete_channel(app_client, sample_channel):
    """DELETE /api/admin/bot/channels/{id} 应删除频道。"""
    resp = await app_client.delete(f"/api/admin/bot/channels/{sample_channel.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_list_settings(app_client):
    """GET /api/admin/bot/settings 应返回设置列表。"""
    resp = await app_client.get("/api/admin/bot/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)


@pytest.mark.asyncio
async def test_update_settings(app_client):
    """PUT /api/admin/bot/settings 应更新设置。"""
    resp = await app_client.put(
        "/api/admin/bot/settings",
        json={"settings": {"queue_interval_minutes": "60"}},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "updated"


@pytest.mark.asyncio
async def test_add_to_queue(app_client, sample_artwork):
    """POST /api/admin/bot/queue 应将作品加入队列。"""
    resp = await app_client.post(
        "/api/admin/bot/queue",
        json={
            "artwork_id": sample_artwork.id,
            "platform": "telegram",
            "priority": 50,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["artwork_id"] == sample_artwork.id
    assert body["status"] == "pending"


@pytest.mark.asyncio
async def test_list_queue(app_client, sample_artwork):
    """GET /api/admin/bot/queue 应返回队列列表。"""
    # 先添加一条
    await app_client.post(
        "/api/admin/bot/queue",
        json={"artwork_id": sample_artwork.id},
    )
    resp = await app_client.get("/api/admin/bot/queue")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_delete_queue_item(app_client, sample_artwork):
    """DELETE /api/admin/bot/queue/{id} 应删除队列条目。"""
    create_resp = await app_client.post(
        "/api/admin/bot/queue",
        json={"artwork_id": sample_artwork.id},
    )
    item_id = create_resp.json()["id"]

    resp = await app_client.delete(f"/api/admin/bot/queue/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_pop_queue(app_client, sample_artwork):
    """POST /api/admin/bot/queue/pop 应取出并标记下一条。"""
    # 先添加
    await app_client.post(
        "/api/admin/bot/queue",
        json={"artwork_id": sample_artwork.id},
    )
    resp = await app_client.post("/api/admin/bot/queue/pop")
    assert resp.status_code == 200
    body = resp.json()
    # 可能返回 null（如果没有 pending 的）或队列条目
    if body is not None:
        assert body["status"] == "processing"


@pytest.mark.asyncio
async def test_today_post_count(app_client):
    """GET /api/admin/bot/post-logs/today-count 应返回今日发布数。"""
    resp = await app_client.get("/api/admin/bot/post-logs/today-count")
    assert resp.status_code == 200
    body = resp.json()
    assert "count" in body
    assert body["count"] >= 0


@pytest.mark.asyncio
async def test_update_channel_not_found(app_client):
    """更新不存在的频道应返回 404。"""
    resp = await app_client.put(
        "/api/admin/bot/channels/99999",
        json={"name": "X"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_channel_not_found(app_client):
    """删除不存在的频道应返回 404。"""
    resp = await app_client.delete("/api/admin/bot/channels/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_setting_by_key(app_client):
    """GET /api/admin/bot/settings/{key} 应返回指定设置。"""
    # 先设置一个 key
    await app_client.put(
        "/api/admin/bot/settings",
        json={"settings": {"queue_interval_minutes": "90"}},
    )
    resp = await app_client.get("/api/admin/bot/settings/queue_interval_minutes")
    assert resp.status_code == 200
    body = resp.json()
    assert body["key"] == "queue_interval_minutes"
    assert body["value"] == "90"


@pytest.mark.asyncio
async def test_get_setting_not_found(app_client):
    """获取不存在的设置应返回 404。"""
    resp = await app_client.get("/api/admin/bot/settings/nonexistent_key")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_queue_priority(app_client, sample_artwork):
    """PATCH /api/admin/bot/queue/{id} 应更新优先级。"""
    create_resp = await app_client.post(
        "/api/admin/bot/queue",
        json={"artwork_id": sample_artwork.id, "priority": 100},
    )
    item_id = create_resp.json()["id"]

    resp = await app_client.patch(
        f"/api/admin/bot/queue/{item_id}",
        json={"priority": 10},
    )
    assert resp.status_code == 200
    assert resp.json()["priority"] == 10


@pytest.mark.asyncio
async def test_update_queue_priority_not_found(app_client):
    """更新不存在的队列条目优先级应返回 404。"""
    resp = await app_client.patch(
        "/api/admin/bot/queue/99999",
        json={"priority": 10},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_mark_queue_done(app_client, sample_artwork):
    """POST /api/admin/bot/queue/{id}/done 应标记为完成。"""
    create_resp = await app_client.post(
        "/api/admin/bot/queue",
        json={"artwork_id": sample_artwork.id},
    )
    item_id = create_resp.json()["id"]
    # 先 pop 使其变为 processing
    await app_client.post("/api/admin/bot/queue/pop")

    resp = await app_client.post(f"/api/admin/bot/queue/{item_id}/done")
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"


@pytest.mark.asyncio
async def test_mark_queue_failed(app_client, sample_artwork):
    """POST /api/admin/bot/queue/{id}/failed 应标记为失败。"""
    create_resp = await app_client.post(
        "/api/admin/bot/queue",
        json={"artwork_id": sample_artwork.id},
    )
    item_id = create_resp.json()["id"]

    resp = await app_client.post(f"/api/admin/bot/queue/{item_id}/failed")
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"


@pytest.mark.asyncio
async def test_get_next_times(app_client, sample_artwork):
    """GET /api/admin/bot/queue/next-times 应返回预计发布时间。"""
    # 先设置间隔 & 添加队列项
    await app_client.put(
        "/api/admin/bot/settings",
        json={"settings": {"queue_interval_minutes": "60"}},
    )
    await app_client.post(
        "/api/admin/bot/queue",
        json={"artwork_id": sample_artwork.id},
    )

    resp = await app_client.get("/api/admin/bot/queue/next-times")
    assert resp.status_code == 200
    body = resp.json()
    assert "times" in body
    assert "interval_minutes" in body
    assert "pending_count" in body
    assert body["pending_count"] >= 1


@pytest.mark.asyncio
async def test_get_next_times_empty(app_client):
    """无 pending 队列时 times 应为空。"""
    resp = await app_client.get("/api/admin/bot/queue/next-times")
    assert resp.status_code == 200
    body = resp.json()
    assert body["times"] == []
    assert body["pending_count"] == 0


@pytest.mark.asyncio
async def test_resolve_channel(app_client, sample_artwork, sample_channel):
    """POST /api/admin/bot/channels/resolve 应返回匹配的频道。"""
    resp = await app_client.post(
        "/api/admin/bot/channels/resolve",
        json={"artwork_id": sample_artwork.id, "platform": "telegram"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # 应匹配 sample_channel（is_default=True）
    if body is not None:
        assert "channel_id" in body


@pytest.mark.asyncio
async def test_resolve_channel_artwork_not_found(app_client):
    """作品不存在时 resolve 应返回 404。"""
    resp = await app_client.post(
        "/api/admin/bot/channels/resolve",
        json={"artwork_id": 99999, "platform": "telegram"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_to_queue_artwork_not_found(app_client):
    """添加不存在的作品到队列应返回 404。"""
    resp = await app_client.post(
        "/api/admin/bot/queue",
        json={"artwork_id": 99999},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_queue_not_found(app_client):
    """删除不存在的队列条目应返回 404。"""
    resp = await app_client.delete("/api/admin/bot/queue/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_post_logs_filter(app_client, sample_post_log):
    """按 artwork_id 过滤发布日志。"""
    resp = await app_client.get(
        "/api/admin/bot/post-logs",
        params={"artwork_id": sample_post_log.artwork_id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    for log in body["data"]:
        assert log["artwork_id"] == sample_post_log.artwork_id


@pytest.mark.asyncio
async def test_pop_queue_empty(app_client):
    """空队列 pop 应返回 null。"""
    resp = await app_client.post("/api/admin/bot/queue/pop")
    assert resp.status_code == 200
    assert resp.json() is None
