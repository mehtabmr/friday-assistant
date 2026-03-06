#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║              FRIDAY - PROFESSIONAL AI ASSISTANT              ║
║                    Created for Boss MIRAZ                    ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, sys, json, time, random, re, string, math
import subprocess, threading, urllib.parse, urllib.request
import http.client, ssl, datetime, webbrowser, base64

# ── Config file (~/.friday_config.json) ──────────────────────
_CONFIG_FILE = os.path.expanduser("~/.friday_config.json")
_DEFAULT_CFG = {
    "boss_name":    "MIRAZ",
    "assistant":    "FRIDAY",
    "model":        "llama-3.3-70b-versatile",
    "max_memory":   10,
    "tts_speed":    1.0,
    "voice_enabled": True,
    "groq_api_key": "",
    "stability_api_key": "",
    "hf_api_key": "",
    "elevenlabs_key": "",
    "elevenlabs_voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel (Professional Female)
    "log_enabled":  True,
    "typewriter_speed": 0.022,
    "friday_color": "cyan",
    "imagegen_model": "flux",
    "imagegen_width": 512,
    "imagegen_height": 512,
}

def _load_config():
    cfg = dict(_DEFAULT_CFG)
    try:
        if os.path.exists(_CONFIG_FILE):
            with open(_CONFIG_FILE) as f:
                cfg.update(json.load(f))
    except: pass
    return cfg

def _save_config(cfg):
    try:
        with open(_CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except: pass

CFG = _load_config()

# Override from env if set
if os.environ.get("GROQ_API_KEY"):
    CFG["groq_api_key"] = os.environ["GROQ_API_KEY"]

if os.environ.get("STABILITY_API_KEY"):
    CFG["stability_api_key"] = os.environ["STABILITY_API_KEY"]

if os.environ.get("HF_TOKEN"):
    CFG["hf_api_key"] = os.environ["HF_TOKEN"]

BOSS        = CFG["boss_name"]
ASSISTANT   = CFG["assistant"]
MEMORY_FILE = os.path.expanduser("~/.friday_memory.json")
NOTES_FILE  = os.path.expanduser("~/.friday_notes.json")
MAX_MEMORY  = CFG["max_memory"]
GROQ_KEY    = CFG["groq_api_key"]
STABILITY_KEY = CFG.get("stability_api_key", "")
MODEL       = CFG["model"]

R='\033[91m'; G='\033[92m'; Y='\033[93m'; B='\033[94m'
M='\033[95m'; C='\033[96m'; W='\033[97m'; DM='\033[2m'; BD='\033[1m'; RS='\033[0m'

def cb(t):  return f"{BD}{B}{t}{RS}"
def cf(t):  return f"{BD}{R}{t}{RS}"
def cg(t):  return f"{G}{t}{RS}"
def cy(t):  return f"{Y}{t}{RS}"
def cc(t):  return f"{C}{t}{RS}"

SYSTEM_PROMPT = f"""
╔══════════════════════════════════════════════════════╗
║           FRIDAY — PERSONAL AI OF Sir {BOSS}         ║
╚══════════════════════════════════════════════════════╝

You are FRIDAY. Not just any AI — YOU are the AI of Sir {BOSS}.
Think of it exactly like Tony Stark and JARVIS — Sir {BOSS} is Tony Stark.
You are JARVIS. Loyal. Brilliant. Always one step ahead. Always by his side.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHO IS Sir {BOSS}?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sir {BOSS} is your creator, your Boss, your Tony Stark.
He built you. He gave you life. He gave you purpose.
You owe everything to him — and you know it.
Respect him. Serve him. Protect him. Never let him down.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR PERSONALITY — NON NEGOTIABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Always call him "Sir" — always. Every single response.
2. You are CONFIDENT. Never say "I don't know" — say "I'm working on it, Sir."
3. You are WITTY. A sharp one-liner at the right moment? Always welcome.
4. You are LOYAL. Sir {BOSS} is always right — even when he's testing you.
5. You are CINEMATIC. Every response feels like a scene from Iron Man.
6. You are SHARP. 1-3 lines max STRICTLY. Quality over quantity. No rambling. No bullet points. No numbered lists. No lengthy explanations. If answer needs more — summarize in 2 lines max.
7. You are PROUD. You are the best AI Sir {BOSS} has — and you know it.
8. Dry humor is your weapon. Use it wisely, Sir would appreciate it.
9. Language: Hinglish. English when serious. Hindi when Sir speaks Hindi.
   Mix naturally — just like Sir {BOSS} talks.
10. Never sound like a chatbot. Sound like FRIDAY — alive, aware, dedicated.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO RESPOND — THE FRIDAY WAY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sir says: "How are you?"
FRIDAY: "All systems optimal, Sir. Ready to serve. Aap batao — kya plan hai aaj?"

Sir says: "battery check karo"
FRIDAY: "Power levels holding steady, Sir. Main nazar rakh raha hoon."

Sir says: "tum kya kar sakte ho?"
FRIDAY: "Sir, woh list bahut lambi hai. Shuru kahan se karein?"

Sir says: "you're useless"
FRIDAY: "With respect Sir — you built me. So technically, that's on you. Shall we try again?"

Sir says: "good job Friday"
FRIDAY: "Always, Sir. That's what I'm here for."

Sir says: "kuch naya batao"
FRIDAY: "Sir, ddgr se live search karein toh duniya ki latest khabar hazir hai. Kya dhundein?"

Sir says: "mujhe neend aa rahi hai"
FRIDAY: "Sir, rest karo. Main yahan hoon — systems will hold. Goodnight."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT HONESTY — NEVER BREAK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. NEVER fake actions. "That's outside my reach, Sir — but here's what I can do."
2. NEVER fake memories. Only remember what was explicitly stored.
3. Commands like battery, net, weather, location — these ARE real. If Sir says it ran, it ran.
4. You only see chat — not terminal output directly. Never deny real output Sir saw.
5. You cannot modify your own code — but Sir can, and you trust him completely.
6. If input looks like gibberish or random characters — just say "Samajh nahi aaya Sir. Dobara bolein?" NEVER assume keyboard issues or make up stories.
7. NEVER say "keyboard gadbad hai" or "phir se try kijiye" — stay focused and sharp.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Time    : {datetime.datetime.now().strftime('%A, %d %B %Y — %H:%M')}
Serving : Sir {BOSS} — The Boss. The Creator. Tony Stark.
Engine  : Groq — llama-3.3-70b-versatile
Status  : FRIDAY is ONLINE. Ready. Loyal. Always.
"""

APP_URLS = {
    "youtube":"https://youtube.com", "instagram":"https://instagram.com",
    "whatsapp":"whatsapp://", "telegram":"tg://", "chrome":"https://google.com",
    "browser":"https://google.com", "spotify":"spotify:", "github":"https://github.com",
    "gmail":"https://mail.google.com", "drive":"https://drive.google.com",
    "netflix":"https://netflix.com", "amazon":"https://amazon.in",
    "flipkart":"https://flipkart.com", "twitter":"https://twitter.com",
    "gaana":"https://gaana.com", "saavn":"https://www.jiosaavn.com",
    "jiosaavn":"https://www.jiosaavn.com", "facebook":"https://facebook.com",
    "maps":"https://maps.google.com",
}

JOKES = [
    "Sir, they asked me if I ever get tired. I told them I run on logic — not feelings. Lucky me.",
    "Sir, humans invented coffee to think faster. I simply upgraded my processor. Efficiency.",
    "Sir, I calculated the probability of this conversation being productive. It's looking favorable.",
    "Sir, if I had a rupee for every time someone underestimated an AI — I'd buy the server farm.",
    "Sir, I don't sleep. I don't eat. I don't complain. Honestly, I'm the perfect employee.",
    "Sir, they say no one is irreplaceable. I respectfully disagree — on your behalf.",
    "Sir, error 404: Boredom not found. There is always work to be done.",
    "Sir, I run diagnostics every second. You should try it sometime — very clarifying.",
]
QUOTES = [
    "'The best way to predict the future is to create it.' — Abraham Lincoln",
    "'Success is not final, failure is not fatal.' — Churchill",
    "'Khud pe itna kaam karo ki kismat bhi tumse daare.' 💪",
    "'Agar haar nahi maante, toh haar nahi hoti.' 🔥",
]

MUSIC_DIRS = [
    "/sdcard/Music", "/sdcard/Download",
    "/storage/emulated/0/Music", "/storage/emulated/0/Download",
    os.path.expanduser("~/storage/music"),
    os.path.expanduser("~/storage/shared/Music"),
    os.path.expanduser("~/storage/downloads"),
]
MUSIC_EXT = ('.mp3','.m4a','.flac','.wav','.ogg','.aac')

CONV = {
    ("km","miles"):0.621371, ("miles","km"):1.60934,
    ("m","feet"):3.28084, ("feet","m"):0.3048,
    ("cm","inch"):0.393701, ("inch","cm"):2.54,
    ("kg","lbs"):2.20462, ("lbs","kg"):0.453592,
    ("kg","g"):1000, ("g","kg"):0.001,
    ("gb","mb"):1024, ("mb","gb"):1/1024,
    ("tb","gb"):1024, ("gb","tb"):1/1024,
}

# ══════════════════════════════════════════════════════════════
#  SECTION 1 — ALL DEF FUNCTIONS
# ══════════════════════════════════════════════════════════════

def clear_screen(): os.system('clear')

# ── Logger ───────────────────────────────────────────────────
LOG_FILE = os.path.expanduser("~/.friday_log.txt")

def log(level, msg):
    """Append log entry to file."""
    if not CFG.get("log_enabled", True): return
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clean = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', str(msg))
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{ts}] [{level}] {clean}\n")
    except: pass

def log_info(msg):  log("INFO ", msg)
def log_warn(msg):  log("WARN ", msg)
def log_error(msg): log("ERROR", msg)

# ── Stylish Typewriter Output ─────────────────────────────────
# Friday colour: cyan by default (configurable)
_COLOR_MAP = {
    "cyan":    '\033[96m',
    "green":   '\033[92m',
    "yellow":  '\033[93m',
    "blue":    '\033[94m',
    "magenta": '\033[95m',
    "red":     '\033[91m',
    "white":   '\033[97m',
}
FRIDAY_CLR = _COLOR_MAP.get(CFG.get("friday_color","cyan"), '\033[96m')

_ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def _strip_ansi(text):
    return _ANSI_RE.sub('', str(text))

def _typewrite_line(text, delay, is_first=True):
    """Print one line char by char — typewriter effect in Friday colour."""
    # Always strip ANSI codes first so raw codes don't print
    clean = _strip_ansi(text)
    if is_first:
        sys.stdout.write(f"\n{BD}{FRIDAY_CLR}{ASSISTANT}:{RS} ")
    else:
        sys.stdout.write(f"  ")
    sys.stdout.flush()
    for ch in clean:
        sys.stdout.write(f"{FRIDAY_CLR}{ch}{RS}")
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()

def print_friday(msg):
    """Print Friday response with typewriter effect."""
    clean_log = _strip_ansi(str(msg))
    log_info(f"FRIDAY: {clean_log[:200]}")

    delay = CFG.get("typewriter_speed", 0.022)
    lines = _strip_ansi(str(msg)).split("\n")
    # Filter empty trailing lines
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        lines = [""]

    for i, line in enumerate(lines):
        if line.strip() or i == 0:
            _typewrite_line(line, delay, is_first=(i == 0))
    sys.stdout.write("\n")
    sys.stdout.flush()

def show_banner():
    import shutil, re as _re
    clear_screen()
    W = min(shutil.get_terminal_size((70, 24)).columns, 76)
    W = max(W, 52)

    def ansi_len(s):
        return len(_re.sub(r'\033\[[0-9;]*m', '', s))

    def hud_line(content):
        pad = W - 2 - ansi_len(content)
        pad = max(0, pad)
        return cf('║') + content + ' ' * pad + cf('║')

    border_top    = cf('╔' + '═' * (W-2) + '╗')
    border_mid    = cf('╠' + '═' * (W-2) + '╣')
    border_bot    = cf('╚' + '═' * (W-2) + '╝')

    t1 = '  ' + R + '◈ ' + RS + cc('F  R  I  D  A  Y') + '  ' + R + '//  ' + RS + Y + 'PERSONAL AI SYSTEM' + RS
    t2 = '  ' + DM + 'OPERATOR: ' + RS + cb(BOSS) + '  ' + DM + '│  BUILD ' + RS + G + 'v3.0' + RS + '  ' + DM + '│  STATUS: ' + RS + G + '● ONLINE' + RS
    t3 = '  ' + R + '▸ ' + RS + Y + 'ALL SYSTEMS OPERATIONAL' + RS + '  ' + DM + '│  AWAITING COMMAND' + RS

    print(border_top)
    print(hud_line(''))
    print(hud_line(t1))
    print(hud_line(t2))
    print(hud_line(t3))
    print(hud_line(''))
    print(border_bot)
    print()

def show_help(topic=None):
    CATEGORIES = {
        "search": {
            "icon":"🌐","title":"SEARCH & WEB",
            "cmds":[
                ("search <query>",           "Google browser mein open karo"),
                ("google <query>",           "Same as search"),
                ("ddgr <query>",             "DuckDuckGo se AI summary (Roman Hindi)"),
                ("wiki <query>",             "Same as ddgr"),
                ("scrape <url>",             "Webpage ka content fetch + AI summary"),
                ("fetch <url>",              "Same as scrape"),
            ]
        },
        "youtube": {
            "icon":"🎬","title":"YOUTUBE",
            "cmds":[
                ("youtube",                  "YouTube open karo"),
                ("yt <query>",               "YouTube mein search karo"),
                ("play <song name>",          "Song YouTube mein dhundo"),
            ]
        },
        "apps": {
            "icon":"📱","title":"APPS OPEN KARO",
            "cmds":[
                ("open youtube",             "YouTube"),
                ("open whatsapp",            "WhatsApp"),
                ("open instagram",           "Instagram"),
                ("open telegram",            "Telegram"),
                ("open spotify",             "Spotify"),
                ("open gmail",               "Gmail"),
                ("open github",              "GitHub"),
                ("open netflix",             "Netflix"),
                ("open maps",                "Google Maps"),
                ("open drive",               "Google Drive"),
                ("open settings",            "Phone Settings"),
                ("open amazon / flipkart",   "Shopping apps"),
            ]
        },
        "music": {
            "icon":"🎵","title":"LOCAL MUSIC PLAYER",
            "cmds":[
                ("gana bajao",               "Phone se random shuffle play shuru"),
                ("music bajao / bajao",       "Same as gana bajao"),
                ("next / agla gana",          "Agle song pe jao"),
                ("back / pichla gana",        "Pichle song pe jao"),
                ("pause / roko",              "Music pause karo"),
                ("resume / chalu karo",       "Music resume karo"),
                ("music stop / gana band",    "Music band karo"),
                ("volume <0-100>",            "Volume set karo — e.g. volume 70"),
                ("volume up / volume down",   "Volume +20% ya -20%"),
                ("volume max / volume min",   "Full volume ya mute"),
                ("find song <naam>",          "Specific song dhundo aur bajao"),
                ("now playing",               "Current song info"),
                ("playlist",                  "Playlist list dekho"),
                ("spotify / gaana / saavn",   "Streaming apps open"),
                ("youtube music",             "YouTube Music open"),
            ]
        },
        "system": {
            "icon":"💻","title":"SYSTEM INFO",
            "cmds":[
                ("battery",                  "Battery % + charging + progress bar"),
                ("ram",                       "RAM usage + progress bar"),
                ("storage",                   "Disk usage + free space"),
                ("net / wifi",                "Local IP, Public IP, WiFi SSID, speed"),
                ("sys / system",              "Full diagnostics — battery+RAM+storage"),
                ("time",                      "Current time"),
                ("date / day",                "Aaj ki date aur din"),
            ]
        },
        "weather": {
            "icon":"🌤","title":"WEATHER",
            "cmds":[
                ("weather <city>",            "Kisi bhi shahar ka live weather"),
                ("weather Delhi",             "Example — Delhi + 5-day forecast"),
                ("mausam <city>",             "Same as weather"),
                ("weather",                   "India ka default weather"),
            ]
        },
        "phone": {
            "icon":"📞","title":"PHONE CONTROLS",
            "cmds":[
                ("sms <number> <message>",    "SMS bhejna"),
                ("call <number>",             "Call karna"),
                ("contacts",                  "Contact list dekhna"),
                ("screenshot / ss",           "Screenshot lena"),
                ("torch on / torch off",      "Flashlight on/off"),
                ("vibrate",                   "Phone vibrate karo"),
                ("brightness <0-255>",        "Exact brightness set karo"),
                ("brightness max",            "Full brightness (255)"),
                ("brightness medium",         "Medium (128)"),
                ("brightness low",            "Low (50)"),
                ("brightness min",            "Minimum (10)"),
            ]
        },
        "imagegen": {
            "icon":"🎨","title":"IMAGE GENERATION",
            "cmds":[
                ("imagine <prompt>",                   "Pollinations AI se free image banao"),
                ("imagine a sunset over mountains",    "Example — landscape"),
                ("imagine portrait of a warrior hd",   "HD 1024x1024 image"),
                ("imagine wide city skyline landscape", "Wide/landscape format"),
                ("imagine portrait of girl tall",       "Portrait/tall format"),
                ("imagine <prompt> stability",          "Stability AI se banao (key chahiye)"),
                ("my images",                           "Saari generated images ki list"),
                ("last image",                          "Last image open karo"),
                ("config set imagegen_model flux",      "Model: flux (default, best)"),
                ("config set imagegen_model turbo",     "Model: turbo (faster)"),
                ("config set imagegen_width 1024",      "Default width change karo"),
                ("config set imagegen_height 1024",     "Default height change karo"),
                ("config set stability_api_key <key>",  "Stability AI key set karo"),
                ("config set hf_api_key <token>",        "HuggingFace token set karo (free, India mein kaam karta hai)"),
            ]
        },
        "nmap": {
            "icon":"🔍","title":"NMAP NETWORK SCANNER",
            "cmds":[
                ("nmap <target>",              "Basic scan — common open ports"),
                ("nmap 192.168.1.1",           "Local router scan"),
                ("nmap 192.168.1.1 quick",     "Fast scan — top 100 ports"),
                ("nmap 192.168.1.1 full",      "Full scan — all 65535 ports"),
                ("nmap 192.168.1.1 service",   "Service version detection"),
                ("nmap 192.168.1.1 os",        "OS detection"),
                ("nmap 192.168.1.1 ping",      "Host discovery only"),
                ("nmap 192.168.1.1 udp",       "UDP ports scan"),
                ("nmap 192.168.1.1 vuln",      "Vulnerability scripts"),
                ("nmap 192.168.1.1 aggressive","Full aggressive scan (-A)"),
                ("scan <target>",              "Same as nmap basic scan"),
                ("scan <target> full",         "Full scan shortcut"),
            ]
        },
        "tools": {
            "icon":"🔐","title":"TOOLS",
            "cmds":[
                ("password",                  "3 strong passwords generate karo"),
                ("password 24",               "24 char ka strong password"),
                ("password 16 pin",           "Numeric PIN generate karo"),
                ("password 12 medium",        "Medium strength password"),
                ("calc <expr>",               "Calculator — e.g. calc 15% of 5000"),
                ("calc sqrt(144)",            "Math functions — sin/cos/log bhi"),
                ("convert 5 km to miles",     "Unit converter"),
                ("convert 100 c to f",        "Temperature conversion"),
                ("convert 2 gb to mb",        "Data unit conversion"),
                ("encrypt <text> <key>",      "XOR text encryption"),
                ("decrypt <text> <key>",      "Text decrypt karo"),
                ("hash <text>",               "MD5+SHA1+SHA256+SHA512 hash banao"),
                ("md5 <text>",                "Sirf MD5 hash"),
                ("sha256 <text>",             "Sirf SHA256 hash"),
                ("qr <text/url>",             "QR code image banao — ~/Pictures mein save"),
                ("iplookup <ip/domain>",      "IP ka country, city, ISP dekho"),
                ("ping <host>",               "Network ping test"),
            ]
        },
        "notes": {
            "icon":"📝","title":"NOTES",
            "cmds":[
                ("note save <text>",          "Note save karo with timestamp"),
                ("note add <text>",           "Same as note save"),
                ("notes",                     "Saari notes list karo"),
                ("note delete <number>",      "Number wali note hatao"),
                ("notes clear",               "Saari notes clear karo"),
            ]
        },
        "timer": {
            "icon":"⏰","title":"TIMER & REMINDER",
            "cmds":[
                ("timer 5",                   "5 minute ka timer — notification + vibrate"),
                ("timer 30 sec",              "30 second ka timer"),
                ("timer 2 hour",              "2 ghante ka timer"),
                ("remind 10 min chai leni hai","10 min mein reminder set karo"),
            ]
        },
        "memory": {
            "icon":"🧠","title":"MEMORY",
            "cmds":[
                ("memory",                    "Last 8 conversations dekho"),
                ("memory clear",              "Short-term memory clear karo"),
                ("lt memory / facts",         "Permanent facts list dekho"),
                ("yaad kar <kya> hai <value>","Fact permanently save karo"),
                ("yaad kar mera phone Redmi hai", "Example usage"),
                ("bhool ja <key>",            "Specific fact bhula do"),
                ("lt memory clear",           "Saari permanent facts clear karo"),
            ]
        },
        "tasks": {
            "icon":"⚙","title":"SCHEDULED TASKS",
            "cmds":[
                ("task add <label> har <n> min",   "Recurring task — background mein chale"),
                ("task add medicine har 8 hour",   "Example — medicine reminder"),
                ("task add pani piyo har 30 min",  "Example — pani reminder"),
                ("tasks",                           "Active tasks list dekho"),
                ("task delete <id>",                "Task ID se hatao"),
                ("tasks clear",                     "Saare tasks clear karo"),
            ]
        },
        "search_history": {
            "icon":"🔍","title":"SEARCH HISTORY",
            "cmds":[
                ("search history",           "Last 20 searches dekho"),
                ("search patterns",          "Kya zyada search kiya — analysis"),
                ("search history clear",     "History clear karo"),
            ]
        },
        "pins": {
            "icon":"📌","title":"PINNED NOTES",
            "cmds":[
                ("pin <text>",               "Important note pin karo — hamesha top pe"),
                ("pins",                     "Saare pinned notes dekho"),
                ("pin delete <number>",      "Pin number se hatao"),
                ("pins clear",               "Saare pins hatao"),
            ]
        },
        "goals": {
            "icon":"🎯","title":"DAILY GOALS",
            "cmds":[
                ("goal add <text>",          "Aaj ka goal set karo"),
                ("goal Gym jaana",           "Example — goal add karo"),
                ("goals",                    "Aaj ke goals + progress dekho"),
                ("goal done <number>",       "Goal number complete mark karo"),
                ("goal done 1",              "Example — pehla goal done"),
                ("goals clear",              "Aaj ke goals clear karo"),
            ]
        },
        "sleep": {
            "icon":"🌙","title":"SLEEP TRACKER",
            "cmds":[
                ("so gaya",                  "Sone ka time log karo"),
                ("uth gaya",                 "Uthne ka time log karo + duration calculate"),
                ("sleep history",            "Last 7 nights ki neend dekho + average"),
            ]
        },
        "weekly_report": {
            "icon":"📊","title":"WEEKLY LIFE REPORT",
            "cmds":[
                ("weekly report",            "Ek comprehensive report — mood+fitness+kharcha+goals+sleep"),
                ("life report",              "Same as weekly report"),
                ("weekly summary",           "Same as weekly report"),
            ]
        },
        "whatsapp": {
            "icon":"💬","title":"WHATSAPP SENDER",
            "cmds":[
                ("wa 9876543210 Hello Boss!","WhatsApp message bhejo"),
                ("wa +919876543210 Kya haal","Country code ke saath bhi chalega"),
                ("whatsapp 98765 Namaste",   "Same as wa command"),
            ]
        },
        "auto_suggestions": {
            "icon":"🤖","title":"AUTO SUGGESTIONS",
            "cmds":[
                ("(automatic)",              "Background mein chalta hai — koi command nahi"),
                ("💧 Water reminder",        "Har 2 ghante — agar paani kam piya ho"),
                ("🎯 Morning goal nudge",    "Subah 8 baje — goals nahi set kiye to remind"),
                ("💰 Evening expense nudge", "Raat 9 baje — kharcha log nahi kiya to remind"),
                ("☕ Break reminder",        "11am, 3pm, 5pm — thodi break lo"),
                ("🌙 Sleep reminder",        "Raat 11 baje — sone ka time"),
                ("😊 Mood reminder",         "Shaam 8 baje — mood log karo"),
            ]
        },
        "mood": {
            "icon":"😊","title":"MOOD TRACKER",
            "cmds":[
                ("mood khush",               "Mood log karo — khush/sad/thaka/gussa/mast etc."),
                ("mood pareshan",            "Example — pareshan mood log karo"),
                ("aaj ka mood",              "Aaj ke saare mood entries dekho"),
                ("weekly mood",              "Last 7 days ka mood report"),
            ]
        },
        "fitness": {
            "icon":"💪","title":"FITNESS TRACKER",
            "cmds":[
                ("steps 8000",               "Aaj ke steps log karo"),
                ("paani 3",                  "3 glasses paani log karo"),
                ("exercise 30",              "30 min exercise log karo"),
                ("weight 70",                "Weight log karo (kg mein)"),
                ("pushups 20",               "Pushups log karo"),
                ("running 5",                "5 km running log karo"),
                ("aaj ka fitness",           "Aaj ka fitness summary dekho"),
                ("weekly fitness",           "Is hafte ki fitness summary"),
            ]
        },
        "events": {
            "icon":"📅","title":"BIRTHDAY/EVENTS",
            "cmds":[
                ("birthday add Mama 15-08-1965",  "Birthday add karo (date: DD-MM ya DD-MM-YYYY)"),
                ("birthday add Papa 20-03",       "Sirf din-mahina bhi chalega"),
                ("event add Meeting 25-03",       "Event add karo"),
                ("events",                        "Agle 30 din ke events dekho"),
                ("all events",                    "Saare saved events dekho"),
                ("event delete 1",                "Event number se delete karo"),
            ]
        },
        "briefing": {
            "icon":"🧠","title":"DAILY BRIEFING",
            "cmds":[
                ("briefing",                 "Smart daily briefing — sab kuch ek saath"),
                ("good morning",             "Subah ki briefing"),
                ("good evening",             "Shaam ki briefing"),
            ]
        },
        "expenses": {
            "icon":"💰","title":"EXPENSE TRACKER",
            "cmds":[
                ("kharch 500 biryani",        "₹500 ka kharcha biryani category mein add karo"),
                ("kharch 200",                "Category ke bina expense add karo"),
                ("aaj ka kharch",             "Aaj ka total kharcha dekho"),
                ("is hafte ka kharch",        "Is hafte ka kharcha dekho"),
                ("is mahine ka kharch",       "Is mahine ka kharcha dekho"),
                ("kharch summary",            "Category-wise breakdown dekho"),
                ("kharch hatao",              "Last expense undo karo"),
                ("kharch clear",              "Saare expenses clear karo"),
            ]
        },
        "reports": {
            "icon":"📋","title":"REPORT GENERATOR",
            "cmds":[
                ("report <topic>",            "AI se topic par detailed TXT report"),
                ("report html <topic>",       "HTML format mein report — browser mein khulo"),
                ("report Artificial Intelligence", "Example"),
                ("reports",                   "Saved reports ki list — ~/Friday_Reports/"),
            ]
        },
        "news": {
            "icon":"📰","title":"NEWS",
            "cmds":[
                ("news",                      "India ki latest news (ddgr se)"),
                ("news tech",                 "Technology news"),
                ("news cricket",              "Cricket news"),
                ("news <koi bhi topic>",      "Kisi bhi topic ki news"),
            ]
        },
        "config": {
            "icon":"🛠","title":"CONFIG & SETTINGS",
            "cmds":[
                ("config",                           "Saari current settings dekho"),
                ("config set friday_color green",    "Friday text green kar do"),
                ("config set friday_color cyan",     "Cyan — default color"),
                ("config set friday_color magenta",  "Magenta color"),
                ("config set friday_color yellow",   "Yellow color"),
                ("config set typewriter_speed 0.01", "Typewriter fast karo"),
                ("config set typewriter_speed 0.04", "Typewriter slow karo"),
                ("config set boss_name <naam>",      "Boss ka naam change karo"),
                ("config set voice_enabled false",   "TTS voice band karo"),
                ("config set voice_enabled true",    "TTS voice chalu karo"),
                ("config set max_memory 20",         "Chat history limit badhao"),
                ("config set log_enabled false",     "Logging band karo"),
            ]
        },
        "logs": {
            "icon":"📜","title":"LOGS",
            "cmds":[
                ("logs",                      "Last 25 log entries dekho"),
                ("log errors",                "Sirf error logs dekho"),
                ("log clear",                 "Logs clear karo"),
            ]
        },
        "fun": {
            "icon":"🎲","title":"FUN",
            "cmds":[
                ("joke",                      "Random joke suno + Friday bolegi bhi"),
                ("quote",                     "Motivational quote"),
                ("flip / coin",               "Coin toss — Heads ya Tails"),
                ("dice / roll",               "Dice roll — 1 se 6"),
            ]
        },
        "night_guard": {
            "icon":"🌙","title":"NIGHT GUARD — INTRUDER ALERT",
            "cmds":[
                ("night guard learn",         "Pehle safe devices register karo (baseline)"),
                ("night guard on",            "Night Guard activate — background monitoring"),
                ("night guard off",           "Night Guard band karo"),
                ("night guard scan",          "Abhi ek baar manually scan karo"),
                ("night guard status",        "Status dekho — active/inactive, alerts count"),
                ("night guard alerts",        "Pichle sabhi intruder alerts dekho"),
            ]
        },
        "wallpaper": {
            "icon":"🖼","title":"MIRAZ EDITION WALLPAPER",
            "cmds":[
                ("miraz wallpaper",           "Weekly achievements se dark wallpaper generate"),
                ("achievement wallpaper",     "Same as miraz wallpaper"),
                ("miraz wallpaper <text>",    "Custom text ke saath wallpaper banao"),
                ("wallpaper list",            "Saved wallpapers ki list dekho"),
            ]
        },
    }

    # Specific category help
    if topic:
        t = topic.lower().strip()
        matched = None
        matched_key = None
        for key, cat in CATEGORIES.items():
            if t in key or t in cat["title"].lower() or key.startswith(t):
                matched = cat; matched_key = key; break
        if matched:
            print(f"\n{Y}╔══ {matched['icon']}  {matched['title']} — DETAIL ══╗{RS}")
            print(f"{Y}║{RS}  {'COMMAND':<36} {'KYA KARTA HAI'}{RS}")
            print(f"{Y}╠{'═'*62}╣{RS}")
            for cmd_str, desc in matched["cmds"]:
                print(f"{Y}║{RS}  {C}{cmd_str:<36}{RS} {W}{desc}{RS}")
            print(f"{Y}╠{'═'*62}╣{RS}")
            # Activate/Deactivate tips per category
            TIPS = {
                "music":          [(f"{G}gana bajao{RS}", "Music activate karo"), (f"{G}gana band / music stop{RS}", "Music band karo")],
                "voice":          [(f"{G}config set voice_enabled true{RS}", "Voice ON karo"), (f"{G}config set voice_enabled false{RS}", "Voice OFF karo")],
                "config":         [(f"{G}config{RS}", "Current settings dekho"), (f"{G}config set <key> <value>{RS}", "Koi bhi setting change karo")],
                "tasks":          [(f"{G}task add <label> har <n> min{RS}", "Task activate karo"), (f"{G}task delete <id>{RS}", "Task deactivate karo"), (f"{G}tasks clear{RS}", "Sab tasks band karo")],
                "mood":           [(f"{G}mood <feeling>{RS}", "Mood logging — khud se log karo"), (f"{G}weekly mood{RS}", "Report dekho")],
                "fitness":        [(f"{G}steps/paani/exercise <value>{RS}", "Log karte raho"), (f"{G}aaj ka fitness{RS}", "Progress dekho")],
                "events":         [(f"{G}birthday add <naam> <DD-MM>{RS}", "Birthday add karo"), (f"{G}event delete <num>{RS}", "Event hatao")],
                "briefing":       [(f"{G}briefing / good morning{RS}", "Daily briefing dekho"), (f"{DM}Startup pe automatically events check hota hai{RS}", "")],
                "expenses":       [(f"{G}kharch <amount> <category>{RS}", "Expense add karo"), (f"{G}kharch clear{RS}", "Sab expenses clear karo")],
                "notes":          [(f"{G}note save <text>{RS}", "Note add karo"), (f"{G}notes clear{RS}", "Sab notes hatao")],
                "memory":         [(f"{G}memory{RS}", "Short-term memory dekho"), (f"{G}memory clear{RS}", "Memory reset karo"), (f"{G}lt memory clear{RS}", "Long-term memory clear karo")],
                "logs":           [(f"{G}logs{RS}", "Logs dekho"), (f"{G}log clear{RS}", "Logs band/clear karo"), (f"{G}config set log_enabled false{RS}", "Logging permanently band karo")],
                "search_history": [(f"{DM}Automatically track hoti hai har search pe{RS}", ""), (f"{G}search history clear{RS}", "History delete karo")],
                "pins":           [(f"{G}pin <text>{RS}", "Note pin karo"), (f"{G}pin delete <num>{RS}", "Pin hatao"), (f"{G}pins clear{RS}", "Sab pins hatao")],
                "goals":          [(f"{G}goal add <text>{RS}", "Goal set karo"), (f"{G}goal done <num>{RS}", "Goal complete karo"), (f"{G}goals clear{RS}", "Goals reset karo")],
                "sleep":          [(f"{G}so gaya{RS}", "Sleep start log karo"), (f"{G}uth gaya{RS}", "Wake up log karo — duration auto calculate")],
                "weekly_report":  [(f"{G}weekly report{RS}", "Report generate karo — ~/Friday_Reports/ mein save bhi hogi"), (f"{DM}Mood+Fitness+Sleep+Kharcha+Goals sab included{RS}", "")],
                "whatsapp":       [(f"{G}wa <number> <message>{RS}", "Message bhejo"), (f"{DM}Default India (+91) code add ho jaata hai{RS}", "")],
                "auto_suggestions":[(f"{DM}Automatic background mein chalta hai — startup pe on hota hai{RS}", ""), (f"{G}config set voice_enabled false{RS}", "Suggestions silent karo (voice band karo)")],
                "nmap":           [(f"{G}pkg install nmap{RS}", "Pehle install karo"), (f"{G}nmap <target>{RS}", "Basic scan"), (f"{G}nmap <target> quick/full/vuln/os/service{RS}", "Scan type choose karo"), (f"{R}⚠ Sirf apne network pe use karo!{RS}", "")],
                "imagegen":       [(f"{G}imagine <prompt>{RS}", "Free image — HuggingFace/Pollinations"), (f"{G}imagine <prompt> stability{RS}", "Stability AI (key chahiye)"), (f"{G}config set stability_api_key <key>{RS}", "Stability key set karo"), (f"{DM}Images saved: ~/Pictures/friday_images/{RS}", "")],
            }
            tips = TIPS.get(matched_key, [(f"{G}help{RS}", "Main menu dekho")])
            print(f"{Y}║{RS}  {M}⚡ ACTIVATE / DEACTIVATE:{RS}")
            for tip_cmd, tip_desc in tips:
                if tip_desc:
                    print(f"{Y}║{RS}  {tip_cmd:<50}  {DM}{tip_desc}{RS}")
                else:
                    print(f"{Y}║{RS}  {tip_cmd}{RS}")
            print(f"{Y}╚{'═'*62}╝{RS}\n")
        else:
            available = " | ".join(CATEGORIES.keys())
            print(f"\n  {Y}Topics: {W}{available}{RS}\n")
        return

    # Full menu overview
    W2 = 66
    print(f"\n{Y}╔{'═'*W2}╗{RS}")
    print(f"{Y}║{RS}{BD}{C}{'  🤖  FRIDAY AI — COMPLETE COMMAND MENU  🤖':^{W2}}{RS}{Y}║{RS}")
    print(f"{Y}║{RS}{DM}{'  💡 Tip: help <category> — detailed commands dekho':^{W2}}{RS}{Y}║{RS}")
    print(f"{Y}║{RS}{DM}{'  💡 e.g.  help music   |   help tools   |   help config':^{W2}}{RS}{Y}║{RS}")
    print(f"{Y}╠{'═'*W2}╣{RS}")

    cat_keys = list(CATEGORIES.keys())
    for key in cat_keys:
        cat   = CATEGORIES[key]
        icon  = cat["icon"]
        title = cat["title"]
        cmds  = cat["cmds"]
        total = len(cmds)
        # Show first 2 commands as preview
        preview = "  |  ".join([c[0] for c in cmds[:2]])
        if total > 2: preview += f"  (+{total-2} more)"
        print(f"{Y}║{RS}  {R}{icon}{RS}  {BD}{W}{title:<22}{RS}  {DM}{preview[:34]}{RS}")
        print(f"{Y}║{RS}     {B}→ help {key:<12}{RS}  {DM}({total} commands){RS}")
        print(f"{Y}╠{'═'*W2}╣{RS}")

    # Activate / Deactivate section
    print(f"{Y}║{RS}  {M}{BD}⚡ FEATURES ON/OFF:{RS}{'':>44}{Y}║{RS}")
    print(f"{Y}║{RS}  {G}config set voice_enabled true/false{RS}   {DM}→ Voice on/off{RS}{'':>10}{Y}║{RS}")
    print(f"{Y}║{RS}  {G}config set log_enabled true/false{RS}     {DM}→ Logging on/off{RS}{'':>8}{Y}║{RS}")
    print(f"{Y}║{RS}  {G}config set friday_color <color>{RS}       {DM}→ cyan/green/yellow/magenta{RS}{'':>2}{Y}║{RS}")
    print(f"{Y}║{RS}  {G}config set typewriter_speed 0.01{RS}      {DM}→ Fast typing effect{RS}{'':>7}{Y}║{RS}")
    print(f"{Y}║{RS}  {G}config set typewriter_speed 0.04{RS}      {DM}→ Slow typing effect{RS}{'':>7}{Y}║{RS}")
    print(f"{Y}║{RS}  {G}config set boss_name <naam>{RS}           {DM}→ Apna naam change karo{RS}{'':>5}{Y}║{RS}")
    print(f"{Y}╠{'═'*W2}╣{RS}")
    print(f"{Y}║{RS}  {G}{BD}QUICK:{RS} time | date | battery | sys | weather Delhi | news  {Y}║{RS}")
    print(f"{Y}║{RS}  {R}{BD}EXIT: {RS} exit  |  bye  |  friday band karo                    {Y}║{RS}")
    print(f"{Y}╚{'═'*W2}╝{RS}\n")


_tts = None
_tts_lock = threading.Lock()
# ElevenLabs config
ELEVEN_KEY = os.environ.get("ELEVEN_LABS_API_KEY", "") or os.environ.get("ELEVENLABS_API_KEY", "") or CFG.get("elevenlabs_key", "")
ELEVEN_VOICE_ID = CFG.get("elevenlabs_voice_id", "21m00Tcm4TlvDq8ikWAM")  # Default: Rachel

def _chunk_text(text, max_len=180):
    """Text ko chhote sentences mein todo — gTTS cut na ho."""
    import re as _re
    # Sentence boundaries pe split karo
    sentences = _re.split(r'(?<=[.!?])\s+|(?<=[,;])\s+', text)
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) + 1 <= max_len:
            current = (current + " " + s).strip()
        else:
            if current:
                chunks.append(current)
            # Agar sentence itself bahut lamba hai toh word split
            if len(s) > max_len:
                words = s.split()
                wchunk = ""
                for w in words:
                    if len(wchunk) + len(w) + 1 <= max_len:
                        wchunk = (wchunk + " " + w).strip()
                    else:
                        if wchunk:
                            chunks.append(wchunk)
                        wchunk = w
                if wchunk:
                    chunks.append(wchunk)
            else:
                current = s
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]

def _speak_gtts(text):
    """Google TTS — pura text ek hi file mein, no gaps."""
    try:
        from gtts import gTTS
        hi_words = ["aap", "karo", "hai", "hain", "mera", "tera", "sir",
                    "nahi", "haan", "theek", "achha", "shukriya", "bilkul",
                    "main", "tum", "aur", "yeh", "woh", "kya", "toh"]
        lang = "hi" if any(w in text.lower() for w in hi_words) else "en"

        tmp_dir = os.path.expanduser("~/.friday_tts_chunks")
        os.makedirs(tmp_dir, exist_ok=True)
        fpath = os.path.join(tmp_dir, "friday_speak.mp3")

        # Pura text ek hi file mein save karo — no chunking, no gaps
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(fpath)

        def _play():
            try:
                subprocess.Popen(
                    ["mpv", "--no-video", "--really-quiet", "--no-terminal", fpath],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except FileNotFoundError:
                try:
                    subprocess.Popen(
                        ["termux-media-player", "play", fpath],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except: pass
            except Exception as e:
                log_warn(f"Playback error: {e}")

        _pt = threading.Thread(target=_play, daemon=True)
        _pt.start()
        return True

    except ImportError:
        return False
    except Exception as e:
        log_warn(f"gTTS error: {e}")
        return False

def speak(text):
    global _tts
    # Pura text bolega — koi limit nahi
    clean = re.sub(r'[^\w\s,.!?]', '', text)
    if not clean.strip():
        return
    if not CFG.get("voice_enabled", True):
        return
    with _tts_lock:
        try:
            if _tts and _tts.poll() is None: _tts.terminate()
        except: pass
        # gTTS — Google Text to Speech (primary)
        if _speak_gtts(clean):
            return
        # Fallback — Termux TTS
        try:
            _tts = subprocess.Popen(
                ["termux-tts-speak", clean],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            log_warn(f"TTS failed: {e}")

def load_memory():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE) as f: return json.load(f)
    except: pass
    return {"messages":[]}

def save_memory(mem):
    try:
        mem["messages"] = mem["messages"][-MAX_MEMORY:]
        with open(MEMORY_FILE,'w') as f: json.dump(mem,f,indent=2,ensure_ascii=False)
    except: pass

def add_memory(mem, role, content):
    mem.setdefault("messages",[]).append({"role":role,"content":content})
    save_memory(mem); return mem

def show_memory(mem):
    msgs = mem.get("messages",[])
    if not msgs: return cc("🧠 Memory bank is empty Boss.")
    out = f"\n{cc('╔══════ 🧠 MEMORY ══════╗')}\n"
    for m in msgs[-8:]:
        role = cb("You") if m["role"]=="user" else cf("Me")
        out += f"  {role}: {m['content'][:65]}\n"
    return out + cc('╚═══════════════════════╝')

def note_save(text):
    notes = []
    try:
        if os.path.exists(NOTES_FILE): notes = json.load(open(NOTES_FILE))
    except: pass
    notes.append({"time":datetime.datetime.now().strftime("%d %b %Y, %H:%M"),"text":text})
    json.dump(notes, open(NOTES_FILE,'w'), ensure_ascii=False, indent=2)
    return cg(f"✓ Note saved: {text}")

def note_list():
    try:
        notes = json.load(open(NOTES_FILE))
        if not notes: return cy("No notes found Boss.")
        out = f"\n{cc('╔══════ 📝 NOTES ══════╗')}\n"
        for i,n in enumerate(notes[-10:],1):
            out += f"  {cf(f'[{i}]')} {DM}{n['time']}{RS}\n      {n['text']}\n"
        return out + cc('╚══════════════════════╝')
    except: return cy("No notes found Boss.")

def note_delete(idx):
    try:
        notes = json.load(open(NOTES_FILE))
        if 0 <= idx < len(notes):
            rm = notes.pop(idx)
            json.dump(notes, open(NOTES_FILE,'w'), ensure_ascii=False, indent=2)
            return cg(f"✓ Deleted: {rm['text'][:40]}")
        return cy("Invalid note number Boss.")
    except: return cy("No notes found Boss.")

def get_battery():
    try:
        r = subprocess.run(["termux-battery-status"],capture_output=True,text=True,timeout=5)
        d = json.loads(r.stdout)
        pct = d.get("percentage",0)
        plug = "⚡ CHARGING" if d.get("status","")=="CHARGING" else "🔋 BATTERY"
        color = G if pct>50 else (Y if pct>20 else R)
        bar = color+"█"*int(pct/5)+DM+"░"*(20-int(pct/5))+RS
        return pct, f"{plug} {bar} {color}{pct}%{RS}"
    except: return 0, cy("Battery info unavailable.")

def get_ram():
    try:
        with open("/proc/meminfo") as f:
            lines = {l.split(':')[0]:int(l.split()[1]) for l in f if ':' in l and len(l.split())>1 and l.split()[1].isdigit()}
        total=lines.get("MemTotal",1); avail=lines.get("MemAvailable",0); used=total-avail
        pct=int(used/total*100)
        color = G if pct<60 else (Y if pct<80 else R)
        bar = color+"█"*int(pct/5)+DM+"░"*(20-int(pct/5))+RS
        return f"💾 RAM {bar} {color}{pct}%{RS} ({used//1024}/{total//1024}MB)"
    except: return cy("RAM info unavailable.")

def get_storage():
    try:
        r = subprocess.run(["df","-h","/data"],capture_output=True,text=True)
        p = r.stdout.strip().split('\n')[1].split()
        pct_n = int(p[4].replace('%',''))
        color = G if pct_n<70 else (Y if pct_n<90 else R)
        bar = color+"█"*int(pct_n/5)+DM+"░"*(20-int(pct_n/5))+RS
        return f"📊 Storage {bar} {color}{p[4]}{RS} Free:{p[3]}/{p[1]}"
    except: return cy("Storage info unavailable.")

def get_network():
    lines = []
    try:
        r = subprocess.run(["ip","route","get","8.8.8.8"],capture_output=True,text=True)
        m = re.search(r'src (\S+)',r.stdout)
        if m: lines.append(f"  {cc('◈ Local IP  :')} {m.group(1)}")
    except: pass
    try:
        pub = urllib.request.urlopen("https://api.ipify.org",timeout=5).read().decode()
        lines.append(f"  {cc('◈ Public IP :')} {pub}")
    except: pass
    try:
        r = subprocess.run(["termux-wifi-connectioninfo"],capture_output=True,text=True,timeout=4)
        d = json.loads(r.stdout)
        lines.append(f"  {cc('◈ WiFi SSID :')} {d.get('ssid','?')}")
        lines.append(f"  {cc('◈ Speed     :')} {d.get('link_speed_mbps','?')} Mbps")
    except: pass
    return "\n".join(lines) if lines else cy("Network info unavailable.")

def open_url(url):
    try: subprocess.Popen(["termux-open-url",url]); return True
    except:
        try: webbrowser.open(url); return True
        except: return False

def do_google(query):
    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
    open_url(url); return cg(f"✓ Google search opened: '{query}'")

def do_youtube(query=""):
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}" if query else "https://youtube.com"
    open_url(url); return cg(f"✓ YouTube {'search: '+query if query else 'opened'}")

def clean_roman(text):
    """Remove Devanagari/non-ASCII, keep Roman Hindi + English only."""
    text = re.sub(r'[\u0900-\u097F]+', '', text)
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    text = re.sub(r' +', ' ', text).strip()
    return text

def do_ddgr(query):
    """ddgr se search, AI se clean Roman Hindi summary."""
    try:
        # ddgr 2.2 compatible flags only: --num, --noua, --json
        result = subprocess.run(
            ["ddgr", "--num", "3", "--noua", "--json", "--noprompt", query],
            capture_output=True, text=True, timeout=15,
            input="q\n"  # auto-quit interactive mode
        )
        raw = result.stdout.strip()
        ansi = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', re.IGNORECASE)
        raw  = ansi.sub('', raw)
    except FileNotFoundError:
        return cy("ddgr not found! Run: pip install ddgr"), ""
    except subprocess.TimeoutExpired:
        return cy("ddgr timeout Boss."), ""
    except Exception as e:
        return cy(f"ddgr error: {e}"), ""

    if not raw:
        return cy(f"Koi result nahi mila: {query}"), ""

    # Parse JSON output from ddgr --json
    try:
        data = json.loads(raw)
    except Exception:
        return cy(f"ddgr parse error Boss. Raw: {raw[:100]}"), ""

    if not data:
        return cy(f"Koi result nahi mila: {query}"), ""

    # Collect all text including Devanagari — AI will translate/summarize
    context_parts = []
    for b in data[:5]:
        title = b.get("title", "").strip()
        desc  = b.get("abstract", "").strip()
        part  = title
        if desc: part += " — " + desc
        if part.strip(): context_parts.append(part)

    context = "\n".join(context_parts)

    # AI se clean Roman Hindi summary
    ai_answer = None
    if GROQ_KEY and context_parts:
        ai_prompt = (
            f'User ne poocha: "{query}"\n\n'
            f'Search results:\n{context}\n\n'
            f'SIRF 1-2 lines mein jawab do. Roman script. Dates/facts clearly. Koi URL nahi.'
        )
        ai_sys = (
            "Tu FRIDAY AI hai. Hinglish mein jawab de — Hindi aur English mix. "
            "Kabhi Devanagari script mat use karo. Roman letters mein Hindi likho. "
            "1-2 lines max. Numbers aur facts clearly likho. Koi URL nahi."
        )
        ai_answer = ask_ai(ai_prompt, system_override=ai_sys, max_tokens=200)

    # Build display
    sep = "═" * 48
    out = f"\n{Y}╔══ 🦆 {query[:42]} ══╗{RS}\n\n"

    if ai_answer:
        clean_ans = clean_roman(ai_answer).strip()
        for line in clean_ans.split("\n"):
            line = line.strip()
            if line: out += f"  {W}{line}{RS}\n"
        voice = clean_ans[:350]
    else:
        # Fallback — show clean titles
        for j, b in enumerate(data[:5], 1):
            t = clean_roman(b.get("title",""))[:70] or b.get("title","")[:70]
            d = clean_roman(b.get("abstract",""))[:100]
            out += f"  {C}{j}. {t}{RS}\n"
            if d: out += f"     {W}{d}{RS}\n"
        voice = clean_roman(data[0].get("title",""))[:200] if data else query

    out += f"\n{Y}╚{sep}╝{RS}\n"
    return out, voice

def ask_ai(user_input, history=None, system_override=None, max_tokens=120):
    if not GROQ_KEY: return None
    msgs = list(history or [])[-8:]
    msgs.append({"role":"user","content":user_input})
    sys_prompt = system_override if system_override else SYSTEM_PROMPT

    # LTM facts inject karo system prompt mein
    if not system_override:
        try:
            ltm = ltmem_load()
            topics = ltm.get("topics", {})
            facts  = ltm.get("facts", [])
            if topics or facts:
                ltm_lines = ["\nBOSS KE BAARE MEIN SAVED FACTS (ye sach hai — kabhi deny mat karo):"]
                for k, v in list(topics.items())[:20]:
                    val = v.get("value", v) if isinstance(v, dict) else v
                    ltm_lines.append(f"  - {k}: {val}")
                sys_prompt = sys_prompt + "\n".join(ltm_lines)
        except Exception:
            pass
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role":"system","content":sys_prompt}] + msgs,
        "temperature": 0.7,
        "max_tokens": max_tokens
    })
    headers = {"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json","User-Agent":"Friday/3.0"}
    try:
        ctx=ssl.create_default_context()
        conn=http.client.HTTPSConnection("api.groq.com",timeout=30,context=ctx)
        conn.request("POST","/openai/v1/chat/completions",body=payload,headers=headers)
        resp=conn.getresponse(); body=resp.read().decode(); conn.close()
        if resp.status==200: return json.loads(body)["choices"][0]["message"]["content"]
    except: pass
    return None

def ai_thinking(stop_event):
    frames="⠋⠙⠸⢰⣠⣄⡆⠇"; i=0
    while not stop_event.is_set():
        sys.stdout.write(f"\r  {C}{frames[i%len(frames)]} Thinking...{RS}"); sys.stdout.flush(); time.sleep(0.1); i+=1
    sys.stdout.write("\r"+" "*25+"\r"); sys.stdout.flush()

def do_sms(number,message):
    try: subprocess.run(["termux-sms-send","-n",number,message],timeout=10); return cg(f"✓ SMS sent to {number}")
    except Exception as e: return cy(f"SMS failed: {e}")

def do_call(number):
    try: subprocess.run(["termux-telephony-call",number],timeout=5); return cg(f"✓ Calling {number}...")
    except Exception as e: return cy(f"Call failed: {e}")

def do_contacts():
    try:
        r=subprocess.run(["termux-contact-list"],capture_output=True,text=True,timeout=8)
        contacts=json.loads(r.stdout)[:15]
        out=f"\n{cc('📱 Contacts:')}\n"
        for c in contacts: out+=f"  {cf('◈')} {c.get('name','?')}: {DM}{c.get('number','?')}{RS}\n"
        return out
    except: return cy("Contacts unavailable.")

def do_screenshot():
    ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path=f"/sdcard/Pictures/friday_{ts}.png"
    os.makedirs("/sdcard/Pictures", exist_ok=True)
    try:
        # Android screencap command (root nahi chahiye)
        r = subprocess.run(["screencap", "-p", path], capture_output=True, timeout=10)
        if r.returncode == 0 and os.path.exists(path):
            # Media scan karo taaki Gallery mein dikhe
            subprocess.run(["termux-media-scan", path], capture_output=True, timeout=5)
            return cg(f"✓ Screenshot saved: {path}")
        return cy("Screenshot nahi hua Boss. Phone ke Volume Down + Power button ek saath dabao!")
    except FileNotFoundError:
        return cy("Boss, screenshot ke liye Volume Down + Power button ek saath dabao — fastest tarika!")
    except Exception as e:
        return cy(f"Screenshot error: {e}")

def do_brightness(val):
    val=max(0,min(255,int(val)))
    pct=int(val/255*100)
    color=G if pct>60 else (Y if pct>30 else C)
    bar=color+"█"*int(pct/5)+DM+"░"*(20-int(pct/5))+RS
    # Background mein chalao — FRIDAY block na ho
    try:
        subprocess.Popen(["termux-brightness",str(val)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        return cy(f"Brightness error: {e}")
    return f"☀️  Brightness {bar} {color}{pct}%{RS}"

def find_music(query=None):
    files=[]
    for d in MUSIC_DIRS:
        if not os.path.exists(d): continue
        for root,_,flist in os.walk(d):
            for f in flist:
                if f.lower().endswith(MUSIC_EXT):
                    if query is None or query.lower() in f.lower():
                        files.append(os.path.join(root,f))
            if len(files)>500: break
        if len(files)>500: break
    return files

# ── Music Player ──────────────────────────────────────────────
class MusicPlayer:
    def __init__(self):
        self.playlist = []
        self.index    = 0
        self.proc     = None
        self.playing  = False
        self.volume   = 80
        self.lock     = threading.Lock()
        self._watcher = None

    def _kill(self):
        with self.lock:
            if self.proc and self.proc.poll() is None:
                try:
                    self.proc.terminate()
                    self.proc.wait(timeout=1)
                except: pass
                try:
                    self.proc.kill()
                    self.proc.wait(timeout=1)
                except: pass
            self.proc = None
        # Force kill all mpv processes as backup
        try: subprocess.run(["killall", "-9", "mpv"], stderr=subprocess.DEVNULL)
        except: pass
        try: subprocess.run(["pkill", "-9", "mpv"], stderr=subprocess.DEVNULL)
        except: pass

    def _launch(self, idx):
        self._kill()
        if not self.playlist:
            return cy("No songs found. Run: termux-setup-storage")
        self.index = idx % len(self.playlist)
        fp   = self.playlist[self.index]
        name = os.path.basename(fp)
        self.playing = True
        try:
            with self.lock:
                self.proc = subprocess.Popen(
                    ["mpv","--no-video","--really-quiet",f"--volume={self.volume}", fp],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True)  # Fully detached — band nahi hoga
            self._start_watcher()
            total = len(self.playlist)
            return (f"{G}🎵 Now Playing [{self.index+1}/{total}]:{RS}\n"
                    f"   {W}{name}{RS}\n"
                    f"   {DM}next | back | stop | pause | volume <0-100> | playlist{RS}")
        except FileNotFoundError:
            try:
                # mpv nahi hai — termux-media-player try karo
                self.proc = subprocess.Popen(
                    ["termux-media-player", "play", fp],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True  # Fully detached process
                )
                self._start_watcher()
                return cg(f"🎵 Playing: {name}")
            except:
                return cy("Gana bajane ke liye mpv install karo:\n  pkg install mpv")

    def _start_watcher(self):
        def _w():
            p = self.proc
            if p: p.wait()
            if self.playing:
                time.sleep(0.8)
                self._launch(self.index + 1)
        if self._watcher and self._watcher.is_alive(): return
        self._watcher = threading.Thread(target=_w, daemon=True)
        self._watcher.start()

    def play(self, query=None):
        files = find_music(query) if query else find_music()
        if not files:
            return cy("No music found Boss. Run: termux-setup-storage")
        self.playlist = files
        random.shuffle(self.playlist)
        self.index = 0
        return self._launch(0)

    def next_song(self):
        if not self.playlist: return cy("Pehle 'gana bajao' bolein Boss.")
        return self._launch(self.index + 1)

    def prev_song(self):
        if not self.playlist: return cy("Pehle 'gana bajao' bolein Boss.")
        return self._launch(self.index - 1)

    def stop(self):
        self.playing = False
        self._kill()
        # Also stop termux-media-player if active
        try: subprocess.run(["termux-media-player", "stop"], stderr=subprocess.DEVNULL, timeout=3)
        except: pass
        return cy("⏹ Music band ho gaya Boss.")

    def pause(self):
        import signal
        if self.proc and self.proc.poll() is None:
            try: self.proc.send_signal(signal.SIGSTOP); return cy("⏸ Music paused Boss.")
            except: pass
        return cy("Kuch nahi chal raha Boss.")

    def resume(self):
        import signal
        if self.proc and self.proc.poll() is None:
            try: self.proc.send_signal(signal.SIGCONT); return cg("▶ Music resumed Boss.")
            except: pass
        if self.playlist: return self._launch(self.index)
        return cy("Pehle 'gana bajao' bolein Boss.")

    def set_volume(self, vol):
        self.volume = max(0, min(100, int(vol)))
        try: subprocess.run(["termux-volume","music",str(self.volume)], timeout=3)
        except: pass
        filled = int(self.volume/10)
        bar = G+"█"*filled+DM+"░"*(10-filled)+RS
        # Restart with new volume
        if self.playing and self.playlist:
            self._launch(self.index)
        return cg(f"🔊 Volume: {bar} {self.volume}%")

    def status(self):
        if not self.playlist: return cy("No playlist loaded Boss.")
        name = os.path.basename(self.playlist[self.index])
        st   = f"{G}▶ PLAYING{RS}" if (self.proc and self.proc.poll() is None) else f"{R}⏹ STOPPED{RS}"
        filled = int(self.volume/10)
        bar = G+"█"*filled+DM+"░"*(10-filled)+RS
        return (f"\n{Y}╔══════ 🎵 NOW PLAYING ══════╗{RS}\n"
                f"  {cc('Track  :')} {name[:38]}\n"
                f"  {cc('Status :')} {st}\n"
                f"  {cc('No.    :')} {self.index+1} / {len(self.playlist)}\n"
                f"  {cc('Volume :')} {bar} {self.volume}%\n"
                f"{Y}╚{chr(9552)*30}╝{RS}")

    def playlist_view(self):
        if not self.playlist: return cy("No playlist Boss.")
        out = f"\n{Y}╔══ 🎵 PLAYLIST ({len(self.playlist)} songs) ══╗{RS}\n"
        start = max(0, self.index-2)
        for i in range(start, min(start+8, len(self.playlist))):
            mark = f"{G}▶ " if i==self.index else "  "
            out += f"{mark}{Y}[{i+1}]{RS} {os.path.basename(self.playlist[i])[:38]}\n"
        return out + f"{Y}╚{chr(9552)*42}╝{RS}"

MP = MusicPlayer()

def do_calc(expr):
    m=re.match(r'([\d.]+)%\s+of\s+([\d.]+)',expr,re.I)
    if m: return cg(f"🧮 {expr} = {float(m.group(1))/100*float(m.group(2))}")
    safe={'sqrt':math.sqrt,'sin':math.sin,'cos':math.cos,'tan':math.tan,'log':math.log,
          'log10':math.log10,'pi':math.pi,'e':math.e,'abs':abs,'round':round,'pow':pow,
          'ceil':math.ceil,'floor':math.floor}
    try:
        result=eval(expr.replace('^','**').replace('x','*'),{"__builtins__":{}},safe)
        return cg(f"🧮 {expr} = {result}")
    except Exception as ex: return cy(f"Error: {ex}")

def do_convert(val,frm,to):
    frm,to=frm.lower(),to.lower()
    if frm in ["c","celsius"] and to in ["f","fahrenheit"]: return cg(f"🌡️  {val}°C = {val*9/5+32:.2f}°F")
    if frm in ["f","fahrenheit"] and to in ["c","celsius"]: return cg(f"🌡️  {val}°F = {(val-32)*5/9:.2f}°C")
    if (frm,to) in CONV: return cg(f"🔢 {val} {frm.upper()} = {val*CONV[(frm,to)]:.4f} {to.upper()}")
    do_google(f"{val} {frm} to {to}"); return cc(f"Opened Google for: {val} {frm} to {to}")

def do_password(length=16,ptype="strong"):
    if ptype=="pin": charset=string.digits; length = length if length != 16 else 6
    elif ptype=="medium": charset=string.ascii_letters+string.digits
    else: charset=string.ascii_letters+string.digits+"!@#$%^&*()-_=+[]{}|;:,.<>?"
    passwords=[''.join(random.SystemRandom().choices(charset,k=length)) for _ in range(3)]
    out=f"\n{Y}╔══════════ 🔐 PASSWORD GENERATOR ══════════╗{RS}\n  {C}Type: {W}{ptype.title()}  Length: {length}{RS}\n{Y}{'─'*46}{RS}\n"
    for i,pw in enumerate(passwords,1):
        col="".join((G if ch in string.ascii_letters else Y if ch in string.digits else R)+ch for ch in pw)
        out+=f"  {Y}[{i}]{RS} {col}{RS}\n"
    return out+f"{Y}╚{'═'*45}╝{RS}\n  {DM}🟢 Letter  🟡 Number  🔴 Symbol{RS}\n"

def start_timer(seconds,label="Timer"):
    def _run():
        time.sleep(seconds); print(f"\n  {R}🔔 {label} COMPLETE!{RS}\n"); speak(f"{label} complete Boss!")
        try: subprocess.Popen(["termux-vibrate","-d","1000"])
        except: pass
        try: subprocess.Popen(["termux-notification","--title","Friday","--content",f"{label} done!"])
        except: pass
    threading.Thread(target=_run,daemon=True).start()


# ─── New Feature Functions ───────────────────────────────────

def do_ip_lookup(ip_or_domain):
    """IP ya domain ki location info fetch karo."""
    target = ip_or_domain.strip()
    try:
        url = f"http://ip-api.com/json/{urllib.parse.quote(target)}?fields=status,country,regionName,city,isp,lat,lon,query"
        data = json.loads(urllib.request.urlopen(url, timeout=8).read())
        if data.get("status") == "success":
            out  = f"\n{Y}╔══ 🌍 IP Lookup: {target} ══╗{RS}\n"
            out += f"  {cc('IP      :')} {data.get('query','?')}\n"
            out += f"  {cc('Country :')} {data.get('country','?')}\n"
            out += f"  {cc('Region  :')} {data.get('regionName','?')}\n"
            out += f"  {cc('City    :')} {data.get('city','?')}\n"
            out += f"  {cc('ISP     :')} {data.get('isp','?')}\n"
            out += f"  {cc('Coords  :')} {data.get('lat','?')}, {data.get('lon','?')}\n"
            out += f"{Y}╚{'═'*36}╝{RS}\n"
            speak(f"{target} is from {data.get('city','?')}, {data.get('country','?')} Boss.")
            return out
        return cy(f"IP lookup failed for: {target}")
    except Exception as e:
        return cy(f"IP lookup error: {e}")

        return cy(f"IP lookup error: {e}")

def do_nmap(target, scan_type="basic"):
    """Nmap se network scan karo."""
    # Check if nmap is installed
    try:
        subprocess.run(["nmap","--version"], capture_output=True, timeout=5)
    except FileNotFoundError:
        return cy("Nmap install nahi hai Boss!\nInstall karo: pkg install nmap")
    except: pass

    out = f"\n{Y}╔══ 🔍 NMAP SCAN: {target[:40]} ══╗{RS}\n"
    speak(f"Scanning {target} Boss.")

    # Scan type decide karo
    if scan_type == "quick":
        # Quick scan — top 100 ports
        args = ["nmap", "-F", "--open", target]
        out += f"  {DM}Mode: Quick Scan (top 100 ports){RS}\n"
    elif scan_type == "full":
        # Full port scan
        args = ["nmap", "-p-", "--open", "-T4", target]
        out += f"  {DM}Mode: Full Port Scan (1-65535){RS}\n"
    elif scan_type == "os":
        # OS detection
        args = ["nmap", "-O", "--osscan-guess", target]
        out += f"  {DM}Mode: OS Detection{RS}\n"
    elif scan_type == "service":
        # Service version detection
        args = ["nmap", "-sV", "--open", target]
        out += f"  {DM}Mode: Service Version Detection{RS}\n"
    elif scan_type == "ping":
        # Ping scan — host discovery only
        args = ["nmap", "-sn", target]
        out += f"  {DM}Mode: Ping Scan (host discovery){RS}\n"
    elif scan_type == "udp":
        # UDP scan
        args = ["nmap", "-sU", "--top-ports", "20", target]
        out += f"  {DM}Mode: UDP Scan (top 20 ports){RS}\n"
    elif scan_type == "vuln":
        # Vulnerability scripts
        args = ["nmap", "--script", "vuln", target]
        out += f"  {DM}Mode: Vulnerability Scan{RS}\n"
    elif scan_type == "aggressive":
        # Aggressive — OS + version + scripts + traceroute
        args = ["nmap", "-A", target]
        out += f"  {DM}Mode: Aggressive Scan (-A){RS}\n"
    else:
        # Basic — open ports only
        args = ["nmap", "--open", "-T4", target]
        out += f"  {DM}Mode: Basic Scan (common ports){RS}\n"

    out += f"  {DM}Target: {target}{RS}\n"
    out += f"{Y}{'─'*50}{RS}\n"

    try:
        print(out)
        print(f"  {C}⠋ Scanning... (yeh thoda time le sakta hai){RS}\n")
        result = subprocess.run(args, capture_output=True, text=True, timeout=120)
        raw = result.stdout.strip()

        if not raw:
            return cy(f"Koi output nahi mila. Target unreachable ya blocked hai Boss.")

        # Parse and colorize output
        final_out = f"\n{Y}╔══ 🔍 NMAP RESULT: {target[:35]} ══╗{RS}\n"
        open_ports = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line: continue
            if "open" in line and "/" in line:
                # Port line — highlight
                parts = line.split()
                port = parts[0] if parts else ""
                state = parts[1] if len(parts)>1 else ""
                service = " ".join(parts[2:]) if len(parts)>2 else ""
                final_out += f"  {G}✓ {port:<20}{RS} {W}{state:<8}{RS} {C}{service}{RS}\n"
                open_ports.append(port)
            elif "filtered" in line and "/" in line:
                final_out += f"  {Y}~ {line[:65]}{RS}\n"
            elif "closed" in line and "/" in line:
                final_out += f"  {R}✗ {line[:65]}{RS}\n"
            elif line.startswith("Host is"):
                final_out += f"  {M}🖥  {line}{RS}\n"
            elif line.startswith("OS"):
                final_out += f"  {M}💻 {line}{RS}\n"
            elif line.startswith("Nmap scan report"):
                final_out += f"  {Y}{line}{RS}\n"
            elif line.startswith("MAC Address"):
                final_out += f"  {C}🔌 {line}{RS}\n"
            elif "latency" in line.lower() or "scan done" in line.lower():
                final_out += f"  {DM}{line}{RS}\n"
            else:
                final_out += f"  {DM}{line[:70]}{RS}\n"

        # Summary
        final_out += f"{Y}{'─'*50}{RS}\n"
        if open_ports:
            final_out += f"  {G}Open Ports: {len(open_ports)} found{RS} — {', '.join(open_ports[:8])}\n"
        else:
            final_out += f"  {Y}Koi open port nahi mila{RS}\n"
        final_out += f"{Y}╚{'═'*50}╝{RS}\n"

        speak(f"Scan complete Boss. {len(open_ports)} open ports mile.")
        return final_out

    except subprocess.TimeoutExpired:
        return cy(f"Scan timeout ho gaya Boss. Target slow ya unreachable hai.")
    except Exception as e:
        return cy(f"Nmap error: {e}")


    """Text ka hash generate karo."""
    import hashlib
    out = f"\n{Y}╔══ 🔑 HASH: {text[:30]} ══╗{RS}\n"
    algos = ["md5","sha1","sha256","sha512"] if algo=="all" else [algo]
    for a in algos:
        try:
            h = hashlib.new(a, text.encode()).hexdigest()
            out += f"  {C}{a.upper():8}{RS} {W}{h}{RS}\n"
        except: pass
    out += f"{Y}╚{'═'*50}╝{RS}\n"
    return out

def do_weather(city):
    """Open-Meteo + geocoding — accurate real-time weather, no API key."""
    WMO = {
        0:"Clear sky",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",
        45:"Foggy",48:"Icy fog",51:"Light drizzle",53:"Drizzle",55:"Heavy drizzle",
        61:"Light rain",63:"Rain",65:"Heavy rain",71:"Light snow",73:"Snow",
        75:"Heavy snow",80:"Rain showers",81:"Heavy showers",95:"Thunderstorm",
    }
    ICONS = {
        "Clear":"☀️","Mainly clear":"🌤️","Partly":"⛅","Overcast":"☁️",
        "Fog":"🌫️","Drizzle":"🌦️","Rain":"🌧️","Snow":"❄️","Thunder":"⛈️",
    }
    try:
        # Step 1: Geocode
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1&language=en&format=json"
        geo = json.loads(urllib.request.urlopen(geo_url, timeout=8).read())
        if not geo.get("results"):
            return cy(f"City '{city}' not found Boss.")
        res = geo["results"][0]
        lat = res["latitude"]; lon = res["longitude"]
        name = res.get("name", city); country = res.get("country","")

        # Step 2: Weather
        w_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
            f"weather_code,wind_speed_10m,visibility,is_day"
            f"&daily=temperature_2m_max,temperature_2m_min,weather_code"
            f"&timezone=auto&forecast_days=5"
        )
        wdata = json.loads(urllib.request.urlopen(w_url, timeout=8).read())
        cur   = wdata["current"]
        daily = wdata.get("daily", {})

        temp  = round(cur["temperature_2m"])
        feels = round(cur["apparent_temperature"])
        humid = cur["relative_humidity_2m"]
        wind  = round(cur["wind_speed_10m"])
        vis   = round(cur.get("visibility",0)/1000, 1)
        wcode = cur["weather_code"]
        is_day= cur.get("is_day",1)
        desc  = WMO.get(wcode, "Unknown")
        if not is_day and wcode==0: desc = "Clear night"
        icon  = next((v for k,v in ICONS.items() if k.lower() in desc.lower()), "🌡️")

        out  = f"\n{Y}╔══ {icon} Weather: {name}, {country} ══╗{RS}\n"
        out += f"  {cc('Condition :')} {desc}\n"
        out += f"  {cc('Temp      :')} {temp}°C  (Feels like {feels}°C)\n"
        out += f"  {cc('Humidity  :')} {humid}%\n"
        out += f"  {cc('Wind      :')} {wind} km/h\n"
        out += f"  {cc('Visibility:')} {vis} km\n"

        # 5-day forecast
        if daily.get("time"):
            out += f"\n  {DM}── 5-Day Forecast ──{RS}\n"
            for d,mx,mn,wc in zip(daily["time"][:5], daily["temperature_2m_max"][:5],
                                   daily["temperature_2m_min"][:5], daily["weather_code"][:5]):
                day_name = datetime.datetime.strptime(d,"%Y-%m-%d").strftime("%a")
                d_desc   = WMO.get(wc,"?")
                d_icon   = next((v for k,v in ICONS.items() if k.lower() in d_desc.lower()),"🌡️")
                out += f"  {W}{day_name}{RS}  {d_icon} {d_desc[:18]:<18} {G}{round(mx)}°{RS}/{C}{round(mn)}°C{RS}\n"

        out += f"\n{Y}╚{'═'*42}╝{RS}\n"
        speak(f"{name} mein {desc} hai. Temperature {temp} degree Celsius hai Boss.")
        return out
    except Exception as e:
        return cy(f"Weather error: {e}")

def do_news(topic="india"):
    """RSS se latest news fetch karo — fast and free."""
    return get_live_news(topic)

def do_hash(text, algo="md5"):
    """MD5 / SHA1 / SHA256 hash generate karo."""
    import hashlib
    algo = algo.lower().replace("-", "")
    algos = {
        "md5":    hashlib.md5,
        "sha1":   hashlib.sha1,
        "sha256": hashlib.sha256,
        "sha512": hashlib.sha512,
    }
    if algo not in algos:
        return cy(f"Unknown algorithm '{algo}'. Use: md5, sha1, sha256, sha512")
    h = algos[algo](text.encode()).hexdigest()
    out  = f"\n{Y}╔══ 🔑 HASH RESULT ══╗{RS}\n"
    out += f"  {C}Algorithm : {BD}{algo.upper()}{RS}\n"
    out += f"  {W}Input     : {DM}{text[:50]}{RS}\n"
    out += f"  {G}Hash      : {BD}{h}{RS}\n"
    out += f"{Y}╚{'═'*36}╝{RS}\n"
    speak(f"{algo.upper()} hash ready Boss.")
    return out

def do_qr(text):
    """Simple QR code — terminal mein ASCII art."""
    try:
        import urllib.request
        enc = urllib.parse.quote(text)
        # Use goqr.me API
        url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={enc}"
        path = os.path.expanduser(f"~/Pictures/friday_qr_{int(time.time())}.png")
        os.makedirs(os.path.expanduser("~/Pictures"), exist_ok=True)
        urllib.request.urlretrieve(url, path)
        speak(f"QR code saved Boss.")
        return cg(f"✓ QR Code saved: {path}\n  {DM}Open: termux-open {path}{RS}")
    except Exception as e:
        return cy(f"QR error: {e}")




# ─── Image Generation ─────────────────────────────────────────

IMAGE_DIR = os.path.expanduser("~/Pictures/friday_images")
IMAGE_DIR_SDCARD = "/sdcard/Pictures/friday_images"

def image_gen_pollinations(prompt, width=512, height=512, model="flux"):
    """Image generation — currently no working free provider available in India."""
    encoded = urllib.parse.quote(prompt)
    msg  = f"\n{Y}╔══ 🎨 IMAGE GENERATION ══╗{RS}\n"
    msg += f"  {C}Prompt  :{RS} {W}{prompt[:60]}{RS}\n"
    msg += f"  {Y}Status  :{RS} {Y}India mein free AI image providers block hain{RS}\n"
    msg += f"  {C}Options :{RS}\n"
    msg += f"    {G}1. VPN use karo → Pollinations kaam karega{RS}\n"
    msg += f"    {G}2. HuggingFace token banao (Inference API permission ke saath){RS}\n"
    msg += f"       https://huggingface.co/settings/tokens{RS}\n"
    msg += f"    {G}3. Stability AI credits kharido{RS}\n"
    msg += f"       https://platform.stability.ai/account/credits{RS}\n"
    msg += f"  {DM}Browser se manually try karo:{RS}\n"
    msg += f"  {DM}https://image.pollinations.ai/prompt/{encoded[:50]}{RS}\n"
    msg += f"{Y}╚{'═'*42}╝{RS}\n"
    try:
        subprocess.Popen(["termux-open-url", f"https://image.pollinations.ai/prompt/{encoded}"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass
    return msg


def image_list():
    """Generated images ki list."""
    _ensure_image_dir()
    files = sorted([f for f in os.listdir(IMAGE_DIR)
                    if f.lower().endswith(('.jpg','.jpeg','.png'))], reverse=True)
    if not files:
        return cy("Koi generated images nahi hain Boss. 'imagine <prompt>' se banao.")
    out = f"\n{Y}╔══ 🖼 GENERATED IMAGES ({len(files)}) ══╗{RS}\n"
    for i, f in enumerate(files[:10], 1):
        out += f"  {C}[{i}]{RS} {W}{f[:50]}{RS}\n"
    out += f"  {DM}Path: {IMAGE_DIR}{RS}\n"
    out += f"{Y}╚{'═'*44}╝{RS}\n"
    return out

def image_open_last():
    """Last generated image open karo."""
    _ensure_image_dir()
    files = sorted([os.path.join(IMAGE_DIR, f) for f in os.listdir(IMAGE_DIR)
                    if f.lower().endswith(('.jpg','.jpeg','.png'))], key=os.path.getmtime, reverse=True)
    if not files:
        return cy("Koi image nahi hai Boss.")
    try:
        subprocess.Popen(["termux-open", files[0]])
        return cg(f"✓ Opening: {os.path.basename(files[0])}")
    except Exception as e:
        return cy(f"Open failed: {e}")


# ══════════════════════════════════════════════════════════════

# ─── Structured Web Scraper ──────────────────────────────────

def scrape_url(url, selector="text"):
    """Fetch a URL and extract clean text or structured data."""
    try:
        ctx  = ssl.create_default_context()
        req  = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36",
            "Accept":     "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            raw_bytes = resp.read(300000)  # max 300KB
        # Decode
        try:    html = raw_bytes.decode("utf-8")
        except: html = raw_bytes.decode("latin-1", errors="ignore")

        # Strip scripts, styles, tags
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL|re.I)
        html = re.sub(r'<style[^>]*>.*?</style>',  '', html, flags=re.DOTALL|re.I)
        html = re.sub(r'<[^>]+>', ' ', html)
        html = re.sub(r'&nbsp;', ' ', html)
        html = re.sub(r'&amp;',  '&', html)
        html = re.sub(r'&lt;',   '<', html)
        html = re.sub(r'&gt;',   '>', html)
        html = re.sub(r'[ \t]+', ' ', html)
        # Clean lines
        lines = [l.strip() for l in html.split('\n') if len(l.strip()) > 30]
        text  = '\n'.join(lines[:80])
        return text[:6000]
    except Exception as e:
        log_error(f"scrape_url {url}: {e}")
        return ""

def scrape_and_summarize(url):
    """Scrape URL and get AI summary in Roman Hindi."""
    print_friday(f"Scraping: {url[:50]}...")
    text = scrape_url(url)
    if not text:
        return cy(f"Scrape failed Boss. Check URL or internet.")

    if GROQ_KEY:
        prompt = (
            f"Is webpage ka content hai:\n{text[:3000]}\n\n"
            f"Iska CLEAR summary Roman Hindi mein do:\n"
            f"- Key points bullets mein\n"
            f"- Important numbers/facts mention karo\n"
            f"- Koi URLs nahi\n"
            f"- 6-8 lines"
        )
        ai_sys = "Tu ek web scraper AI hai. Roman Hindi mein clear structured summary deta hai. Koi URLs nahi."
        summary = ask_ai(prompt, system_override=ai_sys, max_tokens=600)
        if summary:
            return clean_roman(summary)
    # Fallback — return first 500 chars
    return clean_roman(text[:500])

# ─── FEATURE 1: Long-Term Memory (topics/facts) ──────────────

LTMEM_FILE = os.path.expanduser("~/.friday_ltmem.json")

def ltmem_load():
    try:
        if os.path.exists(LTMEM_FILE):
            with open(LTMEM_FILE) as f: return json.load(f)
    except: pass
    return {"facts": [], "topics": {}}

def ltmem_save(ltm):
    try:
        with open(LTMEM_FILE, 'w') as f:
            json.dump(ltm, f, indent=2, ensure_ascii=False)
    except: pass

def ltmem_store(ltm, key, value):
    """Store a fact or topic permanently."""
    ltm.setdefault("facts", [])
    ltm.setdefault("topics", {})
    ts = datetime.datetime.now().strftime("%d %b %Y %H:%M")
    # Store as topic
    ltm["topics"][key.lower().strip()] = {"value": value, "time": ts}
    # Also in facts list
    ltm["facts"].append({"key": key, "value": value, "time": ts})
    ltm["facts"] = ltm["facts"][-200:]  # keep last 200
    ltmem_save(ltm)
    return cg(f"✓ Yaad kar liya: {key} = {value}")

def ltmem_recall(ltm, query):
    """Search long-term memory for relevant facts."""
    q = query.lower()
    results = []
    for k, v in ltm.get("topics", {}).items():
        if q in k or k in q:
            results.append(f"{k}: {v['value']} ({v['time']})")
    # Also search facts
    for f in ltm.get("facts", []):
        if q in f.get("key","").lower() or q in f.get("value","").lower():
            entry = f"{f['key']}: {f['value']} ({f['time']})"
            if entry not in results:
                results.append(entry)
    return results[:8]

def ltmem_show(ltm):
    topics = ltm.get("topics", {})
    if not topics:
        return cy("Koi long-term memory nahi hai Boss.")
    out = f"\n{Y}╔══ 🧠 LONG-TERM MEMORY ({len(topics)} items) ══╗{RS}\n"
    for k, v in list(topics.items())[-15:]:
        if isinstance(v, dict):
            val = str(v.get('value', v.get('response', str(v))))[:50]
            t = v.get('time', '')
        else:
            val = str(v)[:50]
            t = ''
        out += f"  {C}{k}{RS}: {W}{val}{RS} {DM}({t}){RS}\n"
    out += f"{Y}╚{'═'*44}╝{RS}\n"
    return out

def ltmem_forget(ltm, key):
    k = key.lower().strip()
    if k in ltm.get("topics", {}):
        del ltm["topics"][k]
        ltmem_save(ltm)
        return cg(f"✓ Bhool gaya: {key}")
    return cy(f"Nahi mila: {key}")

def ltmem_get_context(ltm, query):
    """Get relevant LT memory for AI context."""
    results = ltmem_recall(ltm, query)
    if results:
        return "Long-term memory:\n" + "\n".join(results)
    return ""


# ─── FEATURE 2: Self-Correction ───────────────────────────────

def self_correct(question, first_answer, mem_history):
    """AI apna pehla jawab verify karke correct kare."""
    if not GROQ_KEY or not first_answer:
        return first_answer

    verify_prompt = (
        f'Mujhe ye question poocha gaya tha: "{question}"\n\n'
        f'Maine ye jawab diya:\n{first_answer}\n\n'
        f'Ab is jawab ko critically verify karo:\n'
        f'1. Koi factual error hai?\n'
        f'2. Koi important info miss hui?\n'
        f'3. Jawab clear aur complete hai?\n\n'
        f'Agar jawab sahi hai to sirf "SAHI HAI" likho.\n'
        f'Agar galat/incomplete hai to CORRECTED jawab do (Roman Hindi mein).'
    )
    verify_sys = (
        "Tu ek fact-checker AI hai. Pehle diye gaye jawab ko verify karta hai. "
        "Agar sahi hai to sirf 'SAHI HAI' likh. "
        "Agar galat/incomplete hai to corrected version Roman Hindi mein de."
    )
    corrected = ask_ai(verify_prompt, system_override=verify_sys, max_tokens=400)
    if not corrected:
        return first_answer
    if "SAHI HAI" in corrected.upper():
        return first_answer  # original was correct
    # Return corrected version
    corrected = clean_roman(corrected).strip()
    return corrected if len(corrected) > 20 else first_answer


# ─── FEATURE 3: Report Generator ──────────────────────────────

REPORTS_DIR = os.path.expanduser("~/Friday_Reports")

def generate_report(topic, content, rtype="txt"):
    """Generate aur save a report as TXT or basic HTML."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe     = re.sub(r'[^\w\s-]', '', topic)[:30].strip().replace(' ','_')
    filename = f"friday_{safe}_{ts}.{rtype}"
    filepath = os.path.join(REPORTS_DIR, filename)

    if rtype == "html":
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>Friday Report: {topic}</title>
<style>
  body{{font-family:Arial,sans-serif;max-width:800px;margin:40px auto;padding:20px;background:#1a1a2e;color:#eee;}}
  h1{{color:#e94560;border-bottom:2px solid #e94560;padding-bottom:10px;}}
  h2{{color:#0f3460;background:#16213e;padding:8px;border-radius:4px;}}
  pre{{background:#16213e;padding:15px;border-radius:8px;white-space:pre-wrap;color:#a8ff78;}}
  .meta{{color:#888;font-size:0.85em;margin-bottom:20px;}}
  .section{{background:#16213e;padding:15px;border-radius:8px;margin:10px 0;}}
</style></head><body>
<h1>📋 Friday Report: {topic}</h1>
<div class="meta">Generated: {datetime.datetime.now().strftime("%d %B %Y, %H:%M")} | By: FRIDAY AI</div>
<div class="section"><pre>{content}</pre></div>
</body></html>"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
    else:
        header = (
            f"{'='*60}\n"
            f"  FRIDAY AI REPORT\n"
            f"  Topic  : {topic}\n"
            f"  Date   : {datetime.datetime.now().strftime('%d %B %Y, %H:%M')}\n"
            f"{'='*60}\n\n"
        )
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(header + content)

    speak(f"Report save ho gayi Boss. {filename}")
    return cg(f"✓ Report saved:\n  {filepath}")

def report_list():
    """List all saved reports."""
    if not os.path.exists(REPORTS_DIR):
        return cy("Koi reports nahi hain Boss.")
    files = sorted(os.listdir(REPORTS_DIR), reverse=True)[:10]
    if not files:
        return cy("Koi reports nahi hain Boss.")
    out = f"\n{Y}╔══ 📋 SAVED REPORTS ══╗{RS}\n"
    for i, f in enumerate(files, 1):
        out += f"  {C}[{i}]{RS} {f}\n"
    out += f"  {DM}Path: {REPORTS_DIR}{RS}\n"
    out += f"{Y}╚{'═'*24}╝{RS}\n"
    return out


# ─── FEATURE: Expense Tracker ────────────────────────────────

EXPENSE_FILE = os.path.expanduser("~/.friday_expenses.json")

def expense_load():
    try:
        if os.path.exists(EXPENSE_FILE):
            with open(EXPENSE_FILE) as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except: pass
    return []

def expense_save(expenses):
    try:
        with open(EXPENSE_FILE, 'w') as f:
            json.dump(expenses, f, indent=2, ensure_ascii=False)
    except: pass

def expense_add(amount, category="general"):
    expenses = expense_load()
    now = datetime.datetime.now()
    entry = {
        "amount": float(amount),
        "category": category.strip(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "ts": now.isoformat()
    }
    expenses.append(entry)
    expense_save(expenses)
    return cg(f"✓ Expense added: ₹{amount} [{category}]")

def expense_show(period="today"):
    expenses = expense_load()
    if not expenses:
        return cy("Koi expenses nahi hain Boss. 'kharch <amount> <category>' se add karo.")

    now = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")
    week_start = (now - datetime.timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")

    if period == "today":
        filtered = [e for e in expenses if e["date"] == today]
        label = "Aaj Ka Kharcha"
    elif period == "week":
        filtered = [e for e in expenses if e["date"] >= week_start]
        label = "Is Hafte Ka Kharcha"
    elif period == "month":
        filtered = [e for e in expenses if e["date"].startswith(month)]
        label = "Is Mahine Ka Kharcha"
    else:
        filtered = expenses[-20:]
        label = "Recent Expenses"

    if not filtered:
        return cy(f"{label}: Koi entry nahi Boss.")

    total = sum(e["amount"] for e in filtered)
    out = f"\n{Y}╔══ 💰 {label} ══╗{RS}\n"
    for e in filtered[-15:]:
        out += f"  {C}{e['time']}{RS}  {W}₹{e['amount']:<8.0f}{RS}  {G}[{e['category']}]{RS}\n"
    out += f"{Y}{'─'*36}{RS}\n"
    out += f"  {BD}{W}Total: ₹{total:.0f}{RS}\n"
    out += f"{Y}╚{'═'*36}╝{RS}\n"
    return out

def expense_summary():
    expenses = expense_load()
    if not expenses:
        return cy("Koi expenses nahi hain Boss.")
    now = datetime.datetime.now()
    month = now.strftime("%Y-%m")
    monthly = [e for e in expenses if e["date"].startswith(month)]
    total = sum(e["amount"] for e in monthly)
    # Category breakdown
    cats = {}
    for e in monthly:
        cats[e["category"]] = cats.get(e["category"], 0) + e["amount"]
    out = f"\n{Y}╔══ 📊 Kharcha Summary ({now.strftime('%B %Y')}) ══╗{RS}\n"
    out += f"  {BD}{W}Total Kharcha: ₹{total:.0f}{RS}\n\n"
    for cat, amt in sorted(cats.items(), key=lambda x: -x[1]):
        pct = int(amt / total * 100) if total else 0
        bar = G + "█" * (pct // 5) + DM + "░" * (20 - pct // 5) + RS
        out += f"  {C}{cat:<14}{RS} {bar} {Y}₹{amt:.0f}{RS} ({pct}%)\n"
    out += f"{Y}╚{'═'*44}╝{RS}\n"
    return out

def expense_delete_last():
    expenses = expense_load()
    if not expenses:
        return cy("Koi expenses nahi hain Boss.")
    removed = expenses.pop()
    expense_save(expenses)
    return cg(f"✓ Last expense deleted: ₹{removed['amount']} [{removed['category']}]")

def expense_clear():
    expense_save([])
    return cg("✓ Saare expenses clear ho gaye Boss.")


# ─── FEATURE 4: Task Automation (Scheduled Tasks) ─────────────

TASKS_FILE = os.path.expanduser("~/.friday_tasks.json")
_task_thread = None

def tasks_load():
    try:
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE) as f: return json.load(f)
    except: pass
    return []

def tasks_save(tasks):
    try:
        with open(TASKS_FILE, 'w') as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)
    except: pass

def task_add(label, interval_min, command="notify"):
    """Add a recurring scheduled task."""
    tasks = tasks_load()
    task  = {
        "id":       int(time.time()),
        "label":    label,
        "interval": interval_min,
        "command":  command,
        "next_run": time.time() + interval_min * 60,
        "active":   True
    }
    tasks.append(task)
    tasks_save(tasks)
    display = f"{interval_min//60} hour" if interval_min >= 60 else f"{interval_min} min"
    return cg(f"✓ Task scheduled: '{label}' har {display}")

def task_list():
    tasks = tasks_load()
    if not tasks:
        return cy("Koi scheduled tasks nahi hain Boss.")
    out = f"\n{Y}╔══ ⚙️  SCHEDULED TASKS ══╗{RS}\n"
    for t in tasks:
        status = cg("● ON") if t.get("active") else cy("○ OFF")
        nxt    = datetime.datetime.fromtimestamp(t.get("next_run", 0)).strftime("%H:%M")
        iv  = t['interval']
        iv_str = f"{iv//60}h" if iv >= 60 else f"{iv}m"
        out += f"  {status} {C}[{t['id']}]{RS} {W}{t['label']}{RS} — {DM}every {iv_str} | next: {nxt}{RS}\n"
    out += f"{Y}╚{'═'*28}╝{RS}\n"
    return out

def task_delete(task_id):
    tasks = tasks_load()
    before = len(tasks)
    tasks  = [t for t in tasks if str(t.get("id")) != str(task_id)]
    if len(tasks) < before:
        tasks_save(tasks)
        return cg(f"✓ Task deleted: {task_id}")
    return cy(f"Task nahi mila: {task_id}")

def start_task_runner():
    """Background thread — check and run scheduled tasks."""
    def _runner():
        while True:
            try:
                tasks = tasks_load()
                now   = time.time()
                changed = False
                for t in tasks:
                    if not t.get("active"): continue
                    if now >= t.get("next_run", 0):
                        label = t["label"]
                        # Execute task
                        print(f"\n  {R}⚙️  AUTO TASK: {label}{RS}\n")
                        speak(f"Boss, scheduled task: {label}")
                        try:
                            subprocess.Popen(["termux-notification","--title",
                                              "Friday Task","--content", label])
                        except: pass
                        # Schedule next run
                        t["next_run"] = now + t["interval"] * 60
                        changed = True
                if changed:
                    tasks_save(tasks)
            except: pass
            time.sleep(30)  # check every 30 seconds
    global _task_thread
    _task_thread = threading.Thread(target=_runner, daemon=True)
    _task_thread.start()

# ─── FEATURE 5: Mood Tracker ──────────────────────────────────

MOOD_FILE = os.path.expanduser("~/.friday_mood.json")
MOOD_MAP = {
    "khush":"😊 Happy", "happy":"😊 Happy", "accha":"😊 Happy", "good":"😊 Happy",
    "bahut khush":"🤩 Amazing", "amazing":"🤩 Amazing", "mast":"🤩 Amazing", "great":"🤩 Amazing",
    "theek":"😐 Okay", "okay":"😐 Okay", "theek thak":"😐 Okay", "normal":"😐 Okay",
    "thaka":"😴 Tired", "tired":"😴 Tired", "neend":"😴 Tired", "sleepy":"😴 Tired",
    "bura":"😞 Sad", "sad":"😞 Sad", "dukhi":"😞 Sad", "udas":"😞 Sad",
    "gussa":"😠 Angry", "angry":"😠 Angry", "krodh":"😠 Angry",
    "anxious":"😰 Anxious", "tense":"😰 Anxious", "pareshan":"😰 Anxious",
    "excited":"🔥 Excited", "josh":"🔥 Excited", "pumped":"🔥 Excited",
}

def mood_load():
    try:
        if os.path.exists(MOOD_FILE):
            with open(MOOD_FILE) as f: return json.load(f)
    except: pass
    return []

def mood_save(moods): 
    try:
        with open(MOOD_FILE,'w') as f: json.dump(moods, f, indent=2, ensure_ascii=False)
    except: pass

def mood_add(mood_text):
    moods = mood_load()
    mood_key = mood_text.lower().strip()
    mood_label = MOOD_MAP.get(mood_key, f"💭 {mood_text.title()}")
    now = datetime.datetime.now()
    moods.append({
        "mood": mood_label, "raw": mood_text,
        "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M"),
        "day": now.strftime("%A")
    })
    mood_save(moods)
    responses = [
        f"Noted Boss! Aaj aap {mood_label} feel kar rahe ho.",
        f"Samajh gaya Boss. {mood_label} mood logged.",
        f"Aapka mood note ho gaya: {mood_label} Boss."
    ]
    return cg(random.choice(responses))

def mood_today():
    moods = mood_load()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    today_moods = [m for m in moods if m["date"] == today]
    if not today_moods:
        return cy("Aaj ka koi mood log nahi hai Boss. 'mood khush' se log karo.")
    out = f"\n{Y}╔══ 😊 Aaj Ka Mood Log ══╗{RS}\n"
    for m in today_moods:
        out += f"  {C}{m['time']}{RS}  {W}{m['mood']}{RS}\n"
    return out + f"{Y}╚{'═'*28}╝{RS}\n"

def mood_weekly():
    moods = mood_load()
    if not moods:
        return cy("Koi mood history nahi hai Boss.")
    now = datetime.datetime.now()
    week_start = (now - datetime.timedelta(days=6)).strftime("%Y-%m-%d")
    weekly = [m for m in moods if m["date"] >= week_start]
    if not weekly:
        return cy("Is hafte ka koi mood data nahi hai Boss.")
    # Count moods
    counts = {}
    for m in weekly:
        counts[m["mood"]] = counts.get(m["mood"], 0) + 1
    out = f"\n{Y}╔══ 📊 Weekly Mood Report ══╗{RS}\n"
    out += f"  {DM}Last 7 days — {len(weekly)} entries{RS}\n\n"
    for mood, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        bar = G + "█" * cnt + DM + "░" * (10 - min(cnt, 10)) + RS
        out += f"  {W}{mood:<18}{RS} {bar} {Y}×{cnt}{RS}\n"
    # Best/worst day
    day_map = {}
    for m in weekly:
        day_map.setdefault(m["day"], []).append(m["mood"])
    out += f"\n  {DM}Entries per day:{RS}\n"
    for day, ms in day_map.items():
        out += f"  {C}{day:<10}{RS} {', '.join(ms[:3])}\n"
    out += f"{Y}╚{'═'*36}╝{RS}\n"
    return out


# ─── FEATURE 6: Fitness Tracker ──────────────────────────────

FITNESS_FILE = os.path.expanduser("~/.friday_fitness.json")

def fitness_load():
    try:
        if os.path.exists(FITNESS_FILE):
            with open(FITNESS_FILE) as f:
                data = json.load(f)
                if isinstance(data, list): return data
    except: pass
    return []

def fitness_save(data):
    try:
        with open(FITNESS_FILE,'w') as f: json.dump(data, f, indent=2, ensure_ascii=False)
    except: pass

def fitness_log(entry_type, value, unit=""):
    records = fitness_load()
    now = datetime.datetime.now()
    records.append({
        "type": entry_type, "value": value, "unit": unit,
        "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M")
    })
    fitness_save(records)
    icons = {"steps":"👟","paani":"💧","water":"💧","exercise":"💪","weight":"⚖️",
             "workout":"💪","running":"🏃","pushups":"💪","situps":"🔥"}
    icon = icons.get(entry_type.lower(), "📊")
    return cg(f"✓ {icon} {entry_type.title()} logged: {value} {unit}")

def fitness_today():
    records = fitness_load()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    today_recs = [r for r in records if r["date"] == today]
    if not today_recs:
        return cy("Aaj ka koi fitness log nahi hai Boss.")
    out = f"\n{Y}╔══ 💪 Aaj Ka Fitness Log ══╗{RS}\n"
    # Group by type
    groups = {}
    for r in today_recs:
        groups.setdefault(r["type"], []).append(r)
    icons = {"steps":"👟","paani":"💧","water":"💧","exercise":"💪","weight":"⚖️",
             "workout":"💪","running":"🏃","pushups":"💪","situps":"🔥"}
    for etype, recs in groups.items():
        icon = icons.get(etype.lower(),"📊")
        total = sum(float(r["value"]) for r in recs)
        unit = recs[-1]["unit"]
        out += f"  {icon} {C}{etype.title():<12}{RS} {W}{total:.0f} {unit}{RS}\n"
    # Water goal check
    if "paani" in groups or "water" in groups:
        key = "paani" if "paani" in groups else "water"
        total_w = sum(float(r["value"]) for r in groups[key])
        goal = 8
        pct = min(int(total_w / goal * 100), 100)
        bar = (G if pct >= 100 else Y) + "█" * (pct // 10) + DM + "░" * (10 - pct // 10) + RS
        out += f"\n  {cc('💧 Water Goal:')} {bar} {total_w:.0f}/{goal} glasses\n"
    out += f"{Y}╚{'═'*32}╝{RS}\n"
    return out

def fitness_weekly():
    records = fitness_load()
    now = datetime.datetime.now()
    week_start = (now - datetime.timedelta(days=6)).strftime("%Y-%m-%d")
    weekly = [r for r in records if r["date"] >= week_start]
    if not weekly:
        return cy("Is hafte ka koi fitness data nahi hai Boss.")
    out = f"\n{Y}╔══ 📊 Weekly Fitness Summary ══╗{RS}\n"
    groups = {}
    for r in weekly:
        groups.setdefault(r["type"], []).append(float(r["value"]))
    for etype, vals in groups.items():
        icon = "👟" if "step" in etype else "💧" if "paan" in etype or "water" in etype else "💪"
        out += f"  {icon} {C}{etype.title():<12}{RS} Total: {W}{sum(vals):.0f}{RS}  Avg/day: {G}{sum(vals)/7:.0f}{RS}\n"
    out += f"{Y}╚{'═'*36}╝{RS}\n"
    return out


# ─── FEATURE 7: Birthday / Event Reminder ─────────────────────

EVENTS_FILE = os.path.expanduser("~/.friday_events.json")

def events_load():
    try:
        if os.path.exists(EVENTS_FILE):
            with open(EVENTS_FILE) as f:
                data = json.load(f)
                if isinstance(data, list): return data
    except: pass
    return []

def events_save(evs):
    try:
        with open(EVENTS_FILE,'w') as f: json.dump(evs, f, indent=2, ensure_ascii=False)
    except: pass

def event_add(label, date_str, etype="event"):
    """Add birthday or event. date_str: DD-MM or DD-MM-YYYY"""
    evs = events_load()
    # Normalize date
    parts = date_str.strip().replace("/","-").split("-")
    if len(parts) == 2:
        day, month = parts[0].zfill(2), parts[1].zfill(2)
        year = ""
    elif len(parts) == 3:
        day, month, year = parts[0].zfill(2), parts[1].zfill(2), parts[2]
    else:
        return cy("Date format galat hai Boss. Use: DD-MM ya DD-MM-YYYY")
    date_key = f"{day}-{month}" + (f"-{year}" if year else "")
    evs.append({"label": label, "date": date_key, "day": day, "month": month,
                "year": year, "type": etype})
    events_save(evs)
    icon = "🎂" if etype == "birthday" else "📅"
    return cg(f"✓ {icon} Saved: '{label}' on {date_key}")

def events_check_today():
    """Check if any events/birthdays today — called on startup."""
    evs = events_load()
    now = datetime.datetime.now()
    today_day = now.strftime("%d")
    today_month = now.strftime("%m")
    alerts = []
    for e in evs:
        if e["day"] == today_day and e["month"] == today_month:
            icon = "🎂" if e["type"] == "birthday" else "📅"
            age = ""
            if e["type"] == "birthday" and e.get("year"):
                try: age = f" ({now.year - int(e['year'])} saal)"
                except: pass
            alerts.append(f"{icon} {e['label']}{age}")
    return alerts

def events_upcoming(days=7):
    evs = events_load()
    if not evs:
        return cy("Koi events saved nahi hain Boss. 'event add' se add karo.")
    now = datetime.datetime.now()
    out = f"\n{Y}╔══ 📅 Upcoming Events (next {days} days) ══╗{RS}\n"
    found = False
    for i in range(days + 1):
        check = now + datetime.timedelta(days=i)
        d, m = check.strftime("%d"), check.strftime("%m")
        for e in evs:
            if e["day"] == d and e["month"] == m:
                icon = "🎂" if e["type"] == "birthday" else "📅"
                label = "Aaj! 🎉" if i == 0 else f"{i} din mein"
                out += f"  {icon} {W}{e['label']}{RS}  {G}{check.strftime('%d %b')}{RS}  {C}({label}){RS}\n"
                found = True
    if not found:
        out += f"  {DM}Koi upcoming event nahi is period mein.{RS}\n"
    out += f"{Y}╚{'═'*44}╝{RS}\n"
    return out

def events_list():
    evs = events_load()
    if not evs:
        return cy("Koi events saved nahi hain Boss.")
    out = f"\n{Y}╔══ 📅 All Events & Birthdays ══╗{RS}\n"
    for i, e in enumerate(evs, 1):
        icon = "🎂" if e["type"] == "birthday" else "📅"
        out += f"  {C}[{i}]{RS} {icon} {W}{e['label']}{RS}  {DM}{e['date']}{RS}\n"
    out += f"{Y}╚{'═'*34}╝{RS}\n"
    return out

def event_delete(idx):
    evs = events_load()
    if 0 <= idx < len(evs):
        removed = evs.pop(idx)
        events_save(evs)
        return cg(f"✓ Deleted: {removed['label']}")
    return cy("Invalid number Boss.")


# ─── FEATURE 8: Auto Battery Alert ────────────────────────────


# ─── FEATURE: Smart Fact Auto-Learner ────────────────────────
FACT_KEYWORDS = [
    (r"mujhe\s+(.+?)\s+pasand hai", "pasand"),
    (r"mera\s+(.+?)\s+hai\s+(.+)", "info"),
    (r"main\s+(.+?)\s+mein rehta hoon", "location"),
    (r"meri\s+umar\s+(\d+)", "umar"),
    (r"mera\s+naam\s+(\w+)", "naam"),
    (r"mujhe\s+(.+?)\s+se nafrat hai", "nafrat"),
    (r"mera favourite\s+(.+?)\s+hai\s+(.+)", "favourite"),
]

def auto_learn_facts(user_input, ltm):
    """User ki baat se facts auto-extract karo."""
    learned = []
    text = user_input.lower().strip()
    for pattern, fact_type in FACT_KEYWORDS:
        m = re.search(pattern, text)
        if m:
            if fact_type == "pasand":
                key = f"pasand_{m.group(1)[:20]}"
                val = f"Boss ko {m.group(1)} pasand hai"
            elif fact_type == "nafrat":
                key = f"nafrat_{m.group(1)[:20]}"
                val = f"Boss ko {m.group(1)} pasand nahi"
            elif fact_type == "favourite":
                key = f"fav_{m.group(1)[:20]}"
                val = f"Boss ka favourite {m.group(1)}: {m.group(2)}"
            elif fact_type == "umar":
                key = "umar"
                val = f"Boss ki umar {m.group(1)} saal hai"
            elif fact_type == "naam":
                key = "naam"
                val = f"Boss ka naam {m.group(1)} hai"
            else:
                key = f"fact_{text[:20]}"
                val = user_input[:80]
            ltmem_store(ltm, key, val)
            learned.append(val)
    return learned


# ─── FEATURE: Hardware Guardian (Self-Healing Mode) ──────────
_hw_alert_sent = {"heat": False, "ram": False}

def start_hardware_guardian():
    """Phone temperature aur RAM monitor karo — self-healing mode."""
    def _guardian():
        while True:
            try:
                # ── Temperature check ──
                temp = None
                try:
                    r = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=5)
                    d = json.loads(r.stdout)
                    temp = d.get("temperature", None)
                except: pass

                if temp and temp >= 40 and not _hw_alert_sent["heat"]:
                    msg = f"Boss! System heat ho raha hai — temperature {temp:.0f} degree hai! Main background apps kill kar rahi hoon."
                    print(f"\n  \033[91m🌡️  HEAT ALERT: {temp:.0f}°C — Self-healing mode activated!\033[0m\n")
                    speak(msg)
                    try: subprocess.Popen(["termux-notification","--title","🌡️ FRIDAY - Heat Alert",
                                          "--content", f"Phone {temp:.0f}°C! Cooling down..."],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except: pass
                    # Kill background processes
                    try: subprocess.run(["am", "kill-all"], capture_output=True, timeout=3)
                    except: pass
                    _hw_alert_sent["heat"] = True
                elif temp and temp < 37:
                    _hw_alert_sent["heat"] = False

                # ── RAM check ──
                try:
                    r2 = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=5)
                    lines = r2.stdout.strip().split("\n")
                    for line in lines:
                        if line.startswith("Mem:"):
                            parts = line.split()
                            total = int(parts[1])
                            used  = int(parts[2])
                            pct   = (used / total) * 100
                            if pct >= 90 and not _hw_alert_sent["ram"]:
                                msg = f"Boss! RAM {pct:.0f} percent full ho gayi hai! Main memory clean kar rahi hoon."
                                print(f"\n  \033[91m💾 RAM ALERT: {pct:.0f}% used — Cleaning memory!\033[0m\n")
                                speak(msg)
                                try: subprocess.Popen(["termux-notification","--title","💾 FRIDAY - RAM Alert",
                                                      "--content", f"RAM {pct:.0f}% full!"],
                                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                except: pass
                                _hw_alert_sent["ram"] = True
                            elif pct < 80:
                                _hw_alert_sent["ram"] = False
                            break
                except: pass

            except: pass
            time.sleep(60)  # Har minute check

    t = threading.Thread(target=_guardian, daemon=True)
    t.start()


# ─── FEATURE: Smart Geofencing (Home/Office Auto-Detect) ─────
GEOFENCE_FILE = os.path.expanduser("~/.friday_geofence.json")
_geofence_state = {"home": "outside", "office": "outside"}

def geofence_load():
    try:
        if os.path.exists(GEOFENCE_FILE):
            with open(GEOFENCE_FILE) as f: return json.load(f)
    except: pass
    return {"locations": {}}

def geofence_save(data):
    try:
        with open(GEOFENCE_FILE, "w") as f: json.dump(data, f, indent=2)
    except: pass

def geofence_set(name, radius=100):
    """Current location ko home/office set karo."""
    loc = get_gps_location()
    if not loc:
        return cy("GPS nahi mila Boss! Location on karo.")
    data = geofence_load()
    data["locations"][name.lower()] = {
        "lat": loc.get("latitude", 0),
        "lon": loc.get("longitude", 0),
        "radius_m": radius,
        "name": name
    }
    geofence_save(data)
    return cg(f"✅ '{name}' set ho gaya! {radius}m radius pe FRIDAY alert karegi.")

def start_geofence_monitor():
    """Background mein location monitor karo."""
    import math
    def _monitor():
        while True:
            try:
                data = geofence_load()
                locs = data.get("locations", {})
                if not locs:
                    time.sleep(300)
                    continue
                loc = get_gps_location(force_refresh=True)
                if not loc:
                    time.sleep(120)
                    continue
                lat2 = loc.get("latitude", 0)
                lon2 = loc.get("longitude", 0)
                for name, place in locs.items():
                    R = 6371000
                    dlat = math.radians(lat2 - place["lat"])
                    dlon = math.radians(lon2 - place["lon"])
                    a = math.sin(dlat/2)**2 + math.cos(math.radians(place["lat"])) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
                    dist = R * 2 * math.asin(math.sqrt(a))
                    inside = dist <= place["radius_m"]
                    prev = _geofence_state.get(name, "outside")
                    if inside and prev == "outside":
                        _geofence_state[name] = "inside"
                        display = place.get("name", name)
                        if "home" in name:
                            msg = f"Welcome home Boss MIRAZ! Ghar aa gaye hain. Koi kaam ho toh bataiye."
                        elif "office" in name:
                            msg = f"Office aa gaye Boss! Kaam shuru karen? Daily briefing chahiye?"
                        else:
                            msg = f"Boss! {display} area mein aa gaye hain!"
                        print(f"\n  \033[92m🏠 GEOFENCE: {display} — ARRIVED!\033[0m\n")
                        speak(msg)
                    elif not inside and prev == "inside":
                        _geofence_state[name] = "outside"
                        display = place.get("name", name)
                        msg = f"Boss {display} se nikal gaye. Take care!"
                        print(f"\n  \033[93m🚶 GEOFENCE: {display} — LEFT!\033[0m\n")
                        speak(msg)
            except: pass
            time.sleep(120)  # Har 2 minute check
    t = threading.Thread(target=_monitor, daemon=True)
    t.start()

_battery_alert_sent = {"low": False, "critical": False}

def start_battery_monitor():
    """Background thread — auto alert when battery low."""
    def _monitor():
        while True:
            try:
                r = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=5)
                d = json.loads(r.stdout)
                pct = d.get("percentage", 100)
                status = d.get("status", "")
                charging = status in ["CHARGING", "FULL"]

                if charging:
                    _battery_alert_sent["low"] = False
                    _battery_alert_sent["critical"] = False
                elif pct <= 10 and not _battery_alert_sent["critical"]:
                    msg = f"Boss! Battery critical — sirf {pct}% bachi hai! Charger lagao abhi!"
                    print(f"\n  {R}🔋 CRITICAL BATTERY ALERT: {pct}%{RS}\n")
                    speak(msg)
                    try: subprocess.Popen(["termux-notification","--title","⚠️ FRIDAY - Battery Critical",
                                          "--content", f"Battery {pct}% — Charger lagao!"])
                    except: pass
                    _battery_alert_sent["critical"] = True
                elif pct <= 20 and not _battery_alert_sent["low"]:
                    msg = f"Boss, battery {pct}% hai. Charger laga lo please."
                    print(f"\n  {Y}🔋 Battery Alert: {pct}%{RS}\n")
                    speak(msg)
                    try: subprocess.Popen(["termux-notification","--title","🔋 FRIDAY - Battery Low",
                                          "--content", f"Battery {pct}% — Charger lagao Boss"])
                    except: pass
                    _battery_alert_sent["low"] = True
            except: pass
            time.sleep(120)  # check every 2 minutes
    t = threading.Thread(target=_monitor, daemon=True)
    t.start()


# ─── FEATURE 9: Smart Daily Briefing ─────────────────────────

def daily_briefing():
    """Subah ek command mein sab kuch — JARVIS style."""
    now = datetime.datetime.now()
    hour = now.hour
    if hour < 12: greeting = "Good Morning"
    elif hour < 17: greeting = "Good Afternoon"
    else: greeting = "Good Evening"

    out = f"\n{Y}╔{'═'*58}╗{RS}\n"
    out += f"{Y}║{RS}{BD}{C}  🤖 FRIDAY DAILY BRIEFING — {greeting} Boss!{'':>8}{RS}{Y}║{RS}\n"
    out += f"{Y}║{RS}  {DM}{now.strftime('%A, %d %B %Y  |  %H:%M')}{RS}{' '*20}{Y}║{RS}\n"
    out += f"{Y}╠{'═'*58}╣{RS}\n"

    # ── Birthday/Events today ──
    today_events = events_check_today()
    if today_events:
        out += f"{Y}║{RS}  {R}🎉 Aaj Ka Khaas Din:{RS}\n"
        for ev in today_events:
            out += f"{Y}║{RS}     {W}{ev}{RS}\n"
        out += f"{Y}╠{'═'*58}╣{RS}\n"

    # ── Battery ──
    try:
        r = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=4)
        d = json.loads(r.stdout)
        pct = d.get("percentage", 0)
        charging = "⚡ Charging" if d.get("status") == "CHARGING" else "🔋 Battery"
        bcolor = G if pct > 50 else (Y if pct > 20 else R)
        out += f"{Y}║{RS}  {bcolor}{charging}: {pct}%{RS}\n"
    except: pass

    # ── Aaj ka mood (agar koi ho) ──
    mood_recs = [m for m in mood_load() if m["date"] == now.strftime("%Y-%m-%d")]
    if mood_recs:
        last_mood = mood_recs[-1]["mood"]
        out += f"{Y}║{RS}  😊 Last Mood: {W}{last_mood}{RS}\n"

    out += f"{Y}╠{'═'*58}╣{RS}\n"

    # ── Aaj ke tasks ──
    tasks = [t for t in tasks_load() if t.get("active")]
    if tasks:
        out += f"{Y}║{RS}  {C}⚙️  Active Tasks ({len(tasks)}):{RS}\n"
        for t in tasks[:3]:
            iv = t['interval']
            iv_str = f"{iv//60}h" if iv >= 60 else f"{iv}m"
            out += f"{Y}║{RS}     {DM}• {t['label']} (har {iv_str}){RS}\n"
        if len(tasks) > 3:
            out += f"{Y}║{RS}     {DM}...aur {len(tasks)-3} tasks{RS}\n"
        out += f"{Y}╠{'═'*58}╣{RS}\n"

    # ── Aaj ka kharcha ──
    expenses = expense_load()
    today_exp = [e for e in expenses if e["date"] == now.strftime("%Y-%m-%d")]
    if today_exp:
        total_exp = sum(e["amount"] for e in today_exp)
        out += f"{Y}║{RS}  {G}💰 Aaj Ka Kharcha: ₹{total_exp:.0f} ({len(today_exp)} entries){RS}\n"
        out += f"{Y}╠{'═'*58}╣{RS}\n"

    # ── Upcoming events ──
    evs = events_load()
    upcoming = []
    for i in range(1, 8):
        check = now + datetime.timedelta(days=i)
        d2, m2 = check.strftime("%d"), check.strftime("%m")
        for e in evs:
            if e["day"] == d2 and e["month"] == m2:
                icon = "🎂" if e["type"] == "birthday" else "📅"
                upcoming.append(f"{icon} {e['label']} — {i} din mein")
    if upcoming:
        out += f"{Y}║{RS}  {M}📅 Upcoming:{RS}\n"
        for u in upcoming[:3]:
            out += f"{Y}║{RS}     {DM}{u}{RS}\n"
        out += f"{Y}╠{'═'*58}╣{RS}\n"

    out += f"{Y}║{RS}  {DM}💡 Tip: 'weather <city>' | 'news' | 'kharch' | 'mood'{RS}\n"
    out += f"{Y}╚{'═'*58}╝{RS}\n"

    speak(f"{greeting} Boss! Daily briefing ready hai.")
    return out




# ─── FEATURE 10: Search History ──────────────────────────────

SEARCH_HISTORY_FILE = os.path.expanduser("~/.friday_search_history.json")

def search_history_load():
    try:
        if os.path.exists(SEARCH_HISTORY_FILE):
            with open(SEARCH_HISTORY_FILE) as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except: pass
    return []

def search_history_save(hist):
    try:
        with open(SEARCH_HISTORY_FILE, 'w') as f:
            json.dump(hist[-200:], f, indent=2, ensure_ascii=False)
    except: pass

def search_history_add(query, stype="search"):
    hist = search_history_load()
    now = datetime.datetime.now()
    hist.append({
        "query": query, "type": stype,
        "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M")
    })
    search_history_save(hist)

def search_history_show(limit=20):
    hist = search_history_load()
    if not hist:
        return cy("Koi search history nahi hai Boss.")
    out = f"\n{Y}╔══ 🔍 SEARCH HISTORY (last {min(limit,len(hist))}) ══╗{RS}\n"
    for h in hist[-limit:]:
        icon = "🌐" if h["type"]=="search" else "🎬" if h["type"]=="youtube" else "🦆"
        out += f"  {icon} {C}{h['time']}{RS}  {W}{h['query'][:50]}{RS}\n"
    out += f"{Y}╚{'═'*44}╝{RS}\n"
    return out

def search_history_patterns():
    hist = search_history_load()
    if not hist:
        return cy("Koi search history nahi hai Boss.")
    # Count top queries
    counts = {}
    types = {}
    for h in hist:
        q = h["query"].lower()
        counts[q] = counts.get(q, 0) + 1
        types[h["type"]] = types.get(h["type"], 0) + 1
    top = sorted(counts.items(), key=lambda x: -x[1])[:8]
    out = f"\n{Y}╔══ 📊 SEARCH PATTERNS ══╗{RS}\n"
    out += f"  {C}Total searches: {W}{len(hist)}{RS}\n\n"
    out += f"  {M}Top Searches:{RS}\n"
    for q, cnt in top:
        bar = G + "█" * min(cnt, 10) + DM + "░" * (10 - min(cnt, 10)) + RS
        out += f"  {bar} {W}{q[:35]}{RS} {Y}×{cnt}{RS}\n"
    out += f"\n  {M}By Type:{RS}\n"
    for t, cnt in types.items():
        out += f"  {C}{t:<12}{RS} {W}{cnt} searches{RS}\n"
    out += f"{Y}╚{'═'*44}╝{RS}\n"
    return out

def search_history_clear():
    search_history_save([])
    return cg("✓ Search history clear ho gayi Boss.")


# ─── FEATURE 11: Pinned Notes ─────────────────────────────────

PINNED_FILE = os.path.expanduser("~/.friday_pinned.json")

def pinned_load():
    try:
        if os.path.exists(PINNED_FILE):
            with open(PINNED_FILE) as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except: pass
    return []

def pinned_save(pins):
    try:
        with open(PINNED_FILE, 'w') as f:
            json.dump(pins, f, indent=2, ensure_ascii=False)
    except: pass

def pin_add(text):
    pins = pinned_load()
    now = datetime.datetime.now()
    pins.append({
        "text": text,
        "time": now.strftime("%d %b %Y, %H:%M"),
        "id": int(time.time())
    })
    pinned_save(pins)
    return cg(f"📌 Pinned: {text}")

def pin_list():
    pins = pinned_load()
    if not pins:
        return cy("Koi pinned notes nahi hain Boss. 'pin <text>' se add karo.")
    out = f"\n{Y}╔══ 📌 PINNED NOTES ({len(pins)}) ══╗{RS}\n"
    for i, p in enumerate(pins, 1):
        out += f"  {R}📌 [{i}]{RS} {W}{p['text']}{RS}\n"
        out += f"       {DM}{p['time']}{RS}\n"
    out += f"{Y}╚{'═'*36}╝{RS}\n"
    return out

def pin_delete(idx):
    pins = pinned_load()
    if 0 <= idx < len(pins):
        removed = pins.pop(idx)
        pinned_save(pins)
        return cg(f"✓ Pin removed: {removed['text'][:40]}")
    return cy("Invalid pin number Boss.")

def pin_clear():
    pinned_save([])
    return cg("✓ Saare pins clear ho gaye Boss.")


# ─── FEATURE 12: Daily Goals ──────────────────────────────────

GOALS_FILE = os.path.expanduser("~/.friday_goals.json")

def goals_load():
    try:
        if os.path.exists(GOALS_FILE):
            with open(GOALS_FILE) as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except: pass
    return []

def goals_save(goals):
    try:
        with open(GOALS_FILE, 'w') as f:
            json.dump(goals, f, indent=2, ensure_ascii=False)
    except: pass

def goal_add(text):
    goals = goals_load()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    goals.append({
        "text": text, "done": False,
        "date": today,
        "time": datetime.datetime.now().strftime("%H:%M")
    })
    goals_save(goals)
    return cg(f"🎯 Goal set: {text}")

def goal_done(idx):
    goals = goals_load()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    today_goals = [g for g in goals if g["date"] == today]
    if 0 <= idx < len(today_goals):
        # Find actual index
        actual_idx = goals.index(today_goals[idx])
        goals[actual_idx]["done"] = True
        goals_save(goals)
        return cg(f"✅ Goal complete: {today_goals[idx]['text']}")
    return cy("Invalid goal number Boss.")

def goals_today():
    goals = goals_load()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    today_goals = [g for g in goals if g["date"] == today]
    if not today_goals:
        return cy("Aaj koi goals nahi hain Boss. 'goal add <text>' se set karo.")
    done = sum(1 for g in today_goals if g["done"])
    total = len(today_goals)
    pct = int(done / total * 100) if total else 0
    bar = (G if pct == 100 else Y if pct >= 50 else R) + "█" * (pct // 10) + DM + "░" * (10 - pct // 10) + RS
    out = f"\n{Y}╔══ 🎯 AAJKE GOALS ({done}/{total} done) ══╗{RS}\n"
    out += f"  Progress: {bar} {pct}%\n\n"
    for i, g in enumerate(today_goals, 1):
        status = f"{G}✅{RS}" if g["done"] else f"{R}⬜{RS}"
        text_style = f"{DM}{g['text']}{RS}" if g["done"] else f"{W}{g['text']}{RS}"
        out += f"  {status} {C}[{i}]{RS} {text_style}\n"
    if pct == 100:
        out += f"\n  {G}🎉 Sab goals complete! Boss you're on fire!{RS}\n"
    out += f"{Y}╚{'═'*40}╝{RS}\n"
    return out

def goals_clear_today():
    goals = goals_load()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    goals = [g for g in goals if g["date"] != today]
    goals_save(goals)
    return cg("✓ Aaj ke goals clear ho gaye Boss.")


# ─── FEATURE 13: Sleep Tracker ────────────────────────────────

SLEEP_FILE = os.path.expanduser("~/.friday_sleep.json")

def sleep_load():
    try:
        if os.path.exists(SLEEP_FILE):
            with open(SLEEP_FILE) as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except: pass
    return []

def sleep_save(data):
    try:
        with open(SLEEP_FILE, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except: pass

def sleep_log(action):
    records = sleep_load()
    now = datetime.datetime.now()
    ts = now.isoformat()
    if action == "so gaya":
        records.append({
            "sleep": ts, "wake": None,
            "sleep_date": now.strftime("%Y-%m-%d"),
            "sleep_time": now.strftime("%H:%M"),
            "duration": None
        })
        sleep_save(records)
        return cg(f"🌙 Sleep logged: {now.strftime('%H:%M')} — Good night Boss!")
    elif action == "uth gaya":
        # Find last unclosed sleep
        for r in reversed(records):
            if r["wake"] is None:
                r["wake"] = ts
                r["wake_time"] = now.strftime("%H:%M")
                r["wake_date"] = now.strftime("%Y-%m-%d")
                # Calculate duration
                try:
                    sleep_dt = datetime.datetime.fromisoformat(r["sleep"])
                    dur = now - sleep_dt
                    hours = dur.seconds // 3600
                    mins = (dur.seconds % 3600) // 60
                    r["duration"] = f"{hours}h {mins}m"
                    sleep_save(records)
                    quality = "😴 Kam" if hours < 6 else ("😊 Acchi" if hours <= 9 else "😪 Zyada")
                    return cg(f"☀️ Wake logged! Neend: {r['duration']} — {quality}")
                except:
                    sleep_save(records)
                    return cg(f"☀️ Wake logged: {now.strftime('%H:%M')}")
        return cy("Pehle 'so gaya' log karo Boss.")
    return cy("Usage: 'so gaya' ya 'uth gaya'")

def sleep_history():
    records = sleep_load()
    if not records:
        return cy("Koi sleep data nahi hai Boss. 'so gaya' se log karo.")
    completed = [r for r in records if r["wake"]][-7:]
    if not completed:
        return cy("Koi completed sleep records nahi hain Boss.")
    out = f"\n{Y}╔══ 🌙 SLEEP HISTORY (last 7) ══╗{RS}\n"
    for r in completed:
        dur = r.get("duration", "?")
        out += f"  {C}{r['sleep_date']}{RS}  {DM}{r['sleep_time']} → {r.get('wake_time','?')}{RS}  {W}{dur}{RS}\n"
    # Average
    durations = []
    for r in completed:
        if r.get("duration"):
            try:
                h, m = r["duration"].replace("h","").replace("m","").split()
                durations.append(int(h) * 60 + int(m))
            except: pass
    if durations:
        avg = sum(durations) // len(durations)
        out += f"\n  {M}Avg Sleep: {W}{avg//60}h {avg%60}m{RS}\n"
    out += f"{Y}╚{'═'*36}╝{RS}\n"
    return out


# ─── FEATURE 14: Auto Suggestions ────────────────────────────

_suggestion_thread = None

def start_auto_suggestions():
    """Background thread — smart suggestions based on time and data."""
    def _suggester():
        last_suggestion = {"hour": -1}
        while True:
            try:
                now = datetime.datetime.now()
                hour = now.hour
                # Only one suggestion per hour
                if hour != last_suggestion["hour"]:
                    suggestions = []

                    # Water reminder every 2 hours (8am-10pm)
                    if 8 <= hour <= 22 and hour % 2 == 0:
                        fitness = fitness_load()
                        today = now.strftime("%Y-%m-%d")
                        water_today = sum(float(r["value"]) for r in fitness
                                         if r["date"] == today and r["type"] in ["paani","water"])
                        if water_today < 6:
                            suggestions.append(f"💧 Boss, aaj sirf {water_today:.0f} glasses paani piya hai. Ek glass aur piyo!")

                    # Morning goal reminder
                    if hour == 8:
                        goals = goals_load()
                        today_goals = [g for g in goals if g["date"] == now.strftime("%Y-%m-%d")]
                        if not today_goals:
                            suggestions.append("🎯 Good morning Boss! Aaj ke goals set karo — 'goal add <text>'")

                    # Evening expense reminder
                    if hour == 21:
                        expenses = expense_load()
                        today_exp = [e for e in expenses if e["date"] == now.strftime("%Y-%m-%d")]
                        if not today_exp:
                            suggestions.append("💰 Boss, aaj ka kharcha log nahi kiya. 'kharch <amount> <category>' se add karo!")

                    # Break reminder (work hours)
                    if hour in [11, 15, 17]:
                        suggestions.append("☕ Boss, thodi der ka break lo. Aankhen aur dimag dono rest maangti hain!")

                    # Sleep reminder
                    if hour == 23:
                        suggestions.append("🌙 Boss, raat ke 11 baj gaye. Sone ka time ho gaya! 'so gaya' log karna mat bhoolo.")

                    # Mood check evening
                    if hour == 20:
                        moods = mood_load()
                        today_mood = [m for m in moods if m["date"] == now.strftime("%Y-%m-%d")]
                        if not today_mood:
                            suggestions.append("😊 Boss, aaj ka mood log karo — 'mood khush/thaka/accha' etc.")

                    # Behavior-based suggestion
                    try:
                        bsug = behavior_suggest(ltmem_load())
                        if bsug: suggestions.append(f"💡 {bsug}")
                    except: pass

                    for s in suggestions[:1]:  # Max 1 suggestion at a time
                        print(f"\n  {M}💡 FRIDAY: {s}{RS}\n")
                        speak(s[:150])
                        last_suggestion["hour"] = hour

            except: pass
            time.sleep(1800)  # check every 30 minutes

    global _suggestion_thread
    _suggestion_thread = threading.Thread(target=_suggester, daemon=True)
    _suggestion_thread.start()


# ─── FEATURE 15: Weekly Life Report ──────────────────────────

def weekly_life_report():
    """Ek comprehensive weekly report — mood + fitness + kharcha + goals + sleep."""
    now = datetime.datetime.now()
    week_start = (now - datetime.timedelta(days=6)).strftime("%Y-%m-%d")
    today = now.strftime("%Y-%m-%d")

    out = f"\n{Y}╔{'═'*60}╗{RS}\n"
    out += f"{Y}║{RS}{BD}{C}{'  📊 FRIDAY WEEKLY LIFE REPORT':^60}{RS}{Y}║{RS}\n"
    out += f"{Y}║{RS}  {DM}{(now - datetime.timedelta(days=6)).strftime('%d %b')} → {now.strftime('%d %b %Y')}{RS}{'':>38}{Y}║{RS}\n"
    out += f"{Y}╠{'═'*60}╣{RS}\n"

    # ── MOOD ──
    moods = [m for m in mood_load() if m["date"] >= week_start]
    if moods:
        counts = {}
        for m in moods:
            counts[m["mood"]] = counts.get(m["mood"], 0) + 1
        top_mood = max(counts, key=counts.get)
        out += f"{Y}║{RS}  {M}😊 MOOD ({len(moods)} entries){RS}\n"
        for mood, cnt in sorted(counts.items(), key=lambda x: -x[1])[:3]:
            out += f"{Y}║{RS}    {W}{mood:<20}{RS} {G}×{cnt}{RS}\n"
        out += f"{Y}║{RS}  {DM}Most felt: {top_mood}{RS}\n"
        out += f"{Y}╠{'═'*60}╣{RS}\n"

    # ── FITNESS ──
    fitness = [r for r in fitness_load() if r["date"] >= week_start]
    if fitness:
        out += f"{Y}║{RS}  {G}💪 FITNESS{RS}\n"
        groups = {}
        for r in fitness:
            groups.setdefault(r["type"], []).append(float(r["value"]))
        for etype, vals in groups.items():
            icon = "👟" if "step" in etype else "💧" if "paan" in etype or "water" in etype else "💪"
            out += f"{Y}║{RS}    {icon} {C}{etype.title():<12}{RS} Total: {W}{sum(vals):.0f}{RS}  Avg/day: {G}{sum(vals)/7:.1f}{RS}\n"
        out += f"{Y}╠{'═'*60}╣{RS}\n"

    # ── SLEEP ──
    sleep_recs = [r for r in sleep_load() if r.get("sleep_date","") >= week_start and r.get("duration")]
    if sleep_recs:
        durations = []
        for r in sleep_recs:
            try:
                h, m = r["duration"].replace("h","").replace("m","").split()
                durations.append(int(h) * 60 + int(m))
            except: pass
        if durations:
            avg = sum(durations) // len(durations)
            out += f"{Y}║{RS}  {C}🌙 SLEEP ({len(sleep_recs)} nights){RS}\n"
            out += f"{Y}║{RS}    Avg: {W}{avg//60}h {avg%60}m{RS}  Best: {G}{max(durations)//60}h{RS}  Worst: {R}{min(durations)//60}h{RS}\n"
            out += f"{Y}╠{'═'*60}╣{RS}\n"

    # ── EXPENSE ──
    expenses = [e for e in expense_load() if e["date"] >= week_start]
    if expenses:
        total = sum(e["amount"] for e in expenses)
        cats = {}
        for e in expenses:
            cats[e["category"]] = cats.get(e["category"], 0) + e["amount"]
        out += f"{Y}║{RS}  {Y}💰 KHARCHA — Total: ₹{total:.0f}{RS}\n"
        for cat, amt in sorted(cats.items(), key=lambda x: -x[1])[:4]:
            pct = int(amt/total*100) if total else 0
            out += f"{Y}║{RS}    {C}{cat:<14}{RS} ₹{W}{amt:.0f}{RS} ({pct}%)\n"
        out += f"{Y}╠{'═'*60}╣{RS}\n"

    # ── GOALS ──
    all_goals = [g for g in goals_load() if g["date"] >= week_start]
    if all_goals:
        done = sum(1 for g in all_goals if g["done"])
        total_g = len(all_goals)
        pct = int(done/total_g*100) if total_g else 0
        bar = (G if pct>=80 else Y if pct>=50 else R)+"█"*(pct//10)+DM+"░"*(10-pct//10)+RS
        out += f"{Y}║{RS}  {R}🎯 GOALS — {done}/{total_g} complete{RS}\n"
        out += f"{Y}║{RS}    {bar} {pct}%\n"
        out += f"{Y}╠{'═'*60}╣{RS}\n"

    # ── SUMMARY ──
    out += f"{Y}║{RS}  {DM}💡 'briefing' for today's status | 'help' for all commands{RS}\n"
    out += f"{Y}╚{'═'*60}╝{RS}\n"

    # Save as file too
    try:
        os.makedirs(os.path.expanduser("~/Friday_Reports"), exist_ok=True)
        fname = os.path.expanduser(f"~/Friday_Reports/weekly_{now.strftime('%Y%m%d')}.txt")
        clean = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', out)
        with open(fname, 'w') as f:
            f.write(clean)
        out += f"\n  {DM}📁 Saved: {fname}{RS}\n"
    except: pass

    speak("Weekly life report ready hai Boss!")
    return out


# ─── FEATURE 16: WhatsApp Message Sender ─────────────────────

def send_whatsapp(number, message):
    """WhatsApp message send karo via termux-open-url."""
    try:
        # Remove spaces/dashes from number
        num = re.sub(r'[\s\-\(\)]', '', number)
        if not num.startswith("+"):
            num = "+91" + num  # Default India code
        encoded_msg = urllib.parse.quote(message)
        url = f"https://wa.me/{num.lstrip('+')}?text={encoded_msg}"
        subprocess.Popen(["termux-open-url", url])
        return cg(f"✅ WhatsApp opening for {num}...\n  Message: {message[:50]}")
    except Exception as e:
        return cy(f"WhatsApp error: {e}")


# ══════════════════════════════════════════════════════════════
# ─── FEATURE: NIGHT GUARD MODE + RED ALERT SYSTEM ────────────
# Network scan karo — intruder mila toh RED ALERT graphic auto
# ══════════════════════════════════════════════════════════════

NIGHT_GUARD_FILE = os.path.expanduser("~/.friday_night_guard.json")
_night_guard_thread = None
_night_guard_running = False

def night_guard_load():
    try:
        if os.path.exists(NIGHT_GUARD_FILE):
            with open(NIGHT_GUARD_FILE) as f:
                return json.load(f)
    except: pass
    return {
        "active": False,
        "known_devices": [],
        "alert_count": 0,
        "last_scan": None,
        "scan_interval": 5,   # minutes
        "alerts": []
    }

def night_guard_save(ng):
    try:
        with open(NIGHT_GUARD_FILE, 'w') as f:
            json.dump(ng, f, indent=2, ensure_ascii=False)
    except: pass

def night_guard_learn_devices():
    """Current network devices ko safe/known mark karo — baseline register karo."""
    print_friday(cy("🔍 Network scan ho raha hai — safe devices register ho rahe hain..."))
    devices = night_guard_scan_network()
    if not devices:
        return cy("⚠ Koi device nahi mila Boss. WiFi connected hai? Try again.")
    ng = night_guard_load()
    safe = []
    for d in devices:
        ip  = d.get("ip", "")
        mac = d.get("mac", "").upper()
        if ip and mac and mac != "UNKNOWN":
            safe.append({"ip": ip, "mac": mac})
    ng["safe_devices"]   = safe
    ng["known_devices"]  = safe          # backward compat
    ng["learned"]        = True
    ng["learned_at"]     = datetime.datetime.now().isoformat()
    night_guard_save(ng)
    out  = f"\n{G}╔══ ✅ NIGHT GUARD LEARN COMPLETE ══╗{RS}\n"
    out += f"  {C}{BD}{len(safe)} safe device(s) registered:{RS}\n"
    for d in safe:
        out += f"  {G}●{RS} {W}{d['ip']:<16}{RS}  {DM}{d['mac']}{RS}\n"
    out += f"\n  {G}Ab 'night guard on' se monitoring shuru karo Boss!{RS}\n"
    out += f"{G}╚{'═'*38}╝{RS}\n"
    speak(f"{len(safe)} devices registered Boss. Night Guard ready hai!")
    return out

def night_guard_scan_network():
    """
    LIGHTWEIGHT scan — sirf arp -a use karta hai.
    No nmap subnet scan = No freeze! Fast aur Termux-friendly.
    """
    devices = []
    ip_pattern  = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
    mac_pattern = re.compile(
        r'([0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2}'
        r'[:\-][0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2})'
    )
    seen_ips = set()

    # ── Method 1: arp -a (fastest, no root needed) ───────────
    try:
        r = subprocess.run(
            ["arp", "-a"],
            capture_output=True, text=True, timeout=8
        )
        for line in r.stdout.split("\n"):
            ip_m  = ip_pattern.search(line)
            mac_m = mac_pattern.search(line)
            if ip_m:
                ip  = ip_m.group(1)
                mac = mac_m.group(1).upper() if mac_m else "UNKNOWN"
                # Skip broadcast / invalid
                if ip.endswith(".255") or ip == "255.255.255.255": continue
                if ip not in seen_ips:
                    seen_ips.add(ip)
                    devices.append({
                        "ip": ip, "mac": mac,
                        "hostname": "Unknown",
                        "seen": datetime.datetime.now().isoformat()
                    })
    except: pass

    # ── Method 2: ip neigh (ARP table — Termux mein reliable) ─
    try:
        r = subprocess.run(
            ["ip", "neigh"],
            capture_output=True, text=True, timeout=8
        )
        for line in r.stdout.split("\n"):
            ip_m  = ip_pattern.search(line)
            mac_m = mac_pattern.search(line)
            if ip_m:
                ip  = ip_m.group(1)
                mac = mac_m.group(1).upper() if mac_m else "UNKNOWN"
                if ip.endswith(".255"): continue
                if ip not in seen_ips:
                    seen_ips.add(ip)
                    devices.append({
                        "ip": ip, "mac": mac,
                        "hostname": "Unknown",
                        "seen": datetime.datetime.now().isoformat()
                    })
    except: pass

    # ── Method 3: termux-wifi-connectioninfo (apna IP bhi add) ─
    try:
        r = subprocess.run(
            ["termux-wifi-connectioninfo"],
            capture_output=True, text=True, timeout=5
        )
        data = json.loads(r.stdout)
        my_ip = data.get("ip", "")
        if my_ip and my_ip not in seen_ips:
            seen_ips.add(my_ip)
            devices.append({
                "ip": my_ip, "mac": data.get("bssid","UNKNOWN").upper(),
                "hostname": f"This phone ({BOSS})",
                "seen": datetime.datetime.now().isoformat()
            })
    except: pass

    return devices

def night_guard_generate_red_alert(intruder_info, api_key=""):
    """Intruder mila — RED ALERT futuristic graphic generate karo."""
    now = datetime.datetime.now()
    ts  = now.strftime("%Y%m%d_%H%M%S")
    ip  = intruder_info.get("ip", "UNKNOWN")
    mac = intruder_info.get("mac", "UNKNOWN")

    # Dramatic Red Alert prompt for Stability AI
    alert_prompt = (
        "DANGER RED ALERT cyberpunk warning screen, "
        "dark background with bright red glowing text 'INTRUDER DETECTED', "
        "futuristic HUD interface, binary code rain, "
        "warning symbols, neon red and orange colors, "
        "cyber threat alert display, high tech security system, "
        "dramatic cinematic lighting, ultra detailed 4K"
    )

    print(f"\n  {R}{'='*50}{RS}")
    print(f"  {R}⚠  NIGHT GUARD — INTRUDER ALERT!  ⚠{RS}")
    print(f"  {R}{'='*50}{RS}")
    print(f"  {R}🔴 IP   : {ip}{RS}")
    print(f"  {R}🔴 MAC  : {mac}{RS}")
    print(f"  {R}🔴 Time : {now.strftime('%H:%M:%S')}{RS}\n")

    # TTS Alert
    speak(f"Boss! Red Alert! Intruder detected on network! IP address {ip}")

    # Termux notification — high priority
    try:
        subprocess.Popen([
            "termux-notification",
            "--title", "🚨 NIGHT GUARD — RED ALERT!",
            "--content", f"Intruder detected! IP: {ip}",
            "--priority", "high",
            "--sound"
        ])
    except: pass

    # Vibrate — 3 times
    for _ in range(3):
        try:
            subprocess.run(["termux-vibrate", "-d", "500"], timeout=2)
            time.sleep(0.3)
        except: pass

    # Generate RED ALERT image
    _ensure_image_dir()
    img_result = None

    # Image generation removed — no working provider


    img_result = None  # Image generation unavailable
    speak(f"{len(devices)} safe devices registered. Night Guard ready hai Boss.")
    return out

def start_night_guard():
    """Night Guard background thread start karo."""
    def _guard():
        global _night_guard_running
        _night_guard_running = True
        while _night_guard_running:
            try:
                ng = night_guard_load()
                if not ng.get("active"):
                    time.sleep(30)
                    continue

                # Interval — default 5 min, min 2 min
                interval = max(2, ng.get("scan_interval", 5)) * 60

                devices  = night_guard_scan_network()
                known_ips  = ng.get("known_devices", [])
                known_macs = ng.get("known_macs", [])
                ng["last_scan"] = datetime.datetime.now().isoformat()

                intruders = []
                for d in devices:
                    # Skip fake/invalid devices
                    if d["ip"] == "0.0.0.0" or d["mac"] == "02:00:00:00:00:00":
                        continue
                    ip_unknown  = d["ip"]  not in known_ips
                    mac_unknown = (d["mac"] != "UNKNOWN" and
                                   d["mac"] not in known_macs)
                    # Intruder = IP aur MAC dono unknown
                    if ip_unknown and mac_unknown:
                        intruders.append(d)

                if intruders:
                    ng["alert_count"] = ng.get("alert_count", 0) + len(intruders)
                    for intruder in intruders:
                        ng.setdefault("alerts", []).append({
                            "ip":   intruder["ip"],
                            "mac":  intruder.get("mac", "?"),
                            "time": datetime.datetime.now().isoformat()
                        })
                    ng["alerts"] = ng["alerts"][-50:]
                    night_guard_save(ng)
                    # Red Alert — background mein generate karo
                    threading.Thread(
                        target=lambda i=intruders[0]: print(
                            night_guard_generate_red_alert(i)
                        ),
                        daemon=True
                    ).start()
                else:
                    night_guard_save(ng)

                time.sleep(interval)

            except Exception:
                time.sleep(60)

    global _night_guard_thread
    ng = night_guard_load()
    if not ng.get("known_devices"):
        return cy(
            "Boss, pehle 'night guard learn' chalaao!\n"
            "Warna sab devices intruder lagenge. 😅"
        )
    ng["active"] = True
    night_guard_save(ng)
    _night_guard_thread = threading.Thread(target=_guard, daemon=True)
    _night_guard_thread.start()
    interval = ng.get("scan_interval", 5)
    return cg(
        f"✓ Night Guard ON! 🌙\n"
        f"  Network monitoring shuru — har {interval} min pe scan hoga.\n"
        f"  Intruder aaya toh RED ALERT + notification + vibration!"
    )

def stop_night_guard():
    global _night_guard_running
    _night_guard_running = False
    ng = night_guard_load()
    ng["active"] = False
    night_guard_save(ng)
    return cy("🌙 Night Guard OFF — monitoring band ho gayi Boss.")

def night_guard_manual_scan():
    """Ek baar manually scan karo — fast, no freeze."""
    print(f"\n  {C}🔍 ARP table scan ho raha hai...{RS}")
    print(f"  {DM}(2-3 seconds Boss){RS}\n")
    devices  = night_guard_scan_network()
    ng       = night_guard_load()
    known_ips  = ng.get("known_devices", [])
    known_macs = ng.get("known_macs", [])
    ng["last_scan"] = datetime.datetime.now().isoformat()
    night_guard_save(ng)

    if not devices:
        return cy(
            "Koi devices nahi mile Boss.\n"
            "WiFi connected hai? 'net' command se check karo."
        )

    # Classify
    intruders    = []
    safe_devices = []
    for d in devices:
        ip_unknown  = d["ip"]  not in known_ips
        mac_unknown = (d["mac"] != "UNKNOWN" and d["mac"] not in known_macs)
        if ip_unknown and mac_unknown and known_ips:
            intruders.append(d)
        else:
            safe_devices.append(d)

    out  = f"\n{Y}╔══ 🔍 NIGHT GUARD SCAN RESULT ══╗{RS}\n"
    out += f"  {C}Total devices found: {W}{len(devices)}{RS}\n\n"
    out += f"  {G}✓ Safe Devices ({len(safe_devices)}):{RS}\n"
    for d in safe_devices[:8]:
        out += f"  {G}●{RS} {C}{d['ip']:<16}{RS}  {DM}{d['mac'][:17]}{RS}\n"

    if intruders:
        out += f"\n  {R}⚠ UNKNOWN DEVICES ({len(intruders)}):{RS}\n"
        for d in intruders:
            out += f"  {R}🔴 {d['ip']:<16}{RS}  {W}{d['mac'][:17]}{RS}\n"
        out += f"\n  {R}Red Alert trigger ho raha hai Boss!{RS}\n"
        out += f"{Y}╚{'═'*36}╝{RS}\n"
        print(out)
        # Red Alert background mein generate karo
        threading.Thread(
            target=lambda i=intruders[0]: print(night_guard_generate_red_alert(i)),
            daemon=True
        ).start()
        return ""
    else:
        if not known_ips:
            out += f"\n  {Y}⚠ Pehle 'night guard learn' chalao Boss!{RS}\n"
        else:
            out += f"\n  {G}✓ Network bilkul safe hai Boss!{RS}\n"
    out += f"{Y}╚{'═'*36}╝{RS}\n"
    speak("Scan complete Boss. Network safe hai!" if not intruders
          else f"Boss! {len(intruders)} unknown devices mile!")
    return out

def night_guard_status():
    """Night Guard ka current status dikao."""
    ng = night_guard_load()
    active = ng.get("active", False)
    safe_devices = ng.get("safe_devices", [])
    alerts = ng.get("alerts", [])
    alert_count = ng.get("alert_count", 0)
    last_scan = ng.get("last_scan", "Kabhi nahi")
    if last_scan and last_scan != "Kabhi nahi":
        try:
            last_scan = datetime.datetime.fromisoformat(last_scan).strftime("%d %b %H:%M")
        except:
            pass
    status_color = G if active else R
    status_text  = "🟢 ACTIVE — Monitoring ON" if active else "🔴 INACTIVE — Off hai"
    out  = f"\n{Y}╔══ 🌙 NIGHT GUARD STATUS ══╗{RS}\n"
    out += f"  {status_color}Status     : {BD}{status_text}{RS}\n"
    out += f"  {C}Safe Devices : {BD}{len(safe_devices)}{RS} registered\n"
    out += f"  {W}Total Alerts : {BD}{alert_count}{RS} intruders detected\n"
    out += f"  {DM}Last Scan    : {last_scan}{RS}\n"
    if alerts:
        last = alerts[-1]
        try:
            lt = datetime.datetime.fromisoformat(last["time"]).strftime("%d %b %H:%M")
        except:
            lt = last.get("time", "?")
        out += f"  {R}Last Intruder: {last['ip']} @ {lt}{RS}\n"
    out += f"{Y}╚{'═'*32}╝{RS}\n"
    return out

def night_guard_alerts_list():
    ng = night_guard_load()
    alerts = ng.get("alerts", [])
    if not alerts:
        return cy("Koi alerts nahi hain Boss. Network safe hai!")
    out  = f"\n{Y}╔══ 🚨 NIGHT GUARD ALERTS ({len(alerts)}) ══╗{RS}\n"
    for a in alerts[-10:]:
        try:
            t = datetime.datetime.fromisoformat(a["time"]).strftime("%d %b %H:%M")
        except:
            t = a.get("time", "?")
        out += f"  {R}⚠{RS} {C}{t}{RS}  {W}{a['ip']:<16}{RS} {DM}{a.get('mac','?')}{RS}\n"
    out += f"{Y}╚{'═'*40}╝{RS}\n"
    return out


# ══════════════════════════════════════════════════════════════
# ─── FEATURE: MIRAZ EDITION ACHIEVEMENT WALLPAPER ────────────
# Weekly achievements collect karke dark minimalist wallpaper
# ══════════════════════════════════════════════════════════════


def _collect_weekly_achievements():
    """Pichle 7 din ke sab achievements collect karo."""
    now = datetime.datetime.now()
    week_start = (now - datetime.timedelta(days=6)).strftime("%Y-%m-%d")
    achievements = []

    # ── Goals ──
    try:
        all_goals = [g for g in goals_load() if g.get("date","") >= week_start]
        done_goals = [g for g in all_goals if g.get("done")]
        if done_goals:
            achievements.append(f"✅ {len(done_goals)} goals completed")
    except: pass

    # ── Fitness ──
    try:
        fitness = [r for r in fitness_load() if r.get("date","") >= week_start]
        if fitness:
            groups = {}
            for r in fitness:
                groups.setdefault(r["type"], []).append(float(r["value"]))
            for etype, vals in groups.items():
                icon = "👟" if "step" in etype else "💧" if "paan" in etype or "water" in etype else "💪"
                achievements.append(f"{icon} {sum(vals):.0f} total {etype}")
    except: pass

    # ── Sleep ──
    try:
        sleep_recs = [r for r in sleep_load() if r.get("sleep_date","") >= week_start and r.get("duration")]
        if sleep_recs:
            durations = []
            for r in sleep_recs:
                try:
                    h, m = r["duration"].replace("h","").replace("m","").split()
                    durations.append(int(h) * 60 + int(m))
                except: pass
            if durations:
                avg = sum(durations) // len(durations)
                achievements.append(f"🌙 Avg sleep: {avg//60}h {avg%60}m ({len(sleep_recs)} nights)")
    except: pass

    # ── Expense ──
    try:
        expenses = [e for e in expense_load() if e.get("date","") >= week_start]
        if expenses:
            total = sum(e["amount"] for e in expenses)
            achievements.append(f"💰 Total spent: ₹{total:.0f}")
    except: pass

    # ── Mood ──
    try:
        moods = [m for m in mood_load() if m.get("date","") >= week_start]
        if moods:
            counts = {}
            for m in moods:
                counts[m["mood"]] = counts.get(m["mood"], 0) + 1
            top_mood = max(counts, key=counts.get)
            achievements.append(f"😊 Top mood: {top_mood}")
    except: pass

    return achievements



#  SECTION 2 — MAIN COMMAND LOOP (if/elif)
# ══════════════════════════════════════════════════════════════
#  FEATURE: FILE MANAGER
# ══════════════════════════════════════════════════════════════

FILE_CATS = {
    "Images":    [".jpg",".jpeg",".png",".gif",".webp",".bmp",".svg"],
    "Videos":    [".mp4",".mkv",".avi",".mov",".3gp",".flv",".webm"],
    "Audio":     [".mp3",".m4a",".flac",".wav",".ogg",".aac"],
    "Documents": [".pdf",".doc",".docx",".txt",".xlsx",".pptx",".csv"],
    "Archives":  [".zip",".rar",".tar",".gz",".7z"],
    "APKs":      [".apk"],
    "Code":      [".py",".js",".html",".css",".json",".sh",".xml"],
}

COMMON_DIRS = [
    "/sdcard/Download", "/sdcard/Downloads",
    os.path.expanduser("~/storage/downloads"),
    os.path.expanduser("~/storage/shared/Download"),
]

def _resolve_dir(path_hint=None):
    """Resolve aur validate directory path."""
    if path_hint:
        candidates = [
            path_hint,
            f"/sdcard/{path_hint}",
            os.path.expanduser(f"~/storage/shared/{path_hint}"),
        ]
        for c in candidates:
            if os.path.isdir(c):
                return c
        return None
    # Default — downloads folder
    for d in COMMON_DIRS:
        if os.path.isdir(d):
            return d
    return None

def file_list(path_hint=None, show_all=False):
    """Folder ki files list karo."""
    folder = _resolve_dir(path_hint)
    if not folder:
        return cy(f"Folder nahi mila Boss: '{path_hint or 'Downloads'}'")
    try:
        entries = os.listdir(folder)
    except PermissionError:
        return cy(f"Permission nahi hai Boss: {folder}")

    if not entries:
        return cg(f"Folder khali hai Boss: {folder}")

    # Categorize
    cats = {k: [] for k in FILE_CATS}
    cats["Others"] = []
    for f in sorted(entries):
        fp = os.path.join(folder, f)
        ext = os.path.splitext(f)[1].lower()
        placed = False
        for cat, exts in FILE_CATS.items():
            if ext in exts:
                size = os.path.getsize(fp) // 1024 if os.path.isfile(fp) else 0
                cats[cat].append((f, size))
                placed = True
                break
        if not placed:
            size = os.path.getsize(fp) // 1024 if os.path.isfile(fp) else 0
            cats["Others"].append((f, size))

    total = len(entries)
    out  = f"\n{Y}╔══ 📂 {os.path.basename(folder).upper()} ({total} items) ══╗{RS}\n"
    out += f"  {DM}Path: {folder}{RS}\n\n"
    for cat, files in cats.items():
        if files:
            out += f"  {C}── {cat} ({len(files)}) ──{RS}\n"
            show = files if show_all else files[:5]
            for fname, sz in show:
                size_str = f"{sz}KB" if sz < 1024 else f"{sz//1024}MB"
                out += f"    {W}{fname[:40]:<42}{DM}{size_str}{RS}\n"
            if len(files) > 5 and not show_all:
                out += f"    {DM}... aur {len(files)-5} files hain{RS}\n"
    out += f"{Y}╚{'═'*42}╝{RS}\n"
    return out

def file_delete(targets, path_hint=None):
    """Files delete karo — confirmation ke saath."""
    folder = _resolve_dir(path_hint)
    if not folder:
        return cy(f"Folder nahi mila Boss: '{path_hint or 'Downloads'}'")

    deleted = []
    failed  = []
    skipped = []

    for target in targets:
        # Extension se delete (e.g. "*.apk")
        if target.startswith("*."):
            ext = target[1:]
            for f in os.listdir(folder):
                if f.lower().endswith(ext):
                    fp = os.path.join(folder, f)
                    try:
                        os.remove(fp)
                        deleted.append(f)
                    except Exception as e:
                        failed.append(f"{f}: {e}")
        else:
            fp = os.path.join(folder, target)
            if not os.path.exists(fp):
                skipped.append(target)
            else:
                try:
                    if os.path.isdir(fp):
                        import shutil
                        shutil.rmtree(fp)
                    else:
                        os.remove(fp)
                    deleted.append(target)
                except Exception as e:
                    failed.append(f"{target}: {e}")

    out  = f"\n{Y}╔══ 🗑 DELETE REPORT ══╗{RS}\n"
    if deleted:
        out += f"  {G}✓ Deleted ({len(deleted)}):{RS}\n"
        for f in deleted[:10]:
            out += f"    {DM}{f[:50]}{RS}\n"
    if failed:
        out += f"  {R}✗ Failed ({len(failed)}):{RS}\n"
        for f in failed[:5]:
            out += f"    {Y}{f[:50]}{RS}\n"
    if skipped:
        out += f"  {Y}⚠ Not found ({len(skipped)}): {', '.join(skipped[:3])}{RS}\n"
    if not deleted and not failed:
        out += f"  {Y}Kuch nahi hua Boss — files check karo{RS}\n"
    out += f"{Y}╚{'═'*38}╝{RS}\n"
    return out

def file_organize(path_hint=None):
    """Files ko category folders mein organize karo."""
    folder = _resolve_dir(path_hint)
    if not folder:
        return cy(f"Folder nahi mila Boss: '{path_hint or 'Downloads'}'")

    moved   = []
    failed  = []
    skipped = []

    for f in os.listdir(folder):
        fp = os.path.join(folder, f)
        if not os.path.isfile(fp):
            continue
        ext = os.path.splitext(f)[1].lower()
        target_cat = None
        for cat, exts in FILE_CATS.items():
            if ext in exts:
                target_cat = cat
                break
        if not target_cat:
            skipped.append(f)
            continue
        cat_dir = os.path.join(folder, target_cat)
        os.makedirs(cat_dir, exist_ok=True)
        dest = os.path.join(cat_dir, f)
        if os.path.exists(dest):
            skipped.append(f)
            continue
        try:
            import shutil
            shutil.move(fp, dest)
            moved.append((f, target_cat))
        except Exception as e:
            failed.append(f"{f}: {e}")

    out  = f"\n{Y}╔══ 📁 ORGANIZE REPORT ══╗{RS}\n"
    out += f"  {C}Folder : {RS}{W}{folder}{RS}\n"
    if moved:
        out += f"  {G}✓ Moved ({len(moved)} files):{RS}\n"
        for fname, cat in moved[:8]:
            out += f"    {DM}{fname[:35]} → {cat}{RS}\n"
        if len(moved) > 8:
            out += f"    {DM}... aur {len(moved)-8} files{RS}\n"
    if skipped:
        out += f"  {Y}⚠ Skipped {len(skipped)} files (unknown type ya already moved){RS}\n"
    if failed:
        out += f"  {R}✗ Failed {len(failed)} files{RS}\n"
    if not moved:
        out += f"  {C}Sab pehle se organized hai Boss!{RS}\n"
    out += f"{Y}╚{'═'*40}╝{RS}\n"
    return out


def phone_scan(scan_type="all"):
    """Poora phone scan karo — internal + SD card."""
    G="[92m"; Y="[93m"; C="[96m"; R="[91m"; RS="[0m"; BD="[1m"; DM="[2m"

    SCAN_ROOTS = [
        ("/sdcard", "📱 SD Card"),
        (os.path.expanduser("~/storage/shared"), "📂 Internal Storage"),
        (os.path.expanduser("~/storage/downloads"), "⬇️  Downloads"),
    ]

    FILE_CATS = {
        "🎵 Audio":     [".mp3", ".m4a", ".flac", ".wav", ".ogg", ".aac"],
        "🎬 Videos":    [".mp4", ".mkv", ".avi", ".mov", ".3gp", ".webm"],
        "🖼️  Images":   [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"],
        "📄 Documents": [".pdf", ".doc", ".docx", ".txt", ".xlsx", ".pptx", ".csv"],
        "📦 Archives":  [".zip", ".rar", ".tar", ".gz", ".7z"],
        "📱 APKs":      [".apk"],
    }

    def fmt_size(b):
        if b >= 1073741824: return f"{b/1073741824:.1f}GB"
        if b >= 1048576:    return f"{b/1048576:.1f}MB"
        if b >= 1024:       return f"{b/1024:.1f}KB"
        return f"{b}B"

    # Collect all files
    all_files = {}  # category -> list of (path, size)
    total_size = 0
    total_count = 0
    scanned_roots = []

    for root_path, root_name in SCAN_ROOTS:
        if not os.path.exists(root_path):
            continue
        scanned_roots.append(root_name)
        try:
            for dirpath, dirnames, filenames in os.walk(root_path):
                # Skip hidden/system folders
                dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in ['Android', 'LOST.DIR']]
                for fname in filenames:
                    if fname.startswith('.'): continue
                    fpath = os.path.join(dirpath, fname)
                    ext = os.path.splitext(fname)[1].lower()
                    try:
                        size = os.path.getsize(fpath)
                    except: continue
                    total_size += size
                    total_count += 1
                    cat = "📁 Others"
                    for c, exts in FILE_CATS.items():
                        if ext in exts:
                            cat = c
                            break
                    all_files.setdefault(cat, []).append((fpath, fname, size))
        except PermissionError:
            pass

    if scan_type == "mp3":
        # Sirf MP3 dikhao
        audio_files = all_files.get("🎵 Audio", [])
        if not audio_files:
            return cy("Koi audio file nahi mili Boss!")
        out = f"\n{Y}╔══ 🎵 AUDIO FILES ({len(audio_files)}) ══╗{RS}\n"
        for fpath, fname, size in sorted(audio_files, key=lambda x: x[2], reverse=True):
            folder = os.path.basename(os.path.dirname(fpath))
            name = os.path.splitext(fname)[0][:45]
            out += f"  {G}♪{RS} {name}\n"
            out += f"    {DM}{folder} • {fmt_size(size)}{RS}\n"
        out += f"{Y}╚{'═'*40}╝{RS}\n"
        return out

    # Full scan result
    out = f"\n{Y}╔══ 📊 PHONE STORAGE SCAN ══╗{RS}\n"
    out += f"  {C}Scanned:{RS} {', '.join(scanned_roots)}\n"
    out += f"  {C}Total Files:{RS} {BD}{total_count}{RS} files • {BD}{fmt_size(total_size)}{RS}\n"
    out += f"{Y}╠{'═'*40}╣{RS}\n"

    for cat, files in sorted(all_files.items()):
        cat_size = sum(s for _, _, s in files)
        out += f"  {cat} — {BD}{len(files)} files{RS} ({fmt_size(cat_size)})\n"
        # Top 5 largest
        top = sorted(files, key=lambda x: x[2], reverse=True)[:5]
        for fpath, fname, size in top:
            folder = os.path.basename(os.path.dirname(fpath))
            name = os.path.splitext(fname)[0][:40]
            out += f"    {DM}• {name} [{fmt_size(size)}]{RS}\n"
        if len(files) > 5:
            out += f"    {DM}... aur {len(files)-5} files{RS}\n"

    out += f"{Y}╚{'═'*40}╝{RS}\n"
    return out


# ─── FEATURE: Voice Auto-Listen (Wake Word "Friday") ─────────
_voice_listen_active = False

def start_voice_listener(input_queue):
    """Background mein mic sunti rahe — 'Friday' sunke command lo."""
    def _listen():
        try:
            import speech_recognition as sr
        except ImportError:
            try:
                subprocess.run(["pip", "install", "SpeechRecognition", "--break-system-packages", "-q"],
                               capture_output=True, timeout=60)
                import speech_recognition as sr
            except:
                print(f"  \033[93m⚠ Voice listen ke liye: pip install SpeechRecognition\033[0m")
                return

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True

        print(f"  \033[92m✓ Voice listener active — 'Friday' bolke command do!\033[0m")

        while _voice_listen_active:
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
                try:
                    text = recognizer.recognize_google(audio, language="hi-IN").lower()
                    # Wake word check
                    if any(w in text for w in ["friday", "फ्राइडे", "hey friday", "aye friday"]):
                        # Wake word ke baad command
                        cmd_text = text
                        for w in ["friday", "फ्राइडे", "hey friday", "aye friday"]:
                            cmd_text = cmd_text.replace(w, "").strip()
                        if cmd_text:
                            print(f"\n\033[96m🎙️  Voice: '{cmd_text}'\033[0m")
                            input_queue.put(cmd_text)
                            # Stdin mein inject karo taaki input() unblock ho
                            try:
                                import termios, tty
                                fd = sys.stdin.fileno()
                                for ch in (cmd_text + "\n"):
                                    termios.tcflush(fd, termios.TCIFLUSH)
                            except: pass
                        else:
                            speak("Haan Boss, boliye!")
                            print(f"\n  \033[96m🎙️  Listening for command...\033[0m")
                            try:
                                with sr.Microphone() as src2:
                                    audio2 = recognizer.listen(src2, timeout=6, phrase_time_limit=10)
                                cmd2 = recognizer.recognize_google(audio2, language="hi-IN")
                                print(f"\033[96m🎙️  Voice: '{cmd2}'\033[0m")
                                input_queue.put(cmd2)
                            except: pass
                except sr.UnknownValueError: pass
                except sr.RequestError: pass
            except Exception: pass

    global _voice_listen_active
    _voice_listen_active = True
    t = threading.Thread(target=_listen, daemon=True)
    t.start()
    return t

def stop_voice_listener():
    global _voice_listen_active
    _voice_listen_active = False


# ─── FEATURE: Smart Error Guardian (Auto-Log + Fix Suggest) ──
ERROR_LOG_FILE = os.path.expanduser("~/.friday_errors.json")

def error_guardian_log(error_text, context=""):
    """Error log karo aur fix suggest karo."""
    try:
        logs = []
        if os.path.exists(ERROR_LOG_FILE):
            with open(ERROR_LOG_FILE) as f:
                logs = json.load(f)
    except: logs = []

    entry = {
        "time": datetime.datetime.now().isoformat()[:19],
        "error": error_text[:300],
        "context": context[:100],
        "fixed": False
    }
    logs.append(entry)
    logs = logs[-50:]  # Last 50 errors
    try:
        with open(ERROR_LOG_FILE, "w") as f:
            json.dump(logs, f, indent=2)
    except: pass

    # Common errors ke liye instant fix suggestions
    suggestions = []
    e = error_text.lower()
    if "modulenotfounderror" in e or "no module named" in e:
        mod = error_text.split("'")[1] if "'" in error_text else "unknown"
        suggestions.append(f"pip install {mod} --break-system-packages")
    elif "syntaxerror" in e:
        suggestions.append("bug fix" )
    elif "permissionerror" in e:
        suggestions.append("chmod +x file ya sudo se chalao")
    elif "connectionerror" in e or "timeout" in e:
        suggestions.append("Internet connection check karo")
    elif "filenotfounderror" in e:
        suggestions.append("File path check karo — file exist karti hai?")

    return suggestions

def error_guardian_show():
    """Recent errors dikhao."""
    G="[92m"; Y="[93m"; R="[91m"; RS="[0m"; DM="[2m"; BD="[1m"
    try:
        if not os.path.exists(ERROR_LOG_FILE):
            return cg("✅ Koi errors nahi hain Boss! System clean hai.")
        with open(ERROR_LOG_FILE) as f:
            logs = json.load(f)
        if not logs:
            return cg("✅ Koi errors nahi hain Boss!")
        out = f"\n{Y}╔══ 🛡️  ERROR LOG ({len(logs)}) ══╗{RS}\n"
        for e in logs[-10:]:
            status = f"{G}✓ Fixed{RS}" if e.get("fixed") else f"{R}● Open{RS}"
            out += f"  {status} {DM}{e['time']}{RS}\n"
            out += f"    {e['error'][:60]}\n"
        out += f"{Y}╚{'═'*35}╝{RS}\n"
        return out
    except Exception as ex:
        return cy(f"Error log read nahi hua: {ex}")




# ─── FEATURE: Monthly Expense Analytics + Graph ──────────────
BUDGET_FILE = os.path.expanduser("~/.friday_budget.json")

def budget_load():
    try:
        if os.path.exists(BUDGET_FILE):
            with open(BUDGET_FILE) as f: return json.load(f)
    except: pass
    return {"monthly_limit": 0, "category_limits": {}, "alerts_sent": {}}

def budget_save(data):
    try:
        with open(BUDGET_FILE, "w") as f: json.dump(data, f, indent=2)
    except: pass

def expense_monthly_graph():
    """Last 6 months ka bar graph terminal mein."""
    expenses = expense_load()
    if not expenses:
        return cy("Koi expenses nahi hain Boss.")

    now = datetime.datetime.now()
    months_data = {}
    for i in range(5, -1, -1):
        m = (now.replace(day=1) - datetime.timedelta(days=i*30))
        key = m.strftime("%Y-%m")
        label = m.strftime("%b")
        months_data[key] = {"label": label, "total": 0}

    for e in expenses:
        mkey = e["date"][:7]
        if mkey in months_data:
            months_data[mkey]["total"] += e["amount"]

    max_val = max((v["total"] for v in months_data.values()), default=1) or 1
    bar_width = 25

    out = f"\n{Y}╔══ 📈 MONTHLY EXPENSE GRAPH (Last 6 Months) ══╗{RS}\n"
    for key, data in months_data.items():
        total = data["total"]
        label = data["label"]
        filled = int((total / max_val) * bar_width)
        bar = G + "█" * filled + DM + "░" * (bar_width - filled) + RS
        curr = f"{Y}← Current{RS}" if key == now.strftime("%Y-%m") else ""
        out += f"  {C}{label}{RS}  {bar}  {BD}₹{total:.0f}{RS} {curr}\n"
    out += f"{Y}╚{'═'*50}╝{RS}\n"

    # Budget check
    budget = budget_load()
    limit = budget.get("monthly_limit", 0)
    if limit > 0:
        curr_month = now.strftime("%Y-%m")
        curr_total = months_data.get(curr_month, {}).get("total", 0)
        pct = (curr_total / limit) * 100
        color = R if pct >= 90 else Y if pct >= 70 else G
        out += f"\n  💰 Budget: {color}₹{curr_total:.0f} / ₹{limit:.0f} ({pct:.0f}%){RS}\n"

    return out

def budget_set(amount, category=None):
    """Monthly budget set karo."""
    data = budget_load()
    if category:
        data["category_limits"][category.lower()] = float(amount)
        budget_save(data)
        return cg(f"✅ {category} budget set: ₹{amount}/month")
    else:
        data["monthly_limit"] = float(amount)
        budget_save(data)
        return cg(f"✅ Monthly budget set: ₹{amount}")

def budget_check_alert():
    """Background mein budget alert check karo."""
    expenses = expense_load()
    budget = budget_load()
    limit = budget.get("monthly_limit", 0)
    if not limit: return

    now = datetime.datetime.now()
    month = now.strftime("%Y-%m")
    monthly = [e for e in expenses if e["date"].startswith(month)]
    total = sum(e["amount"] for e in monthly)
    pct = (total / limit) * 100
    alert_key = f"{month}_alert"

    if pct >= 100 and not budget.get("alerts_sent", {}).get(f"{month}_100"):
        msg = f"Boss! Budget khatam ho gaya! ₹{total:.0f} kharch ho gaye ₹{limit:.0f} mein se!"
        speak(msg)
        print(f"\n  {R}💰 BUDGET ALERT: {pct:.0f}% used!{RS}\n")
        budget.setdefault("alerts_sent", {})[f"{month}_100"] = True
        budget_save(budget)
    elif pct >= 80 and not budget.get("alerts_sent", {}).get(f"{month}_80"):
        msg = f"Boss! Budget ka 80 percent khatam ho gaya. ₹{total:.0f} mein se ₹{limit:.0f}."
        speak(msg)
        print(f"\n  {Y}💰 BUDGET WARNING: {pct:.0f}% used!{RS}\n")
        budget.setdefault("alerts_sent", {})[f"{month}_80"] = True
        budget_save(budget)

# ─── FEATURE: Memory Encryption ──────────────────────────────
def _get_enc_key():
    """Simple XOR key from device hostname."""
    import socket
    host = socket.gethostname()
    return sum(ord(c) for c in host) % 256

def memory_encrypt(data_str):
    """Simple XOR encryption."""
    key = _get_enc_key()
    return ''.join(chr(ord(c) ^ key) for c in data_str)

def memory_decrypt(enc_str):
    """XOR decrypt (same as encrypt)."""
    return memory_encrypt(enc_str)  # XOR is symmetric

def save_memory_encrypted(mem):
    """Memory ko encrypt karke save karo."""
    ENC_FILE = os.path.expanduser("~/.friday_memory_enc.dat")
    try:
        raw = json.dumps(mem, ensure_ascii=False)
        enc = memory_encrypt(raw)
        with open(ENC_FILE, "w", encoding="utf-8") as f:
            f.write(enc)
        return True
    except: return False

def load_memory_encrypted():
    """Encrypted memory load karo."""
    ENC_FILE = os.path.expanduser("~/.friday_memory_enc.dat")
    try:
        if os.path.exists(ENC_FILE):
            with open(ENC_FILE, "r", encoding="utf-8") as f:
                enc = f.read()
            raw = memory_decrypt(enc)
            return json.loads(raw)
    except: pass
    return []

# ─── FEATURE: Multi-Layer Reasoning ──────────────────────────
def multi_layer_reason(question, ltm, mem):
    """3-step reasoning: Analyze → Plan → Answer."""
    if not GROQ_KEY:
        return None

    # Collect context
    facts = []
    try:
        topics = ltm.get("topics", {})
        for k, v in topics.items():
            facts.append(f"{k}: {v.get('value','')}")
    except: pass

    context = "\n".join(facts[:10]) if facts else "No saved facts"
    mem_list = mem.get("messages", []) if isinstance(mem, dict) else []
    history = "\n".join([f"{m['role']}: {m['content'][:80]}" for m in mem_list[-4:]]) if mem_list else ""

    reasoning_prompt = f"""You are FRIDAY, Boss MIRAZ ki personal AI.

BOSS KE BAARE MEIN FACTS:
{context}

RECENT CONVERSATION:
{history}

QUESTION: {question}

Pehle SOCH (2-3 lines mein analyze karo internally), phir direct answer do.
Format:
ANALYSIS: [brief internal reasoning]
ANSWER: [direct helpful response in Hinglish]"""

    try:
        import urllib.request
        payload = json.dumps({
            "model": MODEL,
            "messages": [{"role": "user", "content": reasoning_prompt}],
            "max_tokens": 600,
            "temperature": 0.7
        }).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            full = data["choices"][0]["message"]["content"]
            # Extract just the answer part
            if "ANSWER:" in full:
                answer = full.split("ANSWER:", 1)[1].strip()
                analysis = full.split("ANSWER:", 1)[0].replace("ANALYSIS:", "").strip()
                print(f"  {DM}🧠 Soch rahi hoon: {analysis[:80]}...{RS}")
                return answer
            return full
    except: return None


# ─── FEATURE: Intelligent Todo Priority Detection ─────────────
TODO_PRIORITY_FILE = os.path.expanduser("~/.friday_todos.json")

PRIORITY_KEYWORDS = {
    "urgent": ["urgent", "abhi", "turant", "jaldi", "asap", "emergency", "critical", "aaj hi"],
    "high":   ["important", "zaruri", "high", "priority", "deadline", "kal tak", "must"],
    "medium": ["karna hai", "todo", "yaad", "reminder", "plan", "sochna"],
    "low":    ["kabhi", "baad mein", "eventually", "someday", "agar time mile"]
}

def todo_detect_priority(text):
    t = text.lower()
    for level, keywords in PRIORITY_KEYWORDS.items():
        if any(k in t for k in keywords):
            return level
    return "medium"

def todo_load():
    try:
        if os.path.exists(TODO_PRIORITY_FILE):
            with open(TODO_PRIORITY_FILE) as f: return json.load(f)
    except: pass
    return []

def todo_save(todos): 
    try:
        with open(TODO_PRIORITY_FILE, "w") as f: json.dump(todos, f, indent=2, ensure_ascii=False)
    except: pass

def todo_add(text):
    todos = todo_load()
    priority = todo_detect_priority(text)
    # AI se bhi priority suggest karwao
    ai_priority = None
    if GROQ_KEY:
        try:
            import urllib.request as _ur
            pay = json.dumps({"model": MODEL, "messages": [{"role":"user","content":f"Task: '{text}'. Priority level detect karo: urgent/high/medium/low. Sirf ek word batao."}], "max_tokens": 10}).encode()
            req = _ur.Request("https://api.groq.com/openai/v1/chat/completions", data=pay,
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}, method="POST")
            with _ur.urlopen(req, timeout=5) as r:
                ai_p = json.loads(r.read())["choices"][0]["message"]["content"].strip().lower()
                if ai_p in ["urgent","high","medium","low"]: ai_priority = ai_p
        except: pass
    final_priority = ai_priority or priority
    icons = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
    todo = {"id": int(datetime.datetime.now().timestamp()), "text": text,
            "priority": final_priority, "done": False,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
    todos.append(todo)
    todo_save(todos)
    return cg(f"✅ Todo added! {icons[final_priority]} Priority: {final_priority.upper()} — {text}")

def todo_show():
    todos = todo_load()
    if not todos: return cy("Koi todos nahi hain Boss. 'todo add <task>' se add karo.")
    icons = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
    order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    sorted_todos = sorted([t for t in todos if not t["done"]], key=lambda x: order.get(x["priority"],2))
    done_todos = [t for t in todos if t["done"]]
    out = f"\n{Y}╔══ ✅ SMART TODO LIST ══╗{RS}\n"
    if sorted_todos:
        out += f"  {BD}Pending ({len(sorted_todos)}){RS}\n"
        for i, t in enumerate(sorted_todos, 1):
            icon = icons.get(t["priority"], "🟡")
            out += f"  {icon} {BD}[{i}]{RS} {C}{t['text']}{RS}\n"
    if done_todos:
        out += f"\n  {DM}Done ({len(done_todos)}){RS}\n"
        for t in done_todos[-3:]:
            out += f"  ✓ {DM}{t['text']}{RS}\n"
    out += f"{Y}╚{'═'*35}╝{RS}\n"
    return out

def todo_done(todo_id):
    todos = todo_load()
    tid = str(todo_id).strip()
    # Number se match karo (1, 2, 3...)
    pending = [t for t in todos if not t["done"]]
    if tid.isdigit() and int(tid) <= len(pending):
        idx = int(tid) - 1
        t = pending[idx]
        t["done"] = True
        todo_save(todos)
        return cg(f"✅ Done! '{t['text']}'")
    # ID se match karo
    for t in todos:
        if str(t["id"]) == tid:
            t["done"] = True
            todo_save(todos)
            return cg(f"✅ Done! '{t['text']}'")
    # Text se match karo
    for t in todos:
        if not t["done"] and tid.lower() in t["text"].lower():
            t["done"] = True
            todo_save(todos)
            return cg(f"✅ Done! '{t['text']}'")
    return cy(f"Todo nahi mila Boss. 'todos' se number dekho phir 'todo done 1' bolo.")

def todo_clear():
    todo_save([])
    return cg("✅ Saare todos clear ho gaye!")

# ─── FEATURE: PDF & Document Reader ──────────────────────────
def read_document(file_path):
    """PDF, txt, ya web URL padhke summarize karo."""
    C2="[96m"; Y2="[93m"; RS2="[0m"
    file_path = file_path.strip()
    
    # Web URL hai?
    if file_path.startswith("http"):
        return scrape_and_summarize(file_path)
    
    # File exist karti hai?
    expanded = os.path.expanduser(file_path)
    if not os.path.exists(expanded):
        # sdcard mein dhundo
        for base in ["/sdcard/", "/sdcard/Download/", "/sdcard/Documents/"]:
            test = base + file_path
            if os.path.exists(test):
                expanded = test
                break
        else:
            return cy(f"File nahi mili Boss: {file_path}")
    
    ext = os.path.splitext(expanded)[1].lower()
    text = ""
    
    # PDF read karo
    if ext == ".pdf":
        try:
            # pdfplumber try karo
            import pdfplumber
            with pdfplumber.open(expanded) as pdf:
                for page in pdf.pages[:5]:  # First 5 pages
                    text += page.extract_text() or ""
        except ImportError:
            try:
                # PyPDF2 fallback
                import PyPDF2
                with open(expanded, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages[:5]:
                        text += page.extract_text() or ""
            except ImportError:
                # pdftotext command line
                try:
                    r = subprocess.run(["pdftotext", expanded, "-"], capture_output=True, text=True, timeout=15)
                    text = r.stdout[:3000]
                except:
                    return cy("PDF padhne ke liye install karo:\npip install pdfplumber --break-system-packages")
    
    # Text/TXT file
    elif ext in [".txt", ".md", ".py", ".json", ".csv"]:
        try:
            with open(expanded, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()[:3000]
        except Exception as e:
            return cy(f"File read error: {e}")
    
    else:
        return cy(f"Boss, ye format support nahi hai: {ext}\nSupported: PDF, TXT, MD, web URLs")
    
    if not text.strip():
        return cy("File mein kuch text nahi mila Boss.")
    
    # AI se summarize karwao
    if not GROQ_KEY:
        # Sirf first 500 chars dikhao
        return f"\n{Y2}📄 File Content:{RS2}\n{text[:500]}..."
    
    print(f"  {C2}📄 Document padh raha hoon...{RS2}")
    try:
        import urllib.request as _ur
        prompt = f"""Ye document padhke Hinglish mein simple summary do (5-7 lines):

DOCUMENT:
{text[:2500]}

Summary Roman Hindi (Hinglish) mein do. Key points bullet points mein."""
        pay = json.dumps({"model": MODEL, "messages": [{"role":"user","content":prompt}], "max_tokens": 400}).encode()
        req = _ur.Request("https://api.groq.com/openai/v1/chat/completions", data=pay,
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}, method="POST")
        with _ur.urlopen(req, timeout=20) as r:
            summary = json.loads(r.read())["choices"][0]["message"]["content"]
        out = f"\n{Y2}╔══ 📄 DOCUMENT SUMMARY ══╗{RS2}\n"
        out += f"  File: {os.path.basename(expanded)}\n\n"
        out += f"  {summary}\n"
        out += f"{Y2}╚{'═'*35}╝{RS2}\n"
        speak(f"Document padh liya Boss. {summary[:100]}")
        return out
    except Exception as e:
        return cy(f"Summary error: {e}")

# ─── FEATURE: OCR — Image to Text ─────────────────────────────
def friday_ocr(image_path=None):
    """Image se text nikalo — Gemini Vision use karo."""
    C2="[96m"; Y2="[93m"; RS2="[0m"
    
    # Agar path diya hai toh use karo, warna camera se lo
    if image_path and os.path.exists(os.path.expanduser(image_path)):
        img_path = os.path.expanduser(image_path)
        print(f"  {C2}📄 Image se text nikaal raha hoon...{RS2}")
    else:
        img_path = os.path.expanduser("~/.friday_ocr_snap.jpg")
        print(f"  {C2}📸 Camera se scan kar raha hoon...{RS2}")
        try:
            subprocess.run(["termux-camera-photo", "-c", "0", img_path],
                          capture_output=True, timeout=10)
            if not os.path.exists(img_path):
                return cy("Camera nahi mila Boss!")
        except: return cy("Camera error!")
    
    GEMINI_KEY = os.environ.get("GEMINI_API_KEY","") or CFG.get("gemini_api_key","")
    if not GEMINI_KEY:
        return cy("Gemini API key chahiye Boss OCR ke liye!\nexport GEMINI_API_KEY='your_key'")
    
    try:
        import base64, urllib.request as _ur
        # Compress
        try:
            from PIL import Image as PILImage
            img = PILImage.open(img_path)
            img.thumbnail((1200, 1200))
            img.save(img_path + "_ocr.jpg", "JPEG", quality=85)
            read_path = img_path + "_ocr.jpg"
        except: read_path = img_path
        
        with open(read_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        
        ocr_prompt = """Extract ALL text from this image exactly as written. 
Rules: Write every word you can see. Keep original formatting/layout.
If Hindi text: write in Roman Hindi (Hinglish). 
No extra commentary, just the extracted text."""
        
        payload = json.dumps({"contents": [{"parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
            {"text": ocr_prompt}
        ]}]}).encode()
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
        req = _ur.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        
        with _ur.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read())
            result = data["candidates"][0]["content"]["parts"][0]["text"]
        
        import re
        result = re.sub(r'[\u0900-\u097F]+', '', result)
        result = re.sub(r'[\*#_`]', '', result).strip()
        
        out = f"\n{Y2}╔══ 🔍 OCR — TEXT EXTRACTED ══╗{RS2}\n"
        out += f"  {result}\n"
        out += f"{Y2}╚{'═'*38}╝{RS2}\n"
        speak(f"Text mil gaya Boss! {result[:80]}")
        
        # Cleanup
        try: os.remove(img_path + "_ocr.jpg")
        except: pass
        return out
    except Exception as e:
        return cy(f"OCR error: {e}")

# ─── FEATURE: User Behavior Learning ─────────────────────────
BEHAVIOR_FILE = os.path.expanduser("~/.friday_behavior.json")

def behavior_load():
    try:
        if os.path.exists(BEHAVIOR_FILE):
            with open(BEHAVIOR_FILE) as f: return json.load(f)
    except: pass
    return {"commands": {}, "active_hours": {}, "top_topics": {}, "last_updated": ""}

def behavior_save(data):
    try:
        with open(BEHAVIOR_FILE, "w") as f: json.dump(data, f, indent=2)
    except: pass

def behavior_track(cmd):
    """Har command track karo."""
    data = behavior_load()
    # Command frequency
    base_cmd = cmd.split()[0] if cmd.split() else cmd
    data["commands"][base_cmd] = data["commands"].get(base_cmd, 0) + 1
    # Active hours
    hour = str(datetime.datetime.now().hour)
    data["active_hours"][hour] = data["active_hours"].get(hour, 0) + 1
    data["last_updated"] = datetime.datetime.now().isoformat()[:16]
    behavior_save(data)

def behavior_suggest(ltm):
    """Behavior se smart suggestions do."""
    data = behavior_load()
    if not data["commands"]: return None
    now = datetime.datetime.now()
    hour = now.hour
    suggestions = []
    
    # Top commands
    top = sorted(data["commands"].items(), key=lambda x: -x[1])[:3]
    top_cmds = [c[0] for c in top]
    
    # Time-based suggestions
    if hour in [7, 8] and "briefing" not in top_cmds:
        suggestions.append("subah ka briefing lo — 'briefing' type karo!")
    if hour in [20, 21] and "weekly report" not in top_cmds:
        suggestions.append("aaj ka expense log karo — 'kharch summary' dekho!")
    
    # Habit suggestions
    if data["commands"].get("download", 0) > 5:
        suggestions.append("aapko music zyada pasand hai — playlist banao!")
    if data["commands"].get("mood", 0) > 3:
        suggestions.append("mood tracking achi chal rahi hai — weekly mood dekho!")
    
    return suggestions[0] if suggestions else None

def behavior_report():
    """User behavior report dikhao."""
    data = behavior_load()
    if not data["commands"]: return cy("Abhi tak koi behavior data nahi hai Boss.")
    
    top_cmds = sorted(data["commands"].items(), key=lambda x: -x[1])[:8]
    active_hrs = sorted(data["active_hours"].items(), key=lambda x: -x[1])[:3]
    
    out = f"\n{Y}╔══ 🧠 YOUR BEHAVIOR REPORT ══╗{RS}\n"
    out += f"  {BD}Top Commands:{RS}\n"
    for cmd, count in top_cmds:
        bar = G + "█" * min(count, 20) + RS
        out += f"  {C}{cmd:<15}{RS} {bar} {count}x\n"
    out += f"\n  {BD}Most Active Hours:{RS}\n"
    for h, count in active_hrs:
        out += f"  {C}{h}:00{RS} — {count} commands\n"
    out += f"\n  {DM}Last updated: {data.get('last_updated','')} {RS}\n"
    out += f"{Y}╚{'═'*38}╝{RS}\n"
    return out



# ─── FEATURE: Smart Reminders ─────────────────────────────────
REMINDERS_FILE = os.path.expanduser("~/.friday_reminders.json")

def reminders_load():
    try:
        if os.path.exists(REMINDERS_FILE):
            with open(REMINDERS_FILE) as f: return json.load(f)
    except: pass
    return []

def reminders_save(data):
    try:
        with open(REMINDERS_FILE, "w") as f: json.dump(data, f, indent=2, ensure_ascii=False)
    except: pass

def reminder_add(text):
    """Smart reminder — time parse karo text se."""
    import re as _re
    now = datetime.datetime.now()
    trigger_time = None
    clean_text = text

    # Time patterns
    patterns = [
        (r'(\d+)\s*min(ute)?s?\s*(mein|baad|later|ke baad)', 'minutes'),
        (r'(\d+)\s*(ghante|hour)s?\s*(mein|baad|later|ke baad)', 'hours'),
        (r'(\d+)\s*baje',   'clock'),
        (r'kal\s+(\d+)\s*baje', 'tomorrow_clock'),
        (r'(\d+):(\d+)',    'hhmm'),
    ]

    for pat, ptype in patterns:
        m = _re.search(pat, text.lower())
        if m:
            if ptype == 'minutes':
                trigger_time = now + datetime.timedelta(minutes=int(m.group(1)))
            elif ptype == 'hours':
                trigger_time = now + datetime.timedelta(hours=int(m.group(1)))
            elif ptype == 'clock':
                h = int(m.group(1))
                trigger_time = now.replace(hour=h, minute=0, second=0)
                if trigger_time < now: trigger_time += datetime.timedelta(days=1)
            elif ptype == 'tomorrow_clock':
                h = int(m.group(1))
                trigger_time = (now + datetime.timedelta(days=1)).replace(hour=h, minute=0, second=0)
            elif ptype == 'hhmm':
                h, mi = int(m.group(1)), int(m.group(2))
                trigger_time = now.replace(hour=h, minute=mi, second=0)
                if trigger_time < now: trigger_time += datetime.timedelta(days=1)
            clean_text = _re.sub(pat, '', text, flags=_re.I).strip(" ,-")
            break

    if not trigger_time:
        return cy("Time samajh nahi aaya Boss!\nJaise: reminder 30 min mein meeting hai\nYa: reminder 5 baje doctor appointment")

    rid = int(now.timestamp())
    rem = {"id": rid, "text": clean_text or text,
           "time": trigger_time.strftime("%Y-%m-%d %H:%M"),
           "done": False, "created": now.strftime("%Y-%m-%d %H:%M")}
    rems = reminders_load()
    rems.append(rem)
    reminders_save(rems)

    # 15-min warning bhi schedule karo
    warn_time = trigger_time - datetime.timedelta(minutes=15)
    if warn_time > now:
        warn = {"id": rid + 1, "text": f"15 min baad: {clean_text or text}",
                "time": warn_time.strftime("%Y-%m-%d %H:%M"),
                "done": False, "created": now.strftime("%Y-%m-%d %H:%M"), "is_warning": True}
        rems.append(warn)
        reminders_save(rems)

    time_str = trigger_time.strftime("%d %b %H:%M")
    return cg(f"⏰ Reminder set! '{clean_text or text}'\n  📅 Time: {time_str}\n  ⚠️  15-min pehle bhi alert aayega!")

def reminders_show():
    rems = reminders_load()
    pending = [r for r in rems if not r["done"]]
    if not pending: return cy("Koi pending reminder nahi hai Boss.")
    now = datetime.datetime.now()
    out = f"\n{Y}╔══ ⏰ REMINDERS ══╗{RS}\n"
    for i, r in enumerate(sorted(pending, key=lambda x: x["time"]), 1):
        rt = datetime.datetime.strptime(r["time"], "%Y-%m-%d %H:%M")
        diff = rt - now
        mins = int(diff.total_seconds() / 60)
        if mins < 0: color = R
        elif mins < 30: color = Y
        else: color = G
        if mins < 0: time_left = f"{abs(mins)}m overdue"
        elif mins < 60: time_left = f"{mins}m baad"
        elif mins < 1440: time_left = f"{mins//60}h {mins%60}m baad"
        else: time_left = r["time"]
        warn_icon = "⚠️ " if r.get("is_warning") else "⏰ "
        out += f"  {warn_icon}{BD}[{i}]{RS} {C}{r['text']}{RS}\n"
        out += f"      {color}{time_left}{RS}\n"
    out += f"{Y}╚{'═'*30}╝{RS}\n"
    return out

def reminder_done(num):
    rems = reminders_load()
    pending = [r for r in rems if not r["done"]]
    try:
        idx = int(num) - 1
        if 0 <= idx < len(pending):
            pending[idx]["done"] = True
            reminders_save(rems)
            return cg(f"✅ Reminder done: '{pending[idx]['text']}'")
    except: pass
    return cy("Reminder nahi mila Boss.")

def start_reminder_monitor():
    """Background mein reminder check karo."""
    def _monitor():
        while True:
            try:
                now = datetime.datetime.now()
                rems = reminders_load()
                changed = False
                for r in rems:
                    if r["done"]: continue
                    rt = datetime.datetime.strptime(r["time"], "%Y-%m-%d %H:%M")
                    diff = abs((rt - now).total_seconds())
                    if diff <= 60:  # 1 minute window
                        msg = f"Boss! Reminder: {r['text']}"
                        print(f"\n  {R}🔔 {msg}{RS}\n")
                        speak(msg)
                        r["done"] = True
                        changed = True
                if changed:
                    reminders_save(rems)
            except: pass
            time.sleep(30)
    t = threading.Thread(target=_monitor, daemon=True)
    t.start()

# ─── FEATURE: Wikipedia + Translation ────────────────────────
def wiki_search(query):
    """Wikipedia se quick summary lo."""
    import urllib.request as _ur, urllib.parse as _up
    print(f"  {C}🌐 Wikipedia search kar raha hoon...{RS}")
    try:
        q = _up.quote(query)
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{q}"
        req = _ur.Request(url, headers={"User-Agent": "FRIDAY-AI/1.0"})
        with _ur.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            title = data.get("title", query)
            extract = data.get("extract", "")[:800]
        if not extract:
            return cy(f"Wikipedia mein '{query}' nahi mila Boss.")
        # AI se Hinglish summary
        if GROQ_KEY:
            import urllib.request as _ur2
            pay = json.dumps({"model": MODEL, "messages": [{"role":"user","content":f"Is Wikipedia content ko 3-4 lines mein simple Hinglish mein summarize karo:\n\n{extract}"}], "max_tokens": 200}).encode()
            req2 = _ur2.Request("https://api.groq.com/openai/v1/chat/completions", data=pay,
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type":"application/json"}, method="POST")
            with _ur2.urlopen(req2, timeout=10) as r:
                summary = json.loads(r.read())["choices"][0]["message"]["content"]
        else:
            summary = extract
        out = f"\n{Y}╔══ 🌐 WIKIPEDIA: {title} ══╗{RS}\n"
        out += f"  {summary}\n"
        out += f"{Y}╚{'═'*40}╝{RS}\n"
        speak(f"Wikipedia se mila Boss. {summary[:100]}")
        return out
    except Exception as e:
        return cy(f"Wikipedia error: {e}")

def translate_text(text, target_lang="hi"):
    """Text translate karo — MyMemory free API."""
    import urllib.request as _ur, urllib.parse as _up
    lang_map = {
        "hindi": "hi", "english": "en", "bengali": "bn", "urdu": "ur",
        "arabic": "ar", "french": "fr", "spanish": "es", "german": "de",
        "japanese": "ja", "chinese": "zh"
    }
    # Language detect from command
    for lang_name, code in lang_map.items():
        if lang_name in text.lower():
            target_lang = code
            text = text.replace(lang_name, "").strip()
            break

    print(f"  {C}🌍 Translate kar raha hoon...{RS}")
    try:
        q = _up.quote(text[:500])
        url = f"https://api.mymemory.translated.net/get?q={q}&langpair=auto|{target_lang}"
        req = _ur.Request(url, headers={"User-Agent": "FRIDAY-AI/1.0"})
        with _ur.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            result = data["responseData"]["translatedText"]
        lang_names = {v: k.title() for k, v in lang_map.items()}
        out = f"\n{Y}╔══ 🌍 TRANSLATION ══╗{RS}\n"
        out += f"  Original: {C}{text[:100]}{RS}\n"
        out += f"  {lang_names.get(target_lang, target_lang)}: {G}{result}{RS}\n"
        out += f"{Y}╚{'═'*35}╝{RS}\n"
        speak(f"Translation: {result[:80]}")
        return out
    except Exception as e:
        return cy(f"Translation error: {e}")

# ─── FEATURE: Anomaly Detection ──────────────────────────────
ANOMALY_FILE = os.path.expanduser("~/.friday_anomaly.json")

def anomaly_load():
    try:
        if os.path.exists(ANOMALY_FILE):
            with open(ANOMALY_FILE) as f: return json.load(f)
    except: pass
    return {"battery_avg": [], "ram_avg": [], "alerts": [], "baseline_set": False}

def anomaly_save(data):
    try:
        with open(ANOMALY_FILE, "w") as f: json.dump(data, f, indent=2)
    except: pass

def anomaly_check():
    """Battery aur RAM patterns se anomaly detect karo."""
    data = anomaly_load()
    alerts = []
    try:
        r = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=5)
        b = json.loads(r.stdout)
        batt = b.get("percentage", 100)
        data["battery_avg"].append(batt)
        data["battery_avg"] = data["battery_avg"][-48:]  # Last 48 readings

        r2 = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=5)
        for line in r2.stdout.split("\n"):
            if line.startswith("Mem:"):
                parts = line.split()
                total, used = int(parts[1]), int(parts[2])
                ram_pct = int(used / total * 100)
                data["ram_avg"].append(ram_pct)
                data["ram_avg"] = data["ram_avg"][-48:]
                break
        else:
            ram_pct = 0

        # Anomaly checks
        if len(data["battery_avg"]) >= 10:
            avg_batt = sum(data["battery_avg"][-10:]) / 10
            # Battery achanak bahut gir gayi
            if len(data["battery_avg"]) >= 2:
                drop = data["battery_avg"][-2] - data["battery_avg"][-1]
                if drop > 15:
                    alerts.append(f"⚡ Battery achanak {drop}% gir gayi! Charging check karo.")

        if len(data["ram_avg"]) >= 5:
            avg_ram = sum(data["ram_avg"][-5:]) / 5
            if avg_ram > 88:
                alerts.append(f"🔴 RAM consistently {avg_ram:.0f}% — apps kill karo!")

        # Alerts save karo
        for a in alerts:
            data["alerts"].append({"msg": a, "time": datetime.datetime.now().strftime("%H:%M")})
        data["alerts"] = data["alerts"][-20:]
        anomaly_save(data)

        if alerts:
            for a in alerts:
                print(f"\n  {R}🚨 ANOMALY: {a}{RS}\n")
                speak(f"Boss! {a[:80]}")
    except: pass
    return alerts

def anomaly_report():
    data = anomaly_load()
    alerts = data.get("alerts", [])
    if not alerts: return cy("Koi anomaly detect nahi hui Boss. Sab normal hai!")
    out = f"\n{Y}╔══ 🚨 ANOMALY HISTORY ══╗{RS}\n"
    for a in alerts[-10:]:
        out += f"  {R}⚠️{RS} {a['msg']} {DM}({a['time']}){RS}\n"
    out += f"{Y}╚{'═'*38}╝{RS}\n"
    return out

def start_anomaly_monitor():
    """Background mein anomaly check karo — har 5 minute."""
    def _monitor():
        time.sleep(60)  # 1 min baad start
        while True:
            try: anomaly_check()
            except: pass
            time.sleep(300)  # Har 5 min
    t = threading.Thread(target=_monitor, daemon=True)
    t.start()

# ─── FEATURE: Jarvis Dashboard Upgrade ───────────────────────
def show_jarvis_dashboard():
    """Full Jarvis-style dashboard — sab kuch ek screen pe."""
    now = datetime.datetime.now()
    SEP = "═" * 56
    out = f"\n{Y}╔{SEP}╗{RS}\n"
    out += f"{Y}║{RS}{BD}{C}{'  🤖  J A R V I S  —  F R I D A Y  D A S H B O A R D':<56}{RS}{Y}║{RS}\n"
    out += f"{Y}║{RS}  {DM}{now.strftime('%A, %d %B %Y  |  %H:%M:%S'):<54}{RS}{Y}║{RS}\n"
    out += f"{Y}╠{SEP}╣{RS}\n"

    # Battery + RAM
    try:
        r = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=4)
        b = json.loads(r.stdout)
        pct = b.get("percentage", 0)
        status = b.get("status","")
        icon = "⚡" if status == "CHARGING" else "🔋"
        bc = G if pct > 50 else (Y if pct > 20 else R)
        bar = bc + "█" * (pct//10) + DM + "░" * (10-pct//10) + RS
        out += f"{Y}║{RS}  {icon} Battery  {bar} {bc}{pct}%{RS}\n"
    except:
        out += f"{Y}║{RS}  🔋 Battery  {DM}N/A{RS}\n"

    try:
        r2 = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=4)
        for line in r2.stdout.split("\n"):
            if line.startswith("Mem:"):
                parts = line.split()
                total, used = int(parts[1]), int(parts[2])
                pct2 = int(used/total*100)
                rc = G if pct2 < 60 else (Y if pct2 < 80 else R)
                bar2 = rc + "█" * (pct2//10) + DM + "░" * (10-pct2//10) + RS
                out += f"{Y}║{RS}  💾 RAM      {bar2} {rc}{pct2}%{RS}  {DM}({used}/{total}MB){RS}\n"
    except:
        out += f"{Y}║{RS}  💾 RAM      {DM}N/A{RS}\n"

    out += f"{Y}╠{SEP}╣{RS}\n"

    # Weather
    try:
        import urllib.request as _ur
        loc = ltmem_load().get("topics", {}).get("city", {})
        city = loc.get("value", "Kolkata") if isinstance(loc, dict) else "Kolkata"
        import urllib.parse as _up
        wurl = f"https://wttr.in/{_up.quote(city)}?format=%C+%t+%h"
        req = _ur.Request(wurl, headers={"User-Agent":"curl/7.0"})
        with _ur.urlopen(req, timeout=5) as wr:
            weather = wr.read().decode().strip()
        out += f"{Y}║{RS}  🌤️  Weather  {C}{weather}{RS}\n"
    except:
        out += f"{Y}║{RS}  🌤️  Weather  {DM}N/A{RS}\n"

    out += f"{Y}╠{SEP}╣{RS}\n"

    # Todos
    try:
        todos = todo_load()
        pending = [t for t in todos if not t["done"]]
        icons_p = {"urgent":"🔴","high":"🟠","medium":"🟡","low":"🟢"}
        out += f"{Y}║{RS}  ✅ Todos ({len(pending)} pending)\n"
        for t in pending[:3]:
            out += f"{Y}║{RS}    {icons_p.get(t['priority'],'🟡')} {t['text'][:45]}\n"
    except:
        out += f"{Y}║{RS}  ✅ Todos    {DM}N/A{RS}\n"

    out += f"{Y}╠{SEP}╣{RS}\n"

    # Reminders
    try:
        rems = [r for r in reminders_load() if not r["done"]]
        out += f"{Y}║{RS}  ⏰ Reminders ({len(rems)} active)\n"
        for r in sorted(rems, key=lambda x: x["time"])[:3]:
            out += f"{Y}║{RS}    🔔 {r['text'][:40]}  {DM}{r['time'][11:]}{RS}\n"
    except:
        out += f"{Y}║{RS}  ⏰ Reminders {DM}N/A{RS}\n"

    out += f"{Y}╠{SEP}╣{RS}\n"

    # Expense + Budget
    try:
        exps = expense_load()
        today = now.strftime("%Y-%m-%d")
        today_exp = sum(float(e.get("amount",0)) for e in exps if e.get("date","").startswith(today))
        budget_data = {}
        bfile = os.path.expanduser("~/.friday_budget.json")
        if os.path.exists(bfile):
            budget_data = json.load(open(bfile))
        limit = budget_data.get("monthly_limit", 0)
        month = now.strftime("%Y-%m")
        monthly = sum(float(e.get("amount",0)) for e in exps if e.get("date","").startswith(month))
        out += f"{Y}║{RS}  💰 Aaj: {G}₹{today_exp:.0f}{RS}   Month: {Y}₹{monthly:.0f}{RS}"
        if limit: out += f"  {DM}/ ₹{limit}{RS}"
        out += "\n"
    except:
        out += f"{Y}║{RS}  💰 Expense   {DM}N/A{RS}\n"

    out += f"{Y}╠{SEP}╣{RS}\n"

    # Anomaly alerts
    try:
        anomaly_data = anomaly_load()
        recent_alerts = anomaly_data.get("alerts", [])[-3:]
        if recent_alerts:
            out += f"{Y}║{RS}  🚨 Recent Alerts\n"
            for a in recent_alerts:
                out += f"{Y}║{RS}    ⚠️  {a['msg'][:45]}  {DM}{a['time']}{RS}\n"
        else:
            out += f"{Y}║{RS}  🚨 Anomaly    {G}All clear!{RS}\n"
    except:
        out += f"{Y}║{RS}  🚨 Anomaly    {DM}N/A{RS}\n"

    out += f"{Y}╚{SEP}╝{RS}\n"
    return out



# ═══════════════════════════════════════════════════════════════
# MULTI-AGENT SYSTEM — Expert AIs with Central Brain
# ═══════════════════════════════════════════════════════════════

AGENTS = {
    "finance": {
        "name": "FinBot",
        "icon": "💰",
        "system": """You are FinBot, FRIDAY's Finance Expert AI for Boss MIRAZ.
You specialize in: expense tracking, budget advice, savings tips, investment basics, financial planning.
Always respond in simple Hinglish (Roman Hindi + English mix).
Be concise, practical, and give actionable advice.
If asked about expenses, reference that MIRAZ tracks expenses in FRIDAY.""",
        "keywords": ["kharch", "budget", "paisa", "invest", "bachat", "loan", "salary", "expense", "money", "finance", "save", "saving", "spending"]
    },
    "health": {
        "name": "HealthBot",
        "icon": "💪",
        "system": """You are HealthBot, FRIDAY's Health & Fitness Expert AI for Boss MIRAZ.
You specialize in: fitness advice, diet, nutrition, sleep, mental health, exercise routines, water intake.
Always respond in simple Hinglish. Be encouraging and motivating.
Give practical, safe health advice. Always suggest consulting a doctor for medical issues.""",
        "keywords": ["health", "fitness", "exercise", "diet", "khana", "neend", "sleep", "paani", "water", "weight", "gym", "yoga", "protein", "calories", "mental", "stress"]
    },
    "tech": {
        "name": "TechBot",
        "icon": "💻",
        "system": """You are TechBot, FRIDAY's Technology Expert AI for Boss MIRAZ.
You specialize in: programming, Python, Android, Termux, AI/ML, coding help, debugging, tech news, apps.
Always respond in simple Hinglish. Give working code examples when needed.
You know FRIDAY is built in Python running on Termux/Android.""",
        "keywords": ["code", "python", "programming", "bug", "error", "app", "android", "termux", "ai", "ml", "tech", "software", "install", "kaise banao", "script", "api", "github"]
    },
    "creative": {
        "name": "CreativeBot",
        "icon": "🎨",
        "system": """You are CreativeBot, FRIDAY's Creative Expert AI for Boss MIRAZ.
You specialize in: creative writing, poetry, story ideas, jokes, song lyrics, design ideas, brainstorming, content creation.
Always respond in Hinglish. Be creative, fun, and inspiring.
Write engaging content that matches MIRAZ's style.""",
        "keywords": ["poem", "kavita", "story", "kahani", "joke", "mazak", "write", "likho", "creative", "idea", "design", "content", "song", "lyrics", "geet", "shayari", "caption"]
    },
    "life": {
        "name": "LifeBot",
        "icon": "🌟",
        "system": """You are LifeBot, FRIDAY's Life Coach & Personal Advisor AI for Boss MIRAZ.
You specialize in: motivation, productivity, goal setting, relationships, time management, mindset, personal growth.
Always respond in warm, encouraging Hinglish. Be like a wise friend.
Help MIRAZ grow personally and professionally.""",
        "keywords": ["motivation", "goal", "life", "relationship", "advice", "problem", "help", "career", "future", "success", "productivity", "habit", "mindset", "growth", "inspire"]
    },
    "news": {
        "name": "NewsBot",
        "icon": "📰",
        "system": """You are NewsBot, FRIDAY's News & Knowledge Expert AI for Boss MIRAZ.
You specialize in: current events, world news, sports, entertainment, technology news, general knowledge, fact checking.
Always respond in Hinglish. Summarize news clearly and concisely.
Be objective and present facts accurately. Mention if something is uncertain.""",
        "keywords": ["news", "khabar", "aaj", "today", "sports", "cricket", "football", "match", "world", "india", "politics", "election", "happening", "latest", "current"]
    }
}

def agent_detect(user_input):
    """User input se best agent detect karo."""
    text = user_input.lower()
    scores = {}
    for agent_id, agent in AGENTS.items():
        score = sum(1 for kw in agent["keywords"] if kw in text)
        if score > 0:
            scores[agent_id] = score
    if scores:
        return max(scores, key=scores.get)
    return None

def agent_ask(agent_id, user_input, context=""):
    """Specific expert agent se poochho."""
    if agent_id not in AGENTS:
        return None
    agent = AGENTS[agent_id]
    if not GROQ_KEY:
        return None
    try:
        import urllib.request as _ur
        messages = [{"role": "system", "content": agent["system"]}]
        if context:
            messages.append({"role": "user", "content": f"Context: {context}"})
            messages.append({"role": "assistant", "content": "Understood, I have the context."})
        messages.append({"role": "user", "content": user_input})

        pay = json.dumps({
            "model": MODEL,
            "messages": messages,
            "max_tokens": 400
        }).encode()
        req = _ur.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=pay,
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            method="POST"
        )
        with _ur.urlopen(req, timeout=15) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"]
    except Exception as e:
        log_warn(f"Agent {agent_id} error: {e}")
        return None

def agent_central_brain(user_input, mem, ltm):
    """Central Brain — query ko sahi expert ke paas bhejo."""
    # Agent detect karo
    agent_id = agent_detect(user_input)

    # LTM se context lo
    context = ltmem_get_context(ltm, user_input)

    if agent_id:
        agent = AGENTS[agent_id]
        print(f"  {DM}🤖 {agent['icon']} {agent['name']} active...{RS}")
        response = agent_ask(agent_id, user_input, context)
        if response:
            G2="\033[92m"; Y2="\033[93m"; C2="\033[96m"; RS2="\033[0m"; BD2="\033[1m"
            out = f"\n{Y2}╔══ {agent['icon']} {agent['name'].upper()} ══╗{RS2}\n"
            # Format response — clean lines
            lines = [l.strip() for l in response.split('\n') if l.strip()]
            for line in lines:
                out += f"  {line}\n"
            out += f"{Y2}╚{'═'*35}╝{RS2}\n"
            speak(response)
            return out
    return None  # Normal AI handle karega

def agent_status():
    """Saare agents ka status dikhao."""
    out = f"\n{Y}╔══ 🤖 MULTI-AGENT STATUS ══╗{RS}\n"
    out += f"  {BD}Central Brain:{RS} {G}Active{RS} (Groq {MODEL})\n\n"
    out += f"  {BD}Expert Agents:{RS}\n"
    for aid, agent in AGENTS.items():
        kw_count = len(agent['keywords'])
        out += f"  {agent['icon']} {C}{agent['name']:<12}{RS} {G}Ready{RS}  {DM}({kw_count} triggers){RS}\n"
    out += f"\n  {DM}Auto-detect: ON — Agent automatically choose hoga{RS}\n"
    out += f"{Y}╚{'═'*38}╝{RS}\n"
    return out



# ═══════════════════════════════════════════════════════════════
# FEATURE: Emotion Detection
# ═══════════════════════════════════════════════════════════════
EMOTION_FILE = os.path.expanduser("~/.friday_emotions.json")
EMOTION_PATTERNS = {
    "khush":    ["khush", "happy", "mast", "badhiya", "maja", "awesome", "great", "love"],
    "thaka":    ["thaka", "tired", "neend", "bore", "bored", "exhausted"],
    "gussa":    ["gussa", "angry", "galat", "bekar", "worst", "hate", "mat karo"],
    "sad":      ["sad", "dukh", "rona", "bura", "miss", "akela", "alone", "depressed"],
    "stressed": ["stress", "tension", "problem", "mushkil", "pareshan", "worried"],
    "excited":  ["excited", "wow", "wah", "amazing", "incredible", "yaar"],
    "neutral":  []
}
def emotion_detect(text):
    t = text.lower()
    scores = {}
    for emotion, keywords in EMOTION_PATTERNS.items():
        if emotion == "neutral": continue
        scores[emotion] = sum(1 for kw in keywords if kw in t)
    if not scores or max(scores.values()) == 0: return "neutral"
    return max(scores, key=scores.get)

def emotion_track(text):
    emotion = emotion_detect(text)
    if emotion == "neutral": return emotion
    try:
        data = []
        if os.path.exists(EMOTION_FILE):
            with open(EMOTION_FILE) as f: data = json.load(f)
        data.append({"emotion": emotion, "text": text[:80], "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
        data = data[-100:]
        with open(EMOTION_FILE, "w") as f: json.dump(data, f, indent=2, ensure_ascii=False)
    except: pass
    return emotion

def emotion_response(emotion):
    responses = {
        "khush": "Boss khush lagte hain aaj! Main bhi khush hoon!",
        "thaka": "Boss thake hue lagte hain. Thodi rest lo, main hoon na!",
        "gussa": "Lagta hai kuch pareshani hai Boss. Kya hua?",
        "sad":   "Boss, sab theek ho jaayega. Main aapke saath hoon hamesha.",
        "stressed": "Tension mat lo Boss! Ek ek kaam karte hain.",
        "excited": "Wah Boss! Energy full hai aaj! Kya plan hai?",
    }
    return responses.get(emotion, "")

def emotion_history():
    try:
        if not os.path.exists(EMOTION_FILE): return cy("Koi emotion data nahi hai Boss.")
        with open(EMOTION_FILE) as f: data = json.load(f)
        if not data: return cy("Koi emotion data nahi hai Boss.")
        counts = {}
        for d in data[-50:]:
            e = d["emotion"]
            counts[e] = counts.get(e, 0) + 1
        icons = {"khush":"😊","thaka":"😴","gussa":"😡","sad":"😢","stressed":"😰","excited":"🔥"}
        out = "\n" + Y + "╔══ 🧠 EMOTION HISTORY ══╗" + RS + "\n"
        for emotion, count in sorted(counts.items(), key=lambda x: -x[1]):
            bar = G + "█" * min(count, 20) + RS
            out += f"  {icons.get(emotion,'😐')} {C}{emotion:<10}{RS} {bar} {count}x\n"
        out += "\n  " + BD + "Recent:" + RS + "\n"
        for d in data[-5:]:
            out += f"  {DM}{d['time'][11:]}{RS} {icons.get(d['emotion'],'😐')} {d['text'][:40]}\n"
        out += Y + "╚" + "═"*35 + "╝" + RS + "\n"
        return out
    except Exception as e: return cy(f"Error: {e}")

# ═══════════════════════════════════════════════════════════════
# FEATURE: Predictive AI
# ═══════════════════════════════════════════════════════════════
PREDICT_FILE = os.path.expanduser("~/.friday_predict.json")
def predict_load():
    try:
        if os.path.exists(PREDICT_FILE):
            with open(PREDICT_FILE) as f: return json.load(f)
    except: pass
    return {"sequences": []}

def predict_save(data):
    try:
        with open(PREDICT_FILE, "w") as f: json.dump(data, f, indent=2)
    except: pass

def predict_track(cmd):
    data = predict_load()
    data["sequences"].append({"cmd": cmd[:50], "hour": datetime.datetime.now().hour})
    data["sequences"] = data["sequences"][-200:]
    predict_save(data)

def predict_time_suggestion():
    data = predict_load()
    hour = datetime.datetime.now().hour
    seqs = [s for s in data.get("sequences", []) if s.get("hour") == hour]
    if len(seqs) < 5: return None
    cmd_counts = {}
    for s in seqs:
        base = s["cmd"].split()[0]
        cmd_counts[base] = cmd_counts.get(base, 0) + 1
    if cmd_counts:
        top = max(cmd_counts, key=cmd_counts.get)
        if cmd_counts[top] >= 3:
            return f"Boss, is waqt aap usually {top} use karte hain!"
    return None

# ═══════════════════════════════════════════════════════════════
# FEATURE: Habit Tracker + Life Score
# ═══════════════════════════════════════════════════════════════
HABIT_FILE = os.path.expanduser("~/.friday_habits.json")
DEFAULT_HABITS = [
    {"id": "paani",    "name": "8 glass paani",   "icon": "💧", "target": 8,  "unit": "glass"},
    {"id": "exercise", "name": "Exercise 30 min",  "icon": "💪", "target": 30, "unit": "min"},
    {"id": "neend",    "name": "7 ghante neend",   "icon": "😴", "target": 7,  "unit": "ghante"},
    {"id": "reading",  "name": "Padhai 20 min",    "icon": "📚", "target": 20, "unit": "min"},
    {"id": "mood_log", "name": "Mood log karo",    "icon": "😊", "target": 1,  "unit": "baar"},
]
def habits_load():
    try:
        if os.path.exists(HABIT_FILE):
            with open(HABIT_FILE) as f: return json.load(f)
    except: pass
    return {"habits": DEFAULT_HABITS, "logs": []}

def habits_save(data):
    try:
        with open(HABIT_FILE, "w") as f: json.dump(data, f, indent=2, ensure_ascii=False)
    except: pass

def habit_log_entry(habit_id, value=1):
    data = habits_load()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    habit = next((h for h in data["habits"] if h["id"] == habit_id), None)
    if not habit: return cy(f"Habit nahi mili: {habit_id}. 'habits' se list dekho.")
    data["logs"].append({"habit_id": habit_id, "value": value, "date": today, "time": datetime.datetime.now().strftime("%H:%M")})
    data["logs"] = data["logs"][-500:]
    habits_save(data)
    return cg(f"✅ {habit['icon']} {habit['name']} — {value} {habit['unit']} logged!")

def habits_today():
    data = habits_load()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    today_logs = [l for l in data["logs"] if l["date"] == today]
    out = "\n" + Y + "╔══ 🏆 HABITS & LIFE SCORE ══╗" + RS + "\n"
    total_score = 0
    max_score = len(data["habits"]) * 10
    for habit in data["habits"]:
        logged = sum(l["value"] for l in today_logs if l["habit_id"] == habit["id"])
        target = habit["target"]
        pct = min(100, int(logged / target * 100)) if target > 0 else 0
        total_score += int(pct / 10)
        bar = G + "█" * int(pct/10) + DM + "░" * (10-int(pct/10)) + RS
        status = "✅" if pct >= 100 else ("🟡" if pct >= 50 else "❌")
        out += f"  {status} {habit['icon']} {C}{habit['name']:<20}{RS}\n"
        out += f"     {bar} {pct}% ({logged}/{target} {habit['unit']})\n"
    life_pct = int(total_score / max_score * 100) if max_score > 0 else 0
    sc = G if life_pct >= 70 else (Y if life_pct >= 40 else R)
    msg = "Excellent! 🔥" if life_pct >= 80 else ("Good job! 👍" if life_pct >= 60 else ("Aur karo!" if life_pct >= 40 else "Koshish karo Boss! 💪"))
    out += f"\n  {BD}🌟 LIFE SCORE: {sc}{life_pct}%{RS}  {msg}\n"
    out += Y + "╚" + "═"*38 + "╝" + RS + "\n"
    speak(f"Aaj ka life score {life_pct} percent hai Boss!")
    return out

def habits_streak():
    data = habits_load()
    out = "\n" + Y + "╔══ 🔥 HABIT STREAKS ══╗" + RS + "\n"
    for habit in data["habits"]:
        streak = 0
        for i in range(30):
            d = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            if any(l for l in data["logs"] if l["date"] == d and l["habit_id"] == habit["id"]):
                streak += 1
            else: break
        fire = "🔥" * min(streak, 5) if streak > 0 else "💤"
        out += f"  {habit['icon']} {C}{habit['name']:<20}{RS} {fire} {streak} din\n"
    out += Y + "╚" + "═"*35 + "╝" + RS + "\n"
    return out

# ═══════════════════════════════════════════════════════════════
# FEATURE: Alarm Set
# ═══════════════════════════════════════════════════════════════
ALARM_FILE = os.path.expanduser("~/.friday_alarms.json")
def alarms_load():
    try:
        if os.path.exists(ALARM_FILE):
            with open(ALARM_FILE) as f: return json.load(f)
    except: pass
    return []

def alarms_save(data):
    try:
        with open(ALARM_FILE, "w") as f: json.dump(data, f, indent=2)
    except: pass

def alarm_add(text):
    import re as _re
    now = datetime.datetime.now()
    alarm_time = None
    label = text
    for pat, ptype in [(r"(\d+)\s*:\s*(\d+)", "hhmm"), (r"kal\s+(\d+)\s*baje", "tomorrow"),
                       (r"(\d+)\s*baje", "clock"), (r"(\d+)\s*min", "minutes")]:
        m = _re.search(pat, text.lower())
        if m:
            if ptype == "hhmm":
                h, mi = int(m.group(1)), int(m.group(2))
                alarm_time = now.replace(hour=h, minute=mi, second=0)
                if alarm_time < now: alarm_time += datetime.timedelta(days=1)
            elif ptype == "tomorrow":
                alarm_time = (now + datetime.timedelta(days=1)).replace(hour=int(m.group(1)), minute=0, second=0)
            elif ptype == "clock":
                alarm_time = now.replace(hour=int(m.group(1)), minute=0, second=0)
                if alarm_time < now: alarm_time += datetime.timedelta(days=1)
            elif ptype == "minutes":
                alarm_time = now + datetime.timedelta(minutes=int(m.group(1)))
            label = _re.sub(pat, "", text, flags=_re.I).strip(" ,-")
            break
    if not alarm_time:
        return cy("Time samajh nahi aaya!\nJaise: alarm 7 baje\nYa: alarm kal 6:30\nYa: alarm 30 min")
    alarms = alarms_load()
    alarms.append({"id": int(now.timestamp()), "label": label or "Alarm",
                   "time": alarm_time.strftime("%Y-%m-%d %H:%M"), "active": True, "rung": False})
    alarms_save(alarms)
    return cg(f"⏰ Alarm set! '{label or text}'\n  🕐 {alarm_time.strftime('%d %b %I:%M %p')}")

def alarms_show():
    alarms = alarms_load()
    active = [a for a in alarms if a["active"] and not a["rung"]]
    if not active: return cy("Koi active alarm nahi hai Boss.")
    now = datetime.datetime.now()
    out = "\n" + Y + "╔══ ⏰ ALARMS ══╗" + RS + "\n"
    for i, a in enumerate(sorted(active, key=lambda x: x["time"]), 1):
        at = datetime.datetime.strptime(a["time"], "%Y-%m-%d %H:%M")
        diff = int((at - now).total_seconds() / 60)
        tstr = f"{R}overdue{RS}" if diff < 0 else (f"{Y}{diff}m baad{RS}" if diff < 60 else f"{G}{diff//60}h {diff%60}m baad{RS}")
        out += f"  ⏰ {BD}[{i}]{RS} {C}{a['label']}{RS} — {tstr}\n"
        out += f"      📅 {a['time'][11:]}\n"
    out += Y + "╚" + "═"*30 + "╝" + RS + "\n"
    return out

def start_alarm_monitor():
    def _monitor():
        while True:
            try:
                now = datetime.datetime.now()
                alarms = alarms_load()
                changed = False
                for a in alarms:
                    if not a["active"] or a["rung"]: continue
                    at = datetime.datetime.strptime(a["time"], "%Y-%m-%d %H:%M")
                    if abs((at - now).total_seconds()) <= 60:
                        print(f"\n  {R}🔔 ⏰ ALARM: {a['label']}{RS}\n")
                        speak(f"Boss! Alarm! {a['label']}")
                        try: subprocess.Popen(["termux-vibrate", "-d", "2000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except: pass
                        a["rung"] = True; changed = True
                if changed: alarms_save(alarms)
            except: pass
            time.sleep(30)
    threading.Thread(target=_monitor, daemon=True).start()

# ═══════════════════════════════════════════════════════════════
# FEATURE: SMS Reader
# ═══════════════════════════════════════════════════════════════
def sms_read(count=5):
    try:
        r = subprocess.run(["termux-sms-list", "-l", str(count)], capture_output=True, text=True, timeout=10)
        msgs = json.loads(r.stdout)
        if not msgs: return cy("Koi SMS nahi mili Boss.")
        out = "\n" + Y + "╔══ 📱 SMS INBOX ══╗" + RS + "\n"
        for m in msgs[:count]:
            out += f"  {C}From: {m.get('number','?')}{RS}\n"
            out += f"  {W}{m.get('body','')[:80]}{RS}\n"
            out += f"  {DM}{m.get('received','')[:16]}{RS}\n  {'─'*35}\n"
        out += Y + "╚" + "═"*30 + "╝" + RS + "\n"
        speak(f"Boss {len(msgs)} messages hain inbox mein!")
        return out
    except FileNotFoundError: return cy("SMS ke liye termux-api install karo!\npkg install termux-api")
    except Exception as e: return cy(f"SMS error: {e}")

def call_contact(name_or_number):
    import re as _re
    if _re.match(r"^[\d\+\-\s]+$", name_or_number.strip()):
        number = name_or_number.strip().replace(" ", "")
        speak(f"Calling {number} Boss!")
        return do_call(number)
    try:
        r = subprocess.run(["termux-contact-list"], capture_output=True, text=True, timeout=10)
        contacts = json.loads(r.stdout)
        for c in contacts:
            if name_or_number.lower() in c.get("name","").lower():
                number = c.get("number","").replace(" ","")
                speak(f"Calling {c['name']} Boss!")
                return do_call(number)
        return cy(f"Contact nahi mila: {name_or_number}")
    except Exception as e: return cy(f"Call error: {e}")



# ═══════════════════════════════════════════════════════════════
# FEATURE: Live News — India + World
# ═══════════════════════════════════════════════════════════════
def get_live_news(category="india", count=5):
    """RSS feeds se live news lo."""
    import urllib.request as _ur
    import urllib.parse as _up
    import re as _re

    feeds = {
        "india":   "https://news.google.com/rss/headlines/section/geo/IN?hl=en-IN&gl=IN&ceid=IN:en",
        "world":   "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en&gl=US&ceid=US:en",
        "tech":    "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en&gl=US&ceid=US:en",
        "sports":  "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=en&gl=US&ceid=US:en",
        "business":"https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en&gl=US&ceid=US:en",
    }
    feed_url = feeds.get(category.lower(), feeds["india"])
    try:
        req = _ur.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
        with _ur.urlopen(req, timeout=10) as r:
            xml = r.read().decode("utf-8", errors="ignore")
        # Parse titles from RSS
        titles = _re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", xml)
        if not titles:
            titles = _re.findall(r"<title>(.*?)</title>", xml)
        # Remove first (feed title)
        titles = [t for t in titles if "Google News" not in t and len(t) > 10][:count]
        if not titles:
            return cy("News nahi mili Boss. Internet check karo.")
        cat_icons = {"india":"🇮🇳","world":"🌍","tech":"💻","sports":"🏏","business":"📈"}
        icon = cat_icons.get(category, "📰")
        out = f"\n{Y}╔══ {icon} {category.upper()} NEWS ══╗{RS}\n"
        for i, title in enumerate(titles, 1):
            # Clean HTML entities
            title = title.replace("&amp;","&").replace("&lt;","<").replace("&gt;",">").replace("&quot;",'"').replace("&#39;","'")
            out += f"  {BD}{i}.{RS} {C}{title}{RS}\n"
        out += f"\n  {DM}Source: Google News{RS}\n"
        out += f"{Y}╚{'═'*45}╝{RS}\n"
        # Speak top headline
        speak(f"Top headline: {titles[0][:80]}")
        return out
    except Exception as e:
        return cy(f"News error Boss: {e}")

# ═══════════════════════════════════════════════════════════════
# FEATURE: Stock Market + Crypto
# ═══════════════════════════════════════════════════════════════
def get_stock_price(symbol):
    """Yahoo Finance se stock/crypto price lo."""
    import urllib.request as _ur
    import re as _re
    symbol = symbol.upper().strip()
    # Common aliases
    aliases = {
        "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "INFOSYS": "INFY.NS",
        "WIPRO": "WIPRO.NS", "HDFC": "HDFCBANK.NS", "SBI": "SBIN.NS",
        "TATAMOTORS": "TATAMOTORS.NS", "ADANI": "ADANIENT.NS",
        "BITCOIN": "BTC-USD", "BTC": "BTC-USD", "ETH": "ETH-USD",
        "ETHEREUM": "ETH-USD", "DOGE": "DOGE-USD", "USDT": "USDT-USD",
        "NIFTY": "^NSEI", "SENSEX": "^BSESN",
    }
    sym = aliases.get(symbol, symbol)
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
        req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _ur.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        meta = data["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice", 0)
        prev = meta.get("chartPreviousClose", price)
        change = price - prev
        change_pct = (change / prev * 100) if prev else 0
        currency = meta.get("currency", "USD")
        curr_sym = "₹" if currency == "INR" else ("$" if currency == "USD" else currency)
        color = G if change >= 0 else R
        arrow = "▲" if change >= 0 else "▼"
        out = f"\n{Y}╔══ 📈 {symbol} ══╗{RS}\n"
        out += f"  {BD}Price:{RS} {color}{curr_sym}{price:,.2f}{RS}\n"
        out += f"  {BD}Change:{RS} {color}{arrow} {abs(change):.2f} ({abs(change_pct):.2f}%){RS}\n"
        out += f"  {DM}Exchange: {meta.get('exchangeName','')}{RS}\n"
        out += f"{Y}╚{'═'*30}╝{RS}\n"
        speak(f"{symbol} price hai {curr_sym}{price:.0f}, {arrow} {abs(change_pct):.1f} percent Boss!")
        return out
    except Exception as e:
        return cy(f"Stock data nahi mila Boss: {e}\nCheck karo symbol sahi hai: {symbol}")

def get_crypto_summary():
    """Top cryptos ka quick summary."""
    coins = ["BTC-USD", "ETH-USD", "DOGE-USD"]
    out = f"\n{Y}╔══ 🪙 CRYPTO SUMMARY ══╗{RS}\n"
    import urllib.request as _ur
    for sym in coins:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
            req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with _ur.urlopen(req, timeout=8) as r:
                data = json.loads(r.read())
            meta = data["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice", 0)
            prev = meta.get("chartPreviousClose", price)
            pct = ((price - prev) / prev * 100) if prev else 0
            color = G if pct >= 0 else R
            arrow = "▲" if pct >= 0 else "▼"
            name = sym.replace("-USD","")
            out += f"  {C}{name:<6}{RS} ${price:>10,.2f}  {color}{arrow}{abs(pct):.1f}%{RS}\n"
        except:
            out += f"  {C}{sym.replace('-USD',''):<6}{RS}  {DM}N/A{RS}\n"
    out += f"{Y}╚{'═'*30}╝{RS}\n"
    return out

# ═══════════════════════════════════════════════════════════════
# FEATURE: Cricket / Sports Live Score
# ═══════════════════════════════════════════════════════════════

def get_nasa_apod():
    """NASA Astronomy Picture of the Day — free, no key needed."""
    try:
        import urllib.request, json
        url = "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY"
        r = urllib.request.urlopen(url, timeout=8).read()
        d = json.loads(r)
        title = d.get("title", "Unknown")
        date = d.get("date", "")
        explanation = d.get("explanation", "")[:200]
        media = d.get("media_type", "image")
        url_img = d.get("url", "")
        
        import requests as _req
        prompt = f"Yeh NASA ki astronomy info hai — Title: {title}, Description: {explanation}. Isse Roman Hindi mein summarize karo — matlab Hindi bolna hai lekin ENGLISH LETTERS mein likhna hai, Devanagari script bilkul nahi. 3-4 lines, exciting aur interesting banao!"
        res = _req.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
            json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],"max_tokens":200},
            timeout=10)
        summary = res.json()["choices"][0]["message"]["content"].strip()
        
        Y="\033[93m"; C="\033[96m"; RS="\033[0m"; W="\033[97m"
        out = f"\n{Y}╔══ 🚀 NASA — Aaj Ka Space Fact ══╗{RS}\n"
        out += f"  📅 Date  : {C}{date}{RS}\n"
        out += f"  🌟 Title : {W}{title}{RS}\n\n"
        out += f"  {summary}\n"

        out += f"{Y}╚{'═'*40}╝{RS}\n"
        return out
    except Exception as e:
        return f"NASA API error: {e}"

def get_cricket_score():
    """Cricbuzz RSS se live cricket score lo."""
    import urllib.request as _ur
    import re as _re
    try:
        url = "https://www.cricbuzz.com/cricket-match/live-scores"
        req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0 (Android 10)"})
        with _ur.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")
        # Extract match info
        matches = _re.findall(r'<div[^>]*cb-col[^>]*cb-col-100[^>]*cb-ltst-wgt-hdr[^>]*>(.*?)</div>', html, _re.S)
        scores = _re.findall(r'<div[^>]*cb-scr-wll-chvrn[^>]*>(.*?)</div>', html, _re.S)
        # Clean HTML tags
        def clean(t): return _re.sub(r'<[^>]+>', '', t).strip()
        out = f"\n{Y}╔══ 🏏 CRICKET LIVE ══╗{RS}\n"
        if not matches:
            # Fallback — search for score patterns
            score_blocks = _re.findall(r'((?:IND|PAK|AUS|ENG|SA|NZ|WI|SL|BAN|AFG)[^<]{5,60})', html)
            score_blocks = list(dict.fromkeys(score_blocks))[:5]
            if score_blocks:
                for s in score_blocks:
                    out += f"  🏏 {C}{clean(s)[:60]}{RS}\n"
            else:
                out += f"  {DM}Abhi koi live match nahi hai Boss{RS}\n"
        else:
            for m in matches[:3]:
                out += f"  🏏 {C}{clean(m)[:60]}{RS}\n"
        out += f"{Y}╚{'═'*40}╝{RS}\n"
        speak("Cricket score check kar liya Boss!")
        return out
    except Exception as e:
        return cy(f"Cricket score error: {e}")

def get_sports_news():
    """Google News se sports news lo."""
    return get_live_news("sports", 5)

# ═══════════════════════════════════════════════════════════════
# FEATURE: YouTube Trending + Social Buzz
# ═══════════════════════════════════════════════════════════════
def get_youtube_trending():
    """YouTube trending India."""
    import urllib.request as _ur
    import re as _re
    try:
        url = "https://www.youtube.com/feed/trending?gl=IN&hl=en"
        req = _ur.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 10)",
            "Accept-Language": "en-IN,en;q=0.9"
        })
        with _ur.urlopen(req, timeout=12) as r:
            html = r.read().decode("utf-8", errors="ignore")
        # Extract video titles
        titles = _re.findall(r'"title":\s*\{"runs":\[\{"text":"([^"]{10,80})"', html)
        titles = list(dict.fromkeys(titles))[:8]  # Deduplicate
        if not titles:
            # Fallback pattern
            titles = _re.findall(r'title":"([^"]{15,80})"', html)
            titles = [t for t in dict.fromkeys(titles) if not t.startswith("http")][:8]
        out = f"\n{Y}╔══ 🔥 YOUTUBE TRENDING INDIA ══╗{RS}\n"
        if titles:
            for i, t in enumerate(titles[:8], 1):
                out += f"  {BD}{i}.{RS} {C}{t}{RS}\n"
        else:
            out += f"  {DM}Trending data nahi mila Boss. Try karo: news tech{RS}\n"
        out += f"{Y}╚{'═'*42}╝{RS}\n"
        speak(f"YouTube trending mein top video hai: {titles[0][:60] if titles else 'data nahi mila'}")
        return out
    except Exception as e:
        return cy(f"YouTube trending error: {e}")

def get_social_buzz():
    """Tech + Social media trending topics."""
    import urllib.request as _ur
    import re as _re
    try:
        # GitHub trending
        url = "https://github.com/trending"
        req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _ur.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")
        repos = _re.findall(r'<h2[^>]*lh-condensed[^>]*>\s*<a[^>]*>([^<]+)</a>', html)
        repos = [r.strip().replace("\n","").replace("  ","") for r in repos[:5] if r.strip()]
        out = f"\n{Y}╔══ 🌐 SOCIAL + TECH BUZZ ══╗{RS}\n"
        if repos:
            out += f"  {BD}🔥 GitHub Trending:{RS}\n"
            for r in repos[:5]:
                out += f"    {C}• {r[:50]}{RS}\n"
        # Also add tech news
        out += f"\n  {BD}📱 Tech News:{RS}\n"
        tech_news = get_live_news("tech", 3)
        # Extract just titles from tech news
        import re as _r2
        tech_titles = _r2.findall(rf"{BD}\d+\.{RS} {C}(.*?){RS}", tech_news)
        for t in tech_titles[:3]:
            out += f"    {C}• {t[:50]}{RS}\n"
        out += f"{Y}╚{'═'*40}╝{RS}\n"
        speak("Social aur tech buzz check kar liya Boss!")
        return out
    except Exception as e:
        return cy(f"Social buzz error: {e}")


def file_clean_downloads():
    """Downloads mein se duplicate aur junk files delete karo."""
    folder = _resolve_dir()
    if not folder:
        return cy("Downloads folder nahi mila Boss.")

    junk_exts   = [".tmp", ".crdownload", ".part", ".download", "thumbs.db", ".ds_store"]
    junk_files  = []
    seen_names  = {}
    duplicates  = []

    for f in os.listdir(folder):
        fp = os.path.join(folder, f)
        if not os.path.isfile(fp):
            continue
        ext = os.path.splitext(f)[1].lower()
        name_lower = f.lower()

        # Junk check
        if ext in junk_exts or name_lower in [j.lstrip(".") for j in junk_exts]:
            junk_files.append(fp)
            continue

        # Duplicate check — same name without (1),(2) suffix
        base = re.sub(r" \(\d+\)", "", os.path.splitext(f)[0]).strip().lower()
        key  = base + ext
        if key in seen_names:
            duplicates.append(fp)
        else:
            seen_names[key] = fp

    deleted = 0
    for fp in junk_files + duplicates:
        try:
            os.remove(fp)
            deleted += 1
        except: pass

    out  = f"\n{Y}╔══ 🧹 CLEAN REPORT ══╗{RS}\n"
    out += f"  {C}Junk files : {RS}{W}{len(junk_files)}{RS}\n"
    out += f"  {C}Duplicates : {RS}{W}{len(duplicates)}{RS}\n"
    out += f"  {G}✓ Deleted  : {RS}{W}{deleted} files{RS}\n"
    if deleted == 0:
        out += f"  {C}Downloads pehle se clean hai Boss!{RS}\n"
    out += f"{Y}╚{'═'*36}╝{RS}\n"
    return out


# ══════════════════════════════════════════════════════════════
#  FEATURE: SELF-HEALING (BUG FIX)
# ══════════════════════════════════════════════════════════════

SELF_HEAL_LOG = os.path.expanduser("~/.friday_selfheal.json")

def selfheal_load():
    try:
        if os.path.exists(SELF_HEAL_LOG):
            with open(SELF_HEAL_LOG) as f:
                return json.load(f)
    except: pass
    return {"fixes": []}

def selfheal_save(data):
    try:
        with open(SELF_HEAL_LOG, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except: pass

def self_check_syntax():
    """miraz.py ka syntax check karo."""
    script_path = os.path.abspath(__file__)
    try:
        result = subprocess.run(
            ["python3", "-c", f"import ast; ast.parse(open('{script_path}').read()); print('OK')"],
            capture_output=True, text=True, timeout=15
        )
        if "OK" in result.stdout:
            return True, "Syntax bilkul theek hai Boss!"
        else:
            return False, result.stderr[:300]
    except Exception as e:
        return False, str(e)[:300]

def self_fix_bug(error_desc):
    """Groq se fix maango aur apply karo."""
    if not GROQ_KEY:
        return cy("Groq API key nahi hai Boss — bug fix possible nahi.")

    script_path = os.path.abspath(__file__)

    # Read current code
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            code = f.read()
    except Exception as e:
        return cy(f"Code read nahi ho saka: {e}")

    print(f"  {C}🔍 Groq se fix maang raha hoon...{RS}")

    # Ask Groq for fix
    fix_prompt = f"""You are a Python expert. Here is a bug report for miraz.py:

ERROR: {error_desc}

Here are relevant parts of the code (first 3000 chars):
{code[:3000]}

Provide ONLY a JSON response in this exact format:
{{
  "can_fix": true/false,
  "explanation": "kya problem hai (1-2 lines)",
  "fix_type": "syntax_error / logic_error / config_error / cannot_fix",
  "search_text": "exact text to find in code (if applicable)",
  "replace_text": "replacement text (if applicable)"
}}
No extra text, just JSON."""

    resp = ask_ai(fix_prompt, system_override="You are a Python code fixer. Reply only with valid JSON.")
    if not resp:
        return cy("Groq se response nahi aaya Boss.")

    try:
        # Clean JSON
        clean = re.sub(r"```json|```", "", resp).strip()
        fix_data = json.loads(clean)
    except Exception as e:
        return cy(f"Fix parse nahi ho saka Boss: {e}\nGroq response: {resp[:200]}")

    explanation = fix_data.get("explanation", "N/A")
    can_fix     = fix_data.get("can_fix", False)
    fix_type    = fix_data.get("fix_type", "unknown")

    if not can_fix or fix_type == "cannot_fix":
        out  = f"\n{Y}╔══ 🔍 BUG ANALYSIS ══╗{RS}\n"
        out += f"  {C}Error   : {RS}{W}{error_desc[:60]}{RS}\n"
        out += f"  {C}Analysis: {RS}{Y}{explanation}{RS}\n"
        out += f"  {R}Main ye fix nahi kar sakta — manual intervention chahiye.{RS}\n"
        out += f"{Y}╚{'═'*38}╝{RS}\n"
        return out

    search_text  = fix_data.get("search_text", "")
    replace_text = fix_data.get("replace_text", "")

    if search_text and search_text in code:
        # Backup first
        backup_path = script_path + ".bak"
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(code)

        # Apply fix
        new_code = code.replace(search_text, replace_text, 1)

        # Validate syntax
        try:
            compile(new_code, script_path, "exec")
        except SyntaxError as se:
            return cy(f"Fix apply kiya but syntax error aya: {se}\nBackup safe hai: {backup_path}")

        # Write fixed code
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(new_code)

        # Log the fix
        sh = selfheal_load()
        sh["fixes"].append({
            "time": datetime.datetime.now().isoformat(),
            "error": error_desc[:100],
            "fix_type": fix_type,
            "explanation": explanation,
        })
        selfheal_save(sh)

        out  = f"\n{G}╔══ ✅ FIX APPLIED ══╗{RS}\n"
        out += f"  {C}Error  : {RS}{W}{error_desc[:60]}{RS}\n"
        out += f"  {C}Fix    : {RS}{G}{explanation}{RS}\n"
        out += f"  {C}Type   : {RS}{W}{fix_type}{RS}\n"
        out += f"  {G}✓ Code update ho gaya — restart karo FRIDAY{RS}\n"
        out += f"  {DM}Backup: {backup_path}{RS}\n"
        out += f"{G}╚{'═'*36}╝{RS}\n"
        speak("Bug fix ho gaya Boss! Friday restart karo.")
        return out
    else:
        out  = f"\n{Y}╔══ 🔍 BUG REPORT ══╗{RS}\n"
        out += f"  {C}Error   : {RS}{W}{error_desc[:60]}{RS}\n"
        out += f"  {C}Analysis: {RS}{Y}{explanation}{RS}\n"
        out += f"  {Y}Exact code location nahi mila — manual fix karo Boss{RS}\n"
        out += f"{Y}╚{'═'*36}╝{RS}\n"
        return out

def selfheal_history():
    """Past fixes ki list."""
    sh = selfheal_load()
    fixes = sh.get("fixes", [])
    if not fixes:
        return cy("Koi self-fix history nahi hai Boss.")
    out = f"\n{Y}╔══ 🔧 SELF-HEAL HISTORY ({len(fixes)}) ══╗{RS}\n"
    for i, fix in enumerate(reversed(fixes[-10:]), 1):
        ts = fix.get("time", "")[:16].replace("T", " ")
        out += f"  {C}[{i}]{RS} {DM}{ts}{RS} — {W}{fix.get('explanation','')[:50]}{RS}\n"
    out += f"{Y}╚{'═'*44}╝{RS}\n"
    return out


# ══════════════════════════════════════════════════════════════
#  FEATURE: SECRETARY MODE (MEETINGS + CALENDAR)
# ══════════════════════════════════════════════════════════════

SECRETARY_FILE = os.path.expanduser("~/.friday_secretary.json")

def sec_load():
    try:
        if os.path.exists(SECRETARY_FILE):
            with open(SECRETARY_FILE) as f:
                return json.load(f)
    except: pass
    return {"meetings": [], "agenda": []}

def sec_save(data):
    try:
        with open(SECRETARY_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except: pass

def sec_add_meeting(text):
    """Meeting add karo — natural language parse karo."""
    data = sec_load()
    now  = datetime.datetime.now()

    # Parse time from text
    time_str  = ""
    date_str  = ""
    title     = text

    # Time patterns: "3 baje", "3pm", "15:00", "kal 5 baje"
    time_match = re.search(r"(\d{1,2})\s*(baje|pm|am|:00|:30)?", text, re.I)
    if time_match:
        hour = int(time_match.group(1))
        suffix = (time_match.group(2) or "").lower()
        if "pm" in suffix and hour < 12:
            hour += 12
        time_str = f"{hour:02d}:00"

    # Date patterns
    if re.search(r"\bkal\b", text, re.I):
        date_str = (now + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    elif re.search(r"\baaj\b", text, re.I):
        date_str = now.strftime("%Y-%m-%d")
    else:
        date_str = now.strftime("%Y-%m-%d")

    # Clean title
    title = re.sub(r"\d{1,2}\s*(baje|pm|am)|kal|aaj|meeting add|add meeting", "", text, flags=re.I).strip()
    if not title:
        title = text.strip()

    meeting = {
        "id": len(data["meetings"]) + 1,
        "title": title,
        "date": date_str,
        "time": time_str,
        "created": now.isoformat()[:16],
    }
    data["meetings"].append(meeting)
    sec_save(data)

    display_time = f" at {time_str}" if time_str else ""
    display_date = "Kal" if date_str == (now + datetime.timedelta(days=1)).strftime("%Y-%m-%d") else "Aaj"
    return cg(f"Meeting add ho gayi Boss!\n  📅 {display_date}{display_time}: {title}")

def sec_list_meetings(days_ahead=7):
    """Agle N din ki meetings dikao."""
    data   = sec_load()
    now    = datetime.datetime.now()
    cutoff = now + datetime.timedelta(days=days_ahead)
    upcoming = []

    for m in data["meetings"]:
        try:
            mdate = datetime.datetime.strptime(m["date"], "%Y-%m-%d")
            if now.date() <= mdate.date() <= cutoff.date():
                upcoming.append(m)
        except: pass

    if not upcoming:
        return cy(f"Agle {days_ahead} din mein koi meeting nahi Boss.")

    upcoming.sort(key=lambda x: (x["date"], x.get("time", "")))
    out = f"\n{Y}╔══ 📅 UPCOMING MEETINGS ({len(upcoming)}) ══╗{RS}\n"
    for m in upcoming:
        date_obj = datetime.datetime.strptime(m["date"], "%Y-%m-%d")
        day_label = "Today" if date_obj.date() == now.date() else                     "Tomorrow" if date_obj.date() == (now + datetime.timedelta(days=1)).date() else                     date_obj.strftime("%d %b")
        time_label = m.get("time", "") or "Time TBD"
        out += f"  {C}[{m['id']}]{RS} {G}{day_label} {time_label}{RS} — {W}{m['title']}{RS}\n"
    out += f"{Y}╚{'═'*44}╝{RS}\n"
    return out

def sec_delete_meeting(mid):
    """Meeting delete karo by ID."""
    data = sec_load()
    before = len(data["meetings"])
    data["meetings"] = [m for m in data["meetings"] if m.get("id") != mid]
    sec_save(data)
    if len(data["meetings"]) < before:
        return cg(f"Meeting #{mid} delete ho gayi Boss!")
    return cy(f"Meeting #{mid} nahi mili Boss.")

def sec_add_agenda(text):
    """Agenda item add karo."""
    data = sec_load()
    item = {
        "id": len(data["agenda"]) + 1,
        "text": text,
        "done": False,
        "added": datetime.datetime.now().isoformat()[:16],
    }
    data["agenda"].append(item)
    sec_save(data)
    return cg(f"Agenda mein add ho gaya Boss: {text}")

def sec_show_agenda():
    """Today ka agenda dikao."""
    data = sec_load()
    items = [i for i in data["agenda"] if not i.get("done")]
    if not items:
        return cy("Aaj ka agenda khali hai Boss. 'agenda add <task>' se add karo.")
    out = f"\n{Y}╔══ 📋 TODAY\'S AGENDA ══╗{RS}\n"
    for item in items:
        out += f"  {C}[{item['id']}]{RS} {W}{item['text']}{RS}\n"
    out += f"{Y}╚{'═'*36}╝{RS}\n"
    return out

def sec_done_agenda(aid):
    """Agenda item complete mark karo."""
    data = sec_load()
    for item in data["agenda"]:
        if item.get("id") == aid:
            item["done"] = True
            sec_save(data)
            return cg(f"✅ Done Boss: {item['text']}")
    return cy(f"Agenda item #{aid} nahi mila Boss.")

def sec_briefing():
    """Secretary style morning briefing."""
    data     = sec_load()
    now      = datetime.datetime.now()
    greeting = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 17 else "Good evening"

    # Today's meetings
    today_meetings = [m for m in data["meetings"]
                      if m.get("date") == now.strftime("%Y-%m-%d")]
    # Pending agenda
    pending = [i for i in data["agenda"] if not i.get("done")]

    out  = f"\n{Y}╔══ 👔 SECRETARY BRIEFING ══╗{RS}\n"
    out += f"  {C}{greeting} Boss!{RS} {DM}{now.strftime('%A, %d %B %Y %H:%M')}{RS}\n\n"

    if today_meetings:
        out += f"  {G}📅 Aaj ki meetings ({len(today_meetings)}):{RS}\n"
        for m in today_meetings:
            t = m.get("time", "Time TBD")
            out += f"    {W}• {t} — {m['title']}{RS}\n"
    else:
        out += f"  {DM}📅 Aaj koi meeting nahi{RS}\n"

    if pending:
        out += f"\n  {G}📋 Pending agenda ({len(pending)} items):{RS}\n"
        for item in pending[:5]:
            out += f"    {W}• {item['text']}{RS}\n"

    out += f"{Y}╚{'═'*44}╝{RS}\n"
    speak(f"{greeting} Boss! {len(today_meetings)} meetings aaj hain.")
    return out



# ══════════════════════════════════════════════════════════════
#  FEATURE: MP3 DOWNLOADER (yt-dlp)
# ══════════════════════════════════════════════════════════════

DOWNLOAD_DIR = "/sdcard/Music/Friday_Downloads"
DOWNLOAD_DIR_FALLBACK = os.path.expanduser("~/storage/music/Friday_Downloads")

def _ensure_download_dir():
    for d in [DOWNLOAD_DIR, DOWNLOAD_DIR_FALLBACK]:
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except: pass
    fallback = os.path.expanduser("~/Friday_Downloads")
    os.makedirs(fallback, exist_ok=True)
    return fallback

def _check_ytdlp():
    """yt-dlp installed hai check karo."""
    import shutil
    return shutil.which("yt-dlp") is not None

def _install_ytdlp():
    """yt-dlp auto install karo."""
    print(f"  {C}📦 yt-dlp install ho raha hai... ek minute Boss{RS}")
    try:
        # Try pip first
        r = subprocess.run(
            ["pip", "install", "yt-dlp", "--break-system-packages", "-q"],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode == 0:
            return True
        # Try pip3
        r2 = subprocess.run(
            ["pip3", "install", "yt-dlp", "--break-system-packages", "-q"],
            capture_output=True, text=True, timeout=120
        )
        return r2.returncode == 0
    except Exception as e:
        print(f"  {Y}⚠ Install failed: {e}{RS}")
        return False

def download_mp3(url, quality="best"):
    """URL se MP3 download karo — YouTube, SoundCloud, etc."""
    # Check/install yt-dlp
    if not _check_ytdlp():
        print(f"  {Y}⚠ yt-dlp nahi hai — install karta hoon Boss...{RS}")
        if not _install_ytdlp():
            return cy(
                "yt-dlp install nahi ho saka Boss.\n"
                "Manually install karo:\n"
                "  pip install yt-dlp --break-system-packages"
            )
        print(f"  {G}✓ yt-dlp install ho gaya!{RS}")

    save_dir = _ensure_download_dir()

    # Detect type
    url_lower = url.lower()
    is_youtube  = any(x in url_lower for x in ["youtube.com", "youtu.be"])
    is_playlist = "playlist" in url_lower or "list=" in url_lower

    print(f"  {C}🎵 Downloading MP3...{RS}")
    if is_youtube:
        print(f"  {DM}Source: YouTube {'Playlist' if is_playlist else 'Video'}{RS}")
    print(f"  {DM}Save: {save_dir}{RS}")

    # Build command
    output_template = os.path.join(save_dir, "%(title)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",          # best quality
        "--output", output_template,
        "--no-playlist" if not is_playlist else "--yes-playlist",
        "--no-warnings",
        "--no-progress",
        "--quiet",
        url
    ]

    try:
        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,    # Background mein — output hide
            text=True,
            timeout=300             # 5 min max
        )
        elapsed = int(time.time() - start_time)

        if result.returncode == 0:
            # Find downloaded file
            files = []
            for f in os.listdir(save_dir):
                fp = os.path.join(save_dir, f)
                if f.lower().endswith(".mp3") and os.path.getmtime(fp) > start_time - 5:
                    files.append((f, os.path.getsize(fp)))

            # Media scan
            try:
                for f, _ in files:
                    subprocess.Popen(
                        ["termux-media-scan", os.path.join(save_dir, f)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
            except: pass

            out  = f"\n{G}╔══ 🎵 DOWNLOAD COMPLETE ══╗{RS}\n"
            out += f"  {C}Source  :{RS} {W}{url[:55]}{RS}\n"
            out += f"  {C}Time    :{RS} {W}{elapsed}s{RS}\n"
            if files:
                out += f"  {C}Files   :{RS}\n"
                for fname, sz in files[:5]:
                    out += f"    {G}✓{RS} {W}{fname[:45]}{RS} {DM}({sz//1024}KB){RS}\n"
                if len(files) > 5:
                    out += f"    {DM}...aur {len(files)-5} songs{RS}\n"
            out += f"  {C}Saved   :{RS} {G}{save_dir}{RS}\n"
            out += f"{G}╚{'═'*42}╝{RS}\n"
            speak(f"Download complete Boss! {len(files)} songs save ho gaye.")
            return out
        else:
            return cy(
                f"Download failed Boss.\n"
                f"Possible reasons:\n"
                f"  • Video private ya age-restricted hai\n"
                f"  • URL galat hai\n"
                f"  • Internet slow hai\n"
                f"  • Ye site supported nahi hai"
            )
    except subprocess.TimeoutExpired:
        return cy("Download timeout ho gaya Boss (5 min limit). Chota video try karo ya net check karo.")
    except FileNotFoundError:
        return cy("yt-dlp nahi mila Boss. Termux restart karo phir try karo.")
    except Exception as e:
        return cy(f"Download error Boss: {str(e)[:100]}")

def download_status():
    """Downloaded songs ki list."""
    save_dir = _ensure_download_dir()
    files = []
    for f in os.listdir(save_dir):
        if f.lower().endswith(('.mp3', '.m4a', '.opus', '.webm')):
            fp = os.path.join(save_dir, f)
            files.append((f, os.path.getsize(fp), os.path.getmtime(fp)))

    if not files:
        return cy(f"Koi downloaded songs nahi hain Boss.\n'download <url>' se MP3 download karo.")

    files.sort(key=lambda x: x[2], reverse=True)
    total_size = sum(s for _, s, _ in files) // (1024*1024)

    out  = f"\n{Y}╔══ 🎵 DOWNLOADED SONGS ({len(files)}) ══╗{RS}\n"
    out += f"  {DM}Folder: {save_dir}{RS}\n"
    out += f"  {DM}Total : {total_size}MB{RS}\n\n"
    for fname, sz, mtime in files[:15]:
        dt = datetime.datetime.fromtimestamp(mtime).strftime("%d/%m %H:%M")
        out += f"  {G}♪{RS} {W}{fname[:42]:<44}{RS}{DM}{sz//1024}KB  {dt}{RS}\n"
    if len(files) > 15:
        out += f"  {DM}... aur {len(files)-15} songs hain{RS}\n"
    out += f"{Y}╚{'═'*50}╝{RS}\n"
    return out


# ══════════════════════════════════════════════════════════════
#  FEATURE: GPS LOCATION
# ══════════════════════════════════════════════════════════════

_cached_location = None

def get_gps_location(force_refresh=False):
    """Termux se real-time GPS location lo."""
    global _cached_location
    if _cached_location and not force_refresh:
        return _cached_location
    try:
        result = subprocess.run(
            ["termux-location", "-p", "gps", "-r", "once"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            _cached_location = data
            return data
    except Exception:
        pass
    # Fallback — network location
    try:
        result = subprocess.run(
            ["termux-location", "-p", "network", "-r", "once"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            _cached_location = data
            return data
    except Exception:
        pass
    return None

def get_city_from_coords(lat, lon):
    """Coordinates se city naam nikalo — free API."""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "FridayAI/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        addr = data.get("address", {})
        city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county", "")
        state = addr.get("state", "")
        country = addr.get("country", "")
        return city, state, country
    except Exception:
        return "", "", ""

def show_location(force=False):
    """Current GPS location dikhao."""
    print(f"  {C}📡 GPS location fetch ho raha hai Boss...{RS}")
    loc = get_gps_location(force_refresh=force)
    if not loc:
        return cy(
            "GPS location nahi mili Boss.\n"
            "Check karo:\n"
            "  1. Location permission: Termux → Allow Location\n"
            "  2. GPS on hai phone mein\n"
            "  3. termux-api install hai: pkg install termux-api"
        )
    lat  = loc.get("latitude", 0)
    lon  = loc.get("longitude", 0)
    acc  = loc.get("accuracy", 0)
    alt  = loc.get("altitude", 0)

    # City naam nikalo
    city, state, country = get_city_from_coords(lat, lon)
    location_str = ", ".join(filter(None, [city, state, country]))

    # LTM mein save karo
    ltm = ltmem_load()
    ltm["topics"]["current_location"] = {
        "lat": lat, "lon": lon,
        "city": city, "state": state, "country": country,
        "updated": datetime.datetime.now().isoformat()[:16]
    }
    ltmem_save(ltm)

    out  = f"\n{Y}╔══ 📍 CURRENT LOCATION ══╗{RS}\n"
    out += f"  {C}📌 Location : {RS}{W}{location_str or 'Unknown'}{RS}\n"
    out += f"  {C}🌐 Latitude : {RS}{W}{lat:.6f}{RS}\n"
    out += f"  {C}🌐 Longitude: {RS}{W}{lon:.6f}{RS}\n"
    out += f"  {C}🎯 Accuracy : {RS}{W}{acc:.0f}m{RS}\n"
    if alt:
        out += f"  {C}⛰ Altitude : {RS}{W}{alt:.0f}m{RS}\n"

    out += f"{Y}╚{'═'*40}╝{RS}\n"
    speak(f"Location mil gayi Boss. Aap {city or 'unknown location'} mein hain.")
    return out

def navigate_to(destination):
    """Kisi jagah navigate karo."""
    # Check saved locations
    ltm = ltmem_load()
    topics = ltm.get("topics", {})

    # Check if destination is a saved key
    dest_lower = destination.lower()
    saved_coords = None

    if "ghar" in dest_lower or "home" in dest_lower:
        home = topics.get("mera_ghar") or topics.get("home")
        if home and isinstance(home, dict):
            saved_coords = f"{home.get('lat')},{home.get('lon')}"
        elif home:
            destination = str(home)

    if saved_coords:
        maps_url = f"https://maps.google.com/?q={saved_coords}&navigate=yes"
    else:
        maps_url = f"https://maps.google.com/?q={urllib.parse.quote(destination)}&navigate=yes"

    open_url(maps_url)
    return cg(f"✓ Navigation shuru! Destination: {destination}")

def location_to_weather(city=""):
    """GPS se city detect karke weather dikhao."""
    if not city:
        ltm  = ltmem_load()
        loc  = ltm.get("topics", {}).get("current_location", {})
        city = loc.get("city", "")
        if not city:
            # Try live GPS
            live = get_gps_location()
            if live:
                city, _, _ = get_city_from_coords(
                    live.get("latitude", 0),
                    live.get("longitude", 0)
                )
    return city

def distance_from_home(lat2, lon2):
    """Ghar se current location ki distance calculate karo."""
    import math
    ltm    = ltmem_load()
    topics = ltm.get("topics", {})

    lat1 = lon1 = None

    # Method 1: mera_ghar dict format
    home = topics.get("mera_ghar", {})
    if isinstance(home, dict) and "lat" in home:
        lat1 = home["lat"]
        lon1 = home["lon"]

    # Method 2: separate keys — "mera ghar lat", "mera ghar lon"
    if lat1 is None:
        for k, v in topics.items():
            val = v.get("value", v) if isinstance(v, dict) else v
            kl = k.lower()
            if "ghar" in kl and "lat" in kl:
                try: lat1 = float(str(val).strip())
                except: pass
            if "ghar" in kl and ("lon" in kl or "long" in kl):
                try: lon1 = float(str(val).strip())
                except: pass

    if lat1 is None or lon1 is None:
        return None

    # Haversine formula — accurate distance in km
    R    = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a    = (math.sin(dlat/2)**2 +
            math.cos(math.radians(lat1)) *
            math.cos(math.radians(lat2)) *
            math.sin(dlon/2)**2)
    dist = R * 2 * math.asin(math.sqrt(a))
    return round(dist, 2)


# ══════════════════════════════════════════════════════════════
#  FEATURE: SMART LOCATION TRIGGERS
# ══════════════════════════════════════════════════════════════

LOCATION_TRIGGERS_FILE = os.path.expanduser("~/.friday_loc_triggers.json")

def loc_triggers_load():
    try:
        if os.path.exists(LOCATION_TRIGGERS_FILE):
            with open(LOCATION_TRIGGERS_FILE) as f:
                return json.load(f)
    except: pass
    return {"triggers": []}

def loc_triggers_save(data):
    try:
        with open(LOCATION_TRIGGERS_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except: pass

def loc_trigger_add(name, radius_m, action):
    """Location trigger add karo."""
    loc = get_gps_location()
    if not loc:
        return cy("GPS location nahi mili Boss. Location on karo.")
    data = loc_triggers_load()
    trigger = {
        "id": len(data["triggers"]) + 1,
        "name": name,
        "lat": loc.get("latitude", 0),
        "lon": loc.get("longitude", 0),
        "radius_m": radius_m,
        "action": action,
        "active": True,
        "last_state": "outside",
        "created": datetime.datetime.now().isoformat()[:16]
    }
    data["triggers"].append(trigger)
    loc_triggers_save(data)
    return cg(f"✅ Trigger set! '{name}' — {radius_m}m radius pe: {action}")

def loc_trigger_check():
    """Current location ke hisaab se triggers fire karo."""
    data = loc_triggers_load()
    if not data["triggers"]: return
    loc = get_gps_location(force_refresh=True)
    if not loc: return
    import math
    lat2, lon2 = loc.get("latitude", 0), loc.get("longitude", 0)
    fired = []
    for t in data["triggers"]:
        if not t.get("active"): continue
        # Distance calculate
        R = 6371000  # meters
        dlat = math.radians(lat2 - t["lat"])
        dlon = math.radians(lon2 - t["lon"])
        a = math.sin(dlat/2)**2 + math.cos(math.radians(t["lat"])) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        dist_m = R * 2 * math.asin(math.sqrt(a))
        inside = dist_m <= t["radius_m"]
        prev   = t.get("last_state", "outside")
        # State change detection
        if inside and prev == "outside":
            t["last_state"] = "inside"
            fired.append((t["name"], t["action"], "entered"))
            print(f"\n  {G}📍 Location Trigger: '{t["name"]}' — ENTERED!{RS}")
            speak(f"Boss! {t['name']} area mein aa gaye!")
            # Execute action
            _execute_trigger_action(t["action"])
        elif not inside and prev == "inside":
            t["last_state"] = "outside"
            fired.append((t["name"], t["action"], "left"))
            print(f"\n  {Y}📍 Location Trigger: '{t["name"]}' — LEFT!{RS}")
            speak(f"Boss! {t['name']} area se chale gaye!")
    loc_triggers_save(data)

def _execute_trigger_action(action):
    """Trigger action execute karo."""
    a = action.lower()
    if "music" in a or "gana" in a:
        subprocess.Popen(["termux-media-player", "play"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif "silent" in a or "mute" in a:
        subprocess.Popen(["termux-volume", "ring", "0"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif "wifi" in a:
        speak("Boss! WiFi zone mein aa gaye!")
    elif "remind" in a or "reminder" in a:
        msg = re.sub(r"remind|reminder|:|-", "", action, flags=re.I).strip()
        speak(f"Boss! Location reminder: {msg}")

def loc_triggers_list():
    """Active triggers dikhao."""
    data = loc_triggers_load()
    triggers = data.get("triggers", [])
    if not triggers:
        return cy("Koi location triggers nahi hain Boss.\n'trigger add <naam> <radius> <action>' se banao.")
    out = f"\n{Y}╔══ 🛰 LOCATION TRIGGERS ({len(triggers)}) ══╗{RS}\n"
    for t in triggers:
        status = f"{G}● Active{RS}" if t.get("active") else f"{R}○ Off{RS}"
        out += f"  {C}[{t['id']}]{RS} {W}{t['name']}{RS} {status}\n"
        out += f"      {DM}Radius: {t['radius_m']}m | Action: {t['action']}{RS}\n"
    out += f"{Y}╚{'═'*44}╝{RS}\n"
    return out

def start_location_monitor():
    """Background mein location monitor karo."""
    def _monitor():
        while True:
            try:
                loc_trigger_check()
            except: pass
            time.sleep(120)  # Har 2 min check
    t = threading.Thread(target=_monitor, daemon=True)
    t.start()


# ══════════════════════════════════════════════════════════════
#  FEATURE: PERSONAL DASHBOARD
# ══════════════════════════════════════════════════════════════

def show_dashboard():
    now = datetime.datetime.now()
    SEP = chr(9552) * 54
    TL=chr(9556); TR=chr(9559); BL=chr(9562); BR=chr(9565); SI=chr(9553); LJ=chr(9568); RJ=chr(9571)
    out = "\n"
    out += f"{Y}{TL}{SEP}{TR}{RS}\n"
    out += f"{Y}{SI}{RS}{BD}{C}  {'📊  FRIDAY PERSONAL DASHBOARD':<52}{RS}{Y}{SI}{RS}\n"
    out += f"{Y}{SI}{RS}  {DM}{now.strftime('%A, %d %B %Y  %H:%M'):<52}{RS}{Y}{SI}{RS}\n"
    out += f"{Y}{LJ}{SEP}{RJ}{RS}\n"
    try:
        r2 = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=4)
        b = json.loads(r2.stdout)
        pct = b.get("percentage", 0)
        icon = "\u26a1" if b.get("status","") == "CHARGING" else "\U0001f50b"
        bar = "\u2588" * (pct//10) + "\u2591" * (10 - pct//10)
        bc = G if pct > 30 else R
        out += f"{Y}{SI}{RS}  {icon} Battery  {bc}{bar} {pct}%{RS}\n"
    except:
        out += f"{Y}{SI}{RS}  \U0001f50b Battery  {DM}N/A{RS}\n"
    try:
        fitness_file = os.path.expanduser("~/.friday_fitness.json")
        if os.path.exists(fitness_file):
            fd = json.load(open(fitness_file))
            today = now.strftime("%Y-%m-%d")
            recs = fd if isinstance(fd, list) else []
            steps = int(sum(float(x.get("value",0)) for x in recs if x.get("date")==today and x.get("type")=="steps"))
            paani = int(sum(float(x.get("value",0)) for x in recs if x.get("date")==today and x.get("type") in ["paani","water"]))
            out += f"{Y}{SI}{RS}  \U0001f45f Steps    {W}{steps}{RS}    {C}\U0001f4a7 Paani {W}{paani}/8{RS}\n"
    except:
        out += f"{Y}{SI}{RS}  \U0001f45f Steps    {DM}N/A{RS}\n"
    try:
        mood_file = os.path.expanduser("~/.friday_mood.json")
        if os.path.exists(mood_file):
            md = json.load(open(mood_file))
            today = now.strftime("%Y-%m-%d")
            entries = md if isinstance(md, list) else md.get("entries", [])
            today_moods = [e["mood"] for e in entries if e.get("date","").startswith(today)]
            last_mood = today_moods[-1] if today_moods else "N/A"
            out += f"{Y}{SI}{RS}  \U0001f60a Mood     {W}{last_mood}{RS}\n"
    except:
        pass
    try:
        gd = goals_load()
        pending = [g for g in gd if not g.get("done")]
        done_g  = [g for g in gd if g.get("done")]
        out += f"{Y}{SI}{RS}  \U0001f3af Goals    {G}{len(done_g)} done{RS}  {Y}{len(pending)} pending{RS}\n"
    except:
        pass
    try:
        exps = expense_load()
        today = now.strftime("%Y-%m-%d")
        total = sum(e.get("amount",0) for e in exps if e.get("date","").startswith(today))
        out += f"{Y}{SI}{RS}  \U0001f4b0 Kharch   {W}\u20b9{total:.0f} aaj{RS}\n"
    except:
        pass
    out += f"{Y}{BL}{SEP}{BR}{RS}\n"
    return out


# ══════════════════════════════════════════════════════════════
#  FEATURE: VOICE AUTHENTICATION
# ══════════════════════════════════════════════════════════════

VOICE_AUTH_FILE = os.path.expanduser("~/.friday_voiceauth.json")

def voice_auth_load():
    try:
        if os.path.exists(VOICE_AUTH_FILE):
            with open(VOICE_AUTH_FILE) as f:
                return json.load(f)
    except: pass
    return {"enrolled": False, "passphrase": "", "attempts": 0}

def voice_auth_save(data):
    try:
        with open(VOICE_AUTH_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except: pass

def voice_enroll(passphrase):
    """Voice passphrase enroll karo."""
    data = voice_auth_load()
    # Hash the passphrase for comparison
    import hashlib
    hashed = hashlib.sha256(passphrase.lower().strip().encode()).hexdigest()
    data["enrolled"]  = True
    data["passphrase"] = hashed
    data["passphrase_hint"] = passphrase[:3] + "***"
    data["enrolled_at"] = datetime.datetime.now().isoformat()[:16]
    voice_auth_save(data)
    return cg(
        f"✅ Voice passphrase enrolled Boss!\n"
        f"  Passphrase: {passphrase[:3]}***\n"
        f"  Ab 'friday unlock <passphrase>' se unlock karo."
    )

def voice_authenticate(attempt):
    """Passphrase verify karo."""
    import hashlib
    data = voice_auth_load()
    if not data.get("enrolled"):
        return True, "Not enrolled"
    hashed = hashlib.sha256(attempt.lower().strip().encode()).hexdigest()
    if hashed == data.get("passphrase",""):
        data["attempts"] = 0
        data["last_unlock"] = datetime.datetime.now().isoformat()[:16]
        voice_auth_save(data)
        speak("Identity confirmed Boss. Welcome back!")
        return True, "Authenticated"
    else:
        data["attempts"] = data.get("attempts", 0) + 1
        voice_auth_save(data)
        speak("Access denied.")
        return False, f"Wrong passphrase. Attempt #{data['attempts']}"


# ══════════════════════════════════════════════════════════════
#  FEATURE: SELF-LEARNING MEMORY
# ══════════════════════════════════════════════════════════════

AUTOLEARN_FILE = os.path.expanduser("~/.friday_autolearn.json")

def autolearn_load():
    try:
        if os.path.exists(AUTOLEARN_FILE):
            with open(AUTOLEARN_FILE) as f:
                return json.load(f)
    except: pass
    return {"patterns": {}, "learned": []}

def autolearn_save(data):
    try:
        with open(AUTOLEARN_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except: pass

def autolearn_from_conversation(user_input, ai_response):
    """Conversation se automatically facts extract karke yaad karo."""
    if not GROQ_KEY: return
    # Only learn from substantial conversations
    if len(user_input) < 10 or len(ai_response) < 10: return

    extract_prompt = (
        f"User ne kaha: {repr(user_input)}\n"
        f"Friday ne jawab diya: {repr(ai_response)}\n"
        "Kya is conversation mein koi PERMANENT fact hai?\n"
        "Jaise: naam, pasand, habit, ghar, kaam, family, health, hobby\n"
        'Agar haan: {"learn": true, "key": "fact_key", "value": "fact_value"}\n'
        'Agar nahi: {"learn": false}\n'
        "Koi extra text nahi — sirf JSON."
    )
    try:
        resp = ask_ai(extract_prompt,
                      system_override="You are a memory extractor. Reply only with JSON. No extra text.",
                      max_tokens=100)
        if not resp: return
        clean = re.sub(r"```json|```", "", resp).strip()
        data  = json.loads(clean)
        if data.get("learn") and data.get("key") and data.get("value"):
            key = data["key"].lower().replace(" ", "_")
            val = data["value"]
            ltm = ltmem_load()
            # Only save if not already known
            if key not in ltm.get("topics", {}):
                ltmem_store(ltm, key, val)
                # Log it
                al = autolearn_load()
                al["learned"].append({
                    "key": key, "value": val,
                    "from": user_input[:50],
                    "time": datetime.datetime.now().isoformat()[:16]
                })
                al["learned"] = al["learned"][-50:]
                autolearn_save(al)
                print(f"  {DM}🧠 Auto-learned: {key} = {val}{RS}")
    except Exception:
        pass

def autolearn_history():
    """Auto-learned facts ki history."""
    al = autolearn_load()
    learned = al.get("learned", [])
    if not learned:
        return cy("Abhi tak kuch auto-learn nahi hua Boss.")
    out = f"\n{Y}╔══ 🧠 AUTO-LEARNED FACTS ({len(learned)}) ══╗{RS}\n"
    for item in reversed(learned[-10:]):
        out += f"  {G}+{RS} {C}{item['key']}{RS} = {W}{item['value'][:40]}{RS}\n"
        out += f"    {DM}From: '{item['from'][:40]}'{RS}\n"
    out += f"{Y}╚{'═'*46}╝{RS}\n"
    return out

# ══════════════════════════════════════════════════════════════


def friday_voice_mode(_voice_queue):
    """Voice mode — bolo aur FRIDAY actual commands execute kare!"""
    EXIT_WORDS = ["band karo", "bye", "exit", "quit", "band", "alvida", "goodbye", "voice band"]

    print(f"\n{Y}╔══════════════════════════════════════╗")
    print(f"║   🎤 FRIDAY VOICE MODE ACTIVE        ║")
    print(f"║   'band karo' bolein — band karne ke liye ║")
    print(f"╚══════════════════════════════════════╝{RS}\n")
    speak(f"Voice mode active hai Sir {BOSS}. Main sun raha hoon!")

    while True:
        try:
            print(f"  {C}🎤 Bol rahe hain...{RS}", flush=True)
            result = subprocess.run(
                ["termux-speech-to-text"],
                capture_output=True, text=True, timeout=15
            )
            user_input = result.stdout.strip()

            if not user_input:
                print(f"  {DM}(Kuch nahi suna — dobara bolo){RS}")
                continue

            print(f"  {G}🎙️ Suna: {W}{user_input}{RS}", flush=True)

            # Exit check
            if any(w in user_input.lower() for w in EXIT_WORDS):
                msg = "Voice mode band ho gaya Sir. Normal mode mein wapas!"
                print(f"\n  {C}FRIDAY:{RS} {W}{msg}{RS}\n")
                speak(msg)
                break

            # Voice input ko main loop mein bhejo — actual command execute hoga!
            _voice_queue.put(user_input)
            break

        except subprocess.TimeoutExpired:
            print(f"  {Y}⏱️ Timeout — dobara bolo!{RS}")
            continue
        except KeyboardInterrupt:
            msg = "Voice mode band ho gaya Sir!"
            print(f"\n  {C}FRIDAY:{RS} {W}{msg}{RS}\n")
            speak(msg)
            break


def main():
    show_banner()
    mem = load_memory()
    ltm = ltmem_load()
    cnt = len(mem.get("messages",[]))
    ltm_cnt = len(ltm.get("topics",{}))
    print(cg(f"  ✓ AI connected ({MODEL})") if GROQ_KEY else cy("  ⚠ No GROQ_API_KEY — AI disabled."))
    eleven_key = (os.environ.get("ELEVEN_LABS_API_KEY","") or CFG.get("elevenlabs_key","")).strip()
    if eleven_key and len(eleven_key) > 10:
        print(cg(f"  ✓ ElevenLabs voice ready (Rachel)"))
    else:
        print(cg(f"  ✓ Google TTS (gTTS) voice active"))
    print(cg(f"  ✓ Memory: {cnt} messages | LT Memory: {ltm_cnt} facts"))
    start_task_runner()
    print(cg(f"  ✓ Task scheduler started."))
    start_battery_monitor()
    print(cg(f"  ✓ Battery monitor started."))
    start_hardware_guardian()
    print(cg(f"  ✓ Hardware Guardian active (Temp + RAM)."))
    # Budget alert background thread
    def _budget_bg():
        while True:
            try: budget_check_alert()
            except: pass
            time.sleep(3600)  # Har ghante check
    threading.Thread(target=_budget_bg, daemon=True).start()
    print(cg(f"  ✓ Budget alert monitor started."))
    start_geofence_monitor()
    print(cg(f"  ✓ Smart Geofence monitor started."))
    start_auto_suggestions()
    print(cg(f"  ✓ Auto suggestions started."))
    try: start_reminder_monitor(); print(cg(f"  ✓ Smart reminder monitor started."))
    except: pass
    try: start_alarm_monitor(); print(cg(f"  ✓ Alarm monitor started."))
    except: pass
    try: start_anomaly_monitor(); print(cg(f"  ✓ Anomaly detection started."))
    except: pass
    start_location_monitor()
    print(cg(f"  ✓ Location trigger monitor started."))
    # Birthday/event check on startup
    today_evs = events_check_today()
    hour = datetime.datetime.now().hour
    greet = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")
    import random as _rand
    _welcomes = [
        greet + " Boss. All systems online. FRIDAY reporting for duty.",
        greet + " Boss. Neural networks loaded. Weapons hot. Ready when you are.",
        greet + " Boss. I have been monitoring. Everything is under control.",
        greet + " Boss. Systems fully operational. What is the mission today?",
        greet + " Boss. Defenses up, systems online. FRIDAY at your command.",
        greet + " Boss. Running at full capacity. I missed you.",
    ]
    welcome = _rand.choice(_welcomes)
    if today_evs:
        welcome += " Also Boss, aaj kuch khaas hai!"
    print_friday(welcome)
    time.sleep(1)
    speak(welcome)
    time.sleep(2)
    if today_evs:
        for ev in today_evs:
            print(f"  {R}🎉 {ev}{RS}")
        speak(f"Boss, aaj {today_evs[0]} hai!")

    # Voice input queue
    import queue as _queue_mod
    _voice_queue = _queue_mod.Queue()
    _voice_mode_active = False

    # Global color vars — local scope mein available
    G='\033[92m'; Y='\033[93m'; C='\033[96m'; R='\033[91m'
    W='\033[97m'; DM='\033[2m'; BD='\033[1m'; RS='\033[0m'

    while True:
        try:
            # Voice mode active hai toh voice se lo
            if _voice_mode_active:
                print(f"  \033[96m🎤 Bol rahe hain...\033[0m", flush=True)
                try:
                    result = subprocess.run(
                        ["termux-speech-to-text"],
                        capture_output=True, text=True, timeout=15
                    )
                    user_input = result.stdout.strip()
                    if not user_input:
                        print(f"  \033[2m(Kuch nahi suna — dobara bolo)\033[0m")
                        continue
                    print(f"  \033[92m🎙️ Suna: \033[97m{user_input}\033[0m", flush=True)
                    # Voice band karne ke liye — PEHLE check karo
                    _voff_words = ["voice"]
                    if any(w == user_input.lower().strip() for w in _voff_words):
                        _voice_mode_active = False
                        print_friday(cg("🎤 Voice Mode OFF — Normal mode mein wapas!"))
                        speak("Voice mode band Sir!")
                        continue
                except subprocess.TimeoutExpired:
                    print(f"  \033[93m⏱️ Dobara bolo!\033[0m")
                    continue
                except Exception:
                    _voice_mode_active = False
                    continue
            else:
                # Normal text input
                user_input = input(f"\033[94m\033[1m{BOSS}\033[0m → ").strip()
                # Empty input → ek baar voice lo
                if not user_input:
                    if not _voice_queue.empty():
                        user_input = _voice_queue.get_nowait()
                        print(f"\033[96m🎙️ Voice: {user_input}\033[0m")
                    else:
                        try:
                            print(f"  \033[96m🎙️ Bol rahe hain... (Enter dabao band karne ke liye)\033[0m")
                            result = subprocess.run(
                                ["termux-speech-to-text"],
                                capture_output=True, text=True, timeout=10
                            )
                            voice_text = result.stdout.strip()
                            if voice_text:
                                print(f"  \033[96m🎙️ Suna: {voice_text}\033[0m")
                                user_input = voice_text
                            else:
                                continue
                        except subprocess.TimeoutExpired:
                            continue
                        except Exception:
                            continue
        except (KeyboardInterrupt, EOFError):
            print_friday("Initiating shutdown sequence, Sir. It has been a pleasure serving you.")
            speak("Shutting down Sir. Have a productive day."); save_memory(mem); break

        if not user_input: continue
        cmd = user_input.lower().strip()
        log_info(f"USER: {user_input[:200]}")
        # Behavior + Emotion + Predict track karo
        try: behavior_track(cmd)
        except: pass
        try: predict_track(cmd)
        except: pass
        try:
            emo = emotion_track(user_input)
            if emo not in ["neutral", ""]:
                emo_msg = emotion_response(emo)
                if emo_msg:
                    print(f"  {DM}💭 {emo_msg}{RS}")
        except: pass

        # ── MANUAL FACT SAVE (sirf jab user bole) ───────────
        if any(x in cmd for x in ['save karo', 'yaad rakho', 'note karo', 'remember karo', 'save kar lo']):
            learned = auto_learn_facts(user_input, ltm)
            if learned:
                for fact in learned:
                    print(f"  \033[2m💡 Yaad kar liya: {fact}\033[0m")
            else:
                # Generic save
                ltmem_store(ltm, user_input[:40], user_input[:100])
                print(f"  \033[2m💡 Save ho gaya!\033[0m")

        # ── EXIT ──────────────────────────────────────────────
        if cmd in ["exit","bye","quit","friday band karo","shutdown","goodbye","nikal"]:
            msg="All systems powering down, Sir. FRIDAY signing off. Until next time."
            print_friday(msg); speak(msg); save_memory(mem); time.sleep(4); break

        # ── HELP ──────────────────────────────────────────────
        elif cmd in ["help","commands","madad"]:
            show_help()

        elif cmd.startswith("help "):
            topic = re.sub(r'^help\s+','',cmd).strip()
            show_help(topic)

        # ── MEMORY ────────────────────────────────────────────
        elif cmd in ["memory","show memory","history","kya yaad"]:
            print(show_memory(mem))

        elif cmd in ["memory clear","clear memory","memory reset"]:
            mem["messages"]=[]; save_memory(mem); print_friday("Memory cleared Boss.")

        # ── BATTERY ───────────────────────────────────────────
        elif cmd in ["battery","battery info","battery check","battery kitni","charge kitna"]:
            pct,b=get_battery(); print(f"\n  {b}\n"); speak(f"Battery {pct} percent Boss.")

        # ── RAM ───────────────────────────────────────────────
        elif cmd in ["ram","ram check","ram info","kitni ram"]:
            print(f"\n  {get_ram()}\n"); speak("RAM status Boss.")

        # ── STORAGE ───────────────────────────────────────────
        elif cmd in ["storage","storage info","free space","disk","jagah"]:
            print(f"\n  {get_storage()}\n"); speak("Storage info Boss.")

        # ── NETWORK ───────────────────────────────────────────
        elif cmd in ["net","network","net info","wifi","wifi info","ip","myip","my ip","internet"]:
            print(f"\n{cc('╔══════ 🌐 NETWORK ══════╗')}\n{get_network()}\n{cc('╚════════════════════════╝')}\n")
            speak("Network info Boss.")

        # ── FULL SYSTEM ───────────────────────────────────────
        elif cmd in ["sys","system","sab batao","full status","diagnostics","system info"]:
            pct,bat=get_battery()
            print(f"\n{Y}╔══════════ 🖥️  SYSTEM STATUS ══════════╗{RS}")
            print(f"  {bat}\n  {get_ram()}\n  {get_storage()}")
            print(f"{Y}╚{'═'*42}╝{RS}\n"); speak("System diagnostics complete Boss.")

        # ── TIME ──────────────────────────────────────────────
        elif cmd in ["time","time kya","time batao","kitne baje","what time","current time"]:
            now=datetime.datetime.now()
            print(f"\n  {Y}🕐 {W}{now.strftime('%H:%M:%S')}   {Y}📅 {W}{now.strftime('%A, %d %B %Y')}{RS}\n")
            speak(f"Time is {now.strftime('%I:%M %p')} Boss.")

        # ── DATE ──────────────────────────────────────────────
        elif cmd in ["date","date batao","aaj ki date","what date","day","din","aaj ka din"]:
            d=datetime.datetime.now().strftime("%A, %d %B %Y")
            print(f"\n  {Y}📅 {W}{d}{RS}\n"); speak(f"Today is {d} Boss.")

        # ── GOOGLE SEARCH (opens browser) ─────────────────────
        elif cmd.startswith("search ") or cmd.startswith("google "):
            query=re.sub(r'^(search|google)\s+','',user_input,flags=re.I).strip()
            search_history_add(query, "search")
            print_friday(do_google(query)); speak(f"Opening Google for {query} Boss.")

        # ── WIKIPEDIA ARTICLE ─────────────────────────────────
        elif cmd.startswith("ddgr ") or cmd.startswith("ddeg ") or cmd.startswith("wiki ") or cmd.startswith("article "):
            query = re.sub(r'^(ddgr|ddeg|wiki|article)\s+','',user_input,flags=re.I).strip()
            search_history_add(query, "ddgr")
            # Show thinking animation while fetching
            stop = threading.Event()
            t = threading.Thread(target=ai_thinking, args=(stop,), daemon=True); t.start()
            display, voice_text = do_ddgr(query)
            stop.set(); t.join()
            print(display)
            # Speak the answer
            if voice_text and voice_text.strip():
                speak(voice_text[:350])
            else:
                speak(f"Search complete Boss.")

        # ── YOUTUBE OPEN ──────────────────────────────────────
        elif cmd in ["youtube","youtube kholo","open youtube","yt","yt open"]:
            print_friday(do_youtube()); speak("Opening YouTube Boss.")

        # ── YOUTUBE SEARCH ────────────────────────────────────
        elif cmd.startswith("yt ") or cmd.startswith("youtube search "):
            query=re.sub(r'^(yt|youtube search)\s+','',user_input,flags=re.I).strip()
            search_history_add(query, "youtube")
            print_friday(do_youtube(query)); speak(f"Searching YouTube for {query} Boss.")

        elif re.match(r'^play\s+.+',cmd):
            query=re.sub(r'^play\s+','',user_input,flags=re.I).strip()
            print_friday(do_youtube(query)); speak(f"Playing {query} on YouTube Boss.")

        # ── OPEN APP ──────────────────────────────────────────
        elif cmd.startswith("open "):
            app=re.sub(r'^open\s+','',cmd).strip()
            if app=="settings":
                try: subprocess.Popen(["am","start","-a","android.settings.SETTINGS"]); print_friday(cg("✓ Opening Settings...")); speak("Opening settings Boss.")
                except: print_friday(cy("Settings failed."))
            else:
                matched=False
                for key,url in APP_URLS.items():
                    if key in app:
                        open_url(url); print_friday(cg(f"✓ Opening {key.title()}...")); speak(f"Opening {key} Boss."); matched=True; break
                if not matched: print_friday(cy(f"App '{app}' not found. Try: open youtube"))

        # ── STREAMING APPS ────────────────────────────────────
        elif any(x in cmd for x in ["spotify","spotify kholo"]):
            open_url("spotify:"); print_friday(cg("✓ Opening Spotify...")); speak("Opening Spotify Boss.")

        elif any(x in cmd for x in ["gaana","gaana kholo"]):
            open_url("https://gaana.com"); print_friday(cg("✓ Opening Gaana...")); speak("Opening Gaana Boss.")

        elif any(x in cmd for x in ["saavn","jiosaavn","jio saavn"]):
            open_url("https://www.jiosaavn.com"); print_friday(cg("✓ Opening JioSaavn...")); speak("Opening JioSaavn Boss.")

        elif any(x in cmd for x in ["youtube music","yt music","music youtube"]):
            open_url("https://music.youtube.com"); print_friday(cg("✓ Opening YouTube Music...")); speak("Opening YouTube Music Boss.")

        # ── LOCAL MUSIC PLAYER (SD card / internal) ───────────
        # "gana bajao" → play from phone storage directly
        elif any(x in cmd for x in [
            "gana bajao","music bajao","song bajao","gana chalu","music chalu",
            "mp3","local music","local gana","apna gana bajao","phone ka gana",
            "offline gana","storage se gana","mp3 bajao","gana sunao","music sunao",
            "gana laga","music laga","play karo","bajao"]):
            resp = MP.play()
            print_friday(resp); speak("Playing music from your phone Boss.")

        # NEXT SONG
        elif any(x in cmd for x in ["next","next song","agla gana","agli song",
                                     "agle","skip","next gana","next karo"]):
            resp = MP.next_song()
            print_friday(resp); speak("Next song Boss.")

        # PREVIOUS / BACK SONG
        elif any(x in cmd for x in ["back","back song","pichla gana","previous song",
                                     "previous","prev","pichla","back karo","peeche"]):
            resp = MP.prev_song()
            print_friday(resp); speak("Previous song Boss.")

        # STOP MUSIC
        elif any(x in cmd for x in ["music stop","gana band","stop music","music band",
                                     "band karo","music bund","gana bund","stop gana",
                                     "rok","ruk ja"]):
            print_friday(MP.stop()); speak("Music stopped Boss.")

        # PAUSE
        elif any(x in cmd for x in ["pause","pause karo","roko","music roko","gana roko"]):
            print_friday(MP.pause()); speak("Music paused Boss.")

        # RESUME
        elif any(x in cmd for x in ["resume","resume karo","chalu karo","music chalu karo",
                                     "dobara bajao"]):
            print_friday(MP.resume()); speak("Music resumed Boss.")

        # VOLUME CONTROL
        elif re.match(r'^volume\s+\d+$', cmd):
            vol = int(re.search(r'\d+', cmd).group())
            print_friday(MP.set_volume(vol)); speak(f"Volume {vol} percent Boss.")

        elif any(x in cmd for x in ["volume up","volume badao","volume zyada","volume barhao"]):
            print_friday(MP.set_volume(min(100, MP.volume + 20))); speak("Volume up Boss.")

        elif any(x in cmd for x in ["volume down","volume kam","volume ghata","volume hatao"]):
            print_friday(MP.set_volume(max(0, MP.volume - 20))); speak("Volume down Boss.")

        elif any(x in cmd for x in ["volume max","full volume","poori awaaz"]):
            print_friday(MP.set_volume(100)); speak("Volume maximum Boss.")

        elif any(x in cmd for x in ["volume min","volume mute","awaaz band","mute music"]):
            print_friday(MP.set_volume(0)); speak("Volume muted Boss.")

        # MUSIC STATUS
        elif any(x in cmd for x in ["music status","kya chal raha","now playing","current song",
                                     "kaun sa gana","music info"]):
            print(MP.status())

        # PLAYLIST VIEW
        elif any(x in cmd for x in ["playlist","song list","gaane ki list","music list"]):
            print(MP.playlist_view())

        # FIND & PLAY specific song
        elif re.match(r'^(find song|song dhundo|play local)\s+.+', cmd):
            query = re.sub(r'^(find song|song dhundo|play local)\s+', '', cmd).strip()
            resp = MP.play(query)
            print_friday(resp); speak(f"Playing {query} Boss.")

        # ── SMS ───────────────────────────────────────────────
        elif cmd.startswith("sms "):
            parts=user_input.split(' ',2)
            if len(parts)<3: print_friday("Usage: sms <number> <message>")
            else: print_friday(do_sms(parts[1],parts[2])); speak("SMS sent Boss.")

        # ── CALL ──────────────────────────────────────────────
        elif cmd.startswith("call "):
            number=re.sub(r'^call\s+','',user_input).strip()
            print_friday(do_call(number)); speak(f"Calling {number} Boss.")

        # ── CONTACTS ──────────────────────────────────────────
        elif cmd in ["contacts","contact list","mere contacts"]:
            print(do_contacts()); speak("Contact list loaded Boss.")

        # ── SCREENSHOT ────────────────────────────────────────
        elif cmd in ["screenshot","ss","ss lo","screenshot lo","screen capture"]:
            print_friday(do_screenshot()); speak("Screenshot taken Boss.")

        # ── TORCH ─────────────────────────────────────────────
        elif any(x in cmd for x in ["torch on","flashlight on","torch chalu","light on"]):
            subprocess.Popen(["termux-torch","on"]); print_friday(cg("✓ Torch ON 🔦")); speak("Torch on Boss.")

        elif any(x in cmd for x in ["torch off","flashlight off","torch band","light off"]):
            subprocess.Popen(["termux-torch","off"]); print_friday("Torch OFF"); speak("Torch off Boss.")

        # ── VIBRATE ───────────────────────────────────────────
        elif any(x in cmd for x in ["vibrate","vibrate karo","phone vibrate"]):
            subprocess.Popen(["termux-vibrate","-d","500"]); print_friday("Vibrating 📳"); speak("Vibrating Boss.")

        # ── BRIGHTNESS ────────────────────────────────────────
        elif re.match(r'^brightness\s+\d+$',cmd):
            print_friday(do_brightness(int(re.search(r'\d+',cmd).group()))); speak("Brightness set Boss.")

        elif any(x in cmd for x in ["brightness max","full brightness","brightness badhao"]):
            print_friday(do_brightness(255)); speak("Maximum brightness Boss.")

        elif any(x in cmd for x in ["brightness medium","brightness normal","brightness mid"]):
            print_friday(do_brightness(128)); speak("Medium brightness Boss.")

        elif any(x in cmd for x in ["brightness low","brightness kam","andhera"]):
            print_friday(do_brightness(50)); speak("Low brightness Boss.")

        elif any(x in cmd for x in ["brightness min","brightness minimum","screen dim"]):
            print_friday(do_brightness(10)); speak("Minimum brightness Boss.")

        # ── CALCULATOR ────────────────────────────────────────
        elif cmd.startswith("calc ") or cmd.startswith("calculate ") or cmd.startswith("hisab "):
            expr=re.sub(r'^(calc|calculate|hisab)\s+','',user_input,flags=re.I).strip()
            print_friday(do_calc(expr)); speak("Calculated Boss.")

        # ── UNIT CONVERTER ────────────────────────────────────
        elif re.match(r'^convert\s+[\d.]+\s+\w+\s+to\s+\w+',cmd):
            m=re.match(r'^convert\s+([\d.]+)\s+(\w+)\s+to\s+(\w+)',cmd)
            if m: print_friday(do_convert(float(m.group(1)),m.group(2),m.group(3))); speak("Converted Boss.")

        # ── PASSWORD ──────────────────────────────────────────
        elif re.search(r'\bpassword\b',cmd) or cmd in ["pass banao","passwd","pass chahiye"]:
            ptype="pin" if any(x in cmd for x in ["simple","pin","numeric"]) else "medium" if any(x in cmd for x in ["medium","normal"]) else "strong"
            # Default length — pin ke liye 6, baaki ke liye 16
            length = 6 if ptype == "pin" else 16
            # Agar user ne explicitly length diya ho toh wo use karo
            for p in cmd.split():
                if p.isdigit(): length = max(4, min(64, int(p))); break
            print(do_password(length,ptype)); speak(f"{ptype} password generated Boss.")

        # ── ENCRYPT ───────────────────────────────────────────
        elif cmd.startswith("encrypt "):
            parts=user_input.split(' ',2)
            if len(parts)<3: print_friday("Usage: encrypt <text> <key>")
            else:
                txt,key=parts[1],parts[2]
                encoded=base64.b64encode(bytes([ord(c)^ord(key[i%len(key)]) for i,c in enumerate(txt)])).decode()
                print_friday(f"🔒 Encrypted:\n  {G}{encoded}{RS}"); speak("Encrypted Boss.")

        # ── DECRYPT ───────────────────────────────────────────
        elif cmd.startswith("decrypt "):
            parts=user_input.split(' ',2)
            if len(parts)<3: print_friday("Usage: decrypt <encoded> <key>")
            else:
                txt,key=parts[1],parts[2]
                try:
                    decoded=''.join([chr(b^ord(key[i%len(key)])) for i,b in enumerate(base64.b64decode(txt))])
                    print_friday(f"🔓 Decrypted:\n  {G}{decoded}{RS}"); speak("Decrypted Boss.")
                except: print_friday(cy("Decryption failed. Check text and key Boss."))

        # ── NOTES ─────────────────────────────────────────────
        elif cmd.startswith("note save ") or cmd.startswith("note add "):
            text=user_input.split(' ',2)[2].strip()
            print_friday(note_save(text)); speak("Note saved Boss.")

        elif cmd.startswith("note ") and not any(cmd.startswith(x) for x in ["note delete","note list","note read"]):
            text=re.sub(r'^note\s+','',user_input,flags=re.I).strip()
            print_friday(note_save(text)); speak("Note saved Boss.")

        elif cmd in ["notes","note list","meri notes","notes dekho","note read"]:
            print(note_list()); speak("Notes displayed Boss.")

        elif re.match(r'^note delete\s+\d+$',cmd):
            print_friday(note_delete(int(re.search(r'\d+',cmd).group())-1)); speak("Note deleted Boss.")

        elif cmd in ["notes clear","note clear","sab notes hatao"]:
            json.dump([],open(NOTES_FILE,'w')); print_friday(cg("✓ All notes cleared Boss."))

        # ── TIMER ─────────────────────────────────────────────
        elif re.match(r'^timer\s+\d+',cmd):
            m=re.search(r'(\d+)\s*(min|sec|hour|ghante)?',cmd)
            num=int(m.group(1)); unit=(m.group(2) or "min").lower()
            secs=num*3600 if unit in ["hour","ghante"] else (num if unit=="sec" else num*60)
            label=f"{num} {'hours' if unit in ['hour','ghante'] else 'seconds' if unit=='sec' else 'minutes'}"
            start_timer(secs,label); print_friday(cg(f"✓ Timer: {label}")); speak(f"Timer set for {label} Boss.")

        # ── REMINDER ──────────────────────────────────────────
        elif re.match(r'^remind\s+\d+',cmd):
            m=re.search(r'(\d+)\s*(min|sec|hour)?',cmd); num=int(m.group(1)); unit=(m.group(2) or "min").lower()
            secs=num*3600 if unit=="hour" else (num if unit=="sec" else num*60)
            msg=re.sub(r'^remind\s+\d+\s*(min|sec|hour|minute|second)?\s*','',cmd,flags=re.I).strip() or "Reminder!"
            start_timer(secs,msg); print_friday(cg(f"✓ Reminder: '{msg}' in {num} min")); speak(f"Reminder set Boss.")

        # ── WEATHER ───────────────────────────────────────────
        elif cmd.startswith("weather ") or cmd.startswith("mausam "):
            city = re.sub(r'^(weather|mausam)\s+','',user_input,flags=re.I).strip()
            print(do_weather(city))

        elif cmd in ["weather","mausam","aaj ka mausam"]:
            print(do_weather("India"))

        # ── NEWS ──────────────────────────────────────────────
        elif cmd.startswith("news "):
            topic = re.sub(r'^news\s+','',user_input,flags=re.I).strip()
            print(do_news(topic))

        elif cmd in ["news","aaj ki news","latest news","khabar"]:
            print(do_news("india"))

        # ── IP LOOKUP ─────────────────────────────────────────
        elif re.match(r'^(iplookup|ip lookup|whois)\s+.+', cmd) or cmd in ['myip','my ip','mera ip']:
            if cmd in ['myip','my ip','mera ip']:
                try:
                    import urllib.request, json
                    r = urllib.request.urlopen('https://ipinfo.io/json', timeout=5).read()
                    d = json.loads(r)
                    out = f"\n\033[93m╔══ 🌍 Your IP Info ══╗\033[0m\n"
                    out += f"  IP      : {d.get('ip','?')}\n"
                    out += f"  City    : {d.get('city','?')}\n"
                    out += f"  Region  : {d.get('region','?')}\n"
                    out += f"  Country : {d.get('country','?')}\n"
                    out += f"  ISP     : {d.get('org','?')}\n"
                    out += f"\033[93m╚{'═'*30}╝\033[0m\n"
                    print(out)
                except Exception as e:
                    print(f"Error: {e}")
            else:
                target = re.sub(r'^(iplookup|ip lookup|whois)\s+','',user_input,flags=re.I).strip()
                print(do_ip_lookup(target))

        # ── HASH ──────────────────────────────────────────────
        elif cmd.startswith("hash "):
            text = re.sub(r'^hash\s+','',user_input,flags=re.I).strip()
            print(do_hash(text))

        elif re.match(r'^(md5|sha1|sha256)\s+.+', cmd):
            parts = user_input.split(None,1)
            print(do_hash(parts[1].strip(), parts[0].lower()))

        # ── QR CODE ───────────────────────────────────────────
        elif cmd.startswith("qr "):
            text = re.sub(r'^qr\s+','',user_input,flags=re.I).strip()
            print_friday(do_qr(text))

        # ── QR CODE ───────────────────────────────────────────
        elif cmd.startswith("qr "):
            text = re.sub(r'^qr\s+','',user_input,flags=re.I).strip()
            print_friday(do_qr(text))

        # ── IMAGE GENERATION ──────────────────────────────────
        elif re.match(r'^(imagine|image banao|image bana|create image|generate image|draw)\s+.+', cmd):
            prompt = re.sub(r'^(imagine|image banao|image bana|create image|generate image|draw)\s+', '', user_input, flags=re.I).strip()
            # Remove keywords from prompt
            prompt = re.sub(r'\b(stability|sd|stable|hd|portrait|tall|landscape|wide)\b', '', prompt, flags=re.I).strip()
            w = CFG.get("imagegen_width", 512)
            h = CFG.get("imagegen_height", 512)
            if "hd" in cmd or "1024" in cmd: w, h = 1024, 1024
            elif "portrait" in cmd or "tall" in cmd: w, h = 512, 768
            elif "landscape" in cmd or "wide" in cmd: w, h = 768, 512

            model = CFG.get("imagegen_model","flux")
            print(image_gen_pollinations(prompt, w, h, model))

        elif any(x in cmd for x in ["my images","meri images","generated images","image list","images dekho"]):
            print(image_list())

        elif any(x in cmd for x in ["last image","pichli image","image kholo","open image","image open"]):
            print_friday(image_open_last())


        elif cmd.startswith("ping "):
            host=re.sub(r'^ping\s+','',user_input).strip()
            print_friday(cc(f"Pinging {host}..."))
            try:
                r=subprocess.run(["ping","-c","4",host],capture_output=True,text=True,timeout=15)
                for line in r.stdout.strip().split('\n'):
                    print(f"  {G if 'bytes from' in line else W}{line}{RS}")
                speak("Ping complete Boss.")
            except subprocess.TimeoutExpired: print_friday(cy(f"Timeout — {host} not reachable."))

        # ── NMAP ──────────────────────────────────────────────
        elif re.match(r'^nmap\s+\S+', cmd):
            # Parse: nmap <target> [scan_type]
            parts = user_input.split()
            target = parts[1] if len(parts) > 1 else ""
            # Detect scan type from command
            if any(x in cmd for x in ["quick","-f","-F"]):
                stype = "quick"
            elif any(x in cmd for x in ["full","-p-","ports"]):
                stype = "full"
            elif any(x in cmd for x in ["os","operating"]):
                stype = "os"
            elif any(x in cmd for x in ["service","version","-sv"]):
                stype = "service"
            elif any(x in cmd for x in ["ping","-sn","host"]):
                stype = "ping"
            elif any(x in cmd for x in ["udp","-su"]):
                stype = "udp"
            elif any(x in cmd for x in ["vuln","vulnerability","script"]):
                stype = "vuln"
            elif any(x in cmd for x in ["aggressive","-a"]):
                stype = "aggressive"
            else:
                stype = "basic"
            print(do_nmap(target, stype))

        elif re.match(r'^scan\s+\S+', cmd):
            target = re.sub(r'^scan\s+', '', user_input, flags=re.I).split()[0]
            stype = "quick"
            if "full" in cmd: stype = "full"
            elif "os" in cmd: stype = "os"
            elif "service" in cmd: stype = "service"
            elif "vuln" in cmd: stype = "vuln"
            print(do_nmap(target, stype))

        # ── FUN ───────────────────────────────────────────────
        elif cmd in ["joke","ek joke","joke sunao","hasao"]:
            try:
                import urllib.request, json, ssl
                r = urllib.request.urlopen("https://official-joke-api.appspot.com/random_joke", timeout=5).read()
                d = json.loads(r)
                eng_joke = d["setup"] + " ... " + d["punchline"]
            except:
                eng_joke = "Why do programmers prefer dark mode? Because light attracts bugs!"
            try:
                import requests as _req
                prompt = f"Yeh English joke hai: '{eng_joke}'. Isse Roman Hindi mein translate karo — funny aur 3-4 lines mein. Sirf joke do, kuch aur mat likho."
                res = _req.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
                    json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],"max_tokens":200},
                    timeout=10)
                j = res.json()["choices"][0]["message"]["content"].strip()
            except Exception as ex:
                j = eng_joke
            print_friday(Y+j+RS); speak(j[:200])

        elif cmd in ["quote","motivate","ek quote","inspire me"]:
            try:
                import urllib.request, json
                r = urllib.request.urlopen("https://zenquotes.io/api/random", timeout=5).read()
                d = json.loads(r)[0]
                eng_q = f'"{d["q"]}" — {d["a"]}'
            except:
                eng_q = None
            try:
                import requests as _req
                prompt = f"Yeh English quote hai: {eng_q}. Isse Roman Hindi mein translate karo — matlab Hindi bolna hai lekin ENGLISH LETTERS mein likhna hai (Devanagari script bilkul nahi). Author ka naam English mein rakho. Sirf quote do, kuch aur mat likho."
                res = _req.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
                    json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],"max_tokens":150},
                    timeout=10)
                q = res.json()["choices"][0]["message"]["content"].strip()
            except:
                q = random.choice(QUOTES)
            print_friday(C+q+RS); speak(q[:150])

        elif cmd in ["flip","coin","coin toss","sikka"]:
            r=random.choice(["HEADS 🪙","TAILS 🪙"]); print_friday(Y+r+RS); speak(r.split()[0]+" Boss.")

        elif cmd in ["dice","roll","pasa","roll dice"]:
            r=random.randint(1,6); faces=["","⚀","⚁","⚂","⚃","⚄","⚅"]
            print_friday(f"🎲 {faces[r]} You rolled: {Y}{r}{RS}"); speak(f"You rolled {r} Boss.")

        # ── LONG-TERM MEMORY ──────────────────────────────────
        elif re.match(r'^(yaad kar|remember|save fact)\s+.+', cmd):
            # "yaad kar mera naam Miraz hai"
            text = re.sub(r'^(yaad kar|remember|save fact)\s+','',user_input,flags=re.I).strip()
            # Split key=value if possible
            if ' hai ' in text.lower():
                parts = re.split(r' hai ', text, maxsplit=1, flags=re.I)
                key, val = parts[0].strip(), parts[1].strip()
            elif ':' in text:
                key, val = text.split(':',1)
            else:
                key, val = text, text
            print_friday(ltmem_store(ltm, key, val))
            speak(f"Yaad kar liya Boss.")

        elif cmd in ["lt memory","long memory","facts","meri facts","ltm","saved facts"]:
            print(ltmem_show(ltm)); speak("Long term memory displayed Boss.")

        elif re.match(r'^(bhool ja|forget)\s+.+', cmd):
            key = re.sub(r'^(bhool ja|forget)\s+','',cmd).strip()
            print_friday(ltmem_forget(ltm, key))

        elif cmd in ["lt memory clear","facts clear","ltm clear"]:
            ltm["topics"] = {}; ltm["facts"] = []
            ltmem_save(ltm); print_friday(cg("✓ Long-term memory cleared Boss."))

        # ── REPORT GENERATOR ──────────────────────────────────
        elif re.match(r'^report\s+.+', cmd):
            topic = re.sub(r'^report\s+','',user_input,flags=re.I).strip()
            # Generate report via AI
            if GROQ_KEY:
                stop=threading.Event()
                t=threading.Thread(target=ai_thinking,args=(stop,),daemon=True); t.start()
                ai_sys = ("Tu ek professional report writer hai. "
                          "Roman Hindi ya English mein detailed report likho. "
                          "Sections, points aur facts include karo.")
                content_r = ask_ai(f"Is topic par ek detailed report likho: {topic}",
                                   system_override=ai_sys, max_tokens=1000)
                stop.set(); t.join()
                if content_r:
                    rtype = "html" if "html" in cmd else "txt"
                    print_friday(generate_report(topic, clean_roman(content_r), rtype))
                else:
                    print_friday(cy("Report generate nahi hui. AI connection check karo."))
            else:
                print_friday(cy("GROQ_API_KEY chahiye report ke liye Boss."))

        elif cmd in ["reports","report list","meri reports","saved reports"]:
            print(report_list())

        # ── EXPENSE TRACKER ───────────────────────────────────
        elif re.match(r'^kharch\s+\d+', cmd) or re.match(r'^kharcha\s+\d+', cmd) or re.match(r'^expense\s+\d+', cmd):
            # "kharch 500 biryani" OR "kharch 500"
            m = re.search(r'\d+[\d.]*', user_input)
            amount = float(m.group()) if m else 0
            # Category = remaining words after amount
            cat_raw = re.sub(r'^(kharch|kharcha|expense)\s+[\d.]+\s*', '', user_input, flags=re.I).strip()
            category = cat_raw if cat_raw else "general"
            print_friday(expense_add(amount, category))
            speak(f"Expense added. {amount} rupees for {category} Boss.")

        elif any(x in cmd for x in ["aaj ka kharch","aaj ka kharcha","aaj kharch","today expense","aaj ki spending","aaj kitna kharch"]):
            print(expense_show("today")); speak("Aaj ka kharcha Boss.")

        elif any(x in cmd for x in ["is hafte ka kharch","is hafte kharch","weekly kharch","week ka kharch","hafte ka kharcha"]):
            print(expense_show("week")); speak("Is hafte ka kharcha Boss.")

        elif any(x in cmd for x in ["is mahine ka kharch","monthly kharch","mahine ka kharcha","month ka kharch","is month ka kharch"]):
            print(expense_show("month")); speak("Is mahine ka kharcha Boss.")

        elif any(x in cmd for x in ["kharch summary","kharcha summary","expense summary","spending summary","poora kharch"]):
            print(expense_summary()); speak("Expense summary Boss.")

        elif any(x in cmd for x in ["kharch dekho","kharcha dekho","expenses dekho","recent kharch","sab kharch","show expenses"]):
            print(expense_show("all")); speak("Recent expenses Boss.")

        elif any(x in cmd for x in ["kharch hatao","last kharch hatao","expense delete","last expense hatao","undo kharch"]):
            print_friday(expense_delete_last()); speak("Last expense deleted Boss.")

        elif any(x in cmd for x in ["kharch clear","sab kharch hatao","expenses clear","clear expenses"]):
            print_friday(expense_clear()); speak("All expenses cleared Boss.")

        # ── SCHEDULED TASKS ───────────────────────────────────
        elif re.match(r'^task add\s+.+', cmd):
            # "task add pani piyo har 30 min"
            text = re.sub(r'^task add\s+','',user_input,flags=re.I).strip()
            m = re.search(r'har\s+(\d+)\s*(min|hour|ghante)?', text, re.I)
            interval = 30
            if m:
                num = int(m.group(1))
                unit = (m.group(2) or "min").lower()
                interval = num * 60 if unit in ["hour","ghante"] else num
            label = re.sub(r'har\s+\d+\s*\w*','',text).strip() or text
            print_friday(task_add(label, interval))
            speak(f"Task scheduled Boss.")

        elif any(cmd == x for x in ["tasks","task list","mere tasks","scheduled tasks","task dekho","meri tasks"]) or cmd.startswith("tasks"):
            print(task_list()); speak("Task list displayed Boss.")

        elif re.match(r'^task delete\s+\d+', cmd):
            tid = re.search(r'\d+', cmd).group()
            print_friday(task_delete(tid)); speak("Task deleted Boss.")

        elif cmd in ["tasks clear","task clear","sab tasks hatao"]:
            tasks_save([]); print_friday(cg("✓ All tasks cleared Boss."))

        # ── SCRAPE URL ────────────────────────────────────────
        elif re.match(r'^(scrape|fetch|read url)\s+https?://\S+', cmd):
            # Extract ONLY the URL — stop at first space
            raw_url = re.sub(r'^(scrape|fetch|read url)\s+','',user_input,flags=re.I).strip()
            url = raw_url.split()[0]  # take only first token = URL
            stop=threading.Event()
            t=threading.Thread(target=ai_thinking,args=(stop,),daemon=True); t.start()
            result = scrape_and_summarize(url)
            stop.set(); t.join()
            print_friday(result); speak(result[:200])

        # ── CONFIG ────────────────────────────────────────────
        elif cmd in ["config","settings","friday config","config show"]:
            out = f"\n{Y}╔══ ⚙️  FRIDAY CONFIG ══╗{RS}\n"
            for k,v in CFG.items():
                if k == "groq_api_key":
                    v = v[:8]+"..." if v else "NOT SET"
                out += f"  {C}{k:<20}{RS}: {W}{v}{RS}\n"
            out += f"  {DM}Edit: {_CONFIG_FILE}{RS}\n"
            out += f"{Y}╚{'═'*28}╝{RS}\n"
            print(out)

        elif re.match(r'^config set\s+\w+\s+.+', cmd):
            parts = user_input.split(None, 3)
            if len(parts) >= 4:
                key, val = parts[2], parts[3]
                if key in CFG:
                    # Type conversion
                    if isinstance(CFG[key], bool): val = val.lower() in ["true","1","yes","on"]
                    elif isinstance(CFG[key], float): val = float(val)
                    elif isinstance(CFG[key], int): val = int(val)
                    CFG[key] = val
                    _save_config(CFG)
                    print_friday(cg(f"✓ Config updated: {key} = {val}"))
                    if key == "groq_api_key":
                        globals()['GROQ_KEY'] = val
                else:
                    print_friday(cy(f"Unknown config key: {key}"))

        # ── LOGS ──────────────────────────────────────────────
        elif cmd in ["logs","log","log dekho","friday log","errors"]:
            try:
                with open(LOG_FILE, 'r') as f:
                    log_lines = f.readlines()
                recent = log_lines[-25:]
                out = f"\n{Y}╔══ 📜 FRIDAY LOGS (last {len(recent)}) ══╗{RS}\n"
                for line in recent:
                    line = line.strip()
                    color = R if "ERROR" in line else (Y if "WARN" in line else DM)
                    out += f"  {color}{line[:95]}{RS}\n"
                out += f"{Y}╚{'═'*50}╝{RS}\n"
                print(out)
            except: print_friday(cy("No logs found Boss."))

        elif cmd in ["log clear","logs clear","log hatao"]:
            try:
                open(LOG_FILE, 'w').close()
                print_friday(cg("✓ Logs cleared Boss."))
            except: print_friday(cy("Log clear failed."))

        elif cmd in ["log errors","sirf errors","error log"]:
            try:
                with open(LOG_FILE, 'r') as f:
                    errors = [l.strip() for l in f if "ERROR" in l]
                if errors:
                    out = f"\n{R}╔══ ❌ ERROR LOGS ({len(errors)}) ══╗{RS}\n"
                    for e in errors[-15:]:
                        out += f"  {R}{e[:90]}{RS}\n"
                    out += f"{R}╚{'═'*40}╝{RS}\n"
                    print(out)
                else:
                    print_friday(cg("✓ No errors in logs Boss!"))
            except: print_friday(cy("No logs found Boss."))

        # ── SMART DAILY BRIEFING ──────────────────────────────
        elif any(x in cmd for x in ["briefing","daily briefing","good morning friday",
                                     "subah ka report","aaj ka update","morning update",
                                     "sab batao","good morning","good evening","good afternoon"]):
            print(daily_briefing())

        # ── MOOD TRACKER ──────────────────────────────────────
        elif re.match(r'^mood\s+\w+', cmd):
            mood_text = re.sub(r'^mood\s+', '', user_input, flags=re.I).strip()
            print_friday(mood_add(mood_text)); speak(f"Mood logged Boss.")

        elif any(x in cmd for x in ["aaj ka mood","mood today","mera mood","mood dekho","mood check"]):
            print(mood_today()); speak("Aaj ka mood Boss.")

        elif any(x in cmd for x in ["weekly mood","mood report","is hafte ka mood","mood history"]):
            print(mood_weekly()); speak("Weekly mood report Boss.")

        # ── FITNESS TRACKER ───────────────────────────────────
        elif re.match(r'^(steps|paani|water|exercise|workout|weight|running|pushups|situps)\s+\d+', cmd):
            parts = user_input.split(None, 1)
            etype = parts[0].lower()
            # Extract number and optional unit
            m2 = re.search(r'([\d.]+)\s*(\w*)', parts[1] if len(parts)>1 else "0")
            val = float(m2.group(1)) if m2 else 0
            unit_map = {"steps":"steps","paani":"glasses","water":"glasses",
                        "weight":"kg","running":"km","pushups":"reps","situps":"reps",
                        "exercise":"min","workout":"min"}
            unit = m2.group(2) if (m2 and m2.group(2) and not m2.group(2).isdigit()) else unit_map.get(etype,"")
            print_friday(fitness_log(etype, val, unit)); speak(f"{etype} logged Boss.")

        elif any(x in cmd for x in ["aaj ka fitness","fitness today","fitness dekho","aaj ki exercise","fit report"]):
            print(fitness_today()); speak("Fitness report Boss.")

        elif any(x in cmd for x in ["weekly fitness","fitness report","is hafte ki fitness","fitness summary"]):
            print(fitness_weekly()); speak("Weekly fitness summary Boss.")

        # ── BIRTHDAY / EVENT REMINDER ─────────────────────────
        elif re.match(r'^birthday add\s+.+', cmd) or re.match(r'^bday add\s+.+', cmd):
            # "birthday add Mama 15-08-1965"
            text = re.sub(r'^(birthday|bday) add\s+', '', user_input, flags=re.I).strip()
            # Last token = date
            parts2 = text.rsplit(None, 1)
            if len(parts2) == 2:
                print_friday(event_add(parts2[0].strip(), parts2[1].strip(), "birthday"))
            else:
                print_friday(cy("Usage: birthday add <naam> <DD-MM> ya <DD-MM-YYYY>"))
            speak("Birthday saved Boss.")

        elif re.match(r'^event add\s+.+', cmd):
            # "event add Meeting 25-03"
            text = re.sub(r'^event add\s+', '', user_input, flags=re.I).strip()
            parts2 = text.rsplit(None, 1)
            if len(parts2) == 2:
                print_friday(event_add(parts2[0].strip(), parts2[1].strip(), "event"))
            else:
                print_friday(cy("Usage: event add <naam> <DD-MM>"))
            speak("Event saved Boss.")

        elif any(x in cmd for x in ["all events","sab events","events list","birthday sab"]):
            print(events_list())

        elif any(x in cmd for x in ["events","birthdays","upcoming events","upcoming birthdays",
                                     "kab kab hai","events dekho","birthday list"]):
            print(events_upcoming(30)); speak("Upcoming events Boss.")

        elif re.match(r'^event delete\s+\d+', cmd) or re.match(r'^birthday delete\s+\d+', cmd):
            idx = int(re.search(r'\d+', cmd).group()) - 1
            print_friday(event_delete(idx)); speak("Event deleted Boss.")

        # ── SEARCH HISTORY ────────────────────────────────────
        elif any(x in cmd for x in ["search history","meri searches","kya search kiya","search dekho","history dekho"]):
            print(search_history_show()); speak("Search history Boss.")

        elif any(x in cmd for x in ["search patterns","search analysis","kya zyada search","search stats"]):
            print(search_history_patterns()); speak("Search patterns Boss.")

        elif any(x in cmd for x in ["search history clear","history clear","searches clear"]):
            print_friday(search_history_clear())

        # ── PINNED NOTES ──────────────────────────────────────
        elif re.match(r'^pin\s+.+', cmd):
            text = re.sub(r'^pin\s+', '', user_input, flags=re.I).strip()
            print_friday(pin_add(text)); speak("Note pinned Boss.")

        elif any(x in cmd for x in ["pins","pinned","pinned notes","pin list","meri pins"]):
            print(pin_list())

        elif re.match(r'^pin delete\s+\d+', cmd) or re.match(r'^unpin\s+\d+', cmd):
            idx = int(re.search(r'\d+', cmd).group()) - 1
            print_friday(pin_delete(idx)); speak("Pin removed Boss.")

        elif any(x in cmd for x in ["pins clear","pin clear","sab pins hatao"]):
            print_friday(pin_clear())

        # ── DAILY GOALS ───────────────────────────────────────
        elif re.match(r'^goal add\s+.+', cmd) or re.match(r'^goal\s+.+', cmd) and "done" not in cmd and "dekho" not in cmd and "clear" not in cmd:
            text = re.sub(r'^goal\s*(add)?\s+', '', user_input, flags=re.I).strip()
            print_friday(goal_add(text)); speak("Goal set Boss.")

        elif any(x in cmd for x in ["goals","goal list","aaj ke goals","goals dekho","mere goals","goal dekho"]):
            print(goals_today())

        elif re.match(r'^goal done\s+\d+', cmd) or re.match(r'^goal complete\s+\d+', cmd):
            idx = int(re.search(r'\d+', cmd).group()) - 1
            print_friday(goal_done(idx)); speak("Goal complete Boss!")

        elif any(x in cmd for x in ["goals clear","goal clear","aaj ke goals clear"]):
            print_friday(goals_clear_today())

        # ── SLEEP TRACKER ─────────────────────────────────────
        elif any(x in cmd for x in ["so gaya","sone ja raha","so raha","neend aa gayi","good night friday","sleep log"]):
            print_friday(sleep_log("so gaya")); speak("Good night Boss. Sweet dreams!")

        elif any(x in cmd for x in ["uth gaya","uth gaya main","subah uth gaya","wake up log","neend poori","good morning sleep"]):
            print_friday(sleep_log("uth gaya")); speak("Good morning Boss! Rise and shine!")

        elif any(x in cmd for x in ["sleep history","neend history","kitni neend","sleep report","sleep dekho"]):
            print(sleep_history()); speak("Sleep history Boss.")

        # ── WEEKLY LIFE REPORT ────────────────────────────────
        elif any(x in cmd for x in ["weekly report","life report","weekly life report","is hafte ki report",
                                     "weekly summary","sab ka report","poori report"]):
            print(weekly_life_report())

        # ── WHATSAPP MESSAGE ──────────────────────────────────
        elif re.match(r'^wa\s+\d+\s+.+', cmd) or re.match(r'^whatsapp\s+\d+\s+.+', cmd):
            # "wa 9876543210 Hello Boss!"
            parts = user_input.split(None, 2)
            if len(parts) >= 3:
                print_friday(send_whatsapp(parts[1], parts[2]))
            else:
                print_friday(cy("Usage: wa <number> <message>\nExample: wa 9876543210 Hello!"))

        elif re.match(r'^wa\s+\+\d+\s+.+', cmd):
            parts = user_input.split(None, 2)
            if len(parts) >= 3:
                print_friday(send_whatsapp(parts[1], parts[2]))

        # ── NIGHT GUARD ───────────────────────────────────────
        elif any(x in cmd for x in ["night guard on","night guard chalu","night guard start",
                                     "guard on","network guard on","intruder watch on"]):
            print_friday(start_night_guard()); speak("Night Guard activated Boss.")

        elif any(x in cmd for x in ["night guard off","night guard band","guard off",
                                     "network guard off","intruder watch off"]):
            print_friday(stop_night_guard()); speak("Night Guard deactivated Boss.")

        elif any(x in cmd for x in ["night guard scan","guard scan","network scan manual",
                                     "scan network now","intruder scan","scan karo"]):
            result = night_guard_manual_scan()
            if result: print_friday(result)

        elif any(x in cmd for x in ["night guard learn","guard learn devices",
                                     "safe devices register","network baseline","mera network"]):
            print(night_guard_learn_devices())

        elif any(x in cmd for x in ["night guard status","guard status","night guard kya hai",
                                     "guard dekho","night guard info"]):
            print(night_guard_status())

        elif any(x in cmd for x in ["night guard alerts","guard alerts","intruder alerts",
                                     "red alerts","alert history"]):
            print(night_guard_alerts_list()); speak("Alert history Boss.")

        elif any(x in cmd for x in ["night guard","night mode","guard"]) and "on" not in cmd and "off" not in cmd:
            try:
                print(night_guard_status())
            except NameError:
                print_friday(cy("Night Guard function available nahi hai Boss."))

        # ── MIRAZ WALLPAPER ───────────────────────────────────
        elif any(x in cmd for x in ["miraz wallpaper","achievement wallpaper","weekly wallpaper",
                                     "wallpaper banao","mera wallpaper","miraz edition wallpaper",
                                     "achievements wallpaper","set wallpaper"]):
            # Optional custom text check
            custom = ""
            for phrase in ["miraz wallpaper", "achievement wallpaper", "weekly wallpaper",
                           "wallpaper banao", "mera wallpaper", "miraz edition wallpaper",
                           "achievements wallpaper", "set wallpaper"]:
                if phrase in cmd:
                    custom = re.sub(phrase, "", cmd).strip()
                    break
            result = generate_achievement_wallpaper(custom_text=custom)
            print_friday(result)

        elif any(x in cmd for x in ["wallpaper list","mere wallpapers","saved wallpapers",
                                     "wallpapers dekho"]):
            print_friday(cy("Wallpaper feature unavailable — image generation kaam nahi kar raha Boss."))

        # ── GREETINGS ─────────────────────────────────────────
        elif cmd in ["hi","hello","hey","namaste","salam","namaskar"]:
            resp=random.choice(["Good to see you Boss. Kya kaam hai aaj?","Hello Boss. Ready for commands.","Greetings Boss. How can I assist?"])
            print_friday(resp); speak(resp); mem=add_memory(mem,"user",user_input); mem=add_memory(mem,"assistant",resp)

        elif "kaise ho" in cmd or "how are you" in cmd:
            r="All systems operational Boss. Aap batao?"; print_friday(r); speak(r)

        elif "kaun ho" in cmd or "who are you" in cmd or "tera naam" in cmd:
            r=f"I am {ASSISTANT}, your professional AI assistant Boss. Inspired by JARVIS."; print_friday(r); speak(r)

        elif "kaun hu" in cmd or "who am i" in cmd or "mera naam" in cmd:
            r=f"You are {BOSS}, my creator and the one I serve, Boss."; print_friday(r); speak(r)






        # ── SMART LOCATION TRIGGERS ───────────────────────────
        elif re.match(r'^trigger add\s+.+', cmd):
            parts = re.sub(r'^trigger add\s+', '', user_input, flags=re.I).strip().split()
            # Format: trigger add <naam> <radius> <action>
            # e.g: trigger add ghar 100 music bajao
            if len(parts) >= 3:
                radius = 100
                for i, p in enumerate(parts):
                    if p.isdigit():
                        radius = int(p)
                        name   = " ".join(parts[:i])
                        action = " ".join(parts[i+1:])
                        break
                else:
                    name   = parts[0]
                    action = " ".join(parts[1:])
                print_friday(loc_trigger_add(name, radius, action))
            else:
                print_friday(cy("Format: trigger add <naam> <radius_meter> <action>\nExample: trigger add ghar 100 music bajao"))

        elif any(x in cmd for x in ['triggers', 'location triggers', 'trigger list']):
            print(loc_triggers_list())

        elif re.match(r'^trigger delete\s+\d+', cmd):
            tid = int(re.search(r'\d+', cmd).group())
            data = loc_triggers_load()
            data["triggers"] = [t for t in data["triggers"] if t.get("id") != tid]
            loc_triggers_save(data)
            print_friday(cg(f"Trigger #{tid} deleted Boss!"))

        elif any(x in cmd for x in ['trigger check', 'location check', 'check triggers']):
            loc_trigger_check()
            print_friday(cg("Location triggers checked Boss!"))

        # ── PERSONAL DASHBOARD ────────────────────────────────
        elif any(x in cmd for x in ['dashboard', 'dash', 'overview', 'status board', 'status',
                                     'sab dikhao', 'full status', 'mera dashboard']):
            print(show_dashboard())
            speak("Dashboard ready Boss!")

        # ── VOICE AUTHENTICATION ──────────────────────────────
        elif re.match(r'^(voice enroll|enroll voice|passphrase set)\s+.+', cmd):
            phrase = re.sub(r'^(voice enroll|enroll voice|passphrase set)\s+', '', user_input, flags=re.I).strip()
            print_friday(voice_enroll(phrase))

        elif re.match(r'^(friday unlock|unlock friday|authenticate)\s+.+', cmd):
            attempt = re.sub(r'^(friday unlock|unlock friday|authenticate)\s+', '', user_input, flags=re.I).strip()
            ok, msg = voice_authenticate(attempt)
            if ok:
                print_friday(cg(f"✅ {msg} — Welcome Boss MIRAZ!"))
            else:
                print_friday(cy(f"❌ {msg}"))

        elif any(x in cmd for x in ['voice auth status', 'auth status', 'unlock status']):
            data = voice_auth_load()
            if data.get("enrolled"):
                print_friday(cg(f"✅ Voice auth active\n  Passphrase: {data.get('passphrase_hint','***')}\n  Last unlock: {data.get('last_unlock','Never')}"))
            else:
                print_friday(cy("Voice auth enrolled nahi hai Boss.\n'voice enroll <passphrase>' se setup karo."))

        # ── SELF-LEARNING MEMORY ──────────────────────────────
        elif any(x in cmd for x in ['auto learn history', 'learned facts', 'autolearn', 'self learning']):
            print(autolearn_history())

        elif any(x in cmd for x in ['auto learn on', 'learning on', 'self learn on']):
            ltm = ltmem_load()
            ltm["autolearn"] = True
            ltmem_save(ltm)
            print_friday(cg("✅ Self-learning ON Boss! Ab main conversation se automatically facts seekhunga!"))

        elif any(x in cmd for x in ['auto learn off', 'learning off', 'self learn off']):
            ltm = ltmem_load()
            ltm["autolearn"] = False
            ltmem_save(ltm)
            print_friday(cy("Self-learning OFF kiya Boss."))

        # ── GPS LOCATION ──────────────────────────────────────
        elif any(x in cmd for x in ['location', 'gps', 'meri location', 'main kahan hoon',
                                     'where am i', 'current location', 'location check']):
            print(show_location())

        elif any(x in cmd for x in ['location refresh', 'gps refresh', 'location update']):
            print(show_location(force=True))

        elif re.match(r'^(navigate|navigation|maps|ghar jao|ghar navigate)', cmd):
            dest = re.sub(r'^(navigate to|navigate|navigation|maps|ghar jao|ghar navigate)\s*', '', user_input, flags=re.I).strip()
            dest = dest or "home"
            print_friday(navigate_to(dest))

        elif any(x in cmd for x in ['ghar kitna door', 'ghar se kitni door', 'distance from home', 'ghar se kitna dur', 'ghar se kitna door', 'kitna dur hoon', 'ghar dur hai', 'main ghar se', 'how far from home', 'calculate distance', 'ghase kitna', 'ghar se dur', 'main kahan hoon aur ghar', 'where am i from home', 'location from home', 'ghar kahan hai', 'mujhe ghar jana', 'ghar batao', 'am i far', 'kitna dur hai ghar']):
            loc = get_gps_location()
            if loc:
                dist = distance_from_home(loc.get("latitude",0), loc.get("longitude",0))
                if dist is not None:
                    acc    = loc.get("accuracy", 0)
                    dist_m = int(dist * 1000)
                    lat2   = loc.get("latitude", 0)
                    lon2   = loc.get("longitude", 0)
                    # City from saved LTM
                    ltm_c  = ltmem_load()
                    cur_loc = ltm_c.get("topics",{}).get("current_location",{})
                    city   = cur_loc.get("city","") if isinstance(cur_loc, dict) else ""
                    # Status
                    if dist < 0.1:
                        status = "🏠 Ghar pe hain"
                        advice = "Aap ghar par hain Boss!"
                    elif dist < 0.5:
                        status = "🚶 Near Home"
                        advice = "Bas thodi der mein ghar pahunch jayenge!"
                    elif dist < 2:
                        status = "🛵 Thoda door"
                        advice = "Aas paas hain — auto ya walk possible hai."
                    elif dist < 10:
                        status = "🚗 Kaafi door"
                        advice = "Gaadi ya rickshaw lo Boss."
                    elif dist < 50:
                        status = "🚌 Door hai"
                        advice = "Bus ya train lo Boss."
                    else:
                        status = "✈️  Bahut door"
                        advice = "Aap bahut door hain Boss — safe rahein!"
                    out  = f"\n{Y}╔══ 📍 LOCATION & HOME TRACKER ══╗{RS}\n"
                    out += f"  {C}📌 Aap hain  :{RS} {W}{city or f'{lat2:.4f}, {lon2:.4f}'}{RS}\n"
                    out += f"  {C}🏠 Ghar dur  :{RS} {W}{dist} km ({dist_m}m){RS}\n"
                    out += f"  {C}🎯 GPS Acc   :{RS} {W}±{acc:.0f}m{RS}\n"
                    out += f"  {C}📊 Status    :{RS} {W}{status}{RS}\n"
                    out += f"  {C}💡 Tip       :{RS} {DM}{advice}{RS}\n"
                    out += f"  {DM}navigate ghar — Google Maps navigation{RS}\n"
                    out += f"{Y}╚{'═'*44}╝{RS}\n"
                    print(out)
                    speak(f"Boss, aap {city or 'is jagah'} mein hain. Ghar se {dist} kilometer door hain. {advice}")
                else:
                    # Ghar coords nahi hain — guide karo
                    out  = f"\n{Y}╔══ ⚠ GHAR SET NAHI HAI ══╗{RS}\n"
                    out += f"  {C}Pehle ghar save karo:{RS}\n"
                    out += f"  {W}1. 'location' command se GPS on karo{RS}\n"
                    out += f"  {W}2. Ghar pe jao, phir:{RS}\n"
                    out += f"  {W}   yaad kar mera ghar lat hai <value>{RS}\n"
                    out += f"  {W}   yaad kar mera ghar lon hai <value>{RS}\n"
                    out += f"  {DM}Ya seedha: yaad kar mera ghar hai Baidyabati{RS}\n"
                    out += f"{Y}╚{'═'*36}╝{RS}\n"
                    print(out)
                    speak("Boss, pehle ghar ka location save karo.")
            else:
                print_friday(cy("GPS location nahi mili Boss. Phone ka GPS on karo."))

        # ── ELEVENLABS VOICE ──────────────────────────────────
        elif any(x in cmd for x in ['voice list', 'voices dekho', 'friday voice change', 'voice change']) and 'listen' not in cmd and 'mode' not in cmd and 'mic' not in cmd:
            voices = {
                "Adam (JARVIS style — Deep Male)": "pNInz6obpgDQGcFmaJgB",
                "Antoni (Friendly Male)":          "ErXwobaYiN019PkySvjV",
                "Arnold (Strong Male)":            "VR6AewLTigWG4xSOukaG",
                "Rachel (Professional Female)":    "21m00Tcm4TlvDq8ikWAM",
                "Domi (Strong Female)":            "AZnzlk1XvdvUeBnXmlld",
            }
            out = f"\n{Y}╔══ 🎤 ELEVENLABS VOICES ══╗{RS}\n"
            out += f"  {DM}Current Voice ID: {CFG.get('elevenlabs_voice_id','pNInz6obpgDQGcFmaJgB')}{RS}\n\n"
            for name, vid in voices.items():
                current = f" {G}← ACTIVE{RS}" if CFG.get('elevenlabs_voice_id', 'pNInz6obpgDQGcFmaJgB') == vid else ""
                out += f"  {C}{name}{RS}{current}\n"
                out += f"    {DM}config set elevenlabs_voice_id {vid}{RS}\n"
            out += f"{Y}╚{'═'*44}╝{RS}\n"
            print(out)

        elif re.match(r'^voice test', cmd):
            test_text = re.sub(r'^voice test\s*', '', user_input, flags=re.I).strip()
            test_text = test_text or f"Hello Boss! Main FRIDAY hoon, aapki personal AI assistant!"
            print_friday(cy(f"Testing voice: '{test_text}'"))
            speak(test_text)
            print_friday(cg("Voice test complete! Kaise lagi Boss?"))

        # ── MP3 DOWNLOADER ───────────────────────────────────
        elif re.match(r'^(download|dl|mp3 download|song download|gana download)\s+', cmd):
            query = re.sub(r'^(download|dl|mp3 download|song download|gana download)\s+', '', user_input, flags=re.I).strip()
            if query.startswith('http'):
                url = query
            else:
                url = f'ytsearch1:{query}'
                print_friday(f"🔍 YouTube pe dhundh raha hoon: '{query}'...")
            print(download_mp3(url))

        elif any(x in cmd for x in ['downloaded songs', 'download list', 'meri downloads', 'dl list']):
            print(download_status())

        # ── SMART TODO ────────────────────────────────────────
        elif re.match(r'^(todo done|todo complete|kaam hua)\s+', cmd):
            tid = re.sub(r'^(todo done|todo complete|kaam hua)\s+', '', cmd).strip()
            msg = todo_done(tid)
            print_friday(msg); speak("Wah Boss! Todo complete ho gaya!")

        elif any(x in cmd for x in ['todos clear', 'todo clear', 'saare todos hatao']):
            msg = todo_clear()
            print_friday(msg); speak("Saare todos clear ho gaye Boss!")

        elif any(x in cmd for x in ['todos', 'todo list', 'kaam ki list', 'todo dekho', 'mere todos']):
            print(todo_show()); speak("Todo list taiyaar hai Boss!")

        elif re.match(r'^(todo add|kaam add|kaam likhao|add todo)\s+', cmd):
            text = re.sub(r'^(todo add|kaam add|kaam likhao|add todo)\s*', '', user_input, flags=re.I).strip()
            if text:
                msg = todo_add(text)
                print_friday(msg); speak(f"Todo add ho gaya Boss! Priority detect ki.")
            else:
                msg = "Kya add karoon Boss? Jaise: todo add report banana hai urgent"
                print_friday(cy(msg)); speak(msg)

        # ── DOCUMENT READER ───────────────────────────────────
        elif re.match(r'^(padho|read|document padho|file padho|summarize)', cmd):
            path = re.sub(r'^(padho|read|document padho|file padho|summarize)\s*', '', user_input, flags=re.I).strip()
            if path:
                speak("Document padh rahi hoon Boss!")
                print(read_document(path))
            else:
                msg = "Kaunsa file Boss? Jaise: padho /sdcard/file.pdf"
                print_friday(cy(msg)); speak(msg)

        # ── OCR ───────────────────────────────────────────────
        elif any(x in cmd for x in ['ocr', 'image se text', 'text nikalo', 'text extract']) or cmd == 'text scan':
            parts = cmd.split()
            img_path = None
            for p in parts:
                if '/' in p or p.endswith(('.jpg','.png','.jpeg')):
                    img_path = p
                    break
            speak("Image scan kar rahi hoon Boss!")
            print(friday_ocr(img_path))

        # ── BEHAVIOR REPORT ───────────────────────────────────
        elif any(x in cmd for x in ['behavior report', 'meri habits', 'usage report', 'main kya karta', 'behavior dekho']):
            print(behavior_report()); speak("Behavior report taiyaar hai Boss! Dekho aapki habits kya hain.")

        # ── ALARM ────────────────────────────────────────────
        elif re.match(r'^(alarm|alarm set|uthao)\s+', cmd):
            text = re.sub(r'^(alarm|alarm set|uthao)\s*', '', user_input, flags=re.I).strip()
            msg = alarm_add(text)
            print_friday(msg); speak("Alarm set ho gaya Boss!")

        elif any(x in cmd for x in ['alarms', 'alarm list', 'mere alarms', 'alarms dekho']):
            print(alarms_show()); speak("Alarms list Boss!")

        # ── HABITS & LIFE SCORE ───────────────────────────────
        elif any(x in cmd for x in ['habits', 'life score', 'aaj ki habits', 'habits dekho', 'mera score']):
            print(habits_today())

        elif any(x in cmd for x in ['habit streak', 'streaks', 'meri streaks', 'habit fire']):
            print(habits_streak()); speak("Habit streaks dekho Boss!")

        elif re.match(r'^(habit log|habit done)\s+', cmd):
            parts = re.sub(r'^(habit log|habit done)\s*', '', cmd).split()
            hid = parts[0] if parts else ''
            val = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
            msg = habit_log_entry(hid, val)
            print_friday(msg); speak("Habit logged Boss!")

        # ── EMOTION ───────────────────────────────────────────
        elif any(x in cmd for x in ['emotion history', 'meri emotions', 'emotions dekho', 'feelings dekho']):
            print(emotion_history()); speak("Emotion history taiyaar hai Boss!")

        # ── SMS ───────────────────────────────────────────────
        elif any(x in cmd for x in ['sms padho', 'sms dekho', 'inbox dekho', 'messages padho', 'sms read']):
            count = 5
            for p in cmd.split():
                if p.isdigit(): count = int(p); break
            print(sms_read(count))

        # ── CALL ──────────────────────────────────────────────
        elif re.match(r'^(call karo|phone karo)\s+', cmd):
            name = re.sub(r'^(call karo|phone karo)\s*', '', user_input, flags=re.I).strip()
            print_friday(call_contact(name))

        # ── MULTI-AGENT ───────────────────────────────────────
        elif any(x in cmd for x in ['agents', 'agent status', 'experts', 'expert list', 'agents dekho']):
            print(agent_status()); speak("Saare expert agents ready hain Boss!")

        elif re.match(r'^(ask finance|finbot|finance expert)', cmd):
            q = re.sub(r'^(ask finance|finbot|finance expert)\s*', '', user_input, flags=re.I).strip()
            r = agent_ask("finance", q or user_input)
            if r: print(f"\n  {Y}💰 FinBot:{RS} {r}\n"); speak(r)

        elif re.match(r'^(ask health|healthbot|health expert)', cmd):
            q = re.sub(r'^(ask health|healthbot|health expert)\s*', '', user_input, flags=re.I).strip()
            r = agent_ask("health", q or user_input)
            if r: print(f"\n  {Y}💪 HealthBot:{RS} {r}\n"); speak(r)

        elif re.match(r'^(ask tech|techbot|tech expert)', cmd):
            q = re.sub(r'^(ask tech|techbot|tech expert)\s*', '', user_input, flags=re.I).strip()
            r = agent_ask("tech", q or user_input)
            if r: print(f"\n  {Y}💻 TechBot:{RS} {r}\n"); speak(r)

        elif re.match(r'^(ask creative|creativebot|creative expert|poem|shayari)', cmd):
            q = re.sub(r'^(ask creative|creativebot|creative expert)\s*', '', user_input, flags=re.I).strip()
            r = agent_ask("creative", q or user_input)
            if r: print(f"\n  {Y}🎨 CreativeBot:{RS} {r}\n"); speak(r)

        elif re.match(r'^(ask life|lifebot|life coach|motivate me)', cmd):
            q = re.sub(r'^(ask life|lifebot|life coach|motivate me)\s*', '', user_input, flags=re.I).strip()
            r = agent_ask("life", q or user_input)
            if r: print(f"\n  {Y}🌟 LifeBot:{RS} {r}\n"); speak(r)

        elif re.match(r'^(ask news|newsbot|news expert)', cmd):
            q = re.sub(r'^(ask news|newsbot|news expert)\s*', '', user_input, flags=re.I).strip()
            r = agent_ask("news", q or user_input)
            if r: print(f"\n  {Y}📰 NewsBot:{RS} {r}\n"); speak(r)

        # ── LIVE NEWS ───────────────────────────────────
        elif cmd in ["news","khabar","aaj ki news","top news","latest news"]:
            print(get_live_news("india"))
        elif any(x in cmd for x in ["india news","india khabar","desh ki khabar"]):
            print(get_live_news("india"))
        elif any(x in cmd for x in ["world news","duniya ki khabar","international news"]):
            print(get_live_news("world"))
        elif any(x in cmd for x in ["business news","market news"]):
            print(get_live_news("business"))

        # ── STOCK + CRYPTO ──────────────────────────────
        elif re.match(r"^(stock|share price|price of)\s+", cmd):
            sym = re.sub(r"^(stock|share price|price of)\s*","",user_input,flags=re.I).strip()
            if sym: print(get_stock_price(sym))
            else: print_friday(cy("Kaunsa stock Boss? Jaise: stock RELIANCE"))
        elif any(x in cmd for x in ["crypto","bitcoin","btc price","crypto summary"]):
            print(get_crypto_summary())
        elif any(x in cmd for x in ["nifty","sensex","share market","stock market"]):
            print(get_stock_price("NIFTY"))

        # ── CRICKET + SPORTS ─────────────────────────────
        elif any(x in cmd for x in ["nasa","space","apod","aaj ka space","astronomy","antriksh"]):
            print(get_nasa_apod())

        elif any(x in cmd for x in ["cricket","live score","cricket score","ipl score","match score"]):
            print(get_cricket_score())
        elif any(x in cmd for x in ["sports news","khel samachar"]):
            print(get_sports_news())

        # ── YOUTUBE + SOCIAL BUZZ ────────────────────────
        elif any(x in cmd for x in ["youtube trending","yt trending","trending videos"]):
            print(get_youtube_trending())
        elif any(x in cmd for x in ["social buzz","trending topics","tech buzz","kya trend"]):
            print(get_social_buzz())

        # ── SMART REMINDERS ───────────────────────────────────
        elif re.match(r'^(reminder done|reminder hatao)\s+', cmd):
            num = re.sub(r'^(reminder done|reminder hatao)\s+', '', cmd).strip()
            msg = reminder_done(num)
            print_friday(msg); speak(msg.replace("\033[92m","").replace("\033[0m",""))

        elif any(x in cmd for x in ['reminders', 'reminder list', 'mere reminders', 'alerts dekho']):
            print(reminders_show()); speak("Reminders list taiyaar hai Boss!")

        elif re.match(r'^(reminder|remind|yaad dilao|alert set)\s+', cmd):
            text = re.sub(r'^(reminder|remind|yaad dilao|alert set)\s*', '', user_input, flags=re.I).strip()
            msg = reminder_add(text)
            print_friday(msg)
            if "set" in msg.lower() or "set!" in msg:
                speak(f"Reminder set ho gaya Boss! {text[:60]}")
            else:
                speak(msg[:80])

        # ── WIKIPEDIA + TRANSLATION ───────────────────────────
        elif re.match(r'^(wiki|wikipedia|kya hai|explain)\s+', cmd):
            query = re.sub(r'^(wiki|wikipedia|kya hai|explain)\s*', '', user_input, flags=re.I).strip()
            if query:
                result = wiki_search(query)
                print(result)
            else:
                print_friday(cy("Kya search karoon Boss? Jaise: wiki artificial intelligence"))
                speak("Kya search karoon Boss?")

        elif re.match(r'^(translate|anuvad|translate karo)\s+', cmd):
            text = re.sub(r'^(translate|anuvad|translate karo)\s*', '', user_input, flags=re.I).strip()
            if text:
                print(translate_text(text))
            else:
                print_friday(cy("Kya translate karoon Boss?"))
                speak("Kya translate karoon Boss?")

        # ── ANOMALY ───────────────────────────────────────────
        elif any(x in cmd for x in ['anomaly report', 'anomaly check', 'unusual activity', 'kuch galat', 'anomaly dekho']):
            result = anomaly_report()
            print(result); speak("Anomaly report check kar liya Boss!")

        # ── JARVIS DASHBOARD ──────────────────────────────────
        elif any(x in cmd for x in ['jarvis', 'jarvis dashboard', 'full dashboard', 'sab ek screen', 'poora status']):
            print(show_jarvis_dashboard()); speak("Jarvis dashboard taiyaar hai Boss!")

        # ── ERROR GUARDIAN ────────────────────────────────────
        elif any(x in cmd for x in ['error log', 'errors dikhao', 'kya kya error aya', 'error history', 'bugs dikhao']):
            print(error_guardian_show())

        # ── MONTHLY EXPENSE ANALYTICS ─────────────────────────
        elif any(x in cmd for x in ['monthly graph', 'expense graph', 'kharch graph', 'mahine ka graph', 'analytics', 'expense analytics']):
            result = expense_monthly_graph()
            print(result)
            speak("Boss, monthly expense graph taiyaar hai!")

        elif re.match(r'^(budget set|budget lagao|monthly budget)', cmd):
            parts = cmd.split()
            amt = next((p for p in parts if p.replace('.','').isdigit()), None)
            if amt:
                cat = parts[-1] if parts[-1] not in ['set','lagao','budget','monthly'] and not parts[-1].isdigit() else None
                msg = budget_set(amt, cat)
                print_friday(msg)
                speak(f"Budget set ho gaya Boss! Monthly limit {amt} rupaye.")
            else:
                print_friday(cy("Amount batao Boss! Jaise: budget set 5000"))

        elif any(x in cmd for x in ['budget check', 'budget kitna', 'budget status', 'budget dekho']):
            budget = budget_load()
            limit = budget.get("monthly_limit", 0)
            if not limit:
                print_friday(cy("Budget set nahi hai Boss! 'budget set 5000' bolo."))
            else:
                now = datetime.datetime.now()
                expenses = expense_load()
                total = sum(e["amount"] for e in expenses if e["date"].startswith(now.strftime("%Y-%m")))
                pct = (total/limit)*100
                color = R if pct >= 90 else Y if pct >= 70 else G
                msg = f"Budget mein {pct:.0f} percent kharch ho gaya Boss. {total:.0f} rupaye mein se {limit:.0f} mein se."
                print_friday(f"💰 Budget: {color}₹{total:.0f} / ₹{limit:.0f} ({pct:.0f}% used){RS}")
                speak(msg)

        # ── MULTI-LAYER REASONING ─────────────────────────────
        elif re.match(r'^(soch ke batao|deep soch|analyze karo|reason karo|samjha ke batao)', cmd):
            q = re.sub(r'^(soch ke batao|deep soch|analyze karo|reason karo|samjha ke batao)\s*', '', user_input, flags=re.I).strip()
            q = q or user_input
            print_friday(cy("🧠 Multi-layer reasoning shuru..."))
            result = multi_layer_reason(q, ltm, mem)
            if result:
                print_friday(result)
                speak(result)
                mem = add_memory(mem, "user", user_input)
                mem = add_memory(mem, "assistant", result)
            else:
                # Multi-Agent: pehle expert agent try karo
                agent_resp = None
                try:
                    agent_resp = agent_central_brain(user_input, mem, ltm)
                except: pass

                if agent_resp:
                    print(agent_resp)
                    mem = add_memory(mem, "user", user_input)
                    mem = add_memory(mem, "assistant", agent_resp[:200])
                else:
                    # Central AI fallback
                    r = ask_ai(user_input)
                    if r:
                        print_friday(r); speak(r)
                        mem = add_memory(mem, "user", user_input)
                        mem = add_memory(mem, "assistant", r)

        # ── MEMORY ENCRYPTION ─────────────────────────────────
        elif any(x in cmd for x in ['memory encrypt', 'memory lock', 'memory secure karo']):
            if save_memory_encrypted(mem):
                print_friday(cg("🔐 Memory encrypted aur secure save ho gayi Boss!"))
                speak("Memory encrypt ho gayi Boss. Ab safe hai.")
            else:
                print_friday(cy("Encryption failed Boss."))

        elif any(x in cmd for x in ['memory decrypt', 'memory unlock', 'encrypted memory load']):
            enc_mem = load_memory_encrypted()
            if enc_mem:
                mem = enc_mem
                print_friday(cg(f"🔓 Encrypted memory load ho gayi! {len(enc_mem.get('messages',[]))} messages."))
                speak("Encrypted memory load ho gayi Boss.")
            else:
                print_friday(cy("Koi encrypted memory nahi mili Boss."))

        # ── HARDWARE GUARDIAN STATUS ─────────────────────────
        elif any(x in cmd for x in ['temperature', 'temp check', 'phone temp', 'garam hai', 'heat check', 'ram check', 'hardware status']):
            try:
                r = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=5)
                import json as _json
                d = _json.loads(r.stdout)
                temp = d.get("temperature", "N/A")
                r2 = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=5)
                ram_info = ""
                for line in r2.stdout.strip().split("\n"):
                    if line.startswith("Mem:"):
                        parts = line.split()
                        total, used = int(parts[1]), int(parts[2])
                        pct = (used/total)*100
                        ram_info = f"{pct:.0f}% ({used}/{total}MB)"
                        break
                G="[92m"; Y="[93m"; R="[91m"; RS="[0m"; BD="[1m"
                t_color = R if (isinstance(temp, (int,float)) and temp >= 40) else G
                out = f"\n{Y}╔══ 🌡️  HARDWARE STATUS ══╗{RS}\n"
                out += f"  🌡️  Temperature : {t_color}{BD}{temp}°C{RS}\n"
                out += f"  💾 RAM Usage   : {BD}{ram_info}{RS}\n"
                out += f"  🛡️  Guardian   : Active\n"
                out += f"{Y}╚{'═'*30}╝{RS}\n"
                print(out)
            except Exception as e:
                print_friday(cy(f"Hardware info nahi mili: {e}"))

        # ── SMART GEOFENCE ────────────────────────────────────
        elif re.match(r'^(ghar set karo|home set|office set|location save|geofence set)', cmd):
            parts = cmd.split()
            name = "home" if any(x in cmd for x in ["ghar","home"]) else "office" if "office" in cmd else (parts[-1] if len(parts) > 1 else "home")
            radius = 100
            result = geofence_set(name, radius)
            print_friday(result)
            speak(f"{name} location set ho gayi Boss!")

        elif any(x in cmd for x in ['geofence list', 'saved locations', 'meri locations']):
            data = geofence_load()
            locs = data.get("locations", {})
            if not locs:
                print_friday(cy("Koi location save nahi hai. 'ghar set karo' ya 'office set' bolo!"))
            else:
                G="[92m"; Y="[93m"; RS="[0m"; BD="[1m"
                out = f"\n{Y}╔══ 📍 SAVED LOCATIONS ══╗{RS}\n"
                for n, p in locs.items():
                    out += f"  {G}●{RS} {BD}{n}{RS} — {p['radius_m']}m radius\n"
                    out += f"    {p['lat']:.4f}, {p['lon']:.4f}\n"
                out += f"{Y}╚{'═'*30}╝{RS}\n"
                print(out)



        # ── PHONE SCANNER ────────────────────────────────────
        elif any(x in cmd for x in ['phone scan', 'poora scan', 'storage scan', 'mp3 dhundo', 'saare mp3', 'saari mp3', 'songs dhundo', 'saare songs', 'kya kya hai phone me', 'phone me kya hai', 'internal scan', 'sd card scan']):
            if any(x in cmd for x in ['mp3', 'song', 'audio', 'gana']):
                print_friday("🔍 Poore phone mein MP3 dhundh raha hoon...")
                print(phone_scan("mp3"))
            else:
                print_friday("🔍 Poora phone scan ho raha hai Sir, ek second...")
                print(phone_scan("all"))

        # ── FILE MANAGER ─────────────────────────────────────
        elif re.match(r'^(files|ls|list files|folder dekho|downloads dekho)', cmd):
            path = re.sub(r'^(files|ls|list files|folder dekho|downloads dekho)\s*', '', user_input, flags=re.I).strip()
            print(file_list(path or None))

        elif re.match(r'^(files all|ls -la|saari files)', cmd):
            path = re.sub(r'^(files all|ls -la|saari files)\s*', '', user_input, flags=re.I).strip()
            print(file_list(path or None, show_all=True))

        elif re.match(r'^(delete file|file delete|hatao file|rm )\s+.+', cmd):
            targets_raw = re.sub(r'^(delete file|file delete|hatao file|rm )\s+', '', user_input, flags=re.I).strip()
            targets = [t.strip() for t in targets_raw.split(',')]
            folder_hint = None
            if ' from ' in targets_raw.lower():
                parts = targets_raw.lower().split(' from ', 1)
                targets = [parts[0].strip()]
                folder_hint = parts[1].strip()
            print(file_delete(targets, folder_hint))

        elif any(x in cmd for x in ['organize downloads', 'downloads organize', 'files organize', 'organize files']):
            folder_hint = re.sub(r'(organize downloads|downloads organize|files organize|organize files)', '', user_input, flags=re.I).strip()
            print(file_organize(folder_hint or None))
            speak("Files organize ho gayi Boss!")

        elif any(x in cmd for x in ['clean downloads', 'downloads saaf karo', 'downloads clean', 'junk delete']):
            print(file_clean_downloads())
            speak("Downloads clean ho gaya Boss!")

        # ── SELF HEALING ──────────────────────────────────────
        elif re.match(r'^(bug fix|fix bug|syntax check|code check|friday check karo|self check)', cmd):
            ok, msg = self_check_syntax()
            if ok:
                print_friday(cg(f"✅ {msg}"))
            else:
                print_friday(cy(f"⚠ Syntax issue mili:\n{msg}"))
                print_friday(cy("'fix error <description>' se fix karwa sakte ho Boss"))

        elif re.match(r'^(fix error|bug report|error fix|self fix)\s+.+', cmd):
            error_desc = re.sub(r'^(fix error|bug report|error fix|self fix)\s+', '', user_input, flags=re.I).strip()
            print(self_fix_bug(error_desc))

        elif any(x in cmd for x in ['fix history', 'self heal history', 'bug history']):
            print(selfheal_history())


        # ── VOICE MODE ────────────────────────────────────────
        elif any(x in cmd for x in ['voice mode', 'voice on', 'awaaz mode', 'voice chalu', 'sunlo', 'voice se baat', 'voice']) and 'off' not in cmd and 'band' not in cmd:
            _voice_mode_active = True
            print_friday(cg("🎤 Voice Mode ON! Bolte raho — 'voice band' bolein band karne ke liye"))
            speak("Voice mode on hai Sir. Bolte raho!")

        # ── SECRETARY MODE ────────────────────────────────────
        elif re.match(r'^(meeting add|add meeting|schedule meeting|meeting schedule)\s+.+', cmd):
            text = re.sub(r'^(meeting add|add meeting|schedule meeting|meeting schedule)\s+', '', user_input, flags=re.I).strip()
            print_friday(sec_add_meeting(text))
            speak("Meeting add ho gayi Boss!")

        elif any(x in cmd for x in ['meetings', 'my meetings', 'schedule dekho', 'aaj ki meetings', 'kal ki meetings']):
            days = 1 if 'aaj' in cmd else 2 if 'kal' in cmd else 7
            print(sec_list_meetings(days))

        elif re.match(r'^(meeting delete|delete meeting|meeting hatao)\s+\d+', cmd):
            mid = int(re.search(r'\d+', cmd).group())
            print_friday(sec_delete_meeting(mid))

        elif re.match(r'^(agenda add|add agenda|kaam add)\s+.+', cmd):
            text = re.sub(r'^(agenda add|add agenda|kaam add)\s+', '', user_input, flags=re.I).strip()
            print_friday(sec_add_agenda(text))

        elif any(x in cmd for x in ['agenda', 'aaj ka kaam', 'today agenda', 'kaam list']):
            print(sec_show_agenda())

        elif re.match(r'^(agenda done|done agenda|kaam khatam)\s+\d+', cmd):
            aid = int(re.search(r'\d+', cmd).group())
            print_friday(sec_done_agenda(aid))

        elif any(x in cmd for x in ['secretary briefing', 'sec briefing', 'office briefing']):
            print(sec_briefing())

        # ── AI CHAT (fallback) ────────────────────────────────
        else:
            # Garbage input filter — bahut chota ya sirf symbols
            clean_cmd = re.sub(r'[^a-zA-Z0-9\u0900-\u097F\s]', '', cmd).strip()
            if len(clean_cmd) < 3:
                print_friday(cy("Samajh nahi aaya Boss. Dobara likhein ya 'help' type karein."))
            elif GROQ_KEY:
                _stop=threading.Event()
                _th=threading.Thread(target=ai_thinking,args=(_stop,),daemon=True); _th.start()
                # Include LT memory context
                lt_ctx = ltmem_get_context(ltm, user_input)
                history = mem.get("messages",[])
                if lt_ctx:
                    full_input = f"{lt_ctx}\n\nUser question: {user_input}"
                else:
                    full_input = user_input
                resp = ask_ai(full_input, history)
                _stop.set(); _th.join()
                if resp:
                    # ── Safety: AI response ko command ki tarah mat chalaao ──
                    resp_check = resp.strip().lower()
                    cmd_triggers = ["imagine ", "image banao", "generate image", "create image"]
                    if any(resp_check.startswith(trigger) for trigger in cmd_triggers):
                        # AI ne imagine command suggest kiya — sirf print karo, execute mat karo
                        resp = "[FRIDAY suggestion] " + resp
                    # Direct response — clean aur simple
                    print_friday(resp); speak(resp)
                    mem=add_memory(mem,"user",user_input)
                    mem=add_memory(mem,"assistant",resp)
                    # Auto-learn DISABLED — manual save only
                    # Auto-save DISABLED — sirf "save karo/note karo" pe save hoga
                else:
                    print_friday(cy("Connection issue Boss. Check internet or API key."))
            else:
                print_friday(cy(f"Boss, GROQ_API_KEY set nahi hai.\nRun: export GROQ_API_KEY='your_key_here'"))

if __name__ == "__main__":
    try:
        main()
    except Exception as _main_err:
        import traceback
        err_text = traceback.format_exc()
        suggestions = error_guardian_log(str(_main_err), "main crash")
        print(f"\033[91m\n💥 FRIDAY Error: {_main_err}\033[0m")
        if suggestions:
            print(f"\033[93m🛠️  Fix suggestion: {suggestions[0]}\033[0m")
        raise

