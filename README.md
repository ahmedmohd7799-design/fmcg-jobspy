# FMCG JobSpy feed

Every morning (07:17 Dubai), GitHub runs JobSpy to search LinkedIn, Indeed, Google Jobs, Bayt and Glassdoor for FMCG brand, category, trade and product marketing roles in the six GCC countries. It filters out junior roles, director-level roles, nationals-only roles and roles in other fields, then saves the results as `jobs.json`. At 08:31 your FMCG HUB refresh reads that file, scores each role against your CV and adds the good matches to the hub.

## One-time setup (about 10 minutes, no coding)

1. **Create a free GitHub account** at github.com, if you don't already have one.
2. **Create a new repository.** Click **+** (top right) → **New repository**. Name it `fmcg-jobspy`, choose **Public**, then click **Create repository**.
   Public is needed so the hub can read the file without a password. Only job listings go in it; your CV and personal details don't.
3. **Upload the files.** On the new repo page, click **uploading an existing file** and drag in everything from this zip, keeping the `.github` folder. Then click **Commit changes**.
   If your browser hides the `.github` folder, use **Add file → Create new file** instead, type `.github/workflows/jobspy.yml` as the name, and paste in the contents of that file.
4. **Run it once.** Open the **Actions** tab and enable workflows if GitHub asks. Click **JobSpy daily feed**, then **Run workflow**. The run takes 10–30 minutes. When it finishes, `jobs.json` appears in the repo.
5. **Send Claude the link.** Open `jobs.json`, click **Raw**, and copy the address. It looks like
   `https://raw.githubusercontent.com/<your-username>/fmcg-jobspy/main/jobs.json`.
   Paste it to Claude, and Claude will connect it to your hub.

## Things to know
- **LinkedIn may block GitHub's servers** on some days. Indeed, Google and Bayt usually still work. If LinkedIn keeps coming back with 0 results, you can add a residential proxy (about $5–10 a month) under **Settings → Secrets and variables → Actions → New repository secret**, named `JOBSPY_PROXY`.
- **To change the searches**, edit the lists at the top of `scrape.py` (`MAIN_TERMS`, `MARKETS`, `INCLUDE`, `EXCLUDE`).
- **It reads public listings only.** It never logs in to any site. Scraping LinkedIn goes against LinkedIn's terms of use, so keep the volume modest, as it is set now.
