from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Conversation, Message, Publication, User


class LuxFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="creador", email="creador@example.com", password="clave-segura-123"
        )
        self.visitor = User.objects.create_user(
            username="visitante", email="visitante@example.com", password="clave-segura-123"
        )
        self.publication = Publication.objects.create(
            user=self.owner,
            title="Servicio de diseño",
            description="Diseño premium para proyectos.",
            category="servicio",
        )

    def test_registration_logs_the_new_user_in(self):
        response = self.client.post(
            reverse("registro"),
            {
                "username": "nueva",
                "email": "nueva@example.com",
                "phone_number": "",
                "password1": "Una-clave-segura-123",
                "password2": "Una-clave-segura-123",
            },
        )
        self.assertRedirects(response, reverse("inicio"))
        self.assertEqual(self.client.session["_auth_user_id"], str(User.objects.get(username="nueva").pk))

    def test_contact_reuses_thread_and_sends_messages(self):
        self.client.force_login(self.visitor)
        contact_url = reverse("contactar_publicacion", args=[self.publication.pk])
        response = self.client.post(contact_url)
        conversation = Conversation.objects.get()
        self.assertRedirects(response, reverse("detalle_conversacion", args=[conversation.pk]))
        self.client.post(contact_url)
        self.assertEqual(Conversation.objects.count(), 1)

        response = self.client.post(reverse("detalle_conversacion", args=[conversation.pk]), {"content": "Hola"})
        self.assertRedirects(response, reverse("detalle_conversacion", args=[conversation.pk]))
        self.assertEqual(Message.objects.get().sender, self.visitor)

    def test_private_and_owner_only_routes_are_protected(self):
        edit_url = reverse("editar_publicacion", args=[self.publication.pk])
        self.assertRedirects(self.client.get(edit_url), f"{reverse('login')}?next={edit_url}")

        self.client.force_login(self.visitor)
        self.assertEqual(self.client.get(edit_url).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(edit_url).status_code, 200)

        other = Conversation.objects.create(
            participant_one=self.owner, participant_two=self.visitor, publication=self.publication
        )
        outsider = User.objects.create_user("fuera", "fuera@example.com", "clave-segura-123")
        self.client.force_login(outsider)
        response = self.client.get(reverse("detalle_conversacion", args=[other.pk]))
        self.assertRedirects(response, reverse("conversaciones"))

    def test_authenticated_user_can_create_publication_with_photo(self):
        self.client.force_login(self.owner)
        photo = SimpleUploadedFile(
            "producto.gif",
            (
                b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff"
                b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
            ),
            content_type="image/gif",
        )

        response = self.client.post(
            reverse("crear_publicacion"),
            {
                "title": "Mesa de madera",
                "description": "Mesa restaurada en muy buen estado.",
                "image": photo,
                "category": "producto",
                "price": "950.00",
            },
        )

        publication = Publication.objects.get(title="Mesa de madera")
        self.assertRedirects(
            response,
            reverse("detalle_publicacion", args=[publication.pk]),
            fetch_redirect_response=False,
        )
        self.assertTrue(publication.image.name)
