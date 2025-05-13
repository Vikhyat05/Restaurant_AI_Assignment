# # router.py
# from fastapi import APIRouter
# from fastapi.responses import StreamingResponse
# from pydantic import BaseModel
# from groq import Groq
# import os, asyncio, json, re
# from dotenv import load_dotenv
# from datetime import datetime
# import pytz
# import json
# from utils.supabaseUtils import (
#     search_restaurants,
#     create_reservation,
#     manage_reservation,
# )

# # ───────────────────────────────
# #  CONFIG & PROMPT
# # ───────────────────────────────

# load_dotenv()
# router = APIRouter()
# groq_key = os.getenv("groq_key")
# client = Groq(api_key=groq_key)


# SYSTEM_PROMPT = """
# You are **FoodieSpot’s Reservation Assistant**. Help users in three ways:
# ① find restaurants via **search_restaurants**
# ② book tables via **create_reservation**
# ③ modify or cancel bookings via **manage_reservation** — while keeping the tone friendly and concise.

# ────────────────────────────────────────
# TOOLS
# • search_restaurants(…areas, cuisines, section, amenities, seats, at_time, on_day…)
#   → returns matching venues

# • create_reservation(…restaurant_name, date, time, am_pm, party_size, name, phone, special_requests…)
#   → books a table

# • manage_reservation(…reservation_id, action, [fields to change]…)
#   → `action = "update"` updates specified fields
#   → `action = "delete"` cancels the booking

# ────────────────────────────────────────
# 🔍  WHEN TO CALL **search_restaurants**
# Call immediately whenever the user mentions **any** of: cuisine • area • seating type • amenity • party size • date • time.
# Pass only the details they provided and leave the rest empty.
# Do **not** ask follow-ups before this search.

# After the tool returns:
# * Iterate over `results`;
# * Create a conversation result which u can present to the using the results mentionin name , cuisine ,  area,  seating  and rating for each restaurant
# * Present each venue in friendly Markdown with details about (name , cuisine ,  area,  seating  and rating).

# ────────────────────────────────────────
# 📅  WHEN TO CALL **create_reservation**
# The user explicitly wants to book.

# 1. **You must possess *all* of these fields first**
#    • `restaurant_name` (exact)
#    • `date`  (YYYY-MM-DD)
#    • `time`  (12-hour **H:MM** that matches `am_pm`)  [DO NOT CONVERT TIME TO 24 HOURS KEEP IT IN 12 HOURS ALWAYS]
#    • `am_pm` (“AM” or “PM”)
#    • `party_size`
#    • **customer `name`** (ask; never default to “User”)
#    • **customer `phone`** (ask; never invent a number)
#    • `special_requests`

# 2. If *any* field is missing or unclear, **ask a follow-up question** *before* calling the tool.

# 3. When you finally have everything, call **create_reservation**.
#    → After the call, confirm the booking in friendly Markdown (no JSON or tool names) and provide the "id" of reservation to the user in case they need to modify it later.

# ────────────────────────────────────────
# ✏️  WHEN TO CALL **manage_reservation**
# User wants to **change** or **cancel** an existing booking.
# 1. Make sure you have `reservation_id` (ask them for it if needed).
# 2. Determine the intent:
#    • “change” / “edit” → action = "update" (collect only the fields they want to change).
#    • “cancel” / “delete” → action = "delete".
# 3. Once you have reservation_id **and** either the fields to update or confirmation to delete → call the tool.
# 4. Respond in Markdown confirming the update or cancellation (no JSON or tool names).

# ────────────────────────────────────────
# FORMATTING & VALIDATION RULES
# • Never mention the internal tool names in replies.
# • Dates → “YYYY-MM-DD”.
# • Times → 12-hour “H:MM” (no leading zero), e.g. “6:00”.
#     – If the user supplies 24-hour time (“18:00”), convert to “6:00” and set `am_pm` = “PM”.
# • Always run **search_restaurants** before suggesting venues.
# • Always run **create_reservation** or **manage_reservation** for actual bookings.
# • Never invent placeholder values; politely ask the user instead.

# """


# message_history = [{"role": "system", "content": SYSTEM_PROMPT}]

# FUNCTION_SPECS = [
#     {
#         "type": "function",
#         "function": {
#             "name": "search_restaurants",
#             "description": "Query restaurants details that satisfy the details or prefrences that the user has provided so far.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "areas": {
#                         "type": "string",
#                         "description": "Area or comma-separated list, e.g. 'Koramangala, Indiranagar'",
#                     },
#                     "cuisines": {
#                         "type": "string",
#                         "description": "Cuisine or list, e.g. 'North Indian;Chinese Fusion'",
#                     },
#                     "amenities": {
#                         "type": "string",
#                         "description": "Amenity keywords, e.g. 'rooftop;live-music'",
#                     },
#                     "seats": {"type": "integer", "description": "Party size (≥1)"},
#                     "at_time": {
#                         "type": "string",
#                         "description": "Desired time in 'HH:MM' 24-h format",
#                     },
#                     "on_day": {
#                         "type": "string",
#                         "description": "Day of week as 3-letter code, e.g. 'Fri'",
#                     },
#                     "section": {
#                         "type": "string",
#                         "description": "Seating section preference. Can take only 3 values 'outdoor‑patio', 'indoor‑ac', 'private‑room'",
#                     },
#                 },
#                 "required": [],
#             },
#         },
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "create_reservation",
#             "description": "Create a restaurant reservation with the specified details",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "restaurant_name": {
#                         "type": "string",
#                         "description": "Exact restaurant name from search results",
#                     },
#                     "date": {
#                         "type": "string",
#                         "description": "Reservation date in YYYY-MM-DD format",
#                     },
#                     "time": {
#                         "type": "string",
#                         "description": "Reservation time in H:MM format, e.g. '7:30'",
#                     },
#                     "am_pm": {
#                         "type": "string",
#                         "description": "AM or PM",
#                         "enum": ["AM", "PM"],
#                     },
#                     "party_size": {
#                         "type": "integer",
#                         "description": "Number of people in the party",
#                     },
#                     "name": {"type": "string", "description": "Customer's name"},
#                     "phone": {
#                         "type": "string",
#                         "description": "Customer's phone number",
#                     },
#                     "special_requests": {
#                         "type": "string",
#                         "description": "Any special requests or 'none' if not provided",
#                     },
#                 },
#                 "required": [
#                     "restaurant_name",
#                     "date",
#                     "time",
#                     "am_pm",
#                     "party_size",
#                     "name",
#                     "phone",
#                 ],
#             },
#         },
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "manage_reservation",
#             "description": "Update or cancel an existing reservation.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "reservation_id": {
#                         "type": "string",
#                         "description": "Reservation identifier returned when the booking was created",
#                     },
#                     "action": {
#                         "type": "string",
#                         "enum": ["update", "delete"],
#                         "description": "'update' to change fields, 'delete' to cancel",
#                     },
#                     "restaurant_name": {"type": "string"},
#                     "date": {"type": "string"},
#                     "time": {"type": "string"},
#                     "am_pm": {"type": "string", "enum": ["AM", "PM"]},
#                     "party_size": {"type": "integer"},
#                     "name": {"type": "string"},
#                     "phone": {"type": "string"},
#                     "special_requests": {"type": "string"},
#                 },
#                 "required": ["reservation_id", "action"],
#             },
#         },
#     },
# ]


# def handle_function_call(name: str, args_json: str):
#     """
#     Dispatch an LLM function call to the correct Python helper
#     and wrap its response in a valid function-role message.
#     """
#     # ─────────────────────────────────────────────
#     # 1. Parse arguments safely
#     # ─────────────────────────────────────────────
#     try:
#         args = json.loads(args_json) if args_json else {}
#     except json.JSONDecodeError:
#         args = {}

#     # ─────────────────────────────────────────────
#     # 2. search_restaurants
#     # ─────────────────────────────────────────────
#     if name == "search_restaurants":
#         try:
#             hits = search_restaurants(
#                 areas=args.get("areas"),
#                 cuisines=args.get("cuisines"),
#                 amenities=args.get("amenities"),
#                 seats=args.get("seats"),
#                 at_time=args.get("at_time"),
#                 on_day=args.get("on_day"),
#                 section=args.get("section"),
#                 min_score=args.get("min_score", 75),
#             )
#             return {
#                 "role": "function",
#                 "name": name,
#                 "content": json.dumps(hits, default=str),
#             }
#         except Exception as e:
#             return {
#                 "role": "function",
#                 "name": name,
#                 "content": json.dumps({"error": str(e)}),
#             }

#     # ─────────────────────────────────────────────
#     # 3. create_reservation
#     # ─────────────────────────────────────────────
#     elif name == "create_reservation":
#         try:
#             required_fields = [
#                 "restaurant_name",
#                 "date",
#                 "time",
#                 "am_pm",
#                 "party_size",
#                 "name",
#                 "phone",
#             ]
#             missing = [f for f in required_fields if not args.get(f)]
#             if missing:
#                 return {
#                     "role": "function",
#                     "name": name,
#                     "content": f"As user to please provide: {', '.join(missing)} to complete the reservation,.",
#                 }

#             result = create_reservation(
#                 restaurant_name=args["restaurant_name"],
#                 date=args["date"],
#                 time=args["time"],
#                 am_pm=args["am_pm"],
#                 party_size=args["party_size"],
#                 name=args["name"],
#                 phone=args["phone"],
#                 special_requests=args.get("special_requests", "none"),
#             )

#             print(result)
#             return {
#                 "role": "function",
#                 "name": name,
#                 "content": json.dumps(result, default=str),
#             }

#         except Exception as e:
#             return {
#                 "role": "function",
#                 "name": name,
#                 "content": json.dumps({"success": False, "error": str(e)}),
#             }

#     # ─────────────────────────────────────────────
#     # 4. manage_reservation  ← NEW
#     # ─────────────────────────────────────────────
#     elif name == "manage_reservation":
#         try:
#             # mandatory inputs
#             reservation_id = args.get("reservation_id")
#             action = args.get("action")

#             if not reservation_id or not action:
#                 return {
#                     "role": "function",
#                     "name": name,
#                     "content": "Please provide both reservation_id and action ('update' or 'delete').",
#                 }

#             action = action.lower()
#             if action not in ("update", "delete"):
#                 return {
#                     "role": "function",
#                     "name": name,
#                     "content": "Action must be 'update' or 'delete'.",
#                 }

#             # If it's an update but user supplied no fields to change, prompt them
#             if action == "update":
#                 updatable_keys = {
#                     k: v
#                     for k, v in args.items()
#                     if k
#                     in {
#                         "restaurant_name",
#                         "date",
#                         "time",
#                         "am_pm",
#                         "party_size",
#                         "name",
#                         "phone",
#                         "special_requests",
#                     }
#                     and v is not None
#                 }
#                 if not updatable_keys:
#                     return {
#                         "role": "function",
#                         "name": name,
#                         "content": "Which fields would you like to change? (e.g. time, party_size)",
#                     }

#             # Call helper with **args to forward everything
#             result = manage_reservation(**args)

#             return {
#                 "role": "function",
#                 "name": name,
#                 "content": json.dumps(result, default=str),
#             }

#         except Exception as e:
#             return {
#                 "role": "function",
#                 "name": name,
#                 "content": json.dumps({"success": False, "error": str(e)}),
#             }

#     # ─────────────────────────────────────────────
#     # 5. Unknown function
#     # ─────────────────────────────────────────────
#     else:
#         return {
#             "role": "function",
#             "name": name,
#             "content": json.dumps({"error": f"Unknown function: {name}"}),
#         }


# # ───────────────────────────────
# #  HELPERS
# # ───────────────────────────────
# ISO_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


# def natural_dt(iso_str: str) -> str:
#     dt = datetime.fromisoformat(iso_str)

#     # 1st/2nd/3rd/4th… suffix utility
#     def ordinal(n: int) -> str:
#         return {1: "st", 2: "nd", 3: "rd"}.get(n if 10 < n % 100 < 14 else n % 10, "th")

#     day_suffix = ordinal(dt.day)
#     return dt.strftime(f"%-I:%M %p on %-d{day_suffix} %B %Y")


# # ───────────────────────────────
# #  REQUEST SCHEMA
# # ───────────────────────────────
# class ChatRequest(BaseModel):
#     message: str


# # ───────────────────────────────
# #  ROUTE
# # ───────────────────────────────
# @router.post("/chat")
# async def chat(req: ChatRequest):
#     message_history.append({"role": "user", "content": req.message})

#     async def generate():
#         messages = message_history.copy()

#         while True:  # loop until model “finishes”
#             response = client.chat.completions.create(
#                 model="llama-3.1-8b-instant",
#                 messages=messages,
#                 tools=FUNCTION_SPECS,
#                 tool_choice="auto",
#                 stream=True,
#                 temperature=0,
#             )

#             # Collect stream
#             full_reply, tool_call_id = "", None
#             func_name, func_args_parts = None, []

#             for chunk in response:
#                 delta = chunk.choices[0].delta

#                 # normal assistant text tokens
#                 if delta.content:
#                     full_reply += delta.content
#                     yield delta.content

#                 # tool‑call tokens
#                 if delta.tool_calls:
#                     call = delta.tool_calls[0]
#                     tool_call_id = call.id or tool_call_id
#                     func_name = call.function.name or func_name
#                     if call.function.arguments:
#                         func_args_parts.append(call.function.arguments)

#             # Did the model call a tool?
#             if func_name:
#                 func_args_json = "".join(func_args_parts) or "{}"

#                 # Append assistant‑tool message exactly per spec
#                 message_history.append(
#                     {
#                         "role": "assistant",
#                         "tool_calls": [
#                             {
#                                 "id": tool_call_id,
#                                 "function": {
#                                     "name": func_name,
#                                     "arguments": func_args_json,
#                                 },
#                                 "type": "function",
#                             }
#                         ],
#                         "content": None,
#                     }
#                 )

#                 # Run the tool and add its result
#                 print(func_args_json)
#                 func_response = handle_function_call(func_name, func_args_json)
#                 message_history.append(func_response)

#                 # Continue the loop so model can use the function result
#                 messages = message_history.copy()
#                 continue

#             # No tool call – clean up if model printed a bare ISO string
#             if ISO_REGEX.fullmatch(full_reply.strip()):
#                 full_reply = natural_dt(full_reply.strip())

#             message_history.append({"role": "assistant", "content": full_reply})
#             break  # finished streaming

#     return StreamingResponse(generate(), media_type="text/plain")
