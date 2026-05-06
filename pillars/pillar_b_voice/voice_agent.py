import sys
import json
import re
from pathlib import Path
from enum import Enum
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.logger import log


class VoiceState(Enum):
    GREETING = "greeting"
    DISCLAIMER = "disclaimer"
    TOPIC_SELECT = "topic_select"
    TIME_PREFERENCE = "time_preference"
    SLOT_OFFER = "slot_offer"
    CONFIRMATION = "confirmation"
    BOOKED = "booked"
    FAILED = "failed"


TOPICS = [
    "KYC/Onboarding",
    "SIP/Mandates",
    "Statements/Tax Docs",
    "Withdrawals/Timelines",
    "Account Changes/Nominee",
]

THEME_CODES = {
    "technical": "TECH",
    "customer support": "SUPP",
    "ui/ux": "UIUX",
    "payment": "PAYM",
    "fund": "FUND",
    "account": "ACCT",
    "login": "LOGN",
    "withdrawal": "WDRL",
    "default": "GENR",
}

def _parse_date(text: str) -> str:
    """Parse natural language date into YYYY-MM-DD. Falls back to tomorrow."""
    import re
    from datetime import timedelta, date as _date

    text_l = text.lower().strip()
    today  = datetime.now(timezone.utc).date()

    if "today" in text_l:
        return today.strftime("%Y-%m-%d")
    if "tomorrow" in text_l:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")

    day_names = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    for i, d in enumerate(day_names):
        if d in text_l:
            ahead = i - today.weekday()
            if ahead <= 0:
                ahead += 7
            return (today + timedelta(days=ahead)).strftime("%Y-%m-%d")

    m = re.search(r'in\s+(\d+)\s+days?', text_l)
    if m:
        return (today + timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")
    if "next week" in text_l:
        return (today + timedelta(days=7)).strftime("%Y-%m-%d")

    month_map = {
        "jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
        "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
        "january":1,"february":2,"march":3,"april":4,"june":6,
        "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    }
    for mname, mnum in month_map.items():
        pat = rf'(\d{{1,2}})(?:st|nd|rd|th)?\s+{mname}|{mname}\s+(\d{{1,2}})(?:st|nd|rd|th)?'
        m = re.search(pat, text_l)
        if m:
            day_n = int(m.group(1) or m.group(2))
            yr = today.year
            try:
                from datetime import date as _d
                target = _d(yr, mnum, day_n)
                if target < today:
                    target = _d(yr + 1, mnum, day_n)
                return target.strftime("%Y-%m-%d")
            except ValueError:
                pass

    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', text_l)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    return (today + timedelta(days=1)).strftime("%Y-%m-%d")


def _slots_for_date(date_str: str) -> list[dict]:
    return [
        {"date": date_str, "time": "10:00 AM IST", "advisor": "Advisor A"},
        {"date": date_str, "time": "02:30 PM IST", "advisor": "Advisor B"},
    ]


class VoiceAgent:
    def __init__(self, top_theme: str = "general", pulse_themes: list = None):
        self.state = VoiceState.GREETING
        self.top_theme = top_theme
        self.topic = None
        self.time_pref = None
        self.selected_slot = None
        self.booking_code = None
        self.turn_count = 0
        self.transcript = []
        self.available_slots = []
        # Extended topic list: structured TOPICS + top pulse themes (deduped)
        extra = [t["name"] for t in (pulse_themes or [])[:3]]
        self.all_topics = TOPICS + [e for e in extra if e not in TOPICS]

    def _gen_booking_code(self) -> str:
        theme_code = "GENR"
        for key, code in THEME_CODES.items():
            if key in self.top_theme.lower():
                theme_code = code
                break
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        seq = str(self.turn_count).zfill(3)
        return f"IND-{theme_code}-{date_str}-{seq}"

    def process_turn(self, user_input: str) -> dict:
        self.turn_count += 1
        user_input = user_input.strip()
        self.transcript.append({"role": "user", "text": user_input})

        response = ""
        next_state = self.state

        if self.state == VoiceState.GREETING:
            response = (
                f"Welcome to INDmoney Advisor Scheduling. "
                f"I notice many users are asking about {self.top_theme} today — "
                f"I can help you book a call for that! "
                f"Before we proceed, please note: this is an informational service only, "
                f"not investment advice. Shall I continue?"
            )
            next_state = VoiceState.DISCLAIMER

        elif self.state == VoiceState.DISCLAIMER:
            if any(w in user_input.lower() for w in ["yes", "sure", "ok", "continue", "proceed"]):
                structured = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(TOPICS))
                pulse_extra = self.all_topics[len(TOPICS):]
                pulse_block = ""
                if pulse_extra:
                    start = len(TOPICS) + 1
                    pulse_lines = "\n".join(
                        f"  {start + i}. {t}  [Trending]"
                        for i, t in enumerate(pulse_extra)
                    )
                    pulse_block = f"\nCurrently trending from Weekly Pulse:\n{pulse_lines}"
                response = (
                    f"What topic would you like to discuss with an advisor?\n"
                    f"{structured}{pulse_block}\n"
                    f"Please choose a number or describe your topic."
                )
                next_state = VoiceState.TOPIC_SELECT
            else:
                response = "No problem. Feel free to call back anytime. Goodbye!"
                next_state = VoiceState.FAILED

        elif self.state == VoiceState.TOPIC_SELECT:
            # Check for investment advice
            if any(w in user_input.lower() for w in ["should i invest", "recommend", "best fund", "buy", "sell"]):
                response = "I cannot provide investment advice. For guidance, please visit https://www.amfiindia.com/investor/knowledge-center-info. Would you like to book an advisor call instead?"
                # Stay in TOPIC_SELECT, don't advance
            else:
                # Try to match topic by number or keyword against full topic list
                matched = None
                try:
                    idx = int(user_input.strip()) - 1
                    if 0 <= idx < len(self.all_topics):
                        matched = self.all_topics[idx]
                except ValueError:
                    for t in self.all_topics:
                        words = t.lower().replace("/", " ").replace("&", " ").split()
                        if any(word in user_input.lower() for word in words if len(word) > 3):
                            matched = t
                            break

                if matched:
                    self.topic = matched
                    response = f"Got it — {matched}. When would you prefer the call? (e.g., 'tomorrow', 'Monday afternoon')"
                    next_state = VoiceState.TIME_PREFERENCE
                else:
                    response = f"I didn't catch that. Please choose a number (1–{len(self.all_topics)}) or describe your topic."
                    # Stay in TOPIC_SELECT

        elif self.state == VoiceState.TIME_PREFERENCE:
            self.time_pref = user_input
            target_date = _parse_date(user_input)
            self.available_slots = _slots_for_date(target_date)
            slots_str = "\n".join(
                f"  Slot {i+1}: {s['date']} at {s['time']} with {s['advisor']}"
                for i, s in enumerate(self.available_slots)
            )
            response = (
                f"Based on your preference, here are two available slots:\n"
                f"{slots_str}\n"
                f"Which slot works for you? (1 or 2)"
            )
            next_state = VoiceState.SLOT_OFFER

        elif self.state == VoiceState.SLOT_OFFER:
            try:
                choice = int(user_input) - 1
                if 0 <= choice < len(self.available_slots):
                    self.selected_slot = self.available_slots[choice]
                    slot = self.selected_slot
                    response = (
                        f"Confirming: {self.topic} consultation on {slot['date']} "
                        f"at {slot['time']} with {slot['advisor']}. "
                        f"All times are in IST. Shall I confirm this booking?"
                    )
                    next_state = VoiceState.CONFIRMATION
                else:
                    response = "Please choose slot 1 or 2."
            except ValueError:
                response = "Please enter 1 or 2 to select a slot."

        elif self.state == VoiceState.CONFIRMATION:
            if any(w in user_input.lower() for w in ["yes", "confirm", "ok", "sure"]):
                self.booking_code = self._gen_booking_code()
                slot = self.selected_slot
                response = (
                    f"Booking confirmed!\n"
                    f"  Booking Code: {self.booking_code}\n"
                    f"  Topic: {self.topic}\n"
                    f"  Date: {slot['date']} at {slot['time']}\n"
                    f"  Advisor: {slot['advisor']}\n\n"
                    f"No personal information was collected during this call."
                )
                next_state = VoiceState.BOOKED
            else:
                response = "Booking cancelled. Would you like to try a different slot?"
                next_state = VoiceState.SLOT_OFFER

        elif self.state == VoiceState.BOOKED:
            response = "Your booking is already confirmed. Call back if you need to reschedule. Goodbye!"

        self.state = next_state
        self.transcript.append({"role": "agent", "text": response})
        log.info("VoiceAgent: state={} turn={}", self.state.value, self.turn_count)

        return {
            "state": self.state.value,
            "response": response,
            "booking_code": self.booking_code,
            "topic": self.topic,
            "slot": self.selected_slot,
            "turn_count": self.turn_count,
            "transcript": self.transcript,
        }

    def get_booking_context(self) -> dict:
        if self.state != VoiceState.BOOKED or not self.booking_code:
            return {"error": "No active booking"}
        return {
            "booking_code": self.booking_code,
            "topic": self.topic,
            "slot": self.selected_slot,
            "top_theme": self.top_theme,
            "transcript": self.transcript,
        }
