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

def _future_slots() -> list[dict]:
    from datetime import timedelta
    today = datetime.now(timezone.utc)
    d1 = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    d2 = (today + timedelta(days=2)).strftime("%Y-%m-%d")
    return [
        {"date": d1, "time": "10:00 AM IST", "advisor": "Advisor A"},
        {"date": d1, "time": "02:30 PM IST", "advisor": "Advisor B"},
        {"date": d2, "time": "11:00 AM IST", "advisor": "Advisor A"},
    ]

MOCK_SLOTS = _future_slots()


class VoiceAgent:
    def __init__(self, top_theme: str = "general"):
        self.state = VoiceState.GREETING
        self.top_theme = top_theme
        self.topic = None
        self.time_pref = None
        self.selected_slot = None
        self.booking_code = None
        self.turn_count = 0
        self.transcript = []

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
                topics_str = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(TOPICS))
                response = (
                    f"What topic would you like to discuss with an advisor?\n"
                    f"{topics_str}\n"
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
                # Try to match topic by number or keyword
                matched = None
                try:
                    idx = int(user_input.strip()) - 1
                    if 0 <= idx < len(TOPICS):
                        matched = TOPICS[idx]
                except ValueError:
                    for t in TOPICS:
                        if any(word in user_input.lower() for word in t.lower().replace("/", " ").split()):
                            matched = t
                            break

                if matched:
                    self.topic = matched
                    response = f"Got it — {matched}. When would you prefer the call? (e.g., 'tomorrow', 'Monday afternoon')"
                    next_state = VoiceState.TIME_PREFERENCE
                else:
                    response = "I didn't catch that. Please choose a number (1-5) or describe your topic."
                    # Stay in TOPIC_SELECT

        elif self.state == VoiceState.TIME_PREFERENCE:
            self.time_pref = user_input
            slots_str = "\n".join(
                f"  Slot {i+1}: {s['date']} at {s['time']} with {s['advisor']}"
                for i, s in enumerate(MOCK_SLOTS[:2])
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
                if 0 <= choice < 2:
                    self.selected_slot = MOCK_SLOTS[choice]
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
