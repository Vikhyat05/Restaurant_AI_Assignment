from utils.supabase_utils import (
    search_restaurants,
    create_reservation,
    manage_reservation,
)
import json


def handle_function_call(name: str, args_json: str):
    """
    Dispatch an LLM function call to the correct Python helper
    and wrap its response in a valid function-role message.
    """

    try:
        args = json.loads(args_json) if args_json else {}
    except json.JSONDecodeError:
        args = {}

    if name == "search_restaurants":
        try:
            hits = search_restaurants(
                areas=args.get("areas"),
                cuisines=args.get("cuisines"),
                amenities=args.get("amenities"),
                seats=args.get("seats"),
                at_time=args.get("at_time"),
                on_day=args.get("on_day"),
                section=args.get("section"),
                min_score=args.get("min_score", 75),
            )

            print(hits)
            return {
                "role": "function",
                "name": name,
                "content": json.dumps(hits, default=str),
            }
        except Exception as e:
            return {
                "role": "function",
                "name": name,
                "content": json.dumps({"error": str(e)}),
            }

    elif name == "create_reservation":
        try:
            required_fields = [
                "restaurant_name",
                "date",
                "time",
                "am_pm",
                "party_size",
                "name",
                "phone",
            ]
            missing = [f for f in required_fields if not args.get(f)]
            if missing:
                return {
                    "role": "function",
                    "name": name,
                    "content": f"As user to please provide: {', '.join(missing)} to complete the reservation,.",
                }

            result = create_reservation(
                restaurant_name=args["restaurant_name"],
                date=args["date"],
                time=args["time"],
                am_pm=args["am_pm"],
                party_size=args["party_size"],
                name=args["name"],
                phone=args["phone"],
                special_requests=args.get("special_requests", "none"),
            )

            print(result)
            return {
                "role": "function",
                "name": name,
                "content": json.dumps(result, default=str),
            }

        except Exception as e:
            return {
                "role": "function",
                "name": name,
                "content": json.dumps({"success": False, "error": str(e)}),
            }

    elif name == "manage_reservation":
        try:
            reservation_id = args.get("reservation_id")
            action = args.get("action")

            if not reservation_id or not action:
                return {
                    "role": "function",
                    "name": name,
                    "content": "Please provide both reservation_id and action ('update' or 'delete').",
                }

            action = action.lower()
            if action not in ("update", "delete"):
                return {
                    "role": "function",
                    "name": name,
                    "content": "Action must be 'update' or 'delete'.",
                }

            if action == "update":
                updatable_keys = {
                    k: v
                    for k, v in args.items()
                    if k
                    in {
                        "restaurant_name",
                        "date",
                        "time",
                        "am_pm",
                        "party_size",
                        "name",
                        "phone",
                        "special_requests",
                    }
                    and v is not None
                }
                if not updatable_keys:
                    return {
                        "role": "function",
                        "name": name,
                        "content": "Which fields would you like to change? (e.g. time, party_size)",
                    }

            result = manage_reservation(**args)

            return {
                "role": "function",
                "name": name,
                "content": json.dumps(result, default=str),
            }

        except Exception as e:
            return {
                "role": "function",
                "name": name,
                "content": json.dumps({"success": False, "error": str(e)}),
            }

    else:
        return {
            "role": "function",
            "name": name,
            "content": json.dumps({"error": f"Unknown function: {name}"}),
        }
