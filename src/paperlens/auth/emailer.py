import os

import requests
from dotenv import load_dotenv

load_dotenv()

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


# Email step: send one email with the Brevo API; without an API key it is only printed (local development)
def send_email(to_email, subject, html_content):
    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("BREVO_SENDER_EMAIL")
    sender_name = os.getenv("BREVO_SENDER_NAME", "PaperLens-AI")

    if not api_key or not sender_email:
        print(
            "[email is not configured, printed here instead] to:",
            to_email,
            "| subject:",
            subject,
        )
        print(html_content)
        return True

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
    }
    headers = {
        "api-key": api_key,
        "accept": "application/json",
        "content-type": "application/json",
    }

    try:
        response = requests.post(BREVO_URL, json=payload, headers=headers, timeout=15)
    except requests.RequestException as error:
        print("Brevo request failed:", error)
        return False

    if response.status_code not in (200, 201):
        print("Brevo error", response.status_code, response.text[:200])
        return False

    return True
