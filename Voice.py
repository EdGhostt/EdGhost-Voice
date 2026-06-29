import requests
import time
import os
import sys
import threading
import json
from colorama import Fore, init

try:
    import websocket
except ImportError:
    os.system('pip install websocket-client')
    import websocket

init(autoreset=True)

lock = threading.Lock()
active_accounts = 0
valid_tokens = []

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

# Token doğrulama fonksiyonu
def check_token(token, index):
    headers = {"Authorization": token, "Content-Type": "application/json"}
    # Discord'un kullanıcı ayarları sayfasına istek atarak tokenı test ediyoruz
    res = requests.get("https://discord.com/api/v9/users/@me", headers=headers)
    
    if res.status_code == 200:
        username = res.json().get("username", "Bilinmeyen")
        print(Fore.GREEN + f"[✓] {index}. Token Geçerli! ({username})")
        return True
    else:
        print(Fore.RED + f"[X] {index}. Token GEÇERSİZ / PATLAMIŞ!")
        return False

def draw_voice_dashboard(total_tokens, target_info, mode):
    sys.stdout.write("\033[H")
    mode_text = "Grup (DM)" if mode == "2" else "Sunucu (Guild)"
    panel = f"""
{Fore.CYAN}======================================================
{Fore.MAGENTA}       --- EdGhost Discord Voice Joiner V3 ---
{Fore.CYAN}======================================================
{Fore.YELLOW}  [🕹️] Çalışma Modu       : {Fore.WHITE}{mode_text}
{Fore.YELLOW}  [🔊] Hedef ID           : {Fore.WHITE}{target_info}
{Fore.YELLOW}  [👤] Sesteki Aktif Hesap: {Fore.GREEN}{active_accounts} / {total_tokens}
{Fore.YELLOW}  [🎙️] Konuşma Durumu     : {Fore.GREEN}MİKROFONLAR AKTİF (YEŞİL)
{Fore.CYAN}======================================================
{Fore.GREEN}  Durum: Doğrulanmış hesaplar seste canlı simülasyonda.
{Fore.CYAN}======================================================
"""
    sys.stdout.write(panel)
    sys.stdout.flush()

def connect_to_voice(token, guild_id, channel_id, total_tokens, target_info, mode):
    global active_accounts
    ws_url = "wss://gateway.discord.gg/?v=9&encoding=json"
    ws = websocket.WebSocket()
    
    try:
        ws.connect(ws_url)
        
        # 1. Adım: Kimlik Doğrulama
        identify_payload = {
            "op": 2,
            "d": {
                "token": token,
                "properties": {"$os": "linux", "$browser": "Discord Client", "$device": "desktop"},
                "presence": {
                    "status": "online",
                    "since": 0,
                    "activities": [{"name": "EdGhost V3 Controller", "type": 0}],
                    "afk": False
                }
            }
        }
        ws.send(json.dumps(identify_payload))
        
        # 2. Adım: Ses Kanalına Giriş Sinyali (Mod Seçimine Göre)
        # Eğer grup ise guild_id "null" (None) olmalıdır
        voice_payload = {
            "op": 4,
            "d": {
                "guild_id": guild_id,
                "channel_id": channel_id,
                "self_mute": False,
                "self_deaf": False,
                "self_video": True
            }
        }
        time.sleep(1)
        ws.send(json.dumps(voice_payload))
        
        with lock:
            active_accounts += 1
            draw_voice_dashboard(total_tokens, target_info, mode)
            
        # 3. Adım: Sürekli Canlı Tutma ve Yeşil Işık
        while True:
            try:
                ws.settimeout(10)
                ws.recv()
            except websocket.WebSocketTimeoutException:
                pass
                
            speaking_payload = {
                "op": 5,
                "d": {"speaking": 1, "delay": 0, "ssrc": 1}
            }
            ws.send(json.dumps(speaking_payload))
            time.sleep(4)
                
    except Exception:
        with lock:
            if active_accounts > 0:
                active_accounts -= 1
            draw_voice_dashboard(total_tokens, target_info, mode)

def main():
    global valid_tokens
    clear_screen()
    print(Fore.GREEN + "--- EdGhost Akıllı Ses Denetleyici V3 ---")
    
    try:
        token_sayisi = int(input(Fore.YELLOW + "Kaç adet token girilecek?: "))
    except ValueError:
        print(Fore.RED + "Geçerli bir sayı girin!")
        return

    raw_tokens = []
    for i in range(1, token_sayisi + 1):
        t = input(Fore.WHITE + f"{i}. Token: ")
        raw_tokens.append(t)

    # --- TOKEN CHECKER BÖLÜMÜ ---
    print(Fore.YELLOW + "\n[+] Tokenlar kontrol ediliyor, lütfen bekleyin...")
    time.sleep(1)
    
    valid_tokens = []
    for idx, t in enumerate(raw_tokens, 1):
        if check_token(t, idx):
            valid_tokens.append(t)
            
    if not valid_tokens:
        print(Fore.RED + "\n[X] Çalışan hiçbir token bulunamadı! Program kapatılıyor.")
        return
        
    print(Fore.GREEN + f"\n[✓] Kontrol Tamamlandı! {len(valid_tokens)} adet çalışan token sisteme yüklendi.")
    time.sleep(2)

    # --- MOD SEÇİM BÖLÜMÜ ---
    print(Fore.CYAN + "\n=============================================")
    print(Fore.YELLOW + " Hesapların nerede durmasını istiyorsunuz?")
    print(Fore.WHITE + " [1] Sunucu (Guild) Ses Kanalı")
    print(Fore.WHITE + " [2] Grup (DM Grubu) Ses Kanalı")
    print(Fore.CYAN + "=============================================")
    mode = input(Fore.GREEN + "Seçiminiz (1 veya 2): ")

    guild_id = None
    channel_id = None
    target_info = ""

    if mode == "1":
        guild_id = input(Fore.CYAN + "Sunucu (Guild) ID: ")
        channel_id = input(Fore.CYAN + "Ses Kanal ID: ")
        target_info = channel_id
    elif mode == "2":
        # Gruplarda Sunucu ID olmadığı için guild_id boş kalır, direkt Grup ID yazılır
        channel_id = input(Fore.CYAN + "Grup (DM) ID: ")
        target_info = channel_id
    else:
        print(Fore.RED + "Geçersiz seçim! Varsayılan olarak Sunucu modu seçildi.")
        guild_id = input(Fore.CYAN + "Sunucu (Guild) ID: ")
        channel_id = input(Fore.CYAN + "Ses Kanal ID: ")
        target_info = channel_id
        mode = "1"

    clear_screen()
    print(Fore.YELLOW + "Doğrulanmış hesaplar sese aktarılıyor...")
    time.sleep(1)
    clear_screen()

    # Sadece sağlam olan tokenları işleme alıyoruz
    for t in valid_tokens:
        th = threading.Thread(target=connect_to_voice, args=(t, guild_id, channel_id, len(valid_tokens), target_info, mode))
        th.daemon = True
        th.start()
        time.sleep(0.4)

    while True:
        with lock:
            draw_voice_dashboard(len(valid_tokens), target_info, mode)
        time.sleep(2)

if __name__ == "__main__":
    main()
    sys.stdout.write(panel)
    sys.stdout.flush()

def connect_to_voice(token, guild_id, channel_id, total_tokens):
    global active_accounts
    
    # Discord Gateway URL
    ws_url = "wss://gateway.discord.gg/?v=9&encoding=json"
    ws = websocket.WebSocket()
    
    try:
        ws.connect(ws_url)
        
        # 1. Adım: Discord'a kimlik doğrulaması (Identify) gönderiyoruz
        identify_payload = {
            "op": 2,
            "d": {
                "token": token,
                "properties": {
                    "$os": "linux",
                    "$browser": "Discord Client",
                    "$device": "desktop"
                },
                "presence": {
                    "status": "online",
                    "since": 0,
                    "activities": [],
                    "afk": False
                }
            }
        }
        ws.send(json.dumps(identify_payload))
        
        # 2. Adım: Ses kanalına bağlanma sinyali gönderiyoruz
        # self_mute: False (Mikrofon açık dursun) | self_deaf: False (Kulaklık açık dursun)
        voice_payload = {
            "op": 4,
            "d": {
                "guild_id": guild_id,
                "channel_id": channel_id,
                "self_mute": False,
                "self_deaf": False,
                "self_video": False
            }
        }
        time.sleep(1) # Bağlantının oturması için küçük bir bekleme
        ws.send(json.dumps(voice_payload))
        
        with lock:
            active_accounts += 1
            draw_voice_dashboard(total_tokens, channel_id)
            
        # Bağlantıyı koparmamak için arkada sonsuz döngüde tutuyoruz (Heartbeat mantığı)
        while True:
            # Discord'dan gelen verileri oku ki bağlantı düşmesin
            result = ws.recv()
            if not result:
                break
                
    except Exception:
        with lock:
            if active_accounts > 0:
                active_accounts -= 1
            draw_voice_dashboard(total_tokens, channel_id)

def main():
    clear_screen()
    print(Fore.GREEN + "--- EdGhost Ses Kanalına Çökme Toolu ---")
    
    try:
        token_sayisi = int(input(Fore.YELLOW + "Kaç adet token ses kanalına sokulacak?: "))
    except ValueError:
        print(Fore.RED + "Lütfen geçerli bir sayı girin!")
        return

    tokens = []
    for i in range(1, token_sayisi + 1):
        token = input(Fore.WHITE + f"{i}. Hesabın Tokenını girin: ")
        tokens.append(token)

    guild_id = input(Fore.CYAN + "Sunucu (Guild) ID girin: ")
    channel_id = input(Fore.CYAN + "Ses Kanalı (Voice Channel) ID girin: ")

    clear_screen()
    print(Fore.YELLOW + "Hesaplar ses kanalına sızıyor...")
    time.sleep(2)
    clear_screen()

    # Her hesabı ayrı bir kolda (Thread) sese bağlıyoruz
    for t in tokens:
        th = threading.Thread(target=connect_to_voice, args=(t, guild_id, channel_id, len(tokens)))
        th.daemon = True
        th.start()
        time.sleep(0.5) # Discord'un spam olarak algılamaması için yarım saniye arayla sokuyoruz

    # Paneli canlı tutan ana döngü
    while True:
        with lock:
            draw_voice_dashboard(len(tokens), channel_id)
        time.sleep(2)

if __name__ == "__main__":
    main()
