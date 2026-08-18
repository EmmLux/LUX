from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Conversation, Message, User, Publication


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "phone_number", "is_active", "date_joined")
    search_fields = ("username", "email", "phone_number")
    list_filter = ("is_active", "is_staff", "is_phone_verified")

    fieldsets = UserAdmin.fieldsets + (
        ("Información de Lux", {
            "fields": (
                "phone_number",
                "display_name",
                "is_phone_verified",
            ),
        }),
    )


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "user",
        "category",
        "price",
        "status",
        "created_at",
    )

    list_filter = (
        "category",
        "status",
    )

    search_fields = (
        "title",
        "description",
        "user__username",
        "user__email",
    )

    ordering = (
        "-created_at",
    )


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "participant_one", "participant_two", "publication", "last_activity_at")
    search_fields = ("participant_one__username", "participant_two__username", "publication__title")
    list_filter = ("created_at", "last_activity_at")
    list_select_related = ("participant_one", "participant_two", "publication")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender", "created_at", "is_read")
    search_fields = ("content", "sender__username")
    list_filter = ("is_read", "created_at")
    list_select_related = ("conversation", "sender")
