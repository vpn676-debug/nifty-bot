import yfinance as yf, time, datetime, os, requests, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_CHAT_ID")
last_signal = ""
pcr_history = []

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

def get_pcr():
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        r = s.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        d = r.json()
        ce = d['filtered']['CE']['totOI']; pe = d['filtered']['PE']['totOI']
        return pe/ce if ce!=0 else 1.0
    except: return 1.0

def get_nifty():
    try:
        df = yf.Ticker("^NSEI").history(period="1d", interval="5m")
        c = float(df['Close'].iloc[-1])
        b = float(df['Close'].ewm(span=20, adjust=False).mean().iloc[-1])
        return c, b
    except: return None, None

def wait_exact():
    now = datetime.datetime.now()
    nxt = ((now.minute // 5) + 1) * 5
    if nxt >= 60:
        nxt_t = now.replace(minute=0, second=5, microsecond=0) + datetime.timedelta(hours=1)
    else:
        nxt_t = now.replace(minute=nxt, second=5, microsecond=0)
    sec = (nxt_t - now).total_seconds()
    if sec < 0: sec += 300
    print(f"Next check {nxt_t.strftime('%H:%M:%S')}")
    time.sleep(sec)

def run_server():
    PORT = int(os.environ.get("PORT", 10000))
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"Bot Running")
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()

threading.Thread(target=run_server, daemon=True).start()
print("Bot Started")
send_telegram("✅ Blue+PCR Bot Connected\nGREEN SELL PCR>=1.3 | RED BUY PCR<=0.8")

while True:
    close, blue = get_nifty()
    raw_pcr = get_pcr()
    pcr_history.append(raw_pcr)
    if len(pcr_history) > 20: pcr_history.pop(0)
    pcr = sum(pcr_history)/len(pcr_history)
    if close is None: time.sleep(30); continue
    print(f"{datetime.datetime.now().strftime('%H:%M:%S')} Close:{close:.2f} Blue:{blue:.2f} PCR:{pcr:.2f}")
    if close < blue and pcr >= 1.3:
        if last_signal != "SELL":
            send_telegram(f"🔴 SELL GREEN -> PE BUY\nPrice:{close:.2f} Blue:{blue:.2f} PCR:{pcr:.2f}")
            last_signal="SELL"
    elif close > blue and pcr <= 0.8:
        if last_signal != "BUY":
            send_telegram(f"🟢 BUY RED -> CE BUY\nPrice:{close:.2f} Blue:{blue:.2f} PCR:{pcr:.2f}")
            last_signal="BUY"
    else: print("WAIT")
    wait_exact()
