# Sistema Distribuído P2P para Super Bomberman 4

## Introdução

Este projeto implementa um sistema distribuído peer-to-peer (P2P) para permitir que múltiplos jogadores joguem Super Bomberman 4 online através do emulador RetroArch. O sistema foi projetado como um trabalho prático para a disciplina de Sistemas Distribuídos, demonstrando os conceitos fundamentais de sistemas distribuídos, comunicação em rede e sincronização de estado entre nós em uma arquitetura P2P.

## Arquitetura do Sistema

O sistema utiliza uma arquitetura híbrida P2P com um servidor de descoberta central. Esta escolha de arquitetura balanceia a escalabilidade e robustez de sistemas P2P puros com a facilidade de descoberta e conexão fornecida por um servidor central.

### Componentes principais:

1. **Servidor de Descoberta**: Facilita o encontro dos peers na rede
2. **Clientes P2P**: Peers que se comunicam diretamente entre si
3. **Integração com RetroArch**: Utiliza o recurso NetPlay do RetroArch para sincronização de estado do jogo

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

## Conceitos de Sistemas Distribuídos Implementados

### 1. Arquitetura P2P

O sistema utiliza uma arquitetura P2P híbrida, onde os peers se comunicam diretamente entre si para o jogo, mas utilizam um servidor central para descoberta.

### 2. Descoberta e Registro de Serviços

O servidor de descoberta mantém um registro de todos os peers ativos e facilita a conexão inicial entre eles.

### 3. Comunicação Assíncrona

Os peers utilizam comunicação assíncrona (REST API e WebSockets) para troca de informações.

### 4. Sincronização de Estado

RetroArch NetPlay é utilizado para sincronização de estado do jogo entre os peers.

### 5. Tolerância a Falhas

O sistema implementa mecanismos de detecção de falhas (heartbeats) para identificar e remover peers inativos.

### 6. Escalabilidade

A arquitetura permite a adição de novos peers até o limite do jogo (4 jogadores).

## Implementação

### Tecnologias Utilizadas:

- **Python 3**: Linguagem principal de programação
- **Flask**: Framework web para APIs REST
- **Flask-SocketIO**: Para comunicação em tempo real via WebSockets
- **RetroArch**: Emulador com suporte a NetPlay
- **Super Bomberman 4**: ROM do Super Nintendo com suporte a multijogador

### Componentes do Sistema:

1. **discovery_server.py**: Servidor de descoberta para registro e gerenciamento de peers
2. **p2p_client.py**: Cliente P2P que se comunica com outros peers e controla o RetroArch
3. **retroarch_setup.sh**: Script para configuração do RetroArch para NetPlay
4. **quick_start.sh**: Script de inicialização rápida do sistema

## Instruções de Uso

### Pré-requisitos:

- Python 3.6 ou superior
- RetroArch instalado
- ROM do Super Bomberman 4
- Dispositivos conectados na mesma rede (usando smartphone como hotspot)

### Passos para Execução:

1. **Configuração do Ambiente:**
   ```bash
   chmod +x setup_environment.sh
   ./setup_environment.sh
   ```

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

## Explicação dos Conceitos de Sistemas Distribuídos

### Arquitetura P2P vs Cliente-Servidor

A arquitetura P2P foi escolhida por várias razões:

1. **Melhor latência**: A comunicação direta entre os peers reduz a latência, crucial para jogos
2. **Eliminação de ponto único de falha**: Se o servidor de descoberta falhar após as conexões iniciais, o jogo continua funcionando
3. **Distribuição de carga**: O processamento é distribuído entre todos os participantes

### Sincronização e Consistência

O RetroArch NetPlay implementa uma sincronização baseada em frames para garantir que o estado do jogo seja consistente entre todos os peers:

1. **Lockstep synchronization**: Todos os peers aguardam até que os inputs de todos os jogadores sejam recebidos antes de avançar um frame
2. **Delay frames**: Introdução de um pequeno atraso para compensar a latência da rede

### Detecção de Falhas

O sistema utiliza um mecanismo de heartbeat para detectar falhas:

1. Cada peer envia heartbeats periódicos para o servidor de descoberta
2. Peers não responsivos por mais de 30 segundos são considerados inativos e removidos

## Conclusão

Este projeto demonstra vários conceitos fundamentais de Sistemas Distribuídos, incluindo arquitetura P2P, descoberta de serviços, tolerância a falhas e sincronização de estado. A implementação prática com o jogo Super Bomberman 4 permite visualizar como esses conceitos funcionam em um cenário real e interativo.

A arquitetura escolhida (P2P híbrida) representa um equilíbrio entre as vantagens de sistemas P2P puros (desempenho, resistência a falhas) e sistemas cliente-servidor (facilidade de implementação, descoberta centralizada).

Esta implementação pode ser estendida para outros jogos multijogador no RetroArch, demonstrando a flexibilidade do sistema desenvolvido.