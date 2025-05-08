# 📚 Documento Técnico - Sistema P2P para Jogos Multiplayer

---

## 🎯 Objetivo

Este documento tem como objetivo explicar de forma técnica e clara o funcionamento do sistema desenvolvido para jogar *Super Bomberman 4* online entre múltiplos jogadores. Ele também aborda conceitos de sistemas distribuídos, protocolos de comunicação, escolhas arquiteturais e alternativas possíveis.

---

## 🔧 Arquitetura Geral

O sistema é baseado em uma **arquitetura híbrida** que combina:
- Um **servidor centralizado** (`discovery_server.py`) para descoberta e coordenação inicial
- Comunicação direta entre os jogadores via **NetPlay do RetroArch**

### Componentes Principais

| Componente | Função |
|-----------|--------|
| `discovery_server.py` | Servidor Flask + Socket.IO para registro e notificação dos peers |
| `p2p_client.py` | Cliente P2P que se conecta ao servidor e inicia o jogo via NetPlay |
| **RetroArch NetPlay** | Plataforma de emulação com suporte a jogos multiplayer online |


### Diagrama de Arquitetura:

```
┌─────────────────┐
│                 │
│  Servidor de    │
│  Descoberta     │◄───┐
│                 │    │
└────────┬────────┘    │ Registro e descoberta
         │            │ de peers
         ▼            │
┌─────────────────┐   │    ┌─────────────────┐
│                 │   │    │                 │
│  Cliente P2P 1  ├───┘    │  Cliente P2P 3  │
│  (Host)         │◄──────►│                 │
│                 │        │                 │
└───────┬─────────┘        └─────────────────┘
        │                          ▲
        │                          │
        ▼                          │
┌─────────────────┐                │
│                 │                │
│  Cliente P2P 2  ├────────────────┘
│                 │
│                 │
└─────────────────┘
```

---

## 💬 Como os Clientes Trocam Mensagens?

A comunicação ocorre em duas etapas principais:

### 1. Registro e Coordenação Inicial (via HTTP/Socket.IO)

- Os clientes se registram no servidor de descoberta com informações como IP, porta e nome
- O servidor mantém uma lista de todos os jogadores conectados
- Notificações são feitas via **WebSocket (Socket.IO)**:
  - Novo jogador entrou
  - Jogador saiu
  - Jogo iniciou

> ✅ Formato: JSON  
> ✅ Protocolo: REST API (HTTP) + WebSocket (Socket.IO)

### 2. Jogo em Andamento (via NetPlay do RetroArch)

- Após o início do jogo, o host e os clientes se conectam diretamente usando o **NetPlay do RetroArch**
- A comunicação ocorre por **TCP ou UDP na porta 55435**
- O estado do jogo é sincronizado apenas pelas entradas dos jogadores

> ✅ Formato: Binário interno do NetPlay  
> ✅ Protocolo: TCP/UDP

---

## 🧠 Por Que Usar Essa Abordagem?

### ✔️ Vantagens da Abordagem Atual

| Vantagem | Descrição |
|---------|-----------|
| Simples de implementar | Uso de tecnologias conhecidas (Python, Flask, Socket.IO) |
| Funciona localmente | Ideal para redes locais, sem necessidade de infraestrutura complexa |
| Baixa latência | Conexão direta entre jogadores após início do jogo |
| Reutiliza ferramentas existentes | Usa o NetPlay do RetroArch, já testado e confiável |
| Escalável até 4 jogadores | Limitado pelo próprio NetPlay do RetroArch |

### ❓ Por Que Não Fazer Tudo Diretamente com NetPlay?

O NetPlay do RetroArch permite conectar-se diretamente a outro jogador via IP, mas não possui mecanismo de **descoberta automática** de jogadores na rede local.

Isso significa que, **sem um servidor de descoberta**, cada jogador teria que:
- Saber manualmente o IP do host
- Digitar esse IP toda vez que quiser jogar
- Gerenciar manualmente os índices dos jogadores

> ✅ O servidor centralizado resolve isso com baixo overhead

---

## 🔄 Alternativas Possíveis

| Abordagem                              | Como funcionaria                                     | Vantagens                                 | Desvantagens                          |
| -------------------------------------- | ---------------------------------------------------- | ----------------------------------------- | ------------------------------------- |
| Somente NetPlay (manual)               | Cada jogador digita o IP do host manualmente         | Simples, zero dependências extras         | Não escala, difícil uso em LAN        |
| Todos conectam-se a um MITM Server     | Um servidor intermediário gerencia todas as conexões | Mais estável, funciona fora da rede local | Latência maior, mais complexo         |
| Peer-to-Peer puro (ZeroMQ, gRPC, etc.) | Clientes se comunicam diretamente via TCP/UDP        | Totalmente descentralizado                | Complexidade alta, reinvenção da roda |
| WebRTC + WebAssembly                   | Jogo totalmente no navegador                         | Portabilidade máxima                      | Performance ruim para emulação SNES   |

> ✅ Esta abordagem equilibra simplicidade com funcionalidade prática, sendo ideal para redes locais

---

## ⚙️ Protocolos Utilizados

| Protocolo | Camada | Finalidade |
|----------|--------|------------|
| HTTP/REST | Aplicação | Registro, heartbeat, obtenção de lista de peers |
| WebSocket (Socket.IO) | Aplicação | Eventos em tempo real (novo peer, início do jogo) |
| TCP/UDP (NetPlay) | Transporte | Sincronização de estado durante o jogo |
| JSON | Aplicação | Estruturação de mensagens entre cliente e servidor |
| UUID | Aplicação | Identificação única de jogadores |
| Heartbeat | Aplicação | Garantir que só jogadores ativos estejam conectados |

---

## 🌐 O Sistema Funciona Fora da Rede Local?

### ❌ Não, atualmente ele requer que todos os jogadores estejam na mesma rede local.

#### Motivos:
- O `discovery_server.py` **não faz NAT traversal ou tunneling**
- O NetPlay do RetroArch **usa IPs internos da rede**
- Sem servidor MITM ou configuração de port forwarding, **não há acesso externo**

---

## 🤔 Qual o Custo dessa Implementação?

| Tipo de Custo | Detalhe |
|--------------|----------|
| **Rede** | Baixo — somente o servidor precisa estar acessível |
| **Processamento** | Muito baixo — o cliente apenas repassa dados |
| **Memória** | Pouco consumo — não há armazenamento permanente |
| **Manutenção** | Médio — pode exigir ajustes conforme versão do RetroArch muda |
| **Escalonabilidade** | Limitado a até 4 jogadores simultâneos (limite do NetPlay) |

> Esta abordagem é **ótima para ambientes controlados (como laboratório ou LAN Party)**

---

## 🛠️ Relação com Sistemas Distribuídos

| Conceito | Como foi aplicado |
|---------|--------------------|
| **Transparência de Localização** | O jogador não precisa saber onde está o host — o servidor descobre |
| **Eventos Assíncronos** | Socket.IO notifica início do jogo em tempo real |
| **Tolerância a Falhas** | Heartbeat remove jogadores offline |
| **Sincronização de Estado** | Índices garantem controle individualizado |
| **Comunicação Direta entre Peers** | Após início do jogo, comunicação é P2P |
| **Coordenação Centralizada** | O host decide quando iniciar o jogo |

---

## 🧪 Fluxo Completo do Sistema

1. Servidor de descoberta é iniciado
2. Jogadores se registram no servidor com seu IP, porta e nome
3. Cada jogador recebe a lista de peers conectados
4. Índice do jogador é determinado com base na ordem de entrada
5. Host aperta "iniciar" → evento `start_game` é emitido via WebSocket
6. Todos os jogadores iniciam o RetroArch:
   - Host: `--host`
   - Clientes: `--connect <IP_HOST>`
7. Jogo começa com comunicação direta entre jogadores via NetPlay

---

## 🧱 Estrutura das Mensagens

Todas as mensagens entre cliente e servidor usam **JSON**, um formato leve e amplamente adotado em APIs modernas.

### Exemplo: Registro no Servidor

```json
{
  "peer_id": "uuid",
  "ip": "192.168.0.199",
  "port": 5001,
  "name": "Player1"
}
```

### Exemplo: Resposta com Lista de Peers

```json
{
  "status": "success",
  "peers": {
    "peer1_uuid": { "ip": "...", "port": 5001, "name": "Player1", "last_seen": 123456789 },
    "peer2_uuid": { ... }
  },
  "your_id": "peer2_uuid"
}
```

---

## Instruções de Uso

### Pré-requisitos:

- ROM do Super Bomberman 4
- Dispositivos conectados na mesma rede

### Passos para Execução:


1. **Configuração do Ambiente:**
	1.  Instalar as Dependências
	
	         sudo apt install -y python3 python3-pip retroarch libretro-snes9x

	2. Instalar bibliotecas Python necessárias
	    
	         pip install flask flask-socketio socketio requests netifaces

	3. Configurar RetroArch (caso ainda não tenha)
	
	         pip install flask flask-socketio socketio requests netifaces
	

2. **Configuração do RetroArch:**
   ```bash
   chmod +x retroarch_setup.sh
   ./retroarch_setup.sh
   ```

3. **Iniciando o Servidor de Descoberta (em um dos dispositivos):**
   ```bash
   chmod +x quick_start.sh
   ./quick_start.sh server DiscoveryServer
   ```

4. **Iniciando os Clientes (em cada dispositivo):**
   ```bash
   ./quick_start.sh client Player1 /caminho/para/super_bomberman_4.sfc
   ```

5. **Iniciar o jogo como host:**
   No primeiro cliente que se conectar (que será designado como host), selecione a opção "iniciar" no menu.
