import socket
import threading
import json
from datetime import datetime
import time

# Sunucu temel ayarları
HOST = '127.0.0.1'
PORT = 5555
LOG_FILE = "chat_log.txt"

# Sunucu için global değişkenler
clients = {}  # Bağlı istemciler: {socket: takma_ad}
persistent_users = set()  # Kalıcı kullanıcı listesi
message_times = {}  # Mesaj zaman damgaları: {socket: [zamanlar]}

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"Sunucu {HOST}:{PORT} adresinde çalışıyor")
    except Exception as e:
        print(f"Sunucu {HOST}:{PORT} adresinde başlatılamadı. Hata: {str(e)}")
        return

    # Tüm istemcilere mesaj yayınlama fonksiyonu
    def broadcast(message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        disconnected_clients = []
        for client in clients:
            try:
                client.send(full_message.encode('utf-8'))
            except:
                disconnected_clients.append(client)
        for client in disconnected_clients:
            nickname = clients.get(client, "Bilinmeyen")
            clients.pop(client, None)
            message_times.pop(client, None)
            persistent_users.discard(nickname)
            print(f"Bağlantısı kopan istemci kaldırıldı: {nickname}")
        with open(LOG_FILE, "a", encoding='utf-8') as log_file:
            log_file.write(f"{full_message}\n")

    # Bağlı kullanıcı listesini istemcilere gönderir
    def send_user_list():
        user_list = json.dumps(list(clients.values()))
        print(f"Kullanıcı listesi gönderiliyor: {user_list}")
        disconnected_clients = []
        for client in clients:
            try:
                client.send(f"USERLIST {user_list}".encode('utf-8'))
            except:
                disconnected_clients.append(client)
        for client in disconnected_clients:
            nickname = clients.get(client, "Bilinmeyen")
            clients.pop(client, None)
            message_times.pop(client, None)
            persistent_users.discard(nickname)
            print(f"Kullanıcı listesi güncellenirken bağlantısı kopan istemci kaldırıldı: {nickname}")

    # İstemciden gelen mesajları işleyen fonksiyon
    def handle_chat_receive(conn, sender):
        try:
            while True:
                msg = conn.recv(1024).decode('utf-8')
                if not msg:
                    print(f"{sender} adresinden mesaj alınamadı, bağlantı kapatılıyor")
                    break
                print(f"{sender} adresinden mesaj alındı: {msg}")
                if msg == "Exit":
                    nickname = clients[conn]
                    clients.pop(conn, None)
                    message_times.pop(conn, None)
                    persistent_users.discard(nickname)
                    broadcast(f"{nickname} sohbetten ayrıldı!")
                    send_user_list()
                    conn.close()
                    break
                elif msg.startswith("PM"):
                    _, target, pm_message = msg.split(" ", 2)
                    for client, nick in clients.items():
                        if nick == target:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            pm_full = f"[{timestamp}] [Özel mesaj - {clients[conn]}] {pm_message}"
                            try:
                                client.send(pm_full.encode('utf-8'))
                            except:
                                pass
                            break
                    else:
                        conn.send(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Kullanıcı {target} bulunamadı!".encode('utf-8'))
                else:
                    current_time = time.time()
                    message_times.setdefault(conn, []).append(current_time)
                    message_times[conn] = message_times[conn][-5:]
                    if len(message_times[conn]) == 5 and (current_time - message_times[conn][0]) < 5:
                        conn.send("Mesaj sınırı aşıldı! 10 saniye susturuldunuz.".encode('utf-8'))
                        threading.Event().wait(10)
                        message_times[conn].clear()
                    else:
                        broadcast(f"{clients[conn]}: {msg}")
        except Exception as e:
            print(f"{sender} için mesaj alma hatası: {str(e)}")
            nickname = clients.get(conn, "Bilinmeyen")
            clients.pop(conn, None)
            message_times.pop(conn, None)
            persistent_users.discard(nickname)
            broadcast(f"{nickname} bağlantısı koptu!")
            send_user_list()
            conn.close()

    # Yeni istemci bağlantılarını kabul eder
    while True:
        try:
            client_socket, address = server.accept()
            print(f"{address} ile bağlantı kuruldu")
            client_socket.send("NICK".encode('utf-8'))
            nickname = client_socket.recv(1024).decode('utf-8')
            print(f"Alınan takma ad: {nickname}")
            while nickname in clients.values() or '*' in nickname:
                client_socket.send("Bu takma ad alınmış veya geçersiz! Başka bir tane deneyin.".encode('utf-8'))
                nickname = client_socket.recv(1024).decode('utf-8')
            clients[client_socket] = nickname
            persistent_users.add(nickname)
            broadcast(f"{nickname} sohbete katıldı!")
            send_user_list()
            threading.Thread(target=handle_chat_receive, args=(client_socket, address), daemon=True).start()
        except Exception as e:
            print(f"İstemci kabul hatası: {str(e)}")
            break
    server.close()

if __name__ == "__main__":
    start_server()