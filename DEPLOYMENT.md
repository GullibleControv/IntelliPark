# IntelliPark - Render Deployment Guide

Complete guide to deploy IntelliPark on Render with PostgreSQL database.

## Prerequisites

- GitHub account with the IntelliPark repository
- Render account (free tier works)

---

## Step 1: Create Render Account

1. Go to [render.com](https://render.com)
2. Click **Get Started for Free**
3. Sign up with **GitHub** (recommended for auto-deploy)

---

## Step 2: Deploy Using Blueprint (Recommended)

The easiest way - uses `render.yaml` to auto-configure everything.

### 2.1 Create New Blueprint

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New** → **Blueprint**
3. Connect your GitHub repository: `GullibleControv/IntelliPark`
4. Click **Apply**

### 2.2 Configure Environment Variables

After Blueprint creates the services, set the **ADMIN_PASSWORD**:

1. Go to your **intellipark** service
2. Click **Environment** tab
3. Find `ADMIN_PASSWORD` and set a secure password:
   - Minimum 12 characters
   - Include uppercase, lowercase, numbers, and symbols
   - Example: `SecureAdmin@2024!`

4. Click **Save Changes** (triggers redeploy)

---

## Step 3: Manual Deployment (Alternative)

If Blueprint doesn't work, deploy manually:

### 3.1 Create PostgreSQL Database

1. Render Dashboard → **New** → **PostgreSQL**
2. Settings:
   - **Name**: `intellipark-db`
   - **Database**: `intellipark`
   - **User**: `intellipark`
   - **Region**: Oregon (or nearest)
   - **Plan**: Free
3. Click **Create Database**
4. Copy the **Internal Database URL** (starts with `postgresql://`)

### 3.2 Create Web Service

1. Render Dashboard → **New** → **Web Service**
2. Connect your GitHub repository
3. Settings:
   - **Name**: `intellipark`
   - **Region**: Same as database
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 "app:create_app()"`
   - **Plan**: Free

4. Add Environment Variables:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | (paste Internal Database URL) |
| `SECRET_KEY` | (click Generate) |
| `FLASK_ENV` | `production` |
| `DEBUG` | `false` |
| `RENDER` | `true` |
| `ADMIN_EMAIL` | `admin@intellipark.com` |
| `ADMIN_PASSWORD` | `YourSecurePassword@123!` |

5. Click **Create Web Service**

---

## Step 4: Verify Deployment

### 4.1 Check Health Endpoint

```
https://intellipark.onrender.com/api/health
```

Should return:
```json
{"status": "healthy", "service": "IntelliPark API"}
```

### 4.2 Access the Application

Visit your Render URL:
```
https://intellipark.onrender.com
```

### 4.3 Check Logs

If something fails:
1. Go to your service in Render Dashboard
2. Click **Logs** tab
3. Look for errors after "IntelliPark API initialized successfully"

---

## Step 5: Initialize Data (Optional)

### Create Demo Parking Spaces

Use the Admin panel or API to create parking spaces:

1. Login as admin at `/login.html`
2. Go to Admin Panel (`/admin.html`)
3. Add parking spaces via the interface

Or use the API:
```bash
curl -X POST https://intellipark.onrender.com/api/parking/spaces \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"name": "A-1", "location": "Main Lot", "hourly_rate": 5.0}'
```

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SECRET_KEY` | Yes | Flask secret key (auto-generated) |
| `FLASK_ENV` | Yes | Set to `production` |
| `DEBUG` | No | Set to `false` in production |
| `ADMIN_EMAIL` | No | Admin user email |
| `ADMIN_PASSWORD` | Yes* | Admin password (12+ chars, mixed) |
| `CORS_ORIGINS` | No | Allowed origins (auto-configured) |
| `MAIL_SERVER` | No | SMTP server for emails |
| `MAIL_USERNAME` | No | SMTP username |
| `MAIL_PASSWORD` | No | SMTP password |
| `STRIPE_SECRET_KEY` | No | Stripe API key for payments |

*Required if you want an admin user

---

## Troubleshooting

### "Application Error" or 502

1. Check Render logs for specific error
2. Common causes:
   - Missing `DATABASE_URL` - ensure PostgreSQL is connected
   - Missing `SECRET_KEY` - should be auto-generated
   - Startup timeout - free tier can be slow on first request

### Database Connection Failed

1. Verify PostgreSQL is running in Render Dashboard
2. Check `DATABASE_URL` is set correctly
3. Ensure database and web service are in same region

### Static Files Not Loading

1. Check that frontend files exist in the repository
2. Verify the path calculation in `app/__init__.py`
3. Check browser console for 404 errors

### Admin Login Not Working

1. Ensure `ADMIN_PASSWORD` meets requirements:
   - 12+ characters
   - Uppercase letter
   - Lowercase letter
   - Number
   - Special character (!@#$%^&*)
2. Check logs for "SECURITY ERROR" messages

---

## Custom Domain (Optional)

1. Go to your service → **Settings** → **Custom Domains**
2. Add your domain
3. Configure DNS:
   - Add CNAME record pointing to `intellipark.onrender.com`
4. Render will auto-provision SSL certificate

---

## Updating the Application

Render auto-deploys when you push to the `main` branch:

```bash
git add .
git commit -m "Update feature"
git push origin main
```

Render will automatically:
1. Detect the push
2. Build new version
3. Deploy with zero downtime

---

## Free Tier Limitations

Render free tier includes:
- 750 hours/month of web service runtime
- PostgreSQL with 1GB storage (90-day retention)
- Auto-sleep after 15 minutes of inactivity
- Cold start delay (~30 seconds after sleep)

For production use, consider upgrading to:
- **Starter** ($7/month): No sleep, better performance
- **PostgreSQL Starter** ($7/month): Persistent database

---

## Support

- Render Docs: https://render.com/docs
- IntelliPark Issues: https://github.com/GullibleControv/IntelliPark/issues
