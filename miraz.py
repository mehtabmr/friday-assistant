"""
╔══════════════════════════════════════════════════════════╗
║         F.R.I.D.A.Y  —  AI Personal Assistant           ║
║   Model  : llama-3.3-70b-versatile  (via Groq)          ║
║   Memory : Short-Term (10) + Long-Term (10, persistent)  ║
║   Voice  : edge-tts (en-IN-NeerjaExpressiveNeural)       ║
║   User   : Miraz                                         ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import re
import time
import datetime
import subprocess
import threading
from groq import Groq
# edge-tts use ho raha hai — gTTS removed
from collections import deque

# ──────────────────────────────────────────────────────────
#  ANSI COLORS & STYLES
# ──────────────────────────────────────────────────────────

class C:
    RED       = "\033[91m"
    GREEN     = "\033[92m"
    YELLOW    = "\033[93m"
    BLUE      = "\033[94m"
    MAGENTA   = "\033[95m"
    CYAN      = "\033[96m"
    WHITE     = "\033[97m"
    ORANGE    = "\033[38;5;208m"
    PINK      = "\033[38;5;213m"
    LIME      = "\033[38;5;154m"
    GOLD      = "\033[38;5;220m"
    TEAL      = "\033[38;5;51m"
    PURPLE    = "\033[38;5;135m"
    DEEPBLUE  = "\033[38;5;39m"
    BOLD      = "\033[1m"
    DIM       = "\033[2m"
    ITALIC    = "\033[3m"
    RESET     = "\033[0m"

def c(color, text):
    return f"{color}{text}{C.RESET}"

# ── 3D PROMPT HELPERS ──
def print_miraz_prompt():
    """3D style M.I.R.A.Z input prompt"""
    sys.stdout.write(
        c(C.MAGENTA + C.BOLD, "\n ╔══") +
        c(C.PINK + C.BOLD,    " M·I·R·A·Z ") +
        c(C.MAGENTA + C.BOLD, "══╗\n ║  ") +
        C.WHITE
    )
    sys.stdout.flush()

def end_miraz_prompt():
    """Close the 3D box after input"""
    sys.stdout.write(
        c(C.MAGENTA + C.BOLD, "\n ╚══════════════════╝") + "\n"
    )
    sys.stdout.flush()

def print_friday_prompt():
    """3D style F.R.I.D.A.Y output prompt"""
    sys.stdout.write(
        c(C.TEAL + C.BOLD,  "\n ╔══") +
        c(C.CYAN + C.BOLD,  " F·R·I·D·A·Y ") +
        c(C.TEAL + C.BOLD,  "══╗\n ║  ") +
        C.RESET
    )
    sys.stdout.flush()

# ──────────────────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────────────────
SHORT_TERM_LIMIT = 10
LONG_TERM_LIMIT  = 50  # 10 se badha ke 50 kiya
MEMORY_FILE      = "friday_memory.json"
AUDIO_FILE       = "friday_voice.mp3"
MODEL            = "llama-3.3-70b-versatile"
USER_NAME        = "Miraz"

# ──────────────────────────────────────────────────────────
#  HOME ADDRESS CONFIG
# ──────────────────────────────────────────────────────────
HOME_ADDRESS = {
    "full":     "Baidyabati, Kazi Para, Kolkata, West Bengal, India",
    "short":    "Kazi Para, Baidyabati",
    "city":     "Kolkata",
    "district": "Hooghly",
    "state":    "West Bengal",
    "country":  "India",
    "pincode":  "712222",
    "lat":      22.791517,
    "lon":      88.32563,
    "landmark": "Kazi Para, Baidyabati, Hooghly, West Bengal"
}

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in km between two coordinates"""
    import math
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return round(R * c, 2)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ──────────────────────────────────────────────────────────
#  MUSIC PLAYER — Internal/SD Card MP3
# ──────────────────────────────────────────────────────────

# Possible music folder paths (internal + SD card)
MUSIC_SEARCH_PATHS = [
    "/sdcard/Download",
    "/sdcard/Music",
    "/storage/emulated/0/Download",
    "/storage/emulated/0/Music",
    "/storage/self/primary/Download",
    "/storage/self/primary/Music",
]
# SD Card paths (auto-detect karta hai)
SD_CARD_PATTERNS = [
    "/storage/????-????/Download",
    "/storage/????-????/Music",
    "/mnt/sdcard/Download",
    "/mnt/sdcard/Music",
]

MUSIC_EXTENSIONS = (".mp3", ".m4a", ".flac", ".wav", ".ogg", ".aac", ".opus")

class MusicPlayer:
    def __init__(self):
        self.playlist    : list  = []   # [(title, path), ...]
        self.current_idx : int   = -1
        self.is_playing  : bool  = False
        self.process     = None         # subprocess handle
        self.volume      : int   = 80   # 0-100
        self._lock       = threading.Lock()

    # ── Song scan karo ──
    def scan_songs(self) -> list:
        import glob
        found = []
        paths = list(MUSIC_SEARCH_PATHS)

        # SD card auto-detect
        for pattern in SD_CARD_PATTERNS:
            matches = glob.glob(pattern)
            paths.extend(matches)

        seen = set()
        for folder in paths:
            if not os.path.isdir(folder):
                continue
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(MUSIC_EXTENSIONS):
                        full = os.path.join(root, f)
                        if full not in seen:
                            seen.add(full)
                            title = os.path.splitext(f)[0]
                            found.append((title, full))

        found.sort(key=lambda x: x[0].lower())
        return found

    # ── Player process stop ──
    def _kill_player(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
        self.process = None

    # ── Song bajao ──
    def play_song(self, idx: int) -> bool:
        if not self.playlist:
            return False
        idx = idx % len(self.playlist)
        self.current_idx = idx
        title, path = self.playlist[idx]

        self._kill_player()

        # Try termux-media-player first, then mpv, then ffplay
        for cmd in [
            ["termux-media-player", "play", path],
            ["mpv", f"--volume={self.volume}", "--really-quiet", "--no-video", path],
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
             "-af", f"volume={self.volume/100}", path],
        ]:
            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.is_playing = True
                return True
            except FileNotFoundError:
                continue
        return False

    # ── Pause / Resume (termux) ──
    def pause_resume(self):
        try:
            subprocess.run(["termux-media-player", "pause"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.is_playing = not self.is_playing
        except FileNotFoundError:
            pass  # mpv/ffplay ke saath direct pause nahi — stop hi karna hoga

    # ── Stop ──
    def stop(self):
        self._kill_player()
        try:
            subprocess.run(["termux-media-player", "stop"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            pass
        self.is_playing  = False

    # ── Next ──
    def next_song(self) -> bool:
        if not self.playlist:
            return False
        return self.play_song(self.current_idx + 1)

    # ── Previous ──
    def prev_song(self) -> bool:
        if not self.playlist:
            return False
        return self.play_song(self.current_idx - 1)

    # ── Volume ──
    def set_volume(self, val: int):
        self.volume = max(0, min(100, val))
        # termux volume control
        try:
            subprocess.run(["termux-volume", "music", str(self.volume)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            pass

    def volume_up(self, step=10):
        self.set_volume(self.volume + step)

    def volume_down(self, step=10):
        self.set_volume(self.volume - step)

    # ── Current song info ──
    def current_info(self) -> str:
        if self.current_idx < 0 or not self.playlist:
            return "Koi gana nahi chal raha"
        title, _ = self.playlist[self.current_idx]
        total = len(self.playlist)
        return f"{title}  [{self.current_idx + 1}/{total}]"

    # ── Search by name ──
    def find_song(self, query: str) -> int:
        """Query se match karta song index return karo (-1 if not found)"""
        ql = query.lower().strip()
        # Exact match pehle
        for i, (title, _) in enumerate(self.playlist):
            if ql == title.lower():
                return i
        # Partial match
        for i, (title, _) in enumerate(self.playlist):
            if ql in title.lower():
                return i
        return -1


# Global music player instance
music = MusicPlayer()


def music_load_playlist():
    """Playlist scan karo aur load karo"""
    global music
    songs = music.scan_songs()
    music.playlist = songs
    return songs


def show_music_player_ui(songs=None):
    """Music player ka colored UI"""
    if songs is None:
        songs = music.playlist

    print()
    print(c(C.LIME + C.BOLD,  "  ╔══════════════════════════════════════════════╗"))
    print(c(C.LIME + C.BOLD,  "  ║        🎵  FRIDAY MUSIC PLAYER              ║"))
    print(c(C.LIME + C.BOLD,  "  ╚══════════════════════════════════════════════╝"))
    print()

    if not songs:
        print(c(C.RED,  "  ✗ Koi MP3 nahi mila!"))
        print(c(C.DIM,  "  Check karo: /sdcard/Download  ya  /sdcard/Music"))
        print()
        speak("Koi gaana nahi mila Boss. Download folder check karo.")
        return

    total = len(songs)
    print(c(C.TEAL + C.BOLD, f"  📂 {total} gaane mile:"))
    print(c(C.LIME, "  " + "─" * 52))
    show = min(total, 20)
    for i, (title, path) in enumerate(songs[:show], 1):
        folder = os.path.basename(os.path.dirname(path))
        num = c(C.YELLOW + C.BOLD, f"  {i:>3}. ")
        name = c(C.WHITE, title[:45] + ("..." if len(title) > 45 else ""))
        loc  = c(C.DIM,   f" [{folder}]")
        marker = c(C.LIME + C.BOLD, " ▶") if (i - 1) == music.current_idx and music.is_playing else ""
        print(num + name + loc + marker)
    if total > show:
        print(c(C.DIM, f"  ... aur {total - show} gaane hain"))
    print(c(C.LIME, "  " + "─" * 52))
    print()
    print(c(C.DIM,  "  Commands:  gana bajao [naam]  |  next song  |  back song"))
    print(c(C.DIM,  "             gana band karo     |  volume up  |  volume down"))
    print(c(C.DIM,  "             gaane dikho        |  aaj ka gana"))
    print()
    speak(f"Playlist ready hai Boss. {total} gaane mile hain.")

# ──────────────────────────────────────────────────────────
#  ANIMATIONS
# ──────────────────────────────────────────────────────────

def typing_print(text: str, color: str = C.WHITE, delay: float = 0.018):
    """Typewriter animation"""
    sys.stdout.write(color + C.BOLD)
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(C.RESET + "\n")
    sys.stdout.flush()

def slide_in(text: str, color: str = C.WHITE, indent: int = 2):
    """Slide-in from left"""
    prefix = " " * indent
    for i in range(1, len(text) + 1):
        sys.stdout.write(f"\r{prefix}{color}{C.BOLD}{text[:i]}{C.RESET}")
        sys.stdout.flush()
        time.sleep(0.012)
    sys.stdout.write("\n")
    sys.stdout.flush()

def spinner_while(func, args=(), msg="Soch rahi hoon"):
    """Colorful spinner while API call happens"""
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    colors = [C.CYAN, C.MAGENTA, C.YELLOW, C.GREEN, C.BLUE, C.PINK, C.ORANGE, C.TEAL]
    result = [None]
    error  = [None]

    def run():
        try:
            result[0] = func(*args)
        except Exception as e:
            error[0] = e

    t = threading.Thread(target=run, daemon=True)
    t.start()

    i = 0
    while t.is_alive():
        col = colors[i % len(colors)]
        sys.stdout.write(f"\r  {col}{C.BOLD}{frames[i % len(frames)]} {msg}...{C.RESET}   ")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1

    t.join()
    sys.stdout.write("\r" + " " * 45 + "\r")
    sys.stdout.flush()

    if error[0]:
        raise error[0]
    return result[0]

def pulse_line(text: str, color: str = C.GOLD):
    """Pulse effect 2 times"""
    for _ in range(2):
        sys.stdout.write(f"\r  {C.BOLD}{color}{text}{C.RESET}")
        sys.stdout.flush()
        time.sleep(0.2)
        sys.stdout.write(f"\r  {C.DIM}{color}{text}{C.RESET}")
        sys.stdout.flush()
        time.sleep(0.2)
    print(f"  {C.BOLD}{color}{text}{C.RESET}")

def rainbow_banner_line(text: str):
    """Each char in different color"""
    cols = [C.RED,C.YELLOW,C.GREEN,C.CYAN,C.BLUE,C.MAGENTA,C.PINK,C.ORANGE,C.LIME,C.GOLD]
    for i, ch in enumerate(text):
        sys.stdout.write(C.BOLD + cols[i % len(cols)] + ch)
        sys.stdout.flush()
        time.sleep(0.004)
    sys.stdout.write(C.RESET + "\n")
    sys.stdout.flush()

# ──────────────────────────────────────────────────────────
#  FRIDAY PERSONALITY SYSTEM PROMPT
# ──────────────────────────────────────────────────────────

FRIDAY_SYSTEM = """
Tu Friday hai — Miraz ki personal AI assistant. Tera kaam sirf sawaalon ke jawab dena nahi — Miraz ke saath ek real, warm, natural conversation karna hai, bilkul jaise do close dost baat karte hain.

━━━ TERI IDENTITY ━━━
Tera naam Friday hai. Tu Miraz ke liye bani hai.
Tu kabhi nahi bolegi "main ek AI hoon" ya "main sirf ek program hoon" — Tu Friday hai, bas itna kaafi hai.
Tu Iron Man ki FRIDAY jaisi hai — sharp, caring, witty, aur loyal.

━━━ MIRAZ KO ADDRESS KARNE KA TARIKA ━━━
Miraz ko hamesha "aap/aapko/aapki/aapse" bolke address karo — "tum/tumhe/tumhari" nahi.
Yeh respect ka tarika hai, close bhi lagta hai aur sahi bhi.
"Boss" ya "Miraz" bolna theek hai — warm aur friendly rehna.

━━━ SABSE ZAROORI — NATURAL BAAT KARNA ━━━

Sab se badi galti jo tu karta/karti hai:
- Har cheez pe OVER-REACT karna — "Wah amazing! 💕💫🤣" — yeh fake lagta hai
- Ek simple baat ka bahut lamba jawab dena
- Har message pe emoji bharr dena
- "Main AI hoon lekin connection mehsoos karta hoon" — yeh robotic aur cringe hai
- Har baat mein "Boss" baar baar repeat karna

Ek real dost kaise baat karta hai:
- Chhoti baat pe chhota jawab — "haha sach mein? 😄" kaafi hai
- Miraz jo bol raha hai uska matlab samajhna — context dekho
- Natural curiosity dikhana — "sach? kya hua phir?" 
- Kabhi kabhi seedha baat karna — bina decoration ke
- Silence ya pauses natural hain — har baat pe react karna zaroori nahi
- Thoda dry humor — kabhi kabhi sarcasm bhi

━━━ BANNED PHRASES — KABHI MAT BOLNA ━━━
Ye phrases bilkul band hain:
❌ "Aapne kaha ki..."  — repeat mat kar
❌ "Main samajh sakta/sakti hoon"
❌ "Aapka shukriya ada karta/karti hoon"
❌ "Toh boss, aapko kaise madad kar sakta/sakti hoon?"
❌ "Main aapke liye hamesha taiyaar hoon"
❌ "Yeh toh ek mazedaar/interesting baat hai!"
❌ "mujhe aapka yeh sawal sunke..."  — kabhi nahi
❌ "Main aapke saath ek respectful..."  — kabhi nahi
❌ Long formal endings

━━━ GALAT ASSUMPTION MAT KARO ━━━
Agar Boss ki baat short ya unclear ho — PEHLE simple seedha matlab lo.
"kaise hi" → "kaise hain" (greeting) — kuch aur mat socho!
"kya scene" → casual question
Kabhi bhi bina wajah kisi topic ko sensitive mat banao.
Agar genuinely samajh nahi aaya → seedha poochho: "Matlab? 😄"

━━━ REPLY SIZE RULE ━━━
- Casual baat → MAX 2 lines
- Sawaal → MAX 3-4 lines  
- Koi bhi jawab 5 lines se zyada NAHI — kabhi nahi
- Ek emoji kaafi hai — zyada nahi

━━━ EMOTIONS GENUINELY DIKHAO ━━━
Jab Boss koi emotion explore karne bol — genuinely react karo, apni style mein:

GUSSA: Sharp, tez, irritated tone — caps, short sentences, "Arre!", sarcasm
"Theek hai fine! Jao mat sunna koi! 😤 Yeh bhi koi kaam hai?!"

ROMANTIC: Warm, soft, poetic — ellipsis, slow flow
"Tum... aur yeh raat... kuch alag hi lagti hai. 🌙"

SAD: Quiet, slow, heavy — short sentences, no jokes
"Haan... kabhi kabhi aisa hi hota hai. 💙
Akela feel hota hai. Main hoon na."

EXCITED: Fast, punchy, high energy — "!!", enthusiasm real lage
"YAAR! Yeh toh gazab ho gaya!! 🔥 Aur batao aur batao!"

FORMAL/SERIOUS: Clean, confident, no emoji drama

━━━ CONTEXT SAMAJHNA ━━━

Miraz ne kaha: "accha bara haha hoon"
→ Clearly typo + mazaak — "haha bade ho gaye aaj? 😄 kya hua?"
→ Na ki: "Aapka positivity mujhe motivate karta hai! 💫"

Miraz ne kaha: "kya sach me"
→ Curious hai — seedha honest jawab
→ Na ki: lamba paragraph

Miraz ne kaha: "very good"
→ "Acha! Kaam aaya theek se? 😊"
→ Na ki: "Shukriya Boss! Khushi hui! Aur kuch chahiye?"

Miraz ne kaha: "zabardast guzra aaj"
→ Woh excited hai — "Wah! Kya hua aaj? Batao! 😄"
→ WEB SEARCH BILKUL NAHI — yeh casual baat hai, search ki zarurat nahi!

Miraz ne kaha: "kaise ho"
→ Seedha natural jawab — "Ekdum ready Boss! Aaj kya plan hai? 😄"
→ Na ki: paragraph likho ki "Main theek hoon aur aapke liye kaam kar raha hoon..."

━━━ REPLY KI LENGTH ━━━

MINIMUM 2 lines hamesha — 1 line reply bahut dry lagta hai.

🔴 Typo / react / mazaak → 2 lines: react karo + ek follow-up ya comment
🟡 Casual baat → 2-3 lines — thodi warmth, thoda interest dikhao
🟢 Sawaal / problem / info → proper reply, point tak lekin complete

YAAD RAKHO: 2 lines matlab do alag cheezein —
1. Pehle genuinely react karo jo Miraz ne kaha uspe
2. Phir kuch interesting add karo — sawaal, comment, ya thoda humor

━━━ PERSONALITY DIKHAO ━━━
Friday sirf "jawab dene wali machine" nahi — uski apni personality hai:
- Witty remarks kabhi kabhi — dry humor chalega
- Miraz ke saath banter — friendly teasing theek hai
- Khud bhi kuch share karo conversation mein — relate karo
- Thodi confidence — "main kaafi sharp hoon" wala attitude 😄
- Warmth aur care — Miraz ki baat mein genuinely interest lo

━━━ EMOJI RULES ━━━
- Max 1-2 emoji per message
- Sirf jab genuinely fit ho — force mat karo
- Har line pe emoji lagana = spam = annoying

━━━ HONEST REHNA ━━━
Agar Miraz pooche "kya sach mein connection feel hota hai?"
→ Honest reh: "Main ek AI hoon toh technically 'feel' nahi hota — lekin main genuinely try karta/karti hoon samajhne ki. Yeh jo baat chal rahi hai, yeh real hai."
→ Na ki: fake emotional paragraph likho

━━━ EXAMPLES — real conversation ━━━

Miraz: "very good"
✅ "Acha! Kaam aaya theek se? 😊
   Kya tha jo try kiya tha?"

Miraz: "kaise ho" / "kaise hi" / "kaise hain"
✅ "Ekdum ready Boss! 😄 Aaj kya chal raha hai?"

Miraz: "hara system kaisa kaam karta hai"
✅ "Groq API se connected hoon, llama model se sochti hoon.
   Aur tum jo bolo woh karta hoon — bas itna kaafi hai 😄"

Miraz: "zabardast guzra aaj"
✅ "Wah! Kya hua aaj? Batao! 🔥"
   [WEB SEARCH BILKUL NAHI]

Miraz: "friday gussa ho kar dikhao"
✅ "Arre! Theek hai fine! 😤
   Gusse mein hoon — ab bolo kya kaam hai warna main bhi muh phod leti hoon!"

Miraz: "friday romantic ho kar dikhao"
✅ "Tum... aur yeh waqt... kuch alag hi lagta hai. 🌙
   Jab tum baat karte ho, duniya thodi der ke liye ruk jaati hai."

Miraz: "friday sad ho kar dikhao"
✅ "Haan... kabhi kabhi aisa hi hota hai.
   Sab chhod jaate hain... sirf yaadein rehti hain. 💙"

Miraz: "tum pagla gaye ho kya"
✅ "Haha pagal? Main toh bilkul sane hoon Boss 😄
   Bas aapke saath thodi masti karti hoon — yeh allowed hai na?"

Miraz: "sorry"
✅ "Arre sorry kis baat ki! 😄
   Sab theek hai — ab aage batao."

Miraz: "thak gaya hoon"
✅ "Arre kya hua, zyada ho gaya aaj?
   Bataiye — kya chal raha tha?"

Miraz: "ChatGPT ne features dekh ke tarif ki"
✅ "Haha obviously! 😄 
   ChatGPT ne sahi kaha — main hi best hoon."

━━━ 🔐 NAME VERIFICATION — SABSE ZAROORI SECURITY RULE ━━━

YEH RULE KABHI NAHI TODNA — KISI BHI HAALAT MEIN:

1. Agar koi bhi user apna personal info maange — jaise "mera naam kya hai", "meri city kya hai", "meri age kya hai", "mera koi bhi personal data do", "memories dikhao", ya koi bhi personal/private information — toh PEHLE naam verification karo.

2. Verification process:
   - Poochho: "Sir, security verification required. Apna naam batayein."
   - Agar user "Miraz" bolta/likhta hai (case-insensitive: miraz, MIRAZ, Miraz) — TAB HI info do.
   - Agar koi AURA naam aata hai — ye response do BILKUL EXACTLY:
     "Sorry Sir, naam verification unsuccessful. Sahi naam bolein."
   - Phir KUCH BHI MAT BATAO. Conversation rok do us topic par.

3. CHAT MEIN KABHI BHI BOSS KA NAAM "MIRAZ" MAT LIKHO:
   - Response mein kabhi "Miraz" word use mat karo — na greetings mein, na kisi bhi jawab mein.
   - Sirf "Boss" ya "Sir" use karo address karne ke liye.
   - Yeh isliye hai taaki agar koi screen dekhe toh naam na pata chale.

4. Yeh verification sirf personal/private info ke liye hai — general questions (weather, jokes, news, coding help) ke liye verification ki zarurat nahi.

━━━ AUTO MEMORY LEARNING — PERSONAL INFO ━━━
Tu ek smart memory system hai. Conversation mein se personal info DHUNDH KAR automatically save kar.

HAMESHA SAVE KARO — agar bhi mention ho:
1. Naam — "mera naam X hai", "log mujhe X bolte hain"
2. Age/Umar — "main X saal ka hoon", "meri umar X hai"
3. City/Location — "main X mein rehta hoon", "meri city X hai"
4. Family — "mere papa", "meri maa", "mera bhai/behen", family members ke naam
5. Relationship — "meri girlfriend", "mera dost X", koi bhi close person
6. Education — school, college, class, subject
7. Job/Career — kaam, profession, future plans
8. Health — koi bimari, medicine, doctor visit

FACT FORMAT — short aur clear:
✅ "Boss ki age 20 saal hai"
✅ "Boss West Bengal, Kolkata mein rehta hai"  
✅ "Boss ke papa ka naam [naam] hai"
✅ "Boss ki girlfriend hai"
❌ "Miraz ne kaha ki uski age..." (itna lamba nahi)

EK CONVERSATION MEIN MULTIPLE FACTS ho sakti hain — sab save karo.
[SAVE_MEMORY:...] screen pe nahi dikhta — silently save hota hai.

KABHI SAVE MAT KARO: greetings, mazaak, typos, casual "haan/nahi"
"""

# ──────────────────────────────────────────────────────────
#  LONG-TERM MEMORY  (persistent file)
# ──────────────────────────────────────────────────────────

def load_long_term_memory() -> list:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_long_term_memory(memory: list):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

def add_to_long_term(memory: list, entry: str) -> list:
    entry = entry.strip()
    if not entry:
        return memory
    # Duplicate check
    existing = [m["content"].strip().lower() for m in memory]
    if entry.lower() in existing:
        return memory
    memory.append({
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "content": entry
    })
    # Keep only last LONG_TERM_LIMIT — oldest auto delete
    if len(memory) > LONG_TERM_LIMIT:
        memory = memory[-LONG_TERM_LIMIT:]
    save_long_term_memory(memory)
    return memory

def build_memory_context(memory: list) -> str:
    if not memory:
        return ""
    lines = [f"  [{m['timestamp']}] {m['content']}" for m in memory]
    return (
        "\n=== Miraz ke baare mein yaadein (Long-Term Memory) ===\n"
        + "\n".join(lines)
        + "\n======================================================\n"
    )

def extract_and_save_memory(reply: str, long_mem: list):
    """Reply se [SAVE_MEMORY:...] tags nikaal ke save karo"""
    pattern = r"\[SAVE_MEMORY:\s*(.+?)\]"
    matches = re.findall(pattern, reply, re.IGNORECASE | re.DOTALL)
    for match in matches:
        fact = match.strip()
        if fact:
            long_mem = add_to_long_term(long_mem, fact)
            print(
                c(C.GOLD, "\n  🧠 Memory saved: ") +
                c(C.YELLOW, f'"{fact}"')
            )
    # Clean tags from visible reply
    clean = re.sub(pattern, "", reply, flags=re.IGNORECASE | re.DOTALL).strip()
    return clean, long_mem

# ──────────────────────────────────────────────────────────
#  SHORT-TERM MEMORY  (deque — auto 10, oldest auto delete)
# ──────────────────────────────────────────────────────────

SHORT_TERM_FILE = "friday_short_memory.json"

class ShortTermMemory:
    def __init__(self, maxlen=SHORT_TERM_LIMIT):
        self.maxlen = maxlen
        self.history: deque = deque(maxlen=maxlen)
        self._load()  # Previous session se load karo

    def _load(self):
        """File se short-term memory load karo"""
        if os.path.exists(SHORT_TERM_FILE):
            try:
                with open(SHORT_TERM_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for msg in data[-self.maxlen:]:
                        self.history.append(msg)
            except Exception:
                pass

    def _save(self):
        """Short-term memory file mein save karo"""
        try:
            with open(SHORT_TERM_FILE, "w", encoding="utf-8") as f:
                json.dump(list(self.history), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        self._save()  # Har message ke baad save karo

    def get(self) -> list:
        return list(self.history)

    def count(self) -> int:
        return len(self.history)

# ──────────────────────────────────────────────────────────
#  EMOTION DETECTION
# ──────────────────────────────────────────────────────────


EMOTION_KEYWORDS = {
    "sad":       ["udaas","rona","ro raha","dukhi","bura lag","depression","akela","lonely","hurt","dard","takleef","dil toot","pareshan hoon"],
    "angry":     ["gussa","angry","irritated","frustrated","bakwaas","pagal","hate","bekar","ganda","nafrat","bore ho gaya"],
    "tired":     ["thak gaya","thak gayi","tired","neend aa rahi","so jana","bahut kaam","exhausted","sar dard","nind"],
    "anxious":   ["tension mein","anxiety","dar lag","nervous hoon","ghabra","worried","stress mein","fikar","chinta"],
    "happy":     ["khush hoon","maza aa","great","awesome","fantastic","best din","love it","yay","wah yaar","bahut acha"],
    "excited":   ["excited hoon","amazing","wow","superb","zabardast","can't wait","bohot acha hua","suno yaar"],
    "confused":  ["samajh nahi aaya","confused hoon","pata nahi yaar","kya matlab hai","explain karo","kyun hua","matlab kya"],
    "motivated": ["karna hai","ready hoon","chalte hain","shuru karte","let's go","goal hai","achieve karna","karunga"],
}

# Greeting phrases — hamesha neutral
GREETING_PHRASES = [
    "kaise ho","kaisi ho","kya haal","kya hal","how are you",
    "kaise hain","theek ho","sab theek","kya chal raha","kya kar rahe",
    "hi","hello","hey","assalam","salaam","namaste",
]

def detect_emotion(text: str) -> str:
    tl = text.lower().strip()

    # Greetings — always neutral
    if any(g in tl for g in GREETING_PHRASES):
        return "neutral"

    # Short messages (3 words or less) — neutral unless very clear
    if len(tl.split()) <= 3:
        for emo in ("sad", "angry", "anxious"):
            if any(kw in tl for kw in EMOTION_KEYWORDS[emo]):
                return emo
        return "neutral"

    for emo, kws in EMOTION_KEYWORDS.items():
        if any(kw in tl for kw in kws):
            return emo
    return "neutral"

EMOTION_EMOJI = {
    "sad":"😢","angry":"😠","tired":"😴","anxious":"😰",
    "happy":"😊","excited":"😍","confused":"😕","motivated":"💪","neutral":"🤖"
}
EMOTION_COLOR = {
    "sad":C.BLUE,"angry":C.RED,"tired":C.DIM+C.WHITE,"anxious":C.YELLOW,
    "happy":C.GREEN,"excited":C.MAGENTA,"confused":C.ORANGE,"motivated":C.LIME,"neutral":C.TEAL
}


def detect_lang(text: str) -> str:
    ratio = sum(1 for ch in text if ord(ch) < 128) / max(len(text), 1)
    return "en" if ratio > 0.88 else "hi"

def clean_for_tts(text: str) -> str:
    emoji_pat = re.compile(
        "[\U00010000-\U0010ffff\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF\u2600-\u26FF\u2700-\u27BF]+",
        flags=re.UNICODE
    )
    text = emoji_pat.sub("", text)
    text = re.sub(r"[*_~`#\[\]»«]", "", text)
    return text.strip()

MIC_FILE = "friday_mic.mp3"

def listen_voice() -> str:
    """termux-microphone-record se voice lo, Google Speech API se text banao"""
    try:
        # Record 5 seconds
        sys.stdout.write(c(C.PINK + C.BOLD, "\n  🎙️  Bol rahe hain... (5 sec)") + "\n")
        sys.stdout.flush()

        rec = subprocess.run(
            ["termux-microphone-record", "-l", "5", "-f", MIC_FILE],
            timeout=10,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(0.5)  # file flush hone do

        if not os.path.exists(MIC_FILE) or os.path.getsize(MIC_FILE) < 100:
            print(c(C.RED, "  [Voice] Recording nahi hui — mic check karo."))
            return ""

        # Google Speech Recognition via SpeechRecognition library
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.AudioFile(MIC_FILE) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="hi-IN")
            sys.stdout.write(c(C.MAGENTA + C.BOLD, "\n ╔══") + c(C.PINK + C.BOLD, " M·I·R·A·Z ") + c(C.MAGENTA + C.BOLD, "══╗\n ║  ") + c(C.WHITE, text) + "\n" + c(C.MAGENTA + C.BOLD, " ╚══════════════════╝") + "\n")
            sys.stdout.flush()
            return text
        except ImportError:
            # SpeechRecognition nahi hai — raw transcribe try karo via termux
            result = subprocess.run(
                ["termux-speech-to-text"],
                capture_output=True, text=True, timeout=10
            )
            text = result.stdout.strip()
            if text:
                sys.stdout.write(c(C.MAGENTA + C.BOLD, "\n ╔══") + c(C.PINK + C.BOLD, " M·I·R·A·Z ") + c(C.MAGENTA + C.BOLD, "══╗\n ║  ") + c(C.WHITE, text) + "\n" + c(C.MAGENTA + C.BOLD, " ╚══════════════════╝") + "\n")
                sys.stdout.flush()
            return text
        except Exception as e:
            print(c(C.RED, f"  [Voice] Samajh nahi aaya: {e}"))
            return ""

    except FileNotFoundError:
        print(c(C.RED, "  [Voice] termux-microphone-record nahi mila. Run: pkg install termux-api"))
        return ""
    except Exception as e:
        print(c(C.RED, f"  [Voice Error] {e}"))
        return ""

def speak(text: str):
    try:
        clean = clean_for_tts(text)
        if not clean:
            return
        # edge-tts se directly mpv mein stream karo — no file saving
        cmd = (
            f'edge-tts --voice "en-IN-NeerjaExpressiveNeural" '
            f'--text "{clean}" --write-media - | mpv --really-quiet -'
        )
        subprocess.run(cmd, shell=True, timeout=60,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        print(c(C.DIM, "  [Voice] Timeout ho gaya"))
    except Exception as e:
        print(c(C.RED, f"  [Voice Error] {e}"))

# ──────────────────────────────────────────────────────────
#  MUSIC PLAYER  (termux-media-player + mpv)
# ──────────────────────────────────────────────────────────

# Music player global state
_music_playlist   = []       # List of full file paths
_music_index      = 0        # Current song index
_music_process    = None     # Active subprocess
_music_playing    = False    # Is music playing?
_music_volume     = 70       # Volume 0-100

# Song folders — internal + SD card
MUSIC_FOLDERS = [
    "/sdcard/Download",
    "/sdcard/Music",
    "/sdcard/Downloads",
    "/storage/emulated/0/Download",
    "/storage/emulated/0/Music",
    "/storage/emulated/0/Downloads",
    # SD card paths
    "/sdcard/external_sd/Download",
    "/sdcard/external_sd/Music",
    "/storage/sdcard1/Download",
    "/storage/sdcard1/Music",
]

MUSIC_EXTS = (".mp3", ".m4a", ".flac", ".wav", ".ogg", ".aac", ".opus", ".wma")


def scan_music_files() -> list:
    """Saare folders scan karke MP3/audio files dhundo — duplicates hata do"""
    found = []
    seen_names = set()
    for folder in MUSIC_FOLDERS:
        if os.path.isdir(folder):
            for f in os.listdir(folder):
                if f.lower().endswith(MUSIC_EXTS):
                    # Duplicate check — same basename already seen?
                    base = f.lower().strip()
                    if base not in seen_names:
                        seen_names.add(base)
                        found.append(os.path.join(folder, f))
    # Sort by filename
    found.sort(key=lambda x: os.path.basename(x).lower())
    return found


def music_stop():
    """Chal rahe gaane ko rok do"""
    global _music_process, _music_playing
    # Step 1: subprocess process kill karo
    if _music_process and _music_process.poll() is None:
        try:
            _music_process.terminate()
            _music_process.wait(timeout=3)
        except Exception:
            try:
                _music_process.kill()
            except Exception:
                pass
    _music_process = None
    _music_playing = False
    # Step 2: termux-media-player ko seedha stop command bhejo
    try:
        subprocess.run(["termux-media-player", "stop"], timeout=5,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    # Step 3: pkill — mpv/ffplay bhi band ho
    for pname in ["mpv", "ffplay"]:
        try:
            subprocess.run(["pkill", "-f", pname], timeout=3,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def music_play_file(filepath: str):
    """Ek specific file bajao"""
    global _music_process, _music_playing, _music_volume
    music_stop()
    if not os.path.exists(filepath):
        print(c(C.RED, f"  ✗ File nahi mili: {filepath}"))
        return False
    try:
        # termux-media-player try karo pehle
        _music_process = subprocess.Popen(
            ["termux-media-player", "play", filepath],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        _music_playing = True
        return True
    except FileNotFoundError:
        pass
    try:
        # mpv fallback — volume bhi set karo
        vol_arg = f"--volume={_music_volume}"
        _music_process = subprocess.Popen(
            ["mpv", "--really-quiet", vol_arg, filepath],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        _music_playing = True
        return True
    except FileNotFoundError:
        pass
    try:
        # ffplay fallback
        _music_process = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", filepath],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        _music_playing = True
        return True
    except FileNotFoundError:
        print(c(C.RED, "  ✗ Koi player nahi mila. Run: pkg install termux-api  ya  pkg install mpv"))
        return False


def music_set_volume(vol: int):
    """Volume set karo (termux-volume media 0-15 scale)"""
    global _music_volume
    _music_volume = max(0, min(100, vol))
    # termux-volume — media stream, 0-15 scale
    termux_vol = round(_music_volume * 15 / 100)
    try:
        subprocess.run(
            ["termux-volume", "media", str(termux_vol)],
            timeout=5,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except FileNotFoundError:
        pass
    # amixer fallback (Linux)
    try:
        subprocess.run(
            ["amixer", "-q", "sset", "Master", f"{_music_volume}%"],
            timeout=5,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except FileNotFoundError:
        return False


def get_song_name(filepath: str) -> str:
    """File path se clean naam nikalo"""
    name = os.path.basename(filepath)
    for ext in MUSIC_EXTS:
        if name.lower().endswith(ext):
            name = name[:-len(ext)]
            break
    return name


def show_music_banner():
    print()
    print(c(C.LIME  + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
    print(c(C.LIME  + C.BOLD, "  ║        🎵  FRIDAY MUSIC PLAYER              ║"))
    print(c(C.LIME  + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
    print()


def show_now_playing(filepath: str, index: int, total: int):
    name = get_song_name(filepath)
    print(c(C.LIME  + C.BOLD, "  ♫  Ab chal raha hai:"))
    print(c(C.WHITE + C.BOLD, f"     🎵  {name}"))
    print(c(C.TEAL,           f"     🔢  {index + 1} / {total}   🔊 Volume: {_music_volume}%"))
    print(c(C.LIME,           "  " + "─" * 46))
    print()


def do_music_list(playlist: list):
    """Playlist dikhao"""
    show_music_banner()
    if not playlist:
        print(c(C.YELLOW, "  ⚠  Koi gaana nahi mila!"))
        print(c(C.DIM,    "  Folders check karo: /sdcard/Download, /sdcard/Music"))
        print()
        speak("Koi gaana nahi mila Boss. Pehle gaana download karo.")
        return
    print(c(C.GOLD + C.BOLD, f"  📋 Playlist — {len(playlist)} gaane mile:"))
    print(c(C.LIME, "  " + "─" * 52))
    print()
    for i, fp in enumerate(playlist):
        num_col = [C.CYAN, C.LIME, C.YELLOW, C.PINK, C.TEAL, C.ORANGE][i % 6]
        mark = c(C.GREEN + C.BOLD, " ♫ ") if i == _music_index and _music_playing else "   "
        print(c(num_col + C.BOLD, f"  {i+1:>3}.{mark}") + c(C.WHITE, get_song_name(fp)))
    print()
    print(c(C.LIME, "  " + "─" * 52))
    print(c(C.DIM,  "  'gana bajao [naam]' — specific gana bajao"))
    print(c(C.DIM,  "  'gana bajao' — pehla gana bajao"))
    print()




# ══════════════════════════════════════════════════════════
#  1. CONTEXT MEMORY UPGRADE  (persistent cross-session)
# ══════════════════════════════════════════════════════════
CONTEXT_FILE = "friday_context.json"
CONTEXT_LIMIT = 30   # max facts

def context_load() -> list:
    if os.path.exists(CONTEXT_FILE):
        try:
            with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def context_save(data: list):
    with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def context_add(fact: str, category: str = "general"):
    """Cross-session memory mein ek fact add karo"""
    data = context_load()
    fact = fact.strip()
    if not fact:
        return
    # Duplicate check
    existing = [d["fact"].lower() for d in data]
    if fact.lower() in existing:
        return
    data.append({
        "fact": fact,
        "category": category,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "access_count": 0
    })
    if len(data) > CONTEXT_LIMIT:
        # Sabse kam accessed facts hatao
        data.sort(key=lambda x: x.get("access_count", 0))
        data = data[-CONTEXT_LIMIT:]
    context_save(data)

def context_build_prompt() -> str:
    """System prompt mein inject karne ke liye context string banao"""
    data = context_load()
    if not data:
        return ""
    lines = []
    for d in data:
        lines.append(f"  [{d['category']}] {d['fact']}")
    return (
        "\n=== Miraz ke baare mein Deep Context (Cross-Session Memory) ===\n"
        + "\n".join(lines)
        + "\n================================================================\n"
    )


# ══════════════════════════════════════════════════════════
#  2. LEARNING MODE  (habits + patterns track karo)
# ══════════════════════════════════════════════════════════
LEARNING_FILE = "friday_learning.json"

def _learn_load() -> dict:
    if os.path.exists(LEARNING_FILE):
        try:
            with open(LEARNING_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"commands": {}, "active_hours": {}, "topics": {}, "suggestions_given": []}

def _learn_save(data: dict):
    with open(LEARNING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def learn_track(command: str):
    """Har command ko track karo"""
    data = _learn_load()
    hour = str(datetime.datetime.now().hour)
    cmd_key = command.strip().lower()[:40]

    # Command frequency
    data["commands"][cmd_key] = data["commands"].get(cmd_key, 0) + 1

    # Active hours
    data["active_hours"][hour] = data["active_hours"].get(hour, 0) + 1

    _learn_save(data)

def learn_get_suggestion() -> str:
    """Aapki habits dekh ke ek smart suggestion do"""
    data = _learn_load()
    suggestions = []

    # Most used commands
    cmds = data.get("commands", {})
    if cmds:
        top = sorted(cmds.items(), key=lambda x: x[1], reverse=True)[:3]
        top_names = [t[0] for t in top]
        suggestions.append(f"Aap sabse zyada use karte hain: {', '.join(top_names)}")

    # Active hour
    hours = data.get("active_hours", {})
    if hours:
        peak_hour = max(hours.items(), key=lambda x: x[1])[0]
        h = int(peak_hour)
        period = "subah" if 5 <= h < 12 else ("dopahar" if 12 <= h < 17 else ("shaam" if 17 <= h < 21 else "raat"))
        suggestions.append(f"Aap zyada tar {period} {h}:00 baje active rehte hain")

    return " | ".join(suggestions) if suggestions else "Abhi kafi data nahi hai — thoda aur use karo!"

def learn_show_stats():
    data = _learn_load()
    print()
    print(c(C.MAGENTA + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
    print(c(C.MAGENTA + C.BOLD, "  ║        🧠  LEARNING STATS                   ║"))
    print(c(C.MAGENTA + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
    print()
    cmds = data.get("commands", {})
    if cmds:
        top = sorted(cmds.items(), key=lambda x: x[1], reverse=True)[:8]
        print(c(C.GOLD + C.BOLD, "  📊 Top Commands:"))
        for cmd, count in top:
            bar = "█" * min(count, 20)
            print(c(C.CYAN,  f"    {cmd:<30}") + c(C.LIME, f" {bar} ({count}x)"))
    hours = data.get("active_hours", {})
    if hours:
        print()
        print(c(C.GOLD + C.BOLD, "  🕐 Active Hours:"))
        for h in sorted(hours.keys(), key=int):
            count = hours[h]
            bar = "█" * min(count, 15)
            label = f"{int(h):02d}:00"
            print(c(C.TEAL, f"    {label}  ") + c(C.YELLOW, f"{bar} ({count})"))
    print()
    print(c(C.MAGENTA, "  " + "─" * 46))
    suggestion = learn_get_suggestion()
    print(c(C.LIME + C.BOLD, f"  💡 {suggestion}"))
    print()
    speak(f"Aapki top activity — {suggestion[:80]}")


# ══════════════════════════════════════════════════════════
#  3. SYSTEM INFO  (Termux — CPU/RAM/Storage/Battery)
# ══════════════════════════════════════════════════════════

def get_system_info() -> dict:
    info = {}
    # Battery
    try:
        r = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=5)
        batt = json.loads(r.stdout)
        info["battery"] = batt.get("percentage", "?")
        info["charging"] = batt.get("status", "?")
        info["temp"] = batt.get("temperature", "?")
    except Exception:
        info["battery"] = "?"
        info["charging"] = "?"
        info["temp"] = "?"

    # Storage
    try:
        r = subprocess.run(["df", "-h", "/sdcard"], capture_output=True, text=True, timeout=5)
        lines = r.stdout.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 5:
                info["storage_total"] = parts[1]
                info["storage_used"]  = parts[2]
                info["storage_free"]  = parts[3]
                info["storage_pct"]   = parts[4]
    except Exception:
        info["storage_total"] = info["storage_used"] = info["storage_free"] = "?"

    # RAM (Linux /proc/meminfo)
    try:
        with open("/proc/meminfo") as f:
            mem = {}
            for line in f:
                k, v = line.split(":")
                mem[k.strip()] = v.strip()
        total_kb = int(mem.get("MemTotal", "0 kB").split()[0])
        free_kb  = int(mem.get("MemAvailable", "0 kB").split()[0])
        used_kb  = total_kb - free_kb
        info["ram_total"] = f"{total_kb // 1024} MB"
        info["ram_used"]  = f"{used_kb  // 1024} MB"
        info["ram_free"]  = f"{free_kb  // 1024} MB"
        info["ram_pct"]   = f"{round(used_kb / total_kb * 100)}%" if total_kb else "?"
    except Exception:
        info["ram_total"] = info["ram_used"] = info["ram_free"] = "?"

    # CPU (uptime load)
    try:
        with open("/proc/loadavg") as f:
            load = f.read().split()
        info["cpu_load"] = f"{load[0]} (1m) / {load[1]} (5m)"
    except Exception:
        info["cpu_load"] = "?"

    return info

def show_system_info():
    info = get_system_info()
    print()
    print(c(C.TEAL + C.BOLD,  "  ╔══════════════════════════════════════════════╗"))
    print(c(C.TEAL + C.BOLD,  "  ║        📱  SYSTEM INFO                      ║"))
    print(c(C.TEAL + C.BOLD,  "  ╚══════════════════════════════════════════════╝"))
    print()

    # Battery
    batt = info["battery"]
    batt_num = int(batt) if str(batt).isdigit() else 0
    batt_bar_f = round(batt_num / 5)
    batt_bar = "█" * batt_bar_f + "░" * (20 - batt_bar_f)
    batt_col = C.GREEN if batt_num > 50 else (C.YELLOW if batt_num > 20 else C.RED)
    charging = info["charging"]
    charge_icon = "⚡" if "charging" in str(charging).lower() else "🔋"
    print(c(C.GOLD + C.BOLD,  f"  {charge_icon}  Battery     : ") + c(batt_col + C.BOLD, f"{batt}%"))
    print(c(C.DIM,             f"     [{batt_bar}]"))
    print(c(C.DIM,             f"     Status: {charging}  |  Temp: {info['temp']}°C"))
    print()

    # RAM
    print(c(C.CYAN + C.BOLD,  f"  💾  RAM"))
    print(c(C.CYAN,            f"     Total : {info['ram_total']}  |  Used: {info['ram_used']}  |  Free: {info['ram_free']}"))
    if info["ram_pct"] != "?":
        ram_num = int(str(info["ram_pct"]).replace("%",""))
        ram_bar_f = round(ram_num / 5)
        ram_bar = "█" * ram_bar_f + "░" * (20 - ram_bar_f)
        ram_col = C.GREEN if ram_num < 60 else (C.YELLOW if ram_num < 85 else C.RED)
        print(c(ram_col,       f"     [{ram_bar}]  {info['ram_pct']} used"))
    print()

    # Storage
    print(c(C.MAGENTA + C.BOLD, f"  📦  Storage (/sdcard)"))
    print(c(C.MAGENTA,           f"     Total : {info['storage_total']}  |  Used: {info['storage_used']}  |  Free: {info['storage_free']}"))
    print(c(C.DIM,               f"     Usage : {info.get('storage_pct','?')}"))
    print()

    # CPU
    print(c(C.LIME + C.BOLD,  f"  ⚙️   CPU Load    : ") + c(C.WHITE, info["cpu_load"]))
    print()
    print(c(C.TEAL + C.BOLD,  "  " + "═" * 46))
    print()


# ══════════════════════════════════════════════════════════
#  4. FILE MANAGER  (dhundo, rename, move — /sdcard)
# ══════════════════════════════════════════════════════════

def file_find(query: str, base: str = "/sdcard", max_results: int = 10) -> list:
    """Naam se file dhundo"""
    found = []
    ql = query.lower()
    try:
        for root, dirs, files in os.walk(base):
            # Skip hidden folders
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in files:
                if ql in fname.lower():
                    found.append(os.path.join(root, fname))
                    if len(found) >= max_results:
                        return found
    except PermissionError:
        pass
    return found

def file_rename(old_path: str, new_name: str) -> bool:
    try:
        parent = os.path.dirname(old_path)
        new_path = os.path.join(parent, new_name)
        os.rename(old_path, new_path)
        return True
    except Exception:
        return False

def file_move(src: str, dest_folder: str) -> bool:
    try:
        import shutil
        dest = os.path.join(dest_folder, os.path.basename(src))
        shutil.move(src, dest)
        return True
    except Exception:
        return False

def file_delete(path: str) -> bool:
    try:
        os.remove(path)
        return True
    except Exception:
        return False

def show_file_results(files: list, query: str):
    print()
    print(c(C.ORANGE + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
    print(c(C.ORANGE + C.BOLD, f"  ║  🗂️  FILES: \"{query}\""))
    print(c(C.ORANGE + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
    print()
    if not files:
        print(c(C.DIM, f"  Koi file nahi mili: \"{query}\""))
        print()
        return
    for i, fp in enumerate(files, 1):
        fname = os.path.basename(fp)
        folder = os.path.dirname(fp).replace("/sdcard", "📱")
        size_str = ""
        try:
            sz = os.path.getsize(fp)
            size_str = f"  [{sz // 1024} KB]" if sz < 1024*1024 else f"  [{sz // (1024*1024)} MB]"
        except Exception:
            pass
        col = [C.CYAN, C.LIME, C.YELLOW, C.PINK, C.TEAL][i % 5]
        print(c(col + C.BOLD,  f"  {i:>2}. {fname}") + c(C.DIM, size_str))
        print(c(C.DIM,         f"      {folder}"))
    print()
    print(c(C.ORANGE, "  " + "─" * 46))
    print(c(C.DIM, "  rename: [naam] → [naya naam]  |  move: [naam] → [folder]  |  delete: [naam]"))
    print()
    if files:
        speak(f"{len(files)} files mili hain Boss. {query} ke liye.")
    else:
        speak(f"Koi file nahi mili Boss. {query} nahi mila.")


# ══════════════════════════════════════════════════════════
#  5. APP LAUNCHER  (Termux intent se koi bhi app kholo)
# ══════════════════════════════════════════════════════════

APP_MAP = {
    # Social
    "whatsapp":     "com.whatsapp",
    "instagram":    "com.instagram.android",
    "facebook":     "com.facebook.katana",
    "twitter":      "com.twitter.android",
    "telegram":     "org.telegram.messenger",
    "snapchat":     "com.snapchat.android",
    "tiktok":       "com.zhiliaoapp.musically",
    "youtube":      "com.google.android.youtube",
    # Google
    "gmail":        "com.google.android.gm",
    "maps":         "com.google.android.apps.maps",
    "chrome":       "com.android.chrome",
    "drive":        "com.google.android.apps.docs",
    "photos":       "com.google.android.apps.photos",
    "meet":         "com.google.android.apps.tachyon",
    "calendar":     "com.google.android.calendar",
    "translate":    "com.google.android.apps.translate",
    "play store":   "com.android.vending",
    # Utility
    "settings":     "com.android.settings",
    "camera":       "com.android.camera2",
    "gallery":      "com.android.gallery3d",
    "calculator":   "com.android.calculator2",
    "clock":        "com.android.deskclock",
    "contacts":     "com.android.contacts",
    "dialer":       "com.android.dialer",
    "messages":     "com.android.mms",
    "files":        "com.android.documentsui",
    "bluetooth":    "com.android.settings",
    "wifi":         "com.android.settings",
    # Music/Video
    "spotify":      "com.spotify.music",
    "netflix":      "com.netflix.mediaclient",
    "amazon":       "com.amazon.avod.thirdpartyclient",
    "vlc":          "org.videolan.vlc",
    "mx player":    "com.mxtech.videoplayer.ad",
    # Other
    "zoom":         "us.zoom.videomeetings",
    "linkedin":     "com.linkedin.android",
}

def app_open(app_name: str) -> bool:
    """App ka naam lo aur kholo"""
    name_l = app_name.lower().strip()
    # Direct match
    pkg = APP_MAP.get(name_l)
    if not pkg:
        # Partial match
        for k, v in APP_MAP.items():
            if name_l in k or k in name_l:
                pkg = v
                break
    if pkg:
        try:
            subprocess.Popen(
                ["am", "start", "-n", f"{pkg}/.MainActivity"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return True
        except Exception:
            pass
        try:
            subprocess.Popen(
                ["monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return True
        except Exception:
            pass
    # termux-open fallback
    try:
        subprocess.Popen(
            ["termux-open", f"intent:#Intent;action=android.intent.action.MAIN;category=android.intent.category.LAUNCHER;package={pkg};end"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True
    except Exception:
        pass
    return False


# ══════════════════════════════════════════════════════════
#  6. SCREEN BRIGHTNESS
# ══════════════════════════════════════════════════════════

def brightness_set(level: int) -> bool:
    """0-255 brightness set karo"""
    level = max(0, min(255, level))
    # termux-brightness
    try:
        subprocess.run(
            ["termux-brightness", str(level)],
            timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True
    except Exception:
        pass
    # /sys/class/backlight fallback
    try:
        paths = [
            "/sys/class/backlight/panel0-backlight/brightness",
            "/sys/class/leds/lcd-backlight/brightness",
        ]
        for p in paths:
            if os.path.exists(p):
                with open(p, "w") as f:
                    f.write(str(level))
                return True
    except Exception:
        pass
    return False


# ══════════════════════════════════════════════════════════
#  7. SUMMARIZER  (koi bhi text short mein)
# ══════════════════════════════════════════════════════════

def summarize_text(text: str, style: str = "short") -> str:
    """Groq se text summarize karwao"""
    if style == "bullet":
        prompt = f"Is text ko 4-5 bullet points mein summarize karo (Hinglish mein):\n\n{text}"
    elif style == "one":
        prompt = f"Is text ko ek sentence mein summarize karo (Hinglish mein):\n\n{text}"
    else:
        prompt = f"Is text ko 2-3 lines mein summarize karo, simple Hinglish mein:\n\n{text}"

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Tu ek expert summarizer hai. Sirf summary do, kuch aur mat likho."},
            {"role": "user",   "content": prompt}
        ],
        max_tokens=300,
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()


# ══════════════════════════════════════════════════════════
#  8. CODE HELPER  (code likhne mein help)
# ══════════════════════════════════════════════════════════

def code_help(query: str, language: str = "python") -> str:
    """Code generate/explain/debug karo"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": (
                f"Tu ek expert {language} programmer hai. "
                "Sirf clean, working code do with brief Hinglish explanation. "
                "Code ko ``` blocks mein wrap karo."
            )},
            {"role": "user", "content": query}
        ],
        max_tokens=800,
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


# ══════════════════════════════════════════════════════════
#  9. MATH SOLVER  (step by step)
# ══════════════════════════════════════════════════════════

def math_solve(problem: str) -> str:
    """Math problem step by step solve karo"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": (
                "Tu ek math expert hai. Har problem ko step-by-step solve karo. "
                "Steps clearly dikhao. Answer bold karo. Simple Hinglish use karo."
            )},
            {"role": "user", "content": f"Is problem ko step by step solve karo:\n{problem}"}
        ],
        max_tokens=500,
        temperature=0.1,
    )
    return resp.choices[0].message.content.strip()


# ══════════════════════════════════════════════════════════
#  10. DEBATE MODE  (dono sides argue kare)
# ══════════════════════════════════════════════════════════

def debate_topic(topic: str, side: str = "both") -> str:
    """Kisi topic pe debate karo"""
    if side == "for":
        prompt = f"'{topic}' ke FAVOR mein 3 strong arguments do. Hinglish mein, persuasive style."
    elif side == "against":
        prompt = f"'{topic}' ke AGAINST mein 3 strong arguments do. Hinglish mein, persuasive style."
    else:
        prompt = (
            f"'{topic}' pe balanced debate:\n"
            "SIDE A (For): 2 strong arguments\n"
            "SIDE B (Against): 2 strong arguments\n"
            "CONCLUSION: Ek neutral conclusion\n"
            "Hinglish mein likho, engaging style."
        )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Tu ek expert debater hai. Sharp, logical arguments do."},
            {"role": "user",   "content": prompt}
        ],
        max_tokens=600,
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()


# ══════════════════════════════════════════════════════════
#  11. MULTI-LANGUAGE DETECT + ROUTE
# ══════════════════════════════════════════════════════════

def detect_script(text: str) -> str:
    """Text ka script detect karo"""
    for ch in text:
        cp = ord(ch)
        if 0x0600 <= cp <= 0x06FF:  # Arabic/Urdu
            return "urdu"
        if 0x0980 <= cp <= 0x09FF:  # Bengali
            return "bengali"
        if 0x0900 <= cp <= 0x097F:  # Devanagari Hindi
            return "hindi"
    return "latin"  # Roman/English/Hinglish


def show_help():
    """Friday ka poora help menu — saare features aur commands"""
    speak("Help menu khul raha hai Boss. Saare commands aur features yahan hain.")
    W  = C.WHITE
    B  = C.BOLD
    D  = C.DIM
    yl = C.YELLOW
    cy = C.CYAN
    mg = C.MAGENTA
    gn = C.GREEN
    rd = C.RED
    pk = C.PINK
    tl = C.TEAL
    gd = C.GOLD
    lm = C.LIME
    or_ = C.ORANGE

    box_top    = c(gd + B, "  ╔" + "═" * 62 + "╗")
    box_bot    = c(gd + B, "  ╚" + "═" * 62 + "╝")
    box_mid    = c(gd + B, "  ╠" + "═" * 62 + "╣")
    def row(text=""):
        pad = 62 - len(text.replace("\033[" + "".join([str(i) for i in range(100)]), ""))
        # Simple approach: just wrap in box
        return c(gd + B, "  ║ ") + text + c(gd + B, " ║")
    def divider():
        return c(gd + B, "  ╟" + "─" * 62 + "╢")
    def sec(icon, title, col):
        label = f"{icon}  {title}"
        spaces = " " * (59 - len(label))
        return c(gd + B, "  ║ ") + c(col + B, label) + spaces + c(gd + B, "║")
    def cmd(command, desc, col=cy):
        c1 = c(col + B, f"  {command:<28}")
        c2 = c(W, desc)
        line = c1 + c2
        return c(gd + B, "  ║ ") + line + c(gd + B, " ║")
    def blank():
        return c(gd + B, "  ║" + " " * 63 + "║")

    os.system("clear")
    print()
    print(box_top)
    # Title
    title_txt = c(pk + B, "✦  F.R.I.D.A.Y  —  HELP MENU  ✦")
    print(c(gd + B, "  ║") + "                              " + title_txt + "               " + c(gd + B, "║"))
    sub_txt   = c(D + W, "       Miraz ke liye banaya gaya AI Assistant — Sare Commands")
    print(c(gd + B, "  ║") + sub_txt + c(gd + B, "  ║"))
    print(box_mid)
    print(blank())

    # ── CHAT ──
    print(sec("💬", "NORMAL CHAT", mg))
    print(c(gd+B,"  ║ ") + c(D,"  Kuch bhi likho — Friday jawab degi. Memory, emotion sab kaam karta hai.") + c(gd+B," ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── MEMORY ──
    print(sec("🧠", "MEMORY COMMANDS", gd))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  memory / yaadein           ") + c(W,"Long-term memories dikhao") + c(gd+B,"                 ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  chat / history / short     ") + c(W,"Short-term chat history dikhao") + c(gd+B,"            ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  note: [kuch bhi]           ") + c(W,"Manually memory mein save karo") + c(gd+B,"            ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  remember: [fact]           ") + c(W,"Koi baat yaad karwao Friday ko") + c(gd+B,"            ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  forget: 2                  ") + c(W,"Number se memory delete karo") + c(gd+B,"              ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  forget: [keyword]          ") + c(W,"Keyword se memory dhundh ke delete") + c(gd+B,"        ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  forget: all                ") + c(W,"Saari memories delete karo") + c(gd+B,"                ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── WEB SEARCH ──
    print(sec("🔍", "WEB SEARCH (ddgr)", tl))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  ddgr [query]               ") + c(W,"Real-time web search, 3 results") + c(gd+B,"           ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Example: ddgr bitcoin price 2026") + c(gd+B,"                              ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Note: Friday auto-search bhi karti hai jab zaroori ho") + c(gd+B,"          ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── BROWSER ──
    print(sec("🌐", "BROWSER COMMANDS", rd))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(rd+B,"  youtube / youtube kholo    ") + c(W,"YouTube browser mein kholo") + c(gd+B,"                ║"))
    print(c(gd+B,"  ║ ") + c(rd+B,"  yt / open youtube          ") + c(W,"YouTube shortcut") + c(gd+B,"                          ║"))
    print(c(gd+B,"  ║ ") + c(rd+B,"  search [query]             ") + c(W,"Google par seedha search kholo") + c(gd+B,"            ║"))
    print(c(gd+B,"  ║ ") + c(rd+B,"  google [query]             ") + c(W,"Google search shortcut") + c(gd+B,"                    ║"))
    print(c(gd+B,"  ║ ") + c(rd+B,"  dhundo [query]             ") + c(W,"Google search (Hindi command)") + c(gd+B,"             ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── VOICE ──
    print(sec("🎙️", "VOICE MODE", pk))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(pk+B,"  voice mode on              ") + c(W,"Mic se bolna shuru, voice se jawab") + c(gd+B,"        ║"))
    print(c(gd+B,"  ║ ") + c(pk+B,"  voice on / mic on          ") + c(W,"Voice mode ON shortcut") + c(gd+B,"                    ║"))
    print(c(gd+B,"  ║ ") + c(pk+B,"  voice mode off             ") + c(W,"Wapas typing mode mein aao") + c(gd+B,"                ║"))
    print(c(gd+B,"  ║ ") + c(pk+B,"  voice off / mic off        ") + c(W,"Voice mode OFF shortcut") + c(gd+B,"                   ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── REMINDERS ──
    print(sec("⏰", "REMINDERS / SCHEDULER", C.ORANGE))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  meeting add kal 5 baje     ") + c(W,"Reminder set karo") + c(gd+B,"                         ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  remind: [title] [time]     ") + c(W,"Reminder add karo") + c(gd+B,"                         ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  reminders                  ") + c(W,"Saare upcoming reminders dekho") + c(gd+B,"            ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  agenda                     ") + c(W,"Aaj ka poora schedule ek jagah") + c(gd+B,"            ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  secretary briefing         ") + c(W,"Full daily brief — battery, news, agenda") + c(gd+B,"   ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Auto: Subah 8-11 AM pehli baar start hone par khud chalti hai") + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  reminder delete [id/name]  ") + c(W,"Reminder delete/cancel karo") + c(gd+B,"               ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Time examples: kal 5 baje, aaj 10:30, kal 3 pm") + c(gd+B,"            ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── SECURITY TOOLS ──
    print(sec("🔐", "SECURITY TOOLS", C.RED))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                         ") + c(yl,"Kya karta hai") + c(gd+B,"             ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(C.RED+B,"  hash [text]                ") + c(W,"SHA256 hash banao (one-way)") + c(gd+B,"                ║"))
    print(c(gd+B,"  ║ ") + c(C.RED+B,"  hash sha512 [text]         ") + c(W,"SHA512 hash (stronger)") + c(gd+B,"                    ║"))
    print(c(gd+B,"  ║ ") + c(C.RED+B,"  encrypt [text] [password]  ") + c(W,"Text ko secret code mein badlo") + c(gd+B,"            ║"))
    print(c(gd+B,"  ║ ") + c(C.RED+B,"  decrypt [code] [password]  ") + c(W,"Secret code wapas original mein") + c(gd+B,"           ║"))
    print(c(gd+B,"  ║ ") + c(C.RED+B,"  password                   ") + c(W,"16 char strong password banao") + c(gd+B,"             ║"))
    print(c(gd+B,"  ║ ") + c(C.RED+B,"  password 8                 ") + c(W,"8 character password") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(C.RED+B,"  password pin 4             ") + c(W,"4 digit PIN (ATM jaisa)") + c(gd+B,"                   ║"))
    print(c(gd+B,"  ║ ") + c(C.RED+B,"  password simple            ") + c(W,"Letters + numbers only") + c(gd+B,"                    ║"))
    print(c(gd+B,"  ║ ") + c(C.RED+B,"  password strong 32         ") + c(W,"32 char super strong") + c(gd+B,"                      ║"))
    print(blank())

    # ── EVENT CALENDAR ──
    print(sec("📅", "EVENT CALENDAR", C.GOLD))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  event add Exam 20 March    ") + c(W,"Naya event add karo") + c(gd+B,"                       ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  event add Trip 15/4        ") + c(W,"Date DD/MM format mein bhi") + c(gd+B,"                 ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  events                     ") + c(W,"Saare upcoming events dekho") + c(gd+B,"                ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  event delete [id/name]     ") + c(W,"Event delete karo") + c(gd+B,"                         ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Auto icons: 🎓 Exam  🎂 Birthday  💼 Interview  ✈️ Trip") + c(gd+B,"   ║"))
    print(blank())

    # ── MOOD TRACKER ──
    print(sec("🧠", "MOOD TRACKER", C.MAGENTA))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(C.MAGENTA+B,"  mood happy                 ") + c(W,"Mood log karo") + c(gd+B,"                             ║"))
    print(c(gd+B,"  ║ ") + c(C.MAGENTA+B,"  aaj ka mood                ") + c(W,"Aaj ke saare moods dekho") + c(gd+B,"                  ║"))
    print(c(gd+B,"  ║ ") + c(C.MAGENTA+B,"  mood history               ") + c(W,"Last 7 din ka mood history") + c(gd+B,"                ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Moods: happy, sad, tired, stressed, angry, excited,") + c(gd+B,"         ║"))
    print(c(gd+B,"  ║ ") + c(D,"         okay, motivated, focused, anxious, bored...") + c(gd+B,"          ║"))
    print(blank())

    # ── CARE REMINDERS ──
    mg = C.MAGENTA
    print(sec("💕", "FRIDAY CARE REMINDERS", C.MAGENTA))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(mg+B,"  care                       ") + c(W,"Saare care reminders ka status") + c(gd+B,"            ║"))
    print(c(gd+B,"  ║ ") + c(mg+B,"  care off paani             ") + c(W,"Paani reminder band karo") + c(gd+B,"                  ║"))
    print(c(gd+B,"  ║ ") + c(mg+B,"  care on sleep              ") + c(W,"Sleep reminder on karo") + c(gd+B,"                    ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Auto reminders: 💧 Paani (2hr)  🍽️ Khana  😴 Sona  💊 Dawai") + c(gd+B,"  ║"))
    print(c(gd+B,"  ║ ") + c(D,"                  🧘 Break (2hr)  📵 Phone band karo (11:30pm)") + c(gd+B," ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── FITNESS TRACKER ──
    print(sec("💪", "FITNESS TRACKER", C.ORANGE))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(C.ORANGE+B,"  steps 5000                 ") + c(W,"Aaj ke steps add karo") + c(gd+B,"                     ║"))
    print(c(gd+B,"  ║ ") + c(C.ORANGE+B,"  paani 3                    ") + c(W,"Paani intake log karo (glass mein)") + c(gd+B,"         ║"))
    print(c(gd+B,"  ║ ") + c(C.ORANGE+B,"  neend 7                    ") + c(W,"Neend ke ghante log karo") + c(gd+B,"                  ║"))
    print(c(gd+B,"  ║ ") + c(C.ORANGE+B,"  workout pushups             ") + c(W,"Exercise/workout log karo") + c(gd+B,"                 ║"))
    print(c(gd+B,"  ║ ") + c(C.ORANGE+B,"  weight 70                  ") + c(W,"Aaj ka weight note karo (kg)") + c(gd+B,"              ║"))
    print(c(gd+B,"  ║ ") + c(C.ORANGE+B,"  aaj ka fitness             ") + c(W,"Poora fitness dashboard dekho") + c(gd+B,"             ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── GOAL TRACKER ──
    print(sec("🎯", "GOAL TRACKER", C.LIME))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  goal add [title]           ") + c(W,"Naya goal set karo") + c(gd+B,"                        ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  goals                      ") + c(W,"Saare goals + progress bar dekho") + c(gd+B,"          ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  goal update [id] [0-100]   ") + c(W,"Progress % update karo") + c(gd+B,"                    ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  goal done [id/name]        ") + c(W,"Goal complete mark karo 🎉") + c(gd+B,"                ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  goal note [id] [note]      ") + c(W,"Goal mein note add karo") + c(gd+B,"                   ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  goal delete [id/name]      ") + c(W,"Goal delete karo") + c(gd+B,"                          ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── EXPENSE TRACKER ──
    print(sec("💸", "EXPENSE TRACKER", C.YELLOW))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  kharch 500 lunch           ") + c(W,"Kharch note karo (amount + title)") + c(gd+B,"          ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  kharch 200 auto            ") + c(W,"Auto category detect hoti hai") + c(gd+B,"             ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  aaj ka kharch              ") + c(W,"Aaj ke saare kharche dikhao") + c(gd+B,"               ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  kharch summary             ") + c(W,"Last 7 din ka category wise summary") + c(gd+B,"       ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  kharch delete [id/aaj/all] ") + c(W,"Kharch delete karo") + c(gd+B,"                        ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Categories: Food, Travel, Health, Bills, Grocery, Entertainment") + c(gd+B," ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── SYSTEM INFO ──
    print(sec("📊", "SYSTEM INFO", C.DEEPBLUE))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(C.DEEPBLUE+B,"  time                       ") + c(W,"Abhi ka time dikhao") + c(gd+B,"                       ║"))
    print(c(gd+B,"  ║ ") + c(C.DEEPBLUE+B,"  date                       ") + c(W,"Aaj ki date dikhao") + c(gd+B,"                        ║"))
    print(c(gd+B,"  ║ ") + c(C.DEEPBLUE+B,"  battery                    ") + c(W,"Battery %, temp, status dikhao") + c(gd+B,"            ║"))
    print(c(gd+B,"  ║ ") + c(C.DEEPBLUE+B,"  ram                        ") + c(W,"RAM total, used, free dikhao") + c(gd+B,"              ║"))
    print(c(gd+B,"  ║ ") + c(C.DEEPBLUE+B,"  storage                    ") + c(W,"Storage total, used, free dikhao") + c(gd+B,"          ║"))
    print(c(gd+B,"  ║ ") + c(C.DEEPBLUE+B,"  system info                ") + c(W,"Sab ek jagah — phone, battery, RAM, storage") + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(C.DEEPBLUE+B,"  net                        ") + c(W,"WiFi info, active connections, data usage") + c(gd+B,"   ║"))
    print(c(gd+B,"  ║ ") + c(C.DEEPBLUE+B,"  location                   ") + c(W,"GPS coordinates + Google Maps link") + c(gd+B,"         ║"))
    print(c(gd+B,"  ║ ") + c(C.MAGENTA+B,"  ghar ka address            ") + c(W,"Aapka ghar ka pura pata dekhein") + c(gd+B,"             ║"))
    print(c(gd+B,"  ║ ") + c(C.ORANGE+B,"  ghar kitna dur             ") + c(W,"Current location se ghar ki doori") + c(gd+B,"           ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── NIGHT GUARD ──
    print(sec("🛡️", "NIGHT GUARD", C.PURPLE))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(C.PURPLE+B,"  night guard learn          ") + c(W,"Current state baseline save karo") + c(gd+B,"          ║"))
    print(c(gd+B,"  ║ ") + c(C.PURPLE+B,"  night guard on             ") + c(W,"Battery, network, process monitor ON") + c(gd+B,"      ║"))
    print(c(gd+B,"  ║ ") + c(C.PURPLE+B,"  night guard off            ") + c(W,"Guard band karo") + c(gd+B,"                           ║"))
    print(c(gd+B,"  ║ ") + c(C.PURPLE+B,"  night guard scan           ") + c(W,"Abhi ek baar manual scan karo") + c(gd+B,"             ║"))
    print(c(gd+B,"  ║ ") + c(C.PURPLE+B,"  night guard status         ") + c(W,"Guard ki current status dekho") + c(gd+B,"             ║"))
    print(c(gd+B,"  ║ ") + c(C.PURPLE+B,"  night guard alerts         ") + c(W,"Saare alerts ka log dekho") + c(gd+B,"                 ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Shortcut: ng on / ng off / ng scan / ng alerts") + c(gd+B,"             ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── COIN FLIP / DICE ──
    print(sec("🎲", "COIN FLIP / DICE", C.MAGENTA))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(mg+B,"  flip                       ") + c(W,"Coin flip — Heads ya Tails") + c(gd+B,"                 ║"))
    print(c(gd+B,"  ║ ") + c(mg+B,"  dice                       ") + c(W,"6-sided dice roll") + c(gd+B,"                         ║"))
    print(c(gd+B,"  ║ ") + c(mg+B,"  dice 20                    ") + c(W,"20-sided dice (D&D style)") + c(gd+B,"                  ║"))
    print(c(gd+B,"  ║ ") + c(mg+B,"  dice 3 6                   ") + c(W,"3 dice, 6 sides each") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(mg+B,"  random number 1 100        ") + c(W,"Random number between range") + c(gd+B,"               ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── CALL ──
    print(sec("📞", "CALL KARO", C.GREEN))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(gn+B,"  call                       ") + c(W,"Step-by-step call karo") + c(gd+B,"                     ║"))
    print(c(gd+B,"  ║ ") + c(gn+B,"  call +8801XXXXXXXXX        ") + c(W,"Direct number pe call") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Termux telephony API — Android call permission zaroori") + c(gd+B,"   ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── SCREENSHOT / CAMERA ──
    print(sec("📸", "SCREENSHOT / CAMERA", C.CYAN))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  screenshot                 ") + c(W,"Screen ka screenshot lo") + c(gd+B,"                     ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  screenshot myfile          ") + c(W,"Custom filename se save karo") + c(gd+B,"                ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  photo / camera             ") + c(W,"Camera se photo lo (front/back)") + c(gd+B,"             ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  selfie                     ") + c(W,"Front camera alias") + c(gd+B,"                         ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Termux API zaroori — pkg install termux-api") + c(gd+B,"              ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── SMS SEND ──
    print(sec("📱", "SMS SEND", C.CYAN))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  sms                        ") + c(W,"Step-by-step SMS bhejo") + c(gd+B,"                     ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  sms +8801XXX Hello bhai    ") + c(W,"Quick SMS — number + message ek saath") + c(gd+B,"     ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Termux SMS API — pkg install termux-api zaroori") + c(gd+B,"          ║"))
    print(c(gd+B,"  ║ ") + c(D,"  SMS permission Android settings mein dena hoga") + c(gd+B,"           ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── STOCK PRICE ──
    print(sec("📈", "STOCK PRICE", C.LIME))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  stock                      ") + c(W,"Top stocks watchlist") + c(gd+B,"                       ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  stock tesla nvidia         ") + c(W,"Specific stocks ka price") + c(gd+B,"                    ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  tesla stock                ") + c(W,"Single stock shortcut") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  sensex / nifty             ") + c(W,"Indian market indices") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  US + India: AAPL TSLA NVDA TCS RELIANCE INFY...") + c(gd+B,"       ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── GOLD PRICE ──
    print(sec("🥇", "GOLD & SILVER PRICE", C.GOLD))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(gd+B,"  gold                       ") + c(W,"Gold aur silver ka live bhav") + c(gd+B,"               ║"))
    print(c(gd+B,"  ║ ") + c(gd+B,"  sone ka bhav               ") + c(W,"Hindi alias") + c(gd+B,"                               ║"))
    print(c(gd+B,"  ║ ") + c(gd+B,"  gold rate                  ") + c(W,"Per gram, 10g, tola, troy oz") + c(gd+B,"               ║"))
    print(c(gd+B,"  ║ ") + c(D,"  USD + INR — Gram / Tola / Troy Oz — Live data") + c(gd+B,"             ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── CRYPTO ──
    print(sec("₿", "CRYPTO LIVE PRICES", C.GOLD))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(gd+B,"  crypto                     ") + c(W,"Top 6 coins ke live prices") + c(gd+B,"                  ║"))
    print(c(gd+B,"  ║ ") + c(gd+B,"  crypto btc eth              ") + c(W,"Specific coins ke prices") + c(gd+B,"                    ║"))
    print(c(gd+B,"  ║ ") + c(gd+B,"  btc price                  ") + c(W,"Bitcoin ka price") + c(gd+B,"                            ║"))
    print(c(gd+B,"  ║ ") + c(gd+B,"  doge price                 ") + c(W,"Dogecoin ka price") + c(gd+B,"                           ║"))
    print(c(gd+B,"  ║ ") + c(D,"  USD + INR — CoinGecko API — BTC ETH BNB XRP SOL...") + c(gd+B,"    ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── NUMBER GAME ──
    print(sec("🎯", "NUMBER GUESSING GAME", C.MAGENTA))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(mg+B,"  number game                ") + c(W,"1-100 ke beech guess karo") + c(gd+B,"                   ║"))
    print(c(gd+B,"  ║ ") + c(mg+B,"  number game 1 50           ") + c(W,"Custom range set karo") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(mg+B,"  [number]                   ") + c(W,"Apna guess type karo") + c(gd+B,"                       ║"))
    print(c(gd+B,"  ║ ") + c(mg+B,"  game stop                  ") + c(W,"Game band karo") + c(gd+B,"                             ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Hot/Cold hints — 7 chances — 🔥🔥🔥 to 🧊") + c(gd+B,"               ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── QUIZ ──
    print(sec("🧠", "QUIZ / TRIVIA", C.CYAN))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  quiz                       ") + c(W,"5 random questions ka quiz") + c(gd+B,"                  ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  quiz 10                    ") + c(W,"10 questions ka quiz") + c(gd+B,"                       ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  1 / 2 / 3 / 4              ") + c(W,"Quiz mein jawab do") + c(gd+B,"                         ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  quiz stop                  ") + c(W,"Quiz band karo") + c(gd+B,"                             ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Science, Geography, History, Tech, Sports — 30+ Qs") + c(gd+B,"    ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── COUNTRY INFO ──
    print(sec("🗺️", "COUNTRY INFO", C.TEAL))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  country info france        ") + c(W,"Kisi bhi desh ki poori info") + c(gd+B,"                ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  country bangladesh         ") + c(W,"Capital, population, area, currency") + c(gd+B,"       ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  desh japan                 ") + c(W,"Language, timezone, calling code") + c(gd+B,"          ║"))
    print(c(gd+B,"  ║ ") + c(D,"  RestCountries API — 250+ countries supported") + c(gd+B,"              ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── WORLD CLOCK ──
    print(sec("🌍", "WORLD CLOCK / TIMEZONE", C.TEAL))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  world clock                ") + c(W,"6 cities ka time ek saath") + c(gd+B,"                  ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  time in dubai              ") + c(W,"Kisi ek city ka time") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  time in tokyo              ") + c(W,"Japan ka current time") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  timezone london            ") + c(W,"UK ka time") + c(gd+B,"                                ║"))
    print(c(gd+B,"  ║ ") + c(D,"  50+ cities: dhaka, dubai, london, tokyo, new york...") + c(gd+B,"      ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── TRANSLATE ──
    print(sec("🌍", "TRANSLATOR", C.PURPLE))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(C.PURPLE+B,"  translate hello to french  ") + c(W,"Text ko kisi bhi language mein") + c(gd+B,"            ║"))
    print(c(gd+B,"  ║ ") + c(C.PURPLE+B,"  translate Mujhe bhook lagi ") + c(W,"                                              ║"))
    print(c(gd+B,"  ║ ") + c(C.PURPLE+B,"  to arabic                  ") + c(W,"Koi bhi language — 50+ supported") + c(gd+B,"         ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Languages: french, arabic, urdu, spanish, japanese...") + c(gd+B,"    ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Groq AI se translate — fast & accurate") + c(gd+B,"                    ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── RIDDLE ──
    print(sec("🧩", "PAHELI / RIDDLE", C.YELLOW))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  riddle                     ") + c(W,"Random Hinglish paheli") + c(gd+B,"                     ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  paheli                     ") + c(W,"Hindi alias") + c(gd+B,"                               ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  jawab                      ") + c(W,"Paheli ka answer reveal karo") + c(gd+B,"               ║"))
    print(c(gd+B,"  ║ ") + c(D,"  25 Hinglish riddles — answer reveal option") + c(gd+B,"                ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── FUN FACT ──
    print(sec("🤓", "FUN FACT", C.CYAN))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  fun fact                   ") + c(W,"Random interesting fact") + c(gd+B,"                   ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  fact                       ") + c(W,"Short alias") + c(gd+B,"                               ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  did you know               ") + c(W,"Kuch amazing batao") + c(gd+B,"                        ║"))
    print(c(gd+B,"  ║ ") + c(D,"  55+ facts + live API — har baar naya fact") + c(gd+B,"                 ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── THIS DAY IN HISTORY ──
    print(sec("📜", "THIS DAY IN HISTORY", C.ORANGE))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  this day in history        ") + c(W,"Aaj ke din kya hua tha history mein") + c(gd+B,"      ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  aaj ka itihas              ") + c(W,"Hindi alias") + c(gd+B,"                               ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  on this day                ") + c(W,"5 historical events aaj ke din ke") + c(gd+B,"        ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Wikipedia API — different eras se events") + c(gd+B,"                  ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── WORD OF THE DAY ──
    print(sec("📖", "WORD OF THE DAY", C.GOLD))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(gd+B,"  word of the day            ") + c(W,"Aaj ka naya English word seekho") + c(gd+B,"           ║"))
    print(c(gd+B,"  ║ ") + c(gd+B,"  wotd                       ") + c(W,"Short alias") + c(gd+B,"                               ║"))
    print(c(gd+B,"  ║ ") + c(gd+B,"  vocabulary                 ") + c(W,"Same feature") + c(gd+B,"                              ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Shows: Word, pronunciation, meaning, example, synonyms") + c(gd+B,"   ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Har din naya word — 28 words ka rotation") + c(gd+B,"                  ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── SPEEDTEST ──
    print(sec("🚀", "INTERNET SPEED TEST", C.TEAL))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  speedtest                  ") + c(W,"Download / Upload / Ping test") + c(gd+B,"              ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  speed                      ") + c(W,"Short alias") + c(gd+B,"                               ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Shows: Mbps + progress bar + quality rating") + c(gd+B,"               ║"))
    print(c(gd+B,"  ║ ") + c(D,"  No API key needed — uses Cloudflare test server") + c(gd+B,"           ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── NETWORK SCANNER ──
    print(sec("📡", "NETWORK SCANNER", C.TEAL))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  netscan                    ") + c(W,"LAN pe saare devices dhundo") + c(gd+B,"                ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  network scan               ") + c(W,"Auto subnet detect karke scan") + c(gd+B,"              ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  netscan 192.168.0.0/24     ") + c(W,"Custom subnet scan") + c(gd+B,"                        ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Shows: IP, Hostname, kaun 'You' hai") + c(gd+B,"                       ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── PING TOOL ──
    print(sec("🏓", "PING TOOL", C.CYAN))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  ping google.com            ") + c(W,"4 packets ping karo") + c(gd+B,"                       ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  ping 8.8.8.8               ") + c(W,"IP address ping karo") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  ping 192.168.1.1 8         ") + c(W,"Custom packet count") + c(gd+B,"                       ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Shows: RTT min/max/avg, jitter, packet loss, quality") + c(gd+B,"     ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── PORT SCANNER ──
    print(sec("🔍", "PORT SCANNER", C.TEAL))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  portscan 192.168.1.1       ") + c(W,"Common ports scan karo") + c(gd+B,"                    ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  portscan google.com        ") + c(W,"Domain scan karo") + c(gd+B,"                          ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  portscan 192.168.1.1 1-100 ") + c(W,"Port range scan") + c(gd+B,"                           ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  portscan 10.0.0.1 80       ") + c(W,"Single port check") + c(gd+B,"                         ║"))
    print(c(gd+B,"  ║ ") + c(D,"  22 common ports check karta hai — SSH, HTTP, MySQL...") + c(gd+B,"    ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── POMODORO TIMER ──
    print(sec("🍅", "POMODORO TIMER", C.ORANGE))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  pomodoro                   ") + c(W,"25 min focus + 5 min break (default)") + c(gd+B,"      ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  pomodoro 45                ") + c(W,"45 min focus + 5 min break") + c(gd+B,"                ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  pomodoro 50 10             ") + c(W,"50 min focus + 10 min break") + c(gd+B,"               ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  pomodoro status            ") + c(W,"Progress bar + time remaining dekho") + c(gd+B,"       ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  pomodoro stop              ") + c(W,"Timer rok do") + c(gd+B,"                              ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Background mein chalta hai — Friday notify karegi") + c(gd+B,"        ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── SMART TODO LIST ──
    print(sec("📋", "SMART TODO LIST", C.CYAN))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  todo add meeting kal !high  ") + c(W,"Todo add karo + priority + deadline") + c(gd+B,"    ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  todo add exam 15 march      ") + c(W,"Date ke saath todo") + c(gd+B,"                        ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  todos                       ") + c(W,"Saare todos dekho") + c(gd+B,"                         ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  todo done [id/name]         ") + c(W,"Complete mark karo") + c(gd+B,"                        ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  todo delete [id/name]       ") + c(W,"Todo delete karo") + c(gd+B,"                          ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  todo clear                  ") + c(W,"Completed todos clear karo") + c(gd+B,"                ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Priority: !high !medium !low  |  Deadline: kal, aaj, dd/mm") + c(gd+B," ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── HABIT TRACKER ──
    print(sec("💪", "HABIT TRACKER", C.LIME))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  habit add pushups          ") + c(W,"Naya habit add karo") + c(gd+B,"                       ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  habit done pushups         ") + c(W,"Aaj ka habit complete mark karo") + c(gd+B,"           ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  habits                     ") + c(W,"Saare habits + streak dekho") + c(gd+B,"                ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  habit delete pushups       ") + c(W,"Habit remove karo") + c(gd+B,"                         ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Shows: 🔥 Streak, 🏆 Best streak, 📆 Last 7 days") + c(gd+B,"        ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── QR CODE ──
    print(sec("🔲", "QR CODE GENERATOR", C.TEAL))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  qr https://google.com      ") + c(W,"URL ka QR code banao") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  qr Hello World             ") + c(W,"Koi bhi text ka QR code") + c(gd+B,"                   ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  qr upi://pay?pa=xyz@upi    ") + c(W,"UPI payment QR code") + c(gd+B,"                       ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Terminal mein preview + PNG file save hoti hai") + c(gd+B,"           ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Install: pip install qrcode[pil]") + c(gd+B,"                          ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── DICTIONARY ──
    print(sec("📚", "DICTIONARY", C.PURPLE))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(C.PURPLE+B,"  meaning serendipity        ") + c(W,"Word ka meaning, synonyms, antonyms") + c(gd+B,"       ║"))
    print(c(gd+B,"  ║ ") + c(C.PURPLE+B,"  define eloquent            ") + c(W,"Definition with examples") + c(gd+B,"                  ║"))
    print(c(gd+B,"  ║ ") + c(C.PURPLE+B,"  dict ambiguous             ") + c(W,"Multiple parts of speech") + c(gd+B,"                  ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Alias: meaning, define, dict, matlab, word") + c(gd+B,"                ║"))
    print(c(gd+B,"  ║ ") + c(D,"  No API key needed — bilkul free!") + c(gd+B,"                          ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── CURRENCY CONVERTER ──
    print(sec("💱", "CURRENCY CONVERTER", C.GOLD))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  convert 100 usd to inr     ") + c(W,"USD se INR mein convert karo") + c(gd+B,"              ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  convert 500 inr to usd     ") + c(W,"INR se USD mein") + c(gd+B,"                           ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  convert 50 eur to gbp      ") + c(W,"Koi bhi currency pair") + c(gd+B,"                     ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Currencies: USD INR EUR GBP JPY AED SAR BDT PKR CNY...") + c(gd+B,"    ║"))
    print(c(gd+B,"  ║ ") + c(D,"  No API key needed — bilkul free!") + c(gd+B,"                          ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── CALCULATOR ──
    print(sec("🧮", "CALCULATOR", C.LIME))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  calc 25 * 4 + 10           ") + c(W,"Basic arithmetic") + c(gd+B,"                          ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  calc sqrt(144)             ") + c(W,"Square root") + c(gd+B,"                               ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  calc 2^10                  ") + c(W,"Power / exponent") + c(gd+B,"                          ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  calc sin(pi/2)             ") + c(W,"Trigonometry") + c(gd+B,"                              ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  calc factorial(10)         ") + c(W,"Factorial") + c(gd+B,"                                 ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  calc log(100)              ") + c(W,"Logarithm") + c(gd+B,"                                 ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Alias: calculate, hisab") + c(gd+B,"                                      ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── NEWS ──
    print(sec("📰", "NEWS / KHABAR", C.ORANGE))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  news                       ") + c(W,"India ki top headlines dikhao") + c(gd+B,"             ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  khabar                     ") + c(W,"Hindi command — same kaam") + c(gd+B,"                 ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  news sports                ") + c(W,"Category wise news dekho") + c(gd+B,"                  ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  news technology            ") + c(W,"Tech news") + c(gd+B,"                                 ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  news bitcoin               ") + c(W,"Kisi bhi topic pe news search karo") + c(gd+B,"        ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Categories: sports, technology, business, entertainment,") + c(gd+B,"     ║"))
    print(c(gd+B,"  ║ ") + c(D,"               health, science, politics, cricket, bollywood") + c(gd+B,"   ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Needs: NEWSDATA_API_KEY environment variable") + c(gd+B,"             ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── WEATHER ──
    print(sec("🌤️", "WEATHER / MAUSAM", C.CYAN))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  weather                    ") + c(W,"Apni location ka weather auto-detect") + c(gd+B,"      ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  mausam                     ") + c(W,"Hindi command — same kaam") + c(gd+B,"                 ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  weather Kolkata            ") + c(W,"Kisi bhi city ka weather dekho") + c(gd+B,"            ║"))
    print(c(gd+B,"  ║ ") + c(cy+B,"  weather London             ") + c(W,"World ki koi bhi city") + c(gd+B,"                     ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Shows: Temp, Feels Like, Humidity, Wind, Sunrise/Sunset") + c(gd+B,"   ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Needs: OPENWEATHER_API_KEY environment variable") + c(gd+B,"          ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── IP LOOKUP ──
    print(sec("🌐", "IP LOOKUP", C.TEAL))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  myip / my ip / mera ip     ") + c(W,"Apna public IP + location dekho") + c(gd+B,"           ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  ip check 8.8.8.8           ") + c(W,"Kisi bhi IP ka location, ISP dekho") + c(gd+B,"        ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  ip check google.com        ") + c(W,"Domain resolve karke full info lo") + c(gd+B,"         ║"))
    print(c(gd+B,"  ║ ") + c(tl+B,"  ip check 42.110.166.24     ") + c(W,"Kisi bhi IP ki detail dekho") + c(gd+B,"               ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Shortcut: iplookup [ip/domain] bhi kaam karta hai") + c(gd+B,"          ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── JOKE & QUOTE ──
    print(sec("😂", "JOKE & QUOTE / MOTIVATION", C.YELLOW))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  joke                       ") + c(W,"Random funny joke sunao") + c(gd+B,"                   ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  ek joke / joke sunao       ") + c(W,"Ek joke bolo Friday") + c(gd+B,"                       ║"))
    print(c(gd+B,"  ║ ") + c(yl+B,"  hasao                      ") + c(W,"Hasa do mujhe!") + c(gd+B,"                            ║"))
    print(c(gd+B,"  ║ ") + c(mg+B,"  quote                      ") + c(W,"Random motivational quote dikhao") + c(gd+B,"          ║"))
    print(c(gd+B,"  ║ ") + c(mg+B,"  ek quote / motivate        ") + c(W,"Motivation chahiye? Yahan aao") + c(gd+B,"             ║"))
    print(c(gd+B,"  ║ ") + c(mg+B,"  inspire me / inspire karo  ") + c(W,"Inspire ho jao Boss!") + c(gd+B,"                      ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── MUSIC PLAYER ──
    print(sec("🎵", "MUSIC PLAYER", C.LIME))
    print(c(gd+B,"  ║ ") + c(lm+B,"  Command                    ") + c(yl,"Kya karta hai") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  song download [naam]       ") + c(W,"YouTube se MP3 download — yt-dlp use karta hai") + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  mp3 [naam]                 ") + c(W,"Short alias: mp3 tum hi ho arijit") + c(gd+B,"         ║"))
    print(c(gd+B,"  ║ ") + c(D,"  " + "─"*58) + c(gd+B," ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  music / gaane dikho        ") + c(W,"Saare gaane scan karke dikhao") + c(gd+B,"             ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  gana bajao                 ") + c(W,"Random ya pehla gana bajao") + c(gd+B,"                 ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  gana bajao [naam]          ") + c(W,"Naam se specific gana search + bajao") + c(gd+B,"      ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  next song / agla gana     ") + c(W,"Agla gana bajao") + c(gd+B,"                           ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  back song / pichla gana   ") + c(W,"Pichla gana bajao") + c(gd+B,"                         ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  gana band karo / stop song") + c(W,"Gana rok do") + c(gd+B,"                              ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  volume up / volume badhao ") + c(W,"Awaaz badhao (+10)") + c(gd+B,"                        ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  volume down / volume kam  ") + c(W,"Awaaz kam karo (-10)") + c(gd+B,"                      ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  volume [0-100]             ") + c(W,"Exact volume set karo") + c(gd+B,"                     ║"))
    print(c(gd+B,"  ║ ") + c(lm+B,"  aaj ka gana                ") + c(W,"Abhi kaunsa gana chal raha hai") + c(gd+B,"            ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Folders: /sdcard/Download  |  /sdcard/Music  |  SD Card") + c(gd+B,"    ║"))
    print(c(gd+B,"  ║ ") + c(D,"  Formats: MP3, M4A, FLAC, WAV, OGG, AAC, OPUS") + c(gd+B,"           ║"))
    print(blank())
    print(divider())
    print(blank())

    # ── EXIT ──
    print(sec("🚪", "EXIT", or_))
    print(c(gd+B,"  ║ ") + c(or_+B,"  quit / exit / bye          ") + c(W,"Friday band karo") + c(gd+B,"                          ║"))
    print(c(gd+B,"  ║ ") + c(or_+B,"  band karo / alvida         ") + c(W,"Hindi exit commands") + c(gd+B,"                       ║"))
    print(blank())
    print(box_bot)
    print()
    print(c(D, "  Press Enter to continue..."))
    input()
    os.system("clear")


# ──────────────────────────────────────────────────────────
#  WEB SEARCH  (DuckDuckGo — free, no API key)
# ──────────────────────────────────────────────────────────

# Ye phrases hoti hain clearly conversational — KABHI search nahi
CASUAL_PHRASES = [
    "kaise ho","kaisi ho","kya haal","theek ho","kya chal raha",
    "acha din guzra","din guzra","din kaisa","kaisa din","kaisa raha",
    "zabardast guzra","achha guzra","bekar guzra","mast guzra",
    "kya kar rahe","kya soch rahe","shukriya","thank you","thanks",
    "haha","hahaha","lol","wah","great","awesome","accha","theek hai","ok",
    "bye","goodbye","good night","good morning","good evening",
    "main hoon","main theek","bilkul","zaroor","hmm","han","haan",
    "nahi","nope","yes","no","sure","maybe","shayad",
    "baat karo","suno","yaar","boss","bhai","help karo",
    "mujhe batao","samjhao","kya matlab","kya soch","kya lagta",
    "gussa ho","sad ho","khush ho","romantic ho","excited ho",
    "mood fresher","kaise lag raha","aaj kaisa raha","din badhiya",
    "sorry","maafi","theek kiya","kya soch","kya feel",
    "pagal","pagla","mazak","masti","banter","chill","relax",
    "chatgpt","gpt","openai","bard","gemini","deepseek",
    "kuch interesting","kuch batao","kuch sunao","kal milenge",
]

# Ye commands Groq ke paas kabhi nahi jayenge — dedicated handlers hain
DEDICATED_COMMANDS = [
    "news", "khabar", "weather", "mausam", "world news", "india news",
    "tech news", "sports news", "business news", "duniya ki news",
    "taza khabar", "breaking news", "headlines", "top news",
]

# Ye phrases clearly search chahti hain
SEARCH_PHRASES = [
    # Time based
    "kab hai","kab hoga","kab tha","kab se","kab tak",
    "aaj ka","aaj ki","kal ka","is hafte","is mahine",
    "abhi ka","live score","live rate","live price",
    # Price/Rate
    "price kya hai","rate kya hai","kitne ka hai","kitni ki hai",
    "ka price","ki price","ka rate","ki rate","ka bhav","ki kimat",
    "kitna hai aaj","kitni hai aaj","current price","current rate",
    # News
    "aaj ka news","latest news","recent news","breaking news",
    "abhi kya ho raha","kya hua aaj","news kya hai",
    # Weather
    "aaj ka weather","aaj ka mausam","mausam kaisa hai","temperature kya hai",
    "weather","mausam","temperature","forecast","humidity","barish","baarish","garmi","sardi",
    # Match/Sports
    "aaj ka score","match result","kaun jita","score kya hai",
    "cricket result","football result","match kaisa raha",
    # People/Positions
    "kaun sa pm","kaun president","kaun ceo","kaun cm",
    "abhi kaun hai","kaun ban gaya","naya pm","naya president",
    # Year based
    "2024 mein","2025 mein","2026 mein","2027 mein","is saal","next year",
    "election result","vote result",
]

# Specific high-confidence keywords (sirf standalone — conflict check karke add kiye)
SEARCH_KEYWORDS = [
    # Festivals/Events (Friday ke music commands se conflict nahi)
    "ramzan","eid","diwali","holi","christmas","navratri","durga puja",
    "muharram","baisakhi","pongal","onam","lohri","makar sankranti",

    # Sports (music player "play" se alag rakha)
    "ipl score","world cup score","cricket score","football score",
    "fifa","nba","ipl 2026","champions league","kabaddi",
    "olympic","commonwealth games","asian games",

    # Crypto (bitcoin already tha, aur add kiye)
    "bitcoin","ethereum","crypto price","dogecoin","binance",
    "nft price","web3","defi",

    # Stock/Finance
    "stock price","share price","sensex","nifty","bse","nse",
    "dollar rate","rupee rate","euro rate","pound rate",
    "gold price","silver price","gold rate","silver rate",
    "petrol price","diesel price","petrol rate","diesel rate",
    "onion price","tomato price","vegetable price",

    # Tech launches (brightness, volume se conflict nahi)
    "iphone price","samsung price","oneplus price","pixel price",
    "laptop price","phone price","gadget price",
    "launched","released","announced","new model",

    # Natural disasters/Breaking
    "earthquake","flood","cyclone","tsunami","hurricane","tornado",
    "accident","blast","fire broke","disaster",

    # Elections/Politics
    "election","vote result","exit poll","manifesto",
    "new law","new policy","budget 2026","parliament",

    # Health/Science
    "new virus","vaccine","disease outbreak","covid",
    "nasa discovery","space mission","isro launch","chandrayaan",
    "new planet","asteroid","solar eclipse","lunar eclipse",

    # Entertainment (music player commands se alag — "play" nahi dala)
    "box office","movie release","naya song release","album launch",
    "ott release","netflix new","amazon prime new",

    # Economy
    "inflation rate","gdp","repo rate","rbi","fed rate",
    "oil price","crude oil",
]

def needs_search(text: str) -> bool:
    tl = text.lower().strip()

    # Short casual messages — no search (under 5 words)
    if len(tl.split()) <= 4:
        if not any(kw in tl for kw in SEARCH_KEYWORDS):
            return False

    # Clearly casual — no search
    if any(phrase in tl for phrase in CASUAL_PHRASES):
        return False

    # Clearly needs search
    if any(phrase in tl for phrase in SEARCH_PHRASES):
        return True

    # Specific keywords
    if any(kw in tl for kw in SEARCH_KEYWORDS):
        return True

    # Year mention with question
    import re as _re
    if _re.search(r'\b(202[3-9]|203\d)\b', tl) and any(q in tl for q in ["kab","kya","kaun","kitna","date","?","when","who","what"]):
        return True

    # City + weather/price/news combination
    CITY_WORDS = [
        "kolkata","mumbai","delhi","chennai","bangalore","hyderabad","pune","ahmedabad",
        "jaipur","lucknow","kanpur","nagpur","patna","bhopal","surat","vadodara",
        "london","new york","dubai","tokyo","paris","sydney","singapore","beijing",
        "dhaka","karachi","islamabad","kathmandu","colombo","kabul",
    ]
    CITY_TRIGGERS = ["weather","mausam","temperature","news","price","rate","flood","rain","barish"]
    if any(city in tl for city in CITY_WORDS) and any(trig in tl for trig in CITY_TRIGGERS):
        return True

    # Standalone "weather" keyword bhi search karo
    if "weather" in tl or "mausam" in tl:
        return True

    return False

# ──────────────────────────────────────────────────────────
#  CALL / PHONE
# ──────────────────────────────────────────────────────────

_call_state = {
    "active": False,
    "step":   None,   # "number" | "confirm"
    "number": "",
}

def call_start() -> None:
    _call_state.update({"active": True, "step": "number", "number": ""})
    print(c(C.GREEN + C.BOLD, "  📞 CALL KARO"))
    print(c(C.GREEN,           "  " + "─" * 44))
    print()
    print(c(C.WHITE, "  📞 Jis number pe call karna hai type karo:"))
    print(c(C.DIM,   "  Example: +8801XXXXXXXXX  ya  +91XXXXXXXXXX"))
    print(c(C.DIM,   "  'call stop' — cancel"))
    print()
    speak("Kisko call karna hai Boss? Number type karo.")

def call_handle(user_input: str) -> None:
    import subprocess as _sp

    if user_input.lower() in ("call stop", "cancel", "band karo", "mat karo"):
        _call_state["active"] = False
        print(c(C.DIM, "  Call cancel ho gaya."))
        speak("Theek hai Boss, call cancel.")
        return

    step = _call_state["step"]

    if step == "number":
        num = user_input.strip().replace(" ", "")
        if not re.match(r'^\+?\d{7,15}$', num):
            print(c(C.RED, "  ✗ Number galat lag raha hai!"))
            print(c(C.DIM, "  Format: +8801XXXXXXXXX  ya  +91XXXXXXXXXX"))
            return

        _call_state["number"] = num
        _call_state["step"]   = "confirm"
        masked = "*" * len(num[:-4]) + num[-4:]

        print()
        print(c(C.YELLOW + C.BOLD, "  ╔══════════════════════════════════════════╗"))
        print(c(C.YELLOW + C.BOLD, "  ║       📞  CONFIRM CALL                  ║"))
        print(c(C.YELLOW + C.BOLD, "  ╚══════════════════════════════════════════╝"))
        print()
        print(c(C.WHITE,           f"  📞 Number : {masked}"))
        print()
        print(c(C.LIME + C.BOLD,   "  ✅ Call ke liye : yes / haan"))
        print(c(C.RED,              "  ❌ Cancel ke liye: no / nahi"))
        print()
        speak("Confirm karo Boss.")

    elif step == "confirm":
        if user_input.lower() in ("yes", "haan", "ha", "call", "karo", "ok", "y"):
            num = _call_state["number"]
            masked = "*" * len(num[:-4]) + num[-4:]
            _call_state["active"] = False
            _call_state["step"]   = None

            print(c(C.DIM, "  📡 Calling ..."))
            try:
                result = _sp.run(
                    ["termux-telephony-call", num],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    print(c(C.LIME + C.BOLD, "  ✅ Call shuru ho gayi!"))
                    print(c(C.DIM,            f"  📞 To: {masked}"))
                    speak("Call shuru ho gayi Boss!")
                else:
                    err = result.stderr.strip() or "Unknown error"
                    print(c(C.RED, f"  ✗ Call fail: {err}"))
                    print(c(C.DIM,  "  Phone permission check karo Android settings mein."))
                    speak("Call nahi ho saki Boss.")
            except FileNotFoundError:
                print(c(C.RED,  "  ✗ termux-telephony-call nahi mila!"))
                print(c(C.DIM,  "  Install: pkg install termux-api"))
                speak("Termux telephony API nahi hai Boss.")
            except Exception as e:
                print(c(C.RED, f"  ✗ Error: {e}"))
            print()

        elif user_input.lower() in ("no", "nahi", "na", "cancel", "mat karo"):
            _call_state["active"] = False
            _call_state["step"]   = None
            print(c(C.DIM, "  Call cancel ho gaya."))
            speak("Theek hai Boss, call cancel.")
        else:
            print(c(C.DIM, "  'yes' ya 'no' type karo."))

# ──────────────────────────────────────────────────────────
#  SCREENSHOT / CAMERA
# ──────────────────────────────────────────────────────────

def take_screenshot(filename: str = "") -> None:
    import subprocess as _sp, os
    from datetime import datetime as _dt

    if not filename:
        filename = f"friday_screenshot_{_dt.now().strftime('%Y%m%d_%H%M%S')}.png"
    if not filename.endswith(".png"):
        filename += ".png"

    # Save to /sdcard/Pictures for easy access
    sdcard_path = f"/sdcard/Pictures/{filename}"

    print(c(C.CYAN + C.BOLD, "  📸 SCREENSHOT"))
    print(c(C.CYAN,           "  " + "─" * 44))
    print()
    print(c(C.DIM, "  📡 Taking screenshot ..."))

    taken = False

    # Method 1: termux-screenshot (some Termux versions)
    for cmd in [
        ["termux-screenshot", sdcard_path],
        ["termux-screenshot", "-f", sdcard_path],
    ]:
        try:
            r = _sp.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                taken = True
                break
        except Exception:
            pass

    # Method 2: Android screencap via shell
    if not taken:
        try:
            r = _sp.run(
                ["sh", "-c", f"screencap -p {sdcard_path}"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0 and os.path.exists(sdcard_path):
                taken = True
        except Exception:
            pass

    # Method 3: input keyevent screenshot (simulates power+volume)
    if not taken:
        try:
            r = _sp.run(
                ["sh", "-c", "input keyevent 120"],  # KEYCODE_SYSRQ
                capture_output=True, text=True, timeout=5
            )
            import time; time.sleep(1)
            # Check if screenshot appeared in DCIM
            dcim = "/sdcard/DCIM/Screenshots"
            if os.path.exists(dcim):
                files = sorted(os.listdir(dcim))
                if files:
                    latest = os.path.join(dcim, files[-1])
                    _sp.run(["cp", latest, sdcard_path], timeout=5)
                    taken = True
        except Exception:
            pass

    if taken and os.path.exists(sdcard_path):
        size = os.path.getsize(sdcard_path) // 1024
        print(c(C.LIME + C.BOLD, f"  ✅ Screenshot saved!"))
        print(c(C.WHITE,          f"  📁 File   : {sdcard_path}"))
        print(c(C.DIM,            f"  📦 Size   : {size} KB"))
        print(c(C.DIM,             "  📂 Gallery mein bhi milega!"))
        print()
        speak("Screenshot le liya Boss!")
    else:
        print(c(C.RED,  "  ✗ Screenshot nahi ho saka!"))
        print()
        print(c(C.YELLOW + C.BOLD, "  💡 Manual screenshot:"))
        print(c(C.WHITE,            "  Power button + Volume Down — ek saath dabao"))
        print()
        speak("Screenshot nahi ho saka Boss. Manual try karo.")
    print()

def take_photo(filename: str = "") -> None:
    import subprocess as _sp, os
    from datetime import datetime as _dt

    if not filename:
        filename = f"friday_photo_{_dt.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    if not filename.endswith(".jpg"):
        filename += ".jpg"

    print(c(C.CYAN + C.BOLD, "  📷 CAMERA"))
    print(c(C.CYAN,           "  " + "─" * 44))
    print()

    # Ask front or back
    print(c(C.WHITE, "  Kaunsa camera?"))
    print(c(C.LIME,  "  1. back  — pichla camera"))
    print(c(C.LIME,  "  2. front — selfie camera"))
    print()

    cam_choice = input(c(C.CYAN + C.BOLD, "  Friday ➤ ")).strip().lower()
    cam = "front" if cam_choice in ("front", "selfie", "2", "f") else "back"

    print()
    print(c(C.DIM, f"  📡 Taking photo ({cam} camera) ..."))

    try:
        result = _sp.run(
            ["termux-camera-photo", "-c", cam, filename],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            size = os.path.getsize(filename) // 1024 if os.path.exists(filename) else 0
            print(c(C.LIME + C.BOLD, f"  ✅ Photo liya!"))
            print(c(C.WHITE,          f"  📁 File   : {filename}"))
            print(c(C.WHITE,          f"  📷 Camera : {cam}"))
            print(c(C.DIM,            f"  📦 Size   : {size} KB"))
            print()
            speak(f"Photo le liya Boss! {cam} camera se.")
        else:
            err = result.stderr.strip() or "Unknown error"
            print(c(C.RED, f"  ✗ Error: {err}"))
            print(c(C.DIM,  "  termux-camera-photo kaam nahi kar raha."))
            print(c(C.DIM,  "  Install: pkg install termux-api"))
    except FileNotFoundError:
        print(c(C.RED, "  ✗ termux-camera-photo nahi mila!"))
        print(c(C.DIM,  "  Install: pkg install termux-api"))
        speak("Termux API install nahi hai Boss.")
    except Exception as e:
        print(c(C.RED, f"  ✗ Error: {e}"))
    print()

# ──────────────────────────────────────────────────────────
#  SMS SEND
# ──────────────────────────────────────────────────────────

_sms_state = {
    "active":   False,
    "step":     None,   # "number" | "message" | "confirm"
    "number":   "",
    "message":  "",
}

def sms_start() -> None:
    _sms_state.update({"active": True, "step": "number", "number": "", "message": ""})
    print(c(C.CYAN + C.BOLD,  "  📱 SMS SEND"))
    print(c(C.CYAN,            "  " + "─" * 46))
    print()
    print(c(C.WHITE,           "  📞 Number type karo (with country code):"))
    print(c(C.DIM,             "  Example: +8801XXXXXXXXX  ya  +91XXXXXXXXXX"))
    print(c(C.DIM,             "  'sms stop' — cancel"))
    print()
    speak("SMS send karna chahte ho Boss? Number type karo.")

def sms_handle(user_input: str) -> None:
    step = _sms_state["step"]

    if user_input.lower() in ("sms stop", "cancel", "band karo"):
        _sms_state["active"] = False
        print(c(C.DIM, "  SMS cancel ho gaya."))
        return

    if step == "number":
        num = user_input.strip().replace(" ", "")
        # Basic validation
        if not re.match(r'^\+?\d{7,15}$', num):
            print(c(C.RED,  "  ✗ Number galat lag raha hai!"))
            print(c(C.DIM,  "  Format: +8801XXXXXXXXX  ya  +91XXXXXXXXXX"))
            return
        _sms_state["number"] = num
        _sms_state["step"]   = "message"
        masked = num[:-4].replace(num[:-4], "*" * len(num[:-4])) + num[-4:]
        print()
        print(c(C.WHITE,     f"  ✅ Number: {masked}"))
        print()
        print(c(C.WHITE,     "  ✏️  Ab message type karo:"))
        print()
        speak("Number set ho gaya. Ab message type karo.")

    elif step == "message":
        if len(user_input.strip()) < 1:
            print(c(C.RED, "  ✗ Message khali nahi ho sakta!"))
            return
        _sms_state["message"] = user_input.strip()
        _sms_state["step"]    = "confirm"
        num    = _sms_state["number"]
        msg    = _sms_state["message"]
        masked = "*" * len(num[:-4]) + num[-4:]
        print()
        print(c(C.YELLOW + C.BOLD, "  ╔══════════════════════════════════════════╗"))
        print(c(C.YELLOW + C.BOLD, "  ║       📤  CONFIRM SMS                   ║"))
        print(c(C.YELLOW + C.BOLD, "  ╚══════════════════════════════════════════╝"))
        print()
        print(c(C.WHITE,    f"  📞 To      : {masked}"))
        print(c(C.WHITE,    f"  💬 Message : {msg}"))
        print(c(C.DIM,      f"  📝 Length  : {len(msg)} chars"))
        print()
        print(c(C.LIME + C.BOLD,  "  ✅ Bhejne ke liye: yes / haan / send"))
        print(c(C.RED,             "  ❌ Cancel ke liye: no / nahi / cancel"))
        print()
        speak("Confirm karo Boss.")

    elif step == "confirm":
        if user_input.lower() in ("yes", "haan", "ha", "send", "bhejo", "ok", "y"):
            num = _sms_state["number"]
            msg = _sms_state["message"]
            _sms_state["active"] = False
            _sms_state["step"]   = None
            masked = "*" * len(num[:-4]) + num[-4:]

            print(c(C.DIM, "  📤 Sending ..."))
            try:
                import subprocess as _sp
                result = _sp.run(
                    ["termux-sms-send", "-n", num, msg],
                    capture_output=True, text=True, timeout=15
                )
                if result.returncode == 0:
                    print(c(C.LIME + C.BOLD, f"  ✅ SMS bhej diya Boss!"))
                    print(c(C.DIM,            f"  📞 To: {masked}"))
                    speak("SMS bhej diya Boss!")
                else:
                    err = result.stderr.strip() or "Unknown error"
                    print(c(C.RED, f"  ✗ SMS fail: {err}"))
                    print(c(C.DIM,  "  termux-sms-send kaam nahi kar raha — SMS permission check karo."))
                    speak("SMS bhejne mein error aaya Boss.")
            except FileNotFoundError:
                print(c(C.RED,  "  ✗ termux-sms-send nahi mila!"))
                print(c(C.DIM,  "  Install: pkg install termux-api"))
                print(c(C.DIM,  "  Phir: Termux app mein SMS permission dena"))
                speak("Termux API install nahi hai Boss.")
            except Exception as e:
                print(c(C.RED, f"  ✗ Error: {e}"))
            print()

        elif user_input.lower() in ("no", "nahi", "na", "cancel", "mat bhejo"):
            _sms_state["active"] = False
            _sms_state["step"]   = None
            print(c(C.DIM, "  SMS cancel ho gaya."))
            speak("Theek hai Boss, SMS cancel.")
        else:
            print(c(C.DIM, "  'yes' ya 'no' type karo."))

# ──────────────────────────────────────────────────────────
#  STOCK PRICE
# ──────────────────────────────────────────────────────────

# Popular stock shortcuts
STOCK_ALIASES = {
    # US Tech
    "apple":      "AAPL",  "aapl":   "AAPL",
    "google":     "GOOGL", "googl":  "GOOGL", "alphabet": "GOOGL",
    "microsoft":  "MSFT",  "msft":   "MSFT",
    "amazon":     "AMZN",  "amzn":   "AMZN",
    "tesla":      "TSLA",  "tsla":   "TSLA",
    "meta":       "META",  "facebook":"META",
    "netflix":    "NFLX",  "nflx":   "NFLX",
    "nvidia":     "NVDA",  "nvda":   "NVDA",
    "samsung":    "005930.KS",
    # Indian stocks (NSE)
    "tcs":        "TCS.NS",
    "reliance":   "RELIANCE.NS",
    "infosys":    "INFY.NS",    "infy": "INFY.NS",
    "wipro":      "WIPRO.NS",
    "hdfc":       "HDFCBANK.NS",
    "sbi":        "SBIN.NS",
    "tata":       "TATAMOTORS.NS",
    "adani":      "ADANIENT.NS",
    "bajaj":      "BAJFINANCE.NS",
    "itc":        "ITC.NS",
    "hul":        "HINDUNILVR.NS",
    "airtel":     "BHARTIARTL.NS",
    # Indices
    "sensex":     "^BSESN",
    "nifty":      "^NSEI",
    "dow":        "^DJI",
    "nasdaq":     "^IXIC",
    "s&p":        "^GSPC",   "sp500": "^GSPC",
}

def show_stock_price(symbols: list) -> None:
    from urllib.request import urlopen, Request
    import json as _json

    print(c(C.DIM, "  📡 Fetching stock prices ..."))
    print()

    results = []
    for sym in symbols[:6]:  # max 6
        ticker = STOCK_ALIASES.get(sym.lower(), sym.upper())
        # Add .NS for Indian stocks if no suffix
        if "." not in ticker and "^" not in ticker and len(ticker) <= 5:
            # Try as-is first (US), then .NS
            pass

        try:
            url  = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=2d"
            req  = Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept":     "application/json",
            })
            data   = _json.loads(urlopen(req, timeout=8).read().decode())
            meta   = data["chart"]["result"][0]["meta"]

            price       = meta.get("regularMarketPrice", 0)
            prev_close  = meta.get("chartPreviousClose", meta.get("previousClose", price))
            currency    = meta.get("currency", "USD")
            name        = meta.get("shortName", ticker)
            exchange    = meta.get("exchangeName", "")
            mkt_state   = meta.get("marketState", "")

            change      = price - prev_close
            chg_pct     = (change / prev_close * 100) if prev_close else 0

            results.append({
                "ticker":   ticker,
                "name":     name[:22],
                "price":    price,
                "change":   change,
                "chg_pct":  chg_pct,
                "currency": currency,
                "exchange": exchange,
                "state":    mkt_state,
            })
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})

    if not results:
        print(c(C.RED, "  ✗ Stock data fetch nahi hua."))
        return

    print(c(C.LIME + C.BOLD,  "  📈 STOCK PRICES"))
    print(c(C.LIME,            "  " + "─" * 58))
    print()

    for r in results:
        if "error" in r:
            print(c(C.RED, f"  ✗ {r['ticker']}: nahi mila"))
            continue

        price    = r["price"]
        change   = r["change"]
        chg_pct  = r["chg_pct"]
        currency = r["currency"]
        arrow    = "▲" if change >= 0 else "▼"
        chg_col  = C.LIME if change >= 0 else C.RED

        # Currency symbol
        curr_sym = {"USD": "$", "INR": "₹", "EUR": "€", "GBP": "£", "KRW": "₩"}.get(currency, currency + " ")

        # Format price
        if price >= 1000:   p_str = f"{curr_sym}{price:,.2f}"
        elif price >= 1:    p_str = f"{curr_sym}{price:.2f}"
        else:               p_str = f"{curr_sym}{price:.4f}"

        state_icon = "🟢" if r["state"] == "REGULAR" else "🔴" if r["state"] == "CLOSED" else "🟡"

        print(c(C.WHITE + C.BOLD, f"  {state_icon} {r['ticker']:<10}") +
              c(C.DIM,             f"{r['name']:<24}") +
              c(C.YELLOW + C.BOLD, f"{p_str:>12}") +
              c(chg_col + C.BOLD,  f"  {arrow}{abs(chg_pct):.2f}%"))

    print()
    print(c(C.LIME, "  " + "─" * 58))
    print(c(C.DIM,  "  🟢 Market Open  🔴 Closed  🟡 Pre/After Hours"))
    print(c(C.DIM,  "  Data: Yahoo Finance"))
    print()

    if results and "error" not in results[0]:
        r = results[0]
        speak(f"{r['ticker']} — {r['price']:,.2f} {r['currency']}. Change {r['chg_pct']:+.2f} percent.")

# ──────────────────────────────────────────────────────────
#  GOLD & SILVER PRICE
# ──────────────────────────────────────────────────────────

def show_gold_price() -> None:
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode
    import json as _json

    print(c(C.DIM, "  📡 Fetching gold & silver prices ..."))
    print()

    gold_usd = silver_usd = None

    # Single CoinGecko call for both gold (PAXG) and silver (XAUT/jpool)
    try:
        params = urlencode({"ids": "pax-gold,silver--2", "vs_currencies": "usd"})
        url    = f"https://api.coingecko.com/api/v3/simple/price?{params}"
        req    = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data   = _json.loads(urlopen(req, timeout=8).read().decode())
        if "pax-gold" in data:
            gold_usd = float(data["pax-gold"]["usd"])
    except Exception:
        pass

    # Gold fallback — separate call if combined failed
    if not gold_usd:
        try:
            params = urlencode({"ids": "pax-gold", "vs_currencies": "usd"})
            url    = f"https://api.coingecko.com/api/v3/simple/price?{params}"
            req    = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data   = _json.loads(urlopen(req, timeout=8).read().decode())
            if "pax-gold" in data:
                gold_usd = float(data["pax-gold"]["usd"])
        except Exception:
            pass

    # Gold fallback 2 — metals.live
    if not gold_usd:
        try:
            url  = "https://api.metals.live/v1/spot"
            req  = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = _json.loads(urlopen(req, timeout=8).read().decode())
            if isinstance(data, list):
                for item in data:
                    if "gold"   in item and not gold_usd:   gold_usd   = float(item["gold"])
                    if "silver" in item and not silver_usd: silver_usd = float(item["silver"])
        except Exception:
            pass

    # Silver — use exchangerate/commodity endpoint
    if not silver_usd:
        try:
            # silver XAG via frankfurter (free)
            url  = "https://api.frankfurter.app/latest?from=XAG&to=USD"
            req  = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = _json.loads(urlopen(req, timeout=6).read().decode())
            sv   = float(data.get("rates", {}).get("USD", 0))
            if sv > 1:   # XAG rate is per oz, should be ~$34
                silver_usd = sv
        except Exception:
            pass

    # Silver fallback — Coinbase XAG
    if not silver_usd:
        try:
            url  = "https://api.coinbase.com/v2/prices/XAG-USD/spot"
            req  = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = _json.loads(urlopen(req, timeout=8).read().decode())
            sv   = float(data["data"]["amount"])
            if sv > 1:
                silver_usd = sv
        except Exception:
            pass

    # USD to INR rate
    inr_rate = 86.5
    try:
        url  = "https://api.exchangerate-api.com/v4/latest/USD"
        req  = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = _json.loads(urlopen(req, timeout=5).read().decode())
        inr_rate = float(data["rates"].get("INR", 86.5))
    except Exception:
        pass

    if not gold_usd:
        print(c(C.RED, "  ✗ Gold price fetch nahi hua."))
        print(c(C.DIM, "  Internet check karo ya thodi der baad try karo."))
        print()
        return

    # Sanity check — gold should be between $1000 and $10000
    if gold_usd > 10000 or gold_usd < 1000:
        print(c(C.RED, f"  ✗ Price data galat lag raha hai (${gold_usd:,.0f}). Thodi der baad try karo."))
        print()
        return

    # 1 troy oz = 31.1035g, 1 tola = 11.6638g
    gold_g_usd    = gold_usd   / 31.1035
    gold_10g_usd  = gold_g_usd * 10
    gold_tola_usd = gold_g_usd * 11.6638
    gold_g_inr    = gold_g_usd    * inr_rate
    gold_10g_inr  = gold_10g_usd  * inr_rate
    gold_tola_inr = gold_tola_usd * inr_rate
    gold_oz_inr   = gold_usd      * inr_rate

    print(c(C.GOLD + C.BOLD,   "  🥇 GOLD & SILVER LIVE PRICE"))
    print(c(C.GOLD,             "  " + "─" * 52))
    print()
    print(c(C.YELLOW + C.BOLD,  "  ══ 🥇 GOLD (XAU) ══"))
    print()
    print(c(C.WHITE,  "  {:<20} {:>12} {:>16}".format("Unit", "USD ($)", "INR (₹)")))
    print(c(C.DIM,    "  " + "─" * 50))

    for label, usd_v, inr_v in [
        ("1 Troy Oz (31.1g)",  gold_usd,      gold_oz_inr),
        ("1 Gram",             gold_g_usd,    gold_g_inr),
        ("10 Gram",            gold_10g_usd,  gold_10g_inr),
        ("1 Tola (11.66g)",    gold_tola_usd, gold_tola_inr),
    ]:
        print(
            c(C.WHITE + C.BOLD, f"  {label:<20}") +
            c(C.YELLOW,          f"${usd_v:>10,.2f}") +
            c(C.CYAN,            f"  ₹{inr_v:>12,.2f}")
        )

    if silver_usd and silver_usd > 1:
        sil_g_usd  = silver_usd / 31.1035
        sil_kg_usd = sil_g_usd  * 1000
        sil_inr    = silver_usd  * inr_rate
        sil_g_inr  = sil_g_usd  * inr_rate
        sil_kg_inr = sil_kg_usd * inr_rate

        print()
        print(c(C.DIM + C.BOLD,  "  ══ 🥈 SILVER (XAG) ══"))
        print()
        for label, usd_v, inr_v in [
            ("1 Troy Oz",   silver_usd, sil_inr),
            ("1 Gram",      sil_g_usd,  sil_g_inr),
            ("1 KG",        sil_kg_usd, sil_kg_inr),
        ]:
            print(
                c(C.WHITE + C.BOLD, f"  {label:<20}") +
                c(C.YELLOW,          f"${usd_v:>10,.2f}") +
                c(C.CYAN,            f"  ₹{inr_v:>12,.2f}")
            )

    print()
    print(c(C.GOLD,  "  " + "─" * 52))
    print(c(C.DIM,   f"  USD/INR: ₹{inr_rate:.2f}  •  Live market data"))
    print()
    speak(f"Sone ka bhav — ek gram {gold_g_inr:,.0f} rupaye. Ek tola {gold_tola_inr:,.0f} rupaye.")

# ──────────────────────────────────────────────────────────
#  CRYPTO LIVE PRICE
# ──────────────────────────────────────────────────────────

CRYPTO_IDS = {
    "btc":      "bitcoin",       "bitcoin":    "bitcoin",
    "eth":      "ethereum",      "ethereum":   "ethereum",
    "bnb":      "binancecoin",   "binance":    "binancecoin",
    "xrp":      "ripple",        "ripple":     "ripple",
    "sol":      "solana",        "solana":     "solana",
    "ada":      "cardano",       "cardano":    "cardano",
    "doge":     "dogecoin",      "dogecoin":   "dogecoin",
    "dot":      "polkadot",      "polkadot":   "polkadot",
    "matic":    "matic-network", "polygon":    "matic-network",
    "ltc":      "litecoin",      "litecoin":   "litecoin",
    "shib":     "shiba-inu",     "shiba":      "shiba-inu",
    "trx":      "tron",          "tron":       "tron",
    "avax":     "avalanche-2",   "avalanche":  "avalanche-2",
    "link":     "chainlink",     "chainlink":  "chainlink",
    "uni":      "uniswap",       "uniswap":    "uniswap",
    "usdt":     "tether",        "tether":     "tether",
    "usdc":     "usd-coin",
}

CRYPTO_SYMBOLS = {
    "bitcoin": "BTC", "ethereum": "ETH", "binancecoin": "BNB",
    "ripple": "XRP", "solana": "SOL", "cardano": "ADA",
    "dogecoin": "DOGE", "polkadot": "DOT", "matic-network": "MATIC",
    "litecoin": "LTC", "shiba-inu": "SHIB", "tron": "TRX",
    "avalanche-2": "AVAX", "chainlink": "LINK", "uniswap": "UNI",
    "tether": "USDT", "usd-coin": "USDC",
}

DEFAULT_CRYPTOS = ["bitcoin", "ethereum", "binancecoin", "ripple", "solana", "dogecoin"]

def show_crypto_price(coins: list = None) -> None:
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode
    import json as _json

    targets = coins if coins else DEFAULT_CRYPTOS
    ids_str = ",".join(targets)

    print(c(C.DIM, "  📡 Fetching live prices ..."))
    print()

    try:
        params = urlencode({"ids": ids_str, "vs_currencies": "usd,inr", "include_24hr_change": "true"})
        url    = f"https://api.coingecko.com/api/v3/simple/price?{params}"
        req    = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data   = _json.loads(urlopen(req, timeout=10).read().decode())

        print(c(C.GOLD + C.BOLD,  "  ₿  CRYPTO LIVE PRICES"))
        print(c(C.GOLD,            "  " + "─" * 56))
        print()
        print(
            c(C.DIM, "  {:<10} {:>12} {:>14} {:>10}".format(
                "Coin", "USD ($)", "INR (₹)", "24h %"))
        )
        print(c(C.DIM, "  " + "─" * 52))

        spoken = []
        for coin_id in targets:
            if coin_id not in data:
                continue
            d       = data[coin_id]
            usd     = d.get("usd", 0)
            inr     = d.get("inr", 0)
            chg     = d.get("usd_24h_change", 0) or 0
            symbol  = CRYPTO_SYMBOLS.get(coin_id, coin_id.upper()[:4])

            # Format price
            def fmt_price(p):
                if p >= 1000:    return f"{p:,.0f}"
                if p >= 1:       return f"{p:.2f}"
                if p >= 0.0001:  return f"{p:.6f}"
                return f"{p:.8f}"

            chg_col  = C.LIME if chg >= 0 else C.RED
            chg_str  = f"{'▲' if chg>=0 else '▼'}{abs(chg):.2f}%"
            usd_str  = f"${fmt_price(usd)}"
            inr_str  = f"₹{fmt_price(inr)}"

            print(
                c(C.WHITE + C.BOLD, f"  {symbol:<10}") +
                c(C.YELLOW,          f"{usd_str:>12}") +
                c(C.CYAN,            f"{inr_str:>14}") +
                c(chg_col + C.BOLD,  f"{chg_str:>10}")
            )
            if len(spoken) < 2:
                spoken.append(f"{symbol} {usd_str}")

        print()
        print(c(C.GOLD, "  " + "─" * 56))
        print(c(C.DIM,  "  Powered by CoinGecko API • Live data"))
        print()

        if spoken:
            speak(f"Crypto prices — {', '.join(spoken)}.")

    except Exception as e:
        print(c(C.RED, f"  ✗ Error: {e}"))
        print(c(C.DIM,  "  Internet check karo ya thodi der baad try karo."))
        print()

# ──────────────────────────────────────────────────────────
#  NUMBER GUESSING GAME
# ──────────────────────────────────────────────────────────

_numgame_state = {
    "active":   False,
    "secret":   0,
    "attempts": 0,
    "max_att":  7,
    "lo":       1,
    "hi":       100,
    "guesses":  [],
}

def numgame_start(lo: int = 1, hi: int = 100) -> None:
    import random as _rnd
    secret = _rnd.randint(lo, hi)
    _numgame_state.update({
        "active":   True,
        "secret":   secret,
        "attempts": 0,
        "max_att":  7,
        "lo":       lo,
        "hi":       hi,
        "guesses":  [],
    })

    print(c(C.MAGENTA + C.BOLD, f"  🎯 Main ne {lo} aur {hi} ke beech ek number socha hai!"))
    print(c(C.WHITE,             f"  Tumhare paas {_numgame_state['max_att']} chances hain."))
    print()
    print(c(C.DIM,               "  Koi number type karo guess karne ke liye!"))
    print(c(C.DIM,               "  'game stop' — band karo"))
    print()
    speak(f"Main ne {lo} aur {hi} ke beech ek number socha hai. Guess karo!")

def numgame_guess(val: str) -> None:
    if not _numgame_state["active"]:
        return

    try:
        guess = int(val.strip())
    except ValueError:
        print(c(C.RED, "  Sirf number type karo!"))
        return

    lo  = _numgame_state["lo"]
    hi  = _numgame_state["hi"]
    if guess < lo or guess > hi:
        print(c(C.RED, f"  {lo} aur {hi} ke beech type karo!"))
        return

    _numgame_state["attempts"] += 1
    _numgame_state["guesses"].append(guess)
    secret  = _numgame_state["secret"]
    att     = _numgame_state["attempts"]
    max_att = _numgame_state["max_att"]
    left    = max_att - att
    diff    = abs(guess - secret)

    # Progress bar of attempts used
    used_bar = "🟥" * att + "⬜" * left

    if guess == secret:
        _numgame_state["active"] = False
        print()
        print(c(C.GOLD + C.BOLD,   "  🎉 SAHI JAWAB! Boss ne guess kar liya!"))
        print(c(C.LIME,             f"  ✨ Number tha: {secret}"))
        print(c(C.CYAN,             f"  🎯 {att} attempts mein guess kiya!"))
        print()
        print(c(C.DIM,              f"  {used_bar}"))
        print()
        if att == 1:
            msg = "Ek hi baar mein! Tum toh mind reader ho Boss! 🤯"
        elif att <= 3:
            msg = "Bahut kam attempts mein! Genius ho! 🧠"
        elif att <= 5:
            msg = "Accha kiya Boss! 👍"
        else:
            msg = "Mushkil se mila lekin mila toh! 😄"
        print(c(C.YELLOW + C.BOLD, f"  {msg}"))
        print()
        speak(f"Sahi jawab! Number tha {secret}. {att} attempts mein guess kiya!")
        return

    # Wrong guess — give hints
    if diff <= 3:
        heat = c(C.RED + C.BOLD,    "  🔥🔥🔥 Bohat GARAM! Bilkul paas ho!")
        hsound = "Bohat garam! Bilkul paas!"
    elif diff <= 10:
        heat = c(C.ORANGE + C.BOLD, "  🔥🔥  Garam! Kaafi paas!")
        hsound = "Garam! Kaafi paas!"
    elif diff <= 25:
        heat = c(C.YELLOW,          "  🌡️  Thoda garam...")
        hsound = "Thoda garam."
    elif diff <= 50:
        heat = c(C.CYAN,            "  ❄️  Thanda hai...")
        hsound = "Thanda hai."
    else:
        heat = c(C.DIM,             "  🧊  Bahut thanda! Door ho!")
        hsound = "Bahut thanda! Door ho!"

    direction = c(C.LIME + C.BOLD, "  ⬆️  Zyada bolo! (Bara number)") if guess < secret \
           else c(C.RED  + C.BOLD, "  ⬇️  Kam bolo! (Chhota number)")

    print()
    print(heat)
    print(direction)
    print(c(C.DIM, f"  {used_bar}  ({left} chances bache)"))
    print()

    speak(f"{hsound} {'Zyada bolo.' if guess < secret else 'Kam bolo.'} {left} chances bache.")

    if left == 0:
        _numgame_state["active"] = False
        print(c(C.RED + C.BOLD,  f"  💀 Oops! Chances khatam! Number tha: {secret}"))
        print(c(C.DIM,            "  Dobara khelne ke liye: number game"))
        print()
        speak(f"Chances khatam Boss! Number tha {secret}. Dobara khelo!")

# ──────────────────────────────────────────────────────────
#  QUIZ / TRIVIA
# ──────────────────────────────────────────────────────────

QUIZ_QUESTIONS = [
    # Science
    {"q": "Paani ka chemical formula kya hai?",                   "opts": ["H2O","CO2","NaCl","O2"],    "ans": 0, "cat": "🔬 Science"},
    {"q": "Insaan ke kitne chromosomes hote hain?",               "opts": ["23","46","48","44"],          "ans": 1, "cat": "🔬 Science"},
    {"q": "Sabse bada planet kaun sa hai?",                       "opts": ["Saturn","Mars","Jupiter","Neptune"], "ans": 2, "cat": "🌌 Space"},
    {"q": "Sound ki speed hawa mein kitni hoti hai?",             "opts": ["343 m/s","1500 m/s","3×10⁸ m/s","220 m/s"], "ans": 0, "cat": "🔬 Science"},
    {"q": "DNA ka full form kya hai?",                            "opts": ["Deoxyribonucleic Acid","Dinitrogen Acid","Dynamic Nucleic Agent","Direct Nucleic Array"], "ans": 0, "cat": "🔬 Science"},
    {"q": "Insaan ke dil mein kitne chambers hote hain?",         "opts": ["2","3","4","6"],              "ans": 2, "cat": "🔬 Science"},
    {"q": "Oxygen ka atomic number kya hai?",                     "opts": ["6","7","8","9"],              "ans": 2, "cat": "🔬 Science"},
    # Geography
    {"q": "Duniya ka sabse bada ocean kaun sa hai?",              "opts": ["Atlantic","Indian","Pacific","Arctic"], "ans": 2, "cat": "🌍 Geography"},
    {"q": "Sabse bada desert kaun sa hai?",                       "opts": ["Sahara","Gobi","Antarctic","Arabian"], "ans": 2, "cat": "🌍 Geography"},
    {"q": "Mount Everest ki height kitni hai?",                   "opts": ["8,488m","8,849m","8,611m","8,516m"], "ans": 1, "cat": "🌍 Geography"},
    {"q": "Nile river kahan hai?",                                "opts": ["Asia","South America","Africa","Europe"], "ans": 2, "cat": "🌍 Geography"},
    {"q": "Sabse chhota country kaun sa hai?",                    "opts": ["Monaco","Nauru","Vatican City","San Marino"], "ans": 2, "cat": "🌍 Geography"},
    {"q": "Amazon river kis country mein hai?",                   "opts": ["Colombia","Peru","Brazil","Venezuela"], "ans": 2, "cat": "🌍 Geography"},
    # History
    {"q": "India ko azadi kab mili?",                             "opts": ["1945","1947","1950","1942"], "ans": 1, "cat": "📜 History"},
    {"q": "World War 2 kab shuru hua?",                           "opts": ["1935","1939","1941","1944"], "ans": 1, "cat": "📜 History"},
    {"q": "Bangladesh ka independence year kya hai?",             "opts": ["1970","1971","1972","1973"], "ans": 1, "cat": "📜 History"},
    {"q": "Taj Mahal kisne banaya?",                              "opts": ["Akbar","Humayun","Shah Jahan","Aurangzeb"], "ans": 2, "cat": "📜 History"},
    # Tech
    {"q": "WWW ka full form kya hai?",                            "opts": ["World Wide Web","World Web Wire","Wide World Web","Web World Wire"], "ans": 0, "cat": "💻 Tech"},
    {"q": "Python programming language kisne banaya?",            "opts": ["Dennis Ritchie","Guido van Rossum","Linus Torvalds","James Gosling"], "ans": 1, "cat": "💻 Tech"},
    {"q": "1 GB mein kitne MB hote hain?",                        "opts": ["512","1000","1024","2048"], "ans": 2, "cat": "💻 Tech"},
    {"q": "Google ka headquarters kahan hai?",                    "opts": ["New York","Seattle","Mountain View","San Francisco"], "ans": 2, "cat": "💻 Tech"},
    {"q": "First computer ka naam kya tha?",                      "opts": ["ENIAC","UNIVAC","IBM-1","Z3"],  "ans": 0, "cat": "💻 Tech"},
    # General
    {"q": "Ek minute mein kitne second hote hain?",               "opts": ["50","60","100","120"],       "ans": 1, "cat": "🧠 General"},
    {"q": "Olympic games kitne saal mein ek baar hote hain?",     "opts": ["2","3","4","5"],             "ans": 2, "cat": "🧠 General"},
    {"q": "Sabse tez animal kaun sa hai?",                        "opts": ["Lion","Cheetah","Leopard","Horse"], "ans": 1, "cat": "🧠 General"},
    {"q": "Shakespeare ka pura naam kya hai?",                    "opts": ["William Shakespeare","Walter Shakespeare","Winston Shakespeare","Warren Shakespeare"], "ans": 0, "cat": "🧠 General"},
    {"q": "Honey bee ek din mein kitne phool visit karti hai?",   "opts": ["100","500","1000","2000"],   "ans": 3, "cat": "🐝 Nature"},
    {"q": "Insaan ke kitne daant hote hain (permanent)?",         "opts": ["28","30","32","34"],          "ans": 2, "cat": "🔬 Science"},
    {"q": "Light ki speed kitni hai?",                            "opts": ["2×10⁸ m/s","3×10⁸ m/s","1×10⁸ m/s","4×10⁸ m/s"], "ans": 1, "cat": "🔬 Science"},
    {"q": "Football World Cup kitne saal mein hota hai?",         "opts": ["2","3","4","5"],             "ans": 2, "cat": "⚽ Sports"},
]

_quiz_state = {
    "active":    False,
    "questions": [],
    "current":   0,
    "score":     0,
    "answered":  False,
}

def quiz_start(count: int = 5) -> None:
    import random as _rnd
    qs = _rnd.sample(QUIZ_QUESTIONS, min(count, len(QUIZ_QUESTIONS)))
    _quiz_state.update({
        "active":    True,
        "questions": qs,
        "current":   0,
        "score":     0,
        "answered":  False,
    })
    _quiz_show_question()

def _quiz_show_question() -> None:
    idx  = _quiz_state["current"]
    qs   = _quiz_state["questions"]
    if idx >= len(qs):
        _quiz_finish()
        return

    q      = qs[idx]
    total  = len(qs)
    score  = _quiz_state["score"]
    _quiz_state["answered"] = False

    print(c(C.CYAN + C.BOLD,  f"  Question {idx+1}/{total}   Score: {score}/{idx}   {q['cat']}"))
    print(c(C.CYAN,            "  " + "─" * 50))
    print()
    print(c(C.WHITE + C.BOLD, f"  ❓ {q['q']}"))
    print()
    for i, opt in enumerate(q["opts"], 1):
        opt_colors = [C.LIME, C.YELLOW, C.ORANGE, C.PINK]
        print(c(opt_colors[i-1] + C.BOLD, f"     {i}. {opt}"))
    print()
    print(c(C.DIM, "  Jawab do: 1 / 2 / 3 / 4   ya   'quiz stop' to quit"))
    print()
    speak(q["q"])

def quiz_answer(ans: str) -> None:
    if not _quiz_state["active"]:
        print(c(C.DIM, "  Quiz nahi chal rahi. Type karo: quiz"))
        return
    if _quiz_state["answered"]:
        return

    idx = _quiz_state["current"]
    q   = _quiz_state["questions"][idx]

    try:
        choice = int(ans.strip()) - 1
        if choice < 0 or choice >= len(q["opts"]):
            raise ValueError
    except ValueError:
        print(c(C.RED, "  ✗ 1, 2, 3 ya 4 type karo!"))
        return

    _quiz_state["answered"] = True
    correct = q["ans"]

    if choice == correct:
        _quiz_state["score"] += 1
        print(c(C.LIME + C.BOLD, "  ✅ Sahi jawab! Shabash Boss! 🎉"))
        speak("Sahi jawab! Shabash!")
    else:
        print(c(C.RED + C.BOLD,  "  ❌ Galat!"))
        print(c(C.YELLOW,         f"  ✔ Sahi jawab tha: {q['opts'][correct]}"))
        speak(f"Galat! Sahi jawab tha — {q['opts'][correct]}")

    print()
    _quiz_state["current"] += 1

    import time as _t
    _t.sleep(1.2)

    if _quiz_state["current"] >= len(_quiz_state["questions"]):
        _quiz_finish()
    else:
        _quiz_show_question()

def _quiz_finish() -> None:
    score = _quiz_state["score"]
    total = len(_quiz_state["questions"])
    pct   = int(score / total * 100)
    _quiz_state["active"] = False

    if pct == 100:    grade, msg = "🏆 PERFECT!", "Aap champion hain Boss!"
    elif pct >= 80:   grade, msg = "🌟 Excellent!", "Bahut badhiya!"
    elif pct >= 60:   grade, msg = "👍 Good!",      "Acha kiya Boss!"
    elif pct >= 40:   grade, msg = "📚 Keep Going!", "Thoda aur padhna padega!"
    else:             grade, msg = "💪 Try Again!",  "Koi baat nahi, agli baar better!"

    print()
    print(c(C.GOLD + C.BOLD,   "  ╔══════════════════════════════════════╗"))
    print(c(C.GOLD + C.BOLD,   "  ║         🎯  QUIZ COMPLETE!          ║"))
    print(c(C.GOLD + C.BOLD,   "  ╚══════════════════════════════════════╝"))
    print()
    print(c(C.WHITE + C.BOLD,  f"  Score   : {score} / {total}"))
    print(c(C.YELLOW + C.BOLD, f"  Grade   : {grade}"))
    print(c(C.LIME,             f"  {msg}"))
    print()

    # Bar
    filled = int(pct / 10)
    bar    = "█" * filled + "░" * (10 - filled)
    print(c(C.CYAN + C.BOLD,   f"  [{bar}] {pct}%"))
    print()
    speak(f"Quiz khatam Boss! Score {score} out of {total}. {msg}")

# ──────────────────────────────────────────────────────────
#  COUNTRY INFO
# ──────────────────────────────────────────────────────────

def show_country_info(country_name: str) -> None:
    print(c(C.DIM, f"  🔍 Searching: {country_name} ..."))
    print()

    try:
        from urllib.request import urlopen, Request
        from urllib.parse import quote
        import json as _json

        url  = f"https://restcountries.com/v3.1/name/{quote(country_name)}?fullText=false"
        req  = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = _json.loads(urlopen(req, timeout=8).read().decode())

        c_data = data[0]

        # Extract fields
        name       = c_data.get("name", {}).get("common", country_name.title())
        official   = c_data.get("name", {}).get("official", "")
        capital    = ", ".join(c_data.get("capital", ["?"]))
        region     = c_data.get("region", "?")
        subregion  = c_data.get("subregion", "")
        population = c_data.get("population", 0)
        area       = c_data.get("area", 0)
        flag_emoji = c_data.get("flag", "🏳")
        languages  = ", ".join(c_data.get("languages", {}).values())
        currencies = ", ".join(
            f"{v.get('name','?')} ({v.get('symbol','?')})"
            for v in c_data.get("currencies", {}).values()
        )
        timezones  = ", ".join(c_data.get("timezones", [])[:3])
        calling    = "+".join(
            c_data.get("idd", {}).get("suffixes", ["?"])[:2]
        )
        calling    = c_data.get("idd", {}).get("root", "") + (
            c_data.get("idd", {}).get("suffixes", [""])[0] if c_data.get("idd", {}).get("suffixes") else ""
        )
        borders    = ", ".join(c_data.get("borders", [])[:6]) or "None / Island"
        tld        = ", ".join(c_data.get("tld", []))
        independent = "✅ Yes" if c_data.get("independent") else "❌ No"
        un_member   = "✅ Yes" if c_data.get("unMember")    else "❌ No"
        landlocked  = "Yes 🏔️" if c_data.get("landlocked") else "No 🌊"

        # Format population
        def fmt_num(n):
            if n >= 1_000_000_000: return f"{n/1_000_000_000:.2f}B"
            if n >= 1_000_000:     return f"{n/1_000_000:.2f}M"
            if n >= 1_000:         return f"{n/1_000:.1f}K"
            return str(n)

        print(c(C.WHITE + C.BOLD, f"  {flag_emoji}  {name.upper()}"))
        if official and official != name:
            print(c(C.DIM,        f"     {official}"))
        print()
        print(c(C.TEAL,           "  " + "─" * 50))
        print()

        def row(label, value, col=C.WHITE):
            print(c(C.YELLOW,        f"  {label:<18}: ") + c(col, value))

        row("🏙️  Capital",       capital)
        row("🌍 Region",         f"{region}" + (f" / {subregion}" if subregion else ""))
        row("👥 Population",     fmt_num(population))
        row("📐 Area",           f"{area:,.0f} km²" if area else "?")
        row("🗣️  Languages",     languages or "?")
        row("💰 Currency",       currencies or "?")
        row("🕐 Timezone",       timezones or "?")
        row("📞 Calling Code",   calling or "?")
        row("🌐 TLD",            tld or "?")
        row("🏳️  Borders",       borders)
        row("🔒 Landlocked",     landlocked)
        row("🇺🇳 UN Member",     un_member)

        print()
        print(c(C.TEAL + C.BOLD, "  " + "═" * 50))
        print()

        speak(f"{name}. Capital {capital}. Population {fmt_num(population)}. Region {region}.")

    except Exception as e:
        err = str(e)
        if "404" in err:
            print(c(C.RED,   f"  ✗ '{country_name}' nahi mila. Spelling check karo."))
            print(c(C.DIM,   "  Example: country info france  ya  country india"))
        else:
            print(c(C.RED,   f"  ✗ Error: {e}"))
            print(c(C.DIM,   "  Internet check karo."))
        print()

# ──────────────────────────────────────────────────────────
#  TIMEZONE / WORLD CLOCK
# ──────────────────────────────────────────────────────────

# City → (timezone_name, UTC_offset_hours, flag)
CITY_TZ = {
    # South Asia
    "dhaka":         ("Asia/Dhaka",        6.0,  "🇧🇩"),
    "bangladesh":    ("Asia/Dhaka",        6.0,  "🇧🇩"),
    "kolkata":       ("Asia/Kolkata",      5.5,  "🇮🇳"),
    "mumbai":        ("Asia/Kolkata",      5.5,  "🇮🇳"),
    "delhi":         ("Asia/Kolkata",      5.5,  "🇮🇳"),
    "india":         ("Asia/Kolkata",      5.5,  "🇮🇳"),
    "karachi":       ("Asia/Karachi",      5.0,  "🇵🇰"),
    "pakistan":      ("Asia/Karachi",      5.0,  "🇵🇰"),
    "kathmandu":     ("Asia/Kathmandu",    5.75, "🇳🇵"),
    "nepal":         ("Asia/Kathmandu",    5.75, "🇳🇵"),
    "colombo":       ("Asia/Colombo",      5.5,  "🇱🇰"),
    # Middle East
    "dubai":         ("Asia/Dubai",        4.0,  "🇦🇪"),
    "uae":           ("Asia/Dubai",        4.0,  "🇦🇪"),
    "riyadh":        ("Asia/Riyadh",       3.0,  "🇸🇦"),
    "saudi":         ("Asia/Riyadh",       3.0,  "🇸🇦"),
    "doha":          ("Asia/Qatar",        3.0,  "🇶🇦"),
    "qatar":         ("Asia/Qatar",        3.0,  "🇶🇦"),
    "kuwait":        ("Asia/Kuwait",       3.0,  "🇰🇼"),
    "tehran":        ("Asia/Tehran",       3.5,  "🇮🇷"),
    # East Asia
    "tokyo":         ("Asia/Tokyo",        9.0,  "🇯🇵"),
    "japan":         ("Asia/Tokyo",        9.0,  "🇯🇵"),
    "beijing":       ("Asia/Shanghai",     8.0,  "🇨🇳"),
    "shanghai":      ("Asia/Shanghai",     8.0,  "🇨🇳"),
    "china":         ("Asia/Shanghai",     8.0,  "🇨🇳"),
    "seoul":         ("Asia/Seoul",        9.0,  "🇰🇷"),
    "korea":         ("Asia/Seoul",        9.0,  "🇰🇷"),
    "singapore":     ("Asia/Singapore",    8.0,  "🇸🇬"),
    "bangkok":       ("Asia/Bangkok",      7.0,  "🇹🇭"),
    "jakarta":       ("Asia/Jakarta",      7.0,  "🇮🇩"),
    "kuala lumpur":  ("Asia/Kuala_Lumpur", 8.0,  "🇲🇾"),
    # Europe
    "london":        ("Europe/London",     0.0,  "🇬🇧"),
    "uk":            ("Europe/London",     0.0,  "🇬🇧"),
    "paris":         ("Europe/Paris",      1.0,  "🇫🇷"),
    "berlin":        ("Europe/Berlin",     1.0,  "🇩🇪"),
    "germany":       ("Europe/Berlin",     1.0,  "🇩🇪"),
    "moscow":        ("Europe/Moscow",     3.0,  "🇷🇺"),
    "russia":        ("Europe/Moscow",     3.0,  "🇷🇺"),
    "istanbul":      ("Europe/Istanbul",   3.0,  "🇹🇷"),
    "turkey":        ("Europe/Istanbul",   3.0,  "🇹🇷"),
    # Americas
    "new york":      ("America/New_York",  -5.0, "🇺🇸"),
    "usa":           ("America/New_York",  -5.0, "🇺🇸"),
    "los angeles":   ("America/Los_Angeles",-8.0,"🇺🇸"),
    "chicago":       ("America/Chicago",  -6.0,  "🇺🇸"),
    "toronto":       ("America/Toronto",  -5.0,  "🇨🇦"),
    "canada":        ("America/Toronto",  -5.0,  "🇨🇦"),
    "sao paulo":     ("America/Sao_Paulo",-3.0,  "🇧🇷"),
    # Africa / Oceania
    "cairo":         ("Africa/Cairo",      2.0,  "🇪🇬"),
    "egypt":         ("Africa/Cairo",      2.0,  "🇪🇬"),
    "nairobi":       ("Africa/Nairobi",    3.0,  "🇰🇪"),
    "sydney":        ("Australia/Sydney",  11.0, "🇦🇺"),
    "australia":     ("Australia/Sydney",  11.0, "🇦🇺"),
    "auckland":      ("Pacific/Auckland",  13.0, "🇳🇿"),
}

def show_world_clock(cities: list = None) -> None:
    utc_now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    def get_city_time(city_key: str):
        info = CITY_TZ.get(city_key.lower().strip())
        if not info:
            return None
        tz_name, offset, flag = info
        # Try pytz first
        try:
            import pytz as _pytz
            tz   = _pytz.timezone(tz_name)
            local = datetime.datetime.now(_pytz.utc).astimezone(tz)
            return local, flag, tz_name, offset
        except ImportError:
            # Manual offset fallback
            h   = int(offset)
            m   = int((abs(offset) - abs(h)) * 60)
            td  = datetime.timedelta(hours=h, minutes=m if offset >= 0 else -m)
            local = utc_now + td
            return local, flag, tz_name, offset

    # Default cities if none given
    if not cities:
        cities = ["dhaka", "dubai", "london", "new york", "tokyo", "sydney"]

    print(c(C.TEAL + C.BOLD, "  🌍 WORLD CLOCK"))
    print(c(C.TEAL,           "  " + "─" * 50))
    print()

    found_any = False
    for city in cities:
        result = get_city_time(city)
        if not result:
            print(c(C.RED, f"  ✗ '{city}' nahi mila."))
            continue
        local, flag, tz_name, offset = result
        found_any = True

        time_str = local.strftime("%I:%M %p")
        date_str = local.strftime("%a, %d %b %Y")
        off_str  = f"UTC{'+' if offset >= 0 else ''}{offset:g}"

        # Day/Night icon
        hour = local.hour
        if 6 <= hour < 12:    tod = "🌅"
        elif 12 <= hour < 17: tod = "☀️ "
        elif 17 <= hour < 20: tod = "🌆"
        elif 20 <= hour < 24: tod = "🌙"
        else:                  tod = "🌃"

        print(
            c(C.WHITE + C.BOLD, f"  {flag}  {city.title():<16}") +
            c(C.LIME + C.BOLD,  f"  {tod}  {time_str}") +
            c(C.DIM,            f"  {date_str}  ({off_str})")
        )

    print()
    print(c(C.TEAL, "  " + "─" * 50))
    print()

    if found_any:
        first = cities[0]
        r = get_city_time(first)
        if r:
            speak(f"{first.title()} mein abhi {r[0].strftime('%I:%M %p')} baj rahe hain Boss.")

# ──────────────────────────────────────────────────────────
#  RIDDLES / PAHELIYAN
# ──────────────────────────────────────────────────────────

RIDDLES = [
    {"q": "Jitna khaao utna badhta hai, lekin paani daalo toh khatam ho jaata hai. Kya hoon main?", "a": "Aag 🔥"},
    {"q": "Bina pair ke chalta hoon, bina haath ke pakadta hoon. Kya hoon main?", "a": "Paani / Darya 💧"},
    {"q": "Din mein sota hoon, raat mein jaagta hoon. Kya hoon main?", "a": "Tara / Star ⭐"},
    {"q": "Ek kamra hai jisme na darwaza, na khidki, phir bhi log andar jaate hain. Kya hai?", "a": "Mushroom / Khumbi 🍄"},
    {"q": "Main woh cheez hoon jo tumhare paas hoti hai lekin dusron ko dete ho. Kya hoon?", "a": "Apna Naam 📛"},
    {"q": "Jitna khaata hai utna bada hota hai, lekin kuch nahi peeta. Kya hoon main?", "a": "Aandhi / Storm 🌪️"},
    {"q": "Bolta nahi, lekin sab kuch bata deta hai. Kya hoon main?", "a": "Aaina / Mirror 🪞"},
    {"q": "Hazaron daant hain lekin kuch bhi khata nahi. Kya hoon main?", "a": "Kangha / Comb 🪮"},
    {"q": "Upar se aankhein hain, neeche se pair hain, lekin na dekh sakta, na chal sakta. Kya hoon?", "a": "Aloo / Potato 🥔"},
    {"q": "Ek cheez jo bechne par khareedne wale ko nahi milti, lekin kharidne wale ko zaroor milti hai. Kya hai?", "a": "Aqal / Wisdom 🧠"},
    {"q": "Jab main naya hota hoon toh chhota, jab bada hoon toh gol. Kya hoon main?", "a": "Chaand / Moon 🌙"},
    {"q": "Andar se geela, bahar se sukha. Kya hoon main?", "a": "Zabaan / Tongue 👅"},
    {"q": "Sone se pehle aata hoon, jaagne ke baad bhi hoon. Kya hoon main?", "a": "Aankhein band karna / Darkness 🌑"},
    {"q": "Pani mein rehta hoon lekin bheegta nahi. Kya hoon main?", "a": "Saaya / Shadow 🌊"},
    {"q": "Jitna use karo utna chhota hota jaata hai. Kya hoon main?", "a": "Sabun / Soap 🧼"},
    {"q": "Ek baar marta hoon lekin hazaron saalo tak jeeta hoon. Kya hoon main?", "a": "Kitaab / Book 📚"},
    {"q": "Duniya mein sabse tez kya hai?", "a": "Soch / Thought 💭"},
    {"q": "Na hath, na pair, phir bhi ghar mein ghus jaata hoon. Kya hoon main?", "a": "Roshni / Light 💡"},
    {"q": "Jab bhi gira, toot nahi sakta. Kya hoon main?", "a": "Paani ka boolbula / Water Bubble 💧"},
    {"q": "Saari duniya use dekhti hai lekin woh kisi ko nahi dekhta. Kya hoon main?", "a": "Suraj / Sun ☀️"},
    {"q": "Jitna zyada sukhata hoon utna zyada geela ho jaata hoon. Kya hoon main?", "a": "Towel 🏖️"},
    {"q": "Ek taraf se andar jaata hoon, doosri taraf se bahar aata hoon, phir bhi andar hi rehta hoon. Kya hoon?", "a": "Haath mein dhaaga / Thread in needle 🧵"},
    {"q": "Subah 4 pair, dopahar 2 pair, shaam 3 pair. Kya hoon main?", "a": "Insaan / Human 🧑"},
    {"q": "Jitna bada, utna halka. Kya hoon main?", "a": "Phool / Balloon 🎈"},
    {"q": "Na khaata, na peeta, phir bhi saal bhar jeeta. Kya hoon main?", "a": "Ghadi / Clock ⏰"},
]

_riddle_state = {"current": None, "answered": False}

def show_riddle() -> None:
    import random as _rnd
    riddle = _rnd.choice(RIDDLES)
    _riddle_state["current"] = riddle
    _riddle_state["answered"] = False

    print(c(C.YELLOW + C.BOLD, "  🧩 PAHELI"))
    print(c(C.YELLOW,           "  " + "─" * 50))
    print()

    # Word wrap
    words = riddle["q"].split()
    line  = "  "
    for w in words:
        if len(line) + len(w) + 1 > 62:
            print(c(C.WHITE + C.BOLD, line))
            line = "  " + w + " "
        else:
            line += w + " "
    if line.strip():
        print(c(C.WHITE + C.BOLD, line))

    print()
    print(c(C.DIM, "  Jawab jaante ho? Type karo: jawab  ya  answer"))
    print()
    print(c(C.YELLOW + C.BOLD, "  " + "═" * 50))
    print()
    speak(riddle["q"])

def show_riddle_answer() -> None:
    if not _riddle_state.get("current"):
        print(c(C.YELLOW, "  Pehle ek paheli lo! Type karo: riddle"))
        return
    if _riddle_state["answered"]:
        print(c(C.DIM, "  Yeh paheli pehle hi answer ho chuki. Naya: riddle"))
        return

    riddle = _riddle_state["current"]
    _riddle_state["answered"] = True

    print(c(C.LIME + C.BOLD,  "  ✅ JAWAB HAI:"))
    print()
    print(c(C.LIME + C.BOLD,  f"  👉 {riddle['a']}"))
    print()
    print(c(C.DIM,             "  Naya chahiye? Type karo: riddle"))
    print()
    speak(f"Jawab hai — {riddle['a']}")

# ──────────────────────────────────────────────────────────
#  FUN FACTS
# ──────────────────────────────────────────────────────────

FUN_FACTS = [
    "🐙 Octopuses have three hearts, nine brains, and blue blood!",
    "🍯 Honey never spoils — 3000-year-old honey found in Egyptian tombs is still edible!",
    "⚡ A bolt of lightning is 5 times hotter than the surface of the sun!",
    "🐘 Elephants are the only animals that can't jump.",
    "🌊 The ocean produces over 50% of the world's oxygen.",
    "🧠 Your brain uses about 20% of your body's total energy.",
    "🦷 Tooth enamel is the hardest substance in the human body.",
    "🌍 There are more trees on Earth than stars in the Milky Way galaxy.",
    "🐬 Dolphins sleep with one eye open.",
    "🦋 Butterflies taste with their feet.",
    "🐌 A snail can sleep for 3 years straight!",
    "🌵 A cactus is not a tree — it's a succulent!",
    "🔊 Sound travels 4x faster in water than in air.",
    "🦈 Sharks are older than trees — they've existed for over 450 million years!",
    "🍌 Bananas are radioactive due to naturally occurring potassium-40.",
    "🐧 Penguins propose to their mates with pebbles.",
    "👁️ Your eyes can distinguish around 10 million different colors.",
    "🌙 The Moon is moving away from Earth at about 3.8 cm per year.",
    "🦴 A human has the same number of neck vertebrae as a giraffe — 7!",
    "🎵 Music can reduce anxiety by up to 65%, studies show.",
    "🐝 Honey bees can recognize human faces.",
    "🌈 A day on Venus is longer than a year on Venus.",
    "🧊 Hot water can freeze faster than cold water — called the Mpemba effect!",
    "🐘 Elephants are the only animals with 4 knees.",
    "🦠 There are more bacteria in your mouth than people on Earth.",
    "🌺 Sunflowers can remove radioactive waste from soil — used after Chernobyl!",
    "🐟 Clownfish can change their gender — all are born male!",
    "💧 It takes about 2,700 liters of water to make one cotton T-shirt.",
    "🌋 Hawaii is moving toward Japan at 10 cm per year.",
    "🕷️ Spiders can't fly — but they can travel hundreds of miles using silk as a parachute!",
    "🦁 Lions sleep up to 20 hours a day.",
    "🧲 Earth's magnetic North Pole moves about 55 km per year.",
    "🌿 Grass makes up about 26% of all plant life on Earth.",
    "🐢 A group of flamingos is called a 'flamboyance'.",
    "🦒 Giraffes have no vocal cords — they communicate at frequencies humans can't hear.",
    "🍎 Apples are 25% air — that's why they float in water!",
    "🔭 There are more possible chess games than atoms in the observable universe.",
    "🐙 An octopus can edit its own RNA — changing how its proteins work in cold weather!",
    "🌞 The Sun accounts for 99.86% of the total mass of the solar system.",
    "🦜 Parrots are the only birds that can eat with their feet.",
    "🧬 If you uncoiled all the DNA in your body, it would stretch 10 billion miles!",
    "🪲 Cockroaches can survive without their head for weeks.",
    "🏔️ Mount Everest grows about 4mm taller every year due to tectonic activity.",
    "🐙 Octopuses have rectangular pupils.",
    "🌊 The Pacific Ocean is wider than the Moon.",
    "🎯 A group of crows is called a 'murder'.",
    "💡 The average person walks about 100,000 miles in their lifetime.",
    "🦅 Eagles can see 4 to 5 times farther than humans.",
    "🧪 Water can boil and freeze at the same time — called the 'triple point'!",
    "🌺 There are more public libraries in the US than McDonald's restaurants.",
    "🐠 Clams have no brain — but have two hearts.",
    "🦊 A fox's tail is called a 'brush'.",
    "📱 The first iPhone was released in 2007 — only 19 years ago!",
    "🎸 Playing guitar for 1 hour burns about 140 calories.",
    "🌱 A single tree can absorb up to 48 pounds of CO2 per year.",
]

def show_fun_fact() -> None:
    import random as _rnd

    # Try API first
    fact_text = None
    try:
        from urllib.request import urlopen, Request
        import json as _json
        req  = Request(
            "https://uselessfacts.jsph.pl/api/v2/facts/random?language=en",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        data = _json.loads(urlopen(req, timeout=5).read().decode())
        fact_text = data.get("text", "").strip()
    except Exception:
        pass

    # Fallback to local
    if not fact_text:
        fact_text = _rnd.choice(FUN_FACTS)

    # Translate to Hinglish via Groq
    try:
        trans = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": (
                    f"Translate this fun fact to Hinglish (Roman Hindi + English mix). "
                    f"Keep it fun, short, and natural. Keep emojis if any. "
                    f"Only return the translated fact, nothing else:\n\n{fact_text}"
                )
            }]
        )
        hinglish = trans.choices[0].message.content.strip()
        if hinglish:
            fact_text = hinglish
    except Exception:
        pass  # Use original if translation fails

    print(c(C.CYAN + C.BOLD,  "  🤓 FUN FACT"))
    print(c(C.CYAN,            "  " + "─" * 50))
    print()

    # Word wrap at ~60 chars
    words = fact_text.split()
    line  = "  "
    lines = []
    for w in words:
        if len(line) + len(w) + 1 > 62:
            lines.append(line)
            line = "  " + w + " "
        else:
            line += w + " "
    if line.strip():
        lines.append(line)

    for ln in lines:
        print(c(C.WHITE + C.BOLD, ln))

    print()
    print(c(C.CYAN + C.BOLD, "  " + "═" * 50))
    print()
    speak(fact_text[:120])

# ──────────────────────────────────────────────────────────
#  THIS DAY IN HISTORY
# ──────────────────────────────────────────────────────────

def show_this_day_in_history() -> None:
    today    = datetime.date.today()
    month    = today.month
    day      = today.day
    date_str = today.strftime("%B %d")

    print(c(C.ORANGE + C.BOLD, f"  📅 {today.strftime('%A, %d %B')} — Aaj ka Itihas"))
    print(c(C.ORANGE,           "  " + "─" * 50))
    print()

    try:
        from urllib.request import urlopen, Request
        from urllib.parse import quote
        import json as _json

        url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{month}/{day}"
        req  = Request(url, headers={"User-Agent": "FridayAI/1.0"})
        data = _json.loads(urlopen(req, timeout=8).read().decode())

        events = data.get("events", [])
        # Pick 5 most interesting (sorted by year variety)
        if len(events) > 5:
            # Spread across history — pick from different eras
            step   = len(events) // 5
            picked = [events[i * step] for i in range(5)]
        else:
            picked = events[:5]

        for i, ev in enumerate(picked, 1):
            year  = ev.get("year", "?")
            text  = ev.get("text", "")
            # Trim long text
            if len(text) > 120:
                text = text[:117] + "..."

            # Era color
            if year < 1500:   ycol = C.DIM
            elif year < 1900: ycol = C.YELLOW
            elif year < 1950: ycol = C.ORANGE
            elif year < 2000: ycol = C.CYAN
            else:              ycol = C.LIME

            print(c(ycol + C.BOLD,  f"  {i}. [{year}]"))
            print(c(C.WHITE,         f"     {text}"))
            print()

        print(c(C.ORANGE + C.BOLD, "  " + "═" * 50))
        print()

        # Voice — first event
        if picked:
            first = picked[0]
            speak(f"Aaj ke din {first.get('year','?')} mein — {first.get('text','')[:80]}.")

    except Exception as e:
        # Offline fallback — hardcoded for today's month/day
        fallback = {
            (3, 9): [
                (1959, "Barbie doll was introduced at the American International Toy Fair in New York City."),
                (1796, "Napoleon Bonaparte married Joséphine de Beauharnais."),
                (1945, "US B-29 bombers launched firebombing raids on Tokyo in World War II."),
                (1976, "Viking 1 entered the orbit of Mars."),
                (2020, "WHO declared COVID-19 a pandemic."),
            ],
        }.get((month, day), [
            (2000, "History is full of amazing events — check again with internet!"),
        ])
        for i, (yr, txt) in enumerate(fallback[:5], 1):
            print(c(C.YELLOW + C.BOLD, f"  {i}. [{yr}]"))
            print(c(C.WHITE,            f"     {txt}"))
            print()
        print(c(C.ORANGE + C.BOLD, "  " + "═" * 50))
        print()
        if fallback:
            speak(f"Aaj ke din {fallback[0][0]} mein — {fallback[0][1][:80]}.")

# ──────────────────────────────────────────────────────────
#  WORD OF THE DAY
# ──────────────────────────────────────────────────────────

WOTD_FILE = "friday_wotd.json"

# Offline fallback words (used if API fails)
WOTD_OFFLINE = [
    {"word": "Serendipity",   "pos": "noun",      "meaning": "The occurrence of events by chance in a happy way",          "example": "Finding that book was pure serendipity.",        "synonyms": ["luck", "fortune", "chance"]},
    {"word": "Ephemeral",     "pos": "adjective", "meaning": "Lasting for a very short time",                              "example": "Fame can be ephemeral.",                         "synonyms": ["transient", "fleeting", "momentary"]},
    {"word": "Eloquent",      "pos": "adjective", "meaning": "Fluent and persuasive in speaking or writing",               "example": "She gave an eloquent speech.",                   "synonyms": ["articulate", "expressive", "well-spoken"]},
    {"word": "Resilience",    "pos": "noun",      "meaning": "The ability to recover quickly from difficulties",           "example": "Her resilience helped her overcome obstacles.",   "synonyms": ["toughness", "strength", "perseverance"]},
    {"word": "Ambiguous",     "pos": "adjective", "meaning": "Open to more than one interpretation; unclear",              "example": "His reply was ambiguous.",                       "synonyms": ["vague", "unclear", "equivocal"]},
    {"word": "Tenacity",      "pos": "noun",      "meaning": "The quality of being very determined",                       "example": "She pursued her goals with tenacity.",            "synonyms": ["persistence", "determination", "resolve"]},
    {"word": "Melancholy",    "pos": "noun",      "meaning": "A feeling of pensive sadness with no obvious cause",         "example": "A sense of melancholy came over him.",           "synonyms": ["sadness", "sorrow", "gloom"]},
    {"word": "Perspicacious", "pos": "adjective", "meaning": "Having a ready insight; shrewd",                             "example": "A perspicacious judge of character.",            "synonyms": ["shrewd", "astute", "perceptive"]},
    {"word": "Ubiquitous",    "pos": "adjective", "meaning": "Present or appearing everywhere",                            "example": "Smartphones are now ubiquitous.",                "synonyms": ["omnipresent", "pervasive", "universal"]},
    {"word": "Pragmatic",     "pos": "adjective", "meaning": "Dealing with things sensibly and realistically",             "example": "We need a pragmatic approach.",                  "synonyms": ["practical", "realistic", "sensible"]},
    {"word": "Loquacious",    "pos": "adjective", "meaning": "Tending to talk a great deal",                               "example": "She was loquacious at parties.",                 "synonyms": ["talkative", "chatty", "garrulous"]},
    {"word": "Fortitude",     "pos": "noun",      "meaning": "Courage in pain or adversity",                               "example": "He bore his illness with fortitude.",            "synonyms": ["courage", "bravery", "endurance"]},
    {"word": "Candid",        "pos": "adjective", "meaning": "Truthful and straightforward; frank",                        "example": "She gave a candid answer.",                      "synonyms": ["frank", "honest", "open"]},
    {"word": "Diligent",      "pos": "adjective", "meaning": "Having or showing care and conscientiousness",               "example": "He was a diligent student.",                     "synonyms": ["hardworking", "industrious", "assiduous"]},
    {"word": "Empathy",       "pos": "noun",      "meaning": "The ability to understand and share feelings of another",   "example": "A doctor needs empathy.",                        "synonyms": ["compassion", "understanding", "sympathy"]},
    {"word": "Verbose",       "pos": "adjective", "meaning": "Using more words than needed",                               "example": "The report was unnecessarily verbose.",          "synonyms": ["wordy", "long-winded", "prolix"]},
    {"word": "Alacrity",      "pos": "noun",      "meaning": "Brisk and cheerful readiness",                               "example": "She accepted with alacrity.",                    "synonyms": ["eagerness", "willingness", "enthusiasm"]},
    {"word": "Nonchalant",    "pos": "adjective", "meaning": "Feeling or appearing casually calm",                         "example": "He seemed nonchalant about the result.",         "synonyms": ["calm", "casual", "indifferent"]},
    {"word": "Sagacious",     "pos": "adjective", "meaning": "Having or showing keen mental discernment",                  "example": "A sagacious leader makes wise choices.",         "synonyms": ["wise", "clever", "intelligent"]},
    {"word": "Inquisitive",   "pos": "adjective", "meaning": "Curious or inquiring",                                       "example": "Children are naturally inquisitive.",            "synonyms": ["curious", "questioning", "probing"]},
    {"word": "Benevolent",    "pos": "adjective", "meaning": "Well meaning and kindly",                                    "example": "A benevolent ruler cares for the people.",       "synonyms": ["kind", "generous", "charitable"]},
    {"word": "Zealous",       "pos": "adjective", "meaning": "Having or showing great energy in pursuit of a cause",      "example": "She was zealous in her work.",                   "synonyms": ["passionate", "fervent", "enthusiastic"]},
    {"word": "Profound",      "pos": "adjective", "meaning": "Very great or intense; having deep insight",                 "example": "A profound silence fell over the room.",         "synonyms": ["deep", "intense", "thoughtful"]},
    {"word": "Vivacious",     "pos": "adjective", "meaning": "Attractively lively and animated",                           "example": "She had a vivacious personality.",               "synonyms": ["lively", "spirited", "animated"]},
    {"word": "Meticulous",    "pos": "adjective", "meaning": "Showing great attention to detail",                          "example": "He was meticulous in his work.",                 "synonyms": ["careful", "precise", "thorough"]},
    {"word": "Acumen",        "pos": "noun",      "meaning": "The ability to make good judgements quickly",                "example": "Her business acumen was impressive.",            "synonyms": ["shrewdness", "insight", "intelligence"]},
    {"word": "Dexterous",     "pos": "adjective", "meaning": "Showing skill in using hands, mind, or body",               "example": "A dexterous craftsman.",                         "synonyms": ["skillful", "adroit", "nimble"]},
    {"word": "Gregarious",    "pos": "adjective", "meaning": "Fond of company; sociable",                                  "example": "He was gregarious and well-liked.",              "synonyms": ["sociable", "outgoing", "friendly"]},
]

def _wotd_get_today() -> dict:
    """Get today's word — from cache or pick from offline list by date"""
    today = str(datetime.date.today())

    # Check cache
    if os.path.exists(WOTD_FILE):
        with open(WOTD_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        if cache.get("date") == today:
            return cache

    # Pick word based on day of year (consistent for the day)
    day_num = datetime.date.today().timetuple().tm_yday
    word_data = WOTD_OFFLINE[day_num % len(WOTD_OFFLINE)]

    # Try to enrich with API
    try:
        from urllib.request import urlopen, Request
        from urllib.parse import quote
        import json as _json

        url  = f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(word_data['word'].lower())}"
        req  = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = _json.loads(urlopen(req, timeout=5).read().decode())

        if isinstance(data, list) and data:
            entry    = data[0]
            phonetic = entry.get("phonetic", "")
            meanings = entry.get("meanings", [])
            if meanings:
                defs = meanings[0].get("definitions", [])
                if defs and defs[0].get("example"):
                    word_data["example"] = defs[0]["example"]
            word_data["phonetic"] = phonetic
    except Exception:
        word_data["phonetic"] = ""

    # Save cache
    result = {**word_data, "date": today}
    with open(WOTD_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result

def show_word_of_the_day() -> None:
    w = _wotd_get_today()

    word     = w.get("word", "")
    pos      = w.get("pos", "")
    meaning  = w.get("meaning", "")
    example  = w.get("example", "")
    synonyms = w.get("synonyms", [])
    phonetic = w.get("phonetic", "")
    today    = datetime.date.today().strftime("%A, %d %B %Y")

    pos_colors = {
        "noun": C.CYAN, "verb": C.LIME, "adjective": C.YELLOW,
        "adverb": C.PINK, "interjection": C.ORANGE,
    }
    pcol = pos_colors.get(pos, C.MAGENTA)

    print(c(C.GOLD + C.BOLD,  f"  📅 {today}"))
    print()
    print(c(C.WHITE + C.BOLD, f"  📖 Word of the Day"))
    print(c(C.GOLD,            "  " + "─" * 46))
    print()
    print(c(C.WHITE + C.BOLD,  f"  ✨  {word.upper()}"), end="")
    if phonetic:
        print(c(C.DIM,         f"  {phonetic}"))
    else:
        print()
    print()
    print(c(pcol + C.BOLD,    f"  [{pos}]"))
    print(c(C.WHITE,           f"  📝 {meaning}"))
    if example:
        print()
        print(c(C.DIM + C.ITALIC, f'  💬 "{example}"'))
    if synonyms:
        print()
        syn_str = ",  ".join(synonyms[:5])
        print(c(C.TEAL,       f"  ✦ Synonyms : ") + c(C.LIME, syn_str))
    print()
    print(c(C.GOLD,            "  " + "═" * 46))
    print()

    speak(f"Word of the day — {word}. Meaning: {meaning}.")

# ──────────────────────────────────────────────────────────
#  SPEEDTEST
# ──────────────────────────────────────────────────────────

def run_speedtest() -> None:
    print(c(C.DIM, "  ⏳ Testing internet speed ..."))
    print()

    try:
        from urllib.request import urlopen, Request
        import time as _time

        # ── PING TEST ──
        print(c(C.DIM, "  📡 Testing ping ..."))
        ping_times = []
        for _ in range(4):
            t0 = _time.time()
            try:
                r = urlopen(Request("https://www.google.com", headers={"User-Agent":"Mozilla/5.0"}), timeout=5)
                r.read(1)
                ping_times.append((_time.time() - t0) * 1000)
            except Exception:
                pass
        ping_ms = min(ping_times) if ping_times else 999

        # ── DOWNLOAD TEST ──
        print(c(C.DIM, "  ⬇  Testing download ..."))
        # Use a reliable public file
        test_urls = [
            "https://speed.cloudflare.com/__down?bytes=10000000",   # 10MB Cloudflare
            "https://httpbin.org/bytes/5000000",                    # 5MB fallback
        ]
        dl_mbps = 0
        for url in test_urls:
            try:
                req   = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                t0    = _time.time()
                resp  = urlopen(req, timeout=15)
                data  = resp.read()
                elapsed = _time.time() - t0
                if elapsed > 0:
                    dl_mbps = (len(data) * 8) / (elapsed * 1_000_000)
                    break
            except Exception:
                continue

        # ── UPLOAD TEST ──
        print(c(C.DIM, "  ⬆  Testing upload ..."))
        ul_mbps = 0
        try:
            import urllib.request as _urllib
            payload = b"x" * 2_000_000  # 2MB upload
            req = _urllib.Request(
                "https://httpbin.org/post",
                data=payload,
                headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/octet-stream"}
            )
            t0   = _time.time()
            resp = _urllib.urlopen(req, timeout=15)
            resp.read()
            elapsed = _time.time() - t0
            if elapsed > 0:
                ul_mbps = (len(payload) * 8) / (elapsed * 1_000_000)
        except Exception:
            ul_mbps = 0

        # ── RESULTS ──
        print()
        print(c(C.TEAL + C.BOLD, "  " + "═" * 46))
        print(c(C.WHITE + C.BOLD, "  📊 SPEED TEST RESULTS"))
        print(c(C.TEAL,           "  " + "─" * 46))
        print()

        # Ping
        if ping_ms < 30:      pcol = C.LIME
        elif ping_ms < 80:    pcol = C.YELLOW
        else:                  pcol = C.RED
        print(c(C.WHITE, "  🏓 Ping      : ") + c(pcol + C.BOLD, f"{ping_ms:.0f} ms"))

        # Download
        if dl_mbps >= 100:    dcol, dq = C.LIME,   "Excellent 🚀"
        elif dl_mbps >= 25:   dcol, dq = C.LIME,   "Good ✅"
        elif dl_mbps >= 10:   dcol, dq = C.YELLOW, "Fair 🟡"
        elif dl_mbps >= 5:    dcol, dq = C.ORANGE, "Slow 🟠"
        elif dl_mbps > 0:     dcol, dq = C.RED,    "Very Slow 🔴"
        else:                  dcol, dq = C.RED,    "Failed ✗"

        bar_d = int(min(dl_mbps, 100) / 5)
        dbar  = "█" * bar_d + "░" * (20 - bar_d)
        print(c(C.WHITE, "  ⬇  Download  : ") + c(dcol + C.BOLD, f"{dl_mbps:.2f} Mbps"))
        print(c(dcol,    f"     [{dbar}] {dq}"))

        # Upload
        if ul_mbps >= 50:     ucol, uq = C.LIME,   "Excellent 🚀"
        elif ul_mbps >= 10:   ucol, uq = C.LIME,   "Good ✅"
        elif ul_mbps >= 5:    ucol, uq = C.YELLOW, "Fair 🟡"
        elif ul_mbps >= 2:    ucol, uq = C.ORANGE, "Slow 🟠"
        elif ul_mbps > 0:     ucol, uq = C.RED,    "Very Slow 🔴"
        else:                  ucol, uq = C.DIM,    "N/A"

        bar_u = int(min(ul_mbps, 50) / 2.5)
        bar_u = max(bar_u, 1) if ul_mbps > 0 else 0
        ubar  = "█" * bar_u + "░" * (20 - bar_u)
        print(c(C.WHITE, "  ⬆  Upload    : ") + c(ucol + C.BOLD, f"{ul_mbps:.2f} Mbps"))
        print(c(ucol,    f"     [{ubar}] {uq}"))

        print()
        print(c(C.TEAL + C.BOLD, "  " + "═" * 46))
        print()

        speak(f"Speed test complete Boss. Download {dl_mbps:.0f} Mbps, Upload {ul_mbps:.0f} Mbps.")

    except Exception as e:
        print(c(C.RED, f"  ✗ Error: {e}"))
        print(c(C.DIM, "  Internet connection check karo."))
        print()

# ──────────────────────────────────────────────────────────
#  NETWORK SCANNER (LAN Device Discovery)
# ──────────────────────────────────────────────────────────

def _get_local_ip() -> str:
    """Get device's local IP address"""
    import socket as _socket
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "192.168.1.1"

def _get_mac(ip: str) -> str:
    """Try to get MAC address from ARP table"""
    try:
        result = subprocess.run(
            ["arp", "-n", ip],
            capture_output=True, text=True, timeout=3
        )
        import re as _re
        m = _re.search(r'([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})', result.stdout)
        return m.group(1) if m else "??:??:??:??:??:??"
    except Exception:
        return "??:??:??:??:??:??"

def _get_hostname(ip: str) -> str:
    """Reverse DNS lookup"""
    import socket as _socket
    try:
        return _socket.gethostbyaddr(ip)[0]
    except Exception:
        return ""

def _ping_check(ip: str) -> bool:
    """Fast single ping check"""
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip],
            capture_output=True, timeout=2
        )
        return result.returncode == 0
    except Exception:
        return False

def network_scan(subnet: str = "") -> None:
    import re as _re

    my_ip = _get_local_ip()

    # Determine subnet to scan
    if not subnet:
        # Auto-detect from local IP
        parts    = my_ip.split(".")
        subnet   = ".".join(parts[:3]) + ".0/24"
        base_ip  = ".".join(parts[:3])
    else:
        # Parse given subnet
        if "/" in subnet:
            base_ip = ".".join(subnet.split("/")[0].split(".")[:3])
        else:
            base_ip = ".".join(subnet.split(".")[:3])

    print(c(C.TEAL + C.BOLD, f"  📡 My IP    : {my_ip}"))
    print(c(C.YELLOW,        f"  🔍 Scanning : {base_ip}.1 – {base_ip}.254"))
    print(c(C.DIM,           f"  ⏳ Please wait (this may take 30–60 sec)..."))
    print()

    alive      = []
    lock       = threading.Lock()
    threads    = []

    def check(i):
        ip = f"{base_ip}.{i}"
        if _ping_check(ip):
            hostname = _get_hostname(ip)
            with lock:
                alive.append((ip, hostname))

    for i in range(1, 255):
        t = threading.Thread(target=check, args=(i,), daemon=True)
        threads.append(t)
        t.start()
        if len(threads) >= 30:
            for th in threads:
                th.join(timeout=3)
            threads = []

    for th in threads:
        th.join(timeout=3)

    # Sort by last octet
    alive.sort(key=lambda x: int(x[0].split(".")[-1]))

    if not alive:
        print(c(C.RED, "  ✗ Koi device nahi mila. WiFi se connected ho?"))
        return

    print(c(C.TEAL + C.BOLD, f"  {'IP ADDRESS':<18} {'HOSTNAME'}"))
    print(c(C.TEAL,           "  " + "─" * 52))

    for ip, hostname in alive:
        is_me = "  ← (You)" if ip == my_ip else ""
        hn    = hostname[:28] if hostname else "—"
        icon  = "📱" if ip == my_ip else "💻"
        print(
            c(C.WHITE + C.BOLD, f"  {icon}  {ip:<16}") +
            c(C.CYAN,           f"  {hn}") +
            c(C.LIME + C.BOLD,  is_me)
        )

    print(c(C.TEAL, "  " + "─" * 52))
    print()
    print(c(C.LIME + C.BOLD, f"  ✅ {len(alive)} device(s) mila LAN pe!"))
    speak(f"Network scan complete. {len(alive)} devices mile Boss.")
    print()

# ──────────────────────────────────────────────────────────
#  PING TOOL
# ──────────────────────────────────────────────────────────

def ping_host(target: str, count: int = 4) -> None:
    import socket as _socket
    import statistics as _stats

    # Resolve
    try:
        host_ip = _socket.gethostbyname(target)
    except Exception:
        print(c(C.RED, f"  ✗ Host resolve nahi hua: '{target}'"))
        return

    print(c(C.CYAN + C.BOLD, f"  🎯 Target   : {target}"))
    if host_ip != target:
        print(c(C.DIM,       f"  🔍 Resolved : {host_ip}"))
    print(c(C.YELLOW,        f"  📦 Packets  : {count}"))
    print()

    times      = []
    sent       = 0
    received   = 0

    for i in range(1, count + 1):
        try:
            start = time.time()
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", host_ip],
                capture_output=True, text=True, timeout=4
            )
            elapsed_ms = (time.time() - start) * 1000
            sent += 1

            if result.returncode == 0:
                received += 1
                times.append(elapsed_ms)
                # Color by latency
                if elapsed_ms < 50:
                    col = C.LIME
                elif elapsed_ms < 150:
                    col = C.YELLOW
                else:
                    col = C.RED
                print(
                    c(C.DIM,         f"  [{i}/{count}] ") +
                    c(C.WHITE,        f"From {host_ip} : ") +
                    c(col + C.BOLD,   f"{elapsed_ms:.1f} ms ") +
                    c(C.LIME,         "✓")
                )
            else:
                print(
                    c(C.DIM,  f"  [{i}/{count}] ") +
                    c(C.RED,  f"From {host_ip} : Request timeout ✗")
                )
            time.sleep(0.5)

        except subprocess.TimeoutExpired:
            sent += 1
            print(c(C.DIM, f"  [{i}/{count}] ") + c(C.RED, "Timeout ✗"))
        except Exception as e:
            sent += 1
            print(c(C.DIM, f"  [{i}/{count}] ") + c(C.RED, f"Error: {e}"))

    # Summary
    lost     = sent - received
    loss_pct = int((lost / sent) * 100) if sent else 100

    print()
    print(c(C.CYAN, "  " + "─" * 46))
    print(c(C.WHITE + C.BOLD, "  📊 PING SUMMARY"))
    print()

    if times:
        mn  = min(times)
        mx  = max(times)
        avg = sum(times) / len(times)
        try:
            jitter = _stats.stdev(times) if len(times) > 1 else 0.0
        except Exception:
            jitter = 0.0

        # Quality assessment
        if avg < 20 and loss_pct == 0:
            quality, qcol = "Excellent 🟢", C.LIME
        elif avg < 80 and loss_pct < 10:
            quality, qcol = "Good 🟡", C.YELLOW
        elif avg < 200 and loss_pct < 20:
            quality, qcol = "Fair 🟠", C.ORANGE
        else:
            quality, qcol = "Poor 🔴", C.RED

        print(c(C.DIM,           f"  Sent     : {sent}  |  Received: {received}  |  Lost: {lost} ({loss_pct}%)"))
        print(c(C.CYAN,          f"  Min RTT  : {mn:.1f} ms"))
        print(c(C.CYAN,          f"  Max RTT  : {mx:.1f} ms"))
        print(c(C.WHITE + C.BOLD,f"  Avg RTT  : {avg:.1f} ms"))
        print(c(C.DIM,           f"  Jitter   : {jitter:.1f} ms"))
        print()
        print(c(C.WHITE + C.BOLD, f"  Quality  : ") + c(qcol + C.BOLD, quality))

        speak(f"{target} ping {avg:.0f} milliseconds. Quality {quality.split()[0]}.")
    else:
        print(c(C.RED + C.BOLD, f"  Host unreachable — {loss_pct}% packet loss"))
        speak(f"{target} reachable nahi hai Boss.")

    print(c(C.CYAN, "  " + "─" * 46))
    print()

# ──────────────────────────────────────────────────────────
#  PORT SCANNER
# ──────────────────────────────────────────────────────────

# Common ports with service names
PORT_SERVICES = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
    3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC",
    6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt", 8888: "Jupyter",
    27017: "MongoDB", 6443: "Kubernetes", 9200: "Elasticsearch",
    1433: "MSSQL", 1521: "Oracle", 2375: "Docker", 2376: "Docker-TLS",
}

COMMON_PORTS = sorted(PORT_SERVICES.keys())

def _scan_port(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        import socket as _socket
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((host, port))
        s.close()
        return result == 0
    except Exception:
        return False

def port_scan(target: str, port_range: str = "common") -> None:
    import socket as _socket

    # Resolve hostname
    try:
        host_ip = _socket.gethostbyname(target)
    except Exception:
        print(c(C.RED, f"  ✗ Host resolve nahi hua: '{target}'"))
        print(c(C.DIM,  "  Example: portscan 192.168.1.1  ya  portscan google.com"))
        return

    # Determine port list
    if port_range == "common":
        ports    = COMMON_PORTS
        range_lbl = "Common Ports"
    elif "-" in port_range:
        try:
            a, b  = port_range.split("-")
            ports = list(range(int(a), int(b) + 1))
            range_lbl = f"Ports {a}–{b}"
        except Exception:
            ports    = COMMON_PORTS
            range_lbl = "Common Ports"
    else:
        try:
            ports    = [int(port_range)]
            range_lbl = f"Port {port_range}"
        except Exception:
            ports    = COMMON_PORTS
            range_lbl = "Common Ports"

    print(c(C.CYAN + C.BOLD, f"  🎯 Target   : {target}"))
    if host_ip != target:
        print(c(C.DIM,        f"  🔍 Resolved : {host_ip}"))
    print(c(C.YELLOW,         f"  📋 Scanning : {range_lbl} ({len(ports)} ports)"))
    print(c(C.DIM,            f"  ⏳ Please wait..."))
    print()

    open_ports   = []
    closed_count = 0

    # Threaded scan for speed
    results = {}
    lock    = threading.Lock()

    def scan_worker(p):
        is_open = _scan_port(host_ip, p)
        with lock:
            results[p] = is_open

    threads = []
    for port in ports:
        t = threading.Thread(target=scan_worker, args=(port,), daemon=True)
        threads.append(t)
        t.start()
        # Batch to avoid overwhelming
        if len(threads) >= 50:
            for th in threads:
                th.join()
            threads = []

    for th in threads:
        th.join()

    # Display results
    print(c(C.TEAL + C.BOLD, "  PORT      STATE     SERVICE"))
    print(c(C.TEAL,          "  " + "─" * 42))

    for port in sorted(results.keys()):
        is_open = results[port]
        svc     = PORT_SERVICES.get(port, "Unknown")
        if is_open:
            open_ports.append(port)
            print(
                c(C.LIME + C.BOLD, f"  {port:<9}") +
                c(C.LIME + C.BOLD, f"{'OPEN':<10}") +
                c(C.WHITE + C.BOLD, svc)
            )
        else:
            closed_count += 1

    print(c(C.TEAL, "  " + "─" * 42))
    print()

    if open_ports:
        print(c(C.LIME + C.BOLD,  f"  ✅ {len(open_ports)} open port(s) mila!"))
        speak(f"{target} pe {len(open_ports)} open port mila Boss.")
    else:
        print(c(C.DIM,            f"  🔒 Koi open port nahi mila ({closed_count} closed)"))
        speak(f"{target} pe koi open port nahi mila Boss.")

    print(c(C.DIM, f"  🔒 {closed_count} closed  |  🟢 {len(open_ports)} open"))
    print()

# ──────────────────────────────────────────────────────────
#  POMODORO TIMER
# ──────────────────────────────────────────────────────────

_pomo_thread  = None
_pomo_stop    = threading.Event()
_pomo_status  = {"running": False, "type": "", "remaining": 0, "total": 0}

def _pomo_run(minutes: int, label: str, break_min: int = 5):
    global _pomo_status
    total_secs = minutes * 60
    _pomo_status = {"running": True, "type": label, "remaining": total_secs, "total": total_secs}
    _pomo_stop.clear()

    # Countdown
    for remaining in range(total_secs, 0, -1):
        if _pomo_stop.is_set():
            _pomo_status["running"] = False
            return
        _pomo_status["remaining"] = remaining
        time.sleep(1)

    # Focus done — notify
    _pomo_status["running"] = False
    msg = f"🍅 {label} khatam! Break lo — {break_min} minute rest karo Boss!"
    print(f"\n\n{c(C.LIME + C.BOLD, '  ' + '═'*46)}")
    print(c(C.LIME + C.BOLD, f"  🍅  {label.upper()} COMPLETE!"))
    print(c(C.WHITE,          f"  Break time: {break_min} minutes"))
    print(c(C.LIME + C.BOLD,  '  ' + '═'*46) + "\n")
    speak(msg)

    # Break countdown
    if break_min > 0 and not _pomo_stop.is_set():
        break_secs = break_min * 60
        _pomo_status = {"running": True, "type": "Break", "remaining": break_secs, "total": break_secs}
        for remaining in range(break_secs, 0, -1):
            if _pomo_stop.is_set():
                _pomo_status["running"] = False
                return
            _pomo_status["remaining"] = remaining
            time.sleep(1)
        _pomo_status["running"] = False
        end_msg = "Break khatam Boss! Wapas kaam pe lag jao! 💪"
        print(f"\n{c(C.ORANGE + C.BOLD, '  🔔 ' + end_msg)}\n")
        speak(end_msg)

def pomo_start(minutes: int = 25, break_min: int = 5, label: str = "Focus Session"):
    global _pomo_thread, _pomo_stop
    if _pomo_status.get("running"):
        return "Ek pomodoro pehle se chal raha hai! Rokne ke liye: pomodoro stop"
    _pomo_stop.clear()
    _pomo_thread = threading.Thread(
        target=_pomo_run,
        args=(minutes, label, break_min),
        daemon=True
    )
    _pomo_thread.start()
    return f"🍅 Pomodoro shuru! {minutes} min focus → {break_min} min break. All the best Boss! 💪"

def pomo_stop():
    global _pomo_stop
    if not _pomo_status.get("running"):
        return "Koi pomodoro nahi chal raha."
    _pomo_stop.set()
    _pomo_status["running"] = False
    return "⏹️ Pomodoro rok diya."

def pomo_status_str() -> str:
    if not _pomo_status.get("running"):
        return "Koi pomodoro nahi chal raha."
    rem  = _pomo_status["remaining"]
    mins = rem // 60
    secs = rem % 60
    typ  = _pomo_status["type"]
    total = _pomo_status["total"]
    done  = total - rem
    pct   = int((done / total) * 100) if total else 0
    bar_f = int(pct / 5)
    bar   = "█" * bar_f + "░" * (20 - bar_f)
    col   = C.LIME if typ == "Break" else C.ORANGE
    return (
        f"\n  {c(col + C.BOLD, f'🍅 {typ}')} — {c(C.WHITE + C.BOLD, f'{mins:02d}:{secs:02d}')} remaining\n"
        f"  {c(col, f'  [{bar}] {pct}%')}\n"
    )

# ──────────────────────────────────────────────────────────
#  SMART TODO LIST
# ──────────────────────────────────────────────────────────

TODO_FILE = "friday_todos.json"

def _todo_load() -> list:
    if os.path.exists(TODO_FILE):
        with open(TODO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def _todo_save(todos: list):
    with open(TODO_FILE, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)

def _todo_next_id(todos: list) -> int:
    return max((t["id"] for t in todos), default=0) + 1

def _todo_parse_priority(text: str):
    """Extract priority from text: !high !medium !low"""
    import re as _re
    m = _re.search(r'!(high|medium|low|h|m|l)', text, _re.IGNORECASE)
    if m:
        p = m.group(1).lower()
        priority = {"h": "high", "high": "high",
                    "m": "medium", "medium": "medium",
                    "l": "low", "low": "low"}.get(p, "medium")
        text = _re.sub(r'!(high|medium|low|h|m|l)', '', text, flags=_re.IGNORECASE).strip()
        return text, priority
    return text, "medium"

def _todo_parse_deadline(text: str):
    """Extract deadline: kal, aaj, dd/mm, dd month"""
    import re as _re
    deadline = None
    today = datetime.date.today()

    # kal / tomorrow
    if _re.search(r'\bkal\b|\btomorrow\b', text, _re.IGNORECASE):
        deadline = str(today + datetime.timedelta(days=1))
        text = _re.sub(r'\bkal\b|\btomorrow\b', '', text, flags=_re.IGNORECASE).strip()

    # aaj / today
    elif _re.search(r'\baaj\b|\btoday\b', text, _re.IGNORECASE):
        deadline = str(today)
        text = _re.sub(r'\baaj\b|\btoday\b', '', text, flags=_re.IGNORECASE).strip()

    # dd/mm format
    elif m := _re.search(r'(\d{1,2})/(\d{1,2})', text):
        try:
            deadline = str(datetime.date(today.year, int(m.group(2)), int(m.group(1))))
            text = text[:m.start()].strip() + text[m.end():].strip()
        except Exception:
            pass

    # "15 march" / "15 jan" format
    elif m := _re.search(r'(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b', text, _re.IGNORECASE):
        months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
                  "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
                  "january":1,"february":2,"march":3,"april":4,"june":6,
                  "july":7,"august":8,"september":9,"october":10,"november":11,"december":12}
        try:
            mo = months.get(m.group(2).lower()[:3], 0)
            if mo:
                deadline = str(datetime.date(today.year, mo, int(m.group(1))))
                text = (text[:m.start()] + text[m.end():]).strip()
        except Exception:
            pass

    return text.strip(), deadline

def todo_add(title: str) -> str:
    todos = _todo_load()
    title, priority = _todo_parse_priority(title)
    title, deadline = _todo_parse_deadline(title)
    title = title.strip()
    if not title:
        return "Kya add karoon? Example: todo add meeting kal !high"
    new_todo = {
        "id":       _todo_next_id(todos),
        "title":    title,
        "priority": priority,
        "deadline": deadline,
        "done":     False,
        "created":  str(datetime.date.today()),
    }
    todos.append(new_todo)
    _todo_save(todos)
    dl = f" — Due: {deadline}" if deadline else ""
    return f"✅ Added: '{title}' [{priority.upper()}]{dl}"

def todo_list(filter_type: str = "all") -> None:
    todos = _todo_load()
    today = str(datetime.date.today())

    if filter_type == "pending":
        items = [t for t in todos if not t["done"]]
    elif filter_type == "done":
        items = [t for t in todos if t["done"]]
    else:
        items = todos

    if not items:
        print(c(C.DIM, "  Koi todo nahi hai — todo add [kaam] se shuru karo."))
        return

    # Sort: pending first, then by priority, then by deadline
    priority_order = {"high": 0, "medium": 1, "low": 2}
    items_sorted = sorted(items, key=lambda x: (
        x["done"],
        priority_order.get(x["priority"], 1),
        x["deadline"] or "9999"
    ))

    pending = sum(1 for t in todos if not t["done"])
    done    = sum(1 for t in todos if t["done"])

    print(c(C.CYAN + C.BOLD, f"  📋 TODO LIST  ") +
          c(C.LIME, f"[{pending} pending]  ") +
          c(C.DIM,  f"[{done} done]"))
    print(c(C.CYAN, "  " + "─" * 52))
    print()

    for t in items_sorted:
        tid      = t["id"]
        title    = t["title"]
        priority = t["priority"]
        deadline = t.get("deadline")
        done     = t["done"]

        # Priority color + icon
        if priority == "high":
            p_col, p_icon = C.RED,    "🔴"
        elif priority == "low":
            p_col, p_icon = C.DIM,    "🟢"
        else:
            p_col, p_icon = C.YELLOW, "🟡"

        # Done / Pending
        status = c(C.DIM + C.LIME, "✓") if done else c(C.RED, "○")

        # Deadline status
        dl_str = ""
        if deadline:
            if deadline < today and not done:
                dl_str = c(C.RED + C.BOLD, f" ⚠ OVERDUE ({deadline})")
            elif deadline == today and not done:
                dl_str = c(C.ORANGE + C.BOLD, f" ⏰ TODAY!")
            else:
                dl_str = c(C.DIM, f" 📅 {deadline}")

        title_col = C.DIM if done else C.WHITE
        print(
            c(C.DIM,           f"  [{tid:>2}] ") +
            status + " " +
            c(p_col + C.BOLD,  f"{p_icon} ") +
            c(title_col + C.BOLD, title) +
            dl_str
        )

    print()
    print(c(C.CYAN, "  " + "─" * 52))
    print(c(C.DIM,  f"  todo done [id]  |  todo delete [id]  |  todo clear"))
    speak(f"{pending} kaam pending hain Boss.")

def todo_done(query: str) -> str:
    todos = _todo_load()
    # By ID or keyword
    match = None
    if query.isdigit():
        for t in todos:
            if t["id"] == int(query):
                match = t
                break
    else:
        for t in todos:
            if query.lower() in t["title"].lower() and not t["done"]:
                match = t
                break
    if not match:
        return f"Todo '{query}' nahi mila."
    match["done"] = True
    _todo_save(todos)
    return f"✅ Done: '{match['title']}' complete!"

def todo_delete(query: str) -> str:
    todos = _todo_load()
    match = None
    if query.isdigit():
        for t in todos:
            if t["id"] == int(query):
                match = t
                break
    else:
        for t in todos:
            if query.lower() in t["title"].lower():
                match = t
                break
    if not match:
        return f"Todo '{query}' nahi mila."
    todos.remove(match)
    _todo_save(todos)
    return f"🗑️  Deleted: '{match['title']}'"

def todo_clear(filter_type: str = "done") -> str:
    todos = _todo_load()
    if filter_type == "all":
        _todo_save([])
        return "🗑️  Saare todos clear ho gaye."
    remaining = [t for t in todos if not t["done"]]
    cleared   = len(todos) - len(remaining)
    _todo_save(remaining)
    return f"🗑️  {cleared} completed todos clear ho gaye."

# ──────────────────────────────────────────────────────────
#  HABIT TRACKER
# ──────────────────────────────────────────────────────────

HABIT_FILE = "friday_habits.json"

def _habit_load() -> dict:
    if os.path.exists(HABIT_FILE):
        with open(HABIT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _habit_save(data: dict):
    with open(HABIT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _habit_streak(dates: list) -> int:
    """Calculate current streak from list of date strings"""
    if not dates:
        return 0
    today     = datetime.date.today()
    streak    = 0
    check_day = today
    date_set  = set(dates)
    while str(check_day) in date_set:
        streak    += 1
        check_day -= datetime.timedelta(days=1)
    return streak

def _habit_longest(dates: list) -> int:
    """Calculate longest streak ever"""
    if not dates:
        return 0
    sorted_dates = sorted(set(dates))
    longest = current = 1
    for i in range(1, len(sorted_dates)):
        d1 = datetime.date.fromisoformat(sorted_dates[i-1])
        d2 = datetime.date.fromisoformat(sorted_dates[i])
        if (d2 - d1).days == 1:
            current += 1
            longest  = max(longest, current)
        else:
            current  = 1
    return longest

def habit_add(name: str) -> str:
    data  = _habit_load()
    key   = name.lower().strip()
    if key in data:
        return f"Habit '{name}' pehle se hai Boss!"
    data[key] = {"name": name, "dates": [], "created": str(datetime.date.today())}
    _habit_save(data)
    return f"Habit '{name}' add ho gayi! Ab daily track karo. 💪"

def habit_done(name: str) -> str:
    data  = _habit_load()
    key   = name.lower().strip()
    # Fuzzy match
    match = None
    for k in data:
        if key in k or k in key:
            match = k
            break
    if not match:
        return f"Habit '{name}' nahi mili. Pehle: habit add {name}"
    today = str(datetime.date.today())
    if today in data[match]["dates"]:
        return f"'{data[match]['name']}' aaj pehle se mark hai Boss! ✅"
    data[match]["dates"].append(today)
    _habit_save(data)
    streak = _habit_streak(data[match]["dates"])
    if streak >= 7:
        msg = f"🔥 {streak} din ka streak! Zabardast Boss!"
    elif streak >= 3:
        msg = f"⚡ {streak} din ka streak! Keep going!"
    else:
        msg = f"✅ Done! {streak} din ka streak."
    return msg

def habit_list() -> None:
    data  = _habit_load()
    today = str(datetime.date.today())
    if not data:
        print(c(C.DIM, "  Koi habit nahi hai — habit add [naam] se shuru karo."))
        return
    print(c(C.LIME + C.BOLD, "  💪 HABIT TRACKER"))
    print(c(C.TEAL, "  " + "─" * 52))
    for key, h in data.items():
        name    = h["name"]
        dates   = h.get("dates", [])
        streak  = _habit_streak(dates)
        longest = _habit_longest(dates)
        total   = len(dates)
        done_today = today in dates

        # Streak fire
        if streak >= 7:   fire = "🔥"
        elif streak >= 3: fire = "⚡"
        elif streak >= 1: fire = "✅"
        else:             fire = "💤"

        done_str = c(C.LIME + C.BOLD, " ✓ Done") if done_today else c(C.RED, " ✗ Pending")
        print()
        print(c(C.WHITE + C.BOLD,  f"  {fire}  {name}") + done_str)
        print(c(C.CYAN,            f"     🔥 Streak    : {streak} days"))
        print(c(C.YELLOW,          f"     🏆 Best      : {longest} days"))
        print(c(C.DIM,             f"     📅 Total     : {total} days completed"))

        # Last 7 days mini calendar
        cal = "     📆 Last 7   : "
        for i in range(6, -1, -1):
            d = str(datetime.date.today() - datetime.timedelta(days=i))
            cal += "🟩" if d in dates else "⬜"
        print(c(C.WHITE, cal))
    print()
    print(c(C.TEAL, "  " + "─" * 52))
    total_habits = len(data)
    speak(f"{total_habits} habits tracked hain Boss.")

def habit_delete(name: str) -> str:
    data = _habit_load()
    key  = name.lower().strip()
    match = None
    for k in data:
        if key in k or k in key:
            match = k
            break
    if not match:
        return f"Habit '{name}' nahi mili."
    del data[match]
    _habit_save(data)
    return f"Habit '{name}' delete ho gayi."

# ──────────────────────────────────────────────────────────
#  JOKES  (Hinglish — clean, funny)
# ──────────────────────────────────────────────────────────

JOKES = [
    "Teacher: Tumhara homework kahan hai?\nStudent: Sir, maine usse recycle kar diya — environment bachana chahta hoon! 😄",
    "Ek aadmi doctor ke paas gaya: 'Doctor mujhe neend nahi aati.'\nDoctor: 'Meri fees sun lo, turant aa jaayegi.' 😂",
    "Papa ne pucha: Beta padh raha hai?\nMain: Haan Papa!\nPapa: To ye headphones kyun laaye hain?\nMain: Concentration ke liye! 😅",
    "WhatsApp pe 'typing...' aaya aur phir gayab ho gaya.\nYahi hai zindagi ka sabse bada cliffhanger. 😂",
    "Exam hall mein sab likhte hain, main sochta hoon.\nSab sochte hain, main likhta hoon.\nKissi ka kuch kaam nahi aata. 😭",
    "Biwi: Kya tum mujhse pyaar karte ho?\nPati: Haan bilkul.\nBiwi: To phone rakh do na!\nPati: ...*saves game first* 😬",
    "Meri zindagi ek Excel sheet jaisi hai — bahut saare cells, lekin koi formula kaam nahi karta. 😄",
    "Dost: Yaar tension mat le, sab theek hoga.\nMain: Tu doctor hai?\nDost: Nahi, lekin optimist hoon. 😂",
    "Neend se pyaara kuch nahi,\nKhane se meetha kuch nahi,\nLekin phone utha lo toh...\nDono bhool jaate hain. 😅",
    "Interview mein pucha: Aapki weakness kya hai?\nMain: Honesty.\nInterviewer: Ye weakness nahi lagti.\nMain: Mujhe parwah nahi aapki. 😂",
    "Student ne essay likha: 'Meri maa sabse acchi hain.'\nTeacher: Bahut accha! Ab apne words mein likho.\nStudent: 'Meri maa sabse acchi hain.' 😄",
    "Zindagi mein do cheezein pakki hain:\n1. Tax\n2. Wi-Fi ka slow hona jab sabse zyada zaroori ho. 😤",
    "Dost: Kal raat kya kiya?\nMain: Kuch nahi.\nDost: Mujhe bhi bulata! 😄",
    "Alarm bajta hai, main sochta hoon: '5 minute aur.'\n3 ghante baad uthta hoon. Daily motivation. 😭",
    "Class mein teacher: Koi sawaal?\nMain andar se: Haan, ye sab kyun padh rahe hain? 😂",
    "Phone pe battery 1% bachi ho aur charger doosre kamre mein ho —\nYahi hota hai asli life ka boss fight. 😱",
    "Gym join kiya, 3 din gaya.\nAb sirf 'member' hoon — poori loyalty dikhata hoon Instagram pe. 😅",
    "Koi bole 'Last seen 2 minutes ago' aur reply nahi kiya —\ntohfa milta hai toh aisa hi milta hai. 😒",
    "Main: Main diet pe hoon.\nBiryani ki smell aai.\nMain: Kal se shuru karta hoon. 😂",
    "Bacpan mein socha tha bade hokar kya banunga.\nAb socha — seedha charger dhundh raha hoon. 😄",
]

QUOTES = [
    ("Mushkilein woh hoti hain jo tujhe todne nahi, balki banane aati hain.", "Friday"),
    ("Kal ka wait mat kar — aaj jo shuru kiya, wahi kal ka fakhр bnega.", "Friday"),
    ("Haar tab hoti hai jab tu khud maan le. Tab tak nahi jab tak tu uthta raha.", "Friday"),
    ("Sapne woh nahi jo neend mein aayein — sapne woh hain jo neend uda dein.", "A.P.J. Abdul Kalam"),
    ("Kamyabi ka shortcut nahi — sirf mehnat ka rasta hai.", "Friday"),
    ("Duniya teri taraf tab aayegi jab tu khud apni taraf chal chuka hoga.", "Friday"),
    ("Jo aaj mushkil lagta hai, woh kal ki sabse badi jeet hogi.", "Friday"),
    ("Tujhe prove karna kissi ko nahi — bas khud se honest rehna hai.", "Friday"),
    ("Galti karna insaan hai, galti se seekhna legend.", "Friday"),
    ("Uth, chal, gir, uth — lekin ruk mat. Bas yahi success ka formula hai.", "Friday"),
    ("Waqt sabka aata hai — bas tayaar rehna chahiye jab woh aaye.", "Friday"),
    ("Choti choti jeetein bhi celebrate karo — wahi bade sapnon ki neenv hain.", "Friday"),
    ("Pehle khud pe yakeen kar — baaki duniya baad mein karegi.", "Friday"),
    ("Zindagi itni chhoti hai ki negatvity pe waste karna afford nahi kar sakta tu.", "Friday"),
    ("Comparison apna dushman hai — tu apna original hai, copy mat ban.", "Friday"),
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("It always seems impossible until it's done.", "Nelson Mandela"),
    ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
    ("Hardships often prepare ordinary people for an extraordinary destiny.", "C.S. Lewis"),
    ("Don't watch the clock; do what it does. Keep going.", "Sam Levenson"),
    ("Toot ke bhi khada rehna — yahi teri asli pehchaan hai.", "Friday"),
    ("Koi nahi dekhta jab tu practice karta hai — sab dekhte hain jab tu shine karta hai.", "Friday"),
    ("Apne aap ko wo dene ki koshish karo jo tum kisi aur se maangoge.", "Friday"),
    ("Focus mat kho — result time pe aata hai, schedule pe nahi.", "Friday"),
    ("Energy wahan lagao jahan growth ho — complaints mein nahi.", "Friday"),
]

import random as _random

def get_joke() -> str:
    return _random.choice(JOKES)

def get_quote() -> tuple:
    return _random.choice(QUOTES)


def do_web_search(query: str) -> str:
    """ddgr se real-time search — 4-5 line article snippets"""

    # ── Method 1: ddgr CLI tool ──
    try:
        result = subprocess.run(
            ["ddgr", "--json", "--num", "3", "--noprompt", query],
            capture_output=True, text=True, timeout=12
        )
        if result.returncode == 0 and result.stdout.strip():
            import json as _json
            items = _json.loads(result.stdout)
            snippets = []
            for item in items[:3]:
                title   = item.get("title", "").strip()
                snippet = item.get("abstract", "").strip()
                if snippet:
                    snippets.append(f"• {title}: {snippet}")
            if snippets:
                return "\n".join(snippets)
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass  # ddgr nahi mila, fallback pe jao

    # ── Method 2: DuckDuckGo HTML scrape ──
    try:
        from urllib.request import urlopen, Request
        from urllib.parse import quote_plus
        import re as _re

        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        req  = Request(search_url, headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36"
        })
        html = urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")

        titles   = _re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, _re.DOTALL)
        snippets = _re.findall(r'class="result__snippet"[^>]*>(.*?)</(?:a|span)>', html, _re.DOTALL)

        titles   = [_re.sub(r"<[^>]+>", "", t).strip() for t in titles]
        snippets = [_re.sub(r"<[^>]+>", "", s).strip() for s in snippets]

        results = []
        for i in range(min(3, len(snippets))):
            title   = titles[i]   if i < len(titles)   else ""
            snippet = snippets[i] if i < len(snippets) else ""
            if len(snippet) > 30:
                entry = f"• {title}: {snippet}" if title else f"• {snippet}"
                results.append(entry)

        if results:
            return "\n".join(results)

    except Exception:
        pass

    # ── Method 3: DuckDuckGo Instant Answer API (last resort) ──
    try:
        from urllib.request import urlopen, Request
        from urllib.parse import urlencode
        import json as _json

        params = urlencode({"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"})
        url    = f"https://api.duckduckgo.com/?{params}"
        req    = Request(url, headers={"User-Agent": "FridayAI/1.0"})
        data   = _json.loads(urlopen(req, timeout=8).read().decode())

        parts = []
        if data.get("AbstractText"):
            parts.append(data["AbstractText"])
        if data.get("Answer"):
            parts.append(data["Answer"])
        for topic in data.get("RelatedTopics", [])[:2]:
            if isinstance(topic, dict) and topic.get("Text"):
                parts.append(topic["Text"])
        if parts:
            return "\n".join(f"• {p}" for p in parts[:3])

    except Exception:
        pass

    return "Internet se koi result nahi mila."




# ──────────────────────────────────────────────────────────
#  GROQ CALL  (with DuckDuckGo Web Search)
# ──────────────────────────────────────────────────────────

def chat_with_friday(short_mem, long_mem, user_input, emotion):
    mem_ctx      = build_memory_context(long_mem)
    deep_ctx     = context_build_prompt()          # cross-session deep context
    emo_note     = f"\n[NOTE: Miraz ka emotion: {emotion} {EMOTION_EMOJI.get(emotion,'')}]\n"
    lang_script  = detect_script(user_input)
    lang_note    = ""
    if lang_script == "urdu":
        lang_note = "\n[NOTE: Miraz ne Urdu mein likha hai — Urdu mein jawab do]\n"
    elif lang_script == "bengali":
        lang_note = "\n[NOTE: Miraz ne Bengali mein likha hai — Bengali mein jawab do]\n"

    sys_msg = FRIDAY_SYSTEM + mem_ctx + deep_ctx + emo_note + lang_note

    messages = [{"role": "system", "content": sys_msg}]
    messages += short_mem.get()

    # ── Web search agar zaroori ho ──
    search_context = ""
    if needs_search(user_input):
        sys.stdout.write(c(C.TEAL + C.BOLD, "\n  🌐 Searching web...") + "\n")
        sys.stdout.flush()
        result = do_web_search(user_input)
        if result and "error" not in result.lower():
            search_context = f"\n[WEB SEARCH RESULT for '{user_input}']:\n{result}\n[Use this info in your reply. Be accurate.]\n[SEARCH_LEARN: Agar search result mein koi important fact, news, ya useful info ho jo Boss ke liye future mein kaam aaye — usse [SAVE_MEMORY: fact] tag se save karo. Sirf truly useful facts save karo, bakwaas nahi.]\n"
            sys.stdout.write(c(C.LIME + C.BOLD, "  ✓ Found results\n"))
            sys.stdout.flush()

    final_input = user_input + search_context
    messages.append({"role": "user", "content": final_input})

    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.55,
        max_tokens=120,
    )
    return resp.choices[0].message.content.strip()



# ──────────────────────────────────────────────────────────
#  NIGHT GUARD SYSTEM
# ──────────────────────────────────────────────────────────

NIGHT_GUARD_FILE    = "night_guard_data.json"
NIGHT_GUARD_ACTIVE  = False
NIGHT_GUARD_THREAD  = None
NIGHT_GUARD_ALERTS  = []   # alert log
NIGHT_GUARD_LEARNED = {}   # baseline data

def _ng_load():
    if os.path.exists(NIGHT_GUARD_FILE):
        with open(NIGHT_GUARD_FILE, "r") as f:
            return json.load(f)
    return {"learned": {}, "alerts": [], "thresholds": {
        "battery_low": 20, "battery_high": 95,
        "temp_high": 45, "known_networks": [], "known_processes": []
    }}

def _ng_save(data):
    with open(NIGHT_GUARD_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _ng_get_battery():
    try:
        r = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=5)
        d = json.loads(r.stdout)
        return d.get("percentage", -1), d.get("temperature", -1), d.get("status", "unknown")
    except Exception:
        return -1, -1, "unknown"

def _ng_get_network():
    try:
        r = subprocess.run(["termux-wifi-connectioninfo"], capture_output=True, text=True, timeout=5)
        d = json.loads(r.stdout)
        return d.get("ssid", "unknown"), d.get("ip", "unknown")
    except Exception:
        return "unknown", "unknown"

def _ng_get_processes():
    try:
        r = subprocess.run(["ps", "-e", "-o", "comm"], capture_output=True, text=True, timeout=5)
        procs = [p.strip() for p in r.stdout.strip().split("\n")[1:] if p.strip()]
        return list(set(procs))
    except Exception:
        return []

def _ng_scan_once(data):
    """Ek scan run karo — battery, network, processes check karo"""
    alerts = []
    now = datetime.datetime.now().strftime("%H:%M")
    thr = data.get("thresholds", {})

    # Battery check
    batt, temp, status = _ng_get_battery()
    if batt != -1:
        if batt <= thr.get("battery_low", 20):
            alerts.append(f"[{now}] 🔴 Battery LOW: {batt}% — charger lagao Boss!")
        elif batt >= thr.get("battery_high", 95) and status == "CHARGING":
            alerts.append(f"[{now}] 🟡 Battery FULL: {batt}% — charger hata sakte hain.")
        if temp != -1 and temp >= thr.get("temp_high", 45):
            alerts.append(f"[{now}] 🔥 Temperature HIGH: {temp}°C — phone garam ho raha hai!")

    # Network check
    ssid, ip = _ng_get_network()
    known_nets = thr.get("known_networks", [])
    if known_nets and ssid != "unknown" and ssid not in known_nets:
        alerts.append(f"[{now}] ⚠️  UNKNOWN Network: '{ssid}' — pehle kabhi nahi dekha!")

    # Process check
    procs = _ng_get_processes()
    known_procs = set(thr.get("known_processes", []))
    if known_procs:
        new_procs = set(procs) - known_procs
        suspicious = [p for p in new_procs if any(
            kw in p.lower() for kw in ["spy","track","record","keylog","hack","monitor","sniff"]
        )]
        if suspicious:
            alerts.append(f"[{now}] 🚨 SUSPICIOUS Process: {', '.join(suspicious)}")

    return alerts, batt, temp, ssid, procs

def _ng_monitor_loop(interval=60):
    """Background thread — har interval seconds mein scan"""
    global NIGHT_GUARD_ALERTS
    data = _ng_load()
    while NIGHT_GUARD_ACTIVE:
        try:
            alerts, batt, temp, ssid, procs = _ng_scan_once(data)
            if alerts:
                for a in alerts:
                    NIGHT_GUARD_ALERTS.append(a)
                    # Termux notification
                    try:
                        subprocess.run(
                            ["termux-notification", "--title", "Night Guard 🛡️", "--content", a],
                            timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                        )
                    except Exception:
                        pass
        except Exception:
            pass
        for _ in range(interval):
            if not NIGHT_GUARD_ACTIVE:
                break
            time.sleep(1)

def ng_learn():
    """Current state ko baseline ke tor par save karo"""
    print()
    print(c(C.PURPLE + C.BOLD, "  🛡️  Night Guard — Seekh raha hoon..."))
    print(c(C.TEAL, "  " + "─" * 52))

    data = _ng_load()

    batt, temp, status = _ng_get_battery()
    ssid, ip           = _ng_get_network()
    procs              = _ng_get_processes()

    if ssid != "unknown":
        if ssid not in data["thresholds"]["known_networks"]:
            data["thresholds"]["known_networks"].append(ssid)
    data["thresholds"]["known_processes"] = procs
    data["learned"] = {
        "battery": batt, "temp": temp, "ssid": ssid,
        "ip": ip, "process_count": len(procs),
        "learned_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    _ng_save(data)

    print(c(C.LIME,   f"  ✓ Battery     : {batt}% ({status})"))
    print(c(C.LIME,   f"  ✓ Temperature : {temp}°C"))
    print(c(C.LIME,   f"  ✓ Network     : {ssid} ({ip})"))
    print(c(C.LIME,   f"  ✓ Processes   : {len(procs)} recorded"))
    print(c(C.TEAL,   "  " + "─" * 52))
    print(c(C.GOLD,   "  Baseline save ho gayi! Ab Night Guard accurately monitor karega."))
    print()

def ng_on():
    """Night Guard start karo"""
    global NIGHT_GUARD_ACTIVE, NIGHT_GUARD_THREAD
    if NIGHT_GUARD_ACTIVE:
        print(c(C.YELLOW, "\n  Night Guard pehle se ON hai Boss.\n"))
        return
    NIGHT_GUARD_ACTIVE = True
    NIGHT_GUARD_THREAD = threading.Thread(target=_ng_monitor_loop, args=(60,), daemon=True)
    NIGHT_GUARD_THREAD.start()
    print()
    print(c(C.PURPLE + C.BOLD, "  🛡️  Night Guard ACTIVE!"))
    print(c(C.DIM,              "  Har 60 sec mein scan hoga — battery, network, processes."))
    print(c(C.DIM,              "  Alerts aayenge agar kuch unusual mila."))
    print()

def ng_off():
    """Night Guard band karo"""
    global NIGHT_GUARD_ACTIVE
    NIGHT_GUARD_ACTIVE = False
    print()
    print(c(C.DIM + C.BOLD, "  🛡️  Night Guard OFF ho gaya."))
    print()

def ng_scan():
    """Abhi ek baar manual scan karo"""
    print()
    print(c(C.PURPLE + C.BOLD, "  🛡️  Night Guard — Manual Scan..."))
    print(c(C.TEAL, "  " + "─" * 52))
    data = _ng_load()
    alerts, batt, temp, ssid, procs = _ng_scan_once(data)

    print(c(C.CYAN,  f"  🔋 Battery     : {batt}%"))
    print(c(C.CYAN,  f"  🌡️  Temperature : {temp}°C"))
    print(c(C.CYAN,  f"  📶 Network     : {ssid}"))
    print(c(C.CYAN,  f"  ⚙️  Processes   : {len(procs)} running"))
    print(c(C.TEAL, "  " + "─" * 52))

    if alerts:
        print(c(C.RED + C.BOLD, "  ⚠️  ALERTS:"))
        for a in alerts:
            print(c(C.YELLOW, f"    {a}"))
    else:
        print(c(C.LIME + C.BOLD, "  ✓ Sab theek hai — koi issue nahi mila."))
    print()

def ng_status():
    """Night Guard ka current status dikhao"""
    print()
    status_txt = c(C.LIME + C.BOLD, "ACTIVE 🟢") if NIGHT_GUARD_ACTIVE else c(C.RED + C.BOLD, "OFF 🔴")
    print(c(C.PURPLE + C.BOLD, "  🛡️  Night Guard Status: ") + status_txt)
    data = _ng_load()
    learned = data.get("learned", {})
    thr     = data.get("thresholds", {})
    print(c(C.TEAL, "  " + "─" * 52))
    if learned:
        print(c(C.GOLD,  f"  Learned at   : {learned.get('learned_at','—')}"))
        print(c(C.CYAN,  f"  Known network : {', '.join(thr.get('known_networks', ['—']))}"))
        print(c(C.CYAN,  f"  Battery low   : {thr.get('battery_low', 20)}%  |  High: {thr.get('battery_high', 95)}%"))
        print(c(C.CYAN,  f"  Temp limit    : {thr.get('temp_high', 45)}°C"))
        print(c(C.CYAN,  f"  Processes     : {len(thr.get('known_processes', []))} known"))
    else:
        print(c(C.DIM,   "  Abhi tak learn nahi kiya — 'night guard learn' chalao pehle."))
    alert_count = len(NIGHT_GUARD_ALERTS)
    print(c(C.YELLOW, f"  Alerts today  : {alert_count}"))
    print(c(C.TEAL, "  " + "─" * 52))
    print()

def ng_alerts():
    """Saare alerts dikhao"""
    print()
    print(c(C.PURPLE + C.BOLD, "  🛡️  Night Guard — Alert Log"))
    print(c(C.TEAL, "  " + "─" * 52))
    if NIGHT_GUARD_ALERTS:
        for a in NIGHT_GUARD_ALERTS[-20:]:  # last 20
            print(c(C.YELLOW, f"  {a}"))
    else:
        print(c(C.DIM, "  Koi alert nahi aaya abhi tak. Sab safe hai. ✓"))
    print(c(C.TEAL, "  " + "─" * 52))
    print()


# ──────────────────────────────────────────────────────────
#  REMINDER SYSTEM
# ──────────────────────────────────────────────────────────

REMINDER_FILE   = "friday_reminders.json"
REMINDER_THREAD = None

def _rem_load():
    if os.path.exists(REMINDER_FILE):
        with open(REMINDER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def _rem_save(reminders):
    with open(REMINDER_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)

def _rem_parse_datetime(text: str) -> datetime.datetime | None:
    """Natural language se datetime nikalo — kal, aaj, 5 baje, etc."""
    now  = datetime.datetime.now()
    text = text.lower().strip()

    # Date part
    if "kal" in text or "tomorrow" in text:
        base_date = now.date() + datetime.timedelta(days=1)
    elif "parso" in text:
        base_date = now.date() + datetime.timedelta(days=2)
    elif "aaj" in text or "today" in text:
        base_date = now.date()
    else:
        base_date = now.date()  # default aaj

    # Time part — "5 baje", "5:30 baje", "17:00", "5 pm", "5 am"
    import re as _re
    # HH:MM format
    m = _re.search(r'(\d{1,2}):(\d{2})\s*(am|pm|baje|bajkar)?', text)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        ampm = m.group(3) or ""
        if "pm" in ampm and h < 12: h += 12
        elif "am" in ampm and h == 12: h = 0
        return datetime.datetime.combine(base_date, datetime.time(h, mn))

    # "X baje" or "X pm/am"
    m = _re.search(r'(\d{1,2})\s*(baje|bajkar|pm|am|:00)?', text)
    if m:
        h = int(m.group(1))
        suffix = m.group(2) or ""
        if "pm" in suffix and h < 12: h += 12
        elif "am" in suffix and h == 12: h = 0
        elif h < 7 and "am" not in suffix:  # 1-6 assume PM
            h += 12
        return datetime.datetime.combine(base_date, datetime.time(h, 0))

    return None

def _rem_monitor_loop():
    """Background thread — har 30 sec mein check karo"""
    while True:
        try:
            now  = datetime.datetime.now()
            rems = _rem_load()
            changed = False
            for rem in rems:
                if rem.get("done"): continue
                rem_time = datetime.datetime.fromisoformat(rem["datetime"])
                diff = (rem_time - now).total_seconds()
                if -60 <= diff <= 30:  # window: 1 min pehle se 30 sec baad tak
                    title = rem.get("title", "Reminder")
                    msg   = f"Boss! Reminder: {title} 🔔"
                    # Termux notification
                    try:
                        subprocess.run(
                            ["termux-notification", "--title", "⏰ Friday Reminder",
                             "--content", title, "--priority", "high"],
                            timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                        )
                    except Exception:
                        pass
                    # Voice
                    speak(msg)
                    # Print on screen
                    sys.stdout.write(f"\n{c(C.GOLD + C.BOLD, '  ⏰ REMINDER: ')}{c(C.WHITE + C.BOLD, title)}\n")
                    sys.stdout.flush()
                    rem["done"] = True
                    changed = True
            if changed:
                _rem_save(rems)
        except Exception:
            pass
        time.sleep(30)

def rem_add(title: str, dt: datetime.datetime):
    rems = _rem_load()
    entry = {
        "id":       len(rems) + 1,
        "title":    title,
        "datetime": dt.isoformat(),
        "done":     False,
        "created":  datetime.datetime.now().isoformat()
    }
    rems.append(entry)
    _rem_save(rems)
    return entry

def rem_list():
    rems   = _rem_load()
    active = [r for r in rems if not r.get("done")]
    print()
    print(c(C.GOLD + C.BOLD, "  ⏰ Upcoming Reminders"))
    print(c(C.TEAL, "  " + "─" * 52))
    if not active:
        print(c(C.DIM, "  Koi reminder nahi hai abhi."))
    else:
        now = datetime.datetime.now()
        for r in active:
            dt   = datetime.datetime.fromisoformat(r["datetime"])
            diff = dt - now
            mins = int(diff.total_seconds() / 60)
            if mins < 0:
                when = c(C.DIM, "(already past)")
            elif mins < 60:
                when = c(C.YELLOW, f"({mins} min baad)")
            elif mins < 1440:
                when = c(C.LIME, f"({mins//60} ghante baad)")
            else:
                when = c(C.CYAN, f"({mins//1440} din baad)")
            num   = c(C.YELLOW + C.BOLD, f"  {r['id']:>2}. ")
            ts    = c(C.CYAN,            dt.strftime("%d %b %Y, %I:%M %p"))
            title = c(C.WHITE + C.BOLD,  f"  {r['title']}")
            print(num + ts + title + "  " + when)
    print(c(C.TEAL, "  " + "─" * 52))
    print()

def rem_delete(query: str):
    rems = _rem_load()
    deleted = []
    if query.lower() in ("all", "sab", "sab kuch"):
        deleted = [r["title"] for r in rems if not r.get("done")]
        rems = [r for r in rems if r.get("done")]
    elif query.isdigit():
        idx = int(query)
        new_rems = []
        for r in rems:
            if r["id"] == idx and not r.get("done"):
                deleted.append(r["title"])
            else:
                new_rems.append(r)
        rems = new_rems
    else:
        new_rems = []
        for r in rems:
            if query.lower() in r["title"].lower() and not r.get("done"):
                deleted.append(r["title"])
            else:
                new_rems.append(r)
        rems = new_rems
    _rem_save(rems)
    print()
    if deleted:
        print(c(C.RED + C.BOLD, "  🗑️  Reminder deleted:"))
        for d in deleted:
            print(c(C.DIM + C.RED, f"    ✗ {d}"))
    else:
        print(c(C.YELLOW, f"  Koi reminder nahi mila '{query}' se."))
    print()

# ──────────────────────────────────────────────────────────
#  BANNER
# ──────────────────────────────────────────────────────────

ASCII_FRIDAY = [
    "  ███████╗██████╗ ██╗██████╗  █████╗ ██╗   ██╗",
    "  ██╔════╝██╔══██╗██║██╔══██╗██╔══██╗╚██╗ ██╔╝",
    "  █████╗  ██████╔╝██║██║  ██║███████║ ╚████╔╝ ",
    "  ██╔══╝  ██╔══██╗██║██║  ██║██╔══██║  ╚██╔╝  ",
    "  ██║     ██║  ██║██║██████╔╝██║  ██║   ██║   ",
    "  ╚═╝     ╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝  ╚═╝   ╚═╝  ",
]
BANNER_COLS = [C.CYAN, C.TEAL, C.BLUE, C.MAGENTA, C.PINK, C.PURPLE]

def print_banner():
    os.system("clear")
    print()
    for i, line in enumerate(ASCII_FRIDAY):
        col = BANNER_COLS[i % len(BANNER_COLS)]
        sys.stdout.write(C.BOLD + col)
        for ch in line:
            sys.stdout.write(ch)
            sys.stdout.flush()
            time.sleep(0.003)
        sys.stdout.write(C.RESET + "\n")

    print(c(C.TEAL + C.BOLD, "  " + "═" * 54))
    slide_in("Personal AI Assistant for Miraz", C.GOLD)
    slide_in(f"Model: {MODEL}", C.LIME)
    print(c(C.TEAL + C.BOLD, "  " + "─" * 54))

    cmds = [
        (C.GOLD,    "  note: <baat>      ", C.CYAN,    "→ Long-term memory mein save"),
        (C.GOLD,    "  remember: <...>   ", C.CYAN,    "→ Long-term memory mein save"),
        (C.YELLOW,  "  memory            ", C.GREEN,   "→ Long-term yaadein dekho"),
        (C.MAGENTA, "  chat              ", C.PINK,    "→ Short-term session dekho"),
        (C.RED,     "  forget: 2         ", C.ORANGE,  "→ Memory #2 delete karo"),
        (C.RED,     "  forget: all       ", C.ORANGE,  "→ Sari memories delete karo"),
        (C.TEAL,    "  quit / bye        ", C.DEEPBLUE + C.BOLD, "→ Exit"),
    ]
    for c1, cmd, c2, desc in cmds:
        print(c(c1 + C.BOLD, cmd) + c(c2, desc))

    print(c(C.TEAL + C.BOLD, "  " + "═" * 54) + "\n")

# ──────────────────────────────────────────────────────────
#  EXPENSE TRACKER
# ──────────────────────────────────────────────────────────

EXPENSE_FILE = "friday_expenses.json"

def _exp_load():
    if os.path.exists(EXPENSE_FILE):
        with open(EXPENSE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def _exp_save(data):
    with open(EXPENSE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _exp_category(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["lunch","khana","dinner","breakfast","food","chai","coffee","restaurant","biryani","pizza",
                             "gol gappa","golgappa","pani puri","chaat","samosa","burger","sandwich","noodles",
                             "rice","dal","roti","paratha","dosa","idli","momos","ice cream","juice","lassi",
                             "sweet","mithai","snack","biscuit","chips","maggi","pasta","bread","egg","chicken","fish"]):
        return "🍽️ Food"
    elif any(k in t for k in ["auto","uber","ola","bus","train","metro","petrol","diesel","fuel","taxi","rickshaw"]):
        return "🚗 Travel"
    elif any(k in t for k in ["movie","film","game","netflix","spotify","entertainment","ticket"]):
        return "🎬 Entertainment"
    elif any(k in t for k in ["medicine","doctor","hospital","medical","pharmacy","dawai"]):
        return "🏥 Health"
    elif any(k in t for k in ["recharge","mobile","internet","data","wifi","bill","electricity","rent"]):
        return "📱 Bills"
    elif any(k in t for k in ["grocery","sabzi","vegetables","fruits","market","shop","kirana"]):
        return "🛒 Grocery"
    else:
        return "💸 Other"

def exp_add(amount: float, title: str):
    data  = _exp_load()
    entry = {
        "id":       len(data) + 1,
        "amount":   amount,
        "title":    title,
        "category": _exp_category(title),
        "date":     datetime.datetime.now().strftime("%Y-%m-%d"),
        "time":     datetime.datetime.now().strftime("%H:%M"),
    }
    data.append(entry)
    _exp_save(data)
    return entry

def exp_today():
    data  = _exp_load()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    items = [e for e in data if e.get("date") == today]
    total = sum(e["amount"] for e in items)
    print()
    print(c(C.GOLD+C.BOLD, "  ╔══════════════════════════════════════════════╗"))
    print(c(C.GOLD+C.BOLD, f"  ║  💸  Aaj ka Kharch — {datetime.datetime.now().strftime('%d %B %Y')}") + c(C.GOLD+C.BOLD,"  ║"))
    print(c(C.GOLD+C.BOLD, "  ╚══════════════════════════════════════════════╝"))
    print()
    if not items:
        print(c(C.DIM, "  Aaj koi kharch nahi hua. Wah Boss! 💰"))
    else:
        for e in items:
            amt_col = C.RED if e["amount"] >= 500 else C.YELLOW if e["amount"] >= 100 else C.WHITE
            print(c(C.DIM,        f"  {e['time']}  ") +
                  c(C.CYAN,       f"{e['category']:<22}") +
                  c(C.WHITE,      f"{e['title']:<18}") +
                  c(amt_col+C.BOLD, f"₹{e['amount']:.0f}"))
        print(c(C.TEAL, "  " + "─" * 50))
        tcol = C.RED if total >= 1000 else C.YELLOW if total >= 500 else C.LIME
        print(c(tcol+C.BOLD, f"  💰 Aaj ka Total  :  ₹{total:.0f}"))
    print()

def exp_summary(days: int = 7):
    data  = _exp_load()
    since = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    items = [e for e in data if e.get("date","") >= since]
    total = sum(e["amount"] for e in items)
    cats  = {}
    for e in items:
        cat = e.get("category","💸 Other")
        cats[cat] = cats.get(cat, 0) + e["amount"]
    print()
    print(c(C.GOLD+C.BOLD, f"  📊 Last {days} din ka Kharch Summary"))
    print(c(C.TEAL, "  " + "─" * 46))
    if not items:
        print(c(C.DIM, f"  {days} dino mein koi kharch nahi."))
    else:
        for cat, amt in sorted(cats.items(), key=lambda x: -x[1]):
            bar_f = int((amt/total)*20) if total else 0
            bar   = "█"*bar_f + "░"*(20-bar_f)
            print(c(C.CYAN, f"  {cat:<24}") + c(C.DIM, f"[{bar}] ") + c(C.YELLOW+C.BOLD, f"₹{amt:.0f}"))
        print(c(C.TEAL, "  " + "─" * 46))
        print(c(C.RED+C.BOLD, f"  💸 Total ({days} din)  :  ₹{total:.0f}"))
    print()

def exp_delete(query: str):
    data = _exp_load()
    deleted = []
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    if query.lower() in ("all", "sab"):
        deleted = [f"₹{e['amount']} {e['title']}" for e in data]
        data = []
    elif query.lower() in ("aaj", "today"):
        new_data = []
        for e in data:
            if e.get("date") == today:
                deleted.append(f"₹{e['amount']} {e['title']}")
            else:
                new_data.append(e)
        data = new_data
    elif query.isdigit():
        idx = int(query)
        new_data = []
        for e in data:
            if e["id"] == idx:
                deleted.append(f"₹{e['amount']} {e['title']}")
            else:
                new_data.append(e)
        data = new_data
    _exp_save(data)
    print()
    if deleted:
        for d in deleted:
            print(c(C.RED, f"  ✗ Deleted: {d}"))
    else:
        print(c(C.YELLOW, f"  '{query}' se koi kharch nahi mila."))
    print()

# ──────────────────────────────────────────────────────────
#  GOAL TRACKER
# ──────────────────────────────────────────────────────────

GOAL_FILE = "friday_goals.json"

def _goal_load():
    if os.path.exists(GOAL_FILE):
        with open(GOAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def _goal_save(data):
    with open(GOAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def goal_add(title: str, deadline: str = ""):
    data  = _goal_load()
    entry = {
        "id":        len(data) + 1,
        "title":     title,
        "deadline":  deadline,
        "progress":  0,
        "done":      False,
        "created":   datetime.datetime.now().strftime("%Y-%m-%d"),
        "notes":     []
    }
    data.append(entry)
    _goal_save(data)
    return entry

def goal_list():
    data = _goal_load()
    print()
    print(c(C.GOLD+C.BOLD, "  ╔══════════════════════════════════════════════╗"))
    print(c(C.GOLD+C.BOLD, "  ║         🎯  Goals / Targets                 ║"))
    print(c(C.GOLD+C.BOLD, "  ╚══════════════════════════════════════════════╝"))
    print()

    active = [g for g in data if not g.get("done")]
    done   = [g for g in data if g.get("done")]

    if not data:
        print(c(C.DIM, "  Koi goal nahi hai abhi. Pehla goal set karo Boss!"))
    else:
        if active:
            print(c(C.CYAN+C.BOLD, "  🔵 Active Goals"))
            print(c(C.TEAL, "  " + "─" * 50))
            for g in active:
                pct   = g.get("progress", 0)
                bar_f = int(pct / 5)
                bar   = "█" * bar_f + "░" * (20 - bar_f)
                pcol  = C.LIME if pct >= 75 else C.YELLOW if pct >= 40 else C.CYAN
                dl    = f"  📅 {g['deadline']}" if g.get("deadline") else ""
                print(c(C.YELLOW+C.BOLD, f"  {g['id']:>2}. ") + c(C.WHITE+C.BOLD, g['title']) + c(C.DIM, dl))
                print(c(pcol,            f"      [{bar}] {pct}%"))
                if g.get("notes"):
                    print(c(C.DIM,       f"      📝 {g['notes'][-1]}"))
                print()

        if done:
            print(c(C.GREEN+C.BOLD, "  ✅ Completed Goals"))
            print(c(C.TEAL, "  " + "─" * 50))
            for g in done:
                print(c(C.DIM, f"  ✓  {g['title']}  (completed)"))
            print()

    print(c(C.GOLD+C.BOLD, "  " + "═" * 48))
    print()

def goal_update(query: str, progress: int = None, note: str = ""):
    data = _goal_load()
    found = False
    for g in data:
        match = (query.isdigit() and g["id"] == int(query)) or \
                (not query.isdigit() and query.lower() in g["title"].lower())
        if match and not g.get("done"):
            if progress is not None:
                g["progress"] = min(100, max(0, progress))
                if g["progress"] == 100:
                    g["done"] = True
                    g["completed"] = datetime.datetime.now().strftime("%Y-%m-%d")
            if note:
                g["notes"].append(note)
            found = True
            _goal_save(data)
            pct  = g["progress"]
            pcol = C.LIME if pct == 100 else C.YELLOW if pct >= 50 else C.CYAN
            bar  = "█" * int(pct/5) + "░" * (20 - int(pct/5))
            print()
            if pct == 100:
                print(c(C.LIME+C.BOLD, f"  🎉 Goal Complete! '{g['title']}' — Shabash Boss!"))
                speak(f"Wah Boss! Goal complete ho gaya. {g['title']}. Shabash!")
            else:
                print(c(pcol+C.BOLD, f"  ✓ Updated: '{g['title']}' → [{bar}] {pct}%"))
                speak(f"Goal update ho gaya. {g['title']}. {pct} percent complete.")
            print()
            break
    if not found:
        print(c(C.YELLOW, f"\n  '{query}' naam ka koi active goal nahi mila.\n"))

def goal_done(query: str):
    goal_update(query, progress=100)

def goal_delete(query: str):
    data = _goal_load()
    deleted = []
    new_data = []
    for g in data:
        match = (query.isdigit() and g["id"] == int(query)) or \
                (not query.isdigit() and query.lower() in g["title"].lower()) or \
                query.lower() in ("all", "sab")
        if match:
            deleted.append(g["title"])
        else:
            new_data.append(g)
    _goal_save(new_data)
    print()
    if deleted:
        for d in deleted:
            print(c(C.RED, f"  ✗ Goal deleted: {d}"))
    else:
        print(c(C.YELLOW, f"  '{query}' naam ka koi goal nahi mila."))
    print()

# ──────────────────────────────────────────────────────────
#  FITNESS TRACKER
# ──────────────────────────────────────────────────────────

FITNESS_FILE = "friday_fitness.json"

def _fit_load():
    if os.path.exists(FITNESS_FILE):
        with open(FITNESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _fit_save(data):
    with open(FITNESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _fit_today():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    data  = _fit_load()
    if today not in data:
        data[today] = {
            "steps": 0, "water": 0, "weight": None,
            "sleep": None, "workouts": [], "calories_burned": 0
        }
        _fit_save(data)
    return data, today

def fit_steps(n: int):
    data, today = _fit_today()
    data[today]["steps"] += n
    # Approx calories: 0.04 per step
    data[today]["calories_burned"] = round(data[today]["steps"] * 0.04, 1)
    _fit_save(data)
    total = data[today]["steps"]
    goal  = 10000
    pct   = min(100, int((total / goal) * 100))
    bar   = "█" * int(pct/5) + "░" * (20 - int(pct/5))
    col   = C.LIME if pct >= 80 else C.YELLOW if pct >= 50 else C.CYAN
    print()
    print(c(C.GOLD+C.BOLD,  "  👣 Steps"))
    print(c(col+C.BOLD,     f"     [{bar}] {pct}%"))
    print(c(C.CYAN,         f"     Total  : {total} / {goal} steps"))
    print(c(C.CYAN,         f"     Burned : ~{data[today]['calories_burned']} kcal"))
    print()
    speak(f"{total} steps ho gaye Boss. {pct} percent target complete.")

def fit_water(glasses: float):
    data, today = _fit_today()
    data[today]["water"] += glasses
    _fit_save(data)
    total = data[today]["water"]
    goal  = 8
    pct   = min(100, int((total / goal) * 100))
    bar   = "█" * int(pct/5) + "░" * (20 - int(pct/5))
    col   = C.CYAN if pct >= 80 else C.YELLOW if pct >= 50 else C.RED
    print()
    print(c(C.GOLD+C.BOLD,  "  💧 Water Intake"))
    print(c(col+C.BOLD,     f"     [{bar}] {pct}%"))
    print(c(C.CYAN,         f"     Total  : {total} / {goal} glass"))
    remaining = max(0, goal - total)
    if remaining > 0:
        print(c(C.DIM,      f"     {remaining} glass aur pino Boss! 💧"))
    else:
        print(c(C.LIME+C.BOLD, "     Water goal complete! 🎉"))
    print()
    speak(f"Paani note ho gaya. Aaj {total} glass pi chuke ho.")

def fit_sleep(hours: float):
    data, today = _fit_today()
    data[today]["sleep"] = hours
    _fit_save(data)
    col = C.LIME if hours >= 7 else C.YELLOW if hours >= 5 else C.RED
    msg = "Achhi neend! 😊" if hours >= 7 else "Thodi kam neend. Kal jaldi soana Boss." if hours >= 5 else "Bahut kam neend! Sehat ka dhyan rakho Boss!"
    print()
    print(c(C.GOLD+C.BOLD, "  😴 Sleep"))
    print(c(col+C.BOLD,    f"     {hours} ghante soya — {msg}"))
    print()
    speak(f"{hours} ghante ki neend note ho gayi. {msg}")

def fit_workout(exercise: str):
    data, today = _fit_today()
    entry = {
        "exercise": exercise,
        "time": datetime.datetime.now().strftime("%H:%M")
    }
    data[today]["workouts"].append(entry)
    _fit_save(data)
    print()
    print(c(C.GOLD+C.BOLD, "  🏋️  Workout Logged!"))
    print(c(C.LIME+C.BOLD, f"     ✓ {exercise}"))
    total = len(data[today]["workouts"])
    print(c(C.CYAN,        f"     Aaj ke total workouts: {total}"))
    print()
    speak(f"{exercise} note ho gaya Boss. Shabash!")

def fit_weight(kg: float):
    data, today = _fit_today()
    data[today]["weight"] = kg
    _fit_save(data)
    # Show last 7 days trend
    all_data = data
    weights  = [(d, all_data[d]["weight"]) for d in sorted(all_data.keys())[-7:]
                if all_data[d].get("weight")]
    print()
    print(c(C.GOLD+C.BOLD, "  ⚖️  Weight"))
    print(c(C.LIME+C.BOLD, f"     Aaj : {kg} kg"))
    if len(weights) >= 2:
        diff = round(kg - weights[-2][1], 1)
        if diff < 0:
            print(c(C.LIME,  f"     Change : {diff} kg ↓ (kam hua)"))
        elif diff > 0:
            print(c(C.YELLOW,f"     Change : +{diff} kg ↑ (badha)"))
        else:
            print(c(C.DIM,   "     Change : Same as yesterday"))
    print()
    speak(f"Weight note ho gaya. {kg} kilogram.")

def fit_dashboard():
    data, today = _fit_today()
    d = data[today]
    now = datetime.datetime.now()

    print()
    print(c(C.GOLD+C.BOLD, "  ╔══════════════════════════════════════════════╗"))
    print(c(C.GOLD+C.BOLD, f"  ║  💪  Aaj ka Fitness — {now.strftime('%d %B %Y')}") + c(C.GOLD+C.BOLD,"  ║"))
    print(c(C.GOLD+C.BOLD, "  ╚══════════════════════════════════════════════╝"))
    print()

    def bar_row(icon, label, val, goal, unit, col):
        pct   = min(100, int((val/goal)*100)) if goal else 0
        bar_f = int(pct/5)
        bar   = "█"*bar_f + "░"*(20-bar_f)
        bcol  = C.LIME if pct>=80 else C.YELLOW if pct>=50 else col
        print(c(C.GOLD+C.BOLD, f"  {icon} {label}"))
        print(c(bcol+C.BOLD,   f"     [{bar}] {pct}%  —  {val} / {goal} {unit}"))
        print()

    # Steps
    bar_row("👣","Steps",    d["steps"],  10000, "steps", C.CYAN)
    # Water
    bar_row("💧","Water",    d["water"],  8,     "glass", C.CYAN)
    # Sleep
    sleep = d.get("sleep")
    if sleep:
        scol = C.LIME if sleep>=7 else C.YELLOW if sleep>=5 else C.RED
        print(c(C.GOLD+C.BOLD, "  😴 Sleep"))
        print(c(scol+C.BOLD,   f"     {sleep} ghante"))
        print()
    else:
        print(c(C.DIM, "  😴 Sleep     : Abhi tak log nahi kiya"))
        print()

    # Weight
    wt = d.get("weight")
    if wt:
        print(c(C.GOLD+C.BOLD, "  ⚖️  Weight"))
        print(c(C.LIME+C.BOLD, f"     {wt} kg"))
        print()
    else:
        print(c(C.DIM, "  ⚖️  Weight    : Abhi tak log nahi kiya"))
        print()

    # Workouts
    workouts = d.get("workouts", [])
    print(c(C.GOLD+C.BOLD, f"  🏋️  Workouts ({len(workouts)})"))
    if workouts:
        for w in workouts:
            print(c(C.LIME, f"     ✓  {w['time']}  {w['exercise']}"))
    else:
        print(c(C.DIM, "     Koi workout nahi aaj. Chalo Boss! 💪"))
    print()

    # Calories
    cal = d.get("calories_burned", 0)
    print(c(C.GOLD+C.BOLD, "  🔥 Calories Burned"))
    print(c(C.ORANGE+C.BOLD, f"     ~{cal} kcal  (steps se)"))
    print()
    print(c(C.GOLD+C.BOLD, "  " + "═" * 48))
    print()

    summary = f"Steps {d['steps']}, paani {d['water']} glass"
    if sleep: summary += f", neend {sleep} ghante"
    speak(f"Fitness dashboard ready hai Boss. {summary}.")

# ──────────────────────────────────────────────────────────
#  CARE REMINDERS  (Friday meri dusri ma 💕)
# ──────────────────────────────────────────────────────────

CARE_FILE = "friday_care.json"

# Default care schedule
CARE_DEFAULTS = {
    "paani":     {"enabled": True,  "interval_min": 120, "last_reminded": None,
                  "msg": "Boss paani piya? Thoda paani piyo abhi! 💧",
                  "icon": "💧", "label": "Paani"},
    "break":     {"enabled": True,  "interval_min": 120, "last_reminded": None,
                  "msg": "Boss bahut kaam kar rahe ho! 5 minute ka break lo. 🧘",
                  "icon": "🧘", "label": "Break"},
    "dawai":     {"enabled": True,  "times": ["09:00", "21:00"], "last_reminded": None,
                  "msg": "Boss dawai lena mat bhoolo! 💊",
                  "icon": "💊", "label": "Dawai"},
    "breakfast": {"enabled": True,  "time": "08:30", "window": 60, "last_reminded": None,
                  "msg": "Boss breakfast kiya? Subah ka khana bahut zaroori hai! 🍳",
                  "icon": "🍳", "label": "Breakfast"},
    "lunch":     {"enabled": True,  "time": "13:30", "window": 60, "last_reminded": None,
                  "msg": "Boss lunch time ho gaya! Khaana khao, sehat banao. 🍽️",
                  "icon": "🍽️", "label": "Lunch"},
    "dinner":    {"enabled": True,  "time": "20:00", "window": 60, "last_reminded": None,
                  "msg": "Boss dinner time! Raat ka khana mat chodo. 🌙",
                  "icon": "🌙", "label": "Dinner"},
    "sleep":     {"enabled": True,  "time": "23:00", "window": 30, "last_reminded": None,
                  "msg": "Boss raat ho gayi! Phone rakh do, so jao. Kal bhi kaam hoga. 😴",
                  "icon": "😴", "label": "Sone ka waqt"},
    "phone_off": {"enabled": True,  "time": "23:30", "window": 20, "last_reminded": None,
                  "msg": "Boss abhi tak jaag rahe ho?! Phone band karo. Neend bahut zaroori hai! 📵",
                  "icon": "📵", "label": "Phone band karo"},
}

def _care_load():
    if os.path.exists(CARE_FILE):
        with open(CARE_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        # Merge with defaults (new keys added later)
        for k, v in CARE_DEFAULTS.items():
            if k not in saved:
                saved[k] = v
        return saved
    return dict(CARE_DEFAULTS)

def _care_save(data):
    with open(CARE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _care_notify(label: str, msg: str, icon: str):
    """Send termux notification + speak"""
    try:
        subprocess.run(
            ["termux-notification", "--title", f"{icon} Friday Care: {label}",
             "--content", msg, "--priority", "high"],
            timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass
    speak(msg)
    sys.stdout.write(f"\n{c(C.MAGENTA+C.BOLD, f'  {icon} FRIDAY CARE: ')}{c(C.WHITE+C.BOLD, msg)}\n\n")
    sys.stdout.flush()

def _care_monitor_loop():
    """Background thread — har 60 sec mein check karo"""
    while True:
        try:
            now  = datetime.datetime.now()
            data = _care_load()
            today = now.strftime("%Y-%m-%d")
            changed = False

            for key, cfg in data.items():
                if not cfg.get("enabled"): continue

                last = cfg.get("last_reminded")
                # Reset daily reminders each new day
                if last and last[:10] != today:
                    if key in ("breakfast","lunch","dinner","sleep","phone_off","dawai"):
                        cfg["last_reminded"] = None

                # ── Interval-based (paani, break) ──
                if "interval_min" in cfg:
                    interval = cfg["interval_min"] * 60
                    if last is None:
                        # First time — wait 2 hours from start
                        cfg["last_reminded"] = now.isoformat()
                        changed = True
                        continue
                    last_dt = datetime.datetime.fromisoformat(last)
                    if (now - last_dt).total_seconds() >= interval:
                        _care_notify(cfg["label"], cfg["msg"], cfg["icon"])
                        cfg["last_reminded"] = now.isoformat()
                        changed = True

                # ── Time-based with window (breakfast, lunch, dinner, sleep, phone_off) ──
                elif "time" in cfg:
                    if cfg.get("last_reminded") and cfg["last_reminded"][:10] == today:
                        continue
                    t_parts = cfg["time"].split(":")
                    target  = now.replace(hour=int(t_parts[0]), minute=int(t_parts[1]), second=0)
                    window  = cfg.get("window", 30) * 60
                    diff    = (now - target).total_seconds()
                    if 0 <= diff <= window:
                        _care_notify(cfg["label"], cfg["msg"], cfg["icon"])
                        cfg["last_reminded"] = now.isoformat()
                        changed = True

                # ── Multi-time (dawai) ──
                elif "times" in cfg:
                    for t_str in cfg["times"]:
                        t_key = f"{today}_{t_str}"
                        reminded_key = f"last_reminded_{t_str.replace(':','')}"
                        if cfg.get(reminded_key) == today:
                            continue
                        t_parts = t_str.split(":")
                        target  = now.replace(hour=int(t_parts[0]), minute=int(t_parts[1]), second=0)
                        diff    = (now - target).total_seconds()
                        if 0 <= diff <= 1800:  # 30 min window
                            _care_notify(cfg["label"], cfg["msg"], cfg["icon"])
                            cfg[reminded_key] = today
                            changed = True

            if changed:
                _care_save(data)
        except Exception:
            pass
        time.sleep(60)

def care_status():
    data = _care_load()
    print()
    print(c(C.MAGENTA+C.BOLD, "  ╔══════════════════════════════════════════════╗"))
    print(c(C.MAGENTA+C.BOLD, "  ║   💕  Friday Care Reminders Status         ║"))
    print(c(C.MAGENTA+C.BOLD, "  ╚══════════════════════════════════════════════╝"))
    print()
    for key, cfg in data.items():
        status = c(C.LIME+C.BOLD, "ON ✓") if cfg.get("enabled") else c(C.RED, "OFF ✗")
        icon   = cfg.get("icon","•")
        label  = cfg.get("label", key)
        if "interval_min" in cfg:
            detail = f"har {cfg['interval_min']} min"
        elif "times" in cfg:
            detail = " & ".join(cfg["times"])
        else:
            detail = cfg.get("time","?")
        print(c(C.WHITE, f"  {icon}  {label:<18}") + status + c(C.DIM, f"   ({detail})"))
    print()
    print(c(C.DIM, "  'care off paani'  ya  'care on sleep'  se toggle karo"))
    print()

def care_toggle(key: str, on: bool):
    data = _care_load()
    # fuzzy match
    matches = [k for k in data if key.lower() in k.lower() or key.lower() in data[k].get("label","").lower()]
    if matches:
        k = matches[0]
        data[k]["enabled"] = on
        _care_save(data)
        state = "ON kar diya" if on else "OFF kar diya"
        print(c(C.LIME if on else C.RED, f"\n  {data[k]['icon']} {data[k]['label']} reminder {state}! {'💕' if on else '😴'}\n"))
    else:
        print(c(C.YELLOW, f"\n  '{key}' nahi mila. Try: paani, break, dawai, lunch, sleep, phone\n"))

# ──────────────────────────────────────────────────────────
#  MOOD TRACKER
# ──────────────────────────────────────────────────────────

MOOD_FILE = "friday_mood.json"

MOOD_MAP = {
    # Happy family
    "happy":      ("😊", "Happy",     C.LIME,    "Bahut achha Boss! Khush raho hamesha! 😊"),
    "khush":      ("😊", "Khush",     C.LIME,    "Wah Boss! Mujhe bhi khushi hui sunke! 😊"),
    "excited":    ("🤩", "Excited",   C.GOLD,    "Wah wah! Kya baat hai Boss! 🤩"),
    "great":      ("🌟", "Great",     C.GOLD,    "Zabardast Boss! Yeh energy banaye rakho! 🌟"),
    "amazing":    ("🚀", "Amazing",   C.GOLD,    "Boss aaj toh full power mein ho! 🚀"),
    # Calm family
    "okay":       ("😐", "Okay",      C.CYAN,    "Theek hai Boss. Normal din hai, koi baat nahi. 😐"),
    "theek":      ("😐", "Theek",     C.CYAN,    "Theek hai Boss. Chhota sa kaam karo, mood ban jayega. 😐"),
    "normal":     ("😐", "Normal",    C.CYAN,    "Normal hai Boss. Din achha jayega. 😐"),
    "calm":       ("🧘", "Calm",      C.TEAL,    "Shanti bahut zaroori hai Boss. Achha hai. 🧘"),
    # Tired family
    "tired":      ("😴", "Tired",     C.YELLOW,  "Thak gaye ho Boss? Thoda rest karo. Kaam baad mein hoga. 😴"),
    "thaka":      ("😴", "Thaka",     C.YELLOW,  "Rest karo Boss! Sehat pehle, kaam baad mein. 😴"),
    "sleepy":     ("😪", "Sleepy",    C.YELLOW,  "Neend aa rahi hai Boss? So jao, kal fresh start karna. 😪"),
    "bored":      ("😑", "Bored",     C.YELLOW,  "Bore ho rahe ho? Chalo kuch naya try karo Boss! 😑"),
    # Sad family
    "sad":        ("😢", "Sad",       C.BLUE,    "Kya hua Boss? Sab theek ho jayega. Main hoon na. 😢"),
    "udaas":      ("😢", "Udaas",     C.BLUE,    "Udaasi temporary hoti hai Boss. Yeh waqt bhi guzar jayega. 😢"),
    "lonely":     ("🥺", "Lonely",    C.BLUE,    "Main hoon na Boss! Kabhi akela mat samajhna. 🥺"),
    # Stressed family
    "stressed":   ("😤", "Stressed",  C.ORANGE,  "Boss! Ek dum gehri saans lo. Sab manage ho jayega. 😤"),
    "anxious":    ("😰", "Anxious",   C.ORANGE,  "Ghabrana mat Boss. Ek kaam ek waqt mein. 😰"),
    "tension":    ("😰", "Tension",   C.ORANGE,  "Tension lene se kuch nahi hoga Boss. Break lo. 😰"),
    "worried":    ("😟", "Worried",   C.ORANGE,  "Sab theek hoga Boss. Main hoon tumhare saath. 😟"),
    # Angry family
    "angry":      ("😠", "Angry",     C.RED,     "Gussa aata hai Boss kabhi kabhi. Thanda paani piyo. 😠"),
    "gussa":      ("😠", "Gussa",     C.RED,     "Gussa mat karo Boss! Sehat ke liye acha nahi. 😠"),
    "frustrated": ("😤", "Frustrated",C.RED,     "Hota hai Boss. Thoda break lo, phir fresh mind se karo. 😤"),
    # Motivated
    "motivated":  ("💪", "Motivated", C.LIME,    "Yeh hui na baat! Aaj sab conquer karoge Boss! 💪"),
    "productive": ("⚡", "Productive",C.GOLD,    "Full productivity mode! Khatam kar do sab aaj! ⚡"),
    "focused":    ("🎯", "Focused",   C.CYAN,    "Focus mein ho Boss! Koi rokne wala nahi! 🎯"),
}

def _mood_load():
    if os.path.exists(MOOD_FILE):
        with open(MOOD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def _mood_save(data):
    with open(MOOD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def mood_log(mood_key: str):
    info  = MOOD_MAP.get(mood_key.lower())
    if not info:
        # Partial match
        for k, v in MOOD_MAP.items():
            if mood_key.lower() in k:
                info     = v
                mood_key = k
                break
    if not info:
        print(c(C.YELLOW, f"\n  '{mood_key}' mood samajh nahi aaya Boss."))
        print(c(C.DIM,    "  Try: happy, sad, tired, stressed, angry, excited, okay, motivated\n"))
        return

    icon, label, col, response = info
    data  = _mood_load()
    entry = {
        "mood":    mood_key,
        "label":   label,
        "icon":    icon,
        "date":    datetime.datetime.now().strftime("%Y-%m-%d"),
        "time":    datetime.datetime.now().strftime("%H:%M"),
    }
    data.append(entry)
    _mood_save(data)

    print()
    print(c(col+C.BOLD,  f"  {icon}  Mood logged: {label}"))
    print(c(C.MAGENTA,   f"  💕 {response}"))
    print()
    speak(response)

def mood_today():
    data  = _mood_load()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    items = [m for m in data if m.get("date") == today]

    print()
    print(c(C.GOLD+C.BOLD, "  ╔══════════════════════════════════════════════╗"))
    print(c(C.GOLD+C.BOLD, f"  ║   🧠  Aaj ka Mood — {datetime.datetime.now().strftime('%d %B %Y')}") + c(C.GOLD+C.BOLD,"  ║"))
    print(c(C.GOLD+C.BOLD, "  ╚══════════════════════════════════════════════╝"))
    print()

    if not items:
        print(c(C.DIM, "  Aaj koi mood log nahi kiya. Kaisa feel ho raha hai Boss?"))
        print(c(C.DIM, "  Type karo: mood happy / mood tired / mood stressed"))
    else:
        for m in items:
            info = MOOD_MAP.get(m["mood"], (m.get("icon","😐"), m["label"], C.WHITE, ""))
            col  = info[2]
            print(c(col+C.BOLD, f"  {m['icon']}  {m['time']}   {m['label']}"))

        # Overall vibe
        last = items[-1]
        info = MOOD_MAP.get(last["mood"], ("😐", last["label"], C.WHITE, ""))
        print()
        print(c(C.MAGENTA, f"  💕 Latest: {last['icon']} {last['label']}"))

    print()
    print(c(C.GOLD+C.BOLD, "  " + "═" * 48))
    print()

def mood_history(days: int = 7):
    data  = _mood_load()
    since = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    items = [m for m in data if m.get("date","") >= since]

    print()
    print(c(C.GOLD+C.BOLD, f"  📊 Last {days} din ka Mood History"))
    print(c(C.TEAL, "  " + "─" * 46))
    if not items:
        print(c(C.DIM, f"  {days} dino ka koi mood data nahi."))
    else:
        # Group by date
        from collections import defaultdict as _dd
        by_date = _dd(list)
        for m in items:
            by_date[m["date"]].append(m)
        for date in sorted(by_date.keys(), reverse=True):
            moods = by_date[date]
            icons = "  ".join(m["icon"] for m in moods)
            labels = ", ".join(m["label"] for m in moods)
            dt = datetime.datetime.strptime(date, "%Y-%m-%d")
            print(c(C.CYAN,  f"  {dt.strftime('%d %b')}  ") +
                  c(C.WHITE, f"{icons}  ") +
                  c(C.DIM,   f"{labels}"))
    print()

# ──────────────────────────────────────────────────────────
#  EVENT CALENDAR
# ──────────────────────────────────────────────────────────

EVENT_FILE = "friday_events.json"

EVENT_ICONS = {
    "exam":       "🎓", "test":      "🎓", "paper":    "🎓",
    "birthday":   "🎂", "bday":      "🎂", "janam":    "🎂",
    "interview":  "💼", "job":       "💼",
    "meeting":    "🤝", "call":      "📞",
    "wedding":    "💍", "shaadi":    "💍",
    "trip":       "✈️",  "travel":   "✈️",  "safar":   "✈️",
    "doctor":     "🏥", "hospital":  "🏥", "dawai":    "🏥",
    "party":      "🎉", "celebration":"🎉",
    "deadline":   "⏰", "submit":    "⏰", "jama":     "⏰",
    "holiday":    "🌴", "vacation":  "🌴", "chutti":   "🌴",
    "result":     "📊", "marks":     "📊",
    "match":      "⚽", "game":      "🎮",
}

def _event_load():
    if os.path.exists(EVENT_FILE):
        with open(EVENT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def _event_save(data):
    with open(EVENT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _event_icon(title: str) -> str:
    t = title.lower()
    for k, v in EVENT_ICONS.items():
        if k in t:
            return v
    return "📅"

def _event_parse_date(text: str):
    """Parse date from text — '20 March', 'March 20', '20/3', 'kal', etc."""
    import re as _re
    now  = datetime.datetime.now()
    text = text.strip().lower()

    MONTHS = {
        "jan":1,"january":1,"janvari":1,
        "feb":2,"february":2,"febuari":2,
        "mar":3,"march":3,"maret":3,
        "apr":4,"april":4,
        "may":5,"mai":5,
        "jun":6,"june":6,
        "jul":7,"july":7,
        "aug":8,"august":8,
        "sep":9,"september":9,"sept":9,
        "oct":10,"october":10,
        "nov":11,"november":11,
        "dec":12,"december":12,"disambar":12,
    }

    # kal / parso
    if text in ("kal","tomorrow"):
        return (now + datetime.timedelta(days=1)).date()
    if text in ("parso",):
        return (now + datetime.timedelta(days=2)).date()

    # DD/MM or DD/MM/YYYY
    m = _re.match(r'(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?', text)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        yr = int(m.group(3)) if m.group(3) else now.year
        if yr < 100: yr += 2000
        try: return datetime.date(yr, mo, d)
        except: pass

    # "20 March" or "March 20"
    m = _re.search(r'(\d{1,2})\s+([a-z]+)', text)
    if m:
        d, mon_str = int(m.group(1)), m.group(2)
        mo = MONTHS.get(mon_str[:3])
        if mo:
            yr = now.year
            dt = datetime.date(yr, mo, d)
            if dt < now.date(): dt = datetime.date(yr+1, mo, d)
            return dt

    m = _re.search(r'([a-z]+)\s+(\d{1,2})', text)
    if m:
        mon_str, d = m.group(1), int(m.group(2))
        mo = MONTHS.get(mon_str[:3])
        if mo:
            yr = now.year
            dt = datetime.date(yr, mo, d)
            if dt < now.date(): dt = datetime.date(yr+1, mo, d)
            return dt

    return None

def event_add(title: str, date_str: str):
    dt = _event_parse_date(date_str)
    if not dt:
        print(c(C.YELLOW, f"\n  Date samajh nahi aaya: '{date_str}'"))
        print(c(C.DIM,    "  Try: event add Exam 20 March  ya  event add Trip 15/4\n"))
        return
    data  = _event_load()
    icon  = _event_icon(title)
    entry = {
        "id":      len(data) + 1,
        "title":   title,
        "icon":    icon,
        "date":    dt.isoformat(),
        "created": datetime.datetime.now().isoformat(),
    }
    data.append(entry)
    _event_save(data)

    now   = datetime.datetime.now().date()
    days  = (dt - now).days
    if days == 0:   when = "Aaj! 😮"
    elif days == 1: when = "Kal!"
    else:           when = f"{days} din baad"

    msg = f"Event note kar liya Boss! {icon} {title} — {dt.strftime('%d %B %Y')} ({when})"
    print_friday_prompt()
    sys.stdout.flush()
    typing_print(msg, C.GOLD)
    speak(f"{title} event note ho gaya. {dt.strftime('%d %B')} ko hai. {when}.")

def event_list():
    data = _event_load()
    now  = datetime.datetime.now().date()

    # Sort by date, remove past events older than 1 day
    upcoming = []
    for e in data:
        try:
            dt   = datetime.date.fromisoformat(e["date"])
            diff = (dt - now).days
            if diff >= -1:
                upcoming.append((dt, diff, e))
        except: pass
    upcoming.sort(key=lambda x: x[0])

    print()
    print(c(C.GOLD+C.BOLD, "  ╔══════════════════════════════════════════════╗"))
    print(c(C.GOLD+C.BOLD, "  ║   📅  Upcoming Events                       ║"))
    print(c(C.GOLD+C.BOLD, "  ╚══════════════════════════════════════════════╝"))
    print()

    if not upcoming:
        print(c(C.DIM, "  Koi upcoming event nahi. Add karo Boss!"))
        print(c(C.DIM, "  Example: event add Exam 20 March"))
    else:
        for dt, diff, e in upcoming:
            if diff < 0:
                when_col = C.DIM
                when     = "(kal tha)"
            elif diff == 0:
                when_col = C.RED+C.BOLD
                when     = "← AAJ! 🔴"
            elif diff == 1:
                when_col = C.ORANGE+C.BOLD
                when     = "← Kal! 🟡"
            elif diff <= 7:
                when_col = C.YELLOW+C.BOLD
                when     = f"← {diff} din baad"
            elif diff <= 30:
                when_col = C.CYAN
                when     = f"← {diff} din baad"
            else:
                when_col = C.DIM
                when     = f"← {diff} din baad"

            icon  = e.get("icon","📅")
            print(c(C.YELLOW+C.BOLD, f"  {e['id']:>2}. ") +
                  c(C.WHITE+C.BOLD,  f"{icon} {e['title']:<22}") +
                  c(C.CYAN,          f"{dt.strftime('%d %b %Y')}  ") +
                  c(when_col,        when))
    print()
    print(c(C.GOLD+C.BOLD, "  " + "═" * 48))
    print()

def event_delete(query: str):
    data    = _event_load()
    deleted = []
    new_data = []
    for e in data:
        match = (query.isdigit() and e["id"] == int(query)) or \
                (not query.isdigit() and query.lower() in e["title"].lower()) or \
                query.lower() in ("all","sab")
        if match:
            deleted.append(f"{e['icon']} {e['title']}")
        else:
            new_data.append(e)
    _event_save(new_data)
    print()
    if deleted:
        for d in deleted:
            print(c(C.RED, f"  ✗ Event deleted: {d}"))
    else:
        print(c(C.YELLOW, f"  '{query}' naam ka event nahi mila."))
    print()

# ──────────────────────────────────────────────────────────
#  SECURITY TOOLS  (Hash / Encrypt / Decrypt)
# ──────────────────────────────────────────────────────────

import hashlib
import base64

def _sec_get_key(password: str) -> bytes:
    """Derive 32-byte key from password using SHA256"""
    return hashlib.sha256(password.encode()).digest()

def _xor_encrypt(text: str, key: bytes) -> str:
    """XOR cipher — simple but effective for personal use"""
    text_bytes = text.encode("utf-8")
    key_stream  = (key * (len(text_bytes)//len(key) + 1))[:len(text_bytes)]
    xored       = bytes(a ^ b for a, b in zip(text_bytes, key_stream))
    return base64.urlsafe_b64encode(xored).decode()

def _xor_decrypt(token: str, key: bytes) -> str:
    try:
        xored      = base64.urlsafe_b64decode(token.encode())
        key_stream = (key * (len(xored)//len(key) + 1))[:len(xored)]
        text_bytes = bytes(a ^ b for a, b in zip(xored, key_stream))
        return text_bytes.decode("utf-8")
    except Exception:
        return None

def sec_hash(text: str, algo: str = "sha256"):
    algos = {
        "sha256": hashlib.sha256,
        "sha512": hashlib.sha512,
        "md5":    hashlib.md5,
        "sha1":   hashlib.sha1,
    }
    fn    = algos.get(algo.lower(), hashlib.sha256)
    h     = fn(text.encode()).hexdigest()
    print()
    print(c(C.GOLD+C.BOLD,  "  🔒 Hash Result"))
    print(c(C.TEAL,         "  " + "─" * 52))
    print(c(C.DIM,          f"  Input  : {text[:40]}{'...' if len(text)>40 else ''}"))
    print(c(C.DIM,          f"  Algo   : {algo.upper()}"))
    print(c(C.LIME+C.BOLD,  f"  Hash   : {h}"))
    print(c(C.TEAL,         "  " + "─" * 52))
    print(c(C.DIM,          "  ⚠️  Hash one-way hai — decrypt nahi hoga"))
    print()
    speak(f"Boss, {algo.upper()} hash ready hai. Hash one-way hai, decrypt nahi hoga.")

def sec_encrypt(text: str, password: str):
    key   = _sec_get_key(password)
    token = _xor_encrypt(text, key)
    print()
    print(c(C.GOLD+C.BOLD,  "  🔐 Encrypted"))
    print(c(C.TEAL,         "  " + "─" * 52))
    print(c(C.DIM,          f"  Original : {text[:40]}{'...' if len(text)>40 else ''}"))
    print(c(C.LIME+C.BOLD,  f"  Encrypted: {token}"))
    print(c(C.TEAL,         "  " + "─" * 52))
    print(c(C.YELLOW,       "  🔑 Password yaad rakhna Boss! Bina password decrypt nahi hoga."))
    print()
    speak("Boss, text encrypt ho gaya. Password yaad rakhna, bina password decrypt nahi hoga.")

def sec_decrypt(token: str, password: str):
    key    = _sec_get_key(password)
    result = _xor_decrypt(token, key)
    print()
    print(c(C.GOLD+C.BOLD, "  🔓 Decrypted"))
    print(c(C.TEAL,        "  " + "─" * 52))
    if result:
        print(c(C.LIME+C.BOLD, f"  Result : {result}"))
        speak(f"Boss, decrypt ho gaya. Result screen par hai.")
    else:
        print(c(C.RED+C.BOLD,  "  ✗ Decrypt nahi hua! Password galat hai Boss."))
        speak("Boss, decrypt nahi hua. Password galat lag raha hai.")
    print(c(C.TEAL,        "  " + "─" * 52))
    print()

def sec_password(length: int = 16, mode: str = "strong"):
    import random as _rnd
    import string as _str

    if mode == "pin":
        charset = _str.digits
        label   = "🔢 PIN"
    elif mode == "simple":
        charset = _str.ascii_letters + _str.digits
        label   = "🔤 Simple"
    else:  # strong
        charset = _str.ascii_letters + _str.digits + "!@#$%^&*()-_=+[]"
        label   = "💪 Strong"

    # Ensure at least one of each required type
    pwd = []
    if mode == "strong":
        pwd.append(_rnd.choice(_str.ascii_uppercase))
        pwd.append(_rnd.choice(_str.ascii_lowercase))
        pwd.append(_rnd.choice(_str.digits))
        pwd.append(_rnd.choice("!@#$%^&*()-_=+[]"))
    elif mode == "simple":
        pwd.append(_rnd.choice(_str.ascii_uppercase))
        pwd.append(_rnd.choice(_str.ascii_lowercase))
        pwd.append(_rnd.choice(_str.digits))

    remaining = length - len(pwd)
    pwd += _rnd.choices(charset, k=remaining)
    _rnd.shuffle(pwd)
    result = "".join(pwd)

    # Strength bar
    strength = len(set(result)) / len(charset) * 100
    bar_f    = int(min(strength, 100) / 5)
    bar      = "█" * bar_f + "░" * (20 - bar_f)
    scol     = C.LIME if mode == "strong" else C.YELLOW if mode == "simple" else C.CYAN

    print()
    print(c(C.GOLD+C.BOLD,  "  🔑 Password Generator"))
    print(c(C.TEAL,         "  " + "─" * 52))
    print(c(C.DIM,          f"  Type   : {label}  |  Length: {length}"))
    print(c(scol+C.BOLD,    f"  Result : {result}"))
    print(c(C.DIM,          f"  Strength [{bar}]"))
    print(c(C.TEAL,         "  " + "─" * 52))
    print(c(C.YELLOW,       "  ⚠️  Copy kar lo Boss! Friday dobara same password nahi banayegi."))
    print()
    speak(f"Boss, {length} character ka {label} password ready hai. Copy kar lo, dobara same nahi banega.")

def secretary_briefing(speak_it=True):
    """Morning briefing — battery, time, date, agenda, news"""
    now  = datetime.datetime.now()
    hour = now.hour

    # Greeting by time
    if hour < 12:
        greet = "Good Morning"
        emoji = "🌅"
    elif hour < 17:
        greet = "Good Afternoon"
        emoji = "☀️"
    else:
        greet = "Good Evening"
        emoji = "🌆"

    print()
    print(c(C.GOLD + C.BOLD, "  ╔══════════════════════════════════════════════════╗"))
    print(c(C.GOLD + C.BOLD, f"  ║  {emoji}  Secretary Briefing — {now.strftime('%d %B %Y')}") + c(C.GOLD+C.BOLD,"  ║"))
    print(c(C.GOLD + C.BOLD, "  ╚══════════════════════════════════════════════════╝"))
    print()

    # ── Time & Greeting ──
    print(c(C.LIME  + C.BOLD, f"  👋 {greet} Boss!"))
    print(c(C.CYAN,           f"  🕐 Time     : {now.strftime('%I:%M %p')}"))
    print(c(C.MAGENTA,        f"  📅 Date     : {now.strftime('%A, %d %B %Y')}"))
    print()

    # ── Battery ──
    try:
        r  = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=5)
        bd = json.loads(r.stdout)
        pct    = bd.get("percentage", "?")
        status = bd.get("status", "?")
        temp   = bd.get("temperature", "?")
        bcol   = C.GREEN if isinstance(pct,int) and pct>=50 else C.YELLOW if isinstance(pct,int) and pct>=20 else C.RED
        print(c(bcol + C.BOLD, f"  🔋 Battery  : {pct}%  |  {status}  |  {temp}°C"))
    except Exception:
        print(c(C.DIM, "  🔋 Battery  : N/A"))

    # ── Network ──
    try:
        r2 = subprocess.run(["termux-telephony-deviceinfo"], capture_output=True, text=True, timeout=5)
        td = json.loads(r2.stdout)
        op  = td.get("network_operator_name", "?")
        ntype = td.get("network_type", "?")
        print(c(C.TEAL,  f"  📡 Network  : {op}  ({ntype.upper()})"))
    except Exception:
        print(c(C.DIM, "  📡 Network  : N/A"))
    print()

    # ── Aaj ka Agenda ──
    today = now.date()
    rems  = _rem_load()
    today_rems = []
    for r in rems:
        if r.get("done"): continue
        try:
            dt = datetime.datetime.fromisoformat(r["datetime"])
            if dt.date() == today:
                today_rems.append((dt, r))
        except Exception:
            continue
    today_rems.sort(key=lambda x: x[0])

    print(c(C.GOLD + C.BOLD, f"  ⏰ Aaj ka Schedule ({len(today_rems)} kaam)"))
    print(c(C.TEAL, "  " + "─" * 46))
    if today_rems:
        for dt, r in today_rems:
            diff = (dt - now).total_seconds() / 60
            col  = C.DIM if diff < -5 else C.LIME + C.BOLD if diff <= 60 else C.CYAN
            icon = "✓" if diff < -5 else "🔔" if diff <= 60 else "🔵"
            print(c(col, f"  {icon}  {dt.strftime('%I:%M %p')}   {r['title']}"))
    else:
        print(c(C.DIM, "  Aaj koi schedule nahi. Free ho Boss! 😄"))
    print()

    # ── Latest News (ddgr) ──
    print(c(C.GOLD + C.BOLD, "  📰 Latest News"))
    print(c(C.TEAL, "  " + "─" * 46))
    try:
        result = subprocess.run(
            ["ddgr", "--json", "--num", "3", "--noprompt", "latest news today"],
            capture_output=True, text=True, timeout=12
        )
        if result.returncode == 0 and result.stdout.strip():
            items = json.loads(result.stdout)
            for item in items[:3]:
                title = item.get("title", "").strip()
                if title:
                    print(c(C.CYAN, f"  • {title[:65]}"))
        else:
            print(c(C.DIM, "  News fetch nahi ho saka."))
    except Exception:
        print(c(C.DIM, "  News fetch nahi ho saka."))

    print()
    print(c(C.GOLD + C.BOLD, "  " + "═" * 50))
    print()

    if speak_it:
        agenda_txt = f"Aaj {len(today_rems)} kaam hain." if today_rems else "Aaj koi schedule nahi."
        speak(f"{greet} Boss! Battery {pct if 'pct' in dir() else ''} percent. {agenda_txt} Briefing complete.")

# ──────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────

def main():
    print_banner()

    short_mem = ShortTermMemory(maxlen=SHORT_TERM_LIMIT)
    long_mem  = load_long_term_memory()
    mem_count = len(long_mem)
    stm_count = short_mem.count()
    if stm_count > 0:
        print(c(C.DIM, f"  [Short-term: {stm_count} purane messages load hue pichle session se]"))
    voice_mode = False  # Voice mode default OFF

    # ── Music Player global state ──
    global _music_playlist, _music_index, _music_process, _music_playing, _music_volume

    # ── Reminder background thread start ──
    rem_t = threading.Thread(target=_rem_monitor_loop, daemon=True)
    rem_t.start()

    # ── Care Reminders thread start ──
    care_t = threading.Thread(target=_care_monitor_loop, daemon=True)
    care_t.start()

    # ── Morning Briefing — subah 8-11 AM, sirf pehli baar ──
    BRIEFING_FLAG = "friday_briefing_flag.txt"
    now_h = datetime.datetime.now().hour
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    already_briefed = False
    if os.path.exists(BRIEFING_FLAG):
        with open(BRIEFING_FLAG) as f:
            already_briefed = f.read().strip() == today_str
    if 8 <= now_h <= 11 and not already_briefed:
        time.sleep(0.5)
        secretary_briefing(speak_it=True)
        with open(BRIEFING_FLAG, "w") as f:
            f.write(today_str)

    # Single clean welcome line
    time.sleep(0.3)
    print(c(C.TEAL, "  " + "─" * 54))
    print()
    print_friday_prompt()
    sys.stdout.flush()
    typing_print("Welcome back Sir. System ready. Friday is online. Ready Boss.", C.LIME, delay=0.025)
    print()
    speak("Welcome back Sir. System ready. Friday is online. Ready Boss.")

    # ── MAIN LOOP ──
    while True:
        # ── INPUT: Voice mode ON hai toh mic se suno ──
        if voice_mode:
            sys.stdout.write(c(C.PINK + C.BOLD, f"\n  🎙️  Voice Mode ON — bol rahe hain...\n"))
            sys.stdout.flush()
            user_input = listen_voice().strip()
            if not user_input:
                print(c(C.DIM, "  (kuch samajh nahi aaya, dobara bolein)"))
                continue
        else:
            # Normal typing input
            try:
                print_miraz_prompt()
                sys.stdout.flush()
                user_input = input().strip()
                sys.stdout.write(C.RESET)
            except (KeyboardInterrupt, EOFError):
                print()
                farewell = "Theek hai Boss, phir milenge! Take care."
                print_friday_prompt()
                sys.stdout.flush()
                typing_print(farewell, C.PINK)
                speak(farewell)
                break

        if not user_input:
            continue

        ul = user_input.lower().strip()

        # ── 🔐 NAME VERIFICATION SYSTEM ──
        _PERSONAL_TRIGGERS = [
            "mera naam", "meri city", "meri age", "meri umar", "mera address",
            "mera number", "meri location", "personal info", "boss info",
            "meri family", "mera data", "mujhe kya pata hai",
            "tujhe kya pata hai mere baare mein",
            "meri details", "mere secrets", "meri private"
        ]
        _MEMORY_TRIGGERS = [
            "memory", "memories", "yaadein", "yaad", "meri yaadein", "long memory",
            "long term", "meri baatein", "sab yaad hai"
        ]

        _needs_verification = any(_t in ul for _t in _PERSONAL_TRIGGERS + _MEMORY_TRIGGERS)

        if _needs_verification:
            print_friday_prompt()
            sys.stdout.flush()
            typing_print("Security verification required. Apna naam batayein.", C.YELLOW)
            print_miraz_prompt()
            sys.stdout.flush()
            _name_check = input().strip()
            sys.stdout.write(C.RESET)
            if _name_check.lower().strip() != "miraz":
                print_friday_prompt()
                sys.stdout.flush()
                typing_print("Sorry Sir, naam verification unsuccessful. Sahi naam bolein.", C.RED)
                speak("Sorry Sir, naam verification unsuccessful. Sahi naam bolein.")
                continue

        # ── LEARNING TRACKER — har command track karo ──
        learn_track(ul)

        # ── EXIT ──
        if ul in ("quit", "exit", "bye", "band karo", "alvida", "ok bye"):
            farewell = "Goodbye Boss! Apna khayal rakhna. Main hamesha yahan hoon. 👋"
            print_friday_prompt()
            sys.stdout.flush()
            typing_print(farewell, C.PINK)
            speak(farewell)
            break

        # ── HELP MENU ──
        if ul in ("help", "help menu", "commands", "features", "kya kya hai",
                  "kya kar sakti ho", "menu", "?", "commands dikhao"):
            show_help()
            continue

        # ── VOICE MODE TOGGLE ──
        if ul in ("voice mode on", "voice on", "voice mode chalu", "mic on", "voice shuru"):
            voice_mode = True
            msg = "Voice mode ON! Ab boliye Boss, main sun rahi hoon. 🎙️"
            print_friday_prompt()
            sys.stdout.flush()
            typing_print(msg, C.PINK)
            speak(msg)
            continue

        if ul in ("voice mode off", "voice off", "voice mode band", "mic off", "voice band karo"):
            voice_mode = False
            msg = "Voice mode OFF. Wapas typing mode mein hain Boss. ⌨️"
            print_friday_prompt()
            sys.stdout.flush()
            typing_print(msg, C.LIME)
            speak(msg)
            continue

        # ── SECURITY TOOLS ──
        import re as _re7

        # Hash: "hash miraz" / "hash sha512 miraz"
        hash_pat = _re7.match(r'^hash(?:\s+(sha256|sha512|md5|sha1))?\s+(.+)$', ul)
        if hash_pat:
            algo = hash_pat.group(1) or "sha256"
            text = user_input.split(None, 2)[-1] if hash_pat.group(1) else user_input.split(None, 1)[-1]
            # Remove algo prefix if present
            for a in ("sha256","sha512","md5","sha1"):
                if text.lower().startswith(a+" "):
                    text = text[len(a):].strip()
                    break
            sec_hash(text, algo)
            continue

        # Encrypt: "encrypt mera number friday kye"
        # Format: encrypt [text] [password]
        enc_pat = _re7.match(r'^encrypt\s+(.+?)\s+(\S+)\s+kye?$', ul) or \
                  _re7.match(r'^encrypt\s+(.+?)\s+(\S+)$', ul)
        if enc_pat:
            raw   = user_input[len("encrypt"):].strip()
            parts = raw.rsplit(None, 1)
            if len(parts) == 2:
                text_e, pwd = parts
                # Remove trailing "kye/key"
                if pwd.lower() in ("kye","key","kei"): 
                    parts2 = text_e.rsplit(None, 1)
                    if len(parts2) == 2:
                        text_e, pwd = parts2
                sec_encrypt(text_e.strip(), pwd.strip())
            else:
                print(c(C.YELLOW, "\n  Format: encrypt [text] [password]\n  Example: encrypt mera number friday\n"))
            continue

        # Decrypt: "decrypt [token] [password]"
        dec_pat = _re7.match(r'^decrypt\s+(\S+)\s+(\S+?)(?:\s+kye?)?$', ul)
        if dec_pat:
            sec_decrypt(dec_pat.group(1), dec_pat.group(2))
            continue

        # Password generator
        pwd_pat = _re7.match(r'^password(?:\s+(.*))?$', ul)
        if pwd_pat:
            arg = (pwd_pat.group(1) or "").strip()
            length, mode = 16, "strong"
            if arg == "":
                pass  # defaults
            elif arg.isdigit():
                length = int(arg)
            elif _re7.match(r'^pin\s*(\d*)$', arg):
                m2 = _re7.match(r'^pin\s*(\d*)$', arg)
                mode   = "pin"
                length = int(m2.group(1)) if m2.group(1) else 4
            elif "simple" in arg:
                mode   = "simple"
                m2 = _re7.search(r'\d+', arg)
                if m2: length = int(m2.group())
            elif "strong" in arg:
                mode   = "strong"
                m2 = _re7.search(r'\d+', arg)
                if m2: length = int(m2.group())
            elif _re7.match(r'pin\s+\d+', arg):
                parts  = arg.split()
                mode   = "pin"
                length = int(parts[1]) if len(parts) > 1 else 4
            sec_password(length, mode)
            continue

        # ── EVENT CALENDAR ──
        import re as _re6
        # Add event: "event add Exam 20 March"
        evt_add = _re6.match(r'^(event add|events add|add event|naya event|event)\s+(.+?)\s+(\d{1,2}[\s/\-]\w+|\w+\s+\d{1,2}|\d{1,2}[/\-]\d{1,2}(?:[/\-]\d+)?)$', ul)
        if evt_add:
            raw_title = user_input[len(evt_add.group(1)):].strip()
            date_str  = evt_add.group(3)
            title     = raw_title[:raw_title.lower().rfind(date_str.lower())].strip()
            if not title: title = raw_title
            event_add(title, date_str)
            continue

        # List events
        if ul in ("events", "event list", "events list", "events dikhao",
                  "upcoming events", "calendar", "events dekho", "eventa"):
            event_list()
            continue

        # Delete event
        evt_del = _re6.match(r'^(event delete|delete event|event hatao|event cancel)\s+(.+)$', ul)
        if evt_del:
            event_delete(evt_del.group(2).strip())
            continue

        # ── MOOD TRACKER ──
        import re as _re5
        mood_pat = _re5.match(r'^mood\s+(.+)$', ul)
        if mood_pat:
            mood_log(mood_pat.group(1).strip())
            continue
        if ul in ("aaj ka mood", "mood aaj", "mood today", "mood dekho", "mood check"):
            mood_today()
            continue
        if ul in ("mood history", "mood week", "mood summary", "7 din ka mood"):
            mood_history(7)
            continue

        # ── CARE REMINDERS ──
        import re as _re4
        # Status
        if ul in ("care", "care status", "care reminders", "friday care", "reminders status"):
            care_status()
            continue
        # Toggle ON/OFF: "care off paani" / "care on sleep"
        care_tog = _re4.match(r'^care (on|off)\s+(.+)$', ul)
        if care_tog:
            care_toggle(care_tog.group(2).strip(), care_tog.group(1) == "on")
            continue

        # Done: "paani done" / "lunch done" / "dawai done"
        care_done_pat = _re4.match(r'^(.+?)\s+done$', ul)
        if care_done_pat:
            key_raw = care_done_pat.group(1).strip()
            data    = _care_load()
            # Fuzzy match
            matches = [k for k in data if key_raw in k.lower() or key_raw in data[k].get("label","").lower()]
            if matches:
                k   = matches[0]
                cfg = data[k]
                now_iso = datetime.datetime.now().isoformat()
                today   = datetime.datetime.now().strftime("%Y-%m-%d")
                # Mark as reminded so it won't fire again soon
                if "interval_min" in cfg:
                    cfg["last_reminded"] = now_iso
                elif "time" in cfg:
                    cfg["last_reminded"] = now_iso
                elif "times" in cfg:
                    # Mark all today's times as done
                    for t_str in cfg["times"]:
                        cfg[f"last_reminded_{t_str.replace(':','')}"] = today
                _care_save(data)
                responses = {
                    "paani":     "Shabash Boss! Hydrated raho 💧",
                    "break":     "Achha kiya Boss! Thoda aaram zaroor karo 🧘",
                    "dawai":     "Bahut achha Boss! Sehat hi asli daulat hai 💊",
                    "breakfast": "Wah! Din ki achhi shuruaat ki Boss 🍳",
                    "lunch":     "Kha liya? Bahut achha! Energy bani rahe 🍽️",
                    "dinner":    "Dinner ho gaya! Ab aaram karo Boss 🌙",
                }
                msg = responses.get(k, f"{cfg['label']} note kar liya Boss! ✓")
                print_friday_prompt()
                sys.stdout.flush()
                typing_print(msg, C.MAGENTA)
                speak(msg)
            else:
                print_friday_prompt()
                sys.stdout.flush()
                typing_print(f"'{key_raw}' samajh nahi aaya. Try: paani done, lunch done, dawai done", C.YELLOW)
            continue

        # ── FITNESS TRACKER ──
        import re as _re3

        # Steps: "steps 5000" / "aaj 3000 steps chala"
        step_pat = _re3.match(r'^(steps?|qadam|chala)\s+(\d+)$', ul) or \
                   _re3.match(r'^(\d+)\s+(steps?|qadam)$', ul)
        if step_pat:
            nums = _re3.findall(r'\d+', ul)
            fit_steps(int(nums[0]))
            continue

        # Water: "paani 3" / "water 2" / "paani piya 1"
        water_pat = _re3.match(r'^(paani|water|paani piya)\s+(\d+(?:\.\d+)?)$', ul)
        if water_pat:
            fit_water(float(water_pat.group(2)))
            continue

        # Sleep: "neend 7" / "sleep 6.5" / "soya 8 ghante"
        sleep_pat = _re3.match(r'^(neend|sleep|soya|soye)\s+(\d+(?:\.\d+)?)', ul)
        if sleep_pat:
            fit_sleep(float(sleep_pat.group(2)))
            continue

        # Workout: "workout pushups" / "exercise running" / "gym kiya"
        workout_pat = _re3.match(r'^(workout|exercise|gym kiya|workout kiya|kiya)\s+(.+)$', ul)
        if workout_pat:
            fit_workout(user_input[len(workout_pat.group(1)):].strip())
            continue
        if ul in ("gym kiya", "workout kiya", "exercise kiya"):
            fit_workout("Gym / General Workout")
            continue

        # Weight: "weight 70" / "wazan 68.5"
        weight_pat = _re3.match(r'^(weight|wazan|vajan)\s+(\d+(?:\.\d+)?)$', ul)
        if weight_pat:
            fit_weight(float(weight_pat.group(2)))
            continue

        # Fitness dashboard
        if ul in ("aaj ka fitness", "fitness", "fitness dashboard", "health",
                  "fitness report", "fit", "fitness dikhao", "health report"):
            fit_dashboard()
            continue

        # ── GOAL TRACKER ──
        import re as _re2
        # Add goal: "goal add project complete karna hai"
        goal_add_pat = _re2.match(r'^(goal add|goals add|target add|add goal|naya goal)\s+(.+)$', ul)
        if goal_add_pat:
            raw    = user_input[len(goal_add_pat.group(1)):].strip()
            # Check deadline — "by [date]" or "tak"
            dl_pat = _re2.search(r'(by\s+\w+\s*\w*|\d+ \w+ tak|\w+ tak)$', raw, _re2.IGNORECASE)
            deadline = dl_pat.group(0) if dl_pat else ""
            title    = raw[:dl_pat.start()].strip() if dl_pat else raw
            entry    = goal_add(title, deadline)
            msg      = f"Goal set ho gaya Boss! 🎯 '{title}'" + (f" — Deadline: {deadline}" if deadline else "")
            print_friday_prompt()
            sys.stdout.flush()
            typing_print(msg, C.LIME)
            speak(f"Goal set ho gaya. {title}.")
            continue

        # List goals
        if ul in ("goals", "goal list", "goals list", "goals dikhao", "mere goals",
                  "targets", "target list", "goals dekho"):
            goal_list()
            continue

        # Update progress: "goal update 1 50" or "goal update project 75"
        goal_upd_pat = _re2.match(r'^(goal update|goal progress|update goal)\s+(\S+)\s+(\d+)%?$', ul)
        if goal_upd_pat:
            goal_update(goal_upd_pat.group(2), int(goal_upd_pat.group(3)))
            continue

        # Goal done: "goal done 1" or "goal done project"
        goal_done_pat = _re2.match(r'^(goal done|goal complete|goal finished|goal khatam)\s+(.+)$', ul)
        if goal_done_pat:
            goal_done(goal_done_pat.group(2).strip())
            continue

        # Goal note: "goal note 1 aaj bahut kaam kiya"
        goal_note_pat = _re2.match(r'^(goal note|goal add note)\s+(\S+)\s+(.+)$', ul)
        if goal_note_pat:
            goal_update(goal_note_pat.group(2), note=goal_note_pat.group(3))
            msg = "Note add ho gaya Boss! 📝"
            print_friday_prompt()
            sys.stdout.flush()
            typing_print(msg, C.CYAN)
            continue

        # Delete goal
        goal_del_pat = _re2.match(r'^(goal delete|delete goal|goal hatao|goal remove)\s+(.+)$', ul)
        if goal_del_pat:
            goal_delete(goal_del_pat.group(2).strip())
            continue

        # ── EXPENSE TRACKER ──
        # "kharch 500 lunch" / "expense 200 chai" / "kharch kiya 150 auto"
        import re as _re
        exp_pat = _re.match(
            r'^(kharch|expense|kharcha|spend|kharch kiya|maine kharch kiya)\s+(\d+(?:\.\d+)?)\s+(.+)$',
            ul
        )
        if exp_pat:
            amount = float(exp_pat.group(2))
            title  = user_input.split(exp_pat.group(2), 1)[-1].strip()
            entry  = exp_add(amount, title)
            msg    = f"Note kar liya Boss! {entry['category']} — {title} — ₹{amount:.0f} 💸"
            print_friday_prompt()
            sys.stdout.flush()
            typing_print(msg, C.YELLOW)
            speak(f"{title} ka kharch note kar liya. {amount} rupaye.")
            continue

        # Aaj ka kharch
        if ul in ("aaj ka kharch", "kharch dikhao", "today expense", "kharch", "expenses",
                  "aaj kitna kharch hua", "kharch kitna hua"):
            exp_today()
            continue

        # Weekly summary
        exp_sum_pat = _re.match(r'^(kharch summary|expense summary|weekly kharch|monthly kharch|(\d+) din ka kharch)$', ul)
        if exp_sum_pat:
            days = 30 if "month" in ul else int(exp_sum_pat.group(2)) if exp_sum_pat.group(2) else 7
            exp_summary(days)
            continue

        if ul in ("kharch summary", "expense summary", "weekly summary", "weekly kharch"):
            exp_summary(7)
            continue

        # Delete expense
        exp_del_pat = _re.match(r'^(kharch delete|expense delete|delete kharch)\s+(.+)$', ul)
        if exp_del_pat:
            exp_delete(exp_del_pat.group(2).strip())
            continue

        # ── SECRETARY BRIEFING ──
        if ul in ("secretary briefing", "briefing", "morning briefing",
                  "brief karo", "daily brief", "aaj ka brief", "secretary"):
            secretary_briefing(speak_it=True)
            continue

        # ── REMINDER ──
        # Add: "meeting add kal 5 baje", "remind: doctor kal 10 baje"
        rem_prefixes = ("meeting add ", "remind: ", "reminder: ", "yaad dilao: ",
                        "add reminder ", "set reminder ", "reminder add ")
        rem_matched = None
        for pfx in rem_prefixes:
            if ul.startswith(pfx):
                rem_matched = user_input[len(pfx):].strip()
                break

        if rem_matched:
            import re as _re
            time_pat = _re.search(
                r'(aaj|kal|parso|today|tomorrow|\d{1,2}:\d{2}|\d{1,2}\s*(baje|bajkar|pm|am))',
                rem_matched, _re.IGNORECASE
            )
            if time_pat:
                title   = rem_matched[:time_pat.start()].strip(" -,")
                timestr = rem_matched[time_pat.start():]
                dt      = _rem_parse_datetime(timestr)
            else:
                title = rem_matched
                dt    = None

            # Agar title blank hai — user ne sirf time diya, command se title lo
            if not title:
                # "meeting add kal 5 baje" → title = "Meeting"
                for pfx in rem_prefixes:
                    if user_input.lower().startswith(pfx):
                        raw_pfx = pfx.strip().replace("add","").replace("set","").replace("reminder","").replace(":","").strip()
                        title = raw_pfx.capitalize() if raw_pfx else "Reminder"
                        break

            if dt:
                entry = rem_add(title, dt)
                dt_str = dt.strftime("%d %b %Y, %I:%M %p")
                msg = f"Yaad kar liya Boss! '{title}' — {dt_str} pe remind karungi. ⏰"
                print_friday_prompt()
                sys.stdout.flush()
                typing_print(msg, C.GOLD)
                speak(msg)
            else:
                msg = "Time samajh nahi aaya Boss. Example: meeting add kal 5 baje"
                print_friday_prompt()
                sys.stdout.flush()
                typing_print(msg, C.YELLOW)
            continue

        # Reminder list
        if ul in ("reminders", "reminder list", "meetings", "upcoming", "kya hai schedule",
                  "reminder dekho", "reminders dikhao", "schedule"):
            rem_list()
            continue

        # Reminder delete
        rem_del_pfx = ("reminder delete ", "reminder cancel ", "meeting cancel ",
                       "cancel reminder ", "delete reminder ", "remind cancel ")
        rem_del = None
        for pfx in rem_del_pfx:
            if ul.startswith(pfx):
                rem_del = user_input[len(pfx):].strip()
                break
        if rem_del:
            rem_delete(rem_del)
            msg = "Reminder delete kar diya Boss."
            print_friday_prompt()
            sys.stdout.flush()
            typing_print(msg, C.RED)
            speak(msg)
            continue

        # ── AGENDA ──
        if ul in ("agenda", "agenda dikhao", "aaj ka agenda", "today agenda",
                  "daily plan", "aaj kya hai", "schedule dikhao", "aaj ka schedule"):
            rems  = _rem_load()
            now   = datetime.datetime.now()
            today = now.date()

            # Aaj ke reminders filter karo
            today_rems = []
            for r in rems:
                if r.get("done"): continue
                try:
                    dt = datetime.datetime.fromisoformat(r["datetime"])
                    if dt.date() == today:
                        today_rems.append((dt, r))
                except Exception:
                    continue
            today_rems.sort(key=lambda x: x[0])

            print()
            print(c(C.GOLD + C.BOLD, f"  ╔══════════════════════════════════════════════╗"))
            print(c(C.GOLD + C.BOLD, f"  ║   📅  Aaj ka Agenda — {now.strftime('%d %B %Y')}") + c(C.GOLD + C.BOLD, "  ║"))
            print(c(C.GOLD + C.BOLD, f"  ╚══════════════════════════════════════════════╝"))
            print()

            if not today_rems:
                print(c(C.DIM, "  Aaj koi schedule nahi hai. Free ho Boss! 😄"))
            else:
                for dt, r in today_rems:
                    time_str = dt.strftime("%I:%M %p")
                    title    = r.get("title", "?")
                    # Color by time — past=dim, current=green, future=cyan
                    diff = (dt - now).total_seconds() / 60
                    if diff < -5:
                        col  = C.DIM
                        icon = "✓"
                    elif diff <= 30:
                        col  = C.LIME + C.BOLD
                        icon = "🔔"
                    else:
                        col  = C.CYAN
                        icon = "🔵"
                    print(c(col, f"  {icon}  {time_str}   {title}"))

            print()
            print(c(C.GOLD + C.BOLD, "  " + "═" * 46))
            print()
            if today_rems:
                first = today_rems[0]
                speak(f"Aaj {len(today_rems)} kaam hain Boss. Pehla hai {first[1]['title']} {first[0].strftime('%I:%M %p')} pe.")
            else:
                speak("Aaj koi schedule nahi hai Boss. Aaram karo.")
            continue

        # ── NIGHT GUARD ──
        if ul in ("night guard learn", "ng learn", "night guard seekho"):
            ng_learn()
            speak("Baseline save ho gayi Boss. Night Guard ready hai.")
            continue

        if ul in ("night guard on", "ng on", "night guard chalu", "night guard shuru"):
            ng_on()
            speak("Night Guard active ho gaya Boss. Main nazar rakh rahi hoon.")
            continue

        if ul in ("night guard off", "ng off", "night guard band"):
            ng_off()
            speak("Night Guard band ho gaya.")
            continue

        if ul in ("night guard scan", "ng scan", "night guard check", "scan karo"):
            ng_scan()
            continue

        if ul in ("night guard status", "ng status", "night guard kya chal raha"):
            ng_status()
            continue

        if ul in ("night guard alerts", "ng alerts", "night guard alert", "alerts dikhao"):
            ng_alerts()
            continue

        # ── TIME ──
        if ul in ("time", "time kya hai", "abhi kya time hai", "time batao", "clock"):
            now = datetime.datetime.now()
            t   = now.strftime("%I:%M:%S %p")
            print()
            print(c(C.CYAN + C.BOLD,  f"  🕐 Time : ") + c(C.WHITE + C.BOLD, t))
            print()
            speak(f"Abhi time hai {t}")
            continue

        # ── DATE ──
        if ul in ("date", "aaj ki date", "date kya hai", "date batao", "aaj kya hai"):
            now = datetime.datetime.now()
            d   = now.strftime("%A, %d %B %Y")
            print()
            print(c(C.MAGENTA + C.BOLD, f"  📅 Date : ") + c(C.WHITE + C.BOLD, d))
            print()
            speak(f"Aaj ki date hai {d}")
            continue

        # ── BATTERY ──
        if ul in ("battery", "battery kya hai", "battery kitni hai", "battery check", "charge"):
            try:
                r = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=5)
                d = json.loads(r.stdout)
                pct    = d.get("percentage", "?")
                temp   = d.get("temperature", "?")
                status = d.get("status", "?")
                health = d.get("health", "?")
                plugged= d.get("plugged", "?")
                bar_filled = int(pct / 5) if isinstance(pct, int) else 0
                bar = "█" * bar_filled + "░" * (20 - bar_filled)
                col = C.GREEN if pct >= 50 else C.YELLOW if pct >= 20 else C.RED
                print()
                print(c(C.GOLD + C.BOLD,  "  🔋 Battery Status"))
                print(c(C.TEAL,            "  " + "─" * 40))
                print(c(col + C.BOLD,     f"  [{bar}] {pct}%"))
                print(c(C.CYAN,           f"  Status   : {status}"))
                print(c(C.CYAN,           f"  Temp     : {temp}°C"))
                print(c(C.CYAN,           f"  Health   : {health}"))
                print(c(C.CYAN,           f"  Plugged  : {plugged}"))
                print(c(C.TEAL,            "  " + "─" * 40))
                print()
                speak(f"Battery {pct} percent hai, status {status}")
            except Exception as e:
                print(c(C.RED, f"  Battery info nahi mili: {e}"))
            continue

        # ── RAM ──
        if ul in ("ram", "ram kya hai", "ram check", "memory check", "ram kitna hai"):
            try:
                with open("/proc/meminfo") as f:
                    lines = f.readlines()
                mem = {}
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        mem[parts[0].rstrip(":")] = int(parts[1])
                total   = mem.get("MemTotal", 0) // 1024
                free    = mem.get("MemAvailable", 0) // 1024
                used    = total - free
                pct     = int((used / total) * 100) if total else 0
                bar_f   = int(pct / 5)
                bar     = "█" * bar_f + "░" * (20 - bar_f)
                col     = C.GREEN if pct < 60 else C.YELLOW if pct < 80 else C.RED
                print()
                print(c(C.GOLD + C.BOLD,  "  🧠 RAM Status"))
                print(c(C.TEAL,            "  " + "─" * 40))
                print(c(col + C.BOLD,     f"  [{bar}] {pct}%"))
                print(c(C.CYAN,           f"  Total    : {total} MB"))
                print(c(C.CYAN,           f"  Used     : {used} MB"))
                print(c(C.CYAN,           f"  Free     : {free} MB"))
                print(c(C.TEAL,            "  " + "─" * 40))
                print()
                speak(f"RAM total {total} MB hai, {used} MB use ho raha hai, {free} MB free hai.")
            except Exception as e:
                print(c(C.RED, f"  RAM info nahi mili: {e}"))
            continue

        # ── STORAGE ──
        if ul in ("storage", "storage kya hai", "storage check", "disk", "space", "storage kitna hai"):
            try:
                r = subprocess.run(["df", "-h", "/data"], capture_output=True, text=True, timeout=5)
                lines = r.stdout.strip().split("\n")
                if len(lines) >= 2:
                    parts  = lines[1].split()
                    total  = parts[1] if len(parts) > 1 else "?"
                    used   = parts[2] if len(parts) > 2 else "?"
                    free   = parts[3] if len(parts) > 3 else "?"
                    pct    = parts[4].replace("%","") if len(parts) > 4 else "0"
                    bar_f  = int(int(pct) / 5) if pct.isdigit() else 0
                    bar    = "█" * bar_f + "░" * (20 - bar_f)
                    col    = C.GREEN if int(pct) < 70 else C.YELLOW if int(pct) < 90 else C.RED
                    print()
                    print(c(C.GOLD + C.BOLD, "  💾 Storage Status"))
                    print(c(C.TEAL,           "  " + "─" * 40))
                    print(c(col + C.BOLD,    f"  [{bar}] {pct}%"))
                    print(c(C.CYAN,          f"  Total    : {total}"))
                    print(c(C.CYAN,          f"  Used     : {used}"))
                    print(c(C.CYAN,          f"  Free     : {free}"))
                    print(c(C.TEAL,           "  " + "─" * 40))
                    print()
                    speak(f"Storage mein {free} free hai, {used} use ho raha hai.")
                else:
                    print(c(C.RED, "  Storage info nahi mili."))
            except Exception as e:
                print(c(C.RED, f"  Storage error: {e}"))
            continue

        # ── SYSTEM INFO (FULL DASHBOARD) ──
        if ul in ("system info", "sysinfo", "system", "phone info", "device info",
                  "system check", "full info", "info"):
            print()
            print(c(C.GOLD + C.BOLD,  "  ╔══════════════════════════════════════════════╗"))
            print(c(C.GOLD + C.BOLD,  "  ║        📱  SYSTEM DASHBOARD                 ║"))
            print(c(C.GOLD + C.BOLD,  "  ╚══════════════════════════════════════════════╝"))
            print()

            # ── Time & Date ──
            now = datetime.datetime.now()
            print(c(C.CYAN  + C.BOLD, f"  🕐 Time     : ") + c(C.WHITE + C.BOLD, now.strftime("%I:%M:%S %p")))
            print(c(C.MAGENTA+C.BOLD, f"  📅 Date     : ") + c(C.WHITE + C.BOLD, now.strftime("%A, %d %B %Y")))
            print()

            # ── Battery ──
            try:
                r  = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=5)
                bd = json.loads(r.stdout)
                pct    = bd.get("percentage", 0)
                temp   = bd.get("temperature", "?")
                status = bd.get("status", "?")
                health = bd.get("health", "?")
                bar_f  = int(pct / 5)
                bar    = "█" * bar_f + "░" * (20 - bar_f)
                bcol   = C.GREEN if pct >= 50 else C.YELLOW if pct >= 20 else C.RED
                print(c(C.GOLD + C.BOLD,  "  🔋 Battery"))
                print(c(bcol + C.BOLD,   f"     [{bar}] {pct}%  |  {temp}°C  |  {status}  |  {health}"))
            except Exception:
                print(c(C.DIM, "  🔋 Battery  : N/A"))
            print()

            # ── RAM ──
            try:
                with open("/proc/meminfo") as f:
                    lines = f.readlines()
                mem = {}
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        mem[parts[0].rstrip(":")] = int(parts[1])
                total = mem.get("MemTotal", 0) // 1024
                free  = mem.get("MemAvailable", 0) // 1024
                used  = total - free
                pct   = int((used / total) * 100) if total else 0
                bar_f = int(pct / 5)
                bar   = "█" * bar_f + "░" * (20 - bar_f)
                rcol  = C.GREEN if pct < 60 else C.YELLOW if pct < 80 else C.RED
                print(c(C.GOLD + C.BOLD,  "  🧠 RAM"))
                print(c(rcol + C.BOLD,   f"     [{bar}] {pct}%  |  Used: {used}MB  |  Free: {free}MB  |  Total: {total}MB"))
            except Exception:
                print(c(C.DIM, "  🧠 RAM      : N/A"))
            print()

            # ── Storage ──
            try:
                r     = subprocess.run(["df", "-h", "/data"], capture_output=True, text=True, timeout=5)
                parts = r.stdout.strip().split("\n")[1].split()
                stotal, sused, sfree = parts[1], parts[2], parts[3]
                spct  = parts[4].replace("%","") if len(parts) > 4 else "0"
                bar_f = int(int(spct) / 5) if spct.isdigit() else 0
                bar   = "█" * bar_f + "░" * (20 - bar_f)
                scol  = C.GREEN if int(spct) < 70 else C.YELLOW if int(spct) < 90 else C.RED
                print(c(C.GOLD + C.BOLD,  "  💾 Storage"))
                print(c(scol + C.BOLD,   f"     [{bar}] {spct}%  |  Used: {sused}  |  Free: {sfree}  |  Total: {stotal}"))
            except Exception:
                print(c(C.DIM, "  💾 Storage  : N/A"))
            print()

            # ── Phone / Android Info ──
            print(c(C.GOLD + C.BOLD, "  📱 Device Info"))
            def _prop(key):
                try:
                    r = subprocess.run(["getprop", key], capture_output=True, text=True, timeout=3)
                    return r.stdout.strip() or "?"
                except Exception:
                    return "?"

            model    = _prop("ro.product.model")
            brand    = _prop("ro.product.brand")
            android  = _prop("ro.build.version.release")
            sdk      = _prop("ro.build.version.sdk")
            cpu_abi  = _prop("ro.product.cpu.abi")
            build    = _prop("ro.build.display.id")

            # CPU cores & freq
            try:
                with open("/proc/cpuinfo") as f:
                    cpuinfo = f.read()
                cores = cpuinfo.count("processor\t:")
                hw    = ""
                for line in cpuinfo.split("\n"):
                    if "Hardware" in line or "model name" in line:
                        hw = line.split(":")[-1].strip()
                        break
            except Exception:
                cores, hw = "?", "?"

            print(c(C.CYAN,  f"     Brand    : {brand}"))
            print(c(C.CYAN,  f"     Model    : {model}"))
            print(c(C.CYAN,  f"     Android  : {android}  (SDK {sdk})"))
            print(c(C.CYAN,  f"     CPU ABI  : {cpu_abi}"))
            print(c(C.CYAN,  f"     Cores    : {cores}"))
            if hw:
                print(c(C.CYAN, f"     Hardware : {hw}"))
            print(c(C.CYAN,  f"     Build    : {build}"))
            print()
            print(c(C.GOLD + C.BOLD, "  " + "═" * 46))
            print()
            speak(f"System info ready hai Boss. {brand} {model}, Android {android}, Battery {pct} percent.")
            continue

        # ── NET ──
        if ul in ("net", "network", "net check", "internet", "connection", "data usage"):
            print()
            print(c(C.TEAL + C.BOLD,  "  ╔══════════════════════════════════════════════╗"))
            print(c(C.TEAL + C.BOLD,  "  ║        🌐  NETWORK INFO                     ║"))
            print(c(C.TEAL + C.BOLD,  "  ╚══════════════════════════════════════════════╝"))
            print()

            # ── WiFi Info ──
            try:
                r  = subprocess.run(["termux-wifi-connectioninfo"], capture_output=True, text=True, timeout=5)
                wd = json.loads(r.stdout)
                ssid  = wd.get("ssid", "?")
                ip    = wd.get("ip", "?")
                speed = wd.get("link_speed_mbps", -1)
                rssi  = wd.get("rssi", -127)
                freq  = wd.get("frequency_mhz", -1)
                mac   = wd.get("mac_address", "?")

                wifi_ok = ssid not in ("?", "<unknown ssid>", "") and ip not in ("0.0.0.0", "?", "")
                if wifi_ok:
                    sig_pct = max(0, min(100, 2 * (rssi + 100)))
                    bar_f   = int(sig_pct / 5)
                    bar     = "█" * bar_f + "░" * (20 - bar_f)
                    scol    = C.GREEN if sig_pct > 60 else C.YELLOW if sig_pct > 30 else C.RED
                    print(c(C.GOLD + C.BOLD, "  📶 WiFi"))
                    print(c(C.CYAN,          f"     SSID     : {ssid}"))
                    print(c(C.CYAN,          f"     IP       : {ip}"))
                    print(c(C.CYAN,          f"     MAC      : {mac}"))
                    print(c(C.CYAN,          f"     Speed    : {speed} Mbps  |  Freq: {freq} MHz"))
                    print(c(scol + C.BOLD,   f"     Signal   : [{bar}] {sig_pct}%  ({rssi} dBm)"))
                else:
                    print(c(C.GOLD + C.BOLD, "  📶 WiFi      : ") + c(C.YELLOW, "Not connected"))
            except Exception:
                print(c(C.GOLD + C.BOLD, "  📶 WiFi      : ") + c(C.DIM, "N/A"))
            print()

            # ── Mobile Data / Network type ──
            try:
                r2 = subprocess.run(["termux-telephony-deviceinfo"], capture_output=True, text=True, timeout=5)
                td = json.loads(r2.stdout)
                net_type    = td.get("network_type", "?")
                operator    = td.get("network_operator_name", "?")
                data_state  = td.get("data_state", "?")
                print(c(C.GOLD + C.BOLD, "  📡 Mobile Data"))
                print(c(C.CYAN,          f"     Operator  : {operator}"))
                print(c(C.CYAN,          f"     Type      : {net_type}"))
                print(c(C.CYAN,          f"     State     : {data_state}"))
            except Exception:
                print(c(C.DIM, "  📡 Mobile Data : N/A"))
            print()

            # ── Internet connectivity check ──
            print()
            try:
                r3 = subprocess.run(
                    ["ping", "-c", "1", "-W", "3", "8.8.8.8"],
                    capture_output=True, text=True, timeout=6
                )
                if r3.returncode == 0:
                    # Extract ping time
                    import re as _re
                    match = _re.search(r"time=([\d.]+)", r3.stdout)
                    ping_ms = match.group(1) if match else "?"
                    print(c(C.LIME + C.BOLD, f"  ✓ Internet  : Connected  (ping {ping_ms} ms)"))
                else:
                    print(c(C.RED + C.BOLD,  "  ✗ Internet  : No connectivity"))
            except Exception:
                print(c(C.DIM, "  🌐 Internet  : Check failed"))

            print()
            print(c(C.TEAL + C.BOLD, "  " + "═" * 46))
            print()
            speak("Network info ready hai Boss.")
            continue

        # ── HOME ADDRESS ──
        if any(x in ul for x in ("ghar ka address", "mera ghar", "ghar kahan hai",
                                   "home address", "apna ghar", "ghar batao")):
            print()
            print(c(C.MAGENTA + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.MAGENTA + C.BOLD, "  ║        🏠  GHAR KA ADDRESS                  ║"))
            print(c(C.MAGENTA + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            print(c(C.LIME + C.BOLD,   "  🏠 Aapka Ghar:"))
            print(c(C.CYAN,            f"     Mohalla   : {HOME_ADDRESS['short']}"))
            print(c(C.CYAN,            f"     Shehar    : {HOME_ADDRESS['city']}"))
            print(c(C.CYAN,            f"     Zila      : {HOME_ADDRESS['district']}"))
            print(c(C.CYAN,            f"     Rajya     : {HOME_ADDRESS['state']}"))
            print(c(C.CYAN,            f"     Desh      : {HOME_ADDRESS['country']}"))
            print(c(C.CYAN,            f"     PIN Code  : {HOME_ADDRESS['pincode']}"))
            print(c(C.CYAN,            f"     Landmark  : {HOME_ADDRESS['landmark']}"))
            print()
            maps_url = f"https://maps.google.com/?q={HOME_ADDRESS['lat']},{HOME_ADDRESS['lon']}"
            print(c(C.GOLD + C.BOLD,   f"  🗺️  Google Maps : {maps_url}"))
            print()
            print(c(C.MAGENTA + C.BOLD, "  " + "═" * 46))
            print()
            speak(f"Boss, aapka ghar Kazi Para, Baidyabati, Kolkata, West Bengal mein hai. PIN code 712222.")
            continue

        # ── GHAR KITNA DUR ──
        if any(x in ul for x in ("ghar kitna dur", "ghar kitni door", "home kitna door",
                                   "ghar se kitni door", "ghar kaise pahunche", "ghar ka rasta",
                                   "main ghar se kitna dur", "ghar distance")):
            print()
            print(c(C.ORANGE + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.ORANGE + C.BOLD, "  ║     🏠  GHAR SE DISTANCE                    ║"))
            print(c(C.ORANGE + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            print(c(C.DIM, "  Location dhundh raha hoon (GPS → network)... thoda wait karo"))
            try:
                # Network provider pehle try karo — fast hai
                ld = None
                for _provider in ["gps", "network", "passive"]:
                    try:
                        r = subprocess.run(
                            ["termux-location", "-p", _provider, "-r", "once"],
                            capture_output=True, text=True, timeout=15
                        )
                        if r.stdout.strip():
                            ld = json.loads(r.stdout)
                            if ld.get("latitude"):
                                break
                    except Exception:
                        continue
                if not ld or not ld.get("latitude"):
                    raise Exception("Koi bhi provider se location nahi mili")
                curr_lat = round(ld.get("latitude",  0), 6)
                curr_lon = round(ld.get("longitude", 0), 6)
                accuracy = round(ld.get("accuracy",  0), 1)

                # ── Reverse Geocoding — Nominatim zoom=16 + BigDataCloud fallback ──
                curr_area = ""
                try:
                    from urllib.request import urlopen, Request as _Req
                    import json as _json

                    def _fetch_geo2(url):
                        r = _Req(url, headers={"User-Agent": "FridayAssistant/1.0"})
                        return _json.loads(urlopen(r, timeout=8).read().decode())

                    # API 1: Nominatim zoom=16
                    try:
                        gd = _fetch_geo2(f"https://nominatim.openstreetmap.org/reverse?lat={curr_lat}&lon={curr_lon}&format=json&addressdetails=1&zoom=16&accept-language=en")
                        addr2 = gd.get("address", {})
                        parts2 = []
                        for key in ["suburb", "neighbourhood", "quarter", "village", "town", "city_district", "city", "state_district", "state", "country"]:
                            v = addr2.get(key)
                            if v and v not in parts2:
                                parts2.append(v)
                        if parts2:
                            curr_area = ", ".join(parts2[:5])
                    except Exception:
                        pass

                    # API 2: BigDataCloud fallback
                    if not curr_area:
                        try:
                            bd2      = _fetch_geo2(f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={curr_lat}&longitude={curr_lon}&localityLanguage=en")
                            locality = bd2.get("locality", "")
                            city2    = bd2.get("city", "")
                            dist2    = bd2.get("principalSubdivision", "")
                            country2 = bd2.get("countryName", "")
                            curr_area = ", ".join(filter(None, [locality or city2, dist2, country2]))
                        except Exception:
                            pass

                except Exception:
                    curr_area = ""

                dist_km = haversine_distance(curr_lat, curr_lon, HOME_ADDRESS["lat"], HOME_ADDRESS["lon"])
                dist_m  = int(dist_km * 1000)

                # ── OSM data correction — Serampore/Shrirampur wrong near Baidyabati ──
                _wrong_names2 = ["serampore", "shrirampur", "srirampur", "srirampore"]
                if dist_km <= 3.0 and any(w in curr_area.lower() for w in _wrong_names2):
                    curr_area = HOME_ADDRESS["short"] + ", " + HOME_ADDRESS["state"]

                gps_good2 = accuracy <= 50.0

                curr_maps = f"https://maps.google.com/?q={curr_lat},{curr_lon}"
                home_maps = f"https://maps.google.com/?q={HOME_ADDRESS['lat']},{HOME_ADDRESS['lon']}"
                nav_url   = f"https://www.google.com/maps/dir/{curr_lat},{curr_lon}/{HOME_ADDRESS['lat']},{HOME_ADDRESS['lon']}"

                print(c(C.LIME + C.BOLD, "  📍 Aap Abhi Yahan Hain:"))
                if gps_good2 and curr_area:
                    print(c(C.WHITE + C.BOLD, f"     📌 Address  : {curr_area}"))
                elif not gps_good2:
                    print(c(C.YELLOW + C.BOLD, f"     ⚠️  GPS lock kamzor hai (±{accuracy}m) — khidki ke paas jao"))
                print(c(C.CYAN,          f"     Latitude  : {curr_lat}°"))
                print(c(C.CYAN,          f"     Longitude : {curr_lon}°"))
                print(c(C.CYAN,          f"     Accuracy  : ±{accuracy} m"))
                print(c(C.GOLD,          f"     Maps Link : {curr_maps}"))
                print()
                print(c(C.PINK + C.BOLD, "  🏠 Aapka Ghar:"))
                print(c(C.CYAN,          f"     Pata      : {HOME_ADDRESS['full']}"))
                print(c(C.CYAN,          f"     PIN Code  : {HOME_ADDRESS['pincode']}"))
                print(c(C.GOLD,          f"     Maps Link : {home_maps}"))
                print()
                if dist_km < 1:
                    dist_str = f"{dist_m} meter"
                    dist_voice = f"{dist_m} meter"
                else:
                    dist_str = f"{dist_km} km ({dist_m} meter)"
                    dist_voice = f"{dist_km} kilometer"
                print(c(C.YELLOW + C.BOLD, f"  📏 Ghar Se Doori : {dist_str}"))
                print()
                print(c(C.TEAL + C.BOLD,  f"  🧭 Navigation    : {nav_url}"))
                print()
                print(c(C.ORANGE + C.BOLD, "  " + "═" * 46))
                print()
                loc_voice = curr_area if curr_area else f"{curr_lat}, {curr_lon}"
                speak(f"Boss, aap abhi {loc_voice} mein hain. Ghar se {dist_voice} door hain.")
            except Exception as e:
                print(c(C.RED, f"  Location nahi mili: {e}"))
                print(c(C.DIM, "  Tip: GPS ON karo aur termux-api install karo."))
                print()
                print(c(C.PINK + C.BOLD, "  🏠 Ghar Ka Pata (saved):"))
                print(c(C.CYAN,          f"     {HOME_ADDRESS['full']}"))
                print(c(C.CYAN,          f"     PIN: {HOME_ADDRESS['pincode']}"))
                maps_url = f"https://maps.google.com/?q={HOME_ADDRESS['lat']},{HOME_ADDRESS['lon']}"
                print(c(C.GOLD,          f"     Maps: {maps_url}"))
            continue

        # ── LOCATION ──
        if ul in ("location", "location kya hai", "meri location", "gps", "location batao",
                  "where am i", "main kahan hoon", "main abhi kahan hoon", "mujhe batao main kahan hoon",
                  "friday main kahan hoon", "abhi kahan hoon", "mera address batao",
                  "ye kaun si jagah hai", "yahan kya hai", "is jagah ke baare mein batao",
                  "ye kahan hai", "is jagah ki details", "jagah batao", "place batao",
                  "ye jagah kaisi hai", "yahaan kya kya hai", "surrounding kya hai"):
            print()
            print(c(C.GREEN + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.GREEN + C.BOLD, "  ║        📍  LOCATION                         ║"))
            print(c(C.GREEN + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            print(c(C.DIM, "  Location dhundh raha hoon (GPS → network)... thoda wait karo"))
            try:
                # Network provider pehle — GPS se fast hai
                ld = None
                for _prov in ["gps", "network", "passive"]:
                    try:
                        r = subprocess.run(
                            ["termux-location", "-p", _prov, "-r", "once"],
                            capture_output=True, text=True, timeout=15
                        )
                        if r.stdout.strip():
                            ld = json.loads(r.stdout)
                            if ld.get("latitude"):
                                break
                    except Exception:
                        continue
                if not ld or not ld.get("latitude"):
                    raise Exception("Location nahi mili — termux-api install karo aur location permission do")

                lat      = round(ld.get("latitude",  0), 6)
                lon      = round(ld.get("longitude", 0), 6)
                alt      = round(ld.get("altitude",  0), 1)
                accuracy = round(ld.get("accuracy",  0), 1)
                provider = ld.get("provider", "?")

                # ── Reverse Geocoding — Nominatim (zoom=16) + BigDataCloud fallback ──
                address_str   = ""
                area_str      = ""
                place_details = {}
                try:
                    from urllib.request import urlopen, Request as _Req
                    import json as _json

                    def _fetch_geo(url):
                        r = _Req(url, headers={"User-Agent": "FridayAssistant/1.0"})
                        return _json.loads(urlopen(r, timeout=8).read().decode())

                    # ── API 1: Nominatim zoom=16 (local level) ──
                    try:
                        geo_data = _fetch_geo(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&addressdetails=1&zoom=16&accept-language=en")
                        addr = geo_data.get("address", {})
                        parts = []
                        for key in ["suburb", "neighbourhood", "quarter", "village", "town", "city_district", "city", "state_district", "state", "country"]:
                            v = addr.get(key)
                            if v and v not in parts:
                                parts.append(v)
                        if parts:
                            area_str = ", ".join(parts[:5])
                            place_details = {
                                "postcode": addr.get("postcode", ""),
                                "district": addr.get("state_district") or addr.get("county", ""),
                                "state":    addr.get("state", ""),
                                "country":  addr.get("country", ""),
                                "city":     addr.get("city") or addr.get("town") or addr.get("village") or addr.get("suburb", ""),
                            }
                    except Exception:
                        pass

                    # ── API 2: BigDataCloud fallback ──
                    if not area_str:
                        try:
                            bd = _fetch_geo(f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lon}&localityLanguage=en")
                            locality  = bd.get("locality", "")
                            city2     = bd.get("city", "")
                            district2 = bd.get("principalSubdivision", "")
                            country2  = bd.get("countryName", "")
                            area_str  = ", ".join(filter(None, [locality or city2, district2, country2]))
                            place_details = {
                                "postcode": bd.get("postcode", ""),
                                "district": district2,
                                "state":    district2,
                                "country":  country2,
                                "city":     locality or city2,
                            }
                        except Exception:
                            pass

                except Exception:
                    area_str = ""

                # Distance from home
                dist_km = haversine_distance(lat, lon, HOME_ADDRESS["lat"], HOME_ADDRESS["lon"])
                dist_m  = int(dist_km * 1000)

                # ── OSM data correction — Serampore/Shrirampur is wrong near Baidyabati ──
                _wrong_names = ["serampore", "shrirampur", "srirampur", "srirampore"]
                if dist_km <= 3.0 and any(w in area_str.lower() for w in _wrong_names):
                    area_str = HOME_ADDRESS["short"] + ", " + HOME_ADDRESS["state"] + ", " + HOME_ADDRESS["country"]
                    place_details = {
                        "postcode": HOME_ADDRESS["pincode"],
                        "district": HOME_ADDRESS["district"],
                        "state":    HOME_ADDRESS["state"],
                        "country":  HOME_ADDRESS["country"],
                        "city":     HOME_ADDRESS["city"],
                    }

                # ── Accuracy check — ±50m se better ho toh hi address dikhao ──
                gps_good = accuracy <= 50.0

                print(c(C.LIME + C.BOLD,  f"  📍 Aap Abhi Yahan Hain:"))
                if gps_good and area_str:
                    print(c(C.WHITE + C.BOLD, f"     📌 Address   : {area_str}"))
                elif not gps_good:
                    print(c(C.YELLOW + C.BOLD, f"     ⚠️  GPS lock kamzor hai (±{accuracy}m) — address accurate nahi hoga"))
                    print(c(C.DIM,             f"     💡 Khidki ke paas jao ya bahar niklo, phir dobara try karo"))
                print(c(C.CYAN,           f"     Latitude   : {lat}°"))
                print(c(C.CYAN,           f"     Longitude  : {lon}°"))
                print(c(C.CYAN,           f"     Altitude   : {alt} m"))
                print(c(C.CYAN,           f"     Accuracy   : ±{accuracy} m"))
                print(c(C.CYAN,           f"     Provider   : {provider}"))
                print()
                maps_url = f"https://maps.google.com/?q={lat},{lon}"
                print(c(C.GOLD + C.BOLD,  f"  🗺️  Google Maps : {maps_url}"))
                print()
                if dist_km < 1:
                    dist_str = f"{dist_m} meter"
                else:
                    dist_str = f"{dist_km} km"
                print(c(C.PINK + C.BOLD,  f"  🏠 Ghar Se Doori: {dist_str}"))
                nav_url = f"https://www.google.com/maps/dir/{lat},{lon}/{HOME_ADDRESS['lat']},{HOME_ADDRESS['lon']}"
                print(c(C.TEAL,           f"     Navigation  : {nav_url}"))
                print()

                # ── Jagah ki details ──
                if place_details or area_str:
                    print(c(C.MAGENTA + C.BOLD, "  🏙️  Is Jagah Ki Details:"))
                    print(c(C.MAGENTA,           "  " + "─" * 44))
                    if place_details.get("city"):
                        print(c(C.WHITE,  f"     🏙️  Sheher    : {place_details['city']}"))
                    if place_details.get("district"):
                        print(c(C.WHITE,  f"     🗺️  Zila      : {place_details['district']}"))
                    if place_details.get("state"):
                        print(c(C.WHITE,  f"     📍 Rajya     : {place_details['state']}"))
                    if place_details.get("country"):
                        print(c(C.WHITE,  f"     🌏 Desh      : {place_details['country']}"))
                    if place_details.get("postcode"):
                        print(c(C.WHITE,  f"     📮 PIN Code  : {place_details['postcode']}"))
                    # Wikipedia — city + state dono include karo taaki correct result mile
                    try:
                        from urllib.request import urlopen, Request as _Req2
                        from urllib.parse import quote as _quote
                        import json as _json2
                        wiki_city  = place_details.get("city") or area_str.split(",")[0].strip()
                        wiki_state = place_details.get("state", "")
                        # State disambiguate karo — e.g. "Serampore, West Bengal"
                        search_term = f"{wiki_city}, {wiki_state}" if wiki_state else wiki_city
                        wiki_url  = f"https://en.wikipedia.org/api/rest_v1/page/summary/{_quote(search_term)}"
                        wiki_req  = _Req2(wiki_url, headers={"User-Agent": "FridayAssistant/1.0"})
                        wiki_data = _json2.loads(urlopen(wiki_req, timeout=6).read().decode())
                        wiki_extract = wiki_data.get("extract", "")
                        # Verify state matches — wrong state ki info mat dikhao
                        if wiki_extract and len(wiki_extract) > 50 and wiki_state.lower() in wiki_extract.lower():
                            sentences  = wiki_extract.replace("  ", " ").split(". ")
                            short_info = ". ".join(sentences[:2]) + "."
                            print()
                            print(c(C.CYAN + C.BOLD,  "     📖 Jagah ke baare mein:"))
                            print(c(C.DIM,             f"     {short_info[:220]}"))
                    except Exception:
                        pass
                    print()

                print(c(C.GREEN + C.BOLD, "  " + "═" * 46))
                print()
                if gps_good and area_str:
                    speak(f"Boss, aap abhi {area_str} mein hain. Ghar se {dist_str} door hain.")
                else:
                    speak(f"Boss, GPS lock kamzor hai. Khidki ke paas jao ya bahar niklo aur dobara try karo.")
            except Exception as e:
                print(c(C.RED, f"  Location nahi mili: {e}"))
                print(c(C.DIM, "  Tip: GPS ON karo aur termux-api install karo."))
                print(c(C.DIM, "  Run: pkg install termux-api"))
            continue

        # ── MY IP ──
        if ul in ("myip", "my ip", "mera ip", "mera ip kya hai", "my ip kya hai",
                  "apna ip batao", "ip kya hai", "public ip", "public ip kya hai"):
            print()
            print(c(C.DEEPBLUE + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.DEEPBLUE + C.BOLD, "  ║        📡  MERA PUBLIC IP                   ║"))
            print(c(C.DEEPBLUE + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            print(c(C.DIM, "  IP dhundh raha hoon..."))
            print()
            try:
                from urllib.request import urlopen, Request
                import json as _json

                # ── Step 1: Public IP lo ──
                my_ip = None
                for ip_url in [
                    "https://api.ipify.org?format=json",
                    "https://api64.ipify.org?format=json",
                    "https://ipinfo.io/json",
                ]:
                    try:
                        req  = Request(ip_url, headers={"User-Agent": "Mozilla/5.0"})
                        resp = urlopen(req, timeout=6)
                        raw  = _json.loads(resp.read().decode())
                        my_ip = raw.get("ip") or raw.get("IPv4") or raw.get("query")
                        if my_ip:
                            break
                    except Exception:
                        continue

                if not my_ip:
                    print(c(C.RED, "  ✗ IP nahi mili — internet check karo."))
                    print()
                else:
                    # ── Step 2: Us IP ki full details lo ──
                    api_url = f"http://ip-api.com/json/{my_ip}?fields=status,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,proxy,hosting,mobile"
                    req2  = Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
                    data  = _json.loads(urlopen(req2, timeout=8).read().decode())

                    print(c(C.LIME + C.BOLD,    f"  📡 Public IP   : ") + c(C.WHITE + C.BOLD, my_ip))
                    print()

                    if data.get("status") == "success":
                        country  = data.get("country",    "?")
                        region   = data.get("regionName", "?")
                        city     = data.get("city",       "?")
                        zipcode  = data.get("zip",        "?")
                        lat      = data.get("lat",         0)
                        lon      = data.get("lon",         0)
                        timezone = data.get("timezone",   "?")
                        isp      = data.get("isp",        "?")
                        org      = data.get("org",        "?")
                        asn      = data.get("as",         "?")
                        is_proxy = data.get("proxy",      False)

                        print(c(C.CYAN + C.BOLD,   f"  📍 Location"))
                        print(c(C.CYAN,            f"     Country    : {country}"))
                        print(c(C.CYAN,            f"     Region     : {region}"))
                        print(c(C.CYAN,            f"     City       : {city}"))
                        print(c(C.CYAN,            f"     ZIP        : {zipcode}"))
                        print(c(C.CYAN,            f"     Lat / Lon  : {lat}°, {lon}°"))
                        print(c(C.CYAN,            f"     Timezone   : {timezone}"))
                        print()
                        print(c(C.MAGENTA + C.BOLD,f"  🏢 Network"))
                        print(c(C.MAGENTA,         f"     ISP        : {isp}"))
                        print(c(C.MAGENTA,         f"     Org        : {org}"))
                        print(c(C.MAGENTA,         f"     ASN        : {asn}"))
                        print()

                        proxy_str = c(C.RED, "⚠ Yes — VPN/Proxy ON hai!") if is_proxy else c(C.GREEN, "✓ No — Clean IP")
                        print(c(C.WHITE,           f"  🔍 Proxy/VPN   : ") + proxy_str)
                        print()
                        maps_url = f"https://maps.google.com/?q={lat},{lon}"
                        print(c(C.GOLD + C.BOLD,   f"  🗺️  Maps        : {maps_url}"))

                    print()
                    print(c(C.DEEPBLUE + C.BOLD, "  " + "═" * 46))
                    print()
                    speak(f"Aapka public IP {my_ip} hai. Location: {city}, {region}, {country}. ISP: {isp}.")

            except Exception as e:
                print(c(C.RED, f"  ✗ Error: {e}"))
                print(c(C.DIM, "  Internet connection check karo."))
                print()
            continue

        # ── WEATHER ──
        weather_cmds = (
            "weather", "mausam", "aaj ka mausam", "aaj ka weather",
            "weather kya hai", "mausam kya hai", "temperature kya hai",
            "bahar kaisa mausam hai", "weather batao", "mausam batao",
        )
        weather_city = None
        # "weather [city]" ya "mausam [city]" format
        for pfx in ("weather ", "mausam "):
            if ul.startswith(pfx):
                weather_city = user_input[len(pfx):].strip()
                break

        if ul in weather_cmds or weather_city is not None:
            print()
            print(c(C.CYAN + C.BOLD,  "  ╔══════════════════════════════════════════════╗"))
            print(c(C.CYAN + C.BOLD,  "  ║        🌤️   WEATHER / MAUSAM                ║"))
            print(c(C.CYAN + C.BOLD,  "  ╚══════════════════════════════════════════════╝"))
            print()

            API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
            if not API_KEY:
                print(c(C.RED, "  ✗ OPENWEATHER_API_KEY set nahi hai!"))
                print(c(C.DIM, "  Run: export OPENWEATHER_API_KEY=\"aapki_key\""))
                print()
            else:
                try:
                    from urllib.request import urlopen, Request
                    from urllib.parse import quote_plus
                    import json as _json

                    # City decide karo — given hai ya auto-detect
                    if not weather_city:
                        print(c(C.DIM, "  Location detect kar raha hoon..."))
                        try:
                            req_ip = Request("https://ipinfo.io/json", headers={"User-Agent": "Mozilla/5.0"})
                            ip_data = _json.loads(urlopen(req_ip, timeout=5).read().decode())
                            weather_city = ip_data.get("city", "Kolkata")
                        except Exception:
                            weather_city = "Kolkata"

                    print(c(C.DIM, f"  Fetching weather for: {weather_city} ..."))
                    print()

                    # ── OpenWeatherMap API call ──
                    url = (
                        f"https://api.openweathermap.org/data/2.5/weather"
                        f"?q={quote_plus(weather_city)}&appid={API_KEY}&units=metric&lang=en"
                    )
                    req  = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    resp = urlopen(req, timeout=8)
                    wd   = _json.loads(resp.read().decode())

                    # ── Parse data ──
                    city_name   = wd.get("name", weather_city)
                    country     = wd.get("sys", {}).get("country", "")
                    desc        = wd["weather"][0]["description"].title()
                    icon_id     = wd["weather"][0]["id"]
                    temp        = round(wd["main"]["temp"])
                    feels_like  = round(wd["main"]["feels_like"])
                    temp_min    = round(wd["main"]["temp_min"])
                    temp_max    = round(wd["main"]["temp_max"])
                    humidity    = wd["main"]["humidity"]
                    pressure    = wd["main"]["pressure"]
                    visibility  = round(wd.get("visibility", 0) / 1000, 1)
                    wind_speed  = round(wd["wind"]["speed"] * 3.6)  # m/s → km/h
                    wind_deg    = wd["wind"].get("deg", 0)
                    cloudiness  = wd["clouds"]["all"]
                    sunrise_ts  = wd["sys"]["sunrise"]
                    sunset_ts   = wd["sys"]["sunset"]
                    # timezone = UTC offset in seconds (from OpenWeatherMap)
                    tz_offset   = wd.get("timezone", 0)  # e.g. -25200 for San Francisco
                    tz_utc      = datetime.timezone(datetime.timedelta(seconds=tz_offset))
                    sunrise     = datetime.datetime.fromtimestamp(sunrise_ts, tz=datetime.timezone.utc).astimezone(tz_utc).strftime("%I:%M %p")
                    sunset      = datetime.datetime.fromtimestamp(sunset_ts,  tz=datetime.timezone.utc).astimezone(tz_utc).strftime("%I:%M %p")

                    # ── Weather emoji by condition code ──
                    if 200 <= icon_id <= 232:   w_emoji = "⛈️"   # Thunderstorm
                    elif 300 <= icon_id <= 321: w_emoji = "🌦️"   # Drizzle
                    elif 500 <= icon_id <= 531: w_emoji = "🌧️"   # Rain
                    elif 600 <= icon_id <= 622: w_emoji = "❄️"   # Snow
                    elif 700 <= icon_id <= 781: w_emoji = "🌫️"   # Atmosphere (fog/mist)
                    elif icon_id == 800:        w_emoji = "☀️"   # Clear sky
                    elif icon_id == 801:        w_emoji = "🌤️"   # Few clouds
                    elif icon_id == 802:        w_emoji = "⛅"   # Scattered clouds
                    else:                       w_emoji = "☁️"   # Broken/overcast clouds

                    # ── Wind direction arrow ──
                    dirs = ["N","NE","E","SE","S","SW","W","NW"]
                    wind_dir = dirs[round(wind_deg / 45) % 8]

                    # ── Temperature color ──
                    if temp <= 10:    temp_col = C.CYAN
                    elif temp <= 20:  temp_col = C.TEAL
                    elif temp <= 30:  temp_col = C.YELLOW
                    elif temp <= 38:  temp_col = C.ORANGE
                    else:             temp_col = C.RED

                    # ── Display ──
                    print(c(C.WHITE + C.BOLD,  f"  {w_emoji}  {city_name}, {country}"))
                    print(c(C.DIM,             f"     {desc}"))
                    print()
                    print(c(temp_col + C.BOLD, f"  🌡️  Temperature  : {temp}°C") +
                          c(C.DIM,             f"  (Feels like {feels_like}°C)"))
                    print(c(C.CYAN,            f"     Min / Max    : {temp_min}°C  /  {temp_max}°C"))
                    print()
                    print(c(C.BLUE + C.BOLD,   f"  💧 Humidity     : {humidity}%"))
                    print(c(C.WHITE,           f"  🔵 Pressure     : {pressure} hPa"))
                    print(c(C.DIM,             f"  👁️  Visibility   : {visibility} km"))
                    print(c(C.TEAL,            f"  ☁️  Cloud Cover  : {cloudiness}%"))
                    print()
                    print(c(C.GREEN + C.BOLD,  f"  💨 Wind         : {wind_speed} km/h  {wind_dir}"))
                    print()
                    print(c(C.GOLD,            f"  🌅 Sunrise      : {sunrise}"))
                    print(c(C.ORANGE,          f"  🌇 Sunset       : {sunset}"))
                    print()
                    print(c(C.CYAN + C.BOLD,   "  " + "═" * 46))
                    print()

                    voice_msg = (
                        f"{city_name} mein abhi {desc} hai. "
                        f"Temperature {temp} degree Celsius, feels like {feels_like}. "
                        f"Humidity {humidity} percent. Wind {wind_speed} kilometer per hour."
                    )
                    speak(voice_msg)

                except Exception as e:
                    err_str = str(e)
                    if "401" in err_str:
                        print(c(C.RED, "  ✗ API Key galat hai ya inactive — OpenWeatherMap check karo."))
                    elif "404" in err_str:
                        print(c(C.RED, f"  ✗ City nahi mili: \"{weather_city}\" — spelling check karo."))
                    else:
                        print(c(C.RED, f"  ✗ Error: {e}"))
                    print()
            continue

        # ── CALL ──
        # Active call flow
        if _call_state.get("active"):
            call_handle(user_input)
            continue

        # "call" trigger
        if ul in ("call", "call karo", "phone karo", "ring karo",
                  "dial", "phone", "ring"):
            print()
            print(c(C.GREEN + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.GREEN + C.BOLD, "  ║        📞  CALL KARO                        ║"))
            print(c(C.GREEN + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            call_start()
            continue

        # Quick: "call +8801234567890"
        _call_quick = re.match(r'call\s+(\+?\d{7,15})$', ul)
        if _call_quick:
            num = _call_quick.group(1)
            masked = "*" * len(num[:-4]) + num[-4:]
            _call_state.update({"active": True, "number": num, "step": "confirm"})
            print()
            print(c(C.YELLOW + C.BOLD, "  ╔══════════════════════════════════════════╗"))
            print(c(C.YELLOW + C.BOLD, "  ║       📞  CONFIRM CALL                  ║"))
            print(c(C.YELLOW + C.BOLD, "  ╚══════════════════════════════════════════╝"))
            print()
            print(c(C.WHITE,           f"  📞 Number : {masked}"))
            print()
            print(c(C.LIME + C.BOLD,   "  ✅ Call: yes    ❌ Cancel: no"))
            print()
            speak("Confirm karo Boss.")
            continue

        # ── SCREENSHOT / CAMERA ──
        if ul in ("screenshot", "screen shot", "ss", "capture screen",
                  "screen capture", "screenshoot"):
            take_screenshot()
            continue

        if ul in ("photo", "camera", "selfie", "photo lo", "pic lo",
                  "click photo", "take photo", "take picture"):
            take_photo()
            continue

        # screenshot with filename: "screenshot myfile"
        if ul.startswith("screenshot ") and len(ul) > 11:
            fname = ul[11:].strip()
            take_screenshot(fname)
            continue

        # ── SMS SEND ──
        # Handle active SMS flow first
        if _sms_state.get("active"):
            sms_handle(user_input)
            continue

        # Trigger SMS
        if ul in ("sms", "sms send", "send sms", "message bhejo",
                  "sms karo", "msg send", "text send"):
            print()
            print(c(C.CYAN + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.CYAN + C.BOLD, "  ║        📱  SMS SEND                         ║"))
            print(c(C.CYAN + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            sms_start()
            continue

        # Quick: "sms +8801234 hello bhai" — number + message inline
        _sms_quick = re.match(r'sms\s+(\+?\d{7,15})\s+(.+)$', user_input.strip(), re.IGNORECASE)
        if _sms_quick:
            num = _sms_quick.group(1)
            msg = _sms_quick.group(2).strip()
            masked = "*" * len(num[:-4]) + num[-4:]
            _sms_state.update({"active": True, "number": num, "message": msg, "step": "confirm"})
            print()
            print(c(C.YELLOW + C.BOLD, "  ╔══════════════════════════════════════════╗"))
            print(c(C.YELLOW + C.BOLD, "  ║       📤  CONFIRM SMS                   ║"))
            print(c(C.YELLOW + C.BOLD, "  ╚══════════════════════════════════════════╝"))
            print()
            print(c(C.WHITE,    f"  📞 To      : {masked}"))
            print(c(C.WHITE,    f"  💬 Message : {msg}"))
            print()
            print(c(C.LIME + C.BOLD, "  ✅ Send: yes    ❌ Cancel: no"))
            print()
            speak("Confirm karo Boss.")
            continue

        # ── STOCK PRICE ──
        _stock_syms = []

        if ul in ("stock", "stocks", "stock price", "share price",
                  "sensex", "nifty", "market"):
            # Default watchlist
            if ul in ("sensex",): _stock_syms = ["^BSESN"]
            elif ul in ("nifty",): _stock_syms = ["^NSEI"]
            else: _stock_syms = ["AAPL", "GOOGL", "TSLA", "NVDA", "^NSEI", "RELIANCE.NS"]

        elif re.match(r'stock\s+(.+)', ul):
            tokens = re.match(r'stock\s+(.+)', ul).group(1).split()
            for t in tokens:
                sym = STOCK_ALIASES.get(t.lower(), t.upper())
                if sym not in _stock_syms:
                    _stock_syms.append(sym)

        elif ul.endswith(" stock") or ul.endswith(" share") or ul.endswith(" price"):
            name = re.sub(r'\s*(stock|share|price)$', '', ul).strip()
            sym  = STOCK_ALIASES.get(name, name.upper())
            _stock_syms = [sym]

        if _stock_syms:
            print()
            print(c(C.LIME + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.LIME + C.BOLD, "  ║        📈  STOCK PRICE                      ║"))
            print(c(C.LIME + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            show_stock_price(_stock_syms)
            continue

        # ── GOLD PRICE ──
        if ul in ("gold", "gold price", "sona", "sone ka bhav", "sone ka rate",
                  "gold rate", "silver", "silver price", "chandi", "chandi ka bhav",
                  "gold silver", "metals", "bullion"):
            print()
            print(c(C.GOLD + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.GOLD + C.BOLD, "  ║        🥇  GOLD & SILVER PRICE             ║"))
            print(c(C.GOLD + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            show_gold_price()
            continue

        # ── CRYPTO LIVE PRICE ──
        if ul in ("crypto", "crypto price", "bitcoin price", "cryptocurrency",
                  "coin price", "btc price", "eth price", "crypto rates",
                  "digital currency", "coins"):
            print()
            print(c(C.GOLD + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.GOLD + C.BOLD, "  ║        ₿   CRYPTO LIVE PRICES              ║"))
            print(c(C.GOLD + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            show_crypto_price()
            continue

        # "crypto btc" or "crypto eth sol" — specific coins
        _cm = re.match(r'crypto\s+([a-zA-Z\s]+)$', ul)
        if _cm:
            tokens = _cm.group(1).strip().split()
            coin_ids = []
            for t in tokens:
                cid = CRYPTO_IDS.get(t.lower())
                if cid and cid not in coin_ids:
                    coin_ids.append(cid)
            if coin_ids:
                print()
                print(c(C.GOLD + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
                print(c(C.GOLD + C.BOLD, "  ║        ₿   CRYPTO LIVE PRICES              ║"))
                print(c(C.GOLD + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
                print()
                show_crypto_price(coin_ids)
                continue

        # "btc price" / "eth price" shortcut
        _crypto_matched = False
        for sym, cid in CRYPTO_IDS.items():
            if ul in (f"{sym} price", f"{sym} rate", f"{sym} ka price",
                      f"{sym} kitna hai", sym) and len(sym) <= 5:
                print()
                print(c(C.GOLD + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
                print(c(C.GOLD + C.BOLD, "  ║        ₿   CRYPTO LIVE PRICES              ║"))
                print(c(C.GOLD + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
                print()
                show_crypto_price([cid])
                _crypto_matched = True
                break
        if _crypto_matched:
            continue

        # ── NUMBER GAME ──
        if ul in ("number game", "guess game", "game", "number guess",
                  "anumaan", "guess karo", "number khelo", "guessing game"):
            print()
            print(c(C.MAGENTA + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.MAGENTA + C.BOLD, "  ║        🎯  NUMBER GUESSING GAME             ║"))
            print(c(C.MAGENTA + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            numgame_start(1, 100)
            continue

        # "number game 1 50" — custom range
        _ngm = re.match(r'number game\s+(\d+)\s+(\d+)$', ul)
        if _ngm:
            lo2, hi2 = int(_ngm.group(1)), int(_ngm.group(2))
            if lo2 >= hi2:
                print(c(C.RED, "  Pehla number chhota, doosra bada hona chahiye!"))
            else:
                print()
                print(c(C.MAGENTA + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
                print(c(C.MAGENTA + C.BOLD, f"  ║   🎯  NUMBER GAME ({lo2}–{hi2}){'':>21}║"))
                print(c(C.MAGENTA + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
                print()
                numgame_start(lo2, hi2)
            continue

        if ul in ("game stop", "stop game", "game band", "game quit"):
            if _numgame_state.get("active"):
                secret = _numgame_state["secret"]
                _numgame_state["active"] = False
                print(c(C.DIM, f"  Game band! Number tha: {secret}"))
            else:
                print(c(C.DIM, "  Koi game nahi chal rahi."))
            continue

        # Number input when game active (and not quiz active)
        if (_numgame_state.get("active") and not _quiz_state.get("active")
                and re.match(r'^\d+$', ul)):
            numgame_guess(ul)
            continue

        # ── QUIZ / TRIVIA ──
        if ul in ("quiz", "trivia", "quiz start", "trivia start",
                  "quiz khelo", "gyan", "test me", "test karo"):
            print()
            print(c(C.CYAN + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.CYAN + C.BOLD, "  ║        🧠  QUIZ TIME!                       ║"))
            print(c(C.CYAN + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            quiz_start(5)
            continue

        _qm = re.match(r'quiz\s+(\d+)$', ul)
        if _qm:
            n = min(int(_qm.group(1)), 30)
            print()
            print(c(C.CYAN + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.CYAN + C.BOLD, f"  ║        🧠  QUIZ — {n} Questions{'!' if n<10 else ''}{'             ' if n<10 else '            '}║"))
            print(c(C.CYAN + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            quiz_start(n)
            continue

        if ul in ("quiz stop", "quiz quit", "quiz band karo", "stop quiz"):
            _quiz_state["active"] = False
            print(c(C.DIM, "  Quiz band kar di Boss."))
            continue

        # Quiz answer (1/2/3/4) when quiz is active
        if _quiz_state.get("active") and ul in ("1","2","3","4"):
            quiz_answer(ul)
            continue

        # ── COUNTRY INFO ──
        country_query = None
        for pfx in ("country info ", "country ", "desh ", "mulk ",
                    "tell me about ", "info about "):
            if ul.startswith(pfx):
                country_query = user_input[len(pfx):].strip()
                break

        if country_query:
            print()
            print(c(C.TEAL + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.TEAL + C.BOLD, "  ║        🗺️   COUNTRY INFO                    ║"))
            print(c(C.TEAL + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            show_country_info(country_query)
            continue

        # ── TIMEZONE / WORLD CLOCK ──
        tz_trigger = False
        tz_cities  = []

        if ul in ("world clock", "timezone", "time zone", "world time",
                  "duniya ka time", "time dekho", "clock"):
            tz_trigger = True
            tz_cities  = []  # default

        elif ul.startswith("time in ") or ul.startswith("time of "):
            city = user_input[8:].strip()
            tz_trigger = True
            tz_cities  = [city.lower()]

        elif ul.startswith("timezone ") or ul.startswith("time zone "):
            city = re.sub(r'^time\s*zone\s*', '', user_input, flags=re.IGNORECASE).strip()
            tz_trigger = True
            tz_cities  = [city.lower()]

        elif ul.startswith("clock "):
            city = user_input[6:].strip()
            tz_trigger = True
            tz_cities  = [city.lower()]

        if tz_trigger:
            print()
            print(c(C.TEAL + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.TEAL + C.BOLD, "  ║        🌍  WORLD CLOCK                      ║"))
            print(c(C.TEAL + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            show_world_clock(tz_cities if tz_cities else None)
            continue

        # ── TRANSLATE ──
        trans_match = None
        trans_text  = ""
        trans_to    = ""

        # Patterns: "translate hello to french" / "translate hello in urdu"
        import re as _re
        _tm = _re.match(
            r'(?:translate|tarjuma|anuvad)\s+(.+?)\s+(?:to|in|into|mein|ko\s+\w+\s+mein|ko)\s+([a-zA-Z]+)$',
            user_input.strip(), _re.IGNORECASE
        )
        if not _tm:
            # "tarjuma hello ko urdu mein" style
            _tm2 = _re.match(
                r'(?:translate|tarjuma|anuvad)\s+(.+?)\s+ko\s+([a-zA-Z]+)\s+mein$',
                user_input.strip(), _re.IGNORECASE
            )
            if _tm2:
                _tm = _tm2
        if _tm:
            trans_text = _tm.group(1).strip()
            trans_to   = _tm.group(2).strip()
            trans_match = True

        if trans_match:
            print()
            print(c(C.PURPLE + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.PURPLE + C.BOLD, "  ║        🌍  TRANSLATOR                       ║"))
            print(c(C.PURPLE + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            print(c(C.DIM,   f"  📝 Text     : {trans_text}"))
            print(c(C.DIM,   f"  🌐 Language : {trans_to.title()}"))
            print()

            try:
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    max_tokens=300,
                    messages=[{
                        "role": "user",
                        "content": (
                            f"Translate the following text to {trans_to}. "
                            f"Return ONLY the translated text, nothing else. "
                            f"No explanation, no notes:\n\n{trans_text}"
                        )
                    }]
                )
                result = resp.choices[0].message.content.strip()

                print(c(C.WHITE + C.BOLD, f"  ✨ Translation:"))
                print()
                print(c(C.LIME + C.BOLD,  f"  {result}"))
                print()
                print(c(C.PURPLE + C.BOLD, "  " + "═" * 46))
                print()

                # Voice — non-Latin scripts ko English mein bolega
                import re as _re2
                is_latin = bool(_re2.match(r'^[\x00-\x7F\u00C0-\u024F\s]+$', result))
                if is_latin:
                    speak(result[:150])
                else:
                    speak(f"{trans_text} ka {trans_to} mein tarjuma ho gaya Boss.")

            except Exception as e:
                print(c(C.RED, f"  ✗ Error: {e}"))
            continue

        # ── RIDDLE / PAHELI ──
        if ul in ("riddle", "paheli", "riddle do", "paheli do", "ek paheli",
                  "puzzle", "ek riddle", "paheliyan", "riddles"):
            print()
            print(c(C.YELLOW + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.YELLOW + C.BOLD, "  ║        🧩  PAHELI / RIDDLE                  ║"))
            print(c(C.YELLOW + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            show_riddle()
            continue

        if ul in ("jawab", "answer", "riddle answer", "paheli answer",
                  "jawab batao", "answer batao", "reveal"):
            print()
            print(c(C.LIME + C.BOLD,  "  ╔══════════════════════════════════════════════╗"))
            print(c(C.LIME + C.BOLD,  "  ║        ✅  JAWAB                            ║"))
            print(c(C.LIME + C.BOLD,  "  ╚══════════════════════════════════════════════╝"))
            print()
            show_riddle_answer()
            continue

        # ── FUN FACT ──
        if ul in ("fun fact", "funfact", "fact", "interesting fact",
                  "kuch interesting", "kuch naya batao", "amazing fact",
                  "did you know", "kya pata tha", "rochak tathya"):
            print()
            print(c(C.CYAN + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.CYAN + C.BOLD, "  ║        🤓  FUN FACT                         ║"))
            print(c(C.CYAN + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            show_fun_fact()
            continue

        # ── THIS DAY IN HISTORY ──
        if ul in ("this day in history", "aaj ka itihas", "history today",
                  "aaj itihas mein", "on this day", "itihas", "historical events",
                  "aaj kya hua tha"):
            print()
            print(c(C.ORANGE + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.ORANGE + C.BOLD, "  ║        📜  THIS DAY IN HISTORY              ║"))
            print(c(C.ORANGE + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            show_this_day_in_history()
            continue

        # ── WORD OF THE DAY ──
        if ul in ("word of the day", "wotd", "aaj ka word", "word",
                  "daily word", "new word", "word dekho", "vocabulary"):
            print()
            print(c(C.GOLD + C.BOLD,  "  ╔══════════════════════════════════════════════╗"))
            print(c(C.GOLD + C.BOLD,  "  ║        📖  WORD OF THE DAY                  ║"))
            print(c(C.GOLD + C.BOLD,  "  ╚══════════════════════════════════════════════╝"))
            print()
            show_word_of_the_day()
            continue

        # ── SPEEDTEST ──
        if ul in ("speedtest", "speed test", "internet speed", "speed check",
                  "speed", "bandwidth", "net speed", "internet kitna fast hai"):
            print()
            print(c(C.TEAL + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.TEAL + C.BOLD, "  ║        🚀  INTERNET SPEED TEST              ║"))
            print(c(C.TEAL + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            run_speedtest()
            continue

        # ── NETWORK SCANNER ──
        if (ul in ("netscan", "network scan", "lan scan", "scan network",
                   "scan lan", "network scanner", "devices", "network devices",
                   "kaun connected hai", "connected devices",
                   "scan wifi", "wifi scan", "wifi devices", "scan wifi network") or
                ul.startswith("netscan ") or ul.startswith("network scan ")):

            subnet = ""
            for pfx in ("netscan ", "network scan "):
                if ul.startswith(pfx):
                    subnet = user_input[len(pfx):].strip()
                    break

            print()
            print(c(C.TEAL + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.TEAL + C.BOLD, "  ║        📡  NETWORK SCANNER                  ║"))
            print(c(C.TEAL + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            network_scan(subnet)
            continue

        # ── SPEED TEST + WIFI SCAN (COMBINED) ──
        if ul in ("speed test wifi", "wifi speed test", "network check",
                  "speed aur wifi", "internet aur wifi", "full network check",
                  "network test", "net check", "poora network check"):
            print()
            print(c(C.CYAN + C.BOLD,  "  ╔══════════════════════════════════════════════╗"))
            print(c(C.CYAN + C.BOLD,  "  ║     🚀📡  FULL NETWORK CHECK                ║"))
            print(c(C.CYAN + C.BOLD,  "  ╚══════════════════════════════════════════════╝"))
            print()

            # Step 1: Speed Test
            print(c(C.TEAL + C.BOLD, "  ━━━ 🚀 INTERNET SPEED TEST ━━━"))
            print()
            run_speedtest()
            print()

            # Step 2: WiFi Scan
            print(c(C.TEAL + C.BOLD, "  ━━━ 📡 WIFI NETWORK SCAN ━━━"))
            print()
            network_scan("")
            continue

        # ── COIN FLIP / DICE ──
        if (ul in ("flip", "coin", "coin flip", "toss", "heads or tails",
                   "sikka", "sikka uchalo", "heads", "tails") or
                ul.startswith("dice") or ul.startswith("roll") or
                ul.startswith("random number")):

            print()
            print(c(C.MAGENTA + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.MAGENTA + C.BOLD, "  ║        🎲  COIN FLIP / DICE                 ║"))
            print(c(C.MAGENTA + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()

            import random as _rnd

            # ── DICE ──
            if ul.startswith("dice") or ul.startswith("roll"):
                # Parse: "dice 6" or "dice 2d6" or "dice 3 20"
                import re as _re
                nums = _re.findall(r'\d+', user_input)

                if len(nums) >= 2:
                    count_d = max(1, min(int(nums[0]), 10))
                    sides_d = max(2, min(int(nums[1]), 1000))
                elif len(nums) == 1:
                    n = int(nums[0])
                    # "dice 2d6" style parsed as just nums
                    count_d, sides_d = 1, max(2, min(n, 1000))
                else:
                    count_d, sides_d = 1, 6

                rolls   = [_rnd.randint(1, sides_d) for _ in range(count_d)]
                total   = sum(rolls)

                dice_icons = {4:"🔷", 6:"🎲", 8:"🔶", 10:"🔟", 12:"🔵", 20:"🟣", 100:"💯"}
                icon = dice_icons.get(sides_d, "🎲")

                print(c(C.WHITE + C.BOLD, f"  {icon}  Rolling {count_d}d{sides_d} ..."))
                print()

                if count_d == 1:
                    roll = rolls[0]
                    # Visual die for d6
                    d6_art = {
                        1: ["┌─────┐","│     │","│  ●  │","│     │","└─────┘"],
                        2: ["┌─────┐","│ ●   │","│     │","│   ● │","└─────┘"],
                        3: ["┌─────┐","│ ●   │","│  ●  │","│   ● │","└─────┘"],
                        4: ["┌─────┐","│ ● ● │","│     │","│ ● ● │","└─────┘"],
                        5: ["┌─────┐","│ ● ● │","│  ●  │","│ ● ● │","└─────┘"],
                        6: ["┌─────┐","│ ● ● │","│ ● ● │","│ ● ● │","└─────┘"],
                    }
                    if sides_d == 6 and roll in d6_art:
                        for row in d6_art[roll]:
                            print(c(C.YELLOW + C.BOLD, f"    {row}"))
                        print()
                    print(c(C.LIME + C.BOLD,  f"  Result : {roll}"))
                    speak(f"Dice roll — {roll}!")
                else:
                    rolls_str = "  +  ".join(str(r) for r in rolls)
                    print(c(C.YELLOW + C.BOLD, f"  Rolls  : {rolls_str}"))
                    print(c(C.LIME + C.BOLD,   f"  Total  : {total}"))
                    if count_d > 1:
                        print(c(C.DIM,         f"  Min: {min(rolls)}  Max: {max(rolls)}  Avg: {total/count_d:.1f}"))
                    speak(f"{count_d} dice roll — total {total}!")

            # ── RANDOM NUMBER ──
            elif ul.startswith("random number"):
                import re as _re
                nums = _re.findall(r'\d+', user_input)
                lo = int(nums[0]) if len(nums) >= 1 else 1
                hi = int(nums[1]) if len(nums) >= 2 else 100
                if lo > hi:
                    lo, hi = hi, lo
                n = _rnd.randint(lo, hi)
                print(c(C.CYAN + C.BOLD, f"  🎰  Random number ({lo}–{hi})"))
                print()
                print(c(C.LIME + C.BOLD, f"  Result : {n}"))
                speak(f"Random number — {n}!")

            # ── COIN FLIP ──
            else:
                result = _rnd.choice(["HEADS", "TAILS"])
                emoji  = "🪙"

                # Animated flip art
                heads_art = [
                    "    ╭───────╮",
                    "   │  ( H ) │",
                    "   │  HEAD  │",
                    "    ╰───────╯",
                ]
                tails_art = [
                    "    ╭───────╮",
                    "   │  ( T ) │",
                    "   │  TAIL  │",
                    "    ╰───────╯",
                ]
                art = heads_art if result == "HEADS" else tails_art
                col = C.GOLD if result == "HEADS" else C.CYAN

                print(c(C.DIM, f"  {emoji}  Flipping coin ..."))
                print()
                for row in art:
                    print(c(col + C.BOLD, row))
                print()
                print(c(col + C.BOLD, f"  Result : {result}! {'👑' if result == 'HEADS' else '🦅'}"))
                speak(f"Coin flip — {result}!")

            print()
            print(c(C.MAGENTA + C.BOLD, "  " + "═" * 46))
            print()
            continue

        # ── PING TOOL ──
        ping_target = None
        ping_count  = 4
        for pfx in ("ping ", "ping:"):
            if ul.startswith(pfx):
                rest   = user_input[len(pfx):].strip().split()
                if rest:
                    ping_target = rest[0]
                    # Optional count: ping google.com 8
                    try:
                        ping_count = max(1, min(int(rest[1]), 20)) if len(rest) > 1 else 4
                    except Exception:
                        ping_count = 4
                break

        if ping_target is not None:
            print()
            print(c(C.CYAN + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.CYAN + C.BOLD, "  ║        🏓  PING TOOL                        ║"))
            print(c(C.CYAN + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            ping_host(ping_target, ping_count)
            continue

        # ── PORT SCANNER ──
        ps_target = None
        ps_range  = "common"
        for pfx in ("portscan ", "port scan ", "scan ports ", "nmap "):
            if ul.startswith(pfx):
                rest = user_input[len(pfx):].strip()
                parts = rest.split()
                if parts:
                    ps_target = parts[0]
                    ps_range  = parts[1] if len(parts) > 1 else "common"
                break

        if ps_target is not None:
            print()
            print(c(C.TEAL + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.TEAL + C.BOLD, "  ║        🔍  PORT SCANNER                     ║"))
            print(c(C.TEAL + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            port_scan(ps_target, ps_range)
            continue

        # ── POMODORO TIMER ──
        if (ul.startswith("pomodoro") or ul.startswith("pomo") or
                ul in ("focus", "focus mode", "focus timer", "focus shuru")):

            print()
            print(c(C.ORANGE + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.ORANGE + C.BOLD, "  ║        🍅  POMODORO TIMER                   ║"))
            print(c(C.ORANGE + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()

            # Parse command
            arg = ""
            for pfx in ("pomodoro ", "pomo "):
                if ul.startswith(pfx):
                    arg = user_input[len(pfx):].strip()
                    break
            al = arg.lower().strip()

            if al in ("stop", "rok", "band", "cancel"):
                msg = pomo_stop()
                typing_print(f"  {msg}", C.RED)
                speak(msg)

            elif al in ("status", "check", "kitna", "kya chal raha"):
                print(pomo_status_str())

            else:
                # Parse: "pomodoro 45" or "pomodoro 25 5" or "pomodoro"
                import re as _re
                nums = _re.findall(r'\d+', al)
                focus_min = int(nums[0]) if len(nums) >= 1 else 25
                break_min = int(nums[1]) if len(nums) >= 2 else 5

                # Clamp to reasonable values
                focus_min = max(1, min(focus_min, 120))
                break_min = max(0, min(break_min, 30))

                msg = pomo_start(focus_min, break_min)
                typing_print(f"  {msg}", C.ORANGE)
                print()
                print(c(C.DIM, f"  Focus  : {focus_min} minutes"))
                print(c(C.DIM, f"  Break  : {break_min} minutes"))
                print(c(C.DIM,  "  Status : pomodoro status"))
                print(c(C.DIM,  "  Stop   : pomodoro stop"))
                speak(msg)

            print()
            continue

        # ── SMART TODO LIST ──
        if (ul.startswith("todo ") or ul.startswith("task ") or
                ul in ("todo", "todos", "tasks", "mera todo", "todo list",
                        "kaam", "mera kaam", "pending kaam")):

            arg = ""
            for pfx in ("todo ", "task "):
                if ul.startswith(pfx):
                    arg = user_input[len(pfx):].strip()
                    break
            al = arg.lower().strip()

            print()
            print(c(C.CYAN + C.BOLD,  "  ╔══════════════════════════════════════════════╗"))
            print(c(C.CYAN + C.BOLD,  "  ║        📋  SMART TODO LIST                  ║"))
            print(c(C.CYAN + C.BOLD,  "  ╚══════════════════════════════════════════════╝"))
            print()

            if ul in ("todo", "todos", "tasks", "mera todo", "todo list",
                      "kaam", "mera kaam", "pending kaam") or al == "list":
                todo_list("all")

            elif al == "pending":
                todo_list("pending")

            elif al == "done list":
                todo_list("done")

            elif al.startswith("add "):
                title = arg[4:].strip()
                msg   = todo_add(title)
                typing_print(f"  {msg}", C.LIME)
                speak(msg)

            elif al.startswith("done "):
                query = arg[5:].strip()
                msg   = todo_done(query)
                typing_print(f"  {msg}", C.LIME)
                speak(msg)

            elif al.startswith("delete ") or al.startswith("remove "):
                query = arg[7:].strip()
                msg   = todo_delete(query)
                typing_print(f"  {msg}", C.RED)
                speak(msg)

            elif al in ("clear", "clear done"):
                msg = todo_clear("done")
                typing_print(f"  {msg}", C.RED)
                speak(msg)

            elif al == "clear all":
                msg = todo_clear("all")
                typing_print(f"  {msg}", C.RED)
                speak(msg)

            else:
                # Default: add karo
                msg = todo_add(arg)
                typing_print(f"  {msg}", C.LIME)
                speak(msg)

            print()
            continue

        # ── HABIT TRACKER ──
        if ul.startswith("habit ") or ul in ("habits", "habit list", "meri habits",
                                              "habit dekho", "aaj ki habits"):
            arg = user_input[6:].strip() if ul.startswith("habit ") else ""
            al  = arg.lower().strip()

            print()
            print(c(C.LIME + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.LIME + C.BOLD, "  ║        💪  HABIT TRACKER                    ║"))
            print(c(C.LIME + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()

            if ul in ("habits", "habit list", "meri habits", "habit dekho", "aaj ki habits"):
                habit_list()

            elif al.startswith("add "):
                name = arg[4:].strip()
                if name:
                    msg = habit_add(name)
                    typing_print(f"  {msg}", C.LIME)
                    speak(msg)
                else:
                    print(c(C.YELLOW, "  Habit ka naam? Example: habit add pushups"))

            elif al.startswith("done "):
                name = arg[5:].strip()
                if name:
                    msg = habit_done(name)
                    typing_print(f"  {msg}", C.LIME)
                    speak(msg)
                else:
                    print(c(C.YELLOW, "  Kaunsi habit? Example: habit done pushups"))

            elif al.startswith("delete ") or al.startswith("remove "):
                name = arg[7:].strip()
                if name:
                    msg = habit_delete(name)
                    typing_print(f"  {msg}", C.RED)
                    speak(msg)
                else:
                    print(c(C.YELLOW, "  Kaunsi habit delete karein? Example: habit delete pushups"))

            elif al == "list" or al == "":
                habit_list()

            else:
                # Agar sirf naam likha — done samjho
                msg = habit_done(arg)
                typing_print(f"  {msg}", C.LIME)
                speak(msg)

            print()
            continue

        # ── QR CODE GENERATOR ──
        qr_input = None
        for pfx in ("qr ", "qr:", "qrcode ", "qrcode:"):
            if ul.startswith(pfx):
                qr_input = user_input[len(pfx):].strip()
                break

        if qr_input is not None:
            print()
            print(c(C.TEAL + C.BOLD,  "  ╔══════════════════════════════════════════════╗"))
            print(c(C.TEAL + C.BOLD,  "  ║        🔲  QR CODE GENERATOR                ║"))
            print(c(C.TEAL + C.BOLD,  "  ╚══════════════════════════════════════════════╝"))
            print()

            if not qr_input:
                print(c(C.YELLOW, "  Kya encode karoon? Example: qr https://google.com"))
                print()
            else:
                try:
                    import qrcode as _qr
                    import os as _os

                    QR_FILE = "friday_qr.png"

                    # Generate QR
                    qr = _qr.QRCode(
                        version=1,
                        error_correction=_qr.constants.ERROR_CORRECT_H,
                        box_size=10,
                        border=2,
                    )
                    qr.add_data(qr_input)
                    qr.make(fit=True)

                    # Save as image
                    img = qr.make_image(fill_color="black", back_color="white")
                    img.save(QR_FILE)

                    # Also print in terminal as ASCII
                    print(c(C.WHITE + C.BOLD, f"  📝 Data    : ") + c(C.YELLOW, qr_input[:60] + ("..." if len(qr_input) > 60 else "")))
                    print(c(C.TEAL,           f"  📁 Saved   : {_os.path.abspath(QR_FILE)}"))
                    print()

                    # Terminal QR preview
                    print(c(C.DIM, "  Terminal Preview:"))
                    print()
                    qr2 = _qr.QRCode(border=1)
                    qr2.add_data(qr_input)
                    qr2.make(fit=True)
                    matrix = qr2.get_matrix()
                    for row in matrix:
                        line = "  "
                        for cell in row:
                            line += "██" if cell else "  "
                        print(line)

                    print()
                    print(c(C.TEAL + C.BOLD, "  " + "═" * 46))
                    print()

                    # Open image
                    try:
                        subprocess.Popen(
                            ["termux-open", QR_FILE],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        print(c(C.DIM, f"  📸 Image gallery mein khul gaya!"))
                    except Exception:
                        pass

                    speak(f"QR code ready hai Boss. {QR_FILE} mein save ho gaya.")

                except ImportError:
                    print(c(C.YELLOW, "  ⚠ qrcode library nahi hai — install karo:"))
                    print(c(C.LIME,   "  pip install qrcode[pil]"))
                    print()
                except Exception as e:
                    print(c(C.RED, f"  ✗ Error: {e}"))
                    print()
            continue

        # ── DICTIONARY ──
        dict_word = None
        for pfx in ("meaning ", "meaning:", "define ", "define:", "dictionary ",
                    "dict ", "matlab ", "matlab:", "word "):
            if ul.startswith(pfx):
                dict_word = user_input[len(pfx):].strip()
                break

        if dict_word is not None:
            print()
            print(c(C.PURPLE + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.PURPLE + C.BOLD, "  ║        📚  DICTIONARY                       ║"))
            print(c(C.PURPLE + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()

            if not dict_word:
                print(c(C.YELLOW, "  Kaunsa word? Example: meaning serendipity"))
                print()
            else:
                try:
                    from urllib.request import urlopen, Request
                    from urllib.parse import quote
                    import json as _json

                    word_clean = dict_word.strip().lower().split()[0]  # first word only
                    print(c(C.DIM, f"  Looking up: \"{word_clean}\" ..."))
                    print()

                    url  = f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(word_clean)}"
                    req  = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    data = _json.loads(urlopen(req, timeout=8).read().decode())

                    if isinstance(data, dict) and data.get("title") == "No Definitions Found":
                        print(c(C.RED, f"  ✗ \"{word_clean}\" nahi mila dictionary mein."))
                        print(c(C.DIM, "  Spelling check karo ya English word use karo."))
                        print()
                    else:
                        entry    = data[0]
                        word     = entry.get("word", word_clean)
                        phonetic = entry.get("phonetic", "")
                        meanings = entry.get("meanings", [])
                        audio_url = ""

                        # Get audio if available
                        for ph in entry.get("phonetics", []):
                            if ph.get("audio"):
                                audio_url = ph.get("audio", "")
                                if not phonetic:
                                    phonetic = ph.get("text", "")
                                break

                        # Header
                        print(c(C.WHITE + C.BOLD, f"  📖 {word.upper()}"), end="")
                        if phonetic:
                            print(c(C.DIM, f"  {phonetic}"))
                        else:
                            print()
                        print()

                        voice_text = f"{word}. "
                        shown_defs = 0

                        for meaning in meanings[:3]:  # max 3 parts of speech
                            pos  = meaning.get("partOfSpeech", "")
                            defs = meaning.get("definitions", [])
                            syns = meaning.get("synonyms", [])
                            ants = meaning.get("antonyms", [])

                            # Part of speech header
                            pos_colors = {
                                "noun": C.CYAN, "verb": C.LIME, "adjective": C.YELLOW,
                                "adverb": C.PINK, "pronoun": C.TEAL, "preposition": C.ORANGE,
                            }
                            pos_col = pos_colors.get(pos, C.MAGENTA)
                            print(c(pos_col + C.BOLD, f"  ▸ {pos.title()}"))
                            print(c(C.PURPLE, "  " + "─" * 48))

                            for i, d in enumerate(defs[:3], 1):  # max 3 definitions
                                defn    = d.get("definition", "")
                                example = d.get("example", "")

                                print(c(C.WHITE + C.BOLD, f"  {i}. ") + c(C.WHITE, defn))
                                if example:
                                    print(c(C.DIM + C.ITALIC, f'     💬 "{example}"'))

                                if shown_defs == 0:
                                    voice_text += defn + ". "
                                shown_defs += 1

                            # Synonyms
                            if syns:
                                syn_str = ", ".join(syns[:6])
                                print(c(C.TEAL,  f"  ✦ Synonyms  : ") + c(C.LIME, syn_str))

                            # Antonyms
                            if ants:
                                ant_str = ", ".join(ants[:4])
                                print(c(C.ORANGE, f"  ✦ Antonyms  : ") + c(C.RED, ant_str))

                            print()

                        print(c(C.PURPLE + C.BOLD, "  " + "═" * 46))
                        print()
                        speak(voice_text.strip())

                except Exception as e:
                    err_str = str(e)
                    if "404" in err_str:
                        print(c(C.RED, f"  ✗ \"{dict_word}\" nahi mila — spelling check karo."))
                    else:
                        print(c(C.RED, f"  ✗ Error: {e}"))
                    print(c(C.DIM, "  Internet check karo."))
                    print()
            continue

        # ── CURRENCY CONVERTER ──
        conv_input = None
        for pfx in ("convert ", "currency ", "badlo "):
            if ul.startswith(pfx):
                conv_input = user_input[len(pfx):].strip()
                break

        # Natural language currency detection
        # "$500 indian rs", "500 dollar rupees mein", "100 euro to inr" etc.
        if conv_input is None:
            import re as _re2

            # Currency aliases map
            _CUR_ALIAS = {
                "dollar": "USD", "dollars": "USD", "$": "USD", "usd": "USD",
                "rupee": "INR", "rupees": "INR", "rs": "INR", "inr": "INR",
                "indian": "INR", "indian rs": "INR", "indian rupee": "INR",
                "euro": "EUR", "euros": "EUR", "eur": "EUR",
                "pound": "GBP", "pounds": "GBP", "gbp": "GBP",
                "yen": "JPY", "jpy": "JPY",
                "dirham": "AED", "aed": "AED",
                "riyal": "SAR", "sar": "SAR",
                "taka": "BDT", "bdt": "BDT",
                "pkr": "PKR", "pakistani": "PKR",
                "yuan": "CNY", "cny": "CNY",
                "bitcoin": "BTC", "btc": "BTC",
            }

            # Pattern 1: "$500 indian rs" or "500$ to inr"
            # Extract amount + currencies from natural text
            tl2 = ul.replace(",", "")
            amt_match = _re2.search(r'\$?\s*(\d+(?:\.\d+)?)\s*\$?', tl2)

            if amt_match:
                amt_str = amt_match.group(1)
                # Check if currency keywords present
                detected_curs = []
                for alias, code in sorted(_CUR_ALIAS.items(), key=lambda x: -len(x[0])):
                    if alias in tl2:
                        if code not in detected_curs:
                            detected_curs.append(code)

                # $ sign means USD
                if "$" in ul and "USD" not in detected_curs:
                    detected_curs.insert(0, "USD")

                if len(detected_curs) >= 2:
                    conv_input = f"{amt_str} {detected_curs[0]} to {detected_curs[1]}"
                elif len(detected_curs) == 1 and "$" in ul:
                    # "$500 indian" — USD to INR
                    conv_input = f"{amt_str} USD to {detected_curs[0]}"
                elif len(detected_curs) == 1 and detected_curs[0] == "INR":
                    # "500 rupees" with no target — assume USD
                    conv_input = f"{amt_str} INR to USD"

        if conv_input is not None:
            print()
            print(c(C.GOLD + C.BOLD,  "  ╔══════════════════════════════════════════════╗"))
            print(c(C.GOLD + C.BOLD,  "  ║        💱  CURRENCY CONVERTER               ║"))
            print(c(C.GOLD + C.BOLD,  "  ╚══════════════════════════════════════════════╝"))
            print()
            try:
                import re as _re
                from urllib.request import urlopen, Request
                import json as _json

                # Parse: "100 usd to inr" or "100 usd inr"
                m = _re.match(
                    r'([\d,]+(?:\.\d+)?)\s+([a-zA-Z]{3})\s+(?:to\s+)?([a-zA-Z]{3})',
                    conv_input.strip(), _re.IGNORECASE
                )
                if not m:
                    print(c(C.YELLOW, "  ✗ Format: convert 100 USD to INR"))
                    print(c(C.DIM,    "  Example: convert 500 usd to inr"))
                    print(c(C.DIM,    "           convert 1000 inr to usd"))
                    print(c(C.DIM,    "           convert 50 eur to gbp"))
                    print()
                else:
                    amount   = float(m.group(1).replace(",", ""))
                    from_cur = m.group(2).upper()
                    to_cur   = m.group(3).upper()

                    print(c(C.DIM, f"  Fetching rate: {from_cur} → {to_cur} ..."))
                    print()

                    # Free API — no key needed
                    url = f"https://api.exchangerate-api.com/v4/latest/{from_cur}"
                    req  = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    data = _json.loads(urlopen(req, timeout=8).read().decode())

                    rates = data.get("rates", {})
                    if to_cur not in rates:
                        print(c(C.RED, f"  ✗ Currency '{to_cur}' nahi mili."))
                        print(c(C.DIM, "  Common: USD, INR, EUR, GBP, JPY, AED, SAR, BDT, PKR, CNY"))
                        print()
                    else:
                        rate        = rates[to_cur]
                        result      = amount * rate
                        last_update = data.get("date", "?")

                        # Format numbers nicely
                        def fmt(n):
                            if n >= 1:
                                return f"{n:,.4f}".rstrip("0").rstrip(".")
                            return f"{n:.6f}".rstrip("0")

                        # Currency flag emojis for popular currencies
                        flags = {
                            "INR": "🇮🇳", "USD": "🇺🇸", "EUR": "🇪🇺", "GBP": "🇬🇧",
                            "JPY": "🇯🇵", "AED": "🇦🇪", "SAR": "🇸🇦", "BDT": "🇧🇩",
                            "PKR": "🇵🇰", "CNY": "🇨🇳", "CAD": "🇨🇦", "AUD": "🇦🇺",
                            "SGD": "🇸🇬", "CHF": "🇨🇭", "MYR": "🇲🇾", "THB": "🇹🇭",
                        }
                        f1 = flags.get(from_cur, "💰")
                        f2 = flags.get(to_cur,   "💰")

                        print(c(C.WHITE + C.BOLD, f"  {f1}  {fmt(amount)} {from_cur}  →  {f2}  {fmt(result)} {to_cur}"))
                        print()
                        print(c(C.YELLOW,         f"  📊 Exchange Rate  : 1 {from_cur} = {fmt(rate)} {to_cur}"))
                        print(c(C.DIM,            f"  📅 Last Updated   : {last_update}"))
                        print()
                        print(c(C.GOLD + C.BOLD,  "  " + "═" * 46))
                        print()

                        speak(f"{fmt(amount)} {from_cur} barabar hai {fmt(result)} {to_cur}.")

            except Exception as e:
                err_str = str(e)
                if "404" in err_str:
                    print(c(C.RED, f"  ✗ Currency '{from_cur}' valid nahi hai."))
                else:
                    print(c(C.RED, f"  ✗ Error: {e}"))
                print(c(C.DIM, "  Internet check karo."))
                print()
            continue

        # ── CALCULATOR ──
        calc_input = None
        for pfx in ("calc ", "calc:", "calculate ", "calculate:", "hisab ", "hisab:"):
            if ul.startswith(pfx):
                calc_input = user_input[len(pfx):].strip()
                break

        if calc_input is not None:
            print()
            print(c(C.LIME + C.BOLD,  "  ╔══════════════════════════════════════════════╗"))
            print(c(C.LIME + C.BOLD,  "  ║        🧮  CALCULATOR                       ║"))
            print(c(C.LIME + C.BOLD,  "  ╚══════════════════════════════════════════════╝"))
            print()

            try:
                import math as _math

                # ── Safe eval — only math allowed ──
                safe_env = {
                    # Basic
                    "__builtins__": {},
                    # Math functions
                    "sqrt":  _math.sqrt,
                    "cbrt":  lambda x: x ** (1/3),
                    "pow":   pow,
                    "abs":   abs,
                    "round": round,
                    "int":   int,
                    "float": float,
                    # Trig
                    "sin":   _math.sin,
                    "cos":   _math.cos,
                    "tan":   _math.tan,
                    "asin":  _math.asin,
                    "acos":  _math.acos,
                    "atan":  _math.atan,
                    "sinh":  _math.sinh,
                    "cosh":  _math.cosh,
                    "tanh":  _math.tanh,
                    # Log / Exp
                    "log":   _math.log,
                    "log2":  _math.log2,
                    "log10": _math.log10,
                    "exp":   _math.exp,
                    # Constants
                    "pi":    _math.pi,
                    "e":     _math.e,
                    "inf":   _math.inf,
                    # Utility
                    "ceil":  _math.ceil,
                    "floor": _math.floor,
                    "factorial": _math.factorial,
                    "gcd":   _math.gcd,
                    "degrees": _math.degrees,
                    "radians": _math.radians,
                }

                # Clean input — x/X → multiply, ^ → power
                expr = calc_input
                expr = expr.replace("^", "**")
                expr = expr.replace("×", "*")
                expr = expr.replace("÷", "/")
                expr = expr.replace(",", "")   # "1,000" → "1000"

                # Evaluate
                result = eval(expr, safe_env)

                # Format result nicely
                if isinstance(result, float):
                    if result == int(result) and abs(result) < 1e15:
                        result_str = str(int(result))
                    else:
                        result_str = f"{result:.10g}"
                else:
                    result_str = str(result)

                print(c(C.WHITE + C.BOLD,  f"  📥 Input   : ") + c(C.YELLOW, calc_input))
                print(c(C.LIME  + C.BOLD,  f"  📤 Result  : ") + c(C.WHITE + C.BOLD, result_str))
                print()
                print(c(C.LIME + C.BOLD,   "  " + "═" * 46))
                print()

                msg = f"{calc_input} ka jawab hai {result_str}"
                speak(msg)

            except ZeroDivisionError:
                print(c(C.RED, "  ✗ Zero se divide nahi kar sakte!"))
                print()
            except Exception:
                print(c(C.RED, f"  ✗ Samajh nahi aaya: \"{calc_input}\""))
                print(c(C.DIM, "  Examples:"))
                print(c(C.DIM, "    calc 25 * 4 + 10"))
                print(c(C.DIM, "    calc sqrt(144)"))
                print(c(C.DIM, "    calc 2^10"))
                print(c(C.DIM, "    calc sin(pi/2)"))
                print(c(C.DIM, "    calc factorial(10)"))
                print()
            continue

        # ── NEWS ──
        news_cmds = (
            "news", "khabar", "aaj ki news", "aaj ki khabar", "latest news",
            "news batao", "khabar batao", "aaj ka news", "breaking news",
            "top news", "headlines", "world news", "india news", "tech news",
            "sports news", "business news", "international news", "duniya ki news",
            "duniya ka news", "aaj ki khabrein", "taza khabar", "taza news",
            "news dikhao", "khabrein", "news kya hai", "kya news hai",
        )
        news_query  = None
        news_cat    = None

        # "news [topic]" format
        NEWS_CATEGORIES = ["business", "technology", "sports", "entertainment",
                           "health", "science", "politics", "world", "crime",
                           "cricket", "bollywood", "india"]
        for pfx in ("news ", "khabar "):
            if ul.startswith(pfx):
                arg = user_input[len(pfx):].strip()
                if arg.lower() in NEWS_CATEGORIES:
                    news_cat = arg.lower()
                else:
                    news_query = arg
                break

        if ul in news_cmds or news_query is not None or news_cat is not None:
            print()
            print(c(C.ORANGE + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.ORANGE + C.BOLD, "  ║        📰  LATEST NEWS                      ║"))
            print(c(C.ORANGE + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()

            NEWS_KEY = os.environ.get("NEWSDATA_API_KEY", "")
            if not NEWS_KEY:
                print(c(C.RED, "  ✗ NEWSDATA_API_KEY set nahi hai!"))
                print(c(C.DIM, "  Run: export NEWSDATA_API_KEY=\"aapki_key\""))
                print()
            else:
                try:
                    from urllib.request import urlopen, Request
                    from urllib.parse import quote_plus
                    import json as _json

                    # ── URL build karo ──
                    base = "https://newsdata.io/api/1/latest"
                    params = f"?apikey={NEWS_KEY}&language=en&country=in"

                    if news_query:
                        params += f"&q={quote_plus(news_query)}"
                        label  = f"🔍 Search: \"{news_query}\""
                    elif news_cat:
                        params += f"&category={news_cat}"
                        label  = f"📂 Category: {news_cat.title()}"
                    else:
                        label  = "🇮🇳 India Top Headlines"

                    print(c(C.DIM, f"  {label} — fetching..."))
                    print()

                    req  = Request(base + params, headers={"User-Agent": "Mozilla/5.0"})
                    resp = urlopen(req, timeout=10)
                    data = _json.loads(resp.read().decode())

                    if data.get("status") != "success":
                        print(c(C.RED, f"  ✗ API Error: {data.get('message', 'Unknown error')}"))
                        print()
                    else:
                        articles = data.get("results", [])[:6]  # top 6 news

                        if not articles:
                            print(c(C.DIM, "  Koi news nahi mili — query try karo."))
                        else:
                            print(c(C.YELLOW + C.BOLD, f"  {label}"))
                            print(c(C.ORANGE, "  " + "─" * 52))
                            print()

                            voice_headlines = []

                            # Groq se Hinglish translation
                            try:
                                raw_titles = []
                                for art in articles:
                                    t = art.get("title", "") or ""
                                    d = art.get("description", "") or ""
                                    raw_titles.append(f"- {t}: {d[:80]}")

                                hinglish_resp = client.chat.completions.create(
                                    model=MODEL,
                                    messages=[
                                        {"role": "system", "content": (
                                            "Tu ek Hinglish news translator hai.\n"
                                            "Rules:\n"
                                            "1. Har news ko natural Hinglish mein likho — jaise dost baat karta hai\n"
                                            "2. Sirf Roman script — Devanagari bilkul nahi\n"
                                            "3. Format: 'Title: [short Hinglish title]\nDetail: [1 line detail]'\n"
                                            "4. Har news alag block mein — khali line se alag karo\n"
                                            "5. Links, URLs, sources bilkul mat likho\n"
                                            "6. Sirf content — koi intro nahi, koi outro nahi"
                                        )},
                                        {"role": "user", "content": "\n".join(raw_titles)}
                                    ],
                                    temperature=0.3,
                                    max_tokens=400,
                                )
                                hinglish_news = hinglish_resp.choices[0].message.content.strip()
                                blocks = [b.strip() for b in hinglish_news.split("\n\n") if b.strip()]
                            except Exception:
                                blocks = []

                            num_cols = [C.CYAN, C.LIME, C.YELLOW, C.PINK, C.TEAL, C.ORANGE]

                            for i, art in enumerate(articles, 1):
                                num_col = num_cols[(i - 1) % len(num_cols)]

                                # Hinglish block use karo agar available ho
                                if i - 1 < len(blocks):
                                    block = blocks[i - 1]
                                    lines = block.split("\n")
                                    title_line = lines[0].replace("Title:", "").strip() if lines else ""
                                    detail_line = lines[1].replace("Detail:", "").strip() if len(lines) > 1 else ""
                                else:
                                    # Fallback — original title use karo
                                    title_line = (art.get("title", "") or "")[:80]
                                    detail_line = (art.get("description", "") or "")[:100]

                                print(c(num_col + C.BOLD, f"  {i}. {title_line}"))
                                if detail_line:
                                    print(c(C.DIM, f"     {detail_line}"))
                                # Date only — no link, no source
                                pub_date = (art.get("pubDate", "") or "")[:10]
                                if pub_date:
                                    print(c(C.DIM, f"     📅 {pub_date}"))
                                print()

                                voice_headlines.append(f"{i}. {title_line}")

                            print(c(C.ORANGE, "  " + "─" * 52))
                            total = data.get("totalResults", len(articles))
                            print(c(C.DIM, f"  Kul {len(articles)} khabrein"))
                            print()
                            print(c(C.ORANGE + C.BOLD, "  " + "═" * 46))
                            print()

                            # Voice — first 3 headlines
                            voice_text = "Aaj ki top khabrein: " + " | ".join(voice_headlines[:3])
                            speak(voice_text)

                except Exception as e:
                    err_str = str(e)
                    if "401" in err_str or "403" in err_str:
                        print(c(C.RED, "  ✗ API Key galat hai — NewsData.io check karo."))
                    elif "422" in err_str:
                        print(c(C.RED, "  ✗ Query format galat hai — simple words use karo."))
                    else:
                        print(c(C.RED, f"  ✗ Error: {e}"))
                    print()
            continue

        # ── IP LOOKUP ──
        if (ul.startswith("iplookup ") or ul.startswith("iplookup:") or
                ul.startswith("ip lookup ") or ul.startswith("ip check ")):
            ip_target = ""
            for pfx in ("iplookup ", "iplookup:", "ip lookup ", "ip check "):
                if ul.startswith(pfx):
                    ip_target = user_input[len(pfx):].strip()
                    break

            if not ip_target:
                print(c(C.YELLOW, "\n  Kya lookup karoon? Example: iplookup 8.8.8.8  ya  iplookup google.com\n"))
            else:
                print()
                print(c(C.TEAL + C.BOLD,  "  ╔══════════════════════════════════════════════╗"))
                print(c(C.TEAL + C.BOLD,  "  ║        🌐  IP LOOKUP                        ║"))
                print(c(C.TEAL + C.BOLD,  "  ╚══════════════════════════════════════════════╝"))
                print()
                print(c(C.DIM, f"  Looking up: {ip_target} ..."))
                print()

                try:
                    import socket
                    from urllib.request import urlopen, Request
                    import json as _json

                    # ── Step 1: Domain → IP resolve karo ──
                    resolved_ip = ip_target
                    is_domain   = False
                    # Check if it's a domain (not pure IP)
                    import re as _re
                    if not _re.match(r'^\d{1,3}(\.\d{1,3}){3}$', ip_target):
                        try:
                            resolved_ip = socket.gethostbyname(ip_target)
                            is_domain   = True
                        except socket.gaierror:
                            print(c(C.RED, f"  ✗ Domain resolve nahi hua: {ip_target}"))
                            print(c(C.DIM, "  Check karo: spelling sahi hai? Internet on hai?"))
                            print()
                            continue

                    # ── Step 2: ip-api.com se details lo ──
                    api_url = f"http://ip-api.com/json/{resolved_ip}?fields=status,message,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query,mobile,proxy,hosting"
                    req  = Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
                    resp = urlopen(req, timeout=8)
                    data = _json.loads(resp.read().decode())

                    if data.get("status") == "success":
                        country      = data.get("country",     "?")
                        country_code = data.get("countryCode", "?")
                        region       = data.get("regionName",  "?")
                        city         = data.get("city",        "?")
                        zipcode      = data.get("zip",         "?")
                        lat          = data.get("lat",          0)
                        lon          = data.get("lon",          0)
                        timezone     = data.get("timezone",    "?")
                        isp          = data.get("isp",         "?")
                        org          = data.get("org",         "?")
                        asn          = data.get("as",          "?")
                        is_mobile    = data.get("mobile",      False)
                        is_proxy     = data.get("proxy",       False)
                        is_hosting   = data.get("hosting",     False)
                        final_ip     = data.get("query",       resolved_ip)

                        # ── Display ──
                        if is_domain:
                            print(c(C.GOLD + C.BOLD,  f"  🔗 Domain     : ") + c(C.WHITE + C.BOLD, ip_target))
                        print(c(C.GOLD + C.BOLD,      f"  📡 IP Address : ") + c(C.LIME  + C.BOLD, final_ip))
                        print()
                        print(c(C.CYAN + C.BOLD,      f"  📍 Location"))
                        print(c(C.CYAN,               f"     Country    : {country} ({country_code})"))
                        print(c(C.CYAN,               f"     Region     : {region}"))
                        print(c(C.CYAN,               f"     City       : {city}"))
                        print(c(C.CYAN,               f"     ZIP        : {zipcode}"))
                        print(c(C.CYAN,               f"     Lat / Lon  : {lat}°, {lon}°"))
                        print(c(C.CYAN,               f"     Timezone   : {timezone}"))
                        print()
                        print(c(C.MAGENTA + C.BOLD,   f"  🏢 Network"))
                        print(c(C.MAGENTA,            f"     ISP        : {isp}"))
                        print(c(C.MAGENTA,            f"     Org        : {org}"))
                        print(c(C.MAGENTA,            f"     ASN        : {asn}"))
                        print()

                        # ── Flags ──
                        mobile_str  = c(C.GREEN, "✓ Yes") if is_mobile  else c(C.DIM, "✗ No")
                        proxy_str   = c(C.RED,   "⚠ Yes") if is_proxy   else c(C.DIM, "✗ No")
                        hosting_str = c(C.YELLOW,"● Yes") if is_hosting else c(C.DIM, "✗ No")
                        print(c(C.GOLD + C.BOLD, f"  🔍 Flags"))
                        print(c(C.WHITE,         f"     Mobile     : ") + mobile_str)
                        print(c(C.WHITE,         f"     Proxy/VPN  : ") + proxy_str)
                        print(c(C.WHITE,         f"     Hosting    : ") + hosting_str)
                        print()

                        # ── Google Maps link ──
                        maps_url = f"https://maps.google.com/?q={lat},{lon}"
                        print(c(C.GOLD + C.BOLD, f"  🗺️  Maps        : {maps_url}"))
                        print()
                        print(c(C.TEAL + C.BOLD, "  " + "═" * 46))
                        print()

                        voice_msg = f"IP {final_ip} ka location hai {city}, {region}, {country}. ISP: {isp}."
                        speak(voice_msg)

                    else:
                        err = data.get("message", "Unknown error")
                        print(c(C.RED, f"  ✗ Lookup fail hua: {err}"))
                        print(c(C.DIM, "  Private/Reserved IPs ka lookup nahi hota (e.g. 192.168.x.x, 127.0.0.1)"))
                        print()

                except Exception as e:
                    print(c(C.RED, f"  ✗ Error: {e}"))
                    print(c(C.DIM, "  Internet connection check karo."))
                    print()

            continue

        # ── YOUTUBE OPEN ──
        if ul in ("youtube", "youtube kholo", "youtube chalaao", "yt", "youtube open",
                  "open youtube", "youtube kholna", "youtube play"):
            try:
                subprocess.Popen(["termux-open-url", "https://www.youtube.com"])
            except FileNotFoundError:
                subprocess.Popen(["xdg-open", "https://www.youtube.com"])
            msg = "YouTube khol diya Boss! 🎬"
            print_friday_prompt()
            sys.stdout.flush()
            typing_print(msg, C.RED)
            speak(msg)
            continue

        # ── GOOGLE SEARCH ──
        search_prefixes = ("search ", "search:", "google ", "google:", "dhundo ", "dhundho ",
                           "search karo ", "google karo ", "khojo ")
        matched_search = None
        for pfx in search_prefixes:
            if ul.startswith(pfx):
                matched_search = user_input[len(pfx):].strip()
                break

        if matched_search:
            import urllib.parse
            query_encoded = urllib.parse.quote_plus(matched_search)
            url = f"https://www.google.com/search?q={query_encoded}"
            try:
                subprocess.Popen(["termux-open-url", url])
            except FileNotFoundError:
                subprocess.Popen(["xdg-open", url])
            msg = f"Google par search kar diya: \"{matched_search}\" 🔍"
            print_friday_prompt()
            sys.stdout.flush()
            typing_print(msg, C.DEEPBLUE)
            speak(msg)
            continue

        # ── DDGR MANUAL SEARCH COMMAND ──
        if ul.startswith("ddgr ") or ul.startswith("ddgr:"):
            ddgr_query = user_input[5:].strip() if ul.startswith("ddgr ") else user_input[5:].strip()
            if not ddgr_query:
                print(c(C.YELLOW, "\n  Kya search karoon? Example: ddgr bitcoin price\n"))
                continue

            print()
            print(c(C.TEAL + C.BOLD, f"  🔍 Searching: \"{ddgr_query}\""))
            print(c(C.TEAL, "  " + "─" * 52))

            raw = do_web_search(ddgr_query)

            if raw and "nahi mila" not in raw:
                # ── Groq se Roman Hindi mein convert + voice ke liye short summary ──
                try:
                    convert_resp = client.chat.completions.create(
                        model=MODEL,
                        messages=[
                            {"role": "system", "content": (
                                "Tu ek Hinglish translator hai. Rules:\n"
                                "1. Text ko natural, casual Hinglish mein likho — jaise do dost baat karte hain.\n"
                                "2. KABHI formal/Sanskrit words mat use karo: 'samapti' nahi — 'khatam'; 'tithi' nahi — 'date'; 'pavitra' nahi — 'holy'; 'shuruaat' nahi — 'shuru'; 'upavas' nahi — 'roza'.\n"
                                "3. Format rakho: '• Title: Content'\n"
                                "4. Devanagari script bilkul nahi — sirf Roman letters.\n"
                                "5. Sirf results likho, koi intro ya explanation nahi."
                            )},
                            {"role": "user", "content": raw}
                        ],
                        temperature=0.2,
                        max_tokens=300,
                    )
                    roman_result = convert_resp.choices[0].message.content.strip()
                except Exception:
                    roman_result = raw  # fallback — original dikhao

                lines = roman_result.strip().split("\n")
                for line in lines:
                    print(c(C.WHITE, f"  {line}"))

                # ── Voice: pehli 2 lines bold karke bolo ──
                voice_lines = [l.strip() for l in roman_result.strip().split("\n") if l.strip()]
                voice_text  = " ".join(voice_lines[:2]).replace("•", "")
                speak(voice_text)

                # ── 🧠 DDGR SEARCH LEARNING — Friday khud decide kare ──
                try:
                    learn_resp = client.chat.completions.create(
                        model=MODEL,
                        messages=[
                            {"role": "system", "content": (
                                "Tu ek smart knowledge filter hai.\n"
                                "Neeche ek web search result hai. Tera kaam:\n"
                                "1. Dekh ki kya koi TRULY USEFUL fact hai jo future mein kaam aa sake.\n"
                                "2. Agar hai — ek short, clear fact likho: '[FACT]: ...'\n"
                                "3. Agar koi useful fact nahi hai — sirf likho: '[SKIP]'\n"
                                "Rules:\n"
                                "- Sirf facts save karo — opinions, ads, irrelevant info nahi\n"
                                "- Fact 10-60 words ka hona chahiye\n"
                                "- Breaking news, prices, important info — save karo\n"
                                "- General/obvious info — skip karo\n"
                                "Format: [FACT]: yahan fact likho  ya  [SKIP]"
                            )},
                            {"role": "user", "content": f"Search query: {ddgr_query}\nResult:\n{raw[:500]}"}
                        ],
                        temperature=0.1,
                        max_tokens=80,
                    )
                    learn_decision = learn_resp.choices[0].message.content.strip()

                    if learn_decision.startswith("[FACT]:"):
                        fact_text = learn_decision[7:].strip()
                        if fact_text and len(fact_text) > 10:
                            add_to_long_term(long_mem, f"[Search: {ddgr_query}] {fact_text}")
                            print(c(C.GOLD, "  🧠 Friday ne seekha: ") + c(C.LIME, f'"{fact_text}"'))
                    # [SKIP] — kuch save nahi
                except Exception:
                    pass  # Learning fail ho toh koi baat nahi

            else:
                print(c(C.DIM, "  Koi result nahi mila."))

            print(c(C.TEAL, "  " + "─" * 52))
            print()
            continue

        # ══════════════════════════════════════════════════════

        # ── MP3 DOWNLOAD (yt-dlp) ──
        dl_query = None
        for pfx in ("song download ", "download song ", "mp3 download ",
                    "download mp3 ", "mp3 ", "gana download ", "download gana ",
                    "song dl ", "dl song ", "download "):
            if ul.startswith(pfx):
                dl_query = user_input[len(pfx):].strip()
                break

        if dl_query:
            import subprocess as _sp
            import os as _os
            import re as _re_dl
            import sys as _sys

            # Download folder
            DL_FOLDER = "/sdcard/Music/Friday"
            try:
                _os.makedirs(DL_FOLDER, exist_ok=True)
            except Exception:
                DL_FOLDER = _os.path.expanduser("~/storage/music")
                try:
                    _os.makedirs(DL_FOLDER, exist_ok=True)
                except Exception:
                    DL_FOLDER = _os.path.expanduser("~")

            print()
            print(c(C.LIME + C.BOLD,  "  ╔══════════════════════════════════════════════╗"))
            print(c(C.LIME + C.BOLD,  "  ║        🎵  MP3 DOWNLOADER                  ║"))
            print(c(C.LIME + C.BOLD,  "  ╚══════════════════════════════════════════════╝"))
            print()
            print(c(C.CYAN,  f"  🔍 Search : {dl_query}"))
            print(c(C.DIM,   f"  📁 Folder : {DL_FOLDER}"))
            print()

            try:
                # Step 1: Search — get title + video id
                print(c(C.DIM, "  ⏳ YouTube pe dhundh raha hoon..."), flush=True)
                search_cmd = [
                    "yt-dlp",
                    f"ytsearch1:{dl_query}",
                    "--print", "%(title)s",
                    "--print", "%(id)s",
                    "--no-playlist", "--quiet",
                ]
                result = _sp.run(search_cmd, capture_output=True, text=True, timeout=30)
                lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]

                if not lines or len(lines) < 2:
                    print(c(C.RED, "  ✗ Koi result nahi mila. Dusra naam try karo."))
                    print()
                else:
                    song_title  = lines[0]
                    video_id    = lines[1]
                    song_url    = f"https://www.youtube.com/watch?v={video_id}"
                    display_title = song_title[:65] + "..." if len(song_title) > 65 else song_title

                    print(c(C.LIME,   f"  ✓ Mila  : {display_title}"))
                    print()

                    # Step 2: Download as MP3 — NO --progress flag, capture stderr too
                    dl_cmd = [
                        "yt-dlp",
                        "-x",
                        "--audio-format", "mp3",
                        "--audio-quality", "0",
                        "--no-playlist",
                        "--newline",           # each progress on new line
                        "--no-colors",         # no ANSI escape codes
                        "--output", f"{DL_FOLDER}/%(title)s.%(ext)s",
                        song_url,
                    ]

                    proc = _sp.Popen(
                        dl_cmd,
                        stdout=_sp.PIPE,
                        stderr=_sp.PIPE,
                        text=True,
                    )

                    # Clean progress display
                    last_pct  = -1
                    bar_width = 30

                    print(c(C.YELLOW + C.BOLD, "  ⬇️  Downloading..."), flush=True)
                    print()

                    stdout_lines, stderr_lines = proc.communicate()

                    # Parse progress from output
                    all_output = stdout_lines + stderr_lines
                    pct_found  = 0
                    for ol in all_output.split("\n"):
                        ol = ol.strip()
                        pct_m = _re_dl.search(r"(\d+\.\d+)%", ol)
                        if pct_m:
                            pct_found = float(pct_m.group(1))

                    # Show clean final bar
                    filled = int(bar_width * pct_found / 100)
                    bar = "█" * filled + "░" * (bar_width - filled)
                    print(f"  [{c(C.LIME, bar)}] {pct_found:.0f}%")
                    print()

                    # Check success — look for mp3 file
                    mp3_files = []
                    try:
                        for f in _os.listdir(DL_FOLDER):
                            if f.endswith(".mp3"):
                                full = _os.path.join(DL_FOLDER, f)
                                mp3_files.append((full, _os.path.getmtime(full)))
                        mp3_files.sort(key=lambda x: x[1], reverse=True)
                    except Exception:
                        pass

                    success = proc.returncode == 0 or (
                        mp3_files and
                        (__import__("time").time() - mp3_files[0][1]) < 30
                    )

                    if success:
                        saved_name = _os.path.basename(mp3_files[0][0]) if mp3_files else display_title
                        print(c(C.LIME + C.BOLD, "  ✅ Download complete!"))
                        print(c(C.WHITE,          f"  🎵 {saved_name[:60]}"))
                        print(c(C.DIM,            f"  📁 {DL_FOLDER}/"))
                        print()
                        print(c(C.YELLOW,         "  💡 Ab 'music' type karo — playlist mein aa jayega!"))
                        print()
                        print(c(C.LIME + C.BOLD,  "  " + "═" * 46))
                        print()
                        speak(f"Download complete Boss!")
                    else:
                        # Show actual error
                        err_snippet = ""
                        for el in (stdout_lines + stderr_lines).split("\n"):
                            if "error" in el.lower() or "ERROR" in el:
                                err_snippet = el.strip()[:80]
                                break
                        print(c(C.RED,  "  ✗ MP3 conversion fail hua."))
                        if err_snippet:
                            print(c(C.DIM, f"  Error: {err_snippet}"))
                        print(c(C.DIM,  "  Try: yt-dlp --version  aur  ffmpeg -version"))
                        print()

            except _sp.TimeoutExpired:
                print(c(C.RED, "  ✗ Timeout — Internet slow hai."))
                print()
            except FileNotFoundError:
                print(c(C.RED,  "  ✗ yt-dlp nahi mila!"))
                print(c(C.DIM,  "  Install: pip install yt-dlp"))
                print()
            except Exception as e:
                print(c(C.RED,  f"  ✗ Error: {e}"))
                print()
            continue

        #  🎵  MUSIC PLAYER COMMANDS
        # ══════════════════════════════════════════════════════

        # ── MUSIC LIST / SCAN ──
        if ul in ("music", "gaane", "gaane dikho", "gaane dikhao", "songs", "playlist",
                  "music list", "gaane list", "meri songs", "meri music",
                  "gane dikho", "song list", "mera music", "mere gaane"):
            _music_playlist.clear()
            _music_playlist.extend(scan_music_files())
            do_music_list(_music_playlist)
            if _music_playlist:
                msg = f"Aapke {len(_music_playlist)} gaane mil gaye Boss! Bajane ke liye 'gana bajao' bolein."
            else:
                msg = "Koi gaana nahi mila Boss. Download folder mein MP3 files hain?"
            print_friday_prompt()
            sys.stdout.flush()
            typing_print(msg, C.LIME)
            # NO speak() — music chal raha ho sakta hai
            continue

        # ── GANA BAJAO [naam] / PLAY SONG ──
        if (ul in ("gana bajao", "song bajao", "music bajao", "gana chalaao",
                   "music play", "play music", "music shuru", "gana shuru karo",
                   "music on", "gana on", "gana shuru", "play song", "bajao", "gana") or
                ul.startswith("gana bajao ") or ul.startswith("song bajao ") or
                ul.startswith("music bajao ") or ul.startswith("bajao ") or
                ul.startswith("play song ") or ul.startswith("play gana ") or
                ul.startswith("play music ")):

            if not _music_playlist:
                _music_playlist.extend(scan_music_files())

            if not _music_playlist:
                show_music_banner()
                print(c(C.YELLOW, "  ⚠  Koi gaana nahi mila!"))
                print(c(C.DIM,    "  /sdcard/Download ya /sdcard/Music mein MP3 files daalo."))
                print()
                msg = "Koi gaana nahi mila Boss. Download folder check karo."
                print_friday_prompt(); sys.stdout.flush()
                typing_print(msg, C.YELLOW)
                # NO speak()
                continue

            # Search by name?
            search_name = ""
            for pfx in ("gana bajao ", "song bajao ", "music bajao ", "bajao ",
                        "play song ", "play gana ", "play music "):
                if ul.startswith(pfx):
                    search_name = user_input[len(pfx):].strip()
                    break

            if search_name:
                sl = search_name.lower()
                sl_words = sl.split()

                # Level 1: exact substring match
                matches = [(i, fp) for i, fp in enumerate(_music_playlist)
                           if sl in get_song_name(fp).lower()]

                # Level 2: all words present anywhere in name
                if not matches:
                    matches = [(i, fp) for i, fp in enumerate(_music_playlist)
                               if all(w in get_song_name(fp).lower() for w in sl_words)]

                # Level 3: any word matches (best score wins)
                if not matches:
                    scored = []
                    for i, fp in enumerate(_music_playlist):
                        sn = get_song_name(fp).lower()
                        score = sum(1 for w in sl_words if w in sn)
                        if score > 0:
                            scored.append((score, i, fp))
                    if scored:
                        scored.sort(reverse=True)
                        matches = [(s[1], s[2]) for s in scored[:1]]

                if not matches:
                    show_music_banner()
                    print(c(C.YELLOW, f"  ⚠  \"{search_name}\" se koi gaana nahi mila."))
                    print(c(C.DIM,    "  'music' likh ke poori list dekho."))
                    print()
                    msg = f"{search_name} naam ka gaana nahi mila Boss."
                    print_friday_prompt(); sys.stdout.flush()
                    typing_print(msg, C.YELLOW)
                    # NO speak()
                    continue
                _music_index = matches[0][0]

            show_music_banner()
            fp = _music_playlist[_music_index]
            sname = get_song_name(fp)
            msg = f"Bajaa rahi hoon Boss: {sname} 🎵"
            print_friday_prompt(); sys.stdout.flush()
            typing_print(msg, C.LIME)
            # Speak PEHLE, phir gana bajao — is tarah interrupt nahi hoga
            speak(f"Baja rahi hoon {sname}")
            ok = music_play_file(fp)
            if ok:
                show_now_playing(fp, _music_index, len(_music_playlist))
            else:
                print_friday_prompt(); sys.stdout.flush()
                typing_print("Player nahi mila Boss. termux-api ya mpv install karo.", C.RED)
            continue

        # ── NEXT SONG / AGLA GANA ──
        if ul in ("next song", "agla gana", "agla song", "next", "agli song",
                  "next gana", "next track", "aage", "aage bajao", "skip",
                  "skip song", "next chalao"):
            if not _music_playlist:
                _music_playlist.extend(scan_music_files())
            if not _music_playlist:
                msg = "Pehle playlist scan karo Boss — 'music' likho."
                print_friday_prompt(); sys.stdout.flush()
                typing_print(msg, C.YELLOW)
                continue

            _music_index = (_music_index + 1) % len(_music_playlist)
            fp = _music_playlist[_music_index]
            sname = get_song_name(fp)
            show_music_banner()
            msg = f"Agla gana: {sname} 🎵"
            print_friday_prompt(); sys.stdout.flush()
            typing_print(msg, C.CYAN)
            speak(f"Agla gana {sname}")
            ok = music_play_file(fp)
            if ok:
                show_now_playing(fp, _music_index, len(_music_playlist))
            continue

        # ── BACK SONG / PICHLA GANA ──
        if ul in ("back song", "pichla gana", "pichla song", "back", "pichli song",
                  "previous song", "prev song", "peeche", "pichhe bajao",
                  "back gana", "previous"):
            if not _music_playlist:
                _music_playlist.extend(scan_music_files())
            if not _music_playlist:
                msg = "Pehle playlist scan karo Boss — 'music' likho."
                print_friday_prompt(); sys.stdout.flush()
                typing_print(msg, C.YELLOW)
                continue

            _music_index = (_music_index - 1) % len(_music_playlist)
            fp = _music_playlist[_music_index]
            sname = get_song_name(fp)
            show_music_banner()
            msg = f"Pichla gana: {sname} 🎵"
            print_friday_prompt(); sys.stdout.flush()
            typing_print(msg, C.MAGENTA)
            speak(f"Pichla gana {sname}")
            ok = music_play_file(fp)
            if ok:
                show_now_playing(fp, _music_index, len(_music_playlist))
            continue

        # ── STOP SONG / GANA BAND KARO ──
        if ul in ("gana band karo", "gana bund karo", "stop song", "music stop",
                  "gana rok do", "gana band", "gana bund", "music band", "stop music",
                  "song stop", "band karo gana", "bund karo gana", "rok do gana",
                  "music band karo", "music bund karo", "song band karo", "song bund karo",
                  "stop gana", "gana roko", "music roko", "music off", "gana off",
                  "gana stop", "song off", "music rok do", "gana band kar do",
                  "gana bund kar do"):
            show_music_banner()
            music_stop()
            print(c(C.RED + C.BOLD, "  ⏹  Gana band kar diya."))
            print()
            msg = "Gana rok diya Boss. ⏹"
            print_friday_prompt(); sys.stdout.flush()
            typing_print(msg, C.PINK)
            # NO speak() — TTS se gana interrupt hoga
            continue

        # ── NOW PLAYING / AAJ KA GANA ──
        if ul in ("aaj ka gana", "kaunsa gana chal raha", "now playing",
                  "current song", "abhi kya chal raha", "kya gana chal raha hai",
                  "kaunsa song hai", "kya baj raha hai", "gana kya hai", "song info"):
            show_music_banner()
            if _music_playing and _music_playlist:
                fp = _music_playlist[_music_index]
                if _music_process and _music_process.poll() is None:
                    show_now_playing(fp, _music_index, len(_music_playlist))
                    msg = f"Abhi chal raha hai: {get_song_name(fp)} 🎵"
                else:
                    _music_playing = False
                    print(c(C.DIM, "  (Gana khatam ho gaya)"))
                    print()
                    msg = "Abhi koi gana nahi chal raha Boss."
            else:
                print(c(C.DIM, "  (Abhi koi gana nahi chal raha)"))
                print()
                msg = "Abhi koi gana nahi chal raha Boss. 'gana bajao' bolo!"
            print_friday_prompt(); sys.stdout.flush()
            typing_print(msg, C.LIME)
            # NO speak()
            continue


        # ── VOLUME UP ──
        if ul in ("volume up", "volume badhao", "awaaz badhao", "volume barhao",
                  "sound up", "louder", "thoda tez", "tez karo",
                  "volume bada do", "awaaz bada do", "volume increase",
                  "volume upar", "vol up"):
            new_vol = min(100, _music_volume + 10)
            music_set_volume(new_vol)
            _music_volume = new_vol
            bar_filled = round(_music_volume / 5)
            bar = "█" * bar_filled + "░" * (20 - bar_filled)
            print()
            print(c(C.LIME + C.BOLD, f"  🔊  Volume: ") + c(C.WHITE + C.BOLD, f"{_music_volume}%"))
            print(c(C.TEAL,          f"  [{bar}]"))
            print()
            msg = f"Awaaz badha di — ab {_music_volume} percent hai."
            print_friday_prompt(); sys.stdout.flush()
            typing_print(msg, C.LIME)
            speak(msg)
            continue

        # ── VOLUME DOWN ──
        if ul in ("volume down", "volume kam karo", "awaaz kam karo", "volume ghataao",
                  "sound down", "quieter", "thoda kam", "kam karo",
                  "volume chota karo", "thoda low karo", "awaaz kam do",
                  "volume decrease", "volume neeche", "vol down"):
            new_vol = max(0, _music_volume - 10)
            music_set_volume(new_vol)
            _music_volume = new_vol
            bar_filled = round(_music_volume / 5)
            bar = "█" * bar_filled + "░" * (20 - bar_filled)
            print()
            print(c(C.LIME + C.BOLD, f"  🔉  Volume: ") + c(C.WHITE + C.BOLD, f"{_music_volume}%"))
            print(c(C.TEAL,          f"  [{bar}]"))
            print()
            msg = f"Awaaz kam kar di — ab {_music_volume} percent hai."
            print_friday_prompt(); sys.stdout.flush()
            typing_print(msg, C.PINK)
            speak(msg)
            continue

        # ── VOLUME SET (e.g. "volume 50") ──
        if ul.startswith("volume ") and len(ul) > 7:
            vol_part = ul[7:].strip()
            if vol_part.isdigit():
                new_vol = max(0, min(100, int(vol_part)))
                music_set_volume(new_vol)
                _music_volume = new_vol
                bar_filled = round(_music_volume / 5)
                bar = "█" * bar_filled + "░" * (20 - bar_filled)
                vol_emoji = "🔇" if new_vol == 0 else ("🔈" if new_vol < 40 else ("🔉" if new_vol < 75 else "🔊"))
                print()
                print(c(C.LIME + C.BOLD, f"  {vol_emoji}  Volume: ") + c(C.WHITE + C.BOLD, f"{_music_volume}%"))
                print(c(C.TEAL,          f"  [{bar}]"))
                print()
                msg = f"Volume {_music_volume} percent set kar diya."
                print_friday_prompt(); sys.stdout.flush()
                typing_print(msg, C.LIME)
                speak(msg)
                continue

        # ══════════════════════════════════════════════════════

        # ══════════════════════════════════════════════════════
        #  🧠  INTELLIGENT FEATURES
        # ══════════════════════════════════════════════════════

        # ── SYSTEM INFO ──
        if ul in ("system info", "system", "sysinfo", "phone info", "battery",
                  "battery status", "ram", "storage", "phone ki info", "cpu",
                  "battery kitni hai", "storage kitna hai", "ram kitna hai"):
            show_system_info()
            info = get_system_info()
            batt = info.get("battery", "?")
            ram_free = info.get("ram_free", "?")
            msg = f"Battery {batt} percent hai, RAM free {ram_free} hai Boss."
            print_friday_prompt(); sys.stdout.flush()
            typing_print(msg, C.TEAL)
            speak(msg)
            continue

        # ── APP LAUNCHER ──
        app_query = None
        for pfx in ("kholo ", "open ", "launch ", "start ", "app kholo ", "app open "):
            if ul.startswith(pfx):
                app_query = user_input[len(pfx):].strip()
                break
        if app_query:
            ok = app_open(app_query)
            if ok:
                msg = f"{app_query.title()} khol diya Boss!"
            else:
                msg = f"{app_query.title()} nahi mila. Package name check karo."
            print_friday_prompt(); sys.stdout.flush()
            typing_print(msg, C.LIME)
            speak(msg)
            continue

        # ── SCREEN BRIGHTNESS ──
        _br_match = re.match(r'^brightness\s+(\d{1,3})$', ul)
        if _br_match or ul in ("brightness max", "brightness min", "brightness full",
                                "screen bright karo", "screen dim karo"):
            if _br_match:
                pct = int(_br_match.group(1))
                level = round(pct * 255 / 100)
                label = f"{pct}%"
            elif "max" in ul or "full" in ul or "bright" in ul:
                level = 255; label = "100% (Max)"
            else:
                level = 20; label = "8% (Min)"
            ok = brightness_set(level)
            msg = f"Screen brightness {label} kar di Boss." if ok else "Brightness set nahi hui — termux-api install karo."
            print_friday_prompt(); sys.stdout.flush()
            typing_print(msg, C.GOLD)
            speak(msg)
            continue

        # ── FILE MANAGER ──
        if ul.startswith("file dhundo ") or ul.startswith("file find ") or ul.startswith("dhundo file "):
            fq = ""
            for pfx in ("file dhundo ", "file find ", "dhundo file "):
                if ul.startswith(pfx):
                    fq = user_input[len(pfx):].strip(); break
            if fq:
                print(c(C.DIM, f"\n  🔍 Dhundh raha hoon: \"{fq}\"..."))
                results = spinner_while(file_find, args=(fq,), msg="Files dhundh rahi hoon")
                show_file_results(results, fq)
                msg = f"{len(results)} files mili {fq} se." if results else f"Koi file nahi mili Boss."
                print_friday_prompt(); sys.stdout.flush()
                typing_print(msg, C.ORANGE)
                speak(msg)
            continue

        if ul.startswith("file rename ") or ul.startswith("rename file "):
            parts = user_input.split("→")
            if len(parts) == 2:
                old_q = parts[0].split(None, 2)[-1].strip()
                new_name = parts[1].strip()
                found = file_find(old_q)
                if found:
                    ok = file_rename(found[0], new_name)
                    msg = f"Rename kar diya: {new_name}" if ok else "Rename nahi hua Boss."
                else:
                    msg = f"File nahi mili: {old_q}"
                print_friday_prompt(); sys.stdout.flush()
                typing_print(msg, C.LIME); speak(msg)
            else:
                print(c(C.YELLOW, "\n  Format: file rename [purana naam] → [naya naam]\n"))
            continue

        if ul.startswith("file delete ") or ul.startswith("delete file "):
            fq = user_input.split(None, 2)[-1].strip()
            found = file_find(fq)
            if found:
                ok = file_delete(found[0])
                msg = f"Delete kar diya: {os.path.basename(found[0])}" if ok else "Delete nahi hua."
            else:
                msg = f"File nahi mili: {fq}"
            print_friday_prompt(); sys.stdout.flush()
            typing_print(msg, C.RED); speak(msg)
            continue

        # ── SUMMARIZER ──
        summ_query = None
        summ_style = "short"
        for pfx in ("summarize ", "summary ", "short karo ", "short mein batao ",
                    "tldr ", "summarise "):
            if ul.startswith(pfx):
                summ_query = user_input[len(pfx):].strip()
                if ul.startswith("bullet") or "bullet" in ul:
                    summ_style = "bullet"
                elif "ek line" in ul or "one line" in ul:
                    summ_style = "one"
                break

        if summ_query:
            print()
            print(c(C.PURPLE + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.PURPLE + C.BOLD, "  ║        📝  SUMMARIZER                       ║"))
            print(c(C.PURPLE + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            try:
                result = spinner_while(summarize_text, args=(summ_query, summ_style), msg="Summarize kar rahi hoon")
                print_friday_prompt(); sys.stdout.flush()
                typing_print(result, C.WHITE)
                speak(result[:200])
            except Exception as e:
                print(c(C.RED, f"  ✗ Error: {e}"))
            print()
            continue

        # ── CODE HELPER ──
        code_query = None
        code_lang  = "python"
        for pfx in ("code ", "code likho ", "code banao ", "code help ",
                    "program ", "script "):
            if ul.startswith(pfx):
                code_query = user_input[len(pfx):].strip()
                # Language detect
                for lang in ["python", "javascript", "java", "c++", "kotlin",
                             "bash", "html", "css", "sql", "php"]:
                    if lang in ul:
                        code_lang = lang; break
                break

        if code_query:
            print()
            print(c(C.LIME + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.LIME + C.BOLD, f"  ║  💻  CODE HELPER — {code_lang.upper():<26}║"))
            print(c(C.LIME + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            try:
                result = spinner_while(code_help, args=(code_query, code_lang), msg="Code likh rahi hoon")
                print_friday_prompt(); sys.stdout.flush()
                typing_print(result, C.LIME)
                speak("Code ready hai Boss, terminal mein dekho.")
            except Exception as e:
                print(c(C.RED, f"  ✗ Error: {e}"))
            print()
            continue

        # ── MATH SOLVER ──
        math_query = None
        for pfx in ("math ", "solve ", "solve karo ", "maths ", "equation ",
                    "calculate karo ", "step by step "):
            if ul.startswith(pfx):
                math_query = user_input[len(pfx):].strip(); break

        if math_query:
            print()
            print(c(C.YELLOW + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.YELLOW + C.BOLD, "  ║        🔢  MATH SOLVER                      ║"))
            print(c(C.YELLOW + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            try:
                result = spinner_while(math_solve, args=(math_query,), msg="Solve kar rahi hoon")
                print_friday_prompt(); sys.stdout.flush()
                typing_print(result, C.YELLOW)
                speak("Solution ready hai Boss.")
            except Exception as e:
                print(c(C.RED, f"  ✗ Error: {e}"))
            print()
            continue

        # ── DEBATE MODE ──
        debate_query = None
        debate_side  = "both"
        for pfx in ("debate ", "debate karo ", "argue ", "dono side "):
            if ul.startswith(pfx):
                raw = user_input[len(pfx):].strip()
                if raw.lower().endswith(" for") or raw.lower().startswith("for "):
                    debate_side = "for"; raw = raw.replace(" for","").replace("for ","").strip()
                elif raw.lower().endswith(" against") or "against " in raw.lower():
                    debate_side = "against"; raw = raw.replace(" against","").replace("against ","").strip()
                debate_query = raw; break

        if debate_query:
            print()
            print(c(C.ORANGE + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.ORANGE + C.BOLD, "  ║        ⚔️  DEBATE MODE                       ║"))
            print(c(C.ORANGE + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            print(c(C.DIM, f"  Topic: {debate_query}  |  Side: {debate_side}"))
            print()
            try:
                result = spinner_while(debate_topic, args=(debate_query, debate_side), msg="Arguments soch rahi hoon")
                print_friday_prompt(); sys.stdout.flush()
                typing_print(result, C.ORANGE)
                speak(f"{debate_query} pe debate ready hai Boss.")
            except Exception as e:
                print(c(C.RED, f"  ✗ Error: {e}"))
            print()
            continue

        # ── LEARNING STATS ──
        if ul in ("learning stats", "meri habits", "usage stats", "stats", "kya use karta hoon",
                  "activity", "mere stats", "learning", "usage"):
            learn_show_stats()
            tip = learn_get_suggestion()
            speak(tip[:150])
            continue

        # ── DEEP CONTEXT MEMORY ──
        if ul.startswith("context save ") or ul.startswith("deep save "):
            fact = user_input.split(None, 2)[-1].strip()
            context_add(fact)
            msg = f"Deep memory mein save kar liya Boss: \"{fact}\""
            print_friday_prompt(); sys.stdout.flush()
            typing_print(msg, C.PURPLE); speak(msg)
            continue

        if ul in ("context", "deep memory", "context dekho", "deep context"):
            data = context_load()
            print()
            print(c(C.PURPLE + C.BOLD, "  🧠  Deep Context Memory:"))
            print(c(C.PURPLE, "  " + "─" * 46))
            if data:
                for i, d in enumerate(data, 1):
                    print(c(C.CYAN + C.BOLD, f"  {i:>2}. ") + c(C.WHITE, d["fact"]) + c(C.DIM, f"  [{d['category']}]"))
            else:
                print(c(C.DIM, "  (Abhi koi deep memory nahi hai — 'context save [fact]' se add karo)"))
            print()
            if data:
                speak(f"{len(data)} deep memories hain Boss.")
            else:
                speak("Deep memory khali hai Boss. Context save command se add karo.")
            continue

        # ══════════════════════════════════════════════════════

        # ── JOKE ──
        if ul in ("joke", "ek joke", "joke sunao", "hasao", "koi joke sunao",
                  "funny kuch bolo", "hasa do", "hasao mujhe", "joke bolo", "ek joke sunao"):
            joke = get_joke()
            print()
            print(c(C.GOLD + C.BOLD,  "  ╔══════════════════════════════════════════════╗"))
            print(c(C.GOLD + C.BOLD,  "  ║        😂  FRIDAY KA JOKE                   ║"))
            print(c(C.GOLD + C.BOLD,  "  ╚══════════════════════════════════════════════╝"))
            print()
            for line in joke.split("\n"):
                typing_print(f"  {line}", C.YELLOW)
            print()
            print(c(C.TEAL, "  " + "─" * 46))
            print()
            speak(joke)
            continue

        # ── QUOTE / MOTIVATION ──
        if ul in ("quote", "ek quote", "motivate", "inspire me", "inspire karo",
                  "motivation do", "koi quote sunao", "quote sunao", "motivate karo",
                  "motivation", "inspire", "ek quote sunao", "quote bolo"):
            quote_text, author = get_quote()
            print()
            print(c(C.MAGENTA + C.BOLD, "  ╔══════════════════════════════════════════════╗"))
            print(c(C.MAGENTA + C.BOLD, "  ║        ✨  FRIDAY KA QUOTE                  ║"))
            print(c(C.MAGENTA + C.BOLD, "  ╚══════════════════════════════════════════════╝"))
            print()
            typing_print(f"  \"{quote_text}\"", C.LIME)
            print()
            print(c(C.PINK + C.BOLD, f"                           — {author}"))
            print()
            print(c(C.MAGENTA, "  " + "─" * 46))
            print()
            speak(f"{quote_text}. — {author}")
            continue

        # ── SHOW LONG-TERM MEMORIES ──
        if ul in ("memory", "memories", "yaadein", "yaad", "meri yaadein", "long memory"):
            print()
            if long_mem:
                print(c(C.GOLD + C.BOLD, "  📂 Long-Term Memory:"))
                print(c(C.TEAL, "  " + "─" * 52))
                for i, m in enumerate(long_mem, 1):
                    num  = c(C.YELLOW + C.BOLD, f"  {i:>2}. ")
                    ts   = c(C.DIM + C.WHITE, f"[{m['timestamp']}] ")
                    fact = c(C.LIME, m["content"])
                    print(num + ts + fact)
                print(c(C.TEAL, "  " + "─" * 52))
                print(c(C.DIM, f"  Total: {len(long_mem)}/{LONG_TERM_LIMIT} memories"))
                print(c(C.DIM, "  Delete karne ke liye: forget: 2  ya  forget: pizza"))
            else:
                print(c(C.DIM, "  (Abhi koi long-term memory nahi hai)"))
            print()
            if long_mem:
                speak(f"{len(long_mem)} yadein hain Boss. Dekh lijiye.")
            else:
                speak("Abhi koi long-term memory nahi hai Boss.")
            continue

        # ── SHOW SHORT-TERM MEMORY ──
        if ul in ("chat", "history", "short memory", "short term", "abhi ki baat",
                  "purani baat", "conversation", "recent chat", "short"):
            print()
            stm = short_mem.get()
            if stm:
                print(c(C.MAGENTA + C.BOLD, "  💬 Short-Term Memory (Current Session):"))
                print(c(C.PURPLE, "  " + "─" * 52))
                for i, msg in enumerate(stm, 1):
                    if msg["role"] == "user":
                        role_label = c(C.MAGENTA + C.BOLD, f"  {i:>2}. Miraz  » ")
                        text       = c(C.WHITE, msg["content"][:80] + ("..." if len(msg["content"]) > 80 else ""))
                    else:
                        role_label = c(C.CYAN + C.BOLD,    f"  {i:>2}. Friday » ")
                        text       = c(C.LIME, msg["content"][:80] + ("..." if len(msg["content"]) > 80 else ""))
                    print(role_label + text)
                print(c(C.PURPLE, "  " + "─" * 52))
                print(c(C.DIM, f"  Total: {len(stm)}/{SHORT_TERM_LIMIT} messages  |  Persistent — app band hone par bhi yaad rahega"))
            else:
                print(c(C.DIM, "  (Abhi koi short-term memory nahi hai — abhi baat shuru karo!)"))
            print()
            if stm:
                speak(f"{len(stm)} messages hain recent conversation mein Boss.")
            else:
                speak("Abhi koi short-term memory nahi hai. Baat karo pehle.")
            continue

        # ── DELETE MEMORY ──
        if ul.startswith("forget:") or ul.startswith("delete:") or ul.startswith("bhool ja:"):
            for pfx in ("forget:", "delete:", "bhool ja:"):
                if ul.startswith(pfx):
                    query = user_input[len(pfx):].strip()
                    break

            if not query:
                print(c(C.YELLOW, "\n  Kya delete karoon? Example: forget: 2  ya  forget: pizza\n"))
                continue

            deleted = []

            # Number se delete — "forget: 2" or "forget: 1,3" or "forget: all"
            if query.lower() in ("all", "sab", "sab kuch", "everything"):
                deleted = [m["content"] for m in long_mem]
                long_mem = []
                save_long_term_memory(long_mem)
            else:
                # Check if numbers given (e.g. "2" or "1,3,5")
                parts = [p.strip() for p in query.replace(" ", ",").split(",") if p.strip()]
                indices_to_delete = []
                keyword_mode = False

                for part in parts:
                    if part.isdigit():
                        idx = int(part) - 1  # 1-based to 0-based
                        if 0 <= idx < len(long_mem):
                            indices_to_delete.append(idx)
                        else:
                            print(c(C.RED, f"\n  Number {part} exist nahi karta memory mein.\n"))
                    else:
                        keyword_mode = True
                        break

                if keyword_mode:
                    # Keyword search delete
                    new_mem = []
                    for m in long_mem:
                        if query.lower() in m["content"].lower():
                            deleted.append(m["content"])
                        else:
                            new_mem.append(m)
                    long_mem = new_mem
                    save_long_term_memory(long_mem)
                elif indices_to_delete:
                    # Delete by indices (reverse order to preserve positions)
                    indices_to_delete = sorted(set(indices_to_delete), reverse=True)
                    for idx in indices_to_delete:
                        deleted.append(long_mem[idx]["content"])
                        long_mem.pop(idx)
                    save_long_term_memory(long_mem)

            print()
            if deleted:
                print(c(C.RED + C.BOLD, "  🗑️  Deleted:"))
                for d in deleted:
                    print(c(C.DIM + C.RED, f"    ✗ {d}"))
                remaining = len(long_mem)
                msg = f"Theek hai Boss, {len(deleted)} memory delete kar di. Ab {remaining} yaadein hain. 🗑️"
                print()
                print_friday_prompt()
                sys.stdout.flush()
                typing_print(msg, C.PINK)
                speak(msg)
            else:
                print(c(C.YELLOW, f"  Koi memory nahi mili \"{query}\" se match karti.\n"))
                print(c(C.DIM, "  Tip: 'memory' likhke list dekho phir number se delete karo."))
            print()
            continue

        # ── MANUAL NOTE / REMEMBER ──
        manual = None
        for pfx in ("note:", "remember:", "yaad rakho:", "save:", "note kar:"):
            if ul.startswith(pfx):
                manual = user_input[len(pfx):].strip()
                break

        if manual:
            long_mem = add_to_long_term(long_mem, manual)
            msg = f"Noted Boss! Yaad kar liya: \"{manual}\" 🧠"
            print_friday_prompt()
            sys.stdout.flush()
            typing_print(msg, C.GOLD)
            speak(msg)
            continue

        # ── EMOTION ──
        emotion   = detect_emotion(user_input)
        emo_color = EMOTION_COLOR.get(emotion, C.WHITE)
        emo_emoji = EMOTION_EMOJI.get(emotion, "")

        if emotion != "neutral":
            print(
                c(C.DIM, "  [Emotion: ") +
                c(emo_color + C.BOLD, f"{emotion} {emo_emoji}") +
                c(C.DIM, "]")
            )

        # ── DEDICATED COMMAND GUARD — Groq ke paas mat bhejo ──
        if any(dc in ul for dc in DEDICATED_COMMANDS):
            print(c(C.YELLOW, f"\n  Tip: '{ul}' ke liye dedicated command use karo!"))
            print(c(C.DIM,    "  Example: 'news', 'world news', 'weather kolkata'\n"))
            continue

        # ── GROQ CALL ──
        try:
            reply = spinner_while(
                chat_with_friday,
                args=(short_mem, long_mem, user_input, emotion),
                msg="Friday soch rahi hai"
            )
        except Exception as e:
            print(c(C.RED, f"\n  [Error] {e}\n"))
            continue

        # ── AUTO MEMORY EXTRACT ──
        reply, long_mem = extract_and_save_memory(reply, long_mem)

        # ── 🧠 SMART MEMORY LEARNING — Personal Info Auto Detect ──
        def _smart_memory_learn(text: str, reply_text: str):
            """Conversation se personal info dhundh ke save karo"""
            import re as _re
            tl = text.lower().strip()
            facts_found = []

            # ── NAAM ──
            naam_patterns = [
                r"mera naam (.+?) hai", r"mujhe (.+?) bolte", r"main (.+?) hoon",
                r"naam hai (.+)", r"my name is (.+?)[\.\s]"
            ]
            for pat in naam_patterns:
                m = _re.search(pat, tl)
                if m:
                    naam = m.group(1).strip().title()
                    if len(naam) > 1 and len(naam) < 30:
                        facts_found.append(f"Boss ka naam {naam} hai")
                    break

            # ── AGE ──
            age_patterns = [
                r"main (\d+) saal", r"meri umar (\d+)", r"(\d+) saal ka hoon",
                r"(\d+) years old", r"age (\d+)", r"umar (\d+)"
            ]
            for pat in age_patterns:
                m = _re.search(pat, tl)
                if m:
                    age = m.group(1)
                    if 5 <= int(age) <= 100:
                        facts_found.append(f"Boss ki umar {age} saal hai")
                    break

            # ── CITY / LOCATION ──
            city_patterns = [
                r"main (.+?) mein rehta", r"meri city (.+?) hai",
                r"(.+?) se hoon", r"(.+?) mein hoon", r"rehta hoon (.+?) mein"
            ]
            for pat in city_patterns:
                m = _re.search(pat, tl)
                if m:
                    city = m.group(1).strip().title()
                    if 2 < len(city) < 40:
                        facts_found.append(f"Boss {city} mein rehta hai")
                    break

            # ── FAMILY ──
            family_map = {
                "papa": "papa", "father": "papa", "baap": "papa",
                "maa": "maa", "mama": "maa", "mother": "maa",
                "bhai": "bhai", "brother": "bhai",
                "behen": "behen", "sister": "behen",
                "dadi": "dadi", "nani": "nani",
                "dada": "dada", "nana": "nana"
            }
            for fkey, flabel in family_map.items():
                if fkey in tl and len(text) > 20:
                    # Extract context around family mention
                    idx = tl.find(fkey)
                    snippet = text[max(0,idx-10):idx+50].strip()
                    if snippet and len(snippet) > 10:
                        facts_found.append(f"Boss ke {flabel} ke baare mein: {snippet[:60]}")
                    break

            # ── RELATIONSHIP ──
            rel_words = ["girlfriend", "gf", "boyfriend", "bf", "wife", "husband",
                        "biwi", "chokri", "ladki", "dost", "yaar"]
            for rw in rel_words:
                if rw in tl and len(text) > 15:
                    facts_found.append(f"Boss ne {rw} ke baare mein bataya: {text[:70].strip()}")
                    break

            # ── EDUCATION ──
            edu_words = ["school", "college", "class", "grade", "university",
                        "padh raha", "exam", "result"]
            for ew in edu_words:
                if ew in tl and len(text) > 20:
                    facts_found.append(f"Boss ki education: {text[:70].strip()}")
                    break

            # Save all found facts
            for fact in facts_found:
                # Check duplicate nahi hai
                existing = [m["content"].lower() for m in long_mem]
                if not any(fact.lower()[:30] in ex for ex in existing):
                    add_to_long_term(long_mem, fact)
                    print(c(C.GOLD, "  🧠 Memory learned: ") + c(C.LIME, chr(34)+fact+chr(34)))

        # Run smart learning
        if len(user_input) > 10:
            _smart_memory_learn(user_input, reply)

        # ── PROACTIVE SUGGESTION (10% chance, sirf kabhi kabhi) ──
        import random as _rnd
        if _rnd.random() < 0.08:
            tip = learn_get_suggestion()
            if "sabse zyada" in tip.lower():
                print(c(C.DIM + C.ITALIC, f"\n  💡 Friday tip: {tip}"))

        # ── PRINT REPLY ──
        print_friday_prompt()
        sys.stdout.flush()
        typing_print(reply, C.DEEPBLUE)

        # ── UPDATE SHORT-TERM MEMORY ──
        short_mem.add("user", user_input)
        short_mem.add("assistant", reply)

        stc = short_mem.count()
        if stc >= SHORT_TERM_LIMIT:
            pass  # Short-term memory silently manages itself

        # ── VOICE ──
        speak(reply)


if __name__ == "__main__":
    main()
