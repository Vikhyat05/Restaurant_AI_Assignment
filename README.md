## Prompt Approach and Architecture 

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


## Example conversations showing different user journeys

Below are four **illustrative chat transcripts** that cover the core user journeys your prompt is designed to handle. They mirror the screenshots you shared while making the tool-call logic visible (commented in *italics* for clarity). Feel free to copy-paste these into your submission.

#### Journey A – Search with no exact matches ➜ graceful fallback
**Goal:** User wants North-Indian food + rooftop seating. No venue satisfies both, so the assistant suggests the closest alternative.
| **User**      | “Can you suggest me restaurants that offer North-Indian food **with wifi**?” |
|:-------------:|:------------------------------------------------------------:|
| **Assistant** | *(calls* search_restaurants *with `cuisines=["north indian"], amenities=[“wifi”])*“I couldn’t find a venue that has both North-Indian cuisine and a rooftop area. One option that fits the cuisine (but not rooftop) is **FoodieSpot Indiranagar**. If you’re flexible on seating, would you like more details or other areas?” |


#### Journey B – Search with amenity filter ➜ list of matches
**Goal:** User wants North-Indian food **and** pet-friendly venues.
| **User**      | “Can you suggest a good restaurant that offers North Indian food **and is pet-friendly**?” |
|:-------------:|:------------------------------------------------------------:|
| **Assistant** | *(calls* search_restaurants *with `cuisines=["north indian"], amenities=["pet friendly"])*“Here are some great options:• **FoodieSpot Indiranagar** – North Indian & Chinese Fusion – rooftop, pet-friendly, vegan options – rating 3.8/5.• **FoodieSpot Brookefield** – North Indian & Mughlai – pet-friendly, cocktail bar – rating 4.6/5.Would you like to know more or book a table?” |


#### Journey C – Search ➜ pick venue ➜ collect missing fields ➜ book
**Goal:** User asks for North-Indian places, chooses one, and books for 25 May.
| **User**      | “Suggest some good restaurants that offer North-Indian food.” |
|:-------------:|:------------------------------------------------------------:|
| **Assistant** | *(*search_restaurants → returns 4 venues*)*“Here are some options … (1) FoodieSpot Indiranagar … (2) FoodieSpot Koramangala … Which one appeals to you?” |
| **User**      | “Book a table for **5** at **FoodieSpot Indiranagar** on **25 May** at **6 pm**.” |
| **Assistant** | “Great! May I have the **name** the reservation should be under and a **phone number** I can reach you on?” |
| **User**      | “Vikhyat, 96298 88032.”                                      |
| **Assistant** | *(calls* create_reservation *with complete payload)*“All set! Your table for **5** at **FoodieSpot Indiranagar** is confirmed for **25 May at 6:00 PM**. Your reservation ID is **e2db0484-1c1e-48c4-81a6-ec7d822aa18a**. Keep this ID handy in case you need to modify or cancel.” |

#### Journey D – Modify an existing reservation
**Goal:** User has an ID and wants to move the time from 6 PM to 4 PM on the same day.
| **User**      | “Hey, I’d like to modify my reservation—can you do it for me?” |
|:-------------:|:------------------------------------------------------------:|
| **Assistant** | “Sure! Could you share your reservation ID and tell me what you’d like to change (date, time, party size, etc.)?” |
| **User**      | “My ID is **e2db0484-1c1e-48c4-81a6-ec7d822aa18a**. Change the time from **6 PM to 4 PM**.” |
| **Assistant** | *(calls* manage_reservation *with* action="update", reservation_id=…, time="4:00", am_pm="PM"*)*“Done! Your table is now at **4:00 PM** on **25 May** for **5 people** at **FoodieSpot Indiranagar**. The reservation ID remains the same. Anything else I can help with?” |
