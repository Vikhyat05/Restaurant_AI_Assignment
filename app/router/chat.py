# router.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from groq import Groq
import os
from dotenv import load_dotenv
from utils.time_utils import ISO_REGEX, natural_dt
from core.prompt import SYSTEM_PROMPT
from core.handler import handle_function_call
from core.specs import FUNCTION_SPECS
from core.llm import client

load_dotenv()

router = APIRouter()


message_history = [{"role": "system", "content": SYSTEM_PROMPT}]


class ChatRequest(BaseModel):
    message: str


@router.post("/reset_chat")
async def reset_chat():
    """Reset the message history to just the system prompt."""
    global message_history
    message_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    return {"status": "success", "message": "Chat history reset successfully"}


@router.post("/chat")
async def chat(req: ChatRequest):
    message_history.append({"role": "user", "content": req.message})

    async def generate():
        messages = message_history.copy()

        while True:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                tools=FUNCTION_SPECS,
                tool_choice="auto",
                stream=True,
                temperature=0,
            )

            full_reply, tool_call_id = "", None
            func_name, func_args_parts = None, []

            for chunk in response:
                delta = chunk.choices[0].delta

                if delta.content:
                    full_reply += delta.content
                    yield delta.content

                if delta.tool_calls:
                    call = delta.tool_calls[0]
                    tool_call_id = call.id or tool_call_id
                    func_name = call.function.name or func_name
                    if call.function.arguments:
                        func_args_parts.append(call.function.arguments)

            if func_name:
                func_args_json = "".join(func_args_parts) or "{}"

                message_history.append(
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": tool_call_id,
                                "function": {
                                    "name": func_name,
                                    "arguments": func_args_json,
                                },
                                "type": "function",
                            }
                        ],
                        "content": None,
                    }
                )

                print(func_args_json)
                func_response = handle_function_call(func_name, func_args_json)
                message_history.append(func_response)

                messages = message_history.copy()
                continue

            if ISO_REGEX.fullmatch(full_reply.strip()):
                full_reply = natural_dt(full_reply.strip())

            message_history.append({"role": "assistant", "content": full_reply})
            break

    return StreamingResponse(generate(), media_type="text/plain")
