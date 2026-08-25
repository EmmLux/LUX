from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import MessageForm, ProfileForm, PublicationForm, RegistrationForm
from .models import Conversation, Message, Publication


User = get_user_model()


def registro(request):
    if request.user.is_authenticated:
        return redirect("inicio")
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Tu cuenta está lista. Bienvenido a LUX.")
            return redirect("inicio")
    else:
        form = RegistrationForm()

    return render(request, "accounts/registro.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("inicio")
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        user = User.objects.filter(email=email).first()

        if user:
            authenticated_user = authenticate(
                request,
                username=user.username,
                password=password,
            )

            if authenticated_user:
                login(request, authenticated_user)
                return redirect("inicio")

        messages.error(request, "Correo o contraseña incorrectos.")

    return render(request, "accounts/login.html")


@require_POST
def logout_view(request):
    logout(request)
    return redirect("inicio")


def inicio(request):
    publicaciones = Publication.objects.filter(status="activa").order_by("-created_at")

    return render(
        request,
        "accounts/inicio.html",
        {"publicaciones": publicaciones},
    )


@login_required
def perfil(request):
    publicaciones = request.user.publications.order_by("-created_at")

    return render(
        request,
        "accounts/perfil.html",
        {"publicaciones": publicaciones},
    )


@login_required
def editar_perfil(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Tu perfil se actualizó correctamente.")
            return redirect("perfil")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/editar_perfil.html", {"form": form})


def perfil_publico(request, username):
    profile_user = get_object_or_404(User, username=username, is_active=True)
    publicaciones = profile_user.publications.filter(status="activa").order_by("-created_at")
    return render(request, "accounts/perfil_publico.html", {"profile_user": profile_user, "publicaciones": publicaciones})


@login_required
def crear_publicacion(request):
    if request.method == "POST":
        form = PublicationForm(request.POST, request.FILES)

        if form.is_valid():
            publicacion = form.save(commit=False)
            publicacion.user = request.user
            publicacion.save()

            messages.success(request, "Tu publicación fue creada.")
            return redirect("detalle_publicacion", pk=publicacion.pk)
    else:
        form = PublicationForm()

    return render(
        request,
        "accounts/publicar.html",
        {"form": form},
    )


# Mantiene compatibilidad si algún enlace anterior usa "publicar".
publicar = crear_publicacion


def detalle_publicacion(request, pk):
    publicacion = get_object_or_404(Publication, pk=pk)

    return render(
        request,
        "accounts/detalle_publicacion.html",
        {"publicacion": publicacion},
    )


def publicaciones(request):
    publicaciones_qs = Publication.objects.filter(status="activa").order_by("-created_at")
    query = request.GET.get("q", "").strip()
    if query:
        publicaciones_qs = publicaciones_qs.filter(Q(title__icontains=query) | Q(description__icontains=query))
    return render(request, "accounts/publicaciones.html", {"publicaciones": publicaciones_qs, "query": query})


@login_required
def editar_publicacion(request, pk):
    publicacion = get_object_or_404(Publication, pk=pk, user=request.user)
    form = PublicationForm(request.POST or None, request.FILES or None, instance=publicacion)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "La publicación se actualizó.")
        return redirect("detalle_publicacion", pk=publicacion.pk)
    return render(request, "accounts/publicar.html", {"form": form, "publicacion": publicacion})


@login_required
@require_POST
def eliminar_publicacion(request, pk):
    publicacion = get_object_or_404(Publication, pk=pk, user=request.user)
    publicacion.delete()
    messages.success(request, "La publicación fue eliminada.")
    return redirect("perfil")


@login_required
@require_POST
def contactar_publicacion(request, pk):
    publicacion = get_object_or_404(Publication, pk=pk)

    if publicacion.user == request.user:
        messages.warning(
            request,
            "No puedes contactar tu propia publicación.",
        )
        return redirect("detalle_publicacion", pk=publicacion.pk)

    # Store the smaller id first, making the unique constraint deterministic.
    participant_one, participant_two = sorted((request.user, publicacion.user), key=lambda user: user.pk)
    try:
        conversation, _ = Conversation.objects.get_or_create(
            participant_one=participant_one,
            participant_two=participant_two,
            publication=publicacion,
        )
    except IntegrityError:
        conversation = Conversation.objects.get(
            participant_one=participant_one, participant_two=participant_two, publication=publicacion
        )
    return redirect("detalle_conversacion", pk=conversation.pk)


@login_required
def conversaciones(request):
    conversations_qs = (
        Conversation.objects.filter(Q(participant_one=request.user) | Q(participant_two=request.user))
        .select_related("participant_one", "participant_two", "publication")
        .annotate(unread_count=Count("messages", filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user)))
        .order_by("-last_activity_at")
    )
    for conversation in conversations_qs:
        conversation.other_user = conversation.other_participant(request.user)
        conversation.last_message = conversation.messages.order_by("-created_at").first()
    return render(request, "accounts/conversaciones.html", {"conversations": conversations_qs})


@login_required
def detalle_conversacion(request, pk):
    conversation = get_object_or_404(
        Conversation.objects.select_related("participant_one", "participant_two", "publication"),
        pk=pk,
    )
    if request.user not in (conversation.participant_one, conversation.participant_two):
        messages.error(request, "No tienes permiso para ver esa conversación.")
        return redirect("conversaciones")
    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            Message.objects.create(conversation=conversation, sender=request.user, content=form.cleaned_data["content"])
            conversation.last_activity_at = timezone.now()
            conversation.save(update_fields=["last_activity_at"])
            return redirect("detalle_conversacion", pk=conversation.pk)
    else:
        form = MessageForm()
    return render(request, "accounts/detalle_conversacion.html", {"conversation": conversation, "other_user": conversation.other_participant(request.user), "form": form})
