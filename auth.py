import os

# Пароль будет задан в настройках Render
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "fallback_password_123")

def check_password(password):
    return password == ADMIN_PASSWORD
