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

# Girişte tokenları kontrol eden güvenli fonksiyon
def check_token(token, index):
    headers = {"Authorization": token, "Content-Type": "application/json"}
    try:
        res = requests.get("https://discord.com/api/v9/users/@me", headers=headers, timeout=5)
        if res.status_code == 200:
            username = res.json().get("username", "Bilinmeyen")
            print(Fore.GREEN + f"[✓] {index}. Token Geçerli! ({username})")
            return True
    except:
        pass
    print(Fore.RED + f"[X] {index}. Token GEÇERSİZ veya PATLAMIŞ!")
    return False

def draw_voice_dashboard(total_tokens, channel_id, mode):
    sys.stdout.write("\033[H")
    mode_text = "Grup (DM)" if mode == "2" else "Sunucu (Guild)"
    panel = f"""
{Fore.CYAN}======================================================
{Fore.MAGENTA}       --- EdGhost Discord Voice Joiner V3 ---
{Fore.CYAN}======================================================
{Fore.YELLOW}  [🕹️] Çalışma Modu     : {Fore.WHITE}{mode_text}
{Fore.YELLOW}  [🔊] Hedef Kanal ID   : {Fore.WHITE}{channel_id}
{Fore.YELLOW}  [👤] Sesteki Toplam   : {Fore.GREEN}{active_accounts} / {total_tokens} Hesap Odada
{Fore.CYAN}======================================================
{Fore.GREEN}  Anlık Durum: Doğrulanmış hesaplar seste, kopma yok!
{Fore.CYAN}======================================================
"""
    sys.stdout.write(panel)
    sys.stdout.flush()

def connect_to_voice(token, guild_id, channel_id, total_tokens, mode):
    global active_accounts
    ws_url = "wss://gateway.discord.gg/?v=9&encoding=json"
    ws = websocket.WebSocket()
    
    try:
        ws.connect(ws_url)
        
        # 1. Adım: Kimlik Doğrulama (Identify)
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
        
        # 2. Adım: Ses Kanalına Bağlanma Sinyali
        voice_payload = {
            "op": 4,
            "d": {
                "guild_id": guild_id,  # Grup modunda burası None gidecek
                "channel_id": channel_id,
                "self_mute": False,
                "self_deaf": False,
                "self_video": False
            }
        }
        time.sleep(1) 
        ws.send(json.dumps(voice_payload))
        
        with lock:
            active_accounts += 1
            draw_voice_dashboard(total_tokens, channel_id, mode)
            
        # O çalışan ilk kodundaki orijinal döngü (Bağlantıyı açık tutar)
        while True:
            result = ws.recv()
            if not result:
                break
                
    except Exception:
        with lock:
            if active_accounts > 0:
                active_accounts -= 1
            draw_voice_dashboard(total_tokens, channel_id, mode)

def main():
    global valid_tokens
    clear_screen()
    print(Fore.GREEN + "--- EdGhost Ses Kanalına Çökme Toolu V3 ---")
    
    try:
        token_sayisi = int(input(Fore.YELLOW + "Kaç adet token girilecek?: "))
    except ValueError:
        print(Fore.RED + "Lütfen geçerli bir sayı girin!")
        return

    raw_tokens = []
    for i in range(1, token_sayisi + 1):
        token = input(Fore.WHITE + f"{i}. Hesabın Tokenını girin: ")
        raw_tokens.append(token)

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
        
    print(Fore.GREEN + f"\n[✓] Kontrol Tamamlandı! {len(valid_tokens)} adet sağlam token yüklendi.")
    time.sleep(2)

    # --- GRUP / SUNUCU SEÇİM BÖLÜMÜ ---
    clear_screen()
    print(Fore.CYAN + "=============================================")
    print(Fore.YELLOW + " Hesaplar nereye bağlanacak?")
    print(Fore.WHITE + " [1] Sunucu (Guild) Ses Kanalı")
    print(Fore.WHITE + " [2] Grup (DM Grubu) Ses Kanalı")
    print(Fore.CYAN + "=============================================")
    mode = input(Fore.GREEN + "Seçiminiz (1 veya 2): ")

    guild_id = None
    channel_id = None

    if mode == "1":
        guild_id = input(Fore.CYAN + "Sunucu (Guild) ID girin: ")
        channel_id = input(Fore.CYAN + "Ses Kanalı (Voice Channel) ID girin: ")
    elif mode == "2":
        # Gruplarda Sunucu ID olmadığı için None kalıyor, direkt Grup ID'sini kanal olarak alıyoruz
        channel_id = input(Fore.CYAN + "Grup (DM) ID girin: ")
    else:
        print(Fore.RED + "Geçersiz seçim! Varsayılan olarak Sunucu modu seçildi.")
        guild_id = input(Fore.CYAN + "Sunucu (Guild) ID girin: ")
        channel_id = input(Fore.CYAN + "Ses Kanalı ID girin: ")
        mode = "1"

    clear_screen()
    print(Fore.YELLOW + "Hesaplar ses kanalına sızıyor...")
    time.sleep(1)
    clear_screen()

    # Sadece çalışan sağlam tokenları sese sokuyoruz
    for t in valid_tokens:
        th = threading.Thread(target=connect_to_voice, args=(t, guild_id, channel_id, len(valid_tokens), mode))
        th.daemon = True
        th.start()
        time.sleep(0.5)

    while True:
        with lock:
            draw_voice_dashboard(len(valid_tokens), channel_id, mode)
        time.sleep(2)

if __name__ == "__main__":
    main()
def draw_voice_dashboard(total_tokens, target_info, mode):
    sys.stdout.write("\033[H")
    mode_text = "Grup (DM)" if mode == "2" else "Sunucu (Guild)"
    panel = f"""
{Fore.CYAN}======================================================
{Fore.MAGENTA}       --- EdGhost Discord Voice Joiner V3.2 ---
{Fore.CYAN}======================================================
{Fore.YELLOW}  [🕹️] Çalışma Modu       : {Fore.WHITE}{mode_text}
{Fore.YELLOW}  [🔊] Hedef ID           : {Fore.WHITE}{target_info}
{Fore.YELLOW}  [👤] Sesteki Aktif Hesap: {Fore.GREEN}{active_accounts} / {total_tokens}
{Fore.YELLOW}  [🛡️] Koruma Sistemi     : {Fore.GREEN}OTOMATİK RE-CONNECT AKTİF
{Fore.CYAN}======================================================
{Fore.GREEN}  Durum: Bağlantı kilitlendi. Düşen hesap anında geri girer.
{Fore.CYAN}======================================================
"""
    sys.stdout.write(panel)
    sys.stdout.flush()

def send_heartbeat(ws, interval):
    while True:
        time.sleep(interval / 1000)
        try:
            ws.send(json.dumps({"op": 1, "d": None}))
        except:
            break

def connect_to_voice(token, guild_id, channel_id, total_tokens, target_info, mode):
    global active_accounts
    
    # Döngüye alıyoruz ki sesten atsa bile salisede geri girsin
    while True:
        ws_url = "wss://gateway.discord.gg/?v=9&encoding=json"
        ws = websocket.WebSocket()
        try:
            ws.connect(ws_url)
            init_msg = json.loads(ws.recv())
            heartbeat_interval = init_msg['d']['heartbeat_interval']
            
            threading.Thread(target=send_heartbeat, args=(ws, heartbeat_interval), daemon=True).start()
            
            # Kimlik Doğrulama
            identify_payload = {
                "op": 2,
                "d": {
                    "token": token,
                    "properties": {"$os": "windows", "$browser": "Discord Client", "$device": "desktop"},
                    "presence": {"status": "online", "since": 0, "activities": [{"name": "EdGhost V3.2", "type": 0}], "afk": False}
                }
            }
            ws.send(json.dumps(identify_payload))
            time.sleep(1)
            
            # Sese Giriş Sinyali
            voice_payload = {
                "op": 4,
                "d": {
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "self_mute": False,
                    "self_deaf": False,
                    "self_video": False # Bazı hesaplarda video zorlayınca DC atıyor, stabilite için kapattım kanka
                }
            }
            ws.send(json.dumps(voice_payload))
            
            with lock:
                active_accounts += 1
                draw_voice_dashboard(total_tokens, target_info, mode)
                
            # Canlı Tutma ve Yeşil Işık Dinlemesi
            while True:
                speaking_payload = {
                    "op": 5,
                    "d": {"speaking": 1, "delay": 0, "ssrc": 1}
                }
                ws.send(json.dumps(speaking_payload))
                
                ws.settimeout(5)
                msg = ws.recv()
                if not msg:
                    break
                time.sleep(3)
                
        except Exception:
            pass
        finally:
            with lock:
                if active_accounts > 0:
                    active_accounts -= 1
                draw_voice_dashboard(total_tokens, target_info, mode)
            time.sleep(1) # IP ban yememek için düşerse 1 saniye bekleyip geri dalar

def main():
    global valid_tokens
    clear_screen()
    print(Fore.GREEN + "--- EdGhost Akıllı Ses Denetleyici V3.2 ---")
    
    try:
        token_sayisi = int(input(Fore.YELLOW + "Kaç adet token girilecek?: "))
    except ValueError:
        print(Fore.RED + "Geçerli bir sayı girin!")
        return

    raw_tokens = []
    for i in range(1, token_sayisi + 1):
        t = input(Fore.WHITE + f"{i}. Token: ")
        raw_tokens.append(t)

    print(Fore.YELLOW + "\n[+] Tokenlar kontrol ediliyor...")
    valid_tokens = []
    for idx, t in enumerate(raw_tokens, 1):
        if check_token(t, idx):
            valid_tokens.append(t)
            
    if not valid_tokens:
        print(Fore.RED + "\n[X] Çalışan token bulunamadı!")
        return
        
    print(Fore.CYAN + "\n=============================================")
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
    else:
        channel_id = input(Fore.CYAN + "Grup (DM) ID: ")
        target_info = channel_id

    clear_screen()
    print(Fore.YELLOW + "Hesaplar sese kilitleniyor...")
    time.sleep(1)
    clear_screen()

    for t in valid_tokens:
        th = threading.Thread(target=connect_to_voice, args=(t, guild_id, channel_id, len(valid_tokens), target_info, mode))
        th.daemon = True
        th.start()
        time.sleep(0.5)

    while True:
        with lock:
            draw_voice_dashboard(len(valid_tokens), target_info, mode)
        time.sleep(2)

if __name__ == "__main__":
    main()
    mode_text = "Grup (DM)" if mode == "2" else "Sunucu (Guild)"
    panel = f"""
{Fore.CYAN}======================================================
{Fore.MAGENTA}       --- EdGhost Discord Voice Joiner V3.1 ---
{Fore.CYAN}======================================================
{Fore.YELLOW}  [🕹️] Çalışma Modu       : {Fore.WHITE}{mode_text}
{Fore.YELLOW}  [🔊] Hedef ID           : {Fore.WHITE}{target_info}
{Fore.YELLOW}  [👤] Sesteki Aktif Hesap: {Fore.GREEN}{active_accounts} / {total_tokens}
{Fore.YELLOW}  [🎙️] Bağlantı Durumu    : {Fore.GREEN}KOPMA KORUMASI AKTİF (7/24)
{Fore.CYAN}======================================================
{Fore.GREEN}  Durum: Hesaplar seste çakılı bekliyor, düşme engellendi.
{Fore.CYAN}======================================================
"""
    sys.stdout.write(panel)
    sys.stdout.flush()

# Bağlantının kopmasını engelleyen kalp atışı fonksiyonu
def send_heartbeat(ws, interval):
    while True:
        time.sleep(interval / 1000)
        try:
            ws.send(json.dumps({"op": 1, "d": None})) # Discord'a 'buradayım' sinyali
        except Exception:
            break

def connect_to_voice(token, guild_id, channel_id, total_tokens, target_info, mode):
    global active_accounts
    ws_url = "wss://gateway.discord.gg/?v=9&encoding=json"
    ws = websocket.WebSocket()
    
    try:
        ws.connect(ws_url)
        
        # İlk gelen veriden Heartbeat aralığını alıyoruz
        init_msg = json.loads(ws.recv())
        heartbeat_interval = init_msg['d']['heartbeat_interval']
        
        # Kalp atışı döngüsünü arka planda başlatıyoruz (Düşmeyi engeller)
        threading.Thread(target=send_heartbeat, args=(ws, heartbeat_interval), daemon=True).start()
        
        # 1. Adım: Kimlik Doğrulama
        identify_payload = {
            "op": 2,
            "d": {
                "token": token,
                "properties": {"$os": "linux", "$browser": "Discord Client", "$device": "desktop"},
                "presence": {"status": "online", "since": 0, "activities": [{"name": "EdGhost V3.1", "type": 0}], "afk": False}
            }
        }
        ws.send(json.dumps(identify_payload))
        
        # 2. Adım: Sese Giriş
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
            
        # 3. Adım: Yeşil Işık ve Dinleme Döngüsü
        while True:
            try:
                # Sürekli yeşil ışık yakma sinyali gönderiyoruz
                speaking_payload = {
                    "op": 5,
                    "d": {"speaking": 1, "delay": 0, "ssrc": 1}
                }
                ws.send(json.dumps(speaking_payload))
                
                # Discord'dan gelen yanıtları oku ki bağlantı canlı kalsın
                ws.settimeout(5)
                ws.recv()
            except Exception:
                time.sleep(2)
                
    except Exception:
        with lock:
            if active_accounts > 0:
                active_accounts -= 1
            draw_voice_dashboard(total_tokens, target_info, mode)

def main():
    global valid_tokens
    clear_screen()
    print(Fore.GREEN + "--- EdGhost Akıllı Ses Denetleyici V3.1 ---")
    
    try:
        token_sayisi = int(input(Fore.YELLOW + "Kaç adet token girilecek?: "))
    except ValueError:
        print(Fore.RED + "Geçerli bir sayı girin!")
        return

    raw_tokens = []
    for i in range(1, token_sayisi + 1):
        t = input(Fore.WHITE + f"{i}. Token: ")
        raw_tokens.append(t)

    print(Fore.YELLOW + "\n[+] Tokenlar kontrol ediliyor...")
    valid_tokens = []
    for idx, t in enumerate(raw_tokens, 1):
        if check_token(t, idx):
            valid_tokens.append(t)
            
    if not valid_tokens:
        print(Fore.RED + "\n[X] Çalışan token bulunamadı!")
        return
        
    print(Fore.CYAN + "\n=============================================")
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
    else:
        channel_id = input(Fore.CYAN + "Grup (DM) ID: ")
        target_info = channel_id

    clear_screen()
    print(Fore.YELLOW + "Hesaplar sese çakılıyor...")
    time.sleep(1)
    clear_screen()

    for t in valid_tokens:
        th = threading.Thread(target=connect_to_voice, args=(t, guild_id, channel_id, len(valid_tokens), target_info, mode))
        th.daemon = True
        th.start()
        time.sleep(0.5)

    while True:
        with lock:
            draw_voice_dashboard(len(valid_tokens), target_info, mode)
        time.sleep(2)

if __name__ == "__main__":
    main()
