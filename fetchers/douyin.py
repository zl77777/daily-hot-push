"""
抖音热榜 + 热门博主内容抓取

数据来源:
  1. 天行数据 - 抖音热榜 API (需要 TIANAPI_KEY)
  2. 第三方聚合 - 各平台热词
  3. KOL 内容 - 通过抖音开放平台 / 第三方追踪
"""
import asyncio
import hashlib
import json
import time

import aiohttp

from .base import Article, BaseFetcher
from config import Config, DOUYIN_APIS, DOUYIN_KOL_LIST


class DouyinFetcher(BaseFetcher):

    def __init__(self, config: Config):
        self.tianapi_key = config.tianapi_key
        self.kol_list = DOUYIN_KOL_LIST

    async def fetch(self) -> list[Article]:
        articles: list[Article] = []

        # 1. 抖音热榜
        hot = await self._fetch_hot_list()
        articles.extend(hot)
        print(f"  [抖音] 热榜获取 {len(hot)} 条")

        # 2. 热门博主最新动态 (通过搜索/聚合)
        kol = await self._fetch_kol_content()
        articles.extend(kol)
        print(f"  [抖音] KOL 内容获取 {len(kol)} 条")

        return articles

    # -------------------------------------------------------
    # 抖音热榜
    # -------------------------------------------------------
    async def _fetch_hot_list(self) -> list[Article]:
        """从多个渠道拉取抖音热榜，合并去重"""
        results: list[Article] = []

        # 渠道1: 天行数据抖音热榜 API
        if self.tianapi_key:
            items = await self._fetch_tianapi_hot()
            results.extend(items)

        # 渠道2: 备用聚合（不需要 API key）
        backup = await self._fetch_backup_hot()
        results.extend(backup)

        return self._dedup_by_title(results)[:30]

    async def _fetch_tianapi_hot(self) -> list[Article]:
        """天行数据 - 抖音热榜"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://apis.tianapi.com/douyinhot/index",
                    params={"key": self.tianapi_key},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()
        except Exception:
            return []

        if data.get("code") != 200:
            return []

        articles: list[Article] = []
        for item in data.get("result", {}).get("list", []):
            title = item.get("word", "").strip()  # 热搜词
            if not title:
                continue
            hot_val = item.get("hot_value", 0)
            rank = item.get("rank", "")
            articles.append(Article(
                title=title if not rank else f"[热榜#{rank}] {title}",
                url=f"https://www.douyin.com/search/{title}",
                source="抖音热榜",
                category="douyin",
                summary=f"🔥 热度: {hot_val}  — 抖音实时热点",
            ))
        return articles

    async def _fetch_backup_hot(self) -> list[Article]:
        """备用热榜接口 (多个免费聚合源)"""
        urls = [
            # 今日热榜聚合 - 抖音榜
            "https://tenapi.cn/v2/douyinhot",
            # 其他免费接口
            "https://api.vvhan.com/api/hotlist/douyinHot",
        ]
        articles: list[Article] = []

        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                        data = await resp.json()
                except Exception:
                    continue

                for item in self._extract_items(data):
                    title = item.get("title", "") or item.get("name", "") or item.get("word", "")
                    if not title:
                        continue
                    articles.append(Article(
                        title=title.strip(),
                        url=item.get("url", f"https://www.douyin.com/search/{title}"),
                        source="抖音热榜",
                        category="douyin",
                        summary=f"抖音热搜: {title}",
                    ))
            return articles

    def _extract_items(self, data) -> list[dict]:
        """兼容不同 API 返回格式"""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("data", "list", "result", "hotList"):
                val = data.get(key)
                if isinstance(val, list):
                    return val
                if isinstance(val, dict):
                    inner = val.get("list") or val.get("items")
                    if isinstance(inner, list):
                        return inner
        return []

    # -------------------------------------------------------
    # KOL 博主内容 (通过不同渠道追踪)
    # -------------------------------------------------------
    async def _fetch_kol_content(self) -> list[Article]:
        """
        追踪热门博主最新动态

        方案:
          - 有抖音开放平台权限 → 调用 content/video/list 接口
          - 无权限 → 通过天行/聚合平台的创作者接口
          - 备选 → 通过 RSSHub/社交媒体聚合

        这里实现"聚合搜索"方案：用搜索 API 拉取每个博主最近的相关内容
        """
        if not self.kol_list:
            return []

        # 并发查询每个博主的最新相关话题
        async with aiohttp.ClientSession() as session:
            tasks = [self._search_kol_topics(session, kol) for kol in self.kol_list]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        articles: list[Article] = []
        for res in results:
            if isinstance(res, list):
                articles.extend(res)
        return articles

    async def _search_kol_topics(self, session: aiohttp.ClientSession, kol: dict) -> list[Article]:
        """
        通过"搜索API"反向获取某个博主/话题的最新动态

        不使用私密 API，而是利用：
        1. 各平台的热搜/搜索接口
        2. 谷歌/必应搜索 (site:douyin.com + 博主名)
        3. 微信指数 / 百度指数等替代数据
        """
        # 这里用 天行数据 "全网热搜" 接口，按关键词搜索
        if not self.tianapi_key:
            return []

        try:
            async with session.get(
                "https://apis.tianapi.com/networkhot/index",
                params={"key": self.tianapi_key, "word": kol["name"]},
                timeout=aiohttp.ClientTimeout(total=8),
            ) as resp:
                data = await resp.json()
        except Exception:
            return []

        if data.get("code") != 200:
            return []

        articles: list[Article] = []
        for item in data.get("result", {}).get("list", [])[:3]:
            title = item.get("title", "").strip()
            url = item.get("url", "")
            if not title:
                continue
            articles.append(Article(
                title=f"[{kol['name']}] {title}",
                url=url,
                source=f"抖音·{kol['name']}",
                category=kol.get("cat", "douyin"),
                summary=f"来自抖音博主 {kol['name']} 的相关热点",
            ))

        # 补充说明：实际使用时，建议通过以下方式获取更精准的抖音KOL内容：
        # 1. 抖音开放平台 - content/video/list API (需审核)
        # 2. 新榜 / 飞瓜数据 - 抖音KOL监测 (付费)
        # 3. RSSHub - 自建抖音博主RSS (开源免费)

        return articles

    # -------------------------------------------------------
    # 工具方法
    # -------------------------------------------------------
    @staticmethod
    def _dedup_by_title(articles: list[Article]) -> list[Article]:
        seen = set()
        result: list[Article] = []
        for a in articles:
            # 归一化标题做去重
            key = "".join(c for c in a.title if c.isalnum())
            if key not in seen:
                seen.add(key)
                result.append(a)
        return result
