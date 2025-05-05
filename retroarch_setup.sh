#!/bin/bash
# retroarch_setup.sh
# Script para configurar o RetroArch para Netplay

# Diretório de configuração do RetroArch
CONFIG_DIR="$HOME/.config/retroarch"
CONFIG_FILE="$CONFIG_DIR/retroarch.cfg"

# Verificar se o RetroArch está instalado
if ! command -v retroarch &> /dev/null; then
    echo "RetroArch não encontrado. Instalando..."
    sudo apt update
    sudo apt install -y retroarch
fi

# Criar diretório de configuração se não existir
mkdir -p "$CONFIG_DIR"

# Backup da configuração existente
if [ -f "$CONFIG_FILE" ]; then
    cp "$CONFIG_FILE" "$CONFIG_FILE.backup"
    echo "Backup da configuração existente criado em $CONFIG_FILE.backup"
fi

# Configurar NetPlay no RetroArch
cat > "$CONFIG_FILE" << EOL
# Configurações básicas
video_fullscreen = "false"
video_smooth = "false"
video_vsync = "true"
audio_enable = "true"

# Configurações de caminho
libretro_directory = "/usr/lib/libretro"
libretro_info_path = "/usr/share/libretro/info"
system_directory = "$HOME/.config/retroarch/system"
savefile_directory = "$HOME/.config/retroarch/saves"
savestate_directory = "$HOME/.config/retroarch/states"

# Configurações de NetPlay
netplay_nickname = "Player"
netplay_public_announce = "false"
netplay_start_as_spectator = "false"
netplay_allow_slaves = "true"
netplay_require_slaves = "false"
netplay_stateless_mode = "false"
netplay_use_mitm_server = "false"
netplay_ip_port = "55435"
netplay_delay_frames = "2"
netplay_check_frames = "30"
netplay_client_swap_input = "false"
netplay_player_index = "0" 

# Configuração específica para SNES
input_libretro_device_p1 = "1"
input_libretro_device_p2 = "1"
input_libretro_device_p3 = "1"
input_libretro_device_p4 = "1"

# Configuração para Multitap (suporte a 4 jogadores)
input_player1_joypad_index = "0"
input_player2_joypad_index = "1" 
input_player3_joypad_index = "2"
input_player4_joypad_index = "3"
EOL


echo "Configuração do RetroArch para NetPlay concluída!"

# Baixar ROM se não existir
ROM_DIR="$HOME/ROMs/SNES"
mkdir -p "$ROM_DIR"

echo "Certifique-se de ter a ROM do Super Bomberman 4 em $ROM_DIR"
echo "Nota: Por questões legais, não podemos baixar automaticamente a ROM."
echo "Você precisará fornecer sua própria cópia da ROM."
echo ""

# Criar diretório para a ROM
echo "Criar diretório de sistema para BIOS do SNES"
mkdir -p "$HOME/.config/retroarch/system"

echo "Configuração concluída!"
echo "Execute o cliente P2P com: python3 p2p_client.py <nome_jogador> <ip_servidor>:5000 $ROM_DIR/super_bomberman_4.sfc"