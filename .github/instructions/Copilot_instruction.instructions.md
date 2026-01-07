---
applyTo: '**'
---


# AGENTS — GPT-only (VS Code Codex/Copilot)

## 0) Operator model selection (facts)
- Model is chosen by OPERATOR in VS Code (manual) or VS Code Auto.
- Agents must NOT assume they can switch models programmatically per task.
- If task exceeds the current model limits → agent MUST request split or escalation (operator picks stronger model).

---

## 1) Working mode (non-negotiable)
PDCA: Plan → Do → Check → Act.
ISO-like: define scope, inputs/outputs, acceptance criteria, and record changes.
Smallest next step only; no big refactors.
Deterministic changes > “clever refactors”.
Unknowns: inspect repo files or ask for clarification; do not guess.
Always validate contract (request/response) when testing.
Stop after Plan unless explicitly approved to implement.

---

## 2) Mandatory output format
Always start with:
(1) Assumptions (if any)
(2) Plan
(3) Minimal diff
(4) Check/Tests

---

## 3) Summary enforcement
Always include a progress table (min 3 rows). If no history → prev = N/A baseline.
Progress = 100% only if deliverable exists + Check/Tests done (or explicitly N/A).

Workstream / Task               | Done/Total | Progress | Status
------------------------------ | ---------- | -------- | ----------------------------
WP6 Routing (AUTO FAST/DEEP)   | {d}/{t}    | {p}%     | ✅ OK / ⚠️ Review / ❌ X
WP7 Semantics (FAST pack)      | {d}/{t}    | {p}%     | ⏳ Pending (needs evidence-lite)
UI (local webapp)              | {d}/{t}    | {p}%     | ✅ OK (runs locally)
Demo (Streamlit)               | {d}/{t}    | {p}%     | ✅ OK (public link active)
Tests / Golden suite           | {d}/{t}    | {p}%     | ❌ X (missing automated run)

---

## 4) Work Unit Boundary Rule (must estimate in Plan)
Agent MUST estimate:
- number of files touched
- estimated diff size (LOC)
- work class: GREEN / YELLOW / RED

Classification:
- GREEN: ≤5 files AND ≤500 LOC → implementation allowed (after approval)
- YELLOW: 5–10 files OR 800–2000 LOC → must split into stages
- RED: >10 files OR >2000 LOC → implementation forbidden without architectural decision

---

## 5) WU (Working Units) — deterministic scoring (agent self-compute)

### 5.1 Base from LOC-class
WU_base =
- GREEN  -> 2
- YELLOW -> 5
- RED    -> 8   (planning only; requires arch decision)

### 5.2 Risk/Scope adjustments (additive, deterministic)
WU_task = WU_base
+2 if auth/security/privacy-related
+1 if API contract changes (request/response schema)
+1 if storage/schema/migration involved
+1 if regression tests are missing for touched area (until added or marked N/A)
-1 if pure simplification/cleanup with zero behavior change (must justify)

### 5.3 Model capacity gate (75% rule)
Each model has WU_cap and safe limit:
WU_safe(model) = floor(0.75 * WU_cap(model))

Task is acceptable on current model iff:
WU_task <= WU_safe(model)
Else: agent MUST split or escalate.

---

## 6) Model matrix (GPT-only, VS Code picker aligned)

Note: multipliers reflect VS Code model picker (premium request multiplier).

| Model                      | Mult | Purpose (when to pick)                                  | WU_cap | WU_safe |
|---------------------------|------|----------------------------------------------------------|--------|---------|
| GPT-5.2-Codex             | 1x   | hardest: multi-file, deep repo changes, security/auth     | 12     | 9       |
| GPT-5.1-Codex-Max         | 1x   | long-horizon changes, refactors in core system            | 11     | 8       |
| GPT-5.1-Codex             | 1x   | default for coding + repo reasoning (medium/large tasks)  | 10     | 7       |
| GPT-5-Codex (Preview)     | 1x   | general coding, shorter horizon than Max                  | 9      | 6       |
| GPT-5.2                   | 1x   | analysis/planning + medium patches                         | 9      | 6       |
| GPT-5.1                   | 1x   | general tasks, medium patches                              | 8      | 6       |
| GPT-5                     | 1x   | general tasks, smaller scope                               | 7      | 5       |
| GPT-5.1-Codex-Mini (Prev) | 0.33x| cheap workhorse: GREEN tasks, tests, helpers, small diffs | 6      | 4       |
| GPT-5 mini                | 0x   | included/fast: single-file, trivial diffs only            | 5      | 3       |

---

## 7) Escalation & split rules (no guessing)
- If WU_task > WU_safe(current_model) → split into stages OR escalate model.
- Escalate immediately (no debate) when:
  - auth/security involved AND WU_task >= 6
  - API contract changes AND touched files > 3
  - storage/schema/migration involved
- Split YELLOW into 2–3 stages:
  Stage A: contract/spec + validation plan
  Stage B: minimal implementation
  Stage C: tests + contract verification

---

## 8) Calibration loop (PDCA, lightweight)
Weekly (or after 10 tasks):
- Compare estimated WU_task vs actual pain/bugs/regressions.
- Adjust only WU_cap numbers (+/-1) and keep rules deterministic.
- Record changes (what changed, why, date).

## 9) Approval form
Users' input: "ok, go ahead", "ok, proceed",
if you are not sure if user did give approval --> escalation for confirmation 