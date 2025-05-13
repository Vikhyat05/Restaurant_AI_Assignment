### Prompt Approach and Architecture 

| **Aspect** | **Design Choice** | **Rationale** |
|:-:|:-:|:-:|
| **Primary goals** | ① Find restaurants ② Book tables ③ Modify / cancel bookings | Directly maps to the three business-critical user journeys. |
| **Tone** | “Friendly and concise” | Aligns with FoodieSpot’s brand voice and keeps conversations short (mobile users). |
| **Error tolerance** | Zero tolerance for wrong bookings; ask follow-ups instead of guessing. | Reservations are high-stakes—wrong data costs revenue and trust. |

**High-Level Prompt Architecture**

1. **Role & Mission (first paragraph)** *Anchors model identity (“Reservation Assistant”) and the three user needs.*
2. **TOOLS block** *Declares function signatures exactly as exposed by the FastAPI backend.* *Reason: lets the model auto-generate valid JSON when calling tools.*
3. **WHEN-TO-CALL sections** *Trigger logic written as bullet points → easy for the model to parse.* *Separates search vs. booking vs. management to avoid accidental calls.*
4. **Step-by-Step Post-Tool Instructions** *After search → iterate over* results*, then format them in Markdown.* *After booking → confirm and surface reservation ID.* *Ensures deterministic, user-friendly output.*
5. **Formatting & Validation Rules** *Normalize dates, times, never invent data, never show JSON to users.* *Reduces front-end sanitization work and prevents privacy leaks.*
