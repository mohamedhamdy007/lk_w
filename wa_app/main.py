import os
import json
import logging
import requests
from fastapi import FastAPI, APIRouter,Request, Query, HTTPException,status,BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor
from .utils.api import get_agent,llm_globy
from .utils.data import WATextMessage
from whatsapp_utilsFAPI.utils.utils import (
    send_whatsapp_text_message,
    send_globy_text_message,
    webhook_check,
    get_message
)
logger = logging.getLogger("uvicorn.error")
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
    "Globy_caht_api": os.getenv("Globy_caht_api"),
    "Globy_agent_api": os.getenv("Globy_agent_api","https://globby-ai-rev-d6gjf7dugaa2fncm.westeurope-01.azurewebsites.net/list_agent")

}
# ---------------------- FastAPI App ----------------------
app = FastAPI(title="WhatsApp Webhook API", version="1.0")
router = APIRouter()
executor = ThreadPoolExecutor(max_workers=4)


logger.info(f"######## sys_conf ########\n{sys_conf}\n#########################")
print(f"######## sys_conf ########\n{sys_conf}\n#########################")

VERIFY_TOKEN = sys_conf["VERIFY_TOKEN"]
WHATSAPP_TOKEN = sys_conf["WHATSAPP_TOKEN"]

@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    ):
    """
    WhatsApp webhook verification endpoint.
    """
    logger.info(f"Webhook verification: mode={hub_mode}, token={hub_verify_token}")
    return webhook_check(hub_challenge, hub_verify_token, VERIFY_TOKEN)
@app.post("/webhook")
async def receive_whatsapp_message(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
        res = get_message(data)
        ag_res=get_agent(sys_conf)
        if ag_res['status']==True:
            agent_id=ag_res['res']['agent_id']
            logger.info(f"""📩 Incoming message parsed: {res} == {ag_res}

                            {agent_id}

                        """)
            if not res.get("res"):
                return JSONResponse({"status": "no_messages"}, status_code=200)

            msg = res.get("msg", {})
            if not msg:
                return JSONResponse({"status": "no_messages"}, status_code=200)

            from_number = msg.get("from")
            print(f"""msg
            
                  
                  {list(msg.keys())}
                  """)
            if "text" in list(msg.keys()):
                text = msg["text"]["body"]
                logger.info(f"📨 Text from {from_number}: {text}")
                background_tasks.add_task(llm_globy,from_number, text, sys_conf,agent_id)
                #background_tasks.add_task(send_whatsapp_text_message, from_number, text, sys_conf)
                #background_tasks.add_task(send_globy_text_message, from_number, text, sys_conf,agent_id)
                return JSONResponse({"status": "ok"}, status_code=200)
           
            elif "interactive" in list(msg.keys()):
                logger.info("######## button_reply")
                text = msg["interactive"]["button_reply"]['id']
                executor.submit(send_whatsapp_text_message, from_number, text, sys_conf)
            else:
                raise HTTPException(status_code=400, detail="unsuported process")
        elif ag_res['status']==False:
            logger.info(f""" er:
                        
                        
                        {ag_res}
                        """)
            raise HTTPException(status_code=400, detail=f"{ag_res["res"]}")       
    except (KeyError, IndexError) as parse_err:
        logger.exception(f"Malformed webhook payload: {parse_err}")
        raise HTTPException(status_code=400, detail="Invalid payload")

    except Exception as e:
        logger.exception(f"Unexpected error while processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

     

@router.post("/send-message")
async def wapp_send_msg(payload: WATextMessage):
    """
    Send WhatsApp text message using background thread pool (4 workers).
    """
    try:
        executor.submit(send_whatsapp_text_message, payload.to, payload.text, sys_conf)
        return {"status": "queued", "to": payload.to}
    except Exception as e:
        logger.exception("Error submitting background task")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue message: {str(e)}",
        )


app.include_router(router, prefix="/api")