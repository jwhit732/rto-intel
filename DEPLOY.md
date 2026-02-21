# RTO Intel - VPS Deployment Guide

## Quick Deploy to Digital Ocean

### 1. Push to GitHub (Private Repo)

```bash
# On your Windows machine
git init
git add .
git commit -m "RTO Intel v1.0 - ready for deployment"
git remote add origin git@github.com:yourusername/rto-intel.git
git push -u origin main
```

### 2. Clone on VPS

```bash
# SSH to your droplet
ssh root@your-vps-ip

# Clone repo
cd /root
git clone git@github.com:yourusername/rto-intel.git
cd rto-intel

# Install dependencies
pip install -r requirements.txt
```

### 3. Copy Database from Windows

```bash
# On Windows (Git Bash or PowerShell)
scp data/rto_intel.db root@your-vps-ip:/root/rto-intel/data/
```

### 4. Configure Environment

```bash
# On VPS
cp .env.example .env
nano .env

# Add your Anthropic API key
ANTHROPIC_API_KEY=sk-ant-...
```

### 5. Test Run

```bash
cd /root/rto-intel
python -m src.weekly_run
```

### 6. Set Up Weekly Cron

```bash
# Friday 7am AEST = Thursday 8pm UTC (adjust for your timezone)
crontab -e

# Add this line:
0 20 * * 4 cd /root/rto-intel && /usr/bin/python3 -m src.weekly_run >> /var/log/rto-intel.log 2>&1
```

---

## Output Files for OpenClaw

After each run, these files are created in `/root/rto-intel/output/`:

| File | Purpose |
|------|---------|
| `latest_events.json` | Structured events with contact info |
| `latest_digest.html` | HTML email digest |
| `latest_meta.json` | Run status and metadata |

### OpenClaw Integration

OpenClaw reads `/root/rto-intel/output/latest_events.json`:

```json
{
  "generated_at": "2026-02-28T07:00:00",
  "event_count": 12,
  "events": [
    {
      "rto_code": "41386",
      "rto_name": "Austral College",
      "industry": "Community Services",
      "event_type": "regulatory_new",
      "outreach_score": "High",
      "suggested_opening": "I noticed...",
      "business_implication": "The dual conditions...",
      "contact_name": "Candice Taylor",
      "contact_email": "candice@australcollege.com.au",
      "contact_role": "CEO",
      "website": "http://www.australcollege.com.au"
    }
  ]
}
```

OpenClaw filters to `outreach_score: "High"` and drafts emails.

---

## Updating the Pipeline

```bash
# On VPS
cd /root/rto-intel
git pull origin main
```

Database persists between updates.

---

## Monitoring

```bash
# Check last run
cat /root/rto-intel/output/latest_meta.json

# View logs
tail -100 /var/log/rto-intel.log

# Check cron
crontab -l
```
