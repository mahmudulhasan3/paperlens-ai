import html

ACCENT = "#10a37f"
FONT = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"


# Email design: a paragraph of normal text
def paragraph(text):
    return (
        '<p style="margin:0 0 16px 0;font-size:15px;line-height:1.65;color:#4b5563;">'
        + text
        + "</p>"
    )


# Email design: the big box that shows the login code
def code_box(code):
    return (
        '<div style="margin:8px 0 22px 0;padding:18px 12px 18px 22px;text-align:center;background:#effaf6;'
        "border:1px solid #bfe8da;border-radius:12px;font-family:SFMono-Regular,Consolas,Menlo,monospace;"
        'font-size:36px;font-weight:700;letter-spacing:10px;color:#0b7a5f;">'
        + html.escape(code)
        + "</div>"
    )


# Email design: a green button that opens a link
def button(label, link):
    return (
        '<table role="presentation" cellspacing="0" cellpadding="0" style="margin:8px 0 22px 0;"><tr>'
        '<td style="border-radius:10px;background:' + ACCENT + ';">'
        '<a href="'
        + html.escape(link, quote=True)
        + '" style="display:inline-block;padding:13px 28px;'
        'font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:10px;">'
        + html.escape(label)
        + "</a></td></tr></table>"
    )


# Email design: the frame that every email uses (header, white card, footer)
def layout(preheader, heading, body):
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        '<body style="margin:0;padding:0;background:#f4f5f7;font-family:' + FONT + ';">'
        '<div style="display:none;max-height:0;overflow:hidden;opacity:0;">'
        + html.escape(preheader)
        + "</div>"
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f5f7;">'
        '<tr><td align="center" style="padding:32px 12px;">'
        '<table role="presentation" width="480" cellspacing="0" cellpadding="0" style="width:480px;max-width:100%;">'
        '<tr><td style="padding:0 4px 18px 4px;font-size:20px;font-weight:700;color:#111827;">&#128269; PaperLens-AI</td></tr>'
        '<tr><td style="background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;padding:32px 28px;">'
        '<h1 style="margin:0 0 14px 0;font-size:22px;line-height:1.3;color:#111827;">'
        + html.escape(heading)
        + "</h1>"
        + body
        + "</td></tr>"
        '<tr><td style="padding:18px 8px 0 8px;font-size:12px;line-height:1.6;color:#9ca3af;text-align:center;">'
        "You received this email because this address was used on PaperLens-AI.<br>"
        "If this was not you, you can safely ignore it.<br>Developed by Mahmudul Hasan"
        "</td></tr></table></td></tr></table></body></html>"
    )


# Email step: the login code email, it returns the subject and the html
def otp_email(code, minutes):
    body = paragraph(
        "Enter this code to finish logging in to PaperLens-AI."
    ) + code_box(code)
    body = body + paragraph(
        "The code works for " + str(minutes) + " minutes and can be used only once."
    )
    body = body + paragraph(
        "If you did not try to log in, you can ignore this email. Consider changing your password."
    )

    return code + " is your PaperLens-AI login code", layout(
        "Your login code is " + code, "Your login code", body
    )


# Email step: the password reset email with a button and the plain link as a backup
def reset_email(link, minutes):
    body = paragraph(
        "We received a request to choose a new password for your PaperLens-AI account."
    )
    body = body + button("Choose a new password", link)
    body = body + paragraph(
        "The link works for " + str(minutes) + " minutes and can be used only once."
    )
    body = body + paragraph(
        "If the button does not work, copy this link into your browser:<br>"
        '<span style="word-break:break-all;color:#6b7280;font-size:13px;">'
        + html.escape(link)
        + "</span>"
    )
    body = body + paragraph(
        "If you did not ask for this, ignore this email. Your password stays the same."
    )

    return "Reset your PaperLens-AI password", layout(
        "Choose a new password", "Reset your password", body
    )


# Email step: the welcome email, sent once after the first login
def welcome_email(name, app_url):
    items = [
        "Ask questions about your papers and get answers with page references",
        "Summarize, compare and extract information from papers",
        "Write in English or Bangla, the answer comes in the same language",
        "Your chats and papers are saved in your account",
    ]

    list_html = '<ul style="margin:0 0 20px 0;padding-left:20px;font-size:15px;line-height:1.8;color:#4b5563;">'
    for item in items:
        list_html = list_html + "<li>" + html.escape(item) + "</li>"
    list_html = list_html + "</ul>"

    body = paragraph(
        "Hi " + html.escape(name) + ", your account is ready. Here is what you can do:"
    )
    body = body + list_html + button("Open PaperLens-AI", app_url)
    body = body + paragraph(
        "Every answer is checked against your documents. If the evidence is not enough, PaperLens-AI says so."
    )
    body = body + """
    <p style="margin:24px 0 0 0;font-size:15px;line-height:1.7;color:#4b5563;">
    Best regards,<br>
    <strong style="color:#111827;">PaperLens-AI Team</strong>
    </p>
    """
    return "Welcome to PaperLens-AI", layout(
        "Your account is ready", "Welcome, " + name + "!", body
    )
