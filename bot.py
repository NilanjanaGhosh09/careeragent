import os, time, json, base64, requests

TG = os.environ["TELEGRAM_TOKEN"]
KEY = os.environ["GEMINI_API_KEY"]
TG_URL = f"https://api.telegram.org/bot{TG}"
MODELS = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.8-flash"]
DB = "profiles.json"
TRACK_DB = "track.json"

BASE = (
    "You are CareerAgent, a professional career assistant for students "
    "and freshers in India. Be clear, concise and friendly. Do not use "
    "markdown symbols like ** or #. Help with CVs, finding startup jobs, "
    "and writing outreach emails to founders. "
    "Never invent facts about the user."
)

EXTRACT = (
    "Read this CV and write a clean candidate profile with these headings: "
    "Name, Education, Skills, Projects, Experience, Certifications, "
    "Likely target roles (3). Use only what is in the CV. Keep it short. "
    "Do not use markdown symbols like ** or #."
)

EMAIL_RULES = (
    "Write a cold email from the candidate to a startup founder asking "
    "for an interview or internship. Rules: under 120 words; a clear "
    "subject line; start with one specific line about the startup; "
    "mention only 2 relevant things from the candidate's profile; end "
    "with one simple ask (a 15 minute call). Sound human and polite. "
    "Do not invent any fact about the candidate or the startup. Do not "
    "use markdown symbols. Output: Subject line, then the email body."
)

def load(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}

def save(d, path):
    json.dump(d, open(path, "w"))

profiles = load(DB)
tracks = load(TRACK_DB)

def gemini(parts, system):
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": parts}],
    }
    for m in MODELS:
        for _ in range(2):
            data = None
            try:
                url = ("https://generativelanguage.googleapis.com/v1beta/"
                       f"models/{m}:generateContent")
                r = requests.post(
                    url,
                    headers={"x-goog-api-key": KEY,
                             "content-type": "application/json"},
                    json=body, timeout=90)
                data = r.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                print(m, "failed:", str(data or e)[:200])
                time.sleep(2)
    return "Sorry, the AI is busy right now. Please try again in a minute."

def gemini_search(prompt, system):
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
    }
    for m in MODELS:
        data = None
        try:
            url = ("https://generativelanguage.googleapis.com/v1beta/"
                   f"models/{m}:generateContent")
            r = requests.post(
                url,
                headers={"x-goog-api-key": KEY,
                         "content-type": "application/json"},
                json=body, timeout=120)
            data = r.json()
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts)
        except Exception as e:
            print("search failed", m, str(data or e)[:200])
            time.sleep(2)
    return None

def send(chat_id, text):
    requests.post(f"{TG_URL}/sendMessage",
                  json={"chat_id": chat_id, "text": text[:4000]})

def tg_file(file_id):
    info = requests.get(f"{TG_URL}/getFile",
                        params={"file_id": file_id}, timeout=30).json()
    path = info["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{TG}/{path}"
    return requests.get(url, timeout=60).content

def system_for(cid):
    p = profiles.get(cid)
    if p:
        return BASE + "\n\nThe user's profile:\n" + p
    return BASE

def allowed(cid):
    today = time.strftime("%Y-%m-%d")
    d = load("usage.json")
    u = d.get(cid)
    if not u or u.get("day") != today:
        u = {"day": today, "n": 0}
    if u["n"] >= 20:
        return False
    u["n"] += 1
    d[cid] = u
    save(d, "usage.json")
    return True

def days_since(ts):
    return int((time.time() - ts) / 86400)

def show_list(items):
    if not items:
        return "Your list is empty. Add one like this:\n/track add Zepto | Aadit"
    lines = ["Your startups:"]
    for i, it in enumerate(items, 1):
        who = " (" + it["founder"] + ")" if it.get("founder") else ""
        lines.append(f"{i}. {it['name']}{who} - {it['status']} - "
                     f"{days_since(it['ts'])} days ago")
    lines.append("\nChange status: /track status 1 | replied")
    return "\n".join(lines)

WELCOME = (
    "Hi! I'm CareerAgent.\n\n"
    "Step 1: send me your CV as a PDF file.\n"
    "Step 2: write an email to a founder:\n"
    "/email Startup name | what it does | founder name\n"
    "Step 3: save the startups you emailed:\n"
    "/track add Startup name | founder name\n\n"
    "Other commands:\n"
    "/track - see your list\n"
    "/track status 1 | replied - update a startup\n"
    "/followup - who to follow up with\n"
    "/prep Role - interview practice\n"
    "/find - find startups for you\n"
    "/profile - see your profile\n"
    "/reset - delete your profile\n\n"
    "Or just ask me anything about jobs and CVs.\n\n"
    "Privacy: your CV is sent to Google AI to build your profile. Use /reset to delete it."
)

offset = None
print("Bot is running...")
while True:
    try:
        r = requests.get(f"{TG_URL}/getUpdates",
                         params={"timeout": 30, "offset": offset},
                         timeout=40).json()
        for u in r.get("result", []):
            offset = u["update_id"] + 1
            msg = u.get("message")
            if not msg:
                continue
            cid = str(msg["chat"]["id"])
            text = msg.get("text", "")
            doc = msg.get("document")
            uses_ai = bool(doc) or (text and not text.startswith(("/start", "/profile", "/reset", "/track", "/followup", "/jobs")))
            if uses_ai and not allowed(cid):
                send(cid, "Daily limit reached (20 AI requests). Please try again tomorrow.")
                continue
            if text.startswith("/start"):
                send(cid, WELCOME)
            elif text.startswith("/profile"):
                send(cid, profiles.get(cid, "No profile yet. Send your CV as a PDF."))
            elif text.startswith("/reset"):
                profiles.pop(cid, None)
                save(profiles, DB)
                send(cid, "Your profile has been deleted.")
            elif text.startswith("/followup"):
                items = tracks.get(cid, [])
                due = [(i, it) for i, it in enumerate(items, 1)
                       if it["status"] == "sent" and days_since(it["ts"]) >= 5]
                if not due:
                    send(cid, "No follow-ups needed right now. Follow up 5 days after you send an email.")
                else:
                    lines = ["Time to follow up with:"]
                    for i, it in due:
                        lines.append(f"{i}. {it['name']} - emailed {days_since(it['ts'])} days ago")
                    lines.append("\nSend a short, polite follow-up. Ask me: write a follow-up email for startup name.")
                    send(cid, "\n".join(lines))
            elif text.startswith("/track"):
                arg = text[6:].strip()
                low = arg.lower()
                items = tracks.setdefault(cid, [])
                if low.startswith("add"):
                    parts = [x.strip() for x in arg[3:].split("|")]
                    if not parts[0]:
                        send(cid, "Write it like this:\n/track add Startup name | founder name")
                    else:
                        items.append({
                            "name": parts[0],
                            "founder": parts[1] if len(parts) > 1 else "",
                            "status": "sent",
                            "ts": time.time()})
                        save(tracks, TRACK_DB)
                        send(cid, "Saved: " + parts[0] + " (status: sent).\nSee your list with /track")
                elif low.startswith("status"):
                    parts = [x.strip() for x in arg[6:].split("|")]
                    try:
                        n = int(parts[0])
                        st = parts[1].lower()
                        items[n - 1]["status"] = st
                        save(tracks, TRACK_DB)
                        send(cid, "Updated: " + items[n - 1]["name"] + " is now " + st)
                    except Exception:
                        send(cid, "Write it like this:\n/track status 1 | replied\n(Use the number from your list. Words: sent, replied, interview, offer, rejected)")
                else:
                    send(cid, show_list(items))
            elif text.startswith("/prep"):
                role = text[5:].strip()
                if not role:
                    send(cid, "Write it like this:\n/prep Backend Developer Intern")
                else:
                    send(cid, "Preparing your interview practice, please wait...")
                    ask = ("Prepare interview practice for a fresher applying for this role: " + role + ". Use the candidate's profile. Give 5 likely interview questions (mix of technical questions and questions about their own projects). For each question, give a short tip on how to answer it using the candidate's real projects and skills. Then give 2 smart questions the candidate can ask the founder. Do not invent facts about the candidate. Do not use markdown symbols.")
                    out = gemini([{"text": ask}], system_for(cid))
                    send(cid, out)
            elif text.startswith("/find"):
                topic = text[5:].strip() or "developer intern"
                if cid not in profiles:
                    send(cid, "Please send your CV as a PDF first.")
                else:
                    send(cid, "Looking for real openings, please wait...")
                    try:
                        jr = requests.get(
                            "https://remotive.com/api/remote-jobs",
                            params={"search": topic, "limit": 40},
                            headers={"User-Agent": "CareerAgentBot"},
                            timeout=30).json()
                        jobs = jr.get("jobs", [])
                    except Exception as e:
                        print("jobs failed:", e)
                        jobs = []
                    if not jobs:
                        send(cid, "No openings found for: " + topic + ". Try a simpler word like python, java, backend or intern.")
                    else:
                        lines = []
                        for job in jobs[:40]:
                            lines.append(job.get("title", "") + " | " + job.get("company_name", "") + " | " + job.get("candidate_required_location", "") + " | " + job.get("job_type", "") + " | " + job.get("url", ""))
                        ask = ("Here are real job openings from Remotive:\n" + "\n".join(lines) + "\n\nPick up to 5 that genuinely fit a fresher with 0 to 1 years of experience. Skip senior, lead, manager and non-software roles. If fewer than 5 fit, give fewer and say so. For each give: job title, company, the location restriction exactly as listed, why it fits using the candidate's real skills and projects, and the link. Say clearly if the location may not allow candidates from India. Use only the information above. Do not invent anything. Do not use markdown symbols.")
                        out = gemini([{"text": ask}], system_for(cid))
                        send(cid, out + "\n\nSource: Remotive (remotive.com). Open each link and check the details before you apply. Then use /email.")
            elif text.startswith("/jobs"):
                from urllib.parse import quote_plus
                q = text[5:].strip() or "software intern"
                e = quote_plus(q)
                send(cid, "Search links for: " + q +
                     "\n\nLinkedIn (India):\nhttps://www.linkedin.com/jobs/search/?keywords=" + e + "&location=India" +
                     "\n\nIndeed India:\nhttps://in.indeed.com/jobs?q=" + e +
                     "\n\nInternshala (via Google):\nhttps://www.google.com/search?q=site%3Ainternshala.com+" + e +
                     "\n\nWellfound startups (via Google):\nhttps://www.google.com/search?q=site%3Awellfound.com+" + e + "+India" +
                     "\n\nTap a link, pick a company, then use /email and /track.")
            elif text.startswith("/email"):
                if cid not in profiles:
                    send(cid, "Please send your CV as a PDF first.")
                else:
                    parts = [x.strip() for x in text[6:].split("|")]
                    if len(parts) < 2 or not parts[0]:
                        send(cid, "Please write it like this:\n/email Startup name | what it does | founder name")
                    else:
                        name = parts[0]
                        what = parts[1]
                        founder = parts[2] if len(parts) > 2 and parts[2] else "the founder"
                        send(cid, "Writing your email, please wait...")
                        ask = (EMAIL_RULES + "\n\nStartup: " + name +
                               "\nWhat it does: " + what +
                               "\nFounder: " + founder)
                        out = gemini([{"text": ask}], system_for(cid))
                        send(cid, out + "\n\nRead it carefully and fix anything wrong before you send it. Tell me what to change.\n\nAfter you send it, save it: /track add " + name + " | " + founder)
            elif doc:
                if doc.get("mime_type") == "application/pdf":
                    send(cid, "Reading your CV, please wait...")
                    pdf = base64.b64encode(tg_file(doc["file_id"])).decode()
                    out = gemini(
                        [{"inline_data": {"mime_type": "application/pdf",
                                          "data": pdf}},
                         {"text": EXTRACT}], BASE)
                    profiles[cid] = out
                    save(profiles, DB)
                    send(cid, out + "\n\nIf anything is wrong, tell me what to fix.")
                else:
                    send(cid, "Please send your CV as a PDF file.")
            elif text:
                send(cid, gemini([{"text": text}], system_for(cid)))
    except Exception as e:
        print("error:", e)
        time.sleep(3)
