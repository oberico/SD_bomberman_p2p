#!/bin/bash
# raspberry_setup.sh
# Script específico para configurar o Raspberry Pi 3 Model B

echo "Configurando Raspberry Pi 3 Model B para Super Bomberman 4 P2P..."

# Atualizar o sistema
echo "Atualizando o sistema..."
sudo apt update && sudo apt upgrade -y

# Instalar dependências
echo "Instalando dependências..."
sudo apt install -y python3 python3-pip retroarch libretro-snes9x git python3-flask python3-socketio

# Criar diretório para o projeto
echo "Configurando diretório do projeto..."
mkdir -p ~/bomberman_p2p
cd ~/bomberman_p2p

# Instalar bibliotecas Python necessárias
echo "Instalando bibliotecas Python..."
pip3 install flask flask-socketio requests netifaces python-dotenv

# Otimizar o Raspberry Pi para melhor desempenho
echo "Otimizando o Raspberry Pi para melhor desempenho..."

# Ajustar configurações de overclock (moderado e seguro para Raspberry Pi 3)
sudo tee -a /boot/config.txt > /dev/null << EOL

# Overclock seguro para Raspberry Pi 3
arm_freq=1300
gpu_freq=500
over_voltage=4
temp_limit=80
EOL

# Configurar o RetroArch para o Raspberry Pi
echo "Configurando RetroArch para o Raspberry Pi..."
mkdir -p ~/.config/retroarch

cat > ~/.config/retroarch/retroarch.cfg << EOL
# Configurações básicas para Raspberry Pi
video_driver = "gl"
video_fullscreen = "true"
video_smooth = "false"
video_vsync = "true"
audio_enable = "true"

# Otimizações para desempenho
video_threaded = "true"
video_hard_sync = "true"
video_hard_sync_frames = "3"
video_refresh_rate = "60.000000"
audio_latency = "64"

# Configurações de caminho
libretro_directory = "/usr/lib/libretro"
libretro_info_path = "/usr/share/libretro/info"
system_directory = "/home/pi/.config/retroarch/system"
savefile_directory = "/home/pi/.config/retroarch/saves"
savestate_directory = "/home/pi/.config/retroarch/states"

# Configurações de NetPlay
netplay_nickname = "RaspberryPi"
netplay_public_announce = "false"
netplay_start_as_spectator = "false"
netplay_allow_slaves = "true"
netplay_require_slaves = "false"
netplay_stateless_mode = "false"
netplay_use_mitm_server = "false"
netplay_ip_port = "55435"
netplay_delay_frames = "2"
netplay_check_frames = "30"

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

# Criar diretórios para ROMs e estados
mkdir -p ~/ROMs/SNES
mkdir -p ~/.config/retroarch/saves
mkdir -p ~/.config/retroarch/states
mkdir -p ~/.config/retroarch/system

echo "Configuração do Raspberry Pi concluída!"
# Verificar o caminho correto do core para o Raspberry Pi
LIBRETRO_PATH=$(find /usr/lib -name "snes9x_libretro.so" | head -1)
echo "Core libretro encontrado em: $LIBRETRO_PATH"
echo "Atualize a variável LIBRETRO_PATH no p2p_client.py para: $LIBRETRO_PATH"

echo "Copie os arquivos do sistema P2P para ~/bomberman_p2p e execute o script quick_start.sh"
echo "Lembre-se de também copiar a ROM para ~/ROMs/SNES/"
echo "Comando para iniciar o RetroArch manualmente: retroarch --verbose --libretro=$LIBRETRO_PATH ~/ROMs/SNES/super_bomberman_4.sfc"