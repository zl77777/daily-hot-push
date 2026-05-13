"""NewsAPI 抓取"""
import asyncio
from datetime import datetime, timezone

import aiohttp

from .base import Article, BaseFetcher
from config import Config, NEWSAPI_CATEGORIES


class NewsAPIFetcher(BaseFetcher):

    BASE = "https://newsapi.org/v2/top-headlines"

    def __init__(self, config: Config):
        self.key = config.newsapi_key

    async def fetch(self) -> list[Article]:
        if not self.key:
            print("  [NewsAPI] ⚠️  未配置 NEWSAPI_KEY，跳过")
            return []

        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_category(session, cat) for cat in NEWSAPI_CATEGORIES]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        articles: list[Article] = []
        for res in results:
            if isinstance(res, list):
                articles.extend(res)

        # 按 category 合并到我们自己的分类
        cat_map = {"business": "finance", "technology": "tech", "general": "other"}
        for a in articles:
            a.category = cat_map.get(a.category, a.category)

        return articles

    async def _fetch_category(self, session: aiohttp.ClientSession, category: str) -> list[Article]:
        try:
            async with session.get(
                self.BASE,
                params={"category": category, "apiKey": self.key, "pageSize": 15},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
        except Exception:
            return []

        if data.get("status") != "ok":
            return []

        articles: list[Article] = []
        for item in data.get("articles", []):
            title = (item.get("title") or "").strip()
            url = (item.get("url") or "").strip()
            if not title or not url:
                continue

            articles.append(Article(
                title=title,
                url=url,
                source=item.get("source", {}).get("name", "NewsAPI"),
                category=category,
                summary=(item.get("description") or "")[:300],
                published_at=item.get("publishedAt", ""),
            ))

        return articles
