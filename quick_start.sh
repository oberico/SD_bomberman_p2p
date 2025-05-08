#!/bin/bash
# quick_start.sh
# Script para inicialização rápida do sistema P2P

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Verificar argumentos
if [ "$#" -lt 2 ]; then
    echo -e "${RED}Uso: $0 <modo> <nome_jogador> [caminho_rom]${NC}"
    echo -e "${YELLOW}Modos disponíveis:${NC}"
    echo -e "  ${GREEN}server${NC} - Iniciar como servidor de descoberta"
    echo -e "  ${GREEN}client${NC} - Iniciar como cliente"
    echo -e "  ${YELLOW}Exemplo: $0 server DiscoveryServer${NC}"
    echo -e "  ${YELLOW}Exemplo: $0 client Player1 ~/ROMs/SNES/super_mario_kart.sfc${NC}"
    exit 1
fi

MODE=$1
PLAYER_NAME=$2
ROM_PATH=${3:-"$HOME/ROMs/SNES/super_mario_kart.sfc"}

# Verificar se os scripts Python existem
if [ ! -f "discovery_server.py" ] || [ ! -f "p2p_client.py" ]; then
    echo -e "${RED}Arquivos Python não encontrados no diretório atual.${NC}"
    echo -e "${YELLOW}Verifique se você está no diretório correto.${NC}"
    exit 1
fi

# Verificar se o RetroArch está instalado corretamente
if ! command -v retroarch &> /dev/null; then
    echo -e "${RED}RetroArch não encontrado. Por favor, instale o RetroArch antes de continuar.${NC}"
    exit 1
fi

# Verificar se existe um core do SNES disponível
SNES_CORE=$(find /usr -name "snes9x_libretro.so" 2>/dev/null | head -1)
if [ -z "$SNES_CORE" ]; then
    echo -e "${RED}Core do SNES (snes9x_libretro.so) não encontrado.${NC}"
    echo -e "${YELLOW}Por favor, instale o core snes9x para o RetroArch:${NC}"
    echo -e "${GREEN}sudo apt install -y libretro-snes9x${NC}"
    exit 1
else
    echo -e "${GREEN}Core do SNES encontrado em: $SNES_CORE${NC}"
fi

# Detectar IP local
get_local_ip() {
    ip=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -n 1)
    if [ -z "$ip" ]; then
        ip="127.0.0.1"
    fi
    echo $ip
}

LOCAL_IP=$(get_local_ip)

# Função para iniciar o servidor
start_server() {
    echo -e "${BLUE}Iniciando servidor de descoberta em $LOCAL_IP:5000...${NC}"
    python3 discovery_server.py
}

# Função para iniciar o cliente
start_client() {
    # Verificar se a ROM existe
    if [ ! -f "$ROM_PATH" ]; then
        echo -e "${RED}ROM não encontrada: $ROM_PATH${NC}"
        echo -e "${YELLOW}Especifique o caminho correto para a ROM.${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}Detectado IP local: $LOCAL_IP${NC}"
    echo -e "${YELLOW}Informe o IP do servidor de descoberta (pressione Enter para usar o local $LOCAL_IP):${NC}"
    read SERVER_IP
    SERVER_IP=${SERVER_IP:-$LOCAL_IP}
    
    echo -e "${GREEN}Iniciando cliente P2P como $PLAYER_NAME...${NC}"
    echo -e "${YELLOW}Conectando ao servidor de descoberta em $SERVER_IP:5000${NC}"
    python3 p2p_client.py "$PLAYER_NAME" "$SERVER_IP:5000" "$ROM_PATH"
}

# Verificar permissões de execução
chmod +x discovery_server.py p2p_client.py

# Iniciar no modo escolhido
case $MODE in
    server)
        start_server
        ;;
    client)
        start_client
        ;;
    *)
        echo -e "${RED}Modo inválido: $MODE${NC}"
        echo -e "${YELLOW}Modos disponíveis: server, client${NC}"
        exit 1
        ;;
esac
