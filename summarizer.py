"""
AI 摘要整理模块

把抓取到的几十条原始新闻 → AI 分类、去重、提炼 → 输出结构化日报

支持多 AI 后端: Claude / OpenAI / 千问 / DeepSeek
"""
import json
import asyncio

import aiohttp

from config import Config, MAX_ITEMS_PER_CATEGORY
from fetchers.base import Article


# AI API 地址映射
API_ENDPOINTS = {
    "claude":   "https://api.anthropic.com/v1/messages",
    "openai":   "https://api.openai.com/v1/chat/completions",
    "qwen":     "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/v1/chat/completions",
}

SUMMARIZE_PROMPT = """你是一名资深财经编辑，请将以下今日全球热点新闻整理成一份信息简报。

## 要求
1. 按四类整理：🔴金融市场 / 🔵科技&AI / 🟢大宗商品&农业 / 🟡抖音热门
2. 每类选取最重要的 3-8 条
3. 每一条格式：
   • **{标题}** — {一句话要点概括（20字以内）}  [来源](链接)
4. 如果发现多条新闻讲同一事件，只保留一条，注明多个来源
5. 末尾加一个「📊 今日简报」区块（3-4句话总结今日核心矛盾/主线）
6. 去重：相同或高度相似的新闻只保留一条
7. 只输出 Markdown，不要引言和结语
8. 抖音热门类，注意提炼出"为什么火"和"背后反映了什么"

## 原始新闻列表
{articles_json}

## 输出格式示例

### 🔴 金融市场
• **美联储暗示6月降息** — 市场押注年内两次降息概率升至70%  [Bloomberg](url)
• ...

### 🔵 科技 & AI
• ...

### 🟢 大宗商品 & 农业
• ...

### 🟡 抖音热门话题
• **{热门话题标题}** — {背后反映的趋势}  [抖音](搜索链接)

---

📊 **今日简报**
今日市场主线围绕XXX展开。一方面...另一方面...展望后续...
"""


class AISummarizer:
    """调用 AI 做新闻摘要整理"""

    def __init__(self, config: Config):
        self.provider = config.ai_provider
        self.api_key = config.ai_api_key
        self.model = config.ai_model

    async def summarize(self, articles: list[Article]) -> str:
        if not self.api_key:
            return self._fallback_summary(articles)

        # 预分类 + 截断，减少 token 消耗
        grouped = self._pre_group(articles)
        articles_json = json.dumps(
            [a.to_dict() for a in articles],
            ensure_ascii=False,
            indent=2,
        )

        prompt = SUMMARIZE_PROMPT.format(articles_json=articles_json)

        try:
            return await self._call_ai(prompt)
        except Exception as e:
            print(f"  [AI] 调用失败: {e}，回退到模板化摘要")
            return self._fallback_summary(articles)

    async def _call_ai(self, prompt: str) -> str:
        """统一调用不同 AI API"""
        url = API_ENDPOINTS.get(self.provider)

        if self.provider == "claude":
            return await self._call_claude(url, prompt)
        else:
            return await self._call_openai_compat(url, prompt)

    async def _call_claude(self, url: str, prompt: str) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                data = await resp.json()
        return data["content"][0]["text"]

    async def _call_openai_compat(self, url: str, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                data = await resp.json()
        return data["choices"][0]["message"]["content"]

    # -------------------------------------------------------
    # 降级方案：不调用 AI，直接用模板拼装
    # -------------------------------------------------------
    @staticmethod
    def _fallback_summary(articles: list[Article]) -> str:
        """如果 AI 不可用，按分类模板输出"""
        from collections import defaultdict
        groups: dict[str, list[Article]] = defaultdict(list)
        for a in articles:
            cat = a.category
            if cat in ("finance", "tech", "agriculture"):
                groups[cat].append(a)
            elif cat in ("douyin", "douyin_hot", "douyin_finance"):
                groups["douyin"].append(a)
            else:
                groups["other"].append(a)

        emoji = {
            "finance": "🔴 金融市场",
            "tech": "🔵 科技 & AI",
            "agriculture": "🟢 大宗商品 & 农业",
            "douyin": "🟡 抖音热门话题",
            "other": "⚪ 其他重要事件",
        }

        lines = ["# 🌍 今日全球热点速览\n"]
        for cat, label in emoji.items():
            items = groups.get(cat, [])
            if not items:
                continue
            limit = MAX_ITEMS_PER_CATEGORY.get(cat, 5)
            lines.append(f"### {label}")
            for a in items[:limit]:
                summary_snippet = a.summary[:60].replace("\n", " ") if a.summary else ""
                lines.append(f"• **{a.title}** — {summary_snippet}  [{a.source}]({a.url})")
            lines.append("")

        lines.append("> 📊 今日简报：数据由 AI 自动聚合生成（AI 未配置，展示原始摘要）")
        return "\n".join(lines)

    # -------------------------------------------------------
    # 预分组（传给 AI 时带上分类提示）
    # -------------------------------------------------------
    @staticmethod
    def _pre_group(articles: list[Article]) -> dict[str, int]:
        from collections import Counter
        return Counter(a.category for a in articles)
