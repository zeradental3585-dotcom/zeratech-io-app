#!/usr/bin/env python3
"""
Zera Technologies — Lead Preview Generator
==========================================
Turns a lead's Google Business Profile details into a personalised,
clearly-labelled preview website:  previews/<slug>.html

Usage
  python3 tools/preview/make_preview.py lead.json          # build one preview
  python3 tools/preview/make_preview.py --list-expired     # previews older than 30 days

Output (printed): the preview URL, a Hindi + English WhatsApp message to send the
lead, and one tab-separated row to paste into the lead sheet.

Lead JSON (only "niche" and "name" are required; everything else improves the preview):
{
  "niche": "coaching | dental | clinic | school | ca | law | shop | realestate | generic",
  "name": "Sharma Classes",
  "name_hi": "शर्मा क्लासेस",            # optional Hindi name for the logo line
  "category": "Coaching center",          # GBP category, shown under the name
  "area": "Boring Road", "city": "Patna",
  "address": "2nd floor, ... Patna 800001",
  "phone": "+91 98xxxxxxxx",              # public number from the GBP
  "whatsapp": "+91 98xxxxxxxx",           # optional; defaults to phone if it is a mobile
  "hours": [["Mon–Sat", "7 AM – 8 PM"], ["Sunday", "Closed"]],
  "rating": 4.7, "reviews": 128,          # only as shown on their GBP
  "since": "2012",                        # only if the GBP / owner says so
  "about": "From the GBP description",
  "maps_url": "https://maps.app.goo.gl/...",
  "services": [{"name": "NEET", "desc": "…", "tag": "Class 11–12"}],   # optional
  "lang": "hi-en | en",
  "owner_first_name": "Rakesh"            # optional, for the WhatsApp message
}

Rules baked in (do not remove):
  * A permanent top bar says this is a free preview by Zera Technologies, not the
    business's official website. Footer repeats it. Page is noindex,nofollow.
  * No photos copied from Google; no review texts copied; rating/count only if given.
  * Unknown facts are shown as obvious placeholders ("DD/MM", "Your fees here").
  * After 30 days the bar switches to "This preview has expired".
"""
import html, json, re, sys, datetime, pathlib, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "previews"
SITE = "https://zeratech.io"
ZERA_WA = "918893585348"
GA_ID = "G-YWPLDN029K"
EXPIRY_DAYS = 30

# --------------------------------------------------------------------------
# Niche packs: colours, copy, default services and the "special" table.
# --------------------------------------------------------------------------
PACKS = {
  "coaching": dict(
    label="coaching institute", brand="#7a1f2b", brand2="#b33a3a", soft="#fff3e6", bg="#fffaf3",
    hero_hi="सही मार्गदर्शन, बेहतर रिजल्ट।", hero_en="Coaching for Board, NEET, JEE & competitive exams",
    hero_p="Experienced faculty, small batches and regular tests. Message us on WhatsApp to know fees and batch timings.",
    pill="📢 नया बैच शुरू · New batch starting soon",
    services_title="हमारे कोर्स · Our Courses", cta_item="WhatsApp for fees →",
    services=[("Board Foundation","Class 9–10","Maths, Science and English with weekly tests and doubt classes."),
              ("NEET Preparation","Class 11–12","Physics, Chemistry, Biology with full-syllabus mock tests."),
              ("JEE Main","Class 11–12","Concept classes, practice sheets and test analysis."),
              ("SSC / Banking","Graduates","Quant, reasoning, English and GK for competitive exams."),
              ("Spoken English","All ages","Speaking practice, interview preparation and confidence."),
              ("Computer Basics","Short course","MS Office, typing and internet skills.")],
    table_title="बैच टाइमिंग · Batch Timings", table_note="You update this from a Google Sheet — no coding.",
    table=[["Course","Batch","Days","Starts"],["Board Foundation","7:00 – 8:30 AM","Mon–Sat","DD/MM"],
           ["NEET","4:00 – 6:00 PM","Mon–Sat","DD/MM"],["JEE Main","6:00 – 8:00 PM","Mon–Sat","DD/MM"]],
    proof_title="रिजल्ट · Our Toppers", proof_note="Your real toppers, photos and ranks go here — the strongest proof for new students.",
    proof_items=["Student name · Score / rank","Student name · Score / rank","Student name · Score / rank"],
    why=["Small batches, personal attention","Weekly tests with analysis","Study material and doubt classes","Regular parent updates"],
    landing="/website-for-coaching-institute.html", price="₹9,999", care="₹999",
    monogram="आ"),
  "dental": dict(
    label="dental clinic", brand="#0b6e7a", brand2="#1597a3", soft="#e9f6f7", bg="#f7fcfc",
    hero_hi="मुस्कान की देखभाल, भरोसे के साथ।", hero_en="Gentle, modern dental care",
    hero_p="Painless treatments, sterilised instruments and clear pricing. Book your visit on WhatsApp or call the clinic.",
    pill="🦷 Appointments open today",
    services_title="Treatments · इलाज", cta_item="Book on WhatsApp →",
    services=[("Root Canal Treatment","Save your tooth","Single-sitting RCT where suitable, with digital X-ray."),
              ("Dental Implants","Missing teeth","Fixed replacement for one or more missing teeth."),
              ("Braces & Aligners","Straight teeth","Metal, ceramic and clear aligner options."),
              ("Cleaning & Polishing","Every 6 months","Scaling, polishing and gum care."),
              ("Tooth-coloured Fillings","Cavities","Natural-looking composite fillings."),
              ("Kids Dentistry","Children","Gentle care, fluoride and sealants for kids.")],
    table_title="Clinic hours & fees", table_note="Show starting prices so patients don't hesitate to call.",
    table=[["Treatment","Starting from"],["Consultation","₹ —"],["Cleaning","₹ —"],["Root canal","₹ —"],["Implant","₹ —"]],
    proof_title="Before & after", proof_note="Your own before/after photos (with patient consent) go here.",
    proof_items=["Smile makeover","Braces result","Implant result"],
    why=["Sterilisation you can see","Digital X-ray","Clear prices before treatment","Evening & Sunday slots"],
    landing="/website-for-doctors-clinics.html", price="₹14,999", care="₹1,999", zeradental=True,
    monogram="🦷"),
  "clinic": dict(
    label="clinic", brand="#1d4e89", brand2="#2f6fb5", soft="#eef4fb", bg="#f8fbff",
    hero_hi="आपकी सेहत, हमारी ज़िम्मेदारी।", hero_en="Trusted care for your family",
    hero_p="OPD consultation, health check-ups and lab tests under one roof. Message on WhatsApp for an appointment.",
    pill="🩺 OPD open today",
    services_title="Services · सेवाएं", cta_item="Book on WhatsApp →",
    services=[("OPD Consultation","Daily","General consultation for adults and children."),
              ("Health Check-up","Packages","Full body and senior-citizen check-up packages."),
              ("Lab Tests","Reports on WhatsApp","Blood, sugar, thyroid and more."),
              ("Diabetes & BP Care","Follow-up","Regular monitoring and medicine review."),
              ("Vaccination","Kids & adults","As per schedule, with reminders."),
              ("Home Sample Collection","Nearby areas","Sample pickup from home.")],
    table_title="Doctor schedule", table_note="Patients check timings before visiting — put them on Google and your site.",
    table=[["Doctor","Speciality","Timing"],["Dr. Name","General Physician","10 AM – 2 PM"],["Dr. Name","Paediatrics","5 PM – 8 PM"]],
    proof_title="Facilities", proof_note="Real photos of your reception, OPD and lab go here.",
    proof_items=["Reception","Consultation room","Lab"],
    why=["Experienced doctors","Clean, comfortable clinic","Reports on WhatsApp","Ample parking / easy to find"],
    landing="/website-for-doctors-clinics.html", price="₹9,999", care="₹999",
    monogram="+"),
  "school": dict(
    label="school", brand="#17456b", brand2="#2a6a9c", soft="#eef5ea", bg="#fbfcf8",
    hero_hi="संस्कार और शिक्षा, एक साथ।", hero_en="Quality education with values",
    hero_p="Qualified teachers, safe campus and activities beyond books. Admissions are open — ask on WhatsApp.",
    pill="🎓 Admissions open 2027–28",
    services_title="Classes & facilities", cta_item="Ask about admission →",
    services=[("Pre-primary","Nursery – UKG","Play-based learning in a caring environment."),
              ("Primary","Class 1 – 5","Strong basics in reading, maths and English."),
              ("Middle School","Class 6 – 8","Science labs, computers and activities."),
              ("Secondary","Class 9 – 10","Board preparation with regular tests."),
              ("Transport","Safe routes","School bus with trained staff."),
              ("Sports & Activities","Every week","Games, art, music and annual events.")],
    table_title="Admission schedule", table_note="Parents look for dates and documents — answer it before they call.",
    table=[["Step","Date"],["Forms available","DD/MM"],["Interaction / test","DD/MM"],["Results","DD/MM"],["Session starts","DD/MM"]],
    proof_title="Notice board", proof_note="Holidays, PTMs and results — updated from a Google Sheet.",
    proof_items=["DD/MM · Admission forms available","DD/MM · Parent–teacher meeting","DD/MM · Annual function"],
    why=["Qualified, caring teachers","Safe, CCTV-monitored campus","Smart classes","Regular parent updates"],
    landing="/school-website-design.html", price="₹9,999", care="₹999",
    monogram="✦"),
  "ca": dict(
    label="CA / tax firm", brand="#1b2a44", brand2="#2c4470", soft="#f3f1ea", bg="#fbfaf6",
    hero_hi="GST, ITR और अकाउंट्स — सही समय पर।", hero_en="GST, income tax & accounting, done on time",
    hero_p="Registration, returns and compliance for businesses and individuals. Send your query on WhatsApp.",
    pill="📅 ITR & GST filing open",
    services_title="Services · सेवाएं", cta_item="Ask on WhatsApp →",
    services=[("GST Registration","New business","Registration, amendments and LUT."),
              ("GST Returns","Monthly / quarterly","GSTR-1, GSTR-3B and annual return."),
              ("Income Tax Return","Individuals & firms","Salaried, business and capital gains."),
              ("Company / LLP Registration","Start-ups","Incorporation and ROC compliance."),
              ("Accounting & Bookkeeping","Monthly","Tally / cloud books, MIS reports."),
              ("TDS & Audit","Compliance","TDS returns, tax and statutory audit.")],
    table_title="Documents for ITR", table_note="A checklist page like this saves you 20 phone calls a week.",
    table=[["Document","Needed for"],["PAN & Aadhaar","Everyone"],["Form 16 / salary slips","Salaried"],["Bank statements","Everyone"],["Purchase & sales records","Business"]],
    proof_title="Due-date calendar", proof_note="Upcoming tax deadlines — you update them from a Google Sheet.",
    proof_items=["DD/MM · GSTR-3B","DD/MM · TDS return","DD/MM · Advance tax"],
    why=["Qualified professionals","Deadlines tracked for you","Clear, fixed fees","Documents over WhatsApp"],
    landing="/website-for-ca-and-law-firms.html", price="₹9,999", care="₹999",
    monogram="₹"),
  "law": dict(
    label="law office", brand="#2b2d42", brand2="#44476a", soft="#f2f2f5", bg="#fbfbfc",
    hero_hi="", hero_en="Legal advice and representation",
    hero_p="Practice areas, chamber timings and how to reach the office.",
    pill="⚖️ Chamber hours",
    services_title="Areas of practice", cta_item="Contact the office →",
    services=[("Civil matters","Practice area","Property, recovery and civil suits."),
              ("Criminal matters","Practice area","Bail, trial and appeals."),
              ("Family matters","Practice area","Divorce, maintenance and custody."),
              ("Property documentation","Practice area","Sale deeds, agreements and verification."),
              ("Consumer matters","Practice area","Consumer commission cases."),
              ("Legal notices & drafting","Practice area","Notices, agreements and affidavits.")],
    table_title="Chamber details", table_note="Factual information only, as Bar Council rules allow.",
    table=[["Detail",""],["Enrolment no.","Your Bar Council enrolment"],["Courts","Courts you practise in"],["Languages","Hindi, English"]],
    proof_title="Office", proof_note="Photos of the chamber and directions go here.",
    proof_items=["Chamber","Reception","Directions"],
    why=["Clear practice areas","Chamber timings","Easy directions","Languages spoken"],
    landing="/website-for-ca-and-law-firms.html", price="₹9,999", care="₹999", law=True,
    monogram="§"),
  "shop": dict(
    label="shop", brand="#a2470f", brand2="#d0661b", soft="#fff4ea", bg="#fffbf7",
    hero_hi="अच्छा सामान, सही दाम।", hero_en="Quality products at fair prices",
    hero_p="Visit the store or order on WhatsApp. Home delivery available in nearby areas.",
    pill="🛍️ Open today",
    services_title="What we sell", cta_item="Order on WhatsApp →",
    services=[("Category 1","Popular","Your best-selling products, with prices."),
              ("Category 2","New stock","Latest arrivals every week."),
              ("Category 3","Offers","Festival and combo offers."),
              ("Category 4","Brands","Top brands you stock."),
              ("Home Delivery","Nearby areas","Order on WhatsApp, pay on delivery / UPI."),
              ("Bulk Orders","Shops & events","Special rates for bulk buyers.")],
    table_title="Delivery & payment", table_note="Answer the top questions before they ask.",
    table=[["Question","Answer"],["Home delivery","Areas covered"],["Payment","UPI / cash / card"],["Min. order","₹ —"]],
    proof_title="Offers this week", proof_note="Update offers from a Google Sheet in seconds.",
    proof_items=["Offer 1","Offer 2","Offer 3"],
    why=["Genuine products","Fair prices","Home delivery","UPI accepted"],
    landing="/services.html", price="₹9,999", care="₹999",
    monogram="◆"),
  "realestate": dict(
    label="real-estate business", brand="#1f4d3a", brand2="#2f7357", soft="#eef6f1", bg="#fafcfa",
    hero_hi="सही ज़मीन, सही दाम, साफ़ कागज़।", hero_en="Plots, flats and land with clear paperwork",
    hero_p="Verified properties, site visits and documentation help. Ask for current listings on WhatsApp.",
    pill="🏡 New listings this week",
    services_title="What we offer", cta_item="Ask for details →",
    services=[("Residential Plots","Buy","Plots in growing localities with clear titles."),
              ("Flats & Houses","Buy / rent","Ready and under-construction options."),
              ("Agricultural Land","Buy / sell","Land with records checked."),
              ("Commercial Space","Shops / offices","Spaces on main roads."),
              ("Site Visits","Free","We take you to the property."),
              ("Documentation Help","Registry","Help with registry and mutation process.")],
    table_title="Featured listings", table_note="Listings come from a Google Sheet — add a row, it appears here.",
    table=[["Property","Location","Size","Price"],["Plot","Locality","— sq ft","₹ —"],["2 BHK flat","Locality","— sq ft","₹ —"],["Shop","Locality","— sq ft","₹ —"]],
    proof_title="Registration", proof_note="RERA registration number (where applicable) shown here builds trust.",
    proof_items=["RERA Reg. No. —","Years in business —","Areas served —"],
    why=["Clear titles","Free site visits","Documentation support","Local market knowledge"],
    landing="/services.html", price="₹9,999", care="₹999",
    monogram="⌂"),
  "generic": dict(
    label="business", brand="#1B2A44", brand2="#0E928C", soft="#eef6f6", bg="#fafcfc",
    hero_hi="", hero_en="Trusted service, close to you",
    hero_p="Call or message us on WhatsApp — we reply quickly.",
    pill="✅ Open today",
    services_title="Our services", cta_item="Ask on WhatsApp →",
    services=[("Service 1","Popular","What you do best, in one line."),
              ("Service 2","","Second service."),("Service 3","","Third service."),
              ("Service 4","","Fourth service.")],
    table_title="Prices", table_note="Showing starting prices brings more serious enquiries.",
    table=[["Service","Starting from"],["Service 1","₹ —"],["Service 2","₹ —"]],
    proof_title="Gallery", proof_note="Real photos of your work go here.",
    proof_items=["Photo","Photo","Photo"],
    why=["Experienced team","Fair prices","Quick response","Easy to reach"],
    landing="/services.html", price="₹9,999", care="₹999",
    monogram="★"),
}

E = lambda s: html.escape(str(s), quote=True)

def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:60] or "lead"

def digits(phone):
    d = re.sub(r"\D", "", phone or "")
    if len(d) == 10: d = "91" + d
    if d.startswith("0") and len(d) == 11: d = "91" + d[1:]
    return d

def is_mobile(d):
    return len(d) == 12 and d.startswith("91") and d[2] in "6789"

def build(lead):
    niche = lead.get("niche", "generic")
    if niche not in PACKS: sys.exit(f"Unknown niche '{niche}'. Use one of: {', '.join(PACKS)}")
    p = PACKS[niche]
    name = lead["name"].strip()
    city = lead.get("city", "").strip()
    area = lead.get("area", "").strip()
    place = ", ".join(x for x in [area, city] if x)
    slug = lead.get("slug") or slugify(f"{name}-{city}")
    url = f"{SITE}/previews/{slug}.html"
    today = datetime.date.today()
    made = lead.get("made_on") or today.isoformat()
    expires = (datetime.date.fromisoformat(made) + datetime.timedelta(days=EXPIRY_DAYS)).isoformat()
    phone = lead.get("phone", "").strip()
    pd = digits(phone)
    looks_landline = re.sub(r"[^\d+]", "", phone).startswith("0")  # 0612… = STD landline
    wd = digits(lead.get("whatsapp") or (phone if is_mobile(pd) and not looks_landline else ""))
    hi = lead.get("lang", "hi-en") != "en"

    def biz_wa(text):
        if not wd: return f"tel:+{pd}" if pd else "#contact"
        return f"https://wa.me/{wd}?text=" + urllib.parse.quote(text)
    def zera_wa(text):
        return f"https://wa.me/{ZERA_WA}?text=" + urllib.parse.quote(text)

    zera_msg = (f"Namaste Zera Technologies, I saw the free website preview for {name}"
                f"{' (' + city + ')' if city else ''}: {url}\nI would like to discuss it.")
    biz_msg = f"Namaste, I found {name} on your website. I want to know more."

    services = lead.get("services") or [dict(name=a, tag=b, desc=c) for a, b, c in p["services"]]
    cta_lbl = "WhatsApp करें" if hi else "WhatsApp us"
    if not wd: cta_lbl = "Call now" if pd else "Contact"

    # ---- sections ------------------------------------------------------
    svc_html = "".join(
        f'<article class="card">{f"<span class=tag>{E(s.get("tag",""))}</span>" if s.get("tag") else ""}'
        f'<h3>{E(s["name"])}</h3><p>{E(s.get("desc",""))}</p>'
        f'<a class="wa" href="{E(biz_wa(f"Namaste, I want to know about {s["name"]} at {name}."))}" data-ev="biz_contact">{E(p["cta_item"] if wd else "Call for details →")}</a></article>'
        for s in services)

    tbl = p["table"]
    table_html = "<tr>" + "".join(f"<th>{E(c)}</th>" for c in tbl[0]) + "</tr>" + "".join(
        "<tr>" + "".join(f"<td>{E(c)}</td>" for c in row) + "</tr>" for row in tbl[1:])

    hours = lead.get("hours") or []
    if isinstance(hours, dict): hours = list(hours.items())
    hours_html = ("<table class=hrs>" + "".join(f"<tr><td>{E(d)}</td><td>{E(t)}</td></tr>" for d, t in hours) + "</table>"
                  if hours else '<p class="ph">Opening hours from your Google profile appear here.</p>')

    rating = lead.get("rating"); reviews = lead.get("reviews")
    rating_html = ""
    if rating:
        rating_html = (f'<div class="gr"><strong>★ {E(rating)}</strong> on Google'
                       f'{f" · {E(reviews)} reviews" if reviews else ""}</div>')

    stats = []
    if lead.get("since"): stats.append((f'{E(lead["since"])}', "Serving since"))
    if rating: stats.append((f"★ {E(rating)}", "Google rating"))
    if reviews: stats.append((E(reviews), "Google reviews"))
    if place: stats.append((E(area or city), "Location"))
    stats_html = ('<div class="stats">' + "".join(f"<div><strong>{a}</strong><span>{b}</span></div>" for a, b in stats[:3]) + "</div>") if stats else ""

    proof_html = "".join(f'<div class="card mini"><div class="ph-img">Photo</div><div>{E(x)}</div></div>' for x in p["proof_items"])
    why_html = "".join(f"<li>{E(x)}</li>" for x in p["why"])

    q = urllib.parse.quote(f"{name} {lead.get('address') or place}")
    map_html = (f'<iframe title="Map to {E(name)}" loading="lazy" referrerpolicy="no-referrer-when-downgrade" '
                f'src="https://www.google.com/maps?q={q}&output=embed"></iframe>')
    directions = lead.get("maps_url") or f"https://www.google.com/maps/search/?api=1&query={q}"

    about = lead.get("about") or (f"{name} is a trusted {p['label']} in {place}." if place else f"{name} — a trusted local {p['label']}.")
    hero_h = (f"{E(p['hero_hi'])}<br>" if hi and p["hero_hi"] else "") + E(p["hero_en"])
    if city: hero_h += f" in {E(city)}"
    sub_line = E(lead.get("name_hi") or lead.get("category") or p["label"].title()) + (f" · {E(place)}" if place else "")
    initial = E(name[0].upper())

    law_note = '<p class="ph">Kept factual (no claims, ratings or testimonials) to respect Bar Council of India rules on advocates\' websites.</p>' if p.get("law") else ""
    if p.get("law"): rating_html = ""; stats_html = ""  # no ratings on advocate sites

    if p.get("zeradental"):
        pitch_price = (f'Dental clinic websites from <strong>{p["price"]} + GST</strong> · '
                       f'Zera Care {p["care"]}/month (hosting, edits, Google posts). '
                       f'<a href="https://zeradental.in/pricing" style="color:#ffd56b">See packages</a>')
    else:
        pitch_price = (f'Websites from <strong>{p["price"]} + GST</strong> (domain + 1 year hosting included) · '
                       f'Care plan {p["care"]}/month · first month of Care free.')

    data_blob = json.dumps({**lead, "slug": slug, "made_on": made}, ensure_ascii=False).replace("</", "<\\/")

    page = f"""<!doctype html>
<html lang="{'hi-IN' if hi else 'en-IN'}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(name)} — Free Website Preview | Zera Technologies</title>
<meta name="description" content="A free website preview made by Zera Technologies for {E(name)}{', ' + E(city) if city else ''}. Not the official website.">
<meta name="robots" content="noindex,nofollow">
<meta name="preview-expires" content="{expires}">
<meta property="og:title" content="Website preview for {E(name)}">
<meta property="og:description" content="See how {E(name)}'s website could look — made free by Zera Technologies.">
<meta property="og:image" content="{SITE}/og-image.png">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="{p['brand']}">
<style>
:root{{--ink:#1d1d1f;--muted:#646770;--line:#e4e2dc;--bg:{p['bg']};--card:#fff;--brand:{p['brand']};--brand2:{p['brand2']};--soft:{p['soft']};--wa:#1fae5b;--font:system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans Devanagari","Noto Sans",Arial,sans-serif}}
*{{box-sizing:border-box}}body{{margin:0;font-family:var(--font);color:var(--ink);background:var(--bg);font-size:16.5px;line-height:1.6}}
a{{color:var(--brand)}}.wrap{{max-width:1040px;margin:0 auto;padding:0 16px}}
.demo-bar{{background:#111;color:#fff;font-size:.86rem;padding:9px 0;text-align:center;line-height:1.45}}
.demo-bar a{{color:#ffd56b;font-weight:700}}
header{{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:20}}
header .wrap{{display:flex;align-items:center;justify-content:space-between;min-height:62px;gap:10px}}
.brand{{display:flex;align-items:center;gap:10px;font-weight:800;color:var(--brand);text-decoration:none;line-height:1.15;min-width:0}}
.brand b{{flex:0 0 40px;width:40px;height:40px;border-radius:11px;background:var(--brand);color:#fff;display:grid;place-items:center;font-size:1.15rem}}
.brand span{{overflow:hidden;text-overflow:ellipsis}}
.brand small{{display:block;color:var(--muted);font-weight:600;font-size:.72rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.call{{background:var(--brand);color:#fff;text-decoration:none;font-weight:700;padding:9px 14px;border-radius:10px;font-size:.92rem;white-space:nowrap}}
.hero{{background:linear-gradient(160deg,var(--brand) 0%,var(--brand2) 100%);color:#fff;padding:38px 0 44px}}
.hero h1{{font-size:clamp(1.7rem,6vw,2.7rem);line-height:1.22;margin:.25em 0 .4em}}
.hero p{{color:rgba(255,255,255,.88);font-size:1.06rem;max-width:640px}}
.pill{{display:inline-block;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);padding:5px 12px;border-radius:99px;font-size:.85rem;font-weight:700}}
.gr{{display:inline-block;margin-top:6px;background:#fff;color:#1d1d1f;border-radius:99px;padding:5px 12px;font-size:.88rem}}.gr strong{{color:#b7791f}}
.btns{{display:flex;flex-wrap:wrap;gap:10px;margin-top:20px}}
.btn{{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:12px 20px;border-radius:12px;font-weight:800;text-decoration:none}}
.btn-wa{{background:var(--wa);color:#fff}}.btn-light{{background:#fff;color:var(--brand)}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:26px;max-width:560px}}
.stats div{{background:rgba(255,255,255,.13);border-radius:12px;padding:12px 6px;text-align:center}}
.stats strong{{display:block;font-size:1.2rem}}.stats span{{font-size:.78rem;color:rgba(255,255,255,.85)}}
section{{padding:42px 0}}h2{{font-size:clamp(1.4rem,4.5vw,2rem);margin:0 0 .3em;line-height:1.25}}
.sub{{color:var(--muted);margin:0 0 20px}}.grid{{display:grid;gap:14px}}
@media(min-width:640px){{.g2{{grid-template-columns:1fr 1fr}}.g3{{grid-template-columns:1fr 1fr}}}}
@media(min-width:900px){{.g3{{grid-template-columns:repeat(3,1fr)}}}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px}}
.card h3{{margin:0 0 6px;font-size:1.1rem}}.card p{{margin:0}}
.tag{{display:inline-block;background:var(--soft);color:var(--brand);font-size:.74rem;font-weight:800;padding:3px 9px;border-radius:99px;margin-bottom:8px}}
.card .wa{{display:inline-block;margin-top:10px;font-weight:800;color:var(--wa);text-decoration:none}}
.tbl{{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:#fff}}
table{{width:100%;border-collapse:collapse;font-size:.95rem}}th,td{{padding:11px 12px;border-bottom:1px solid var(--line);text-align:left}}
th{{background:var(--soft)}}.hrs td{{padding:7px 0;border-bottom:1px dashed var(--line)}}.hrs td:last-child{{text-align:right;font-weight:700}}
.soft{{background:var(--soft)}}.ph{{font-size:.82rem;color:var(--muted)}}
.mini{{padding:10px;text-align:center;font-size:.85rem;font-weight:700}}
.ph-img{{height:90px;border-radius:10px;margin-bottom:8px;background:repeating-linear-gradient(45deg,var(--soft),var(--soft) 10px,#fff 10px,#fff 20px);display:grid;place-items:center;color:var(--muted);font-size:.78rem}}
.proof{{grid-template-columns:repeat(3,1fr)}}
.why{{padding-left:1.15em;margin:0}}.why li{{margin:.3em 0}}
iframe{{width:100%;height:260px;border:0;border-radius:14px;background:var(--soft)}}
.pitch{{background:#111;color:#eee;padding:36px 0}}.pitch h2{{color:#fff}}.pitch p,.pitch li{{color:#d6d6d6}}
footer{{background:#1a1a1a;color:#cfcfcf;padding:22px 0 92px;font-size:.86rem}}footer a{{color:#ffd56b}}
.wa-float{{position:fixed;right:16px;bottom:16px;background:var(--wa);color:#fff;border-radius:99px;padding:13px 18px;font-weight:800;text-decoration:none;box-shadow:0 8px 24px rgba(31,174,91,.4);z-index:30}}
</style>
</head>
<body>
<div class="demo-bar" id="demo-bar"><div class="wrap">🔍 <strong>Free website preview</strong> made by Zera Technologies for {E(name)} — not the official website. Details are from the public Google profile; sections marked “—” or “DD/MM” are placeholders.
 <a href="{E(zera_wa(zera_msg))}" data-ev="zera_whatsapp" data-loc="bar">Make it live →</a></div></div>

<header><div class="wrap">
  <a class="brand" href="#top"><b>{initial}</b><span>{E(name)}<small>{sub_line}</small></span></a>
  <a class="call" href="{E(biz_wa(biz_msg))}" data-ev="biz_contact">{E(cta_lbl)}</a>
</div></header>

<main id="top">
<section class="hero"><div class="wrap">
  <span class="pill">{E(p['pill'])}</span>
  <h1>{hero_h}</h1>
  <p>{E(p['hero_p'])}</p>
  {rating_html}
  <div class="btns">
    <a class="btn btn-wa" href="{E(biz_wa(biz_msg))}" data-ev="biz_contact">💬 {E(cta_lbl)}</a>
    {f'<a class="btn btn-light" href="tel:+{pd}" data-ev="biz_call">📞 {E(phone)}</a>' if pd else '<a class="btn btn-light" href="#services">Explore</a>'}
  </div>
  {stats_html}
</div></section>

<section id="services"><div class="wrap">
  <h2>{E(p['services_title'])}</h2>
  <p class="sub">Each service gets its own section, so people searching Google for it can find {E(name)}.</p>
  <div class="grid g3">{svc_html}</div>
</div></section>

<section class="soft"><div class="wrap">
  <h2>{E(p['table_title'])}</h2><p class="sub">{E(p['table_note'])}</p>
  <div class="tbl"><table>{table_html}</table></div>
  {law_note}
</div></section>

<section><div class="wrap grid g2">
  <div><h2>About {E(name)}</h2><p>{E(about)}</p><ul class="why">{why_html}</ul></div>
  <div><h2>{E(p['proof_title'])}</h2><p class="sub">{E(p['proof_note'])}</p><div class="grid proof">{proof_html}</div></div>
</div></section>

<section class="soft" id="contact"><div class="wrap grid g2" style="align-items:start">
  <div>
    <h2>{'हमसे मिलें · Visit us' if hi else 'Visit us'}</h2>
    <p>{E(lead.get('address') or place or 'Your full address and landmark go here.')}</p>
    {hours_html}
    <div class="btns">
      <a class="btn btn-wa" href="{E(biz_wa(biz_msg))}" data-ev="biz_contact">💬 {E(cta_lbl)}</a>
      <a class="btn btn-light" href="{E(directions)}" target="_blank" rel="noopener" data-ev="biz_directions">📍 Directions</a>
    </div>
  </div>
  <div>{map_html}</div>
</div></section>

<section class="pitch"><div class="wrap">
  <h2>{'यह वेबसाइट ' + E(name) + ' की हो सकती है' if hi else 'This could be ' + E(name) + "'s website"}</h2>
  <p>We made this preview free from your public Google profile. The real website gets your photos, prices and content — in Hindi, English or both.</p>
  <ul>
    <li>Opens fast on every phone, even on slow data</li>
    <li>WhatsApp and call buttons on every section — enquiries come straight to you</li>
    <li>Connected to Google and Google Maps so local customers find you</li>
    <li>Timings, notices and prices you can update yourself from a Google Sheet</li>
  </ul>
  <p>{pitch_price}</p>
  <div class="btns">
    <a class="btn btn-wa" href="{E(zera_wa(zera_msg))}" data-ev="zera_whatsapp" data-loc="pitch">Make it live — WhatsApp Zera</a>
    <a class="btn btn-light" href="{SITE}{p['landing']}" data-ev="zera_learn">Learn more</a>
  </div>
</div></section>
</main>

<footer><div class="wrap">Free preview for demonstration only — not the official website of {E(name)}, and not endorsed by it. Business name, address, hours and rating are taken from its public Google Business Profile. Designed and developed by <a href="{SITE}/" target="_blank" rel="noopener">Zera Technologies</a> · <a href="{E(zera_wa(zera_msg))}" data-ev="zera_whatsapp" data-loc="footer">WhatsApp +91 88935 85348</a> · hello@zeratech.io</div></footer>
<a class="wa-float" href="{E(biz_wa(biz_msg))}" data-ev="biz_contact">💬 {E('WhatsApp' if wd else cta_lbl)}</a>

<script type="application/json" id="lead-data">{data_blob}</script>
<script>
(function(){{
  var slug={json.dumps(slug)}, exp={json.dumps(expires)};
  window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}
  var s=document.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtag/js?id={GA_ID}';document.head.appendChild(s);
  gtag('js',new Date());gtag('config','{GA_ID}');
  gtag('event','preview_view',{{preview_slug:slug,niche:{json.dumps(niche)}}});
  document.addEventListener('click',function(e){{var a=e.target.closest('a[data-ev]');if(!a)return;
    gtag('event','preview_'+a.getAttribute('data-ev'),{{preview_slug:slug,link_location:a.getAttribute('data-loc')||''}});}});
  if(new Date().toISOString().slice(0,10)>exp){{var b=document.getElementById('demo-bar');
    b.querySelector('.wrap').innerHTML='⏳ This free preview has expired. <a href="https://wa.me/{ZERA_WA}">WhatsApp Zera Technologies</a> to see it again.';}}
}})();
</script>
</body>
</html>
"""
    return slug, url, page

def lead_message(lead, url):
    p = PACKS[lead.get("niche", "generic")]
    who = lead.get("owner_first_name")
    hi_greet = f"Namaste {who} ji 🙏" if who else "Namaste sir 🙏"
    name = lead["name"]
    return (f"{hi_greet} Satish, Zera Technologies se.\n"
            f"Maine {name} ke liye ek free website preview banaya hai — aapke Google profile ki details se:\n"
            f"{url}\n"
            f"Phone par 1 minute mein dekh lijiye. Asli website mein aapki photos, fees/prices aur poori jaankari hogi, "
            f"WhatsApp button ke saath. Website {p['price']} + GST se shuru.\n"
            f"Kaisa laga? Koi badlav chahiye to bataiye 🙂")

def sheet_row(lead, url):
    made = lead.get("made_on") or datetime.date.today().isoformat()
    follow = (datetime.date.fromisoformat(made) + datetime.timedelta(days=3)).isoformat()
    cols = [lead["name"], lead.get("area") or lead.get("city", ""), lead.get("phone", ""),
            "Y" if lead.get("website") else "N", str(lead.get("rating", "")), made,
            "Preview sent", follow, f"Preview: {url}"]
    return "\t".join(cols)

def list_expired():
    today = datetime.date.today().isoformat()
    found = False
    for f in sorted(OUT_DIR.glob("*.html")):
        m = re.search(r'name="preview-expires" content="([\d-]+)"', f.read_text(encoding="utf-8"))
        if m and m.group(1) < today:
            print(f"EXPIRED {m.group(1)}  previews/{f.name}"); found = True
    if not found: print("No expired previews.")

def main():
    if len(sys.argv) < 2: sys.exit(__doc__)
    if sys.argv[1] == "--list-expired": return list_expired()
    lead = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    slug, url, page = build(lead)
    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / f"{slug}.html"
    out.write_text(page, encoding="utf-8")
    print(f"FILE   previews/{slug}.html\nURL    {url}\n")
    print("----- WhatsApp message to the lead -----\n" + lead_message(lead, url) + "\n")
    print("----- Lead-sheet row (paste into the sheet) -----\n" + sheet_row(lead, url))

if __name__ == "__main__":
    main()
