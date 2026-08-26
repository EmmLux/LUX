from django.urls import path
from . import views


urlpatterns = [

    # =========================
    # PÁGINA PRINCIPAL
    # =========================

    path("", views.inicio, name="home"),
    path("inicio/", views.inicio, name="inicio"),


    # =========================
    # AUTENTICACIÓN
    # =========================

    path("login/", views.login_view, name="login"),
    path("registro/", views.registro, name="registro"),
    path("logout/", views.logout_view, name="logout"),
    path("explorar/", views.publicaciones, name="explorar"),
    path("publicaciones/", views.publicaciones, name="publicaciones"),


    # =========================
    # PUBLICACIONES
    # =========================

    path(
        "publicacion/<int:pk>/",
        views.detalle_publicacion,
        name="detalle_publicacion",
    ),

    path(
        "publicacion/<int:pk>/contactar/",
        views.contactar_publicacion,
        name="contactar_publicacion",
    ),
    path(
        "publicacion/<int:pk>/oferta/",
        views.proponer_oferta,
        name="proponer_oferta",
    ),
    path("publicacion/<int:pk>/editar/", views.editar_publicacion, name="editar_publicacion"),
    path("publicacion/<int:pk>/eliminar/", views.eliminar_publicacion, name="eliminar_publicacion"),


    # =========================
    # CREAR PUBLICACIÓN
    # =========================

    path(
        "publicar/",
        views.crear_publicacion,
        name="crear_publicacion",
    ),


    # =========================
    # PERFIL
    # =========================

    path(
        "perfil/",
        views.perfil,
        name="perfil",
    ),
    path("perfil/editar/", views.editar_perfil, name="editar_perfil"),
    path("perfil/cobros/", views.configurar_cobros, name="configurar_cobros"),
    path("perfil/cobros/resultado/", views.cobros_configurados, name="cobros_configurados"),
    path("usuarios/<str:username>/", views.perfil_publico, name="perfil_publico"),
    path("mensajes/", views.conversaciones, name="conversaciones"),
    path("mensajes/<int:pk>/", views.detalle_conversacion, name="detalle_conversacion"),
    path("mensajes/<int:pk>/acuerdo/", views.crear_acuerdo, name="crear_acuerdo"),
    path("transacciones/", views.transacciones, name="transacciones"),
    path("acuerdos/<int:pk>/", views.detalle_acuerdo, name="detalle_acuerdo"),
    path("acuerdos/<int:pk>/<str:status>/", views.cambiar_estado_acuerdo, name="cambiar_estado_acuerdo"),
    path("acuerdos/<int:pk>/completar/", views.completar_acuerdo, name="completar_acuerdo"),
    path("acuerdos/<int:pk>/checkout/", views.iniciar_checkout, name="iniciar_checkout"),
    path("publicacion/<int:pk>/reportar/", views.crear_reporte, name="crear_reporte"),
    path("transacciones/<int:pk>/evaluar/", views.crear_review, name="crear_review"),
    path("webhooks/stripe/", views.stripe_webhook, name="stripe_webhook"),

]
