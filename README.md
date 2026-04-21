# ZipZop 💬

Um sistema de mensagens instantâneas distribuído inspirado no funcionamento básico do WhatsApp. O projeto foi desenvolvido para exercitar conceitos de sistemas distribuídos, como concorrência, comunicação em rede, chamadas remotas e sincronização de estados.

## ✨ Funcionalidades

- **Identificação Simples:** Cadastro de usuários utilizando o número de telefone, nome e apelido.
- **Mensagens em Tempo Real:** Envio e recebimento de mensagens instantâneas (Stream server-side).
- **Status de Entrega e Leitura:** Acompanhamento completo do ciclo de vida da mensagem:
  - `✓` **Enviada** (chegou ao servidor)
  - `✓✓` **Entregue** (destinatário conectou-se e recebeu)
  - `✓✓🔵` **Lida** (destinatário abriu o histórico da conversa)
- **Tolerância a Desconexões:** Mensagens enviadas a usuários offline ficam guardadas com segurança no servidor e são disparadas assim que o destinatário se reconecta.
- **Histórico de Conversas:** Recuperação completa das mensagens trocadas.

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3
- **Comunicação de Rede:** gRPC / Protocol Buffers (RPC robusto sobre HTTP/2)
- **Banco de Dados:** SQLite (com modo `WAL` ativado para suporte a leitura e escrita concorrentes)
- **Concorrência:** Threads e Locks nativos do Python para lidar perfeitamente com múltiplos usuários simultâneos.

## ⚙️ Arquitetura

O sistema implementa uma arquitetura estritamente **distribuída e cliente-servidor**:
- `server/server.py`: O núcleo de rede. Roda o servidor gRPC e mantém filas em memória (Streams) para empurrar mensagens e atualizações de status aos clientes conectados em tempo real.
- `server/database.py`: A camada de persistência. Isolada do cliente, assegura as regras de salvamento de dados usando SQLite.
- `client/client.py`: Aplicação de terminal do usuário final. Comunica-se exclusivamente pela rede com o servidor (nunca tocando no banco diretamente) e utiliza threads secundárias para ouvir mensagens em tempo real sem bloquear as opções do menu (input) do usuário.

## 🚀 Como Executar

### 1. Pré-requisitos
Certifique-se de ter o Python 3 instalado. Instale as dependências de rede e do compilador protobuf executando:
```bash
pip install -r requirements.txt
```

### 2. Rodando de Forma Automatizada (Windows)
A maneira mais fácil de testar o projeto no Windows é utilizando o script que automatiza a abertura de vários terminais:
```bash
python start.py
```
Isso levantará o Servidor em uma janela e dois Clientes separados em outras janelas para você interagir.

### 3. Rodando Manualmente
Se preferir, ou se estiver em Linux/Mac, abra abas de terminal separadas:

**Terminal 1 (O Servidor):**
```bash
python server/server.py
```

**Terminal 2, 3, etc (Os Clientes):**
```bash
python client/client.py
```

---
*Projeto desenvolvido para a disciplina de Sistemas Distribuídos.*
