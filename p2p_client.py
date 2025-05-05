import socket
import threading
import subprocess
import sys
import json
import time

REMOTE_PORT = 55355
SNES9X_CORE = "/usr/lib/libretro/snes9x_libretro.so"

def listen_for_peers(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", port))
    s.listen(1)
    conn, addr = s.accept()
    print(f"[INFO] Conectado por {addr}")
    conn.close()

def connect_to_server(name, server_ip, rom_path):
    host, port = server_ip.split(":")
    port = int(port)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))

    s.sendall(name.encode())
    data = s.recv(1024)
    info = json.loads(data.decode())
    
    return info

def main():
    if len(sys.argv) != 4:
        print("Uso: python3 p2p_client.py <nome> <ip_servidor:porta> <rom_path>")
        sys.exit(1)

    name = sys.argv[1]
    server_ip = sys.argv[2]
    rom_path = sys.argv[3]

    info = connect_to_server(name, server_ip, rom_path)
    player_index = info["player_index"]
    peer_ip = info["peer_ip"]

    print(f"[INFO] Você é o jogador {player_index}")
    print(f"[INFO] IP do peer: {peer_ip}")

    if player_index == 0:
        # Espera por conexão do peer
        threading.Thread(target=listen_for_peers, args=(REMOTE_PORT,), daemon=True).start()
        time.sleep(2)  # espera o peer tentar conectar

        subprocess.Popen([
            "retroarch",
            "--host",
            "--port", str(REMOTE_PORT),
            "--set", "input_player1_joypad_index=0",
            "--set", "input_player2_joypad_index=1",
            "--set", "input_max_users=2",
            "-L", SNES9X_CORE,
            rom_path
        ])
    else:
        subprocess.Popen([
            "retroarch",
            "--connect", peer_ip,
            "--port", str(REMOTE_PORT),
            "--set", "input_player1_joypad_index=1",
            "--set", "input_player2_joypad_index=0",
            "--set", "input_max_users=2",
            "-L", SNES9X_CORE,
            rom_path
        ])

if __name__ == "__main__":
    main()
