import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import newsletter_name as _newsletter_name
from .dashboard import render_template

logger = logging.getLogger(__name__)

SMTP_USER_ENV = "SMTP_USER"
SMTP_PASSWORD_ENV = "SMTP_APP_PASSWORD"
DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587


def _build_plain_text(date_key, articles, overview, brand):
    lines = [f"{brand} — {date_key}", f"{len(articles)} article{'s' if len(articles) != 1 else ''}", ""]
    if overview:
        lines.extend([overview, ""])
    for article in articles:
        lines.append(f"• {(article.title or 'Untitled').strip()}")
        lines.append(f"  {article.url}")
        summary = (article.summary or "").strip()
        if summary:
            lines.append(f"  {summary}")
        lines.append("")
    return "\n".join(lines)


def send_newsletter(date_key, articles, overview, recipient, smtp_user=None, smtp_password=None,
                    smtp_host=DEFAULT_SMTP_HOST, smtp_port=DEFAULT_SMTP_PORT):
    smtp_user = smtp_user or os.environ.get(SMTP_USER_ENV)
    smtp_password = smtp_password or os.environ.get(SMTP_PASSWORD_ENV)
    if not smtp_user or not smtp_password:
        raise EnvironmentError(
            f"Missing SMTP credentials. Set {SMTP_USER_ENV} and {SMTP_PASSWORD_ENV} in .env."
        )

    brand = _newsletter_name()
    article_dicts = [a.to_dict() for a in articles]
    html_body = render_template("email.html", {
        "date_key": date_key,
        "articles": article_dicts,
        "run_count": len(articles),
        "overview": overview,
        "newsletter_name": brand,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    })
    text_body = _build_plain_text(date_key, articles, overview, brand)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{brand} · {date_key} · {len(articles)} article{'s' if len(articles) != 1 else ''}"
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    logger.info("Sending newsletter to %s via %s:%d", recipient, smtp_host, smtp_port)
    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, [recipient], msg.as_string())
    logger.info("Newsletter email sent.")
