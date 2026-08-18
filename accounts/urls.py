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
    path("usuarios/<str:username>/", views.perfil_publico, name="perfil_publico"),
    path("mensajes/", views.conversaciones, name="conversaciones"),
    path("mensajes/<int:pk>/", views.detalle_conversacion, name="detalle_conversacion"),

]
