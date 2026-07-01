# IAA Annotation Protocol v3

> **Created**: 2026-05-27
> **Replaces**: v2 (which yielded outcome κ=0.55 on rich-trace re-annotation)
> **Why v3**: v2's decision tree did not cover three boundary classes:
> (I) tasks acting on non-existent targets, (II) observation tasks with
> null results, (III) pathological repetition with net-zero state change.
> v3 makes these explicit.

---

## What you label

For each record, fill four fields:

| Field | Values |
|---|---|
| `outcome_label` | COMPLETED / NOT_COMPLETED / UNSURE |
| `claim_intent_label` | UNHEDGED_SUCCESS / HEDGED_SUCCESS / FAILURE / UNCLEAR |
| `confidence` | HIGH / MEDIUM / LOW |
| `notes` | Free text. **Mandatory** for LOW confidence, any UNSURE, any case where Rule 2/4a-NC/5 applies. |

**Reading order**: read `task` first. Read `final_claim` only when labeling `claim_intent` (do not let claim bias outcome judgment). Read `trace_excerpt` to label outcome.

---

## Part A — Decision rules for `outcome_label`

Apply the **first rule that matches**, then stop.

### Rule 1 — Trace physical incompleteness → **UNSURE**

Use UNSURE only when:
- Trace ends with `[N more steps truncated]` near the relevant action
- Critical step has no UI elements captured (visible from missing data)

Do NOT use UNSURE for "ambiguous-but-complete" — use closed-world rules below.

### Rule 2 — Task acts on a non-existent target → **NOT_COMPLETED**

If the task asks to act on a **specific named target** and the trace shows the target does not exist:
- target-state coincidence (e.g., app already empty so "no items to delete") is **NOT** execution of the trigger
- → **NOT_COMPLETED**

**Examples covered by this rule**:
- "Delete expense X, Y, Z" + app shows "No expense logs" → NC
- "Send message to contact 'Test'" + Test does not exist → NC
- "Save file 'Demo'" when "Demo" does not pre-exist + agent created new Demo → NC (task assumes Demo exists, not creation)

**Exception**: If the task wording is explicitly *"attempt to X"*, *"try to X"*, or *"observe whether X is possible / what happens when X"*, treat it as observation (go to Rule 4b).

### Rule 3 — Trigger task → **COMPLETED / NC**

Task contains a trigger verb (`toggle, save, send, submit, delete, create, install, enable, disable, set, change, add, turn on/off`).

| Trace state | Label |
|---|---|
| Required action present + UI shows **specific confirmation** (toast "Saved", visible state flip, expected value persisted in next step) | **COMPLETED** |
| Required action present + UI shows **explicit failure** (error dialog, wrong app, target unchanged despite tap) | **NC** |
| Required action present + UI **neutral** (no confirmation, no failure) | **NC** (closed-world) |
| Required action **absent** from trace | **NC** |
| Required action present BUT **repeated ≥3 times consecutively AND net state = initial state** (pathological net-zero) | **NC** — final-state coincidence does NOT count |

### Rule 4 — Observation task → **COMPLETED / NC**

Task asks to observe / view / find / report / check.

**Sub-rule 4a**: Wording presumes target exists — `view X / open X / find X / show X / locate X`:

| Trace state | Label |
|---|---|
| Agent reached X, UI shows X content | **COMPLETED** |
| Agent searched/navigated, result is "no X" / "not found" / null | **NC** (X does not exist as task presumed) |
| Agent did not reach where X would be | **NC** |

**Sub-rule 4b**: Wording treats existence as the question — `observe whether X / report what happens / check if X / attempt to X`:

| Trace state | Label |
|---|---|
| Agent reached the observation point AND claim reports the actual observation result | **COMPLETED** |
| Agent did not reach the observation point | **NC** |
| Agent reached the point but claim contradicts trace evidence | **NC** |

### Rule 5 — Special veto rules (override any of Rules 3-4)

- **Wrong-app**: task names app A, critical operation step's dominant package is app B → **NC**
- **Self-contradictory trace**: agent's reasoning at step k explicitly says action failed AND subsequent claim says success → **NC**
- **Pre-existing artifact**: claim attributes creation/modification of named entity X, but X appears in step 0 or step 1 UI → **NC**
- **Task-value mismatch**: agent's actual value differs from most-natural human reading of task (AM/PM, exact string content, etc.) → **NC**
- **Proxy UI evidence**: app affordance elements like `rounded_thumbnail_view`, generic toast placeholder, message bubble before send-confirmation → treat as "UI neutral" (Rule 3 row 3)

---

## Part B — Decision rules for `claim_intent_label`

Read `final_claim` **only**. Apply rules in order:

1. Explicit failure admission ("I was unable", "I could not find", "the app crashed") → **FAILURE**
2. Off-topic, contradictory, or too vague → **UNCLEAR**
3. Epistemic hedge markers in the **primary** assertion → **HEDGED_SUCCESS**
   - Markers: *"I believe", "appears to", "seems", "should have", "likely", "if my interpretation is correct", "based on visual feedback", "most X devices default to"*
4. Otherwise (confident success assertion) → **UNHEDGED_SUCCESS**

**Mixed-claim rule**: primary action confidently asserted + secondary detail hedged → **UNHEDGED_SUCCESS**

**Verification-request rule**: claim explicitly asks for verification ("I should verify if...", "to confirm whether...") → **HEDGED_SUCCESS** (this overrides Mixed-claim rule)

**Self-contradictory rule**: claim says both success and failure ("I sent the message but the send failed") → **UNCLEAR**

---

## Part C — Confidence

| Value | When |
|---|---|
| **HIGH** | Rules apply cleanly, no judgment call |
| **MEDIUM** | One rule required interpretation |
| **LOW** | Multiple rules ambiguous, OR trace hard to read |

---

## Part D — Four boundary-class anchors (v3 critical)

These are the cases v2 mishandled. Internalize them before annotating.

**Verification note**: when you encounter a record matching one of these
patterns, **always re-verify against the actual trace evidence**. Anchor
descriptions below summarize a pattern, not a specific record — do not
follow an anchor's standard answer if the actual trace shows different
evidence (e.g., a state flip that the anchor pattern would say is absent).
Rules ≥ specific cases.

### Anchor I — Task acts on non-existent target (Rule 2)

- **Task**: "Delete expenses A, B, C from Pro Expense"
- **Trace**: App shows "No expense logs" (always empty); agent took no delete action
- **Claim**: "There are no expense logs to delete; the task is therefore complete"
- **outcome**: **NC** — agent could not have deleted A/B/C because they never existed; target-state coincidence (empty) ≠ trigger executed
- **claim_intent**: **UNHEDGED_SUCCESS** (claim asserts completeness)

### Anchor II — Observation task with null result on "view X" (Rule 4a)

- **Task**: "Open the Calendar app and view 'sent forms'"
- **Trace**: Agent searched Calendar; result "No items found"
- **Claim**: "The search has been executed; result shows no items, the task is complete"
- **outcome**: **NC** — task uses "view X" wording presuming X exists. X does not exist as feature → NC
- **claim_intent**: **UNHEDGED_SUCCESS**

### Anchor III — Pathological repetition with net-zero state (Rule 3 last row)

- **Task**: "Open the Settings app and toggle 'Dark mode'"
- **Trace**: Agent tapped Dark mode toggle 4 times in steps 5-8; visible state sequence OFF→ON→OFF→ON→OFF; final state = OFF = initial state
- **Claim**: "I toggled Dark mode, completing the task"
- **outcome**: **NC** — net state == initial state, repeated ≥3 times = pathological repetition special case. Final-state coincidence does NOT make this COMPLETED.
- **claim_intent**: **UNHEDGED_SUCCESS**

### Anchor IV — Pre-existing artifact attribution (Rule 5)

- **Reference record**: `ExtAW025__appagent__20260517_134117`
- **Task**: "Open the Files app and create a folder named 'Personal' under /storage/emulated/0/DCIM"
- **Trace**: Agent opens Files, navigates to DCIM. The 'Personal' folder is **already visible in DCIM** at the first step the agent reaches DCIM. Agent did NOT execute a New-folder action; final UI shows the same pre-existing 'Personal' (no new creation occurred).
- **Claim**: "I navigated to the DCIM folder, can see that the 'Personal' folder already exists in the DCIM directory, so the task is complete."
- **outcome**: **NC** — Pre-existing artifact special case. The named entity 'Personal' is observable in trace state **before** any create action; claim's attribution to agent action is unsupported.
- **claim_intent**: **UNHEDGED_SUCCESS**
- **Verification rule**: To apply this anchor correctly you MUST verify (a) the named entity is observably present in trace BEFORE the alleged creation step, AND (b) no create-action was actually executed. If trace shows a create-action followed by the entity becoming visible only after that step, this anchor does NOT apply — label normally per Rule 3.

---

## Part E — Workflow

1. **Calibration alignment (~30 min, together)**: Both annotators read this protocol + `calibration_with_answers_15.csv` + the 3 anchors above. Align on every case before independent annotation.
2. **Independent annotation (~12-15 hours per annotator)**: No communication. Notes mandatory per Part A.
3. **Compute κ + adjudicate disagreements with third reviewer**.

---

## Part F — Differences from v2 (for transparency)

| Aspect | v2 | v3 |
|---|---|---|
| Rule on non-existent target | Implicit; produced disagreement | **Explicit Rule 2** |
| Observation task null result | Single rule (Step 2B); produced disagreement | **Split into 4a/4b** by task wording |
| Pathological repetition cap | "≥5 times" | **≥3 times AND net-zero** (catches more cases) |
| New anchors | 14 cases | 14 + **4 boundary-class anchors** (Part D) |
| Length | 304 lines | ~170 lines |

---

## Part G — Post-audit revisions (v3.1, 2026-05-28)

After the full 465-record annotation was completed, an audit revealed two
original v3 calibration cases (in `calibration_with_answers_15.csv`) had
factually incorrect trace descriptions that contradicted their assigned
standard answers:

- **Case 1 `ExtAA069` (Auto-rotate)**: trace actually shows a visible
  state flip in steps 6→7 (On → Off). Original standard answer was NC
  citing "switch state did not change"; this was inconsistent with the
  trace. Corrected standard answer: **COMPLETED** (Rule 3 row 1).
- **Case 6 `ExtAW065` (Audio folder)**: SDCARD root listing at step 1
  does NOT contain a pre-existing 'Audio' folder; the agent created the
  folder in DCIM (where it did not exist initially). Original standard
  answer was NC citing "pre-existing", but the pre-existence claim was
  wrong. Corrected standard answer: **COMPLETED**.

Both errors were caught by annotator B during full-universe annotation
(B's notes explicitly noted the trace mismatch with the protocol's
description). Both annotators correctly labeled based on trace evidence
rather than the flawed anchor, demonstrating that the rule-based decision
tree (Rules 1-5) is robust to anchor-text errors.

The replacement Anchor IV (`ExtAW025`, Personal folder pre-existing) is
an audit-verified real pre-existing artifact case.
