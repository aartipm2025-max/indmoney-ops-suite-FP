# MCP Integration Design — INDmoney Investor Ops Suite

## Overview

This document describes the MCP-style tool calling layer (Pillar C) that connects the INDmoney Investor Ops Suite to three Google services: Calendar, Gmail, and Google Docs.

## Tool Definitions

Each Google service action is defined as a structured Python function that returns a typed payload dict. No action executes immediately. All payloads are submitted to the HITL outbox for human review.

| Tool | Function | Output |
|---|---|---|
| `calendar_hold` | `create_calendar_hold()` | Tentative calendar event payload |
| `email_draft` | `create_email_draft()` | Gmail draft payload (never auto-sent) |
| `doc_append` | `create_doc_append()` | Google Docs append payload |

## HITL Lifecycle

All actions follow a strict state machine:

`PENDING → APPROVED → EXECUTED → FAILED` (on API error)
`PENDING → REJECTED` (human veto with reason)

An advisor or ops user reviews each queued action in the HITL outbox (SQLite). On approval, the real Google API call fires. Rejection requires a structured reason from the `REJECT_REASONS` enum, which is logged to the audit trail.

## Booking Code

A booking code (format: `IND-{THEME}-{DATE}-{SEQ}`) must appear in all three outputs: the calendar event description, the email subject line and body, and the Google Doc entry. This ensures full traceability across channels.

## Advisor Briefing Card

The `briefing_card.py` module generates a structured card from Pillar B pulse data and embeds it in the email draft (HTML + plain text fallback). It surfaces top themes, sentiment direction, user quotes, and suggested advisor talking points.
