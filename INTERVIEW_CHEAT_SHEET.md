# IntelliPark Interview Cheat Sheet

## Quick Stats
```
Backend Tests: 259 passing    | API Endpoints: ~35
Database Tables: 7            | Security Headers: 7
Lines of Code: ~5000          | Frontend Tests: 0 (planned)
```

---

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────►│   Flask     │────►│ PostgreSQL  │
│ Vanilla JS  │◄────│   REST API  │◄────│  Database   │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │WebSocket │ │  Stripe  │ │   YOLO   │
        │ Updates  │ │ Payments │ │Detection │
        └──────────┘ └──────────┘ └──────────┘
```

**Why Flask over Django?** Lighter weight, API-first design
**Why Vanilla JS?** Demonstrate fundamentals without framework abstraction
**Why JWT over Sessions?** Stateless, horizontally scalable
**Why PostgreSQL?** ACID compliance for booking transactions

---

## 7 Database Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| User | Authentication | email, password_hash, is_admin |
| ParkingSpace | Space config | name, location, coordinates, hourly_rate |
| Booking | Reservations | user_id, space_id, start_time, end_time, status |
| VideoSource | Camera config | url, location, frame dimensions |
| OccupancyLog | Analytics | space_id, is_occupied, confidence |
| RecurringBooking | Templates | pattern, days_of_week, valid_from/until |
| Waitlist | Queue system | desired_date, status, expires_at |

---

## Flow 1: JWT Authentication

```
REGISTER/LOGIN                    PROTECTED REQUEST
     │                                  │
     ▼                                  ▼
┌─────────────┐                  ┌─────────────────┐
│ Validate    │                  │ Extract token   │
│ credentials │                  │ from header     │
└──────┬──────┘                  └────────┬────────┘
       │                                  │
       ▼                                  ▼
┌─────────────┐                  ┌─────────────────┐
│ Hash with   │                  │ jwt.decode()    │
│ bcrypt      │                  │ verify signature│
└──────┬──────┘                  └────────┬────────┘
       │                                  │
       ▼                                  ▼
┌─────────────┐                  ┌─────────────────┐
│ Generate    │                  │ Attach user_id  │
│ JWT token   │                  │ to request      │
└─────────────┘                  └─────────────────┘
```

**JWT Payload:** `{user_id, exp, iat}` signed with SECRET_KEY using HS256

**Security Features:**
- bcrypt (slow hashing, salted)
- Constant-time comparison
- Generic error messages (prevent enumeration)
- Rate limiting (10 login/min)

---

## Flow 2: Booking & Conflict Detection

```sql
-- THE CONFLICT DETECTION QUERY
SELECT * FROM bookings
WHERE space_id = ?
  AND status IN ('pending', 'confirmed', 'active')
  AND start_time < ?   -- existing starts before new ends
  AND end_time > ?     -- existing ends after new starts
```

**Visual:**
```
Existing:  10:00 |=========| 12:00
New:             11:00 |=========| 14:00
                      ↑ OVERLAP! (conflict found)
```

**Booking States:**
```
pending → confirmed → active → completed
    ↓         ↓
cancelled  cancelled
```

---

## Flow 3: Stripe Payment

```
1. POST /create-checkout-session {booking_id}
2. Create Stripe Session (amount in CENTS!)
3. Return {session_id, url}
4. Redirect user to Stripe Checkout
5. User pays → redirected to success_url
6. POST /verify-session {session_id}
7. Retrieve session, verify payment_status='paid'
8. Store payment_intent_id (FOR REFUNDS!)
9. Update booking status
```

**Critical Bug Fixed:** Original code didn't call `stripe.Refund.create()` - marked as refunded without actually refunding!

---

## Flow 4: WebSocket Real-time

```
Browser                    Server                    Detection
   │                          │                          │
   │ subscribe_location       │                          │
   │ {location: "Mall"}       │                          │
   │─────────────────────────►│                          │
   │                          │  PUT /spaces/5/status    │
   │                          │  {is_occupied: true}     │
   │                          │◄─────────────────────────│
   │                          │                          │
   │  emit('space_update')    │                          │
   │◄─────────────────────────│                          │
   │                          │                          │
   ▼ Update UI instantly      │                          │
```

**Room Types:** `location_{name}`, `space_{id}`, `user_{id}`

---

## Flow 5: YOLO Detection

```
Camera → OpenCV → YOLO 11s → Bounding Boxes
                                   │
                                   ▼
                    For each parking space polygon:
                    1. Get car center point (x + w/2, y + h/2)
                    2. Ray-casting: is center inside polygon?
                    3. If state changed → PUT /spaces/{id}/status
```

**Why center point?** Bounding boxes overlap; center is always in one space

---

## Flow 6: Waitlist

```
1. User joins waitlist (desired date/time/location)
2. Someone cancels → check_waitlist_availability()
3. Find matching waitlist entries (first-come-first-served)
4. Notify via email + WebSocket
5. User has 30 MINUTES to book
6. If expired → notify next person
```

---

## Security Fixes Made (CRITICAL)

| Issue | CWE | Fix |
|-------|-----|-----|
| Unauth /init-db | CWE-306 | Secret token + env check |
| XSS in emails | CWE-79 | markupsafe.escape() |
| Fake refunds | CWE-840 | Store payment_intent, call Stripe |
| Bad coordinates | CWE-20 | validate_coordinates() |

---

## Interview Questions - Quick Answers

### Authentication

**Q: Why JWT over sessions?**
> Stateless. Any server can validate without central session store. Enables horizontal scaling.

**Q: JWT weaknesses?**
> Can't revoke before expiration. Mitigate with short expiry, refresh tokens, or blacklist.

### Booking

**Q: How prevent double booking?**
> Overlapping time range query in database transaction. ACID properties handle race conditions.

**Q: Why check pending/confirmed/active statuses?**
> These are "blocking" statuses. Cancelled/completed don't claim the space.

### Payment

**Q: Walk through Stripe integration.**
> Create checkout session → redirect to Stripe → verify on return → store payment_intent → update booking.

**Q: Why store payment_intent?**
> Required for refunds. Can't refund without it.

### Real-time

**Q: Why WebSocket rooms?**
> Efficiency. User viewing "Mall Parking" doesn't need "Airport Parking" updates.

**Q: What if connection drops?**
> Socket.IO auto-reconnects. Client re-subscribes to rooms. Fetch latest state via REST.

### Detection

**Q: How does YOLO detection work?**
> Process video frames → detect vehicles → check if center is inside parking polygon → notify API on change.

**Q: Why YOLO?**
> Real-time (30+ FPS), single-pass detection, pre-trained on vehicles.

### Architecture

**Q: What would you improve?**
> 1. Add frontend tests (Jest)
> 2. Redis for rate limiting
> 3. OpenAPI documentation
> 4. Split large route files

---

## Key File Locations

| File | Contains |
|------|----------|
| `app/__init__.py` | App factory, security headers |
| `app/models.py` | All 7 database models |
| `routes/auth.py` | JWT authentication |
| `routes/booking.py` | Booking CRUD + conflict detection |
| `routes/payments.py` | Stripe integration |
| `services/websocket.py` | Real-time updates |
| `services/email.py` | Email templates + XSS fix |
| `utils/auth.py` | JWT helpers, decorators |

---

## Code Snippets to Remember

### JWT Token Generation
```python
payload = {
    'user_id': user_id,
    'exp': datetime.utcnow() + timedelta(hours=24),
    'iat': datetime.utcnow()
}
return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
```

### Conflict Detection
```python
conflict = Booking.query.filter(
    Booking.space_id == space_id,
    Booking.status.in_(['pending', 'confirmed', 'active']),
    Booking.start_time < end_time,
    Booking.end_time > start_time
).first()
```

### XSS Prevention
```python
from markupsafe import escape as html_escape

def safe_str(value):
    if value is None:
        return ''
    return html_escape(str(value))
```

### Stripe Refund
```python
refund = stripe.Refund.create(
    payment_intent=booking.stripe_payment_intent_id,
    reason='requested_by_customer'
)
```

---

## The Golden Rule

> "I found this bug, I fixed it, here's what I learned."

Interviewers want to see:
1. You can **identify** problems
2. You can **prioritize** by severity
3. You can **implement** fixes
4. You can **explain** your thinking

---

## 30-Second Project Pitch

> "IntelliPark is a smart parking management system I built full-stack.
> The backend is Flask with PostgreSQL, handling bookings with conflict
> detection, Stripe payments with proper refund handling, and real-time
> occupancy updates via WebSocket.
>
> The detection component uses YOLO computer vision to automatically
> track which spaces are occupied.
>
> I conducted a security review and fixed critical issues including
> XSS vulnerabilities, an unauthenticated admin endpoint, and a bug
> where refunds weren't actually being processed through Stripe.
>
> The backend has 259 passing tests. Key areas for improvement are
> frontend testing and migrating rate limiting to Redis."

---

*Print this. Study this. Ace the interview.*
