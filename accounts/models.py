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

    STRIPE_ACCOUNT_STATUS_CHOICES = [
        ("no_configurada", "No configurada"),
        ("pendiente", "Pendiente"),
        ("configurada", "Configurada"),
        ("restringida", "Restringida"),
    ]
    stripe_account_id = models.CharField(max_length=100, blank=True)
    stripe_account_status = models.CharField(
        max_length=20, choices=STRIPE_ACCOUNT_STATUS_CHOICES, default="no_configurada"
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
        ("completada", "Completada"),
        ("cancelada", "Cancelada"),
        ("archivada", "Archivada"),
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

    currency = models.CharField(max_length=3, default="mxn")
    location = models.CharField(max_length=160, blank=True)
    availability = models.CharField(max_length=160, blank=True)

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


class Agreement(models.Model):
    STATUS_CHOICES = [
        ("propuesta", "Propuesta"),
        ("aceptado", "Aceptado"),
        ("rechazado", "Rechazado"),
        ("cancelado", "Cancelado"),
        ("pagado", "Pagado"),
        ("en_proceso", "En proceso"),
        ("completado", "Completado"),
    ]
    buyer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="agreements_as_buyer")
    seller = models.ForeignKey(User, on_delete=models.PROTECT, related_name="agreements_as_seller")
    publication = models.ForeignKey(Publication, on_delete=models.PROTECT, related_name="agreements")
    conversation = models.ForeignKey(Conversation, on_delete=models.SET_NULL, null=True, blank=True, related_name="agreements")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="mxn")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="propuesta")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def transition_to(self, new_status):
        allowed = {
            "propuesta": {"aceptado", "rechazado", "cancelado"},
            "aceptado": {"pagado", "cancelado"},
            "pagado": {"en_proceso", "cancelado"},
            "en_proceso": {"completado", "cancelado"},
            "rechazado": set(), "cancelado": set(), "completado": set(),
        }
        if new_status not in allowed.get(self.status, set()):
            raise ValueError(f"Transición inválida: {self.status} -> {new_status}")
        self.status = new_status


class Transaction(models.Model):
    STATUS_CHOICES = [(value, label) for value, label in [
        ("pendiente", "Pendiente"), ("pago_iniciado", "Pago iniciado"),
        ("pagado", "Pagado"), ("en_proceso", "En proceso"),
        ("completado", "Completado"), ("cancelado", "Cancelado"),
        ("reembolsado", "Reembolsado")]]
    agreement = models.OneToOneField(Agreement, on_delete=models.PROTECT, related_name="transaction")
    buyer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="purchases")
    seller = models.ForeignKey(User, on_delete=models.PROTECT, related_name="sales")
    publication = models.ForeignKey(Publication, on_delete=models.PROTECT, related_name="transactions")
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    lux_fee = models.DecimalField(max_digits=10, decimal_places=2)
    seller_amount = models.DecimalField(max_digits=10, decimal_places=2)
    processing_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="mxn")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pendiente")
    external_payment_id = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def transition_to(self, new_status):
        allowed = {
            "pendiente": {"pago_iniciado", "cancelado"},
            "pago_iniciado": {"pagado", "cancelado"},
            "pagado": {"en_proceso", "reembolsado", "cancelado"},
            "en_proceso": {"completado", "reembolsado"},
            "completado": {"reembolsado"},
            "cancelado": set(), "reembolsado": set(),
        }
        if new_status not in allowed.get(self.status, set()):
            raise ValueError(f"Transición inválida: {self.status} -> {new_status}")
        self.status = new_status


class Review(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT, related_name="reviews")
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reviews_written")
    subject = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reviews_received")
    rating = models.PositiveSmallIntegerField()
    content = models.TextField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("transaction", "author"), name="one_review_per_transaction_author")]


class Report(models.Model):
    STATUS_CHOICES = [("pendiente", "Pendiente"), ("revisando", "Revisando"), ("resuelto", "Resuelto"), ("descartado", "Descartado")]
    REASON_CHOICES = [(value, value.replace("_", " ").title()) for value in ("fraude", "inapropiado", "enganosa", "incumplimiento", "spam", "evasión", "otro")]
    reporter = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reports_made")
    reported_user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="reports_received")
    publication = models.ForeignKey(Publication, on_delete=models.PROTECT, null=True, blank=True, related_name="reports")
    message = models.ForeignKey(Message, on_delete=models.PROTECT, null=True, blank=True, related_name="reports")
    agreement = models.ForeignKey(Agreement, on_delete=models.PROTECT, null=True, blank=True, related_name="reports")
    transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT, null=True, blank=True, related_name="reports")
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    description = models.TextField(max_length=2000)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pendiente")
    moderator = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="reports_moderated")
    resolution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)


class Warning(models.Model):
    LEVEL_CHOICES = [(1, "Advertencia"), (2, "Advertencia formal"), (3, "Última advertencia"), (4, "Suspensión")]
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="warnings")
    reason = models.CharField(max_length=120)
    description = models.TextField(max_length=2000)
    level = models.PositiveSmallIntegerField(choices=LEVEL_CHOICES)
    evidence_reference = models.CharField(max_length=200, blank=True)
    moderator = models.ForeignKey(User, on_delete=models.PROTECT, related_name="warnings_issued")
    is_serious = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
