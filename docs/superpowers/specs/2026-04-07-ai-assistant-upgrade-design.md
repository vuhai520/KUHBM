# AI Assistant Upgrade — Design Spec
**Date:** 2026-04-07
**Scope:** Improve the KUHBM AI chat assistant with session memory and personal guest context

---

## Problem
The current AI assistant is fully stateless. Every message is sent to OpenAI with no prior conversation history and no knowledge of the logged-in guest's bookings or service requests. This makes it unable to hold a conversation or answer personal questions like "when is my check-out?".

---

## Solution: Option A — Server-side session history + guest context injection

### What changes

**`routes/chat.py`** — the only file modified

**Imports:** Add `session` to the existing Flask import line.

**Role guard:** Both the `/` (index) and `/send` routes require `current_user.role == 'guest'`. Return 403 for any other role on both routes. The entire chat blueprint is guest-only.

**Session history:**
- Read `session.get('chat_history', [])` at the start of each `/send` request
- Cap the list to the **last 20 entries total** (user + assistant combined) after appending the new pair. Always slice from an even index to preserve user/assistant pairs — i.e. `history[-20:]` and then drop a leading `assistant` entry if present, ensuring the first entry is always `role: user`
- After a **successful** OpenAI call, append the user message and assistant reply as two entries
- If the OpenAI call fails, do **not** append anything to history — return the error message without modifying session state
- After updating the list, reassign it explicitly: `session['chat_history'] = updated_list` and set `session.modified = True` to ensure Flask persists the mutation

**User message length:** Reject messages longer than 500 characters — return a JSON error without calling OpenAI or modifying history.

**System prompt — keep existing room context + add guest context:**
- Keep the existing available-rooms block (room number, type, price, description)
- Add guest's name (from `current_user.name`)
- Add guest's active bookings: query where `user_id == current_user.id` and `status IN ('confirmed', 'checked_in')` — include room number, check-in, check-out, status, total price
- Add guest's open service requests: query where `user_id == current_user.id` and `status IN ('pending', 'in_progress')` — include type, description, status

**OpenAI call structure:**
```
messages = [
    {"role": "system", "content": system_prompt},
    *chat_history,                      # prior turns
    {"role": "user", "content": user_message}   # current turn
]
```
After a successful response, append:
```python
{"role": "user", "content": user_message}
{"role": "assistant", "content": reply}
```
Then cap to last 20, reassign, set `session.modified = True`.

**Session cookie size note:** Flask's default client-side session has a ~4KB cookie limit. With 20 short messages this is workable, but acknowledged as a known constraint. The 500-character message limit and 20-message cap are the mitigations.

**`templates/guest/chat.html`** — no changes

**`models.py`** — no changes

**`app.py`** — no changes

---

## Data flow

```
Guest sends message (max 500 chars)
  → role guard: guest only
  → load session['chat_history'] (default [])
  → query DB: active bookings (confirmed/checked_in) + open requests (pending/in_progress)
  → build system prompt: rooms + guest name + bookings + requests
  → call OpenAI: system prompt + history + new user message
  → on success: append user+assistant to history, cap to 20, session.modified = True
  → on failure: do not modify history, return error message
  → return JSON response to browser
```

---

**Session cleanup on logout:** `routes/auth.py` logout route must call `session.clear()` before `logout_user()` to ensure `chat_history` is not retained in the browser cookie across login sessions.

---

## Files to modify
| File | Change |
|---|---|
| `routes/chat.py` | Session history, guest context, role guard on both routes, message length cap |
| `routes/auth.py` | Add `session.clear()` to logout route |

## Files unchanged
| File | Reason |
|---|---|
| `templates/guest/chat.html` | Frontend already works |
| `models.py` | Existing models sufficient |
| `app.py` | No changes needed |
