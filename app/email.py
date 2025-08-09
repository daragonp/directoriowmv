
from flask import current_app
def send_verification_email(to_email, code):
    # Demo: print to console. Replace with SMTP later.
    print(f"[EMAIL] To: {to_email} | Your verification code is: {code}")
    if not current_app.config.get("USE_CONSOLE_EMAIL", True):
        # Implement SMTP if desired.
        pass
