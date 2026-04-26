# Voice Agent — Design Document

## Purpose

Simulated text-based voice agent for the INDmoney Investor Ops Suite. Routes users
through an advisor-booking flow, surfacing the top complaint theme from the latest
weekly pulse as a context-aware greeting.

## Finite State Machine

```
GREETING → DISCLAIMER → TOPIC_SELECT → TIME_PREFERENCE → SLOT_OFFER → CONFIRMATION → BOOKED
                              ↓ (advice detected)
                         TOPIC_SELECT (loop)
```

States are modelled as a Python `Enum`. Each `process_turn()` call advances the FSM
by exactly one transition; invalid input keeps the current state.

## Booking Code Format

`IND-{THEME_CODE}-{YYYYMMDD}-{SEQ}`  (e.g. `IND-SUPP-20260428-003`)

Theme codes: TECH, SUPP, UIUX, PAYM, FUND, ACCT, LOGN, WDRL, GENR (default).

## Supported Topics

KYC/Onboarding · SIP/Mandates · Statements/Tax Docs · Withdrawals/Timelines ·
Account Changes/Nominee

## Intent Handling

| Intent | How triggered |
|---|---|
| `book_new` | Normal FSM flow |
| `reschedule` | "reschedule" keyword at BOOKED state |
| `cancel` | Negative response at CONFIRMATION |
| `what_to_prepare` | (reserved — topic detail expansion) |
| `check_availability` | Slot listing at SLOT_OFFER |

## Guardrails

No PII is collected on-call. Investment-advice requests (buy / sell / recommend) are
refused with a redirect to AMFI. All times are stated in IST.

## Pipeline Labels (all simulated)

`VAD → ASR → LLM → Tools → TTS`
