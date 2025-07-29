import os
import base64
from mailjet_rest import Client

API_KEY = os.getenv("MAILJET_API_KEY", "a3b17035fdb5121f9b5295459821cadb")
SECRET_KEY = os.getenv("MAILJET_SECRET_KEY", "020db9d9867d0d900885893af5893d91")
SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@example.com")

_mailjet = Client(auth=(API_KEY, SECRET_KEY), version='v3.1')

def send_via_mailjet(to_email, subject, text=None, html=None, attachments=None):
    """Envio básico de e-mail usando a API do Mailjet."""
    message = {
        "From": {"Email": SENDER},
        "To": [{"Email": to_email}],
        "Subject": subject,
    }
    if text:
        message["TextPart"] = text
    if html:
        message["HTMLPart"] = html
    if attachments:
        files = []
        for path in attachments:
            with open(path, "rb") as f:
                files.append({
                    "ContentType": "application/octet-stream",
                    "Filename": os.path.basename(path),
                    "Base64Content": base64.b64encode(f.read()).decode(),
                })
        message["Attachments"] = files
    data = {"Messages": [message]}
    return _mailjet.send.create(data=data)
