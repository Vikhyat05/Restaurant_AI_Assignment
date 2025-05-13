## Setup Instructions

Follow these steps to set up the project locally:

---

### Step 1: Supabase Setup

1. Create a [Supabase](https://supabase.com/) project.
2. Create the following **tables**:

### `restaurants`

- Upload the provided CSV file
    
    📁 [**Download CSV**](https://docs.google.com/spreadsheets/d/1TnwtKM0kdpCcg-vMyiajkBSjqlop8n571Lgsptj5Lgw/edit?usp=sharing)
    

### `reservation`

| Column Name | Type |
| --- | --- |
| `id` | `uuid` |
| `created_at` | `timestamp with time zone` |
| `restaurant_id` | `text` |
| `datetime` | `timestamp with time zone` |
| `party_size` | `smallint` |
| `name` | `text` |
| `phone` | `text` |
| `special_requests` | `text` |


### Step 2: Groq API Setup

- Sign up at [Groq](https://console.groq.com/login).
- Generate an **API key**.


### Step 3: Create `.env` File

In the root of your project, create a `.env` file with the following variables:

```
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_key
SUPABASE_URL=your_supabase_project_url
GROQ_KEY=your_groq_api_key

```

### Step 4: Start Backend Server (Go in app folder)

```bash
uvicorn main:app --reload --port 8000

```


### Step 5: Open Frontend

Open `frontend/index.html` in your browser or serve it using a live server (e.g., VS Code Live Server Extension).

---


## Prompt Approach and Architecture 

| **Aspect** | **Design Choice** | **Rationale** |
|:-:|:-:|:-:|
| **Primary goals** | ① Find restaurants ② Book tables ③ Modify / cancel bookings | Directly maps to the three business-critical user journeys. |
| **Tone** | “Friendly and concise” | Aligns with FoodieSpot’s brand voice and keeps conversations short (mobile users). |
| **Error tolerance** | Zero tolerance for wrong bookings; ask follow-ups instead of guessing. | Reservations are high-stakes—wrong data costs revenue and trust. |

**High-Level Prompt Architecture**

1. **Role & Mission (first paragraph)**  *Anchors model identity (“Reservation Assistant”) and the three user needs.*
2. **TOOLS block** *Declares function signatures exactly as exposed by the FastAPI backend.* *Reason: lets the model auto-generate valid JSON when calling tools.*
3. **WHEN-TO-CALL sections** *Trigger logic written as bullet points → easy for the model to parse.* *Separates search vs. booking vs. management to avoid accidental calls.*
4. **Step-by-Step Post-Tool Instructions** *After search → iterate over* results*, then format them in Markdown.* *After booking → confirm and surface reservation ID.* *Ensures deterministic, user-friendly output.*
5. **Formatting & Validation Rules** *Normalize dates, times, never invent data, never show JSON to users.* *Reduces front-end sanitization work and prevents privacy leaks.*

---
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

---
## Business Strategy Summary – FoodieSpot AI Reservation Assistant

📁 [**Complete Case Document**](https://www.notion.so/Sarvam-Assignment-Generative-AI-Engineer-1f278e10361080f3ac28f2734037070b?pvs=4)

**North-Star Objective**

Make the assistant the default entry point for every dining decision, raising table-fill rates and average ticket size while cutting front-of-house labor.

### 1. Value Creation Levers

| Lever | How It Drives Business Impact |
| --- | --- |
| **Automation (≥ 95 % self-serve bookings)** | Reduces staffing costs and wait times; scales flawlessly across locations. |
| **Section-level capacity intelligence** | Maximizes seat utilization (e.g., rooftop vs. private room) and smooths demand peaks. |
| **Conversational upsell engine** | Context-aware add-ons (desserts, wine, birthday packages) lift average check. |
| **Unified customer profile** | Enables hyper-personalized offers and loyalty programs that boost repeat visits. |
| **Multilingual, multichannel reach** | Captures wider demographic (English, Hindi, Kannada on WhatsApp, web, voice). |


### 2. Success Metrics & ROI

| KPI | Financial Upside |
| --- | --- |
| Reservation automation rate | ↓ labor hours / shift |
| Avg. ticket uplift (upsells) | ↑ revenue / cover |
| Off-peak seat occupancy | Monetizes idle capacity |
| Post-interaction CSAT | Higher retention & referrals |


### 3. Roll-Out Playbook

1. **Pilot (2 outlets on WhatsApp)** – human shadowing, two-week test.
2. **A/B city roll-out (10 % traffic)** – benchmark conversion vs. human agents.
3. **Full city deployment** – add web chat & voice; weekly model tuning.
4. **Cross-city replication** – reuse multilingual layer, adapt menus.
5. **Continuous learning loop** – feed chat logs into fine-tunes for upsell and intent accuracy.


### 4. Expansion Horizons

- **Horizontal**: Other restaurant groups via white-label SaaS.
- **Vertical**: Cinemas, healthcare clinics, theme parks, EV-charging stations—any venue requiring time-slot or seat optimization.


### 5. Competitive Moats

1. **Granular seat-map intelligence** most rivals lack.
2. **Data-driven upsell playbook** tuned on historical spend.
3. **Rapid multilingual deployment kit** enabling new regions to go live in days.



By pairing real-time seat intelligence with a revenue-focused conversational layer, FoodieSpot can boost top-line growth, trim operating costs, and build a defensible data asset that powers expansion into adjacent booking-driven verticals.


---



**Limitations**
- No authentication system for users — reservations are open and not tied to a user account.
- **Seat-inventory race conditions** – Two users can book the same table in the same second; no transaction-level locking yet.
- **No notifications** – The system doesn’t send SMS / email confirmations or reminders.
- LLM may not gracefully handle ambiguous or incomplete user queries without further prompt engineering.

**Future Enhancements**
- **Google Maps integration** to show nearby restaurants and distance from user.
- **Calendar integration** to let users add reservations to Google Calendar and invite others.
- **Admin dashboard** to view/manage reservations, restaurant details, and customer data.
- **Multilingual support** via LLM prompting or translation layer.
- **Responsive mobile UI** or a native app for easier booking on the go.
- **Notifications** — Send reminders and confirmations via email/SMS.


