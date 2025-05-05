#!/usr/bin/env python3
# discovery_server.py
# Servidor de descoberta para encontrar peers na rede

import json
import os
import time
from flask import Flask, request, jsonify
from flask_socketio import SocketIO
import netifaces as ni
import logging

# Configuração do logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('discovery_server')

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Armazenamento para os peers ativos
active_peers = {}
MAX_PLAYERS = 4  # Limite máximo de jogadores

def get_local_ip():
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

@app.route('/register', methods=['POST'])
def register_peer():
    """Registra um novo peer no servidor"""
    data = request.json
    peer_id = data.get('peer_id')
    peer_ip = data.get('ip', request.remote_addr)
    peer_port = data.get('port')
    peer_name = data.get('name', f'Player_{len(active_peers)+1}')
    
    if len(active_peers) >= MAX_PLAYERS:
        return jsonify({"status": "error", "message": "Máximo de jogadores atingido"}), 400
    
    # Registrar o peer
    active_peers[peer_id] = {
        'ip': peer_ip,
        'port': peer_port,
        'name': peer_name,
        'last_seen': time.time()
    }
    
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
        "your_id": peer_id
    })

@app.route('/peers', methods=['GET'])
def get_peers():
    """Retorna a lista de peers ativos"""
    # Remover peers inativos (não vistos nos últimos 30 segundos)
    current_time = time.time()
    inactive_peers = [pid for pid, peer in active_peers.items() 
                     if current_time - peer['last_seen'] > 30]
    
    for pid in inactive_peers:
        logger.info(f"Removendo peer inativo: {active_peers[pid]['name']}")
        del active_peers[pid]
    
    return jsonify(active_peers)

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
        logger.info(f"Peer removido: {peer_name}")
        
        # Notificar outros peers
        socketio.emit('peer_left', {
            'peer_id': peer_id
        })
        
        return jsonify({"status": "success"})
    
    return jsonify({"status": "error", "message": "Peer não encontrado"}), 404

if __name__ == '__main__':
    host_ip = get_local_ip()
    port = 5000
    logger.info(f"Iniciando servidor de descoberta em {host_ip}:{port}")
    socketio.run(app, host=host_ip, port=port, debug=True, allow_unsafe_werkzeug=True)