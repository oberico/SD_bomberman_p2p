#!/usr/bin/env python3
# discovery_server.py
# Servidor de descoberta para encontrar peers na rede

import json
import os
import time
from flask import Flask, request, jsonify
from flask_socketio import SocketIO
import logging

# Configurações via variáveis de ambiente (padrão se não definidas)
MAX_PLAYERS = int(os.getenv("MAX_PLAYER_COUNT", "4"))
HEARTBEAT_TIMEOUT = int(os.getenv("HEARTBEAT_TIMEOUT", "30"))

# Configuração do logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('discovery_server')

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Armazenamento para os peers ativos
active_peers = {}
active_peers_order = []  # Mantém a ordem de entrada dos jogadores

def get_local_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # Google DNS
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

@app.route('/register', methods=['POST'])
def register_peer():
    """Registra um novo peer no servidor"""
    data = request.json

    peer_id = data.get('peer_id')
    peer_name = data.get('name', f'Player_{len(active_peers)+1}')
    peer_port = data.get('port')

    if not peer_id or not isinstance(peer_id, str):
        return jsonify({"status": "error", "message": "peer_id inválido"}), 400
    if not peer_port or not isinstance(peer_port, int):
        return jsonify({"status": "error", "message": "porta inválida"}), 400

    if len(active_peers) >= MAX_PLAYERS:
        return jsonify({"status": "error", "message": "Máximo de jogadores atingido"}), 400

    peer_ip = request.remote_addr  # Fonte confiável do IP

    active_peers[peer_id] = {
        'ip': peer_ip,
        'port': peer_port,
        'name': peer_name,
        'last_seen': time.time()
    }

    if peer_id not in active_peers_order:
        active_peers_order.append(peer_id)

    logger.info(f"Peer registrado: {peer_name} ({peer_ip}:{peer_port})")

    # Notificar todos os peers sobre o novo jogador
    socketio.emit('new_peer', {
        'peer_id': peer_id,
        'ip': peer_ip,
        'port': peer_port,
        'name': peer_name
    })

    return jsonify({
        "status": "success",
        "peers": active_peers,
        "order": active_peers_order,
        "your_id": peer_id
    })

@app.route('/peers', methods=['GET'])
def get_peers():
    """Retorna a lista de peers ativos e a ordem de entrada"""
    current_time = time.time()

    # Remover peers inativos
    inactive_peers = [pid for pid, peer in active_peers.items() if current_time - peer['last_seen'] > HEARTBEAT_TIMEOUT]
    for pid in inactive_peers:
        name = active_peers[pid]['name']
        logger.info(f"Removendo peer inativo: {name}")
        del active_peers[pid]
        if pid in active_peers_order:
            active_peers_order.remove(pid)

    return jsonify({
        "peers": active_peers,
        "order": active_peers_order
    })

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    """Atualiza o timestamp de último contato de um peer"""
    data = request.json
    peer_id = data.get('peer_id')

    if peer_id in active_peers:
        active_peers[peer_id]['last_seen'] = time.time()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Peer não encontrado"}), 404

@app.route('/leave', methods=['POST'])
def leave_game():
    """Remove um peer da lista de ativos"""
    data = request.json
    peer_id = data.get('peer_id')

    if peer_id in active_peers:
        peer_name = active_peers[peer_id]['name']
        del active_peers[peer_id]
        if peer_id in active_peers_order:
            active_peers_order.remove(peer_id)
        logger.info(f"Peer removido: {peer_name}")

        # Notificar outros peers
        socketio.emit('peer_left', {'peer_id': peer_id})
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Peer não encontrado"}), 404

if __name__ == '__main__':
    host_ip = get_local_ip()
    port = int(os.getenv("DISCOVERY_PORT", "5000"))
    logger.info(f"Iniciando servidor de descoberta em {host_ip}:{port}")
    socketio.run(app, host=host_ip, port=port, debug=True, allow_unsafe_werkzeug=True)