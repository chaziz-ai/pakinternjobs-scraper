import os
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from supabase import create_client
import feedparser
from slugify import slugify

# ─── SUPABASE CONNECTION ───────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ─── HELPERS ──────────────────────────────────────────────
def categorize(title, desc=""):
    text = (title + " " + desc).lower()
    if any(w in text for w in ["software","developer","engineer","react","python","java","frontend","backend","fullstack","devops","cloud","ai","ml","data science","programmer","coding"]):
        return "Technology"
    if any(w in text for w in ["marketing","seo","social media","brand","content","digital","campaign","advertising"]):
        return "Marketing"
    if any(w in text for w in ["finance","account","banking","audit","tax","treasury","investment","financial"]):
        return "Banking & Finance"
    if any(w in text for w in ["design","ui","ux","graphic","figma","creative","illustrator","photoshop"]):
        return "Design"
    if any(w in text for w in ["sales","business development","bd","growth","client","revenue"]):
        return "Sales"
    if any(w in text for w in ["hr","human resource","recruiter","talent","people ops"]):
        return "Human Resources"
    if any(w in text for w in ["data analyst","analytics","bi","sql","tableau","power bi","excel"]):
        return "Data & Analytics"
    if any(w in text for w in ["operations","supply chain","logistics","procurement","warehouse"]):
        return "Operations"
    if any(w in text for w in ["teacher","education","training","tutor","lecturer","professor"]):
        return "Education"
    if any(w in text for w in ["health","medical","pharma","nurse","doctor","clinical","lab"]):
        return "Healthcare"
    if any(w in text for w in ["government","civil service","public sector","ministry","federal","provincial"]):
        return "Government"
    if any(w in text for w in ["intern","internship","trainee","graduate trainee","management trainee"]):
        return "Internship"
    return "General"

def make_hash(title, company, location):
    raw = f"{title.lower().strip()}{company.lower().strip()}{location.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()

def make_slug(title, company, city):
    base = f"{title} {company} {city}"
    return slugify(base)[:100]

def save_job(job):
    try:
        existing = supabase.table("jobs_pakistan").select("id").eq("hash", job["hash"]).execute()
        if existing.data:
            print(f"  ⏭ Duplicate: {job['title']}")
            return
        supabase.table("jobs_pakistan").insert(job).execute()
        print(f"  ✅ Saved: {job['title']} @ {job['company']}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

def build_job(title, company, location, apply_url, source, job_type="fulltime", desc=""):
    return {
        "title": title,
        "company": company,
        "location": location,
        "category": categorize(title, desc),
        "apply_url": apply_url,
        "posted_at": datetime.now().isoformat(),
        "deadline_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "hash": make_hash(title, company, location),
        "source": source,
        "url": apply_url,
        "type": job_type,
        "slug": make_slug(title, company, location),
        "seo_keywords": f"{title}, {company} jobs Pakistan, {location} jobs",
        "expires_at": (datetime.now() + timedelta(days=45)).isoformat()
    }

def expire_old_jobs():
    cutoff = (datetime.now() - timedelta(days=45)).isoformat()
    try:
        supabase.table("jobs_pakistan").delete().lt("posted_at", cutoff).execute()
        print("\n🗑 Expired old jobs removed")
    except Exception as e:
        print(f"❌ Expire error: {e}")

# ══════════════════════════════════════════════════════════
# SCRAPER 1 — Rozee.pk RSS
# ══════════════════════════════════════════════════════════
def scrape_rozee():
    print("\n🔍 Scraping Rozee.pk...")
    try:
        feed = feedparser.parse("https://www.rozee.pk/rss/jobs")
        for entry in feed.entries[:40]:
            title = entry.get("title", "").strip()
            company = entry.get("author", "Unknown").strip()
            location = entry.get("tags", [{}])[0].get("term", "Pakistan") if entry.get("tags") else "Pakistan"
            apply_url = entry.get("link", "")
            desc = entry.get("summary", "")
            if not title or not apply_url:
                continue
            save_job(build_job(title, company, location, apply_url, "Rozee.pk", "fulltime", desc))
    except Exception as e:
        print(f"❌ Rozee error: {e}")

# ══════════════════════════════════════════════════════════
# SCRAPER 2 — Mustakbil RSS
# ══════════════════════════════════════════════════════════
def scrape_mustakbil():
    print("\n🔍 Scraping Mustakbil...")
    try:
        feed = feedparser.parse("https://mustakbil.com/jobs/rss")
        for entry in feed.entries[:40]:
            title = entry.get("title", "").strip()
            company = entry.get("author", "Unknown").strip()
            apply_url = entry.get("link", "")
            desc = entry.get("summary", "")
            if not title or not apply_url:
                continue
            save_job(build_job(title, company, "Pakistan", apply_url, "Mustakbil", "fulltime", desc))
    except Exception as e:
        print(f"❌ Mustakbil error: {e}")

# ══════════════════════════════════════════════════════════
# SCRAPER 3 — Internshala Pakistan
# ══════════════════════════════════════════════════════════
def scrape_internshala():
    print("\n🔍 Scraping Internshala...")
    try:
        url = "https://internshala.com/internships/pakistan-internships"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.select(".internship_meta")
        for card in cards[:25]:
            try:
                title = card.select_one(".profile h3")
                company = card.select_one(".company_name")
                location = card.select_one(".location_link")
                link = card.select_one("a.view_internship_button")
                title = title.text.strip() if title else ""
                company = company.text.strip() if company else "Unknown"
                location = location.text.strip() if location else "Pakistan"
                apply_url = "https://internshala.com" + link["href"] if link else ""
                if not title or not apply_url:
                    continue
                save_job(build_job(title, company, location, apply_url, "Internshala", "internship"))
            except Exception as e:
                print(f"  ⚠ Card error: {e}")
    except Exception as e:
        print(f"❌ Internshala error: {e}")

# ══════════════════════════════════════════════════════════
# SCRAPER 4 — LinkedIn Public Pakistan
# ══════════════════════════════════════════════════════════
def scrape_linkedin():
    print("\n🔍 Scraping LinkedIn...")
    try:
        url = "https://www.linkedin.com/jobs/search/?location=Pakistan&f_E=1%2C2&f_JT=F%2CI"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.select(".base-card")
        for card in cards[:25]:
            try:
                title = card.select_one(".base-search-card__title")
                company = card.select_one(".base-search-card__subtitle")
                location = card.select_one(".job-search-card__location")
                link = card.select_one("a.base-card__full-link")
                title = title.text.strip() if title else ""
                company = company.text.strip() if company else "Unknown"
                location = location.text.strip() if location else "Pakistan"
                apply_url = link["href"] if link else ""
                if not title or not apply_url:
                    continue
                save_job(build_job(title, company, location, apply_url, "LinkedIn", "fulltime"))
            except Exception as e:
                print(f"  ⚠ Card error: {e}")
    except Exception as e:
        print(f"❌ LinkedIn error: {e}")

# ══════════════════════════════════════════════════════════
# SCRAPER 5 — Systems Limited
# ══════════════════════════════════════════════════════════
def scrape_systems_limited():
    print("\n🔍 Scraping Systems Limited...")
    try:
        url = "https://www.systemsltd.com/careers"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.select(".job-opening, .career-item, .position, .job-listing")
        for card in cards[:20]:
            try:
                title = card.select_one("h3, h4, .job-title, .position-title")
                location = card.select_one(".location, .city, .job-location")
                link = card.select_one("a")
                title = title.text.strip() if title else ""
                location = location.text.strip() if location else "Lahore"
                apply_url = link["href"] if link else url
                if not title:
                    continue
                if not apply_url.startswith("http"):
                    apply_url = "https://www.systemsltd.com" + apply_url
                save_job(build_job(title, "Systems Limited", location, apply_url, "Systems Limited"))
            except Exception as e:
                print(f"  ⚠ Error: {e}")
    except Exception as e:
        print(f"❌ Systems Limited error: {e}")

# ══════════════════════════════════════════════════════════
# SCRAPER 6 — Netsol Technologies
# ══════════════════════════════════════════════════════════
def scrape_netsol():
    print("\n🔍 Scraping Netsol Technologies...")
    try:
        url = "https://www.netsoltech.com/careers"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.select(".career-item, .job-opening, .position, .job-card")
        for card in cards[:20]:
            try:
                title = card.select_one("h3, h4, .job-name, .job-title")
                location = card.select_one(".location, .city")
                link = card.select_one("a")
                title = title.text.strip() if title else ""
                location = location.text.strip() if location else "Lahore"
                apply_url = link["href"] if link else url
                if not title:
                    continue
                if not apply_url.startswith("http"):
                    apply_url = "https://www.netsoltech.com" + apply_url
                save_job(build_job(title, "Netsol Technologies", location, apply_url, "Netsol Technologies"))
            except Exception as e:
                print(f"  ⚠ Error: {e}")
    except Exception as e:
        print(f"❌ Netsol error: {e}")

# ══════════════════════════════════════════════════════════
# SCRAPER 7 — Jazz Pakistan
# ══════════════════════════════════════════════════════════
def scrape_jazz():
    print("\n🔍 Scraping Jazz Pakistan...")
    try:
        url = "https://jazz.com.pk/careers/"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.select(".position-card, .job-card, .vacancy, .career-item")
        for card in cards[:20]:
            try:
                title = card.select_one("h3, h4, .position-title, .job-title")
                location = card.select_one(".location, .city")
                link = card.select_one("a")
                title = title.text.strip() if title else ""
                location = location.text.strip() if location else "Islamabad"
                apply_url = link["href"] if link else url
                if not title:
                    continue
                if not apply_url.startswith("http"):
                    apply_url = "https://jazz.com.pk" + apply_url
                save_job(build_job(title, "Jazz Pakistan", location, apply_url, "Jazz Pakistan"))
            except Exception as e:
                print(f"  ⚠ Error: {e}")
    except Exception as e:
        print(f"❌ Jazz error: {e}")

# ══════════════════════════════════════════════════════════
# SCRAPER 8 — HBL Bank
# ══════════════════════════════════════════════════════════
def scrape_hbl():
    print("\n🔍 Scraping HBL...")
    try:
        url = "https://www.hbl.com/careers"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.select(".career-posting, .job-item, .vacancy-item, .job-card")
        for card in cards[:20]:
            try:
                title = card.select_one("h3, h4, .job-title")
                location = card.select_one(".location, .city")
                link = card.select_one("a")
                title = title.text.strip() if title else ""
                location = location.text.strip() if location else "Karachi"
                apply_url = link["href"] if link else url
                if not title:
                    continue
                if not apply_url.startswith("http"):
                    apply_url = "https://www.hbl.com" + apply_url
                save_job(build_job(title, "HBL", location, apply_url, "HBL", "fulltime"))
            except Exception as e:
                print(f"  ⚠ Error: {e}")
    except Exception as e:
        print(f"❌ HBL error: {e}")

# ══════════════════════════════════════════════════════════
# SCRAPER 9 — Meezan Bank
# ══════════════════════════════════════════════════════════
def scrape_meezan():
    print("\n🔍 Scraping Meezan Bank...")
    try:
        url = "https://www.meezanbank.com/careers/"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.select(".job-card, .career-item, .vacancy, .job-listing")
        for card in cards[:20]:
            try:
                title = card.select_one("h3, h4, .job-title")
                location = card.select_one(".location, .city")
                link = card.select_one("a")
                title = title.text.strip() if title else ""
                location = location.text.strip() if location else "Karachi"
                apply_url = link["href"] if link else url
                if not title:
                    continue
                if not apply_url.startswith("http"):
                    apply_url = "https://www.meezanbank.com" + apply_url
                save_job(build_job(title, "Meezan Bank", location, apply_url, "Meezan Bank", "fulltime"))
            except Exception as e:
                print(f"  ⚠ Error: {e}")
    except Exception as e:
        print(f"❌ Meezan error: {e}")

# ══════════════════════════════════════════════════════════
# SCRAPER 10 — Telenor Pakistan
# ══════════════════════════════════════════════════════════
def scrape_telenor():
    print("\n🔍 Scraping Telenor Pakistan...")
    try:
        url = "https://www.telenor.com.pk/about-telenor/careers/"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.select(".job-listing, .career-item, .position, .job-card")
        for card in cards[:20]:
            try:
                title = card.select_one("h3, h4, .job-title, .position")
                location = card.select_one(".location, .city")
                link = card.select_one("a")
                title = title.text.strip() if title else ""
                location = location.text.strip() if location else "Islamabad"
                apply_url = link["href"] if link else url
                if not title:
                    continue
                if not apply_url.startswith("http"):
                    apply_url = "https://www.telenor.com.pk" + apply_url
                save_job(build_job(title, "Telenor Pakistan", location, apply_url, "Telenor Pakistan"))
            except Exception as e:
                print(f"  ⚠ Error: {e}")
    except Exception as e:
        print(f"❌ Telenor error: {e}")

# ══════════════════════════════════════════════════════════
# SCRAPER 11 — NTS Government Jobs
# ══════════════════════════════════════════════════════════
def scrape_nts():
    print("\n🔍 Scraping NTS...")
    try:
        url = "https://www.nts.org.pk/nts/index.php"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.select(".job-item, .vacancy-item, tr")
        for card in cards[:20]:
            try:
                title = card.select_one(".job-title, td:nth-child(2), h4")
                link = card.select_one("a")
                title = title.text.strip() if title else ""
                apply_url = link["href"] if link else url
                if not title or len(title) < 5:
                    continue
                if not apply_url.startswith("http"):
                    apply_url = "https://www.nts.org.pk" + apply_url
                save_job(build_job(title, "NTS Pakistan", "Pakistan", apply_url, "NTS", "fulltime"))
            except Exception as e:
                print(f"  ⚠ Error: {e}")
    except Exception as e:
        print(f"❌ NTS error: {e}")

# ══════════════════════════════════════════════════════════
# SCRAPER 12 — Unilever Pakistan
# ══════════════════════════════════════════════════════════
def scrape_unilever():
    print("\n🔍 Scraping Unilever Pakistan...")
    try:
        url = "https://careers.unilever.com/search?country=Pakistan"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.select(".job-tile, .job-card, .search-result-item")
        for card in cards[:20]:
            try:
                title = card.select_one("h3, h4, .job-title, .position-title")
                location = card.select_one(".location, .job-location")
                link = card.select_one("a")
                title = title.text.strip() if title else ""
                location = location.text.strip() if location else "Karachi"
                apply_url = link["href"] if link else url
                if not title:
                    continue
                if not apply_url.startswith("http"):
                    apply_url = "https://careers.unilever.com" + apply_url
                save_job(build_job(title, "Unilever Pakistan", location, apply_url, "Unilever"))
            except Exception as e:
                print(f"  ⚠ Error: {e}")
    except Exception as e:
        print(f"❌ Unilever error: {e}")

# ══════════════════════════════════════════════════════════
# SCRAPER 13 — P&G Pakistan
# ══════════════════════════════════════════════════════════
def scrape_pg():
    print("\n🔍 Scraping P&G Pakistan...")
    try:
        url = "https://www.pgcareers.com/search-jobs/results?keyword=&country=Pakistan"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.select(".job-list-item, .job-card, .search-result")
        for card in cards[:20]:
            try:
                title = card.select_one("h3, h4, .job-title")
                location = card.select_one(".location, .job-location")
                link = card.select_one("a")
                title = title.text.strip() if title else ""
                location = location.text.strip() if location else "Karachi"
                apply_url = link["href"] if link else url
                if not title:
                    continue
                if not apply_url.startswith("http"):
                    apply_url = "https://www.pgcareers.com" + apply_url
                save_job(build_job(title, "P&G Pakistan", location, apply_url, "P&G"))
            except Exception as e:
                print(f"  ⚠ Error: {e}")
    except Exception as e:
        print(f"❌ P&G error: {e}")

# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("🚀 PakInternJobs Scraper Starting...")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    scrape_rozee()
    scrape_mustakbil()
    scrape_internshala()
    scrape_linkedin()
    scrape_systems_limited()
    scrape_netsol()
    scrape_jazz()
    scrape_hbl()
    scrape_meezan()
    scrape_telenor()
    scrape_nts()
    scrape_unilever()
    scrape_pg()
    expire_old_jobs()

    print("\n" + "=" * 50)
    print("✅ All scrapers completed!")
