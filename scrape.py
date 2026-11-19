"""
FMCG Job Hub - JobSpy feed for Mohammed Ahmed.

Searches LinkedIn, Indeed, Google Jobs, Bayt and Glassdoor for GCC FMCG
marketing roles, filters them, and writes jobs.json. The hub's daily
refresh reads that file and scores/adds the good matches.

Run locally:   python scrape.py
Run on GitHub: the workflow in .github/workflows/jobspy.yml runs it daily.
"""
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
from jobspy import scrape_jobs

# ---------- settings you can change ----------
HOURS_OLD = 72          # only postings from the last 3 days
RESULTS_PER_SEARCH = 25
KEEP_DAYS = 7           # keep a rolling week in jobs.json
PROXY = os.environ.get("JOBSPY_PROXY") or None   # optional, e.g. "user:pass@host:port"

MAIN_TERMS = [
    "brand manager", "assistant brand manager", "category manager",
    "trade marketing", "shopper marketing", "product manager FMCG",
    "marketing manager FMCG", "marketing executive FMCG",
]
SHORT_TERMS = ["brand manager", "category manager", "FMCG marketing"]

# (label, LinkedIn/Google location, Indeed country, Indeed city, terms)
MARKETS = [
    ("UAE", "United Arab Emirates", "united arab emirates", "Dubai", MAIN_TERMS),
    ("KSA", "Saudi Arabia", "saudi arabia", "Riyadh", MAIN_TERMS),
    ("Qatar", "Qatar", "qatar", "Doha", SHORT_TERMS),
    ("Kuwait", "Kuwait", "kuwait", "Kuwait City", SHORT_TERMS),
    ("Oman", "Oman", "oman", "Muscat", SHORT_TERMS),
    ("Bahrain", "Bahrain", "bahrain", "Manama", SHORT_TERMS),
]
BAYT_TERMS = ["brand manager FMCG", "category manager", "trade marketing", "assistant brand manager"]

INCLUDE = re.compile(
    r"brand|category|trade market|shopper|product (manager|marketing)|npd|innovation|"
    r"marketing (manager|executive|specialist|lead)|customer (development|marketing)|key account",
    re.I)
EXCLUDE = re.compile(
    r"intern|trainee|graduate|director|head of|vice president|\bvp\b|general manager|"
    r"designer|engineer|developer|software|seo|performance market|social media|"
    r"real estate|property|hotel|clinic|hospital|pharma sales|medical rep|"
    r"emirati|saudi national|nationals only|uae national",
    re.I)
GCC = {
    "UAE": ["united arab emirates", "uae", "dubai", "abu dhabi", "sharjah", "ajman", "al ain", "ras al"],
    "KSA": ["saudi", "ksa", "riyadh", "jeddah", "dammam", "khobar", "makkah", "mecca", "medina"],
    "Qatar": ["qatar", "doha"],
    "Kuwait": ["kuwait"],
    "Oman": ["oman", "muscat"],
    "Bahrain": ["bahrain", "manama"],
}
# ---------------------------------------------


def country_of(location: str) -> str:
    loc = (location or "").lower()
    for c, words in GCC.items():
        if any(w in loc for w in words):
            return c
    return ""


def safe_scrape(label, **kw):
    for attempt in (1, 2):
        try:
            df = scrape_jobs(verbose=0, proxies=PROXY, **kw)
            print(f"  {label}: {len(df)} rows")
            return df
        except Exception as e:  # one site failing must not stop the run
            print(f"  {label}: error ({attempt}) {str(e)[:120]}")
            time.sleep(5)
    return pd.DataFrame()


def run():
    frames, errors = [], []
    for label, loc, indeed_c, city, terms in MARKETS:
        for term in terms:
            frames.append(safe_scrape(f"linkedin {label} '{term}'",
                site_name=["linkedin"], search_term=term, location=loc,
                results_wanted=RESULTS_PER_SEARCH, hours_old=HOURS_OLD,
                linkedin_fetch_description=True))
            time.sleep(4)  # be gentle with LinkedIn
            frames.append(safe_scrape(f"indeed {label} '{term}'",
                site_name=["indeed"], search_term=term, location=city,
                country_indeed=indeed_c, results_wanted=RESULTS_PER_SEARCH,
                hours_old=HOURS_OLD))
        frames.append(safe_scrape(f"google {label}",
            site_name=["google"],
            google_search_term=f"brand manager OR category manager OR trade marketing FMCG jobs in {loc} since 3 days ago",
            results_wanted=RESULTS_PER_SEARCH))
        if label in ("UAE", "KSA"):
            frames.append(safe_scrape(f"glassdoor {label}",
                site_name=["glassdoor"], search_term="brand manager", location=city,
                country_indeed=indeed_c, results_wanted=15, hours_old=HOURS_OLD))
    for term in BAYT_TERMS:
        frames.append(safe_scrape(f"bayt '{term}'", site_name=["bayt"],
                                  search_term=term, results_wanted=RESULTS_PER_SEARCH))

    frames = [f for f in frames if f is not None and not f.empty]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    new = []
    if not df.empty:
        df = df.where(pd.notnull(df), None)
        for r in df.to_dict("records"):
            title = str(r.get("title") or "")
            loc = str(r.get("location") or "")
            c = country_of(loc)
            if not c or not INCLUDE.search(title) or EXCLUDE.search(title):
                continue
            desc = str(r.get("description") or "")
            if re.search(r"nationals? only|emirati only|saudi nationals", desc, re.I):
                continue
            emails = r.get("emails")
            if isinstance(emails, str):
                emails = [e.strip().lower() for e in emails.split(",") if e.strip()]
            elif not isinstance(emails, list):
                emails = []
            dp = r.get("date_posted")
            new.append({
                "site": r.get("site"),
                "title": title,
                "company": r.get("company"),
                "location": loc,
                "country": c,
                "city": loc.split(",")[0].strip(),
                "date_posted": str(dp) if dp else "",
                "job_url": r.get("job_url"),
                "job_url_direct": r.get("job_url_direct"),
                "description": desc[:8000],
                "emails": emails or [],
                "min_amount": r.get("min_amount"),
                "max_amount": r.get("max_amount"),
                "currency": r.get("currency"),
                "interval": r.get("interval"),
                "job_level": r.get("job_level"),
                "company_industry": r.get("company_industry"),
                "seen_at": datetime.now(timezone.utc).isoformat(),
            })

    # merge with last run's file, dedupe by URL, keep a rolling week
    old = []
    if os.path.exists("jobs.json"):
        try:
            old = json.load(open("jobs.json")).get("jobs", [])
        except Exception:
            old = []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).isoformat()
    by_url = {}
    for j in old + new:
        if (j.get("seen_at") or "") < cutoff:
            continue
        key = j.get("job_url") or f"{j.get('title')}|{j.get('company')}|{j.get('country')}"
        by_url[key] = j
    jobs = sorted(by_url.values(), key=lambda j: j.get("date_posted") or "", reverse=True)

    new_unique = {j.get("job_url") for j in new}
    out = {"generated_at": datetime.now(timezone.utc).isoformat(),
           "new_this_run": len(new_unique), "count": len(jobs), "errors": errors, "jobs": jobs}
    with open("jobs.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print(f"Done: {len(new_unique)} matching this run, {len(jobs)} in the rolling file.")


if __name__ == "__main__":
    run()
