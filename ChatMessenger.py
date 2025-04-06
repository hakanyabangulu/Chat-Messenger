import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import json
import os
import sys
from datetime import datetime
import time

# Sunucu ve istemci temel ayarları
HOST = '127.0.0.1'
PORT = 5555
CONFIG_FILE = "chat_config.json"
LOG_FILE = "chat_log.txt"
EXIT_COMMAND = "exit"
MAX_MESSAGE_LENGTH = 500

# Karanlık tema renk tanımları
THEME = {
    "root_bg": "#1A202C", "top_bg": "#2D3748", "panel_bg": "#2D3748", "entry_bg": "#4A5568",
    "fg": "#E2E8F0", "top_fg": "#E2E8F0", "button_bg": "#63B3ED", "select_bg": "#90CDF4",
    "chat_bg": "#1A202C", "self_msg_fg": "#FFFFFF", "other_msg_fg": "#A0AEC0", "shadow": "#2D3748"
}

# Sunucu için global değişkenler
clients = {}
persistent_users = set()
message_times = {}

# Sunucu fonksiyonu
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

# İstemci arayüzü sınıfı
class ChatMessenger:
    def __init__(self, root):
        self.root = root
        self.root.title("Sohbet Uygulaması")
        self.root.geometry("900x700")
        self.client_socket = None
        self.nickname = None
        self.user_list_data = []
        self.all_users = []
        self.theme = THEME
        self.running = True
        self.chat_active = False
        self.current_frame = None
        self.current_chat_target = None
        self.chat_history = {"Genel Sohbet": []}  # Sohbet geçmişini saklar {hedef: [(mesaj, is_self)]}
        self.setup_ui()

    # Arayüzü kurar
    def setup_ui(self):
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Helvetica", 11), padding=8, borderwidth=0, background=self.theme["button_bg"], foreground="#000000")  # Siyah yazı
        self.style.map("TButton", background=[('active', self.theme["select_bg"])])
        self.style.configure("TLabel", font=("Helvetica", 12), background=self.theme["root_bg"], foreground=self.theme["fg"])

        self.top_frame = tk.Frame(self.root, height=50, bg=self.theme["top_bg"])
        self.top_frame.pack(fill=tk.X)
        self.top_label = tk.Label(self.top_frame, text="Sohbet Uygulaması", font=("Helvetica", 16, "bold"), bg=self.theme["top_bg"], fg=self.theme["top_fg"])
        self.top_label.pack(side=tk.LEFT, padx=15, pady=10)

        self.main_container = tk.Frame(self.root, bg=self.theme["root_bg"])
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.status_bar = tk.Label(self.root, text="Hazır | Bağlı Kullanıcı: 0", bd=1, relief=tk.SUNKEN, anchor=tk.W, font=("Helvetica", 10), bg=self.theme["panel_bg"], fg=self.theme["fg"])
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.show_start_screen()

    # Başlangıç ekranını gösterir
    def show_start_screen(self):
        if self.current_frame:
            self.current_frame.pack_forget()
        self.start_frame = tk.Frame(self.main_container, bg=self.theme["root_bg"])
        self.start_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = self.start_frame
        self.current_chat_target = None

        self.nick_frame = tk.Frame(self.start_frame, bg=self.theme["root_bg"])
        self.nick_frame.pack(pady=50)
        tk.Label(self.nick_frame, text="Takma Ad:", font=("Helvetica", 12), bg=self.theme["root_bg"], fg=self.theme["fg"]).pack(side=tk.LEFT, padx=5)
        self.nick_entry = tk.Entry(self.nick_frame, font=("Helvetica", 12), relief=tk.FLAT, borderwidth=1, bg=self.theme["entry_bg"], fg=self.theme["fg"], insertbackground=self.theme["fg"])
        self.nick_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.nick_entry.insert(0, "Takma adınızı girin...")
        self.nick_entry.bind("<FocusIn>", lambda e: self.nick_entry.delete(0, tk.END) if self.nick_entry.get() == "Takma adınızı girin..." else None)
        self.connect_button = ttk.Button(self.nick_frame, text="Bağlan", command=self.connect)
        self.connect_button.pack(side=tk.LEFT, padx=5)

        self.status_text = scrolledtext.ScrolledText(self.start_frame, font=("Helvetica", 12), wrap=tk.WORD, borderwidth=0, state=tk.DISABLED, bg=self.theme["chat_bg"], fg=self.theme["fg"], height=20)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    # Sohbet ekranını gösterir
    def show_chat_screen(self, target="Genel Sohbet"):
        if self.current_frame:
            self.current_frame.pack_forget()
        self.chat_frame = tk.Frame(self.main_container, bg=self.theme["root_bg"])
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = self.chat_frame
        self.current_chat_target = target

        # Sol panel (Kullanıcı listesi)
        self.left_panel = tk.Frame(self.chat_frame, width=250, bg=self.theme["panel_bg"])
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 1))
        
        self.user_header = tk.Frame(self.left_panel, bg=self.theme["panel_bg"])
        self.user_header.pack(fill=tk.X, pady=(10, 0))
        self.user_label = tk.Label(self.user_header, text="Kişiler", font=("Helvetica", 14, "bold"), bg=self.theme["panel_bg"], fg=self.theme["fg"])
        self.user_label.pack(side=tk.LEFT, padx=10)
        
        self.search_entry = tk.Entry(self.left_panel, font=("Helvetica", 11), relief=tk.FLAT, borderwidth=1, bg=self.theme["entry_bg"], fg="#A0AEC0", insertbackground=self.theme["fg"])
        self.search_entry.insert(0, "Kişi ara...")
        self.search_entry.bind("<FocusIn>", lambda e: self.search_entry.delete(0, tk.END) if self.search_entry.get() == "Kişi ara..." else None)
        self.search_entry.bind("<FocusOut>", lambda e: self.search_entry.insert(0, "Kişi ara...") if not self.search_entry.get() else None)
        self.search_entry.bind("<KeyRelease>", self.filter_users)
        self.search_entry.pack(fill=tk.X, padx=10, pady=5)
        
        self.user_list = tk.Listbox(self.left_panel, font=("Helvetica", 11), borderwidth=0, highlightthickness=0, bg=self.theme["panel_bg"], fg=self.theme["fg"], selectbackground=self.theme["select_bg"])
        self.user_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.user_list.insert(tk.END, "Genel Sohbet")
        self.user_list.bind('<Double-1>', self.switch_chat)

        # Sağ panel (Sohbet alanı)
        self.right_panel = tk.Frame(self.chat_frame, bg=self.theme["root_bg"])
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.chat_title = tk.Label(self.right_panel, text=target if target == "Genel Sohbet" else f"{target} ile Özel Sohbet", font=("Helvetica", 14, "bold"), bg=self.theme["root_bg"], fg=self.theme["fg"])
        self.chat_title.pack(pady=(5, 10), padx=10, anchor="w")

        self.chat_window_frame = tk.Frame(self.right_panel, bg=self.theme["chat_bg"])
        self.chat_window_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.chat_window = scrolledtext.ScrolledText(self.chat_window_frame, font=("Helvetica", 12), wrap=tk.WORD, borderwidth=0, state=tk.DISABLED, bg=self.theme["chat_bg"], fg=self.theme["fg"])
        self.chat_window.pack(fill=tk.BOTH, expand=True)

        self.msg_frame = tk.Frame(self.right_panel, bg=self.theme["root_bg"])
        self.msg_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.msg_entry = tk.Entry(self.msg_frame, font=("Helvetica", 12), relief=tk.FLAT, borderwidth=1, bg=self.theme["entry_bg"], fg=self.theme["fg"], insertbackground=self.theme["fg"])
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.msg_entry.bind("<Return>", self.send_message)
        self.msg_entry.bind("<KeyRelease>", self.update_char_count)
        self.send_button = ttk.Button(self.msg_frame, text="Gönder", command=self.send_message)
        self.send_button.pack(side=tk.LEFT)

        self.char_count_label = tk.Label(self.msg_frame, text=f"0/{MAX_MESSAGE_LENGTH}", font=("Helvetica", 10), bg=self.theme["root_bg"], fg=self.theme["fg"])
        self.char_count_label.pack(side=tk.LEFT, padx=5)

        self.back_button = ttk.Button(self.right_panel, text="Başlangıç Ekranına Dön", command=self.show_start_screen)
        self.back_button.pack(pady=10)

        # Önceki mesajları yükle
        self.load_chat_history(target)
        if self.user_list_data:
            self.update_user_list()

    # Sohbet geçmişini yükler
    def load_chat_history(self, target):
        self.chat_window.config(state=tk.NORMAL)
        self.chat_window.delete(1.0, tk.END)  # Ekranı temizle
        for message, is_self in self.chat_history.get(target, []):
            self.chat_window.insert(tk.END, f"{message}\n", ("self" if is_self else "other",))
            self.chat_window.tag_configure("self", justify="right", foreground=self.theme["self_msg_fg"], font=("Helvetica", 12), lmargin1=50, lmargin2=50, rmargin=10)
            self.chat_window.tag_configure("other", justify="left", foreground=self.theme["other_msg_fg"], font=("Helvetica", 12), lmargin1=10, lmargin2=10, rmargin=50)
        self.chat_window.config(state=tk.DISABLED)
        self.chat_window.see(tk.END)

    # Kullanıcı listesini filtreler
    def filter_users(self, event=None):
        search_text = self.search_entry.get().lower()
        if search_text == "kişi ara...":
            search_text = ""
        self.user_list.delete(0, tk.END)
        self.user_list.insert(tk.END, "Genel Sohbet")
        for nick in self.all_users:
            if nick != self.nickname and search_text in nick.lower():
                self.user_list.insert(tk.END, f"{nick} ●")

    # Mesaj karakter sayısını günceller
    def update_char_count(self, event=None):
        msg = self.msg_entry.get()
        length = len(msg)
        self.char_count_label.config(text=f"{length}/{MAX_MESSAGE_LENGTH}")
        if length > MAX_MESSAGE_LENGTH:
            self.char_count_label.config(fg="red")
            self.send_button.config(state=tk.DISABLED)
        else:
            self.char_count_label.config(fg=self.theme["fg"])
            self.send_button.config(state=tk.NORMAL)

    # Sunucuya bağlanır
    def connect(self):
        if not self.nick_entry.get() or self.nick_entry.get() == "Takma adınızı girin...":
            messagebox.showerror("Hata", "Lütfen bir takma ad girin!")
            return
        self.nickname = self.nick_entry.get()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.settimeout(5)
        try:
            print(f"{HOST}:{PORT} adresine bağlanılıyor")
            self.client_socket.connect((HOST, PORT))
            print(f"{HOST}:{PORT} adresine bağlanıldı")
            self.client_socket.settimeout(None)
            self.nick_entry.config(state=tk.DISABLED)
            self.connect_button.config(state=tk.DISABLED)
            self.chat_active = True
            self.status_bar.config(text=f"{self.nickname} olarak bağlandınız | Bağlı Kullanıcı: {len(self.user_list_data)}")
            self.insert_status_message(f"{self.nickname} olarak sunucuya bağlandınız.")
            self.show_chat_screen()
            threading.Thread(target=self.handle_chat_receive, args=(self.client_socket, "Sunucu"), daemon=True).start()
        except socket.timeout:
            print("Bağlantı 5 saniye içinde kurulamadı")
            self.insert_status_message("Sunucuya bağlanılamadı! Bağlantı zaman aşımına uğradı.")
            messagebox.showerror("Hata", "Sunucuya bağlanılamadı! Bağlantı zaman aşımına uğradı.")
            self.status_bar.config(text="Bağlantı başarısız")
        except Exception as e:
            print(f"Bağlantı hatası: {str(e)}")
            self.insert_status_message(f"Sunucuya bağlanılamadı! Hata: {str(e)}")
            messagebox.showerror("Hata", f"Sunucuya bağlanılamadı! Hata: {str(e)}")
            self.status_bar.config(text="Bağlantı başarısız")
        finally:
            if not self.chat_active and self.client_socket:
                self.client_socket.close()
                self.client_socket = None

    # Başlangıç ekranına durum mesajı ekler
    def insert_status_message(self, message):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.config(state=tk.DISABLED)
        self.status_text.see(tk.END)

    # Sohbet penceresine mesaj ekler ve geçmişe kaydeder
    def insert_message(self, message, is_self=False, target=None):
        if target is None:
            target = self.current_chat_target
        if target not in self.chat_history:
            self.chat_history[target] = []
        self.chat_history[target].append((message, is_self))
        
        if target == self.current_chat_target:
            self.chat_window.config(state=tk.NORMAL)
            self.chat_window.insert(tk.END, f"{message}\n", ("self" if is_self else "other",))
            self.chat_window.tag_configure("self", justify="right", foreground=self.theme["self_msg_fg"], font=("Helvetica", 12), lmargin1=50, lmargin2=50, rmargin=10)
            self.chat_window.tag_configure("other", justify="left", foreground=self.theme["other_msg_fg"], font=("Helvetica", 12), lmargin1=10, lmargin2=10, rmargin=50)
            self.chat_window.config(state=tk.DISABLED)
            self.chat_window.see(tk.END)

    # Sunucudan gelen mesajları işler
    def handle_chat_receive(self, conn, sender):
        try:
            while self.running and self.chat_active:
                msg = conn.recv(1024).decode('utf-8')
                if not msg:
                    print("Mesaj alınamadı, bağlantı kapatılıyor")
                    break
                print(f"{sender} adresinden mesaj alındı: {msg}")
                if msg == "NICK":
                    print(f"Takma ad gönderiliyor: {self.nickname}")
                    conn.send(self.nickname.encode('utf-8'))
                elif msg.startswith("USERLIST"):
                    try:
                        self.user_list_data = json.loads(msg.split(" ", 1)[1])
                        self.all_users = self.user_list_data
                        self.root.after(0, self.update_user_list)
                    except json.JSONDecodeError as e:
                        print(f"Kullanıcı listesi çözümleme hatası: {e}")
                elif "[Özel mesaj -" in msg:
                    sender = msg.split("[Özel mesaj - ")[1].split("]")[0]
                    message_content = msg.split("] ")[2]
                    self.root.after(0, lambda m=f"{sender}: {message_content}", t=sender: self.insert_message(m, is_self=False, target=t))
                else:
                    message_content = msg.split("] ")[1]  # Zaman damgasından sonrasını al
                    sender_name = message_content.split(": ", 1)[0]
                    content = message_content.split(": ", 1)[1] if ": " in message_content else message_content
                    self.root.after(0, lambda m=message_content, s=(sender_name == self.nickname): self.insert_message(m, is_self=s, target="Genel Sohbet"))
        except Exception as e:
            print(f"Mesaj alma hatası: {str(e)}")
            self.root.after(0, lambda: self.insert_message("Bağlantı koptu!", target="Genel Sohbet"))
            self.root.after(0, lambda: self.status_bar.config(text="Bağlantı koptu"))
            self.chat_active = False
            self.root.after(0, self.show_start_screen)
            self.insert_status_message("Bağlantı koptu!")
            conn.close()

    # Kullanıcı listesini günceller
    def update_user_list(self):
        self.all_users = self.user_list_data
        self.filter_users()
        self.status_bar.config(text=f"{self.nickname} olarak bağlandınız | Bağlı Kullanıcı: {len(self.user_list_data)}")

    # Mesaj gönderir
    def send_message(self, event=None):
        if not self.chat_active or not self.client_socket:
            messagebox.showerror("Hata", "Önce sunucuya bağlanmalısınız!")
            return
        msg = self.msg_entry.get().strip()
        if not msg:
            return
        if len(msg) > MAX_MESSAGE_LENGTH:
            messagebox.showerror("Hata", f"Mesaj {MAX_MESSAGE_LENGTH} karakterden uzun olamaz!")
            return
        try:
            if self.current_chat_target == "Genel Sohbet":
                self.client_socket.sendall(msg.encode('utf-8'))
                print(f"Gönderilen mesaj: {msg}")
            else:
                self.client_socket.sendall(f"PM {self.current_chat_target} {msg}".encode('utf-8'))
                print(f"{self.current_chat_target} adresine özel mesaj gönderildi: {msg}")
                self.insert_message(f"{self.nickname}: {msg}", is_self=True, target=self.current_chat_target)
            self.msg_entry.delete(0, tk.END)
            self.update_char_count()
        except Exception as e:
            print(f"Gönderme hatası: {str(e)}")
            self.insert_message("Mesaj gönderilemedi, bağlantı koptu!", target=self.current_chat_target)
            self.status_bar.config(text="Bağlantı koptu")
            self.chat_active = False
            self.show_start_screen()

    # Sohbet ekranını değiştirir
    def switch_chat(self, event):
        selected = self.user_list.get(self.user_list.curselection())
        if selected and selected != self.nickname:
            target = selected.replace(" ●", "")
            self.show_chat_screen(target)

    # Sunucudan ayrılır ve uygulamayı kapatır
    def disconnect(self):
        if self.client_socket:
            try:
                self.client_socket.sendall("Exit".encode('utf-8'))
                print("Sunucuya çıkış komutu gönderildi")
                self.client_socket.close()
            except Exception as e:
                print(f"Çıkış hatası: {str(e)}")
            self.client_socket = None
        self.chat_active = False
        self.nick_entry.config(state=tk.NORMAL)
        self.connect_button.config(state=tk.NORMAL)
        self.status_bar.config(text="Bağlantı kesildi | Bağlı Kullanıcı: 0")
        self.insert_status_message("Sunucudan ayrıldınız.")
        self.show_start_screen()
        self.root.quit()  # Pencereyi kapatır

# Ana program
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Kullanım: python chat_app.py [server|client]")
        sys.exit(1)

    mode = sys.argv[1].lower()
    if mode == "server":
        start_server()
    elif mode == "client":
        root = tk.Tk()
        app = ChatMessenger(root)
        root.protocol("WM_DELETE_WINDOW", app.disconnect)  # Pencere kapandığında disconnect çalışır
        root.mainloop()
    else:
        print("Geçersiz mod! 'sunucu' veya 'istemci' kullanın.")
        sys.exit(1)