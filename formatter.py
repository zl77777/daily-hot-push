"""
内容排版模块

把 AI 摘要 + 原始数据 → 适配公众号消息格式

公众号文字消息限制:
  - 纯文本: 最多 2048 字节（约 680 个中文字）
  - 图文消息: 需要素材 media_id
  - 这里默认用"图文消息 + 纯文本摘要"双模式
"""
from datetime import datetime


def format_daily_report(ai_summary: str, date_str: str | None = None) -> str:
    """
    把 AI 整理的内容包装成公众号群发格式

    注意：纯文本最多 ~680 汉字，超过会被截断
    """
    today = date_str or datetime.now().strftime("%Y年%m月%d日")

    # 计算摘要长度，必要时截断
    max_chars = 600

    if len(ai_summary) > max_chars:
        # 智能截断：在最后一个完整段落处切割
        cutoff = ai_summary.rfind("\n", 0, max_chars)
        if cutoff < 100:
            cutoff = max_chars
        body = ai_summary[:cutoff] + "\n\n...\n> 📎 完整版请查看今日推送图文"
    else:
        body = ai_summary

    return f"""🌍 全球热点速递 | {today}

{body}

---
🤖 由 AI 自动聚合整理 | 内容仅供参考
📩 如需订阅，请回复「订阅」"""


def format_template_message(ai_summary: str, brief: str) -> dict:
    """
    服务号模板消息格式

    模板消息结构:
      first:   开头
      keyword1-5: 固定关键词
      remark:  结尾
    """
    lines = ai_summary.split("\n")
    sections: dict[str, str] = {}
    current_key = ""
    for line in lines:
        if line.startswith("###"):
            current_key = line.replace("###", "").strip()
            sections[current_key] = ""
        elif current_key:
            sections[current_key] += line + "\n"

    # 提取各分类摘要
    finance_brief = sections.get("🔴 金融市场", sections.get("🔴 金融市场\n", ""))[:100]
    tech_brief = sections.get("🔵 科技 & AI", "")[:100]
    agri_brief = sections.get("🟢 大宗商品 & 农业", "")[:100]

    return {
        "first":    {"value": f"📊 今日全球热点已更新", "color": "#173177"},
        "keyword1": {"value": finance_brief.strip() or "今日无重大事件", "color": "#d32f2f"},
        "keyword2": {"value": tech_brief.strip() or "今日无重大事件", "color": "#1976d2"},
        "keyword3": {"value": agri_brief.strip() or "今日无重大事件", "color": "#388e3c"},
        "keyword4": {"value": datetime.now().strftime("%Y-%m-%d %H:%M"), "color": "#666666"},
        "remark":   {"value": "点击查看完整日报 →", "color": "#173177"},
    }


def truncate_for_wechat_text(text: str, max_chars: int = 600) -> str:
    """微信文字消息有字数限制，按字符数截断"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 3] + "..."
