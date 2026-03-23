"""外部以图搜图服务 — SauceNAO + IQDB。"""

import asyncio
import logging
import re
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ReverseSearchResult:
    source_url: str
    similarity: float  # 0-100
    platform: str  # "pixiv", "twitter", "danbooru", etc.
    title: str = ""
    author: str = ""
    thumb_url: str = ""
    provider: str = ""  # "saucenao" or "iqdb"


# URL 域名 → platform 映射（用于从 ext_urls / source 字段推断平台）
_URL_PLATFORM_MAP: dict[str, str] = {
    "pixiv.net": "pixiv",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "danbooru.donmai.us": "danbooru",
    "gelbooru.com": "gelbooru",
    "yande.re": "yandere",
    "deviantart.com": "deviantart",
    "anime-pictures.net": "anime-pictures",
    "kemono.su": "kemono",
    "skeb.jp": "skeb",
}


def _platform_from_url(url: str) -> str:
    """从 URL 推断平台名。"""
    for domain, plat in _URL_PLATFORM_MAP.items():
        if domain in url:
            return plat
    return "other"


async def search_saucenao(
    image_data: bytes,
    api_key: str,
    min_similarity: float = 70.0,
) -> list[ReverseSearchResult]:
    """SauceNAO search. Returns results sorted by similarity."""
    if not api_key:
        return []

    results: list[ReverseSearchResult] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                "https://saucenao.com/search.php",
                data={"output_type": "2", "numres": "8", "api_key": api_key},
                files={"file": ("image.jpg", image_data, "image/jpeg")},
            )
            resp.raise_for_status()
        except Exception:
            logger.warning("SauceNAO request failed", exc_info=True)
            return []

    data = resp.json()
    for item in data.get("results", []):
        header = item.get("header", {})
        body = item.get("data", {})
        similarity = float(header.get("similarity", 0))
        if similarity < min_similarity:
            continue

        title = body.get("title", "")
        author = body.get("member_name", "") or body.get("creator", "")
        thumb_url = header.get("thumbnail", "")
        seen_urls: set[str] = set()

        # 收集所有候选 URL：pixiv_id > source 字段 > ext_urls
        candidate_urls: list[str] = []

        # pixiv_id 直接构造标准 URL（最可靠）
        if body.get("pixiv_id"):
            candidate_urls.append(f"https://www.pixiv.net/artworks/{body['pixiv_id']}")

        # data.source 字段：booru 结果中通常是原始来源（如 pixiv URL）
        source_field = body.get("source", "")
        if isinstance(source_field, str) and source_field.startswith("http"):
            candidate_urls.append(source_field)

        # ext_urls：SauceNAO 提供的所有外部链接
        candidate_urls.extend(body.get("ext_urls", []))

        for url in candidate_urls:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            platform = _platform_from_url(url)
            results.append(
                ReverseSearchResult(
                    source_url=url,
                    similarity=similarity,
                    platform=platform,
                    title=title,
                    author=author,
                    thumb_url=thumb_url,
                    provider="saucenao",
                )
            )

    results.sort(key=lambda r: r.similarity, reverse=True)
    return results


# IQDB HTML parsing patterns
_IQDB_SIMILARITY_RE = re.compile(r"(\d+)% similarity")
_IQDB_LINK_RE = re.compile(r'<a href="(//[^"]+)"')

# 需要过滤掉的搜索引擎域名（IQDB 结果中常混入 "Search on SauceNAO" 等链接）
_IQDB_SKIP_DOMAINS = {"saucenao.com", "iqdb.org", "google.com", "tineye.com"}


async def search_iqdb(
    image_data: bytes,
    min_similarity: float = 70.0,
) -> list[ReverseSearchResult]:
    """IQDB search via HTML scraping."""
    results: list[ReverseSearchResult] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                "https://iqdb.org/",
                files={"file": ("image.jpg", image_data, "image/jpeg")},
            )
            resp.raise_for_status()
        except Exception:
            logger.warning("IQDB request failed", exc_info=True)
            return []

    html = resp.text
    # Split by table rows — each result is in a <table> block
    blocks = html.split("<table>")[1:]  # skip header

    for block in blocks:
        sim_match = _IQDB_SIMILARITY_RE.search(block)
        if not sim_match:
            continue
        similarity = float(sim_match.group(1))
        if similarity < min_similarity:
            continue

        # 遍历 block 内所有链接，跳过搜索引擎域名
        url = ""
        for link_path in _IQDB_LINK_RE.findall(block):
            candidate = "https:" + link_path
            if any(d in candidate for d in _IQDB_SKIP_DOMAINS):
                continue
            url = candidate
            break

        if not url:
            continue

        platform = _platform_from_url(url)

        results.append(
            ReverseSearchResult(
                source_url=url,
                similarity=similarity,
                platform=platform,
                provider="iqdb",
            )
        )

    results.sort(key=lambda r: r.similarity, reverse=True)
    return results


async def reverse_search(
    image_data: bytes,
    api_key: str = "",
    min_similarity: float = 70.0,
) -> list[ReverseSearchResult]:
    """统一入口: SauceNAO + IQDB 并行搜索，合并去重。"""
    tasks: list[asyncio.Task[list[ReverseSearchResult]]] = []
    if api_key:
        tasks.append(asyncio.create_task(search_saucenao(image_data, api_key, min_similarity)))
    tasks.append(asyncio.create_task(search_iqdb(image_data, min_similarity)))

    all_results = await asyncio.gather(*tasks)

    # 合并并按 source_url 去重（保留相似度更高的）
    best: dict[str, ReverseSearchResult] = {}
    for batch in all_results:
        for r in batch:
            existing = best.get(r.source_url)
            if not existing or r.similarity > existing.similarity:
                best[r.source_url] = r

    results = sorted(best.values(), key=lambda r: r.similarity, reverse=True)
    return results
