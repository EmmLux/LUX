from decimal import Decimal
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import AgreementForm, MessageForm, ProfileForm, PublicationForm, RegistrationForm, ReportForm, ReviewForm
from .models import Agreement, Conversation, Message, Publication, Report, Review, Transaction
from .services import calculate_platform_fee, calculate_seller_amount


logger = logging.getLogger(__name__)
User = get_user_model()

def _stripe_sdk():
    try:
        import stripe
    except ImportError as exc:
        logger.exception("Dependencia Stripe no instalada.")
        raise exc
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def _stripe_v2_request(method, path, payload=None):
    stripe = _stripe_sdk()
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"https://api.stripe.com{path}",
        data=body,
        headers={
            "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
            "Content-Type": "application/json",
            "Stripe-Version": "2026-08-26.preview",
        },
        method=method,
    )
    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read()
            status_code = response.status
            response_headers = dict(response.headers.items())
    except HTTPError as exc:
        response_body = exc.read()
        status_code = exc.code
        response_headers = dict(exc.headers.items()) if exc.headers else {}
    except URLError as exc:
        raise stripe.error.APIConnectionError(str(exc.reason)) from exc

    try:
        response_data = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        response_data = {"raw": response_body.decode("utf-8", errors="replace")}

    if status_code >= 400:
        error_data = response_data.get("error", response_data) if isinstance(response_data, dict) else response_data
        error_message = error_data.get("message", "Stripe devolvió un error HTTP.") if isinstance(error_data, dict) else str(error_data)
        raise stripe.error.APIError(
            message=error_message,
            http_body=response_body,
            http_status=status_code,
            json_body=response_data,
            headers=response_headers,
            code=error_data.get("code") if isinstance(error_data, dict) else None,
        )

    return response_data


def _stripe_create_connected_account(user):
    return _stripe_v2_request(
        "POST",
        "/v2/core/accounts",
        {
            "contact_email": user.email,
            "dashboard": "full",
            "identity": {"country": "MX"},
            "configuration": {
                "merchant": {
                    "capabilities": {"card_payments": {"requested": True}},
                },
            },
            "defaults": {
                "currency": "mxn",
                "responsibilities": {
                    "fees_collector": "stripe",
                    "losses_collector": "stripe",
                },
            },
        },
    )


def _stripe_get_account(account_id):
    stripe = _stripe_sdk()
    try:
        return _stripe_v2_request("GET", f"/v2/core/accounts/{account_id}")
    except stripe.error.APIError as exc:
        if exc.http_status != 404:
            raise
        logger.info("Cuenta %s se consulta mediante el endpoint v1 compatible.", account_id)
        return stripe.Account.retrieve(account_id)


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
    completed_count = Agreement.objects.filter(Q(buyer=request.user) | Q(seller=request.user), status="completado").count()
    reviews = Review.objects.filter(subject=request.user)
    average_rating = reviews.aggregate(average=Avg("rating"))["average"]

    return render(
        request,
        "accounts/perfil.html",
        {"publicaciones": publicaciones, "completed_count": completed_count, "review_count": reviews.count(), "average_rating": average_rating},
    )


@login_required
def configurar_cobros(request):
    if not settings.STRIPE_SECRET_KEY:
        logger.warning(
            "Stripe TEST no está configurado para %s.",
            request.user.username,
        )
        messages.error(
            request,
            "Stripe TEST aún no está configurado en el servidor.",
        )
        return redirect("perfil")

    try:
        stripe = _stripe_sdk()

        if not request.user.stripe_account_id:
            account = _stripe_create_connected_account(request.user)
            request.user.stripe_account_id = account.get("id")

            if not request.user.stripe_account_id:
                raise ValueError(
                    "Stripe no devolvió un Account ID."
                )

            logger.info(
                "Cuenta Stripe Connect v2 creada para %s: %s",
                request.user.username,
                request.user.stripe_account_id,
            )

        request.user.stripe_account_status = "pendiente"
        request.user.save(
            update_fields=[
                "stripe_account_id",
                "stripe_account_status",
            ]
        )

        # Stripe permite utilizar Account Links v1 con IDs de Accounts v2.
        account_link = stripe.AccountLink.create(
            account=request.user.stripe_account_id,
            refresh_url=request.build_absolute_uri(
                reverse("configurar_cobros")
            ),
            return_url=request.build_absolute_uri(
                reverse("cobros_configurados")
            ),
            type="account_onboarding",
        )

        logger.info(
            "Onboarding Stripe generado para %s.",
            request.user.stripe_account_id,
        )

        return redirect(account_link.url)

    except ValueError as exc:
        logger.error(
            "No se pudo iniciar cobros para %s: %s",
            request.user.username,
            exc,
        )
        messages.error(request, str(exc))
        return redirect("perfil")

    except Exception as exc:
        logger.exception(
            "Error Stripe al configurar cobros para %s: %s",
            request.user.username,
            exc,
        )

        detail = str(exc).strip()

        messages.error(
            request,
            (
                "Stripe no pudo iniciar la configuración de cobros TEST: "
                f"{detail[:240]}"
            )
            if detail
            else "No fue posible iniciar la configuración de cobros TEST.",
        )

        return redirect("perfil")


@login_required
def cobros_configurados(request):
    if (
        not settings.STRIPE_SECRET_KEY
        or not request.user.stripe_account_id
    ):
        return redirect("perfil")

    try:
        account = _stripe_get_account(
            request.user.stripe_account_id
        )

        configured = False

        if isinstance(account, dict):
            configuration = account.get("configuration") or {}
            merchant = configuration.get("merchant") or {}

            card_payments = (
                merchant.get("capabilities", {})
                .get("card_payments", {})
            )

            configured = bool(
                card_payments.get("status") == "active"
            )

            if not configured:
                configured = bool(
                    account.get("charges_enabled")
                    and account.get("payouts_enabled")
                )

        request.user.stripe_account_status = (
            "configurada" if configured else "pendiente"
        )

        request.user.save(
            update_fields=["stripe_account_status"]
        )

        if configured:
            messages.success(
                request,
                "Cobros configurados correctamente en Stripe TEST.",
            )
        else:
            messages.info(
                request,
                "La configuración de cobros está pendiente en Stripe Connect.",
            )

    except Exception as exc:
        logger.exception(
            "No se pudo consultar Stripe para %s: %s",
            request.user.username,
            exc,
        )

        messages.error(
            request,
            f"No fue posible consultar Stripe: {str(exc)[:240]}",
        )

    return redirect("perfil")


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
    publicacion = get_object_or_404(Publication, pk=pk, status="activa")

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
    category = request.GET.get("category", "").strip()
    if category in dict(Publication.CATEGORY_CHOICES):
        publicaciones_qs = publicaciones_qs.filter(category=category)
    minimum = request.GET.get("min_price", "").strip()
    maximum = request.GET.get("max_price", "").strip()
    if minimum:
        publicaciones_qs = publicaciones_qs.filter(price__gte=minimum)
    if maximum:
        publicaciones_qs = publicaciones_qs.filter(price__lte=maximum)
    ordering = request.GET.get("order", "recent")
    ordering_map = {"recent": "-created_at", "oldest": "created_at", "low": "price", "high": "-price"}
    publicaciones_qs = publicaciones_qs.order_by(ordering_map.get(ordering, "-created_at"))
    return render(request, "accounts/publicaciones.html", {
        "publicaciones": publicaciones_qs, "query": query, "category": category,
        "min_price": minimum, "max_price": maximum, "order": ordering,
        "categories": Publication.CATEGORY_CHOICES,
    })


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
    publicacion = get_object_or_404(Publication, pk=pk, status="activa")

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


@login_required
def crear_acuerdo(request, pk):
    conversation = get_object_or_404(
        Conversation.objects.select_related("participant_one", "participant_two", "publication"), pk=pk
    )
    if request.user not in (conversation.participant_one, conversation.participant_two) or not conversation.publication:
        return redirect("conversaciones")
    seller = conversation.publication.user
    if request.user == seller:
        return redirect("detalle_conversacion", pk=pk)
    form = AgreementForm(request.POST or None, initial={"price": conversation.publication.price, "currency": conversation.publication.currency})
    if request.method == "POST" and form.is_valid():
        agreement = form.save(commit=False)
        agreement.buyer = request.user
        agreement.seller = seller
        agreement.publication = conversation.publication
        agreement.conversation = conversation
        agreement.save()
        return redirect("detalle_acuerdo", pk=agreement.pk)
    return render(request, "accounts/acuerdo.html", {"form": form, "conversation": conversation})


@login_required
def detalle_acuerdo(request, pk):
    agreement = get_object_or_404(Agreement.objects.select_related("buyer", "seller", "publication"), pk=pk)
    if request.user not in (agreement.buyer, agreement.seller):
        return redirect("conversaciones")
    return render(request, "accounts/detalle_acuerdo.html", {"agreement": agreement, "platform_fee": calculate_platform_fee(agreement.price), "seller_amount": calculate_seller_amount(agreement.price), "LUX_PLATFORM_FEE_PERCENT": settings.LUX_PLATFORM_FEE_PERCENT})


@login_required
@require_POST
def cambiar_estado_acuerdo(request, pk, status):
    agreement = get_object_or_404(Agreement, pk=pk)
    if request.user not in (agreement.buyer, agreement.seller):
        return redirect("conversaciones")
    if status == "aceptado" and request.user != agreement.seller:
        return redirect("detalle_acuerdo", pk=pk)
    if status in {"rechazado", "cancelado"}:
        pass
    try:
        agreement.transition_to(status)
    except ValueError:
        messages.error(request, "Ese cambio de estado no está permitido.")
    else:
        agreement.save(update_fields=["status", "updated_at"])
    return redirect("detalle_acuerdo", pk=pk)


@login_required
@require_POST
def completar_acuerdo(request, pk):
    agreement = get_object_or_404(Agreement, pk=pk)
    if request.user != agreement.buyer or agreement.status != "en_proceso":
        return redirect("detalle_acuerdo", pk=pk)
    agreement.transition_to("completado")
    agreement.save(update_fields=["status", "updated_at"])
    transaction = getattr(agreement, "transaction", None)
    if transaction and transaction.status == "en_proceso":
        transaction.transition_to("completado")
        transaction.save(update_fields=["status", "updated_at"])
    return redirect("detalle_acuerdo", pk=pk)


@login_required
@require_POST
def iniciar_checkout(request, pk):
    agreement = get_object_or_404(Agreement.objects.select_related("buyer", "seller", "publication"), pk=pk)
    if request.user != agreement.buyer or agreement.status != "aceptado":
        return redirect("detalle_acuerdo", pk=pk)
    if not settings.STRIPE_SECRET_KEY or agreement.seller.stripe_account_status != "configurada" or not agreement.seller.stripe_account_id:
        messages.error(request, "El proveedor aún no tiene configurado el cobro dentro de LUX.")
        return redirect("detalle_acuerdo", pk=pk)
    try:
        import stripe
    except ImportError:
        messages.error(request, "La dependencia Stripe no está instalada.")
        return redirect("detalle_acuerdo", pk=pk)
    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        fee = calculate_platform_fee(agreement.price)
        transaction, _ = Transaction.objects.get_or_create(
            agreement=agreement,
            defaults={"buyer": agreement.buyer, "seller": agreement.seller, "publication": agreement.publication,
                      "original_price": agreement.price, "lux_fee": fee, "seller_amount": calculate_seller_amount(agreement.price), "currency": agreement.currency},
        )
        if transaction.status == "pendiente":
            transaction.transition_to("pago_iniciado")
            transaction.save(update_fields=["status", "updated_at"])
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price_data": {"currency": agreement.currency, "product_data": {"name": agreement.publication.title}, "unit_amount": int(agreement.price * Decimal("100"))}, "quantity": 1}],
            success_url=request.build_absolute_uri(f"/acuerdos/{agreement.pk}/?pago=pendiente"),
            cancel_url=request.build_absolute_uri(f"/acuerdos/{agreement.pk}/"),
            payment_intent_data={"application_fee_amount": int(fee * Decimal("100")), "transfer_data": {"destination": agreement.seller.stripe_account_id}},
            metadata={"transaction_id": str(transaction.pk), "agreement_id": str(agreement.pk)},
        )
        transaction.external_payment_id = session.id
        transaction.save(update_fields=["external_payment_id", "updated_at"])
        return redirect(session.url)
    except stripe.error.StripeError:
        messages.error(request, "No fue posible iniciar el pago TEST.")
        return redirect("detalle_acuerdo", pk=pk)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    if not settings.STRIPE_WEBHOOK_SECRET:
        return JsonResponse({"error": "webhook no configurado"}, status=503)
    try:
        import stripe
        event = stripe.Webhook.construct_event(request.body, request.META.get("HTTP_STRIPE_SIGNATURE", ""), settings.STRIPE_WEBHOOK_SECRET)
    except ImportError:
        return JsonResponse({"error": "stripe no instalado"}, status=503)
    except (ValueError, stripe.error.SignatureVerificationError):
        return JsonResponse({"error": "firma inválida"}, status=400)
    if event["type"] == "checkout.session.completed":
        transaction_id = event["data"]["object"].get("metadata", {}).get("transaction_id")
        transaction = Transaction.objects.filter(pk=transaction_id).select_related("agreement").first()
        if transaction and transaction.status == "pago_iniciado":
            transaction.transition_to("pagado")
            transaction.save(update_fields=["status", "updated_at"])
            if transaction.agreement.status == "aceptado":
                transaction.agreement.transition_to("pagado")
                transaction.agreement.save(update_fields=["status", "updated_at"])
    return JsonResponse({"received": True})


@login_required
@require_POST
def crear_reporte(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    form = ReportForm(request.POST)
    if form.is_valid():
        report = form.save(commit=False)
        report.reporter = request.user
        report.reported_user = publication.user
        report.publication = publication
        report.save()
        messages.success(request, "Tu reporte fue enviado para revisión.")
    return redirect("detalle_publicacion", pk=pk)


@login_required
@require_POST
def crear_review(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, status="completado")
    if request.user not in (transaction.buyer, transaction.seller):
        return redirect("inicio")
    subject = transaction.seller if request.user == transaction.buyer else transaction.buyer
    form = ReviewForm(request.POST)
    if form.is_valid():
        Review.objects.get_or_create(transaction=transaction, author=request.user, defaults={"subject": subject, "rating": form.cleaned_data["rating"], "content": form.cleaned_data["content"]})
    return redirect("detalle_acuerdo", pk=transaction.agreement_id)
