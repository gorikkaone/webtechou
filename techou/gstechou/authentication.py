from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class EmailAuthBackend(ModelBackend):
    """
    カスタム認証バックエンド：`email` を使ってログインできるようにする
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email", username)  # `username` の代わりに `email` を取得
        logger.debug(f"Authenticating user: {email}")

        try:
            user = User.objects.get(email=email)
            logger.debug(f"User found: {user}")
        except User.DoesNotExist:
            logger.debug("User does not exist")
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            logger.debug("Password is correct")
            return user
        else:
            logger.debug("Password is incorrect")
            return None
