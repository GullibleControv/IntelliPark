# IntelliPark Interview Study Guide

## Executive Summary

This guide prepares you for technical interviews about the IntelliPark project. It covers critical issues to fix, architecture understanding, and common interview questions.

---

## Part 1: Critical Issues Found

### Security Review Summary

| Severity | Count | Examples |
|----------|-------|----------|
| CRITICAL | 3 | Unauthenticated DB endpoint, XSS in emails, missing CSRF docs |
| HIGH | 5 | Memory rate limiting, weak passwords, no account lockout |
| MEDIUM | 8 | JWT no revocation, threading for emails, logging PII |

### Code Quality Summary

| Severity | Count | Examples |
|----------|-------|----------|
| CRITICAL | 3 | Refund not processed, silent exceptions, plaintext logging |
| HIGH | 6 | No frontend tests, large files, N+1 queries |
| MEDIUM | 8 | Code duplication, missing API docs, unbounded queries |

---

## Part 2: Top 5 Issues to Fix

### 1. CRITICAL: Unauthenticated /api/init-db
**File:** backend/app/__init__.py:91-99
**Problem:** Anyone can reset the database
**Fix:** Add @admin_required decorator

### 2. CRITICAL: Refund Not Actually Processed  
**File:** backend/app/routes/payments.py:313-316
**Problem:** Booking marked refunded but no money returned
**Fix:** Call stripe.Refund.create()

### 3. CRITICAL: XSS in Email Templates
**File:** backend/app/services/email.py
**Problem:** User input rendered without escaping
**Fix:** Use markupsafe.escape() on all user data

### 4. HIGH: No Frontend Tests
**Problem:** 0% frontend test coverage
**Fix:** Add Jest tests for api.js and auth.js

### 5. HIGH: Rate Limiter Memory Storage
**File:** backend/app/__init__.py:18
**Problem:** Resets on restart, doesn't scale
**Fix:** Use Redis storage_uri

---

## Part 3: Architecture Knowledge

### System Components

1. **Frontend** - Vanilla JavaScript, HTML5, CSS3
2. **Backend** - Flask 3.0 + SQLAlchemy + Flask-SocketIO
3. **Database** - PostgreSQL (SQLite for dev)
4. **Detection** - YOLO 11s + OpenCV (runs separately)
5. **Payments** - Stripe Checkout

### Key Design Decisions

| Decision | Choice | Reasoning |
|----------|--------|-----------|
| Framework | Flask over Django | Lighter weight, API-first |
| Frontend | Vanilla JS over React | Demonstrate fundamentals |
| Auth | JWT over sessions | Stateless, scalable |
| Database | PostgreSQL over MongoDB | ACID for bookings |
| Real-time | WebSocket | Live occupancy updates |

---

## Part 4: Interview Questions

### Q: Walk me through a booking request
A: User authenticates with JWT -> POST /bookings -> Validate token -> Check time conflicts with SQL query -> Create booking -> Send async email -> Return 201

### Q: How do you prevent double booking?
A: Database-level conflict detection with overlapping time range query in a transaction

### Q: How does real-time detection work?
A: Detection system runs YOLO on video frames, checks if vehicle center is inside parking polygon (ray-casting), sends PUT request on status change, Flask broadcasts via WebSocket

### Q: What security measures did you implement?
A: bcrypt passwords, JWT auth, rate limiting, SQL injection prevention via ORM, XSS escaping, security headers (CSP, HSTS, X-Frame-Options), input validation

### Q: What would you improve?
A: Add frontend tests, fix critical security issues, use Redis for rate limiting, add API documentation, split large route files

---

## Part 5: Study Checklist

### Understand These Files
- [ ] backend/app/__init__.py (app factory, security headers)
- [ ] backend/app/models.py (7 database models)
- [ ] backend/app/routes/auth.py (JWT authentication)
- [ ] backend/app/routes/booking.py (conflict detection)
- [ ] frontend/js/api.js (API client class)

### Be Ready To Explain
- [ ] JWT authentication flow
- [ ] Booking conflict detection SQL
- [ ] Real-time WebSocket architecture
- [ ] YOLO detection process
- [ ] Security measures implemented

### Know Your Weaknesses
- [ ] No frontend tests (plan to add Jest)
- [ ] Rate limiter needs Redis
- [ ] Some critical bugs to fix
- [ ] API needs OpenAPI documentation

---

## Part 6: Quick Stats

| Metric | Value |
|--------|-------|
| Backend test files | 24 |
| Frontend test files | 0 |
| API endpoints | ~35 |
| Database tables | 7 |
| Security headers | 7 |
| Lines of code | ~5000 |

---

Good luck! Remember: acknowledging issues and having a fix plan shows maturity.
