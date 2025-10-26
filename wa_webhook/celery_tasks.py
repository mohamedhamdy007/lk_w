import os
import pandas as pd

from celery import shared_task

from celery.utils.log import get_task_logger
from pydub import AudioSegment

from whatsapp_utils.utils.STT import transcribe_audio
from whatsapp_utils.utils.utils import (
    convert_mp3_to_wav,
    whatsapp_upload_media,
    delete_files_by_mask,
    convert_mp3_to_ogg,
    send_whatsapp_audio_by_id,
    send_whatsapp_voice,send_whatsapp_text_message,
    send_globy_text_message,send_globy_text_message_t,send_globy_text_message_t_1
)

from whatsapp_utils.utils.TTS import text_to_arabic_speech
from whatsapp_utils.utils.LLM import llm_gpt4,llm_globy
from .sys_conf import sys_conf

logger = get_task_logger(__name__)


def get_files(fpath: str = sys_conf["audio_path"]) -> pd.DataFrame:
    """
    List and extract file metadata (fid, aid, tid) from audio directory.
    """
    files = os.listdir(fpath)
    records = []

    for filename in files:
        try:
            fid, aid, tid_with_ext = filename.split("_")
            tid = tid_with_ext.split(".")[0]
            records.append({"fid": fid, "aid": aid, "tid": tid})
        except ValueError:
            logger.warning("Unexpected filename format skipped: %s", filename)
            continue

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.drop_duplicates(keep="first").sort_values(["tid"])
    return df




@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def celery_send_whatsapp_txt(self,fromid,text_q,sys_conf):
    logger.info("🎧 Starting WhatsApp TEXT  processing for %s")
    try:
        #llm_response = llm_gpt4(text_q, sys_conf)
        #send_whatsapp_text_message(fromid,llm_response,sys_conf)
        
        send_whatsapp_text_message(fromid,text_q,sys_conf)
    except FileNotFoundError as e:
        logger.error("File not found during processing: %s", e)
        raise self.retry(exc=e)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def celery_send_whatsapp_qloby_txt(self,fromid,text_q: str,sys_conf):
    logger.info("🎧 Starting WhatsApp TEXT  processing for %s")
    try:
        llm_response = llm_globy(text_q, sys_conf)
        send_globy_text_message(fromid,llm_response,sys_conf)
    except FileNotFoundError as e:
        logger.error("File not found during processing: %s", e)
        raise self.retry(exc=e)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def celery_send_whatsapp_audio(self, audio_path: str):
    """
    Celery task to process an incoming audio file and send a WhatsApp voice response.

    Steps:
    1. Convert MP3 → WAV
    2. Transcribe audio (Azure STT)
    3. Generate reply using GPT-4
    4. Convert reply to Arabic speech (TTS)
    5. Upload and send reply as WhatsApp voice
    6. Clean up temporary files
    """
    logger.info("🎧 Starting WhatsApp voice processing for %s", audio_path)

    try:
        base_path = os.path.splitext(audio_path)[0]
        filename = os.path.basename(base_path)
        fid, aid, tid = filename.split("_")

        # Step 1: Convert MP3 → WAV
        wav_path = f"{base_path}.wav"
        convert_mp3_to_wav(f"{base_path}.mp3", wav_path)
        logger.info("Audio converted to WAV: %s", wav_path)

        # Step 2: Speech-to-text (Azure)
        text = transcribe_audio(wav_path, sys_conf)
        logger.info("Transcribed text: %s", text)

        # Step 3: LLM processing (GPT-4)
        llm_response = llm_gpt4(text, sys_conf)
        logger.info("LLM response: %s", llm_response)

        # Step 4: Text-to-speech (Arabic)
        reply_mp3 = f"{base_path}_rep.mp3"
        text_to_arabic_speech(llm_response, reply_mp3, sys_conf)
        logger.info("TTS reply generated: %s", reply_mp3)

        # Step 5: Convert MP3 → OGG and send over WhatsApp
        reply_ogg = f"{base_path}_rep.ogg"
        convert_mp3_to_ogg(reply_mp3, reply_ogg)
        #media_id=whatsapp_upload_media(reply_ogg,sys_conf)
        #logger.info(f"########  medis ID  :  {media_id}")
        send_whatsapp_voice(fid, reply_ogg, sys_conf)
        logger.info("Reply sent as WhatsApp voice message")

    except FileNotFoundError as e:
        logger.error("File not found during processing: %s", e)
        raise self.retry(exc=e)

    except Exception as e:
        logger.exception("Unhandled error during WhatsApp voice task: %s", e)
        raise self.retry(exc=e)

    finally:
        try:
            delete_files_by_mask(sys_conf["audio_path"], f"{filename}*")
            logger.info("Temporary files cleaned for %s", filename)
        except Exception as cleanup_err:
            logger.warning("Failed to clean temporary files: %s", cleanup_err)
