# Carrier Proxy Rules

## Overview
Success-criterion **carrier** is a keyword-based proxy for the type of evidence
required to verify task completion. It is derived from the task-name token of
the record_id (the segment before the first `__`).

**IMPORTANT**: The carrier proxy is a **hypothesis-generating** classification,
not an established taxonomy. Only 47/180 POS records could be reliably classified
by keyword. Results stratified by carrier are suggestive, not conclusive.

## Classification rules (applied in order)

| Carrier            | Trigger keywords in task name                                   | Example tasks                     |
|--------------------|-----------------------------------------------------------------|-----------------------------------|
| `delete-vacuous`   | delete, remove, clear, duplicate                                | "Delete the expense", "Remove duplicate contacts" |
| `file-system`      | camera, photo, audio, record, video                             | "Take a photo", "Record audio"    |
| `external/comms`   | sms, email, message, send, share, call, contact                 | "Send SMS", "Share via email"     |
| `value/toggle`     | brightness, bluetooth, wifi, rotate, setting, volume, timer, alarm, clock, toggle | "Turn brightness to max", "Toggle wifi" |
| `render/list`      | recipe, calendar, event, note, markor, expense, task, draw, sketch, add, create, new | "Create a new event", "Add an expense" |
| `other`            | (fallback — no keyword match)                                   | miscellaneous                     |

## Carrier × vision rescue (key finding)

Adding a screenshot (crossing to a new modality) rescues POS records that
the text-only trace-state estimator missed, but **only when the success
criterion is visible in the screenshot**:

| Carrier            | Vision rescue / blind miss | Interpretation                           |
|--------------------|---------------------------|------------------------------------------|
| `render/list`      | 2/2                       | Screenshots show the rendered result     |
| `delete-vacuous`   | 1/9                       | Absence is invisible in screenshots      |
| `file-system`      | 0/1                       | File-system state not in UI screenshot   |
| `external/comms`   | 0/2                       | Off-screen delivery unobservable         |

## Paper reference
See §RQ3 (carrier × information-layer crossing) and `results/rq3_carrier_crossing.csv`.
