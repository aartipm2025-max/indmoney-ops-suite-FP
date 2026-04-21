# CLAUDE.md — Operating Rules for This Project

You are working on the INDmoney Investor Ops & Intelligence Suite.
Phases 0 and 1 are COMPLETE and IMMUTABLE.

## Current phase: Phase 2 — Data Seeding (REAL DATA ONLY)

## ABSOLUTE PROHIBITIONS — violating any of these aborts the work

1. NEVER create synthetic, fictional, hypothetical, example, or generated data of any kind.
2. NEVER write content to `data/factsheets/markdown/` or `data/fees/` unless that content was derived from a real file downloaded from a real public source URL in this same session.
3. NEVER use the words `synthetic`, `fictional`, `hypothetical`, `example data`, `sample fund`, `generated`, or `placeholder` anywhere in any file written to `data/`.
4. NEVER invent fund names, fund manager names, AUM figures, NAV values, expense ratios, exit loads, or any other fund-specific number.
5. NEVER add funds outside this exact list: SBI Bluechip Fund, SBI Small Cap Fund, SBI Equity Hybrid Fund, SBI Midcap Fund, SBI Long Term Equity Fund (ELSS). HDFC, Axis, ICICI, Nippon, and all others are FORBIDDEN.
6. NEVER modify anything in `core/`, `config.py`, `schemas/`, or `docs/`.
7. NEVER go beyond the exact scope of the current step prompt. If a step says `download files`, do not parse them. If a step says `parse one file`, do not parse others.

## EXECUTION RULES

1. Work ONLY on the explicit step I give you. Do not plan or execute future steps.
2. If ANY ambiguity exists, STOP and ASK. Do not guess. Do not improvise.
3. If a download fails, a URL 404s, or a parse fails — STOP and REPORT. Do not fall back to generating content.
4. If a PowerShell command is rejected by the user, STOP. Do not reformulate the command without explicit approval.
5. After each sub-step, print a short summary table and STOP. Wait for the user to verify before proceeding.

## CURRENT STEP: Waiting for instructions.

Do not begin any work until the user explicitly invokes a sub-step.
