#!/usr/bin/env python3
# p2p_client.py
# Cliente P2P para Super Bomberman 4 - Versão Simples com Reconexão Automática

import os
import sys
import time
import json
import uuid
import signal
import socket
import threading
import subprocess
import requests
import netifaces as ni
import logging
from flask import Flask, request, jsonify
from flask_socketio import SocketIO
import socketio as sio_client

# Configurações
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('p2p_client')

RETROARCH_PATH = "retroarch"
ROM_PATH = ""  # Será definido via linha de comando
CLIENT_PORT = 5001
HEARTBEAT_INTERVAL = 10

def find_snes_core():
    paths = [
        "~/.config/retroarch/cores/snes9x_libretro.so",
        "/home/joabson/.config/retroarch/cores/snes9x_libretro.so"
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    try:
        import subprocess
        result = subprocess.run(["find", "/usr", "-name", "snes9x_libretro.so"],
                               capture_output=True, text=True)
        if result.stdout:
            return result.stdout.strip().split('\n')[0]
    except Exception as e:
        logger.warning(f"Erro ao buscar core SNES: {e}")
    return "/home/joabson/.config/retroarch/cores/snes9x_libretro.so"

SNES_CORE_PATH = find_snes_core()

class P2PClient:
    def __init__(self, player_name, discovery_server, rom_path):
        self.player_name = player_name
        self.discovery_server = discovery_server
        self.rom_path = rom_path
        self.peer_id = str(uuid.uuid4())
        self.peers = {}
        self.is_host = False
        self.running = True
        self.client_port = self.find_available_port(CLIENT_PORT)
        self.local_ip = self.get_local_ip()
        self.player_index = 0  # Base 0 → usado como index+1
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self.setup_routes()

        # Socket.IO Client
        self.sio_client = sio_client.Client()
        self.setup_socketio_client()

    def get_local_ip(self):
        try:
            interfaces = ni.interfaces()
            for interface in interfaces:
                if interface.startswith(('wl', 'en')):
                    addresses = ni.ifaddresses(interface)
                    if ni.AF_INET in addresses:
                        return addresses[ni.AF_INET][0]['addr']
            return '127.0.0.1'
        except Exception as e:
            logger.error(f"Erro ao obter IP local: {e}")
            return '127.0.0.1'

    def find_available_port(self, start_port):
        port = start_port
        while port < start_port + 100:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind(('', port))
                return port
            except OSError:
                port += 1
            finally:
                sock.close()
        raise RuntimeError("Porta indisponível")

    def setup_routes(self):
        @self.app.route('/game_state', methods=['POST'])
        def receive_game_state():
            data = request.json
            logger.debug(f"Estado recebido de {data.get('peer_id')}")
            return jsonify({"status": "success"})

        @self.app.route('/start_game', methods=['POST'])
        def start_game_request():
            if not self.is_host:
                threading.Thread(target=self.start_retroarch, args=(False,)).start()
            return jsonify({"status": "success"})

        @self.app.route('/ping', methods=['GET'])
        def ping():
            return jsonify({"status": "alive"})

    def setup_socketio_client(self):
        @self.sio_client.on('new_peer')
        def on_new_peer(data):
            peer_id = data.get('peer_id')
            if peer_id != self.peer_id and peer_id not in self.peers:
                self.peers[peer_id] = data
                logger.info(f"Novo peer conectado: {data.get('name')}")

        @self.sio_client.on('peer_left')
        def on_peer_left(data):
            peer_id = data.get('peer_id')
            if peer_id in self.peers:
                logger.info(f"Peer desconectado: {self.peers[peer_id]['name']}")
                del self.peers[peer_id]

        @self.sio_client.on('connect')
        def on_connect():
            logger.info("Conectado ao servidor de descoberta")

        @self.sio_client.on('disconnect')
        def on_disconnect():
            logger.info("Desconectado do servidor de descoberta")

        @self.sio_client.on('start_game')
        def on_start_game(data):
            logger.info("Evento 'start_game' recebido. Iniciando RetroArch...")
            threading.Thread(target=self.start_retroarch, args=(False,)).start()

    def register_with_discovery_server(self):
        try:
            response = requests.post(
                f"http://{self.discovery_server}/register",
                json={
                    "peer_id": self.peer_id,
                    "ip": self.local_ip,
                    "port": self.client_port,
                    "name": self.player_name
                }
            )
            data = response.json()
            if response.status_code == 200:
                self.peers = data.get('peers', {})
                self.player_index = self.get_player_index()
                logger.info(f"Você é o Player {self.player_index + 1}")
                if len(self.peers) == 1:
                    self.is_host = True
                    logger.info("Você é o host da partida!")
                return True
            else:
                logger.error(f"Erro no registro: {data.get('message')}")
                return False
        except Exception as e:
            logger.error(f"Falha ao conectar ao servidor: {e}")
            return False

    def get_player_index(self):
        if not self.peers:
            return 0
        sorted_peers = sorted(self.peers.items(), key=lambda x: x[1].get('last_seen', 0))
        for idx, (peer_id, _) in enumerate(sorted_peers):
            if peer_id == self.peer_id:
                return idx
        return len(sorted_peers)

    def heartbeat_loop(self):
        while self.running:
            try:
                requests.post(
                    f"http://{self.discovery_server}/heartbeat",
                    json={"peer_id": self.peer_id}
                )
                time.sleep(HEARTBEAT_INTERVAL)
            except Exception as e:
                logger.warning(f"Heartbeat falhou: {e}")

    def leave_game(self):
        try:
            requests.post(
                f"http://{self.discovery_server}/leave",
                json={"peer_id": self.peer_id}
            )
            logger.info("Saída do jogo notificada")
        except Exception as e:
            logger.warning(f"Erro ao sair: {e}")

    def wait_for_host(self, host_ip, timeout=10, retries=5):
        """Espera até que o host esteja aceitando conexões"""
        import socket
        attempt = 0
        while attempt < retries and self.running:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            try:
                sock.connect((host_ip, 55435))  # Porta do NetPlay
                logger.info(f"Host {host_ip} está pronto.")
                return True
            except socket.error:
                logger.warning(f"Tentativa {attempt + 1}: Host ainda não está pronto. Aguardando...")
                time.sleep(3)
                attempt += 1
            finally:
                sock.close()
        logger.error("Não foi possível alcançar o host após múltiplas tentativas.")
        return False

    def generate_retroarch_config(self, is_host):
        config_dir = os.path.expanduser("~/.config/bomberman_p2p")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "retroarch_netplay.cfg")

        config = [
            "netplay = true",
            f"netplay_mode = {'host' if is_host else 'client'}",
            f"netplay_player_index = {self.player_index + 1}",
            "netplay_client_swap_input = false",
            "netplay_delay_frames = 2",
            f"netplay_nickname = \"{self.player_name}\"",
            "netplay_public_announce = false",
            "netplay_password = \"\"",
            "netplay_spectator_mode_enable = false",
            "netplay_use_mitm_server = false",
            'savefile_directory = "/tmp"',
            "netplay_ip_port = 55435",
        ]
        if not is_host:
            host_peer = next((peer for pid, peer in self.peers.items() if pid != self.peer_id), None)
            if host_peer:
                config.append(f"netplay_ip_address = \"{host_peer['ip']}\"")

        with open(config_path, 'w') as f:
            f.write('\n'.join(config))
        logger.info(f"Arquivo de configuração gerado: {config_path}")
        return config_path

    def start_retroarch(self, is_host=False):
        """Inicia o RetroArch com NetPlay configurado"""
        config_path = self.generate_retroarch_config(is_host)

        # Validações pré-execução
        if not os.path.exists(self.rom_path):
            logger.error(f"ROM não encontrada: {self.rom_path}")
            return

        if not os.path.exists(SNES_CORE_PATH):
            logger.error(f"SNES Core não encontrado: {SNES_CORE_PATH}")
            return

        # Monta o comando base
        cmd = [
            RETROARCH_PATH,
            "-L", SNES_CORE_PATH,
            "--appendconfig", config_path,
            self.rom_path,
            "--verbose"
        ]

        # Modo Host
        if is_host:
            cmd.append("--host")
            logger.info("Iniciando como host...")
            
            # Notifica todos os peers para iniciar o jogo
            for peer_id, peer in self.peers.items():
                if peer_id != self.peer_id:
                    try:
                        requests.post(
                            f"http://{peer['ip']}:{peer['port']}/start_game",
                            json={"host_id": self.peer_id}
                        )
                    except Exception as e:
                        logger.warning(f"Falha ao notificar peer {peer['name']}: {e}")

        # Modo Cliente
        else:
            if not self.peers:
                logger.warning("Nenhum peer conectado. Não é possível iniciar.")
                return
            
            host_ip = next(iter(self.peers.values()))['ip']
            logger.info(f"Conectando ao host em {host_ip}")
            cmd.extend(["--connect", host_ip])

        logger.info(f"Executando RetroArch: {' '.join(cmd)}")
        try:
            # Inicia o processo sem bloquear o script
            subprocess.Popen(cmd)
        except Exception as e:
            logger.error(f"Erro ao iniciar RetroArch: {e}")

    def run(self):
        if not self.register_with_discovery_server():
            logger.error("Falha ao registrar. Saindo.")
            return

        heartbeat_thread = threading.Thread(target=self.heartbeat_loop)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()

        try:
            self.sio_client.connect(f"http://{self.discovery_server}")
        except Exception as e:
            logger.warning(f"Falha ao conectar ao SocketIO: {e}")

        flask_thread = threading.Thread(
            target=lambda: self.socketio.run(self.app, host=self.local_ip, port=self.client_port,
                                             debug=False, use_reloader=False)
        )
        flask_thread.daemon = True
        flask_thread.start()

        logger.info(f"Cliente P2P iniciado em {self.local_ip}:{self.client_port}")
        logger.info(f"Seu ID: {self.peer_id}")

        try:
            while self.running:
                command = input("\nComandos disponíveis:\n"
                                "1. iniciar - Iniciar o jogo\n"
                                "2. peers - Listar peers conectados\n"
                                "3. sair - Sair do jogo\n"
                                "Comando: ")
                if command.lower() in ['iniciar', '1']:
                    if self.is_host:
                        logger.info("Iniciando jogo como host...")
                        threading.Thread(target=self.start_retroarch, args=(True,)).start()
                    else:
                        logger.info("Apenas o host pode iniciar o jogo.")
                elif command.lower() in ['peers', '2']:
                    logger.info(f"Peers conectados ({len(self.peers)}):")
                    for peer_id, peer in self.peers.items():
                        host_status = " (HOST)" if peer_id == self.peer_id and self.is_host else ""
                        logger.info(f"  - {peer['name']} ({peer['ip']}:{peer['port']}){host_status}")
                elif command.lower() in ['sair', '3']:
                    self.running = False
                else:
                    logger.info("Comando inválido.")
        except KeyboardInterrupt:
            logger.info("Encerrando cliente...")
        finally:
            self.leave_game()
            self.running = False
            time.sleep(1)
            logger.info("Cliente encerrado.")

def main():
    if len(sys.argv) < 4:
        print(f"Uso: {sys.argv[0]} <nome_jogador> <servidor_descoberta> <caminho_rom>")
        print("Exemplo: python3 p2p_client.py berico 192.168.0.1:5000 /path/to/rom.sfc")
        sys.exit(1)

    player_name = sys.argv[1]
    discovery_server = sys.argv[2]
    rom_path = sys.argv[3]

    client = P2PClient(player_name, discovery_server, rom_path)

    def signal_handler(sig, frame):
        print("\nEncerrando...")
        client.running = False
        client.leave_game()
        time.sleep(1)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    client.run()

if __name__ == "__main__":
    main()