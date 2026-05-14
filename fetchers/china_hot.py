"""
中文互联网热点全量抓取

多源冗余: 一个源挂了自动切下一个
"""
import asyncio

import aiohttp

from .base import Article, BaseFetcher


class ChinaHotFetcher(BaseFetcher):
    """中文互联网全热点聚合 — 多源冗余"""

    async def fetch(self) -> list[Article]:
        articles: list[Article] = []

        async with aiohttp.ClientSession() as session:
            results = await asyncio.gather(
                self._weibo_hot(session),
                self._zhihu_hot(session),
                self._baidu_hot(session),
                self._cls_telegraph(session),
                return_exceptions=True,
            )

        names = ["微博", "知乎", "百度", "财联社"]
        for i, res in enumerate(results):
            if isinstance(res, list):
                if res:
                    print(f"  [{names[i]}] 获取 {len(res)} 条")
                articles.extend(res)
            elif isinstance(res, Exception):
                print(f"  [{names[i]}] 失败: {res}")

        return articles

    # -------------------------------------------------------
    # 微博热搜 — 官方接口
    # -------------------------------------------------------
    async def _weibo_hot(self, session: aiohttp.ClientSession) -> list[Article]:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://weibo.com",
            }
            async with session.get(
                "https://weibo.com/ajax/side/hotSearch",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
        except Exception:
            return await self._weibo_backup(session)

        items = []
        for item in data.get("data", {}).get("realtime", [])[:20]:
            word = (item.get("word") or item.get("word_scheme", "").strip("#")).strip()
            if not word:
                continue
            rank = item.get("realpos", "")
            hot = item.get("num", 0)
            hot_str = f"{hot/10000:.0f}万" if hot > 10000 else str(hot)
            items.append(Article(
                title=f"微博热搜#{rank}: {word}",
                url=f"https://s.weibo.com/weibo?q={word}",
                source="微博热搜",
                category="social",
                summary=f"微博实时热搜第{rank}位 热度{hot_str} — {item.get('note','')}",
            ))
        return items

    async def _weibo_backup(self, session: aiohttp.ClientSession) -> list[Article]:
        """备用微博热搜接口"""
        backup_urls = [
            "https://api.vvhan.com/api/hotlist/wbHot",
            "https://tenapi.cn/v2/weibohot",
        ]
        for url in backup_urls:
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    data = await resp.json()
                items = []
                lst = data if isinstance(data, list) else data.get("data", [])
                for item in lst[:20]:
                    title = (item.get("name") or item.get("title") or item.get("word", "")).strip()
                    if not title:
                        continue
                    items.append(Article(
                        title=f"微博热搜: {title}",
                        url=f"https://s.weibo.com/weibo?q={title}",
                        source="微博热搜",
                        category="social",
                        summary=f"微博实时热搜: {title}",
                    ))
                if items:
                    return items
            except Exception:
                continue
        return []

    # -------------------------------------------------------
    # 知乎热榜
    # -------------------------------------------------------
    async def _zhihu_hot(self, session: aiohttp.ClientSession) -> list[Article]:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.zhihu.com",
            }
            async with session.get(
                "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=15",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
        except Exception:
            return await self._zhihu_backup(session)

        items = []
        for item in data.get("data", [])[:15]:
            target = item.get("target", {})
            title = target.get("title", "").strip()
            url = target.get("url", "") or f"https://www.zhihu.com/question/{target.get('id','')}"
            if not title:
                continue
            metrics = target.get("metrics_text", "") or target.get("excerpt", "")
            items.append(Article(
                title=title,
                url=url,
                source="知乎热榜",
                category="social",
                summary=f"知乎热议 — {metrics}" if metrics else "知乎热议",
            ))
        return items

    async def _zhihu_backup(self, session: aiohttp.ClientSession) -> list[Article]:
        backup_urls = [
            "https://api.vvhan.com/api/hotlist/zhihuHot",
            "https://tenapi.cn/v2/zhihuhot",
        ]
        for url in backup_urls:
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    data = await resp.json()
                items = []
                lst = data if isinstance(data, list) else data.get("data", [])
                for item in lst[:15]:
                    title = (item.get("name") or item.get("title") or item.get("query", "")).strip()
                    if not title:
                        continue
                    items.append(Article(
                        title=title,
                        url=item.get("url", f"https://www.zhihu.com/search?q={title}"),
                        source="知乎热榜",
                        category="social",
                        summary=f"知乎热议: {title}",
                    ))
                if items:
                    return items
            except Exception:
                continue
        return []

    # -------------------------------------------------------
    # 百度热搜
    # -------------------------------------------------------
    async def _baidu_hot(self, session: aiohttp.ClientSession) -> list[Article]:
        backup_urls = [
            "https://api.vvhan.com/api/hotlist/baiduRD",
            "https://tenapi.cn/v2/baiduhot",
        ]
        for url in backup_urls:
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    data = await resp.json()
                items = []
                lst = data if isinstance(data, list) else data.get("data", [])
                for item in lst[:15]:
                    title = (item.get("name") or item.get("title") or item.get("word", "")).strip()
                    if not title:
                        continue
                    items.append(Article(
                        title=title,
                        url=f"https://www.baidu.com/s?wd={title}",
                        source="百度热搜",
                        category="social",
                        summary=f"百度实时热搜: {title}",
                    ))
                if items:
                    return items
            except Exception:
                continue
        return []

    # -------------------------------------------------------
    # 财联社快讯 (CLS Telegraph — RSS)
    # -------------------------------------------------------
    async def _cls_telegraph(self, session: aiohttp.ClientSession) -> list[Article]:
        """财联社电报 — 最快的金融市场快讯"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.cls.cn",
            }
            async with session.get(
                "https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=8.4.6",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
        except Exception:
            return []

        items = []
        for item in data.get("data", {}).get("roll_data", [])[:20]:
            title = item.get("title", "").strip()
            brief = item.get("brief", "").strip()
            if not title:
                continue
            display = brief[:100] if brief else title
            items.append(Article(
                title=title,
                url=f"https://www.cls.cn/detail/{item.get('id','')}",
                source="财联社",
                category="finance",
                summary=display,
            ))
        return items
