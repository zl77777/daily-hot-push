"""
市场情绪数据抓取

提供 AI 分析时需要的市场上下文:
  - 恐贪指数 (Fear & Greed)
  - 关键股指
  - VIX 恐慌指数
  - 加密货币行情
"""
import asyncio

import aiohttp


class MarketDataFetcher:
    """抓取市场情绪与行情快照，作为 AI 分析的上下文"""

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None

    async def fetch_context(self) -> dict:
        """返回市场情绪快照，直接注入 AI prompt"""
        async with aiohttp.ClientSession() as session:
            self.session = session
            fear_greed, global_idx, crypto = await asyncio.gather(
                self._fear_greed(),
                self._global_indices(),
                self._crypto_snapshot(),
                return_exceptions=True,
            )

        return {
            "fear_greed": fear_greed if not isinstance(fear_greed, Exception) else {},
            "global_indices": global_idx if not isinstance(global_idx, Exception) else {},
            "crypto": crypto if not isinstance(crypto, Exception) else {},
        }

    # -------------------------------------------------------
    # 恐贪指数 (Alternative.me)
    # -------------------------------------------------------
    async def _fear_greed(self) -> dict:
        try:
            async with self.session.get(
                "https://api.alternative.me/fng/?limit=2",
                timeout=aiohttp.ClientTimeout(total=8),
            ) as resp:
                data = await resp.json()
            items = data.get("data", [])
            if not items:
                return {}
            latest = items[0]
            val = int(latest.get("value", 50))
            label = latest.get("value_classification", "neutral")
            return {
                "now": val,
                "label": label,
                "signal": "extreme_fear" if val < 25 else ("fear" if val < 45 else ("greed" if val > 55 else ("extreme_greed" if val > 75 else "neutral"))),
            }
        except Exception:
            return {}

    # -------------------------------------------------------
    # 全球关键指数快照 (雅虎财经)
    # -------------------------------------------------------
    async def _global_indices(self) -> dict:
        symbols = {
            "上证": "000001.SS",
            "恒生": "^HSI",
            "标普500": "^GSPC",
            "纳指": "^IXIC",
            "日经": "^N225",
        }
        result = {}
        for name, sym in symbols.items():
            try:
                async with self.session.get(
                    f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                    params={"range": "1d", "interval": "1d"},
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as resp:
                    data = await resp.json()
                quote = (
                    data.get("chart", {})
                    .get("result", [{}])[0]
                    .get("meta", {})
                )
                prev = quote.get("previousClose", 0)
                cur = quote.get("regularMarketPrice", 0)
                chg_pct = ((cur - prev) / prev * 100) if prev else 0
                result[name] = {
                    "price": round(cur, 2),
                    "change_pct": round(chg_pct, 2),
                    "direction": "up" if chg_pct > 0 else ("down" if chg_pct < 0 else "flat"),
                }
            except Exception:
                continue
        return result

    # -------------------------------------------------------
    # 加密货币快照
    # -------------------------------------------------------
    async def _crypto_snapshot(self) -> dict:
        try:
            async with self.session.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={
                    "ids": "bitcoin,ethereum",
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                },
                timeout=aiohttp.ClientTimeout(total=8),
            ) as resp:
                data = await resp.json()
            out = {}
            for coin, info in data.items():
                out[coin] = {
                    "price": info.get("usd", 0),
                    "change_24h": round(info.get("usd_24h_change", 0), 2),
                }
            return out
        except Exception:
            return {}
