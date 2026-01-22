# Mensageria

Sistema de chat criptografado onde múltiplos clientes trocam mensagens através de um servidor central com segurança end-to-end.

## Guia Rápido - Como Rodar

### Pré-requisitos

- Python 3.8+
- Biblioteca `cryptography`

### Instalação

```bash
cd seguranca_final


pip install cryptography
```

### Execução Passo a Passo

Você vai precisar de **3 terminais** abertos.

#### Terminal 1 - Iniciar o Servidor

```bash
cd src
python server.py
```

Saída esperada:
```
2026-01-20 10:00:00 - Server - INFO - Servidor iniciado em 0.0.0.0:9999
2026-01-20 10:00:00 - Server - INFO - Credenciais salvas: ../certs/server.crt, ../certs/server.key
2026-01-20 10:00:00 - Server - INFO - Servidor aguardando conexões em 0.0.0.0:9999
```


#### Terminal 2 - Conectar Cliente 1 (Alice)

```bash
cd src
python client.py Alice
```

Saída esperada:
```
2026-01-20 10:00:05 - Client - INFO - Cliente inicializado: Alice (a1b2c3d4...)
2026-01-20 10:00:05 - Client - INFO - Conectado ao servidor 127.0.0.1:9999
2026-01-20 10:00:05 - Client - INFO - Handshake concluído com sucesso

Conectado como: Alice (a1b2c3d4)
Formato de comando: /msg <recipient_id_hex> <mensagem>
Exemplo: /msg a1b2c3d4e5f6g7h8 Oi, tudo bem?
Digite /quit para sair

>
```

**Anote o ID** que aparece entre parênteses (ex: `a1b2c3d4`). O ID completo tem 32 caracteres hexadecimais.

#### Terminal 3 - Conectar Cliente 2 (Bob)

```bash
cd src
python client.py Bob
```

**Anote o ID do Bob** também.

### Enviando Mensagens

Para enviar uma mensagem, use o comando `/msg` com o **ID completo** (32 caracteres) do destinatário:

```
> /msg <ID_COMPLETO_DO_DESTINATARIO> sua mensagem aqui
```

#### Exemplo Prático

Supondo que:
- Alice tem ID: `a1b2c3d4e5f6789012345678abcdef00`
- Bob tem ID: `b8h7g6f5e4d3c2b1fedcba9876543210`

**No terminal da Alice**, digite:
```
> /msg b8h7g6f5e4d3c2b1fedcba9876543210 Oi Bob, tudo bem?
```

**No terminal do Bob** aparecerá:
```
[Mensagem de a1b2c3d4]: Oi Bob, tudo bem?
```

**Bob responde**:
```
> /msg a1b2c3d4e5f6789012345678abcdef00 Tudo otimo Alice!
```

### Comandos Disponíveis

| Comando | Descrição |
|---------|-----------|
| `/msg <id> <texto>` | Envia mensagem para o cliente com o ID especificado |
| `/quit` | Encerra a conexão e sai do cliente |

### Encerrando

- Para parar um cliente: digite `/quit` ou pressione `Ctrl+C`
- Para parar o servidor: pressione `Ctrl+C` no terminal do servidor

---

## Estrutura do Projeto

```
seguranca_final/
├── src/
│   ├── server.py       # Servidor de mensageria
│   ├── client.py       # Cliente de mensageria
│   ├── protocol.py     # Protocolo de handshake
│   ├── crypto.py       # Funções criptográficas
│   └── init_certs.py   # Geração de certificados (opcional)
├── certs/              # Certificados RSA (gerados automaticamente)
│   ├── server.crt
│   └── server.key
└── README.md
```

---

## Segurança Implementada

| Propriedade | Mecanismo | Descrição |
|-------------|-----------|-----------|
| **Confidencialidade** | AES-128-GCM | Mensagens cifradas, ilegíveis sem a chave |
| **Integridade** | Tag GCM | Detecta qualquer alteração na mensagem |
| **Autenticidade** | RSA-2048 + Certificado | Servidor prova sua identidade |
| **Forward Secrecy** | ECDHE (P-256) | Sessões antigas protegidas mesmo se RSA vazar |
| **Anti-Replay** | Contador monotônico | Impede reenvio de mensagens capturadas |

----

##  Link do Vídeo:

https://drive.google.com/file/d/1bViqEkbI2c3VQBeolFu0TEpgOhmQw1kc/view?usp=sharing

----

## ✨ Créditos ✨

Desenvolvido por:

**Maria Beatriz**
**Luana Stanz**
**Anne Carvalho**


💕
