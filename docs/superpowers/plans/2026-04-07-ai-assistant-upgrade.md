# AI Assistant Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add session-based conversation memory and personal guest context (bookings + service requests) to the KUHBM AI chat assistant.

**Architecture:** Flask's server-side session stores `chat_history` as a list of `{role, content}` dicts. On each `/chat/send` request, the full history plus live guest data is injected into the OpenAI call. History is capped at 20 entries and cleared on logout.

**Tech Stack:** Flask session, OpenAI `gpt-4o-mini`, SQLAlchemy (Booking + ServiceRequest models already exist)

---

## Files Modified

| File | What changes |
|---|---|
| `routes/chat.py` | Add session, role guard, message length cap, guest context in system prompt, history management |
| `routes/auth.py` | Add `session.clear()` before `logout_user()` |

---

## Task 1: Clear session on logout (`routes/auth.py`)

**Files:**
- Modify: `routes/auth.py` (logout route, line 59)

- [ ] **Step 1: Add `session` to the Flask import in `auth.py`**

Open `routes/auth.py`. Change line 1 from:
```python
from flask import Blueprint, render_template, redirect, url_for, flash, request
```
to:
```python
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
```

- [ ] **Step 2: Call `session.clear()` before `logout_user()`**

Change the logout route (lines 57–61) from:
```python
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
```
to:
```python
@auth_bp.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('auth.login'))
```

- [ ] **Step 3: Manually verify**

Start the app (`python app.py`), log in as `guest@hotel.com / guest123`, send a chat message, then log out and log back in. The chat history should be empty on the new session.

- [ ] **Step 4: Commit**

```bash
git add routes/auth.py
git commit -m "Clear session on logout to prevent chat history leaking across logins"
```

---

## Task 2: Role guard on chat routes (`routes/chat.py`)

**Files:**
- Modify: `routes/chat.py`

- [ ] **Step 1: Add `session` and `abort` to the Flask import**

Change line 1 from:
```python
from flask import Blueprint, render_template, request, jsonify
```
to:
```python
from flask import Blueprint, render_template, request, jsonify, session, abort
```

- [ ] **Step 2: Add role guard to the `index` route**

Change:
```python
@chat_bp.route('/')
@login_required
def index():
    return render_template('guest/chat.html')
```
to:
```python
@chat_bp.route('/')
@login_required
def index():
    if current_user.role != 'guest':
        abort(403)
    return render_template('guest/chat.html')
```

- [ ] **Step 3: Add role guard to the `send` route**

Add the role guard as the **very first line** of `send()`, before the API key check:
```python
@chat_bp.route('/send', methods=['POST'])
@login_required
def send():
    if current_user.role != 'guest':
        abort(403)
    if not Config.OPENAI_API_KEY:
        return jsonify({'response': 'AI assistant is not configured. Please add an API key.'})
    # ... rest of function unchanged for now
```

- [ ] **Step 4: Manually verify**

Log in as `admin@hotel.com / admin123` and navigate to `/chat/`. You should see a 403 error page. Log in as `guest@hotel.com / guest123` and it should load normally.

- [ ] **Step 5: Commit**

```bash
git add routes/chat.py
git commit -m "Add guest-only role guard to chat index and send routes"
```

---

## Task 3: Message length validation (`routes/chat.py`)

**Files:**
- Modify: `routes/chat.py` (`send` route)

- [ ] **Step 1: Add length check after the empty-message check**

In the `send()` function, after:
```python
if not user_message.strip():
    return jsonify({'response': 'Please enter a message.'})
```
add:
```python
if len(user_message) > 500:
    return jsonify({'response': 'Message too long. Please keep messages under 500 characters.'})
```

- [ ] **Step 2: Manually verify**

Use the browser dev tools console on the chat page to send a long message:
```javascript
fetch('/chat/send', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message: 'a'.repeat(501)})}).then(r=>r.json()).then(console.log)
```
Expected: `{response: "Message too long..."}`

- [ ] **Step 3: Commit**

```bash
git add routes/chat.py
git commit -m "Reject chat messages over 500 characters"
```

---

## Task 4: Inject guest context into system prompt (`routes/chat.py`)

**Files:**
- Modify: `routes/chat.py` (`send` route)

- [ ] **Step 1: Add `ServiceRequest` to the models import**

Change line 3 from:
```python
from models import Room, Booking
```
to:
```python
from models import Room, Booking, ServiceRequest
```

- [ ] **Step 2: Query guest's active bookings and open service requests**

Note: `b.room` is valid — `models.py` defines `Room.bookings` with `backref='room'`, which automatically creates the reverse `.room` attribute on every `Booking` instance.

In `send()`, after the existing `available_rooms` query, add:
```python
# Guest's active bookings
active_bookings = Booking.query.filter(
    Booking.user_id == current_user.id,
    Booking.status.in_(['confirmed', 'checked_in'])
).all()
booking_info = '\n'.join([
    f"- Room {b.room.number} ({b.room.type}): check-in {b.check_in}, check-out {b.check_out}, status: {b.status}, total: ${b.total_price}"
    for b in active_bookings
]) or 'No active bookings.'

# Guest's open service requests
open_requests = ServiceRequest.query.filter(
    ServiceRequest.user_id == current_user.id,
    ServiceRequest.status.in_(['pending', 'in_progress'])
).all()
request_info = '\n'.join([
    f"- {r.type} request: '{r.description}', status: {r.status}"
    for r in open_requests
]) or 'No open service requests.'
```

- [ ] **Step 3: Update the system prompt to include guest context**

Replace the existing `system_prompt` string with:
```python
system_prompt = f"""You are a friendly hotel assistant for KUHBM.
You are speaking with {current_user.name}.
Help them with room inquiries, booking information, service requests, and general hotel questions.

Currently available rooms:
{room_info if room_info else 'No rooms currently available.'}

{current_user.name}'s active bookings:
{booking_info}

{current_user.name}'s open service requests:
{request_info}

Keep responses concise and helpful. If the guest wants to make a new booking, direct them to the Booking page.
If they want to submit a new service request, direct them to the Services page.
You can answer questions about their existing bookings and requests using the information above."""
```

- [ ] **Step 4: Manually verify**

Log in as `guest@hotel.com / guest123`, make a booking (or check if one exists from seed), then go to the AI chat and ask "what are my bookings?". The assistant should name the actual booking details.

- [ ] **Step 5: Commit**

```bash
git add routes/chat.py
git commit -m "Inject guest bookings and service requests into AI system prompt"
```

---

## Task 5: Add session-based conversation history (`routes/chat.py`)

**Files:**
- Modify: `routes/chat.py` (`send` route)

- [ ] **Step 1: Load history from session at the start of `send()`**

At the top of `send()`, after the length check, add:
```python
chat_history = session.get('chat_history', [])
```

- [ ] **Step 2: Pass history to the OpenAI call**

Replace the existing OpenAI `messages` list:
```python
messages=[
    {'role': 'system', 'content': system_prompt},
    {'role': 'user', 'content': user_message}
]
```
with:
```python
messages=[
    {'role': 'system', 'content': system_prompt},
    *chat_history,
    {'role': 'user', 'content': user_message}
]
```

- [ ] **Step 3: Save history back to session on success**

After `reply = response.choices[0].message.content`, add:
```python
chat_history.append({'role': 'user', 'content': user_message})
chat_history.append({'role': 'assistant', 'content': reply})

# Cap to last 20 entries, always starting with a user turn
chat_history = chat_history[-20:]
if chat_history and chat_history[0]['role'] == 'assistant':
    chat_history = chat_history[1:]

session['chat_history'] = chat_history
session.modified = True
```

- [ ] **Step 4: Verify history does NOT save on OpenAI failure**

The existing `except Exception` block returns an error reply without touching `chat_history` or session — confirm the `session['chat_history'] = ...` lines are only inside the `try` block after a successful `reply`.

- [ ] **Step 5: Manually verify memory works**

In the chat, send: "My name is Alex." Then send: "What did I just tell you my name was?" The assistant should recall "Alex" from history.

- [ ] **Step 6: Commit**

```bash
git add routes/chat.py
git commit -m "Add session-based conversation history to AI assistant (max 20 messages)"
```

---

## Task 6: Push and verify on Render

- [ ] **Step 1: Push all commits**

```bash
git push
```

- [ ] **Step 2: Wait for Render to redeploy**

Check the Render dashboard Logs tab — wait for "Your service is live".

- [ ] **Step 3: Smoke test on live URL**

1. Log in as `guest@hotel.com / guest123`
2. Go to AI Assistant
3. Ask "what rooms do you have?" — should list real rooms
4. Ask "what are my bookings?" — should show real booking data
5. Say "remember this: I prefer a quiet room" then ask "what did I ask you to remember?" — should recall it
6. Log out, log back in, go to chat — history should be empty

- [ ] **Step 4: Done ✅**
