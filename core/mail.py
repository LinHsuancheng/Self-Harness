"""Gmail API delivery for saved HTML reports."""
import base64
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import json
import os
from pathlib import Path
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TOKEN_URL = "https://oauth2.googleapis.com/token"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


def compose_message(report_path, recipient, html):
    path = Path(report_path)
    message = EmailMessage()
    message["To"] = recipient
    message["Subject"] = f"Self Harness 报告：{path.stem}"
    message.set_content(f"{path.name} 的 HTML 报告内容见邮件正文。")
    message.add_alternative(html, subtype="html")
    return message


def _post(url, data, content_type, access_token=None):
    headers = {"Content-Type": content_type}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    request = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except HTTPError as exc:
        try:
            body = json.loads(exc.read())
            error = body.get("error", "unknown_error")
            if isinstance(error, dict):
                error = error.get("status", "api_error")
        except Exception:
            error = "unreadable_error_response"
        raise RuntimeError(f"Google API 请求失败：HTTP {exc.code} ({error})") from None
    except URLError as exc:
        raise RuntimeError(f"Google API 网络请求失败：{type(exc.reason).__name__}") from None


def _save_token(path, token):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(token, output, ensure_ascii=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _access_token(token_path):
    token = json.loads(token_path.read_text(encoding="utf-8"))
    scopes = token.get("scopes", token.get("scope", []))
    if isinstance(scopes, str):
        scopes = scopes.split()
    if SEND_SCOPE not in scopes:
        raise ValueError("Google token 缺少 gmail.send 权限；请重新授权")

    expiry = datetime.fromisoformat(token.get("expiry", "1970-01-01T00:00:00+00:00"))
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if token.get("token") and expiry > datetime.now(timezone.utc) + timedelta(seconds=30):
        return token["token"]
    if not token.get("refresh_token"):
        raise ValueError("Google token 已过期且没有 refresh token；请重新授权")

    refreshed = _post(
        TOKEN_URL,
        urlencode({
            "client_id": token["client_id"],
            "client_secret": token["client_secret"],
            "refresh_token": token["refresh_token"],
            "grant_type": "refresh_token",
        }).encode("ascii"),
        "application/x-www-form-urlencoded",
    )
    if not refreshed.get("access_token"):
        raise RuntimeError("Google OAuth 未返回 access token")
    token["token"] = refreshed["access_token"]
    token["expiry"] = (datetime.now(timezone.utc) + timedelta(seconds=refreshed.get("expires_in", 3600))).isoformat()
    if refreshed.get("refresh_token"):
        token["refresh_token"] = refreshed["refresh_token"]
    _save_token(token_path, token)
    return token["token"]


def send_report(config, report_path, config_dir):
    settings = config.get("email", {})
    recipient = settings.get("to")
    if not isinstance(recipient, str) or not recipient.strip():
        raise ValueError("请在 config.json 的 email.to 中设置收件人")
    if not settings.get("token_file"):
        raise ValueError("请在 config.json 的 email.token_file 中设置 Google token 文件路径")
    token_path = Path(settings["token_file"])
    if not token_path.is_absolute():
        token_path = Path(config_dir) / token_path
    if not token_path.is_file():
        raise ValueError(f"Google token 文件不存在：{token_path}")

    report_path = Path(report_path)
    message = compose_message(report_path, recipient.strip(), report_path.read_text(encoding="utf-8"))
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii").rstrip("=")
    result = _post(
        SEND_URL,
        json.dumps({"raw": raw}).encode("utf-8"),
        "application/json",
        access_token=_access_token(token_path),
    )
    if not result.get("id"):
        raise RuntimeError("Gmail API 未返回邮件 ID")
    return result["id"]
