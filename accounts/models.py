from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    display_name = models.CharField(
        max_length=100,
        blank=True
    )

    is_phone_verified = models.BooleanField(
        default=False
    )


class Publication(models.Model):

    CATEGORY_CHOICES = [
        ("producto", "Producto"),
        ("servicio", "Servicio"),
        ("oportunidad", "Oportunidad"),
    ]

    STATUS_CHOICES = [
        ("activa", "Activa"),
        ("pausada", "Pausada"),
        ("cerrada", "Cerrada"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="publications"
    )

    title = models.CharField(
        max_length=150
    )

    description = models.TextField()

    image = models.ImageField(
        upload_to="publicaciones/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Foto",
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="activa"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.title


class Conversation(models.Model):
    """A private thread, optionally started from a publication."""

    participant_one = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="conversations_started"
    )
    participant_two = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="conversations_received"
    )
    publication = models.ForeignKey(
        Publication,
        on_delete=models.SET_NULL,
        related_name="conversations",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("participant_one", "participant_two", "publication"),
                name="unique_conversation_participants_and_publication",
            ),
            models.CheckConstraint(
                condition=~models.Q(participant_one=models.F("participant_two")),
                name="conversation_requires_two_different_users",
            ),
        ]
        ordering = ("-last_activity_at",)

    def __str__(self):
        return f"Conversación #{self.pk}"

    def other_participant(self, user):
        return self.participant_two if user == self.participant_one else self.participant_one


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    content = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return f"Mensaje #{self.pk}"
