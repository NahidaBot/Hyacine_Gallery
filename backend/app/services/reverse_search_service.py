"""外部以图搜图服务 — SauceNAO + IQDB。"""

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


# SauceNAO index → platform mapping
_SAUCENAO_INDEX_MAP: dict[int, str] = {
    5: "pixiv",  # Pixiv
    9: "danbooru",
    12: "yandere",
    25: "gelbooru",
    34: "deviantart",
    37: "anime-pictures",
    38: "e-hentai",
    40: "nhentai",
    41: "twitter",
    43: "kemono",
}


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

        index_id = header.get("index_id", 0)
        platform = _SAUCENAO_INDEX_MAP.get(index_id, "other")
        ext_urls = body.get("ext_urls", [])
        source_url = ext_urls[0] if ext_urls else ""

        # Try to get better source for pixiv
        if body.get("pixiv_id"):
            source_url = f"https://www.pixiv.net/artworks/{body['pixiv_id']}"
            platform = "pixiv"

        results.append(
            ReverseSearchResult(
                source_url=source_url,
                similarity=similarity,
                platform=platform,
                title=body.get("title", ""),
                author=body.get("member_name", "") or body.get("creator", ""),
                thumb_url=header.get("thumbnail", ""),
                provider="saucenao",
            )
        )

    results.sort(key=lambda r: r.similarity, reverse=True)
    return results


# IQDB HTML parsing patterns
_IQDB_SIMILARITY_RE = re.compile(r"(\d+)% similarity")
_IQDB_LINK_RE = re.compile(r'<a href="(//[^"]+)"')

_IQDB_DOMAIN_MAP: dict[str, str] = {
    "danbooru.donmai.us": "danbooru",
    "yande.re": "yandere",
    "gelbooru.com": "gelbooru",
    "anime-pictures.net": "anime-pictures",
    "e-shuushuu.net": "e-shuushuu",
    "konachan.com": "konachan",
}


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

        link_match = _IQDB_LINK_RE.search(block)
        if not link_match:
            continue
        url = "https:" + link_match.group(1)

        # Determine platform from URL domain
        platform = "other"
        for domain, plat in _IQDB_DOMAIN_MAP.items():
            if domain in url:
                platform = plat
                break

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
    """统一入口: 先 SauceNAO（有 key 时），再 IQDB fallback。"""
    results: list[ReverseSearchResult] = []

    if api_key:
        results = await search_saucenao(image_data, api_key, min_similarity)
        if results:
            return results

    iqdb_results = await search_iqdb(image_data, min_similarity)
    return iqdb_results
