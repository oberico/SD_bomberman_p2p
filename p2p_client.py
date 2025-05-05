#!/usr/bin/env python3
# p2p_client.py
# Cliente P2P para jogo Super Bomberman 4

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
from flask_socketio import SocketIO, emit
import socketio as sio_client

SNES9X_CORE = "/usr/lib/libretro/snes9x_libretro.so"
if not os.path.exists(SNES9X_CORE):
    # Tentar encontrar o core em outro local comum no Raspberry Pi
    SNES9X_CORE = "/usr/lib/arm-linux-gnueabihf/libretro/snes9x_libretro.so"
    if not os.path.exists(SNES9X_CORE):
        print("[ERRO] Core SNES9x não encontrado!")
        sys.exit(1)
        
# Configuração do logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('p2p_client')

# Configurações
RETROARCH_PATH = "retroarch"  # Caminho para o executável do RetroArch
ROM_PATH = ""  # Caminho para a ROM do Super Bomberman 4
DISCOVERY_SERVER = ""  # Endereço do servidor de descoberta
CLIENT_PORT = 5001  # Porta padrão do cliente (será incrementada se ocupada)
HEARTBEAT_INTERVAL = 10  # Intervalo de heartbeat em segundos

def find_snes_core():
    """Encontra o caminho para o core do SNES (snes9x_libretro.so)"""
    import os
    import platform
    
    possible_paths = [
        "/usr/lib/x86_64-linux-gnu/libretro/snes9x_libretro.so",
        "/usr/lib/arm-linux-gnueabihf/libretro/snes9x_libretro.so",
        "/usr/lib/libretro/snes9x_libretro.so"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
            
    try:
        import subprocess
        result = subprocess.run(["find", "/usr", "-name", "snes9x_libretro.so"], 
                               capture_output=True, text=True)
        if result.stdout:
            return result.stdout.strip().split("\n")[0]
    except:
        pass
        
    if platform.machine().startswith('arm'):
        return "/usr/lib/arm-linux-gnueabihf/libretro/snes9x_libretro.so"
    else:
        return "/usr/lib/x86_64-linux-gnu/libretro/snes9x_libretro.so"

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
        self.player_index = 0  # Índice do jogador (0 = Player 1, 1 = Player 2, etc.)
        
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self.setup_routes()
        
        self.sio_client = sio_client.Client()
        self.setup_socketio_client()

    def get_local_ip(self):
        """Obtém o IP local da máquina"""
        try:
            interfaces = ni.interfaces()
            for interface in interfaces:
                if interface.startswith('wl'):  # Interfaces wireless
                    addresses = ni.ifaddresses(interface)
                    if ni.AF_INET in addresses:
                        return addresses[ni.AF_INET][0]['addr']
            return '127.0.0.1'
        except Exception as e:
            logger.error(f"Erro ao obter IP local: {e}")
            return '127.0.0.1'

    def find_available_port(self, start_port):
        """Encontra uma porta disponível começando da porta inicial"""
        port = start_port
        while port < start_port + 100:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind(('', port))
                sock.close()
                return port
            except OSError:
                port += 1
            finally:
                sock.close()
        raise RuntimeError("Não foi possível encontrar uma porta disponível")

    def setup_routes(self):
        """Configura as rotas do servidor Flask"""
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
        """Configura eventos do cliente SocketIO"""
        @self.sio_client.on('new_peer')
        def on_new_peer(data):
            peer_id = data.get('peer_id')
            if peer_id != self.peer_id:
                logger.info(f"Novo peer conectado: {data.get('name')}")
                self.peers[peer_id] = data
        
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

    def register_with_discovery_server(self):
        """Registra o cliente no servidor de descoberta"""
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
                logger.info(f"Registrado com sucesso. Peers ativos: {len(self.peers)}")
                
                # Determinar o índice do jogador baseado na ordem de conexão
                self.player_index = self.get_player_index()
                logger.info(f"Você é o Player {self.player_index + 1}")
                
                if len(self.peers) == 1:
                    self.is_host = True
                    logger.info("Você é o host da partida!")
                    
                return True
            else:
                logger.error(f"Erro no registro: {data.get('message')}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Falha ao conectar ao servidor de descoberta: {e}")
            return False

    def get_player_index(self):
        """Define o índice do jogador baseado na ordem de conexão"""
        if not self.peers:  # Primeiro jogador (host)
            return 0
        
        # Lista de peers ordenados por tempo de conexão
        sorted_peers = sorted(self.peers.items(), key=lambda x: x[1].get('last_seen', 0))
        
        # Encontra a posição deste peer na lista
        for idx, (peer_id, _) in enumerate(sorted_peers):
            if peer_id == self.peer_id:
                return idx
        
        return 0  # Fallback seguro

    def heartbeat_loop(self):
        """Envia heartbeats periódicos para o servidor de descoberta"""
        while self.running:
            try:
                requests.post(
                    f"http://{self.discovery_server}/heartbeat",
                    json={"peer_id": self.peer_id}
                )
                time.sleep(HEARTBEAT_INTERVAL)
            except requests.exceptions.RequestException as e:
                logger.warning(f"Falha no heartbeat: {e}")
                time.sleep(5)

    def leave_game(self):
        """Notifica o servidor que o peer está saindo do jogo"""
        try:
            requests.post(
                f"http://{self.discovery_server}/leave",
                json={"peer_id": self.peer_id}
            )
            logger.info("Saída do jogo notificada")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Falha ao notificar saída: {e}")

    def start_retroarch(self, is_host=False):
        """Inicia o RetroArch com as configurações de NetPlay"""
        retroarch_config = self.generate_retroarch_config(is_host)
        
        if is_host:
            for peer_id, peer in self.peers.items():
                if peer_id != self.peer_id:
                    try:
                        requests.post(
                            f"http://{peer['ip']}:{peer['port']}/start_game",
                            json={"host_id": self.peer_id}
                        )
                    except requests.exceptions.RequestException as e:
                        logger.warning(f"Falha ao notificar peer {peer['name']}: {e}")
        
        cmd = [
            RETROARCH_PATH,
            "--verbose",
            f"--libretro={SNES_CORE_PATH}",
            "--config", retroarch_config,
            "--appendconfig", retroarch_config,
            self.rom_path
        ]
        
        logger.info(f"Iniciando RetroArch: {' '.join(cmd)}")
        
        try:
            subprocess.run(cmd)
            logger.info("RetroArch encerrado")
        except Exception as e:
            logger.error(f"Erro ao iniciar RetroArch: {e}")

    def generate_retroarch_config(self, is_host):
        config_dir = os.path.expanduser("~/.config/bomberman_p2p")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "retroarch_netplay.cfg")
        
        config = [
            f"netplay_mode = {'host' if is_host else 'client'}",
            "netplay_client_swap_input = false",  # 🔥 Crucial: desativa troca automática
            f"netplay_player_index = {self.player_index}",  # Índice definido automaticamente
            "netplay_delay_frames = 2",
            f"netplay_nickname = \"{self.player_name}\"",
            "netplay_ip_port = 55435",
        ]
        
        if not is_host:
            host_ip = next((p['ip'] for p in self.peers.values() if p['ip'] != self.local_ip), None)
            if host_ip:
                config.append(f"netplay_ip_address = \"{host_ip}\"")
        
        with open(config_path, 'w') as f:
            f.write('\n'.join(config))
        
        return config_path

    def run(self):
        """Inicia o cliente P2P"""
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
            target=lambda: self.socketio.run(
                self.app, 
                host=self.local_ip, 
                port=self.client_port,
                debug=False,
                use_reloader=False
            )
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
                    break
                
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
        print("Exemplo: python p2p_client.py Player1 192.168.0.100:5000 /path/to/bomberman4.sfc")
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