"""reverse_search_service 单元测试。"""

import httpx
import respx

from app.services.reverse_search_service import (
    reverse_search,
    search_iqdb,
    search_saucenao,
)

_FAKE_IMAGE = b"\xff\xd8\xff\xe0" + b"\x00" * 100


# ── SauceNAO ──


@respx.mock
async def test_search_saucenao_success():
    """SauceNAO 应正确解析返回结果。"""
    respx.post("https://saucenao.com/search.php").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "header": {
                            "similarity": "92.5",
                            "index_id": 5,
                            "thumbnail": "https://img.saucenao.com/thumb.jpg",
                        },
                        "data": {
                            "ext_urls": ["https://www.pixiv.net/artworks/99999"],
                            "pixiv_id": 99999,
                            "title": "Test Artwork",
                            "member_name": "Test Artist",
                        },
                    }
                ]
            },
        )
    )
    results = await search_saucenao(_FAKE_IMAGE, "test-api-key")
    assert len(results) == 1
    r = results[0]
    assert r.source_url == "https://www.pixiv.net/artworks/99999"
    assert r.similarity == 92.5
    assert r.platform == "pixiv"
    assert r.title == "Test Artwork"
    assert r.author == "Test Artist"
    assert r.provider == "saucenao"


async def test_search_saucenao_no_key():
    """空 API key 应直接返回空列表。"""
    results = await search_saucenao(_FAKE_IMAGE, "")
    assert results == []


@respx.mock
async def test_search_saucenao_below_similarity():
    """低于阈值的结果应被过滤。"""
    respx.post("https://saucenao.com/search.php").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "header": {"similarity": "50.0", "index_id": 5, "thumbnail": ""},
                        "data": {
                            "ext_urls": ["https://example.com"],
                            "title": "Low Match",
                        },
                    }
                ]
            },
        )
    )
    results = await search_saucenao(_FAKE_IMAGE, "test-key", min_similarity=70.0)
    assert results == []


@respx.mock
async def test_search_saucenao_http_error():
    """HTTP 错误应返回空列表而非抛出异常。"""
    respx.post("https://saucenao.com/search.php").mock(return_value=httpx.Response(500))
    results = await search_saucenao(_FAKE_IMAGE, "test-key")
    assert results == []


# ── IQDB ──


@respx.mock
async def test_search_iqdb_success():
    """IQDB 应正确从 HTML 中解析结果。"""
    html = (
        "<html><body>"
        "<table>Header table</table>"
        '<table><a href="//danbooru.donmai.us/posts/12345">link</a>'
        "<br>85% similarity</table>"
        "</body></html>"
    )
    respx.post("https://iqdb.org/").mock(return_value=httpx.Response(200, text=html))
    results = await search_iqdb(_FAKE_IMAGE, min_similarity=70.0)
    assert len(results) == 1
    r = results[0]
    assert "danbooru.donmai.us" in r.source_url
    assert r.similarity == 85.0
    assert r.platform == "danbooru"
    assert r.provider == "iqdb"


@respx.mock
async def test_search_iqdb_no_match():
    """无匹配的 HTML 应返回空列表。"""
    html = "<html><body><table>No relevant results</table></body></html>"
    respx.post("https://iqdb.org/").mock(return_value=httpx.Response(200, text=html))
    results = await search_iqdb(_FAKE_IMAGE)
    assert results == []


@respx.mock
async def test_search_iqdb_http_error():
    """HTTP 错误应返回空列表。"""
    respx.post("https://iqdb.org/").mock(return_value=httpx.Response(500))
    results = await search_iqdb(_FAKE_IMAGE)
    assert results == []


# ── reverse_search 统一入口 ──


@respx.mock
async def test_reverse_search_with_key():
    """有 API key 时优先使用 SauceNAO。"""
    respx.post("https://saucenao.com/search.php").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "header": {"similarity": "90.0", "index_id": 41, "thumbnail": ""},
                        "data": {
                            "ext_urls": ["https://twitter.com/status/123"],
                            "title": "",
                            "creator": "artist",
                        },
                    }
                ]
            },
        )
    )
    # IQDB 不应被调用，但注册以防万一
    respx.post("https://iqdb.org/").mock(return_value=httpx.Response(200, text="<html></html>"))
    results = await reverse_search(_FAKE_IMAGE, api_key="my-key")
    assert len(results) == 1
    assert results[0].provider == "saucenao"


@respx.mock
async def test_reverse_search_no_key():
    """无 API key 时跳过 SauceNAO，使用 IQDB。"""
    html = (
        "<html><body>"
        "<table>Header</table>"
        '<table><a href="//yande.re/post/show/999">link</a>'
        "<br>80% similarity</table>"
        "</body></html>"
    )
    respx.post("https://iqdb.org/").mock(return_value=httpx.Response(200, text=html))
    results = await reverse_search(_FAKE_IMAGE, api_key="")
    assert len(results) == 1
    assert results[0].provider == "iqdb"
    assert results[0].platform == "yandere"
