import logging
import requests
from whatsapp_utilsFAPI.utils.utils import send_whatsapp_text_message, send_globy_text_message

# Configure logger
logger = logging.getLogger("uvicorn.error")

# Example question list (Arabic + English test data)
QUESTIONS = [
    "jbnkdbgcf jhcgwkjbfwe kugfiewgfw hfikwuvkbk",
    "التلت اتثلتالباتصلبت نتغلتغلت بنلنتار",
    "خهعتخهثبخعاخبعاص لان نضثلاربهمضصثب لاهالب",
    "تالاتلب ثمهعغبلصثهنابلعخغثصب عغلبعثب",
]


def get_agent(sys_conf: dict) -> dict:
    """
    Fetch agent configuration from the remote Globy API.

    Args:
        sys_conf (dict): System configuration containing 'Globy_agent_api' key.

    Returns:
        dict: A dictionary with status (bool) and result (dict or str).
    """
    try:
        response = requests.get(sys_conf["Globy_agent_api"], timeout=30)

        if response.status_code == 200:
            return {"status": True, "res": response.json()}

        logger.warning("Agent API returned non-200 status: %s", response.status_code)
        return {"status": False, "res": f"Bad request {response.status_code}"}

    except requests.RequestException as req_err:
        logger.error("Network error while calling agent API: %s", req_err)
        return {"status": False, "res": f"Request error: {req_err}"}

    except Exception as exc:
        logger.exception("Unexpected exception in get_agent(): %s", exc)
        return {"status": False, "res": f"Exception: {exc}"}


def llm_globy(to: str, question: str, sys_conf: dict, agent: str, thread: str = "") -> dict:
    """
    Interact with the Globy LLM API and send response via WhatsApp.

    Args:
        to (str): Recipient phone number.
        question (str): User question text.
        sys_conf (dict): Configuration containing API URLs.
        agent (str): Agent ID.
        thread (str, optional): Conversation thread ID. Defaults to "".

    Returns:
        dict: Response from the Globy API or an error message.
    """
    logger.info("#### Starting llm_globy for recipient: %s", to)

    payload = {
        "message": question,
        "agent_id": agent,
        "thread_id": thread,
    }

    headers = {"Content-Type": "application/json"}

    try:
        # Call Globy chat API
        response = requests.post(
            sys_conf["Globy_caht_api"],
            json=payload,
            headers=headers,
            timeout=120,
        )

        # Raise HTTPError if response is not 2xx
        response.raise_for_status()

        response_data = response.json()
        logger.info("Globy chat API response: %s", response_data)

        # --- Example mocked response for now ---
        text = "اجابت السؤال كامل"
        docs = ["w", "e", "r", "t"]
        suggestions = QUESTIONS
        thread_id = response_data.get("thread_id", "")
        agent_id = response_data.get("agent_id", "")

        # Send WhatsApp message with results
        send_globy_text_message(
            to=to,
            text=text,
            sys_conf=sys_conf,
            agent=agent_id or agent,
            thread=thread_id or thread,
            t_list=docs,
            b_list=suggestions,
        )

        return {"status": True, "res": response_data}

    except requests.Timeout:
        logger.error("Timeout while calling Globy chat API.")
        return {"status": False, "res": "Timeout while calling Globy chat API"}

    except requests.RequestException as req_err:
        logger.error("Network error calling Globy chat API: %s", req_err)
        return {"status": False, "res": f"Request error: {req_err}"}

    except Exception as exc:
        logger.exception("Unexpected error in llm_globy(): %s", exc)
        return {"status": False, "res": f"Exception: {exc}"}
