import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@plannerinbox.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://emily-dalton.github.io/personal-finance")


def send_verification_email(to_email: str, token: str):
    verify_url = f"{FRONTEND_URL}?verify={token}"
    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": to_email,
            "subject": "Verify your Planner in a Box account",
            "html": f"""
<div style="font-family:'Helvetica Neue',Helvetica,sans-serif;max-width:480px;margin:0 auto;
            padding:40px 32px;background:#fffdf8;border-radius:12px">
  <div style="font-family:Georgia,serif;font-size:22px;font-weight:400;color:#211f1a;margin-bottom:10px">
    Verify your email
  </div>
  <p style="font-size:14px;line-height:1.65;color:#6b6558;margin-bottom:28px">
    Click the button below to confirm your address and start using Planner in a Box.
    This link expires in 24 hours.
  </p>
  <a href="{verify_url}"
     style="display:inline-block;padding:13px 24px;border-radius:10px;
            background:#211f1a;color:#fffdf8;text-decoration:none;
            font-size:14px;font-weight:600">
    Verify email →
  </a>
  <p style="font-size:12px;color:#b3ada1;margin-top:32px;line-height:1.5">
    If you didn't sign up for Planner in a Box, you can ignore this email.<br>
    Or paste this link in your browser:<br>
    <span style="color:#7a6a4a">{verify_url}</span>
  </p>
</div>
""",
        })
    except Exception as e:
        print(f"Email send failed: {e}")
