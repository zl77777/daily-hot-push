"""
邮件发送模块 —— 通过 QQ 邮箱 SMTP 发送每日热点文章
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr
from datetime import datetime


class EmailSender:
    """QQ 邮箱 SMTP 发送"""

    SMTP_HOST = "smtp.qq.com"
    SMTP_PORT = 465  # SSL

    def __init__(self, sender_email: str, smtp_code: str):
        """
        sender_email: 发件人 QQ 邮箱地址
        smtp_code:    QQ 邮箱 SMTP 授权码（不是 QQ 密码！）
        """
        self.sender_email = sender_email
        self.smtp_code = smtp_code

    def send_html_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
    ) -> dict:
        """发送 HTML 邮件"""
        msg = MIMEMultipart("alternative")
        msg["From"] = formataddr(("每日热点速递", self.sender_email))
        msg["To"] = to_email
        msg["Subject"] = Header(subject, "utf-8")

        # 纯文本备用
        import re
        plain = re.sub(r"<[^>]+>", "", html_body)
        plain = re.sub(r"\n\s*\n", "\n\n", plain).strip()

        msg.attach(MIMEText(plain, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            server = smtplib.SMTP_SSL(self.SMTP_HOST, self.SMTP_PORT, timeout=15)
            server.login(self.sender_email, self.smtp_code)
            server.sendmail(self.sender_email, [to_email], msg.as_string())
            server.quit()
            print(f"  [邮件] 发送成功 → {to_email}")
            return {"status": "sent", "to": to_email}
        except smtplib.SMTPAuthenticationError:
            print("  [邮件] 认证失败——检查 SMTP 授权码是否正确")
            return {"status": "failed", "reason": "SMTP 认证失败"}
        except Exception as e:
            print(f"  [邮件] 发送失败: {e}")
            return {"status": "failed", "reason": str(e)}


def build_email_title() -> str:
    """生成邮件标题"""
    today = datetime.now().strftime("%m月%d日")
    return f"🌍 全球热点速递 | {today}"
