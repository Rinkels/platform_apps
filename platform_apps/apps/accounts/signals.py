from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserContext


# Connected from AccountsConfig.ready(). sender must be the resolved user
# model class — passing the AUTH_USER_MODEL string never matches at dispatch.
@receiver(post_save, sender=get_user_model())
def ensure_user_context(sender, instance, created, **kwargs):
    if created:
        UserContext.objects.get_or_create(user=instance)
