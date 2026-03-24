import os
import requests
import schedule
import time
import json
import threading
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

JOB_SEARCHES = [
    "Network Engineer",
    "IT Support",
    "Help Desk",
    "Cybersecurity Analyst",
    "System Administrator",
    "Network Administrator",
    "Junior IT",
    "IT Intern",
]

JOB_TYPES = ["full_time", "part_time", "contract"]
LOCATIONS = ["Calgary", "Edmonton", "Remote Canada"]
SEEN_JOBS_FILE = "seen_jobs.json"


def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_jobs(seen_jobs):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen_jobs), f)


def send_telegram_message(message):
    if not TELEGRAM_CHAT_ID:
        print("TELEGRAM_CHAT_ID not set — run /chatid in Telegram first")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    chunks = [message[i:i+4096] for i in range(0, len(message), 4096)]
    for chunk in chunks:
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        })


def search_adzuna(keyword, location="Calgary"):
    try:
        url = f"https://api.adzuna.com/v1/api/jobs/ca/search/1"
        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "what": keyword,
            "where": location,
            "results_per_page": 5,
            "content-type": "application/json"
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get("results", [])
    except Exception as e:
        print(f"Adzuna error: {e}")
    return []


def is_relevant_job(title):
    title_lower = title.lower()
    relevant_keywords = [
        "network", "it support", "help desk", "helpdesk",
        "cyber", "security", "sysadmin", "system admin",
        "cloud", "intern", "junior", "administrator"
    ]
    return any(kw in title_lower for kw in relevant_keywords)


def is_government_job(title, company):
    gov_keywords = ["government", "federal", "municipal", "province",
                   "alberta", "canada revenue", "rcmp", "city of"]
    combined = (title + " " + company).lower()
    return any(kw in combined for kw in gov_keywords)


def fetch_all_jobs():
    seen_jobs = load_seen_jobs()
    new_jobs = []

    for keyword in JOB_SEARCHES:
        for location in LOCATIONS:
            results = search_adzuna(keyword, location)
            for job in results:
                job_id = job.get("id", "")
                if job_id and job_id not in seen_jobs:
                    title = job.get("title", "Unknown")
                    company = job.get("company", {}).get("display_name", "Unknown")
                    if is_relevant_job(title):
                        seen_jobs.add(job_id)
                        new_jobs.append({
                            "id": job_id,
                            "title": title,
                            "company": company,
                            "location": job.get("location", {}).get("display_name", location),
                            "salary": job.get("salary_min", ""),
                            "url": job.get("redirect_url", ""),
                            "description": job.get("description", "")[:200],
                            "is_gov": is_government_job(title, company),
                            "created": job.get("created", "")
                        })

    save_seen_jobs(seen_jobs)
    return new_jobs


def format_job_briefing(jobs):
    if not jobs:
        return "🤖 <b>Jarvis Morning Briefing</b>\n\nNo new IT jobs found in Calgary today. I'll keep watching!"

    now = datetime.now().strftime("%B %d, %Y")
    msg = f"🤖 <b>Jarvis Morning Job Briefing</b>\n📅 {now}\n"
    msg += f"Found <b>{len(jobs)}</b> new IT jobs for you Danish!\n"
    msg += "─────────────────────\n\n"

    calgary_jobs = [j for j in jobs if "calgary" in j["location"].lower()]
    remote_jobs = [j for j in jobs if "remote" in j["location"].lower()]
    gov_jobs = [j for j in jobs if j["is_gov"]]

    if calgary_jobs:
        msg += "📍 <b>Calgary Jobs</b>\n\n"
        for job in calgary_jobs[:5]:
            msg += format_single_job(job)

    if remote_jobs:
        msg += "\n🌐 <b>Remote Jobs</b>\n\n"
        for job in remote_jobs[:3]:
            msg += format_single_job(job)

    if gov_jobs:
        msg += "\n🏛 <b>Government Roles</b> (relocation considered)\n\n"
        for job in gov_jobs[:3]:
            msg += format_single_job(job)

    msg += "─────────────────────\n"
    msg += "Reply <b>/jobs</b> anytime to get latest jobs on demand."
    return msg


def format_single_job(job):
    msg = f"💼 <b>{job['title']}</b>\n"
    msg += f"🏢 {job['company']}\n"
    msg += f"📍 {job['location']}\n"
    if job['salary']:
        msg += f"💰 ${job['salary']:,.0f}/yr\n"
    if job['description']:
        msg += f"📝 {job['description']}...\n"
    msg += f"🔗 <a href='{job['url']}'>View Job</a>\n\n"
    return msg


def daily_briefing():
    print(f"Running daily job briefing at {datetime.now()}")
    jobs = fetch_all_jobs()
    message = format_job_briefing(jobs)
    send_telegram_message(message)
    print(f"Briefing sent — {len(jobs)} new jobs found")


def run_scheduler():
    schedule.every().day.at("07:00").do(daily_briefing)
    print("Job scheduler running — briefing at 7:00 AM daily")
    while True:
        schedule.run_pending()
        time.sleep(60)


def start_job_scheduler():
    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()


if __name__ == "__main__":
    daily_briefing()