FUNCTION_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "search_restaurants",
            "description": "Query restaurants details that satisfy the details or prefrences that the user has provided so far.",
            "parameters": {
                "type": "object",
                "properties": {
                    "areas": {
                        "type": "string",
                        "description": "Area or comma-separated list, e.g. 'Koramangala, Indiranagar'",
                    },
                    "cuisines": {
                        "type": "string",
                        "description": "Cuisine or list, e.g. 'North Indian;Chinese Fusion'",
                    },
                    "amenities": {
                        "type": "string",
                        "description": "Amenity keywords, e.g. 'rooftop;live-music'",
                    },
                    "seats": {"type": "integer", "description": "Party size (≥1)"},
                    "at_time": {
                        "type": "string",
                        "description": "Desired time in 'HH:MM' 24-h format",
                    },
                    "on_day": {
                        "type": "string",
                        "description": "Day of week as 3-letter code, e.g. 'Fri'",
                    },
                    "section": {
                        "type": "string",
                        "description": "Seating section preference. Can take only 3 values 'outdoor‑patio', 'indoor‑ac', 'private‑room'",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_reservation",
            "description": "Create a restaurant reservation with the specified details",
            "parameters": {
                "type": "object",
                "properties": {
                    "restaurant_name": {
                        "type": "string",
                        "description": "Exact restaurant name from search results",
                    },
                    "date": {
                        "type": "string",
                        "description": "Reservation date in YYYY-MM-DD format",
                    },
                    "time": {
                        "type": "string",
                        "description": "Reservation time in H:MM format, e.g. '7:30'",
                    },
                    "am_pm": {
                        "type": "string",
                        "description": "AM or PM",
                        "enum": ["AM", "PM"],
                    },
                    "party_size": {
                        "type": "integer",
                        "description": "Number of people in the party",
                    },
                    "name": {"type": "string", "description": "Customer's name"},
                    "phone": {
                        "type": "string",
                        "description": "Customer's phone number",
                    },
                    "special_requests": {
                        "type": "string",
                        "description": "Any special requests or 'none' if not provided",
                    },
                    "section": {
                        "type": "string",
                        "description": "Seating section preference. Can take only 3 values 'outdoor‑patio', 'indoor‑ac', 'private‑room'",
                    },
                },
                "required": [
                    "restaurant_name",
                    "date",
                    "time",
                    "am_pm",
                    "party_size",
                    "name",
                    "phone",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_reservation",
            "description": "Update or cancel an existing reservation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_id": {
                        "type": "string",
                        "description": "Reservation identifier returned when the booking was created",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["update", "delete"],
                        "description": "'update' to change fields, 'delete' to cancel",
                    },
                    "restaurant_name": {"type": "string"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "am_pm": {"type": "string", "enum": ["AM", "PM"]},
                    "party_size": {"type": "integer"},
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "special_requests": {"type": "string"},
                },
                "required": ["reservation_id", "action"],
            },
        },
    },
]
