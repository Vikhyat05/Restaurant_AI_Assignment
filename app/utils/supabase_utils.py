import os
import pytz
from supabase import create_client, Client
from postgrest import APIError
from datetime import datetime, time
import json
from dotenv import load_dotenv
from rapidfuzz import fuzz
from postgrest import APIError
from utils.helper_utils import _lower_list, _to_time, _inside_range, _blank_to_none
from typing import Sequence, Union, List, Dict, Any, Optional
from datetime import datetime, time


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabaseSync: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


AreaInput = Union[str, Sequence[str]]
CuisineInput = Union[str, Sequence[str]]


def search_restaurants(
    *,
    areas: Optional[Union[str, Sequence[str]]] = None,
    cuisines: Optional[Union[str, Sequence[str]]] = None,
    amenities: Optional[Union[str, Sequence[str]]] = None,
    seats: Optional[int] = None,
    at_time: Optional[Union[str, datetime, time]] = None,
    on_day: Optional[str] = None,
    section: Optional[str] = None,
    min_score: int = 90,
) -> Dict[str, Any]:
    """
    Composite filter; honours only the parameters you pass and returns:

        {
          "result_count": 3,
          "results": [ …shaped restaurant dicts… ]
        }
    """

    areas = _blank_to_none(areas)
    cuisines = _blank_to_none(cuisines)
    amenities = _blank_to_none(amenities)
    at_time = _blank_to_none(at_time)
    on_day = _blank_to_none(on_day)
    section = _blank_to_none(section)
    seats = _blank_to_none(seats)

    if seats not in [None, ""]:
        try:
            seats = int(seats)
        except ValueError:
            return {
                "success": False,
                "restaurants": "Invalid party-size given; please use a number.",
            }

    area_list = _lower_list(areas) if areas else []
    cuisine_qs = _lower_list(cuisines) if cuisines else []
    amenity_qs = _lower_list(amenities) if amenities else []
    at_time_val = _to_time(at_time) if at_time not in [None, ""] else None

    if on_day in [None, ""]:
        on_day = datetime.now().astimezone().strftime("%a")
    on_day = on_day[:3].title()

    section_key = section.lower().strip() if section not in [None, ""] else None

    q = supabaseSync.table("restaurants").select("*")

    if area_list:
        q = q.or_(",".join(f"area.ilike.*{a}*" for a in area_list))

    if seats not in [None, ""]:
        q = q.gte("total_capacity", seats)

    try:
        rows: List[Dict] = q.execute().data or []
    except APIError as e:
        raise RuntimeError(f"Supabase error: {e.message}") from e

    def _tag_ok(queries: List[str], raw: str) -> bool:
        if not queries:
            return True
        tags = [t.strip().lower() for t in raw.split(";")]
        return any(
            max(fuzz.token_set_ratio(q, t) for t in tags) >= min_score for q in queries
        )

    def _tag_ok(queries: List[str], raw: str) -> bool:
        """
        Return True if *every* cuisine/amenity query has a strong
        match among the venue’s tags.

        • Uses token_sort_ratio (order-aware, keeps duplicates)
        • Falls back to exact-substring match first (fast & avoids fuzz errors)
        """
        if not queries:
            return True

        tags = [t.strip().lower() for t in raw.split(";")]

        def _best_score(q: str) -> int:
            q = q.strip().lower()
            for t in tags:
                if q == t:
                    return 100

            return max(fuzz.token_sort_ratio(q, t) for t in tags)

        return all(_best_score(q) >= min_score for q in queries)

    good: List[Dict[str, Any]] = []
    for r in rows:
        if not _tag_ok(cuisine_qs, r.get("cuisine", "")):
            continue
        if not _tag_ok(amenity_qs, r.get("amenities", "")):
            continue

        if at_time_val is not None:
            try:
                oh = r["opening_hours"]
                oh = json.loads(oh) if isinstance(oh, str) else oh
                hours = oh.get(on_day)
                if not hours:
                    continue
                start_s, end_s = hours.split("-")
                start_t, end_t = _to_time(start_s), _to_time(end_s or "00:00")
                if not _inside_range(at_time_val, start_t, end_t):
                    continue
            except Exception:
                continue

        if section_key:
            try:
                sections = (
                    r["sections"]
                    if isinstance(r["sections"], list)
                    else json.loads(r["sections"])
                )
            except Exception:
                continue
            matching = next(
                (s for s in sections if s.get("name", "").lower() == section_key), None
            )
            if not matching:
                continue
            if seats not in [None, ""]:
                seat_total = matching.get("capacity")
                if seat_total is not None and seat_total < seats:
                    continue

        good.append(_shape_row(r))

    if not good:
        return {
            "success": False,
            "restaurants": "There are no restaurants available based on your criteria.",
        }

    return {"success": True, "result_count": len(good), "results": good}


def create_reservation(
    *,
    restaurant_name: str,
    date: str,  # "2025-05-12"
    time: str,  # "7:30" or "18:00"
    am_pm: str = "",  # "" = 24-h, otherwise "AM"/"PM"
    party_size: int,
    name: str,
    phone: str,
    special_requests: Optional[str] = None,
    section: Optional[str] = None,  # NEW ⬅
) -> Dict:
    """
    Insert a reservation only if the requested party_size fits
    (a) the chosen section, else (b) any other section, else (c) the venue.

    • Accepts 12-h or 24-h time strings.
    • Converts IST → UTC for storage.
    • Capacity check order:
        1. Requested section (if given)
        2. Any other section that can fit
        3. Restaurant total_capacity
    """

    # ---------- 0️⃣  validate input -----------------------------------------
    try:
        party_size = int(party_size)
    except ValueError:
        return {"success": False, "error": "Invalid party size provided."}

    sec_key = section.lower().strip() if section not in [None, ""] else None

    # ---------- 1️⃣  fetch restaurant meta ----------------------------------
    try:
        resp = (
            supabaseSync.table("restaurants")
            .select("restaurant_id, total_capacity, sections")
            .ilike("name", restaurant_name)
            .execute()
        )
    except Exception as e:
        return {"success": False, "error": f"Supabase error: {e}"}

    if not resp.data:
        return {"success": False, "error": "Restaurant not found."}

    r = resp.data[0]
    restaurant_id = r["restaurant_id"]
    total_capacity = r.get("total_capacity")  # may be None
    sections_raw = r.get("sections") or []  # list[dict] or json str

    # normalise sections → list[dict]
    try:
        sections = (
            sections_raw if isinstance(sections_raw, list) else json.loads(sections_raw)
        )
    except Exception:
        sections = []

    # ---------- 2️⃣  section-level checks -----------------------------------
    def _find_section(name: str):
        return next((s for s in sections if s.get("name", "").lower() == name), None)

    # 2a. If a section is requested, check its capacity first
    if sec_key:
        sel = _find_section(sec_key)
        if not sel:
            return {
                "success": False,
                "error": f"The section “{section}” doesn’t exist at this restaurant.",
            }

        sel_cap = sel.get("capacity")
        if sel_cap is not None and party_size > sel_cap:
            # 2b. Look for any *other* section that can fit
            alternatives = [
                s["name"]
                for s in sections
                if s.get("capacity") and party_size <= s["capacity"]
            ]

            if alternatives:
                return {
                    "success": False,
                    "error": (
                        f"The {section} section can seat only {sel_cap} guests, "
                        f"but your party has {party_size}. "
                        f"Would you like to book in {', '.join(alternatives)} instead?"
                    ),
                }
            # 2c. No section can fit
            return {
                "success": False,
                "error": (
                    f"Sorry, none of our sections can accommodate a party of "
                    f"{party_size} at {restaurant_name}."
                ),
            }

    # 2d. No specific section requested → find any that fits
    if not sec_key and sections:
        fits_any = any(
            s.get("capacity") and party_size <= s["capacity"] for s in sections
        )
        if not fits_any:
            return {
                "success": False,
                "error": (
                    f"Sorry, none of our sections can accommodate a party of "
                    f"{party_size} at {restaurant_name}."
                ),
            }

    # ---------- 3️⃣  venue-level capacity fallback --------------------------
    if total_capacity is not None and party_size > total_capacity:
        return {
            "success": False,
            "error": (
                f"Requested party size ({party_size}) exceeds the restaurant’s "
                f"overall capacity ({total_capacity})."
            ),
        }

    # ---------- 4️⃣  build UTC datetime -------------------------------------
    ist = pytz.timezone("Asia/Kolkata")
    try:
        dt_str = f"{date} {time} {am_pm.upper()}".strip()
        dt_naive = datetime.strptime(dt_str, "%Y-%m-%d %I:%M %p")
    except ValueError:
        dt_str = f"{date} {time}"
        dt_naive = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    dt_ist = ist.localize(dt_naive)
    dt_utc = dt_ist.astimezone(pytz.utc)

    # ---------- 5️⃣  write reservation --------------------------------------
    try:
        insert_resp = (
            supabaseSync.table("reservation")
            .insert(
                {
                    "restaurant_id": restaurant_id,
                    "datetime": dt_utc.isoformat(),
                    "party_size": party_size,
                    "name": name,
                    "phone": phone,
                    "special_requests": special_requests or "none",
                    "section": section or "unspecified",  # optional: store it
                }
            )
            .execute()
        )
    except Exception as e:
        return {"success": False, "error": f"Supabase error: {e}"}

    if insert_resp.data:
        return {"success": True, "reservation": insert_resp.data[0]}
    return {"success": False, "error": insert_resp.error.message}


def manage_reservation(
    *,
    reservation_id: str,
    action: str,
    restaurant_name: Optional[str] = None,
    date: Optional[str] = None,
    time: Optional[str] = None,
    am_pm: Optional[str] = None,
    party_size: Optional[int] = None,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    special_requests: Optional[str] = None,
) -> Dict:
    """
    Update or delete an existing reservation.
    • `reservation_id`  – UUID/string primary key of the row in `reservation`.
    • `action`          – "update" or "delete".
    • Other parameters  – Only relevant for updates; omit any you don’t want
                          to change.

    Returns {"success": bool, "...": ...} just like create_reservation.
    """
    try:
        action = action.lower()
        if action not in ("update", "delete"):
            return {"success": False, "error": "action must be 'update' or 'delete'."}

        exist_resp = (
            supabaseSync.table("reservation")
            .select("*")
            .eq("id", reservation_id)
            .execute()
        )
        if not exist_resp.data:
            return {"success": False, "error": "Reservation not found."}

        if action == "delete":
            del_resp = (
                supabaseSync.table("reservation")
                .delete()
                .eq("id", reservation_id)
                .execute()
            )
            if del_resp.data:
                return {"success": True, "deleted": del_resp.data[0]}
            return {"success": False, "error": del_resp.error.message}

        update_fields = {}

        if restaurant_name:
            rest_resp = (
                supabaseSync.table("restaurants")
                .select("restaurant_id")
                .ilike("name", restaurant_name)
                .execute()
            )
            if not rest_resp.data:
                return {"success": False, "error": "Restaurant not found."}
            update_fields["restaurant_id"] = rest_resp.data[0]["restaurant_id"]

        if date or time or am_pm:
            current_dt = datetime.fromisoformat(exist_resp.data[0]["datetime"])
            ist = pytz.timezone("Asia/Kolkata")
            current_dt = current_dt.astimezone(ist)

            new_date = date or current_dt.strftime("%Y-%m-%d")
            new_time = time or current_dt.strftime("%I:%M")
            new_am_pm = (am_pm or current_dt.strftime("%p")).upper()

            dt_str = f"{new_date} {new_time} {new_am_pm}"
            dt_naive = datetime.strptime(dt_str, "%Y-%m-%d %I:%M %p")
            dt_ist = ist.localize(dt_naive)
            dt_utc = dt_ist.astimezone(pytz.utc)
            update_fields["datetime"] = dt_utc.isoformat()

        if party_size is not None:
            update_fields["party_size"] = party_size
        if name is not None:
            update_fields["name"] = name
        if phone is not None:
            update_fields["phone"] = phone
        if special_requests is not None:
            update_fields["special_requests"] = special_requests

        if not update_fields:
            return {"success": False, "error": "No fields to update."}

        upd_resp = (
            supabaseSync.table("reservation")
            .update(update_fields)
            .eq("id", reservation_id)
            .execute()
        )

        if upd_resp.data:
            return {"success": True, "reservation": upd_resp.data[0]}
        return {"success": False, "error": upd_resp.error.message}

    except Exception as e:
        return {"success": False, "error": str(e)}


def _shape_row(r: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a raw DB row into a clean, typed structure that is
    easy for the chat model to read & summarise.
    """
    sections = (
        json.loads(r["sections"]) if isinstance(r["sections"], str) else r["sections"]
    )
    opening = (
        json.loads(r["opening_hours"])
        if isinstance(r["opening_hours"], str)
        else r["opening_hours"]
    )

    cuisine_list = [c.strip() for c in r["cuisine"].split(";") if c.strip()]
    amenities_list = [a.strip() for a in r["amenities"].split(";") if a.strip()]

    return {
        "id": r["restaurant_id"],
        "name": r["name"],
        "area": r["area"],
        "cuisine": cuisine_list,
        "amenities": amenities_list,
        "rating": r["rating"],
        "opening_hours": opening,
        "sections": sections,
        "total_capacity": r["total_capacity"],
    }
