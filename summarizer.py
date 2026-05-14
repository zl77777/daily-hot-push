"""
AI 深度分析模块

不做信息罗列，而是做交叉分析和深层洞察。

两个视角:
  视角A — 金融从业者: 市场主线、资金流向、风险信号、预期差
  视角B — 互联网冲浪人: 流行趋势、情绪变化、文化现象、出圈事件
"""
import json

import aiohttp

from config import Config

API_ENDPOINTS = {
    "claude":   "https://api.anthropic.com/v1/messages",
    "openai":   "https://api.openai.com/v1/chat/completions",
    "qwen":     "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/v1/chat/completions",
}

DEEP_ANALYSIS_PROMPT = """你叫老猫，是一个做了十五年财经记者的自由撰稿人。你不为任何机构写报告，你写的每篇文章只有一个标准：**朋友看完会转发给另一个朋友**。

你的读者不是"投资者"或"互联网从业者"——他们是聪明但对金融术语没耐心的人。他们想知道的是：**今天到底发生了什么真正重要的事？为什么？跟我有什么关系？**

---

## 写作铁律

1. **每段开头必须有具体数字或具体名字**。不要写"市场下跌"，写"标普跌了1.2%，但真正疼的是纳指里的二线SaaS——它们的平均跌幅是4.7%。"
2. **每解释一件事，用一个比喻**。复杂的事情用日常生活打比方。把"信用利差走阔"说成"借钱的人要多付利息了，银行开始挑客户了"。
3. **敢于下判断**。不要写"可能""或许""值得关注"。写"这就是。"或"不对，真正的逻辑是..."。错了就错了，但不能含混。
4. **短句**。超过25个字就断。一段不超过3句话。
5. **去掉所有AI腔**。不许出现：值得注意的是、综上所述、一方面另一方面、首先其次最后、在某种程度上、从某种意义上说。
6. **网感**。可以用"说白了""你品""这波""翻一下就是""细思恐极"这种口语。但不要滥用，一篇文章最多两处。

---

## 素材

### 市场情绪
__MARKET_CONTEXT__

### 今天的新闻
__NEWS_STREAM__

### 大家在搜什么
__SOCIAL_STREAM__

---

## 输出结构

# 今天，有件事不对劲
（用一段话，最多4句，讲今天最让你觉得意外/矛盾/反常的一件事。不要概括全天——就抓一个瞬间、一个数字、一个对比。让读者觉得"嗯？什么情况？"然后不得不往下看。）

---

# 三件事，值得展开说

## 第一件：【起一个有信息量的标题，不要用"XX发生"这种——用"XX背后，其实是YY"】

**发生了什么（≤2句）**

**真正的逻辑是什么（≤4句）**
换一个角度解释这件事。大多数报道说的是A，但其实B才是关键。给出你的判断。用数据支撑。

**往后看，盯一个指标（≤1句）**
告诉读者，接下来如果看到X，就说明Y。具体、可验证。

---

## 第二件：【同上格式】

（同上）

---

## 第三件：【同上格式】

（同上）

---

# 还有个事，今天没人聊但我注意到了
（1-2句话，指出一个被忽略的信息、一个异常的沉默、或者一个刚刚冒头的小趋势。让人觉得"有意思，之前没想到"。）

---

# 一个数字
（选今天最震撼你的一组数据，单独列出来。可以是涨幅、金额、人数、排名。写一行解释为什么这个数字重要。）

---

# 明天盯什么
（≤3条，每条≤20字。极简，给读者一个用来验证明天的checklist。）

---

## 铁律（违反一条，整篇作废）

1. **不编造**。素材里没有的公司名、人名、数字、事件——一个都不许出现。如果素材不够支撑三件事，就只写两件。宁可短，不能假。
2. **每段有数字**。不是"大幅上涨"，是"涨了33%"。不是"很多人讨论"，是"微博热搜第3位，280万热度"。没有数字的观察 = 废话。
3. **有判断**。不光说发生了什么，还要说这意味着什么。错了没关系，不敢判断不行。
4. **短句**。一句话超过25个字就断开。一段不超过4句。
5. **禁用AI腔**。这些词全都不能出现：值得注意的是 / 综上所述 / 一方面另一方面 / 首先其次最后 / 在某种程度上 / 从某种意义上说 / 可能或许 / 值得关注 / 引人深思。
6. **可以用的口语**（全文最多3处）：说白了 / 翻一下就是 / 你品 / 这波 / 细思恐极 / 有点意思。
7. **全文 ≤1500字**。完了就停。不写结尾套话。
8. **明天盯什么**只写素材里能验证的事。每条后面括号标注这条依据的是今天哪条素材。

输出纯 Markdown。不要签名。不要"以上是今日分析"。"""


class AISummarizer:

    def __init__(self, config: Config):
        self.provider = config.ai_provider
        self.api_key = config.ai_api_key
        self.model = config.ai_model

    async def summarize(
        self,
        news_articles: list,
        social_articles: list,
        market_context: dict,
    ) -> str:
        if not self.api_key:
            return self._fallback_summary(news_articles + social_articles)

        # 组装素材
        news_stream = self._format_articles(news_articles, max_items=30)
        social_stream = self._format_articles(social_articles, max_items=25)
        market_json = json.dumps(market_context, ensure_ascii=False, indent=2)

        prompt = (
            DEEP_ANALYSIS_PROMPT
            .replace("__MARKET_CONTEXT__", market_json)
            .replace("__NEWS_STREAM__", news_stream)
            .replace("__SOCIAL_STREAM__", social_stream)
        )

        try:
            return await self._call_ai(prompt)
        except Exception as e:
            print(f"  [AI] 调用失败: {e}，回退到模板")
            return self._fallback_summary(news_articles + social_articles)

    async def _call_ai(self, prompt: str) -> str:
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
            async with session.post(
                url, json=body, headers=headers,
                timeout=aiohttp.ClientTimeout(total=90),
            ) as resp:
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
            async with session.post(
                url, json=body, headers=headers,
                timeout=aiohttp.ClientTimeout(total=90),
            ) as resp:
                data = await resp.json()
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def _format_articles(articles: list, max_items: int) -> str:
        lines = []
        for a in articles[:max_items]:
            lines.append(f"- [{a.source}] {a.title}")
            if a.summary:
                # 提取摘要中的有用信息（过滤纯HTML或纯链接）
                clean = a.summary.strip()
                if clean and not clean.startswith("http"):
                    lines.append(f"  {clean[:250]}")
        return "\n".join(lines)

    @staticmethod
    def _fallback_summary(articles: list) -> str:
        from collections import defaultdict
        groups: dict[str, list] = defaultdict(list)
        for a in articles:
            cat = a.category[:20]
            groups[cat].append(a)

        lines = ["# 今日热点速览\n"]
        for cat, items in groups.items():
            lines.append(f"## {cat}")
            for a in items[:6]:
                s = a.summary[:80] if a.summary else ""
                lines.append(f"- **{a.title[:80]}** — {s}  [{a.source}]({a.url})")
            lines.append("")
        lines.append("> AI 深度分析未配置，展示原始聚合。配置 AI_API_KEY 获取洞察。")
        return "\n".join(lines)
