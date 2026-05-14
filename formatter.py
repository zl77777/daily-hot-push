"""
内容排版模块 → 生成公众号图文 HTML
"""
import re
from datetime import datetime


def markdown_to_wechat_html(ai_summary: str) -> str:
    """
    把 AI 生成的 Markdown → 公众号文章 HTML

    公众号文章限制:
      - 只支持部分 HTML 标签: p, h1-h6, strong, em, a, img, blockquote, ul, ol, li, span, br, section
      - 样式必须内联 (inline style)
      - 不支持 class / id / script / iframe
    """
    lines = ai_summary.split("\n")
    html_lines = []
    in_list = False
    in_order_list = False

    for line in lines:
        stripped = line.strip()

        # 空行
        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if in_order_list:
                html_lines.append("</ol>")
                in_order_list = False
            html_lines.append("<p>&nbsp;</p>")
            continue

        # 标题
        if stripped.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if in_order_list:
                html_lines.append("</ol>")
                in_order_list = False
            text = stripped[4:]
            html_lines.append(
                f'<h3 style="font-size:18px;color:#1a1a1a;margin:20px 0 12px;padding-left:10px;border-left:4px solid #d32f2f;">'
                f"{_inline_format(text)}</h3>"
            )
            continue

        if stripped.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            text = stripped[3:]
            html_lines.append(
                f'<h2 style="font-size:20px;color:#1a1a1a;margin:24px 0 14px;text-align:center;">'
                f"{_inline_format(text)}</h2>"
            )
            continue

        # 分隔线
        if stripped == "---":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(
                '<hr style="border:none;border-top:1px solid #e0e0e0;margin:20px 0;">'
            )
            continue

        # 引用
        if stripped.startswith("> "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            text = stripped[2:]
            html_lines.append(
                f'<blockquote style="background:#f5f7fa;padding:10px 16px;margin:12px 0;border-left:3px solid #1976d2;color:#555;font-size:14px;">'
                f"{_inline_format(text)}</blockquote>"
            )
            continue

        # 无序列表
        if re.match(r"^[•\-\*]\s+", stripped):
            if in_order_list:
                html_lines.append("</ol>")
                in_order_list = False
            if not in_list:
                html_lines.append(
                    '<ul style="padding-left:20px;margin:8px 0;line-height:1.8;">'
                )
                in_list = True
            text = re.sub(r"^[•\-\*]\s+", "", stripped)
            html_lines.append(
                f'<li style="margin-bottom:6px;font-size:15px;color:#333;">'
                f"{_inline_format(text)}</li>"
            )
            continue

        # 有序列表
        if re.match(r"^\d+[\.\、]\s+", stripped):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if not in_order_list:
                html_lines.append(
                    '<ol style="padding-left:20px;margin:8px 0;line-height:1.8;">'
                )
                in_order_list = True
            text = re.sub(r"^\d+[\.\、]\s+", "", stripped)
            html_lines.append(
                f'<li style="margin-bottom:6px;font-size:15px;color:#333;">'
                f"{_inline_format(text)}</li>"
            )
            continue

        # 普通段落
        if in_list:
            html_lines.append("</ul>")
            in_list = False
        if in_order_list:
            html_lines.append("</ol>")
            in_order_list = False

        html_lines.append(
            f'<p style="font-size:15px;color:#333;line-height:1.8;margin:6px 0;">'
            f"{_inline_format(stripped)}</p>"
        )

    # 关闭未闭合的列表
    if in_list:
        html_lines.append("</ul>")
    if in_order_list:
        html_lines.append("</ol>")

    return "\n".join(html_lines)


def _inline_format(text: str) -> str:
    """处理行内格式: **粗体**, *斜体*, [链接](url), `代码`"""
    # 粗体
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # 斜体
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # 链接
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" style="color:#1976d2;">\1</a>',
        text,
    )
    # 行内代码
    text = re.sub(
        r"`([^`]+)`",
        r'<code style="background:#f0f0f0;padding:2px 6px;border-radius:3px;">\1</code>',
        text,
    )
    return text


def wrap_html_page(title: str, body_html: str, date_str: str = "") -> str:
    """把正文 HTML 包装成完整的公众号文章（带头部和尾部）"""
    today = date_str or datetime.now().strftime("%Y年%m月%d日")

    return f"""<section style="padding:0 2px;">

  <!-- 头部 -->
  <section style="text-align:center;padding:30px 0 20px;border-bottom:2px solid #1976d2;margin-bottom:24px;">
    <h1 style="font-size:22px;color:#1a1a1a;margin:0 0 10px;">🌍 全球热点速递</h1>
    <p style="font-size:13px;color:#999;margin:0;">{today} · AI 自动聚合整理</p>
  </section>

  <!-- 正文 -->
  {body_html}

  <!-- 尾部 -->
  <hr style="border:none;border-top:1px solid #e0e0e0;margin:30px 0 16px;">
  <section style="text-align:center;font-size:12px;color:#999;padding:10px 0 30px;">
    <p style="margin:4px 0;">内容由 DeepSeek AI 自动聚合整理，仅供参考</p>
    <p style="margin:4px 0;">如不想接收推送，请前往公众号设置关闭</p>
  </section>

</section>"""


# ---- 兼容旧接口 ----
def format_daily_report(ai_summary: str, date_str: str | None = None) -> str:
    """生成公众号 HTML 文章（新版）"""
    today = date_str or datetime.now().strftime("%Y年%m月%d日")
    title = f"全球热点速递 | {today}"
    body_html = markdown_to_wechat_html(ai_summary)
    return wrap_html_page(title, body_html, today)
