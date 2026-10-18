"""Small offline check for report email composition."""
from email.message import EmailMessage
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import mail


report = Path("week-2026-10-13.html")
message = mail.compose_message(report, "reader@example.com", "<html><body>Report</body></html>")
assert isinstance(message, EmailMessage)
assert message["To"] == "reader@example.com"
assert message["Subject"] == "Self Harness 报告：week-2026-10-13"
assert message.get_content_type() == "multipart/mixed"
assert "week-2026-10-13.html" in message.get_body(preferencelist=("plain",)).get_content()
attachments = list(message.iter_attachments())
assert len(attachments) == 1
attachment = attachments[0]
assert attachment.get_filename() == "week-2026-10-13.html"
assert attachment.get_content_type() == "text/html"
assert "<body>Report</body>" in attachment.get_content()
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    token_path = root / "token.json"
    token_path.write_text("{}", encoding="utf-8")
    html_path = root / report
    html_path.write_text("<html><body>Report</body></html>", encoding="utf-8")
    config = {"email": {"to": "reader@example.com", "token_file": str(token_path)}}
    with patch.object(mail, "_access_token", return_value="test-access-token"), patch.object(
        mail, "_post", return_value={"id": "test-message-id"}
    ) as post:
        assert mail.send_report(config, html_path, root) == "test-message-id"
    url, payload, content_type = post.call_args.args[:3]
    assert url == mail.SEND_URL and content_type == "application/json"
    raw = json.loads(payload)["raw"]
    decoded = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    assert b"reader@example.com" in decoded and b"week-2026-10-13.html" in decoded
help_text = subprocess.run(
    [sys.executable, "-m", "core.run", "--help"],
    check=True, capture_output=True, text=True,
).stdout
assert "--send-email" in help_text
print("Report email composition checks passed")
