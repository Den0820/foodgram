from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class MyUser(AbstractUser):
    avatar = models.ImageField(
        upload_to='users/images/',
        null=True,
        default=None,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name', 'password')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name='unique_user',
                fields=['email'],
            ),
        ]


class Subscription(models.Model):
    subscriber = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='subscriptions',
        on_delete=models.CASCADE,
    )
    subscribed_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='subscribers',
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('subscriber', 'subscribed_to')
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f'{self.subscriber} подписан на {self.subscribed_to}'
