
import json

import logging

import requests
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializer import wa_text_message_sr
from .celery_tasks import celery_send_whatsapp_txt,celery_send_whatsapp_audio,celery_send_whatsapp_qloby_txt
from whatsapp_utils.utils.utils import (
    download_whatsapp_audio,webhook_check,get_message
)
from .sys_conf import sys_conf
import os
logger = logging.getLogger(__name__)

VERIFY_TOKEN = sys_conf.get("VERIFY_TOKEN")
WHATSAPP_TOKEN = sys_conf.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = sys_conf.get("PHONE_NUMBER_ID")

sys_conf = {
    "audio_ext": os.getenv("AUDIO_EXT"),
    "VERIFY_TOKEN": os.getenv("VERIFY_TOKEN"),
    "WHATSAPP_TOKEN": os.getenv("WHATSAPP_TOKEN"),
    "PHONE_NUMBER_ID": os.getenv("PHONE_NUMBER_ID"),
    "audio_path": os.getenv("AUDIO_PATH"),
    "AZURE_SPEECH_KEY": os.getenv("AZURE_SPEECH_KEY"),
    "AZURE_SPEECH_REGION": os.getenv("AZURE_SPEECH_REGION"),
    "AZURE_OPENAI_KEY": os.getenv("AZURE_OPENAI_KEY"),
    "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "OPENAI_API_VERSION": os.getenv("OPENAI_API_VERSION"),
    "AZURE_OPENAI_DEPLOYMENT": os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    "Globy_caht_api": os.getenv("GLOBY_CHAT_API")
}
logger.info(f"""############# sys_conf
            
            
            {sys_conf}
            
             """)

class WebhookView(APIView):
    """
    Handles WhatsApp webhook verification and message reception.
    """

    def get(self, request):
        """
        Verify webhook subscription with the Facebook API.
        """
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        logger.info("Webhook verification request received: mode=%s, token=%s", mode, token)
        wh=webhook_check(challenge,token,VERIFY_TOKEN)
        return wh

    def post(self, request):
        """
        Process incoming WhatsApp messages and trigger async Celery tasks.
        """
        try:
            data = request.data
            res=get_message(data)
            logger.info(f"##  ## res   {res}")
            print(f"##  ## res   {res}")
            if res['res']==True:
                msg=res['msg']
                if msg=="":
                    return Response({"status": "no_messages"}, status=status.HTTP_200_OK)
                from_number=res['msg']['from']
                if "text" in msg:
                    text = msg["text"]["body"]
                    logger.info("📩 Text message from %s: %s", from_number, text)
                    
                    celery_send_whatsapp_qloby_txt.delay(from_number, f"{text}",sys_conf)

                elif "audio" in msg:
                    media_id = msg["audio"]["id"]
                    logger.info("🎤 Received audio message: media_id=%s", media_id)

                    mp3_path = download_whatsapp_audio(
                        media_id,
                        WHATSAPP_TOKEN,
                        from_number,
                     
                        sys_conf.get("audio_path"),
                    )

                    logger.info("Audio downloaded successfully: %s", mp3_path)
                    celery_send_whatsapp_audio.delay(mp3_path)
                    logger.info("Celery task triggered for audio transcription and response")

                else:
                    logger.info("Received unsupported message type from %s", from_number)
            

        except (KeyError, IndexError) as parse_err:
            logger.exception("Malformed webhook payload: %s", parse_err)
            return Response({"error": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("Unexpected error while processing WhatsApp webhook: %s", e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class Wapp_send_msg(APIView):
    def post(self, request):
        serializer = wa_text_message_sr(data=request.data)
        if serializer.is_valid():
            mobile_number = serializer.validated_data['to']
            text= serializer.validated_data['text']
            celery_send_whatsapp_txt.delay(mobile_number, f"{text}",sys_conf)
            return Response({"status": "ok"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)