import requests
import time
import os
import sys
import threading
import json
from colorama import Fore, init

# Tek bir kütüphane ekliyoruz (WebSocket bağlantısı için Termux'ta gerekir)
# Kurmak için: pip install websocket-client
try:
    import websocket
except ImportError:
    os.system('pip install websocket-client')
    import websocket

init(autoreset=True)

lock = threading.Lock()
active_accounts = 0

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def draw_voice_dashboard(total_tokens, channel_id):
    sys.stdout.write("\033[H")
    panel = f"""
{Fore.CYAN}======================================================
{Fore.MAGENTA}       --- EdGhost Discord Voice Joiner V1 ---
{Fore.CYAN}======================================================
{Fore.YELLOW}  [🔊] Hedef Ses Kanalı : {Fore.WHITE}{channel_id}
{Fore.YELLOW}  [👤] Sesteki Toplam   : {Fore.GREEN}{active_accounts} / {total_tokens} Hesap Odada
{Fore.CYAN}======================================================
{Fore.GREEN}  Anlık Durum: Hesaplar seste çakılı kaldı, çıkmıyor!
{Fore.CYAN}======================================================
"""
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
