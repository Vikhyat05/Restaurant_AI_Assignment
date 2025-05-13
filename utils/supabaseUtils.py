# import os
# import pytz
# from supabase import create_client, Client
# from postgrest import APIError
# from datetime import datetime, time
# import json
# from dotenv import load_dotenv
# from rapidfuzz import fuzz
# from postgrest import APIError
# from utils.helper import _lower_list, _to_time, _inside_range
# from typing import Sequence, Union, List, Dict, Any, Optional
# from datetime import datetime, time


# load_dotenv()

# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# supabaseSync: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


# AreaInput = Union[str, Sequence[str]]
# CuisineInput = Union[str, Sequence[str]]


# # ──────────────────────────────────────────────────────────────
# #  SEARCH TOOL  —  returns model-friendly JSON
# # ──────────────────────────────────────────────────────────────


# def search_restaurants(
#     *,
#     areas: Optional[Union[str, Sequence[str]]] = None,
#     cuisines: Optional[Union[str, Sequence[str]]] = None,
#     amenities: Optional[Union[str, Sequence[str]]] = None,
#     seats: Optional[int] = None,  # party size
#     at_time: Optional[Union[str, datetime, time]] = None,  # "19:30", datetime, ...
#     on_day: Optional[str] = None,  # "Mon", "Tue", …
#     section: Optional[str] = None,
#     min_score: int = 90,
# ) -> Dict[str, Any]:
#     """
#     Composite filter; honours only the parameters you pass and returns:

#         {
#           "result_count": 3,
#           "results": [ …shaped restaurant dicts… ]
#         }
#     """

#     # -------- 1️⃣  normalise inputs -----------------------------------------
#     if seats not in [None, ""]:
#         try:
#             seats = int(seats)
#         except ValueError:
#             return {
#                 "success": False,
#                 "restaurants": "Invalid party-size given; please use a number.",
#             }

#     area_list = _lower_list(areas) if areas else []
#     cuisine_qs = _lower_list(cuisines) if cuisines else []
#     amenity_qs = _lower_list(amenities) if amenities else []
#     at_time_val = _to_time(at_time) if at_time not in [None, ""] else None

#     if on_day in [None, ""]:
#         on_day = datetime.now().astimezone().strftime("%a")  # "Mon"
#     on_day = on_day[:3].title()  # normalise to "Mon"

#     section_key = section.lower().strip() if section not in [None, ""] else None

#     # -------- 2️⃣  build server-side filters --------------------------------
#     q = supabaseSync.table("restaurants").select("*")

#     if area_list:
#         q = q.or_(",".join(f"area.ilike.*{a}*" for a in area_list))

#     if seats not in [None, ""]:
#         q = q.gte("total_capacity", seats)

#     try:
#         rows: List[Dict] = q.execute().data or []
#     except APIError as e:
#         raise RuntimeError(f"Supabase error: {e.message}") from e

#     # -------- 3️⃣  client-side refinements ----------------------------------
#     def _tag_ok(queries: List[str], raw: str) -> bool:
#         if not queries:
#             return True
#         tags = [t.strip().lower() for t in raw.split(";")]
#         return any(
#             max(fuzz.token_set_ratio(q, t) for t in tags) >= min_score for q in queries
#         )

#     def _tag_ok(queries: List[str], raw: str) -> bool:
#         """
#         Return True if *every* cuisine/amenity query has a strong
#         match among the venue’s tags.

#         • Uses token_sort_ratio (order-aware, keeps duplicates)
#         • Falls back to exact-substring match first (fast & avoids fuzz errors)
#         """
#         if not queries:
#             return True

#         tags = [t.strip().lower() for t in raw.split(";")]

#         def _best_score(q: str) -> int:
#             q = q.strip().lower()
#             for t in tags:
#                 if q == t:  # perfect hit
#                     return 100
#             # order-aware similarity
#             return max(fuzz.token_sort_ratio(q, t) for t in tags)

#         # ✔ require *all* query tokens to clear the bar
#         return all(_best_score(q) >= min_score for q in queries)

#     good: List[Dict[str, Any]] = []
#     for r in rows:
#         if not _tag_ok(cuisine_qs, r.get("cuisine", "")):
#             continue
#         if not _tag_ok(amenity_qs, r.get("amenities", "")):
#             continue

#         # opening-hours filter
#         if at_time_val is not None:
#             try:
#                 oh = r["opening_hours"]
#                 oh = json.loads(oh) if isinstance(oh, str) else oh
#                 hours = oh.get(on_day)  # e.g. "11:00-23:00"
#                 if not hours:
#                     continue
#                 start_s, end_s = hours.split("-")
#                 start_t, end_t = _to_time(start_s), _to_time(end_s or "00:00")
#                 if not _inside_range(at_time_val, start_t, end_t):
#                     continue
#             except Exception:
#                 continue  # malformed JSON/time → reject

#         # section-specific capacity filter
#         if section_key:
#             try:
#                 sections = (
#                     r["sections"]
#                     if isinstance(r["sections"], list)
#                     else json.loads(r["sections"])
#                 )
#             except Exception:
#                 continue
#             matching = next(
#                 (s for s in sections if s.get("name", "").lower() == section_key), None
#             )
#             if not matching:
#                 continue
#             if seats not in [None, ""]:
#                 seat_total = matching.get("capacity")
#                 if seat_total is not None and seat_total < seats:
#                     continue

#         good.append(_shape_row(r))  # <<— shaped

#     # -------- 4️⃣  return payload -------------------------------------------
#     if not good:
#         return {
#             "success": False,
#             "restaurants": "There are no restaurants available based on your criteria.",
#         }

#     return {"success": True, "result_count": len(good), "results": good}


# def create_reservation(
#     *,
#     restaurant_name: str,
#     date: str,  # "2025-05-12"
#     time: str,  # "7:30" or "18:00"
#     am_pm: str = "",  # "" for 24-h; otherwise "AM"/"PM"
#     party_size: int,
#     name: str,
#     phone: str,
#     special_requests: Optional[str] = None,
# ) -> Dict:
#     """
#     Insert a reservation only if the requested party_size fits the venue.

#     • Accepts both 12-h and 24-h time strings.
#     • Converts IST → UTC for storage.
#     • Capacity check:
#         – compares party_size against restaurants.total_capacity
#         – if exceeded, returns {"success": False, "error": "..."}
#     """

#     try:
#         party_size = int(party_size)
#     except ValueError:
#         return {"success": False, "error": "Invalid party size provided."}
#     try:
#         # ── 1️⃣  Fetch restaurant + capacity ────────────────────────────────
#         resp = (
#             supabaseSync.table("restaurants")
#             .select("restaurant_id, total_capacity")
#             .ilike("name", restaurant_name)
#             .execute()
#         )

#         if not resp.data:
#             return {"success": False, "error": "Restaurant not found."}

#         r = resp.data[0]
#         restaurant_id = r["restaurant_id"]
#         total_capacity = r.get("total_capacity")  # may be None
#         print(type(party_size))
#         print(type(total_capacity))

#         # ── 2️⃣  Guard: capacity exceeded? ───────────────────────────────────
#         if total_capacity is not None and party_size > total_capacity:
#             return {
#                 "success": False,
#                 "error": (
#                     f"Requested party size ({party_size}) exceeds "
#                     f"the restaurant’s capacity ({total_capacity})."
#                 ),
#             }

#         # ── 3️⃣  Parse local IST time → UTC ─────────────────────────────────
#         ist = pytz.timezone("Asia/Kolkata")

#         try:
#             # first try 12-hour with AM/PM
#             dt_str = f"{date} {time} {am_pm.upper()}".strip()
#             dt_naive = datetime.strptime(dt_str, "%Y-%m-%d %I:%M %p")
#         except ValueError:
#             # fallback to 24-hour
#             dt_str = f"{date} {time}"
#             dt_naive = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")

#         dt_ist = ist.localize(dt_naive)
#         dt_utc = dt_ist.astimezone(pytz.utc)

#         # ── 4️⃣  Insert reservation ─────────────────────────────────────────
#         insert_resp = (
#             supabaseSync.table("reservation")
#             .insert(
#                 {
#                     "restaurant_id": restaurant_id,
#                     "datetime": dt_utc.isoformat(),
#                     "party_size": party_size,
#                     "name": name,
#                     "phone": phone,
#                     "special_requests": special_requests or "none",
#                 }
#             )
#             .execute()
#         )

#         if insert_resp.data:
#             return {"success": True, "reservation": insert_resp.data[0]}
#         else:
#             return {"success": False, "error": insert_resp.error.message}

#     except Exception as e:
#         return {"success": False, "error": str(e)}


# def manage_reservation(
#     *,
#     reservation_id: str,
#     action: str,  # "update" | "delete"
#     # ――― fields below are OPTIONAL and used only when action == "update" ―――
#     restaurant_name: Optional[str] = None,
#     date: Optional[str] = None,  # "YYYY-MM-DD"
#     time: Optional[str] = None,  # "7:30"
#     am_pm: Optional[str] = None,  # "AM" | "PM"
#     party_size: Optional[int] = None,
#     name: Optional[str] = None,
#     phone: Optional[str] = None,
#     special_requests: Optional[str] = None,
# ) -> Dict:
#     """
#     Update or delete an existing reservation.
#     • `reservation_id`  – UUID/string primary key of the row in `reservation`.
#     • `action`          – "update" or "delete".
#     • Other parameters  – Only relevant for updates; omit any you don’t want
#                           to change.

#     Returns {"success": bool, "...": ...} just like create_reservation.
#     """
#     try:
#         # ------------------------------------------------------------------
#         # Sanity checks
#         # ------------------------------------------------------------------
#         action = action.lower()
#         if action not in ("update", "delete"):
#             return {"success": False, "error": "action must be 'update' or 'delete'."}

#         # ------------------------------------------------------------------
#         # Make sure the reservation exists
#         # ------------------------------------------------------------------
#         exist_resp = (
#             supabaseSync.table("reservation")
#             .select("*")
#             .eq("id", reservation_id)
#             .execute()
#         )
#         if not exist_resp.data:
#             return {"success": False, "error": "Reservation not found."}

#         # ------------------------------------------------------------------
#         # DELETE
#         # ------------------------------------------------------------------
#         if action == "delete":
#             del_resp = (
#                 supabaseSync.table("reservation")
#                 .delete()
#                 .eq("id", reservation_id)
#                 .execute()
#             )
#             if del_resp.data:
#                 return {"success": True, "deleted": del_resp.data[0]}
#             return {"success": False, "error": del_resp.error.message}

#         # ------------------------------------------------------------------
#         # UPDATE
#         # ------------------------------------------------------------------
#         update_fields = {}

#         # 1️⃣  If restaurant_name changes, map → restaurant_id
#         if restaurant_name:
#             rest_resp = (
#                 supabaseSync.table("restaurants")
#                 .select("restaurant_id")
#                 .ilike("name", restaurant_name)
#                 .execute()
#             )
#             if not rest_resp.data:
#                 return {"success": False, "error": "Restaurant not found."}
#             update_fields["restaurant_id"] = rest_resp.data[0]["restaurant_id"]

#         # 2️⃣  If any date/time component provided, rebuild datetime
#         if date or time or am_pm:
#             # Fall back to current values for missing parts
#             current_dt = datetime.fromisoformat(exist_resp.data[0]["datetime"])
#             ist = pytz.timezone("Asia/Kolkata")
#             current_dt = current_dt.astimezone(ist)

#             new_date = date or current_dt.strftime("%Y-%m-%d")
#             new_time = time or current_dt.strftime("%I:%M")
#             new_am_pm = (am_pm or current_dt.strftime("%p")).upper()

#             dt_str = f"{new_date} {new_time} {new_am_pm}"
#             dt_naive = datetime.strptime(dt_str, "%Y-%m-%d %I:%M %p")
#             dt_ist = ist.localize(dt_naive)
#             dt_utc = dt_ist.astimezone(pytz.utc)
#             update_fields["datetime"] = dt_utc.isoformat()

#         # 3️⃣  Simple scalar fields
#         if party_size is not None:
#             update_fields["party_size"] = party_size
#         if name is not None:
#             update_fields["name"] = name
#         if phone is not None:
#             update_fields["phone"] = phone
#         if special_requests is not None:
#             update_fields["special_requests"] = special_requests

#         if not update_fields:
#             return {"success": False, "error": "No fields to update."}

#         upd_resp = (
#             supabaseSync.table("reservation")
#             .update(update_fields)
#             .eq("id", reservation_id)
#             .execute()
#         )

#         if upd_resp.data:
#             return {"success": True, "reservation": upd_resp.data[0]}
#         return {"success": False, "error": upd_resp.error.message}

#     except Exception as e:
#         return {"success": False, "error": str(e)}


# def _shape_row(r: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Convert a raw DB row into a clean, typed structure that is
#     easy for the chat model to read & summarise.
#     """
#     # Parse nested JSON strings (if not already parsed)
#     sections = (
#         json.loads(r["sections"]) if isinstance(r["sections"], str) else r["sections"]
#     )
#     opening = (
#         json.loads(r["opening_hours"])
#         if isinstance(r["opening_hours"], str)
#         else r["opening_hours"]
#     )

#     # Split compound columns into lists
#     cuisine_list = [c.strip() for c in r["cuisine"].split(";") if c.strip()]
#     amenities_list = [a.strip() for a in r["amenities"].split(";") if a.strip()]

#     return {
#         "id": r["restaurant_id"],
#         "name": r["name"],
#         "area": r["area"],
#         "cuisine": cuisine_list,  # list[str]
#         "amenities": amenities_list,  # list[str]
#         "rating": r["rating"],  # float
#         "opening_hours": opening,  # dict[day -> "hh:mm-hh:mm"]
#         "sections": sections,  # list[ {name, capacity} ]
#         "total_capacity": r["total_capacity"],
#     }
