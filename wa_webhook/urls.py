from django.urls import path
from .views import WebhookView,Wapp_send_msg


app_name = 'wa_webhook'
urlpatterns = [
    path("webhook", WebhookView.as_view(), name="whatsapp-webhook"),
    path("Wappsendmsg", Wapp_send_msg.as_view(), name="Wapp_send_msg"),
]


