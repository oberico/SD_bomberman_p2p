#!/bin/bash
# Script para instalação dos requisitos no notebook e Raspberry Pi

# Atualizar sistema
sudo apt update
sudo apt upgrade -y

# Instalar dependências
sudo apt install -y python3 python3-pip retroarch libretro-snes9x

# Instalar bibliotecas Python necessárias
pip3 install flask flask-socketio requests netifaces python-dotenv

# Configurar RetroArch (caso ainda não tenha)
mkdir -p ~/.config/retroarch/