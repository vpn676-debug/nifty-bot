import yfinance as yf, time, datetime, os, requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_CHAT_ID")
last_signal = ""
pcr_history = []

# --- FIX FOR RENDER: Dummy server ---
def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is Running")
        def log_message(self, *args): return
    print(f"Starting dummy server on {port}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print(f"Sent: {msg}")
    except: pass

def get_pcr():
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        r = s.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        ce_oi = sum([x['CE']['openInterest'] for x in data['records']['data'] if 'CE' in x and 'openInterest' in x['CE']][:20])
        pe_oi = sum([x['PE']['openInterest'] for x in data['records']['data'] if 'PE' in x and 'openInterest' in x['PE']][:20])
        if ce_oi > 0:
            return pe_oi / ce_oi
    except Exception as e:
        print(f"PCR Error: {e}")
    return 1.0

def get_blue():
    try:
        hist = yf.Ticker("^NSEI").history(period="1d", interval="5m")
        if len(hist) > 20:
            return hist['Close'].ewm(span=20).mean().iloc[-1], hist['Close'].iloc[-1]
    except: pass
    return None, None

# --- START ---
send_telegram(f"✅ Blue+PCR Bot Connected\nGREEN SELL PCR>=1.3 | RED BUY PCR<=0.8\nTime: {datetime.datetime.now().strftime('%H:%M:%S')}")

while True:
    now = datetime.datetime.now()
    if now.minute % 5 == 0 and now.second >= 5 and now.second <= 15:
        blue, close = get_blue()
        pcr = get_pcr()
        if blue and close:
            print(f"{now} Close:{close:.2f} Blue:{blue:.2f} PCR:{pcr:.2f}")
            if close < blue and pcr >= 1.3 and last_signal != f"SELL_{now.minute}":
                send_telegram(f"🔴 GREEN CANDLE SELL\nNIFTY {close:.2f} < Blue {blue:.2f}\nPCR {pcr:.2f} (>=1.3)\nPE BUY ✅\n{now.strftime('%H:%M:%S')}")
                last_signal = f"SELL_{now.minute}"
            elif close > blue and pcr <= 0.8 and last_signal != f"BUY_{now.minute}":
                send_telegram(f"🟢 RED CANDLE BUY\nNIFTY {close:.2f} > Blue {blue:.2f}\nPCR {pcr:.2f} (<=0.8)\nCE BUY ✅\n{now.strftime('%H:%M:%S')}")
                last_signal = f"BUY_{now.minute}"
        time.sleep(65)
    time.sleep(1)
