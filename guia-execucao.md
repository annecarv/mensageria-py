Guia Completo de Execucao
=========================

Sistema Operacional: macOS / Linux
Python: 3.8+
Dependências: cryptography

Estrutura do Projeto
====================

seguranca_final/
├── README.md                    # Documentação geral
├── TECH_CRYPTO.md              # Componentes de criptografia
├── TECH_PROTOCOL.md            # Protocolo de handshake
├── TECH_SERVER_CLIENT.md       # Servidor e cliente
├── VIDEO_PRESENTATION.md       # Guia de apresentação em vídeo
├── PRACTICAL_EXAMPLES.md       # Exemplos práticos de uso
├── src/
│   ├── crypto.py               # Implementação de criptografia
│   ├── protocol.py             # Protocolo de handshake e estruturas
│   ├── server.py               # Servidor de mensageria
│   ├── client.py               # Cliente de mensageria
│   └── init_certs.py           # Inicialização de certificados
├── certs/
│   ├── server.crt              # Certificado RSA do servidor (gerado)
│   └── server.key              # Chave privada RSA (gerado)
└── logs/
    └── (logs de execução)

PASSO 1: Instalacao de Dependencias
===================================

Abrir terminal:

```bash
# Atualizar pip (opcional)
python3 -m pip install --upgrade pip

# Instalar cryptography
pip install cryptography

# Verificar instalação
python3 -c "import cryptography; print(cryptography.__version__)"

Esperado: Exibe versão do cryptography (ex: 41.0.0 ou superior)
```

Se receber erro de permissão:
```bash
# Usar --user flag
pip install --user cryptography
```

PASSO 2: Inicializacao de Certificados
======================================

Terminal (primeira vez apenas):

```bash
cd /Users/enniax/Documents/seguranca_final/src

python3 init_certs.py
```

Output esperado:
```
Gerando par de chaves RSA-2048...
Certificado salvo: ../certs/server.crt
Chave privada salvo: ../certs/server.key
Certificados inicializados com sucesso!
```

Verifica:
```bash
ls -la ../certs/

total 16
-rw-r--r--  1 user  group  294 Jan 20 14:00 server.crt
-rw-r--r--  1 user  group  1704 Jan 20 14:00 server.key
```

Resultado: Arquivos criados em /Users/enniax/Documents/seguranca_final/certs/

PASSO 3: Iniciar Servidor
=========================

Terminal 1 (Servidor):

```bash
cd /Users/enniax/Documents/seguranca_final/src

python3 server.py
```

Output esperado:
```
2024-01-20 14:30:00,123 - Server - INFO - Servidor iniciado em 0.0.0.0:9999
2024-01-20 14:30:00,124 - Server - INFO - Credenciais salvas: ../certs/server.crt, ../certs/server.key
2024-01-20 14:30:00,125 - Server - INFO - Servidor aguardando conexões em 0.0.0.0:9999
```

Status: Servidor está rodando e aguardando conexões.
Manter este terminal aberto.

PASSO 4: Conectar Primeiro Cliente
==================================

Terminal 2 (novo):

```bash
cd /Users/enniax/Documents/seguranca_final/src

python3 client.py "Alice"
```

Output esperado:
```
2024-01-20 14:30:05,123 - Client - INFO - Cliente inicializado: Alice (a1b2c3d4e5f6...)
2024-01-20 14:30:05,124 - Client - INFO - Conectado ao servidor 127.0.0.1:9999
2024-01-20 14:30:05,125 - Client - INFO - Mensagem inicial enviada (client_id + pk_C)
2024-01-20 14:30:05,126 - Client - INFO - Resposta do servidor recebida (pk_S + cert + sig + salt)
2024-01-20 14:30:05,127 - Client - INFO - Assinatura RSA validada e chaves derivadas
2024-01-20 14:30:05,128 - Client - INFO - Handshake concluído com sucesso

Conectado como: Alice (a1b2c3d4)
Formato de comando: /msg <recipient_id_hex> <mensagem>
Exemplo: /msg b8h7g6f5e4d3c2b1 Ola, tudo bem?
Digite /quit para sair

>
```

Observar também no Terminal 1 (Servidor):
```
2024-01-20 14:30:05,123 - Server - INFO - Nova conexão de ('127.0.0.1', 54321)
2024-01-20 14:30:05,124 - Server - INFO - Cliente conectado: a1b2c3d4e5f6g7h8
2024-01-20 14:30:05,125 - Server - INFO - Sessão estabelecida para a1b2c3d4e5f6g7h8
```

Anotar UUID de Alice: a1b2c3d4e5f6g7h8

PASSO 5: Conectar Segundo Cliente
=================================

Terminal 3 (novo):

```bash
cd /Users/enniax/Documents/seguranca_final/src

python3 client.py "Bob"
```

Output esperado:
```
2024-01-20 14:30:10,123 - Client - INFO - Cliente inicializado: Bob (b8h7g6f5e4d3c2b1...)
2024-01-20 14:30:10,124 - Client - INFO - Conectado ao servidor 127.0.0.1:9999
2024-01-20 14:30:10,125 - Client - INFO - Handshake concluído com sucesso

Conectado como: Bob (b8h7g6f5e)
>
```

Observar no Terminal 1 (Servidor):
```
2024-01-20 14:30:10,123 - Server - INFO - Nova conexão de ('127.0.0.1', 54322)
2024-01-20 14:30:10,124 - Server - INFO - Cliente conectado: b8h7g6f5e4d3c2b1
2024-01-20 14:30:10,125 - Server - INFO - Sessão estabelecida para b8h7g6f5e4d3c2b1
```

Anotar UUID de Bob: b8h7g6f5e4d3c2b1

PASSO 6: Trocar Mensagens
=========================

Terminal 2 (Alice):

```
> /msg b8h7g6f5e4d3c2b1 Ola Bob! Como voce está?
```

Output:
```
2024-01-20 14:30:15,123 - Client - INFO - Mensagem enviada para b8h7g6f5e
```

Terminal 1 (Servidor):
```
2024-01-20 14:30:15,123 - Server - INFO - Mensagem de a1b2c3d4e5f6 para b8h7g6f5e4d3c2b1: Ola Bob! Como voce está?
2024-01-20 14:30:15,124 - Server - INFO - Mensagem roteada para b8h7g6f5e4d3c2b1
```

Terminal 3 (Bob):
```
[Mensagem de a1b2c3d4]: Ola Bob! Como voce está?
>
```

Bob responde:

Terminal 3 (Bob):
```
> /msg a1b2c3d4e5f6g7h8 Ola Alice! Tudo bem!
```

Terminal 2 (Alice):
```
[Mensagem de b8h7g6f5e]: Ola Alice! Tudo bem!
>
```

Sucesso: Comunicação bidirecional funcionando!

PASSO 7: Encerrar Sessao
========================

Terminal 2 (Alice):
```
> /quit
2024-01-20 14:30:20,123 - Client - INFO - Encerrando...

Sair automaticamente
```

Terminal 1 (Servidor):
```
2024-01-20 14:30:20,123 - Server - INFO - Sessão encerrada: a1b2c3d4e5f6g7h8
```

Terminal 3 (Bob):
```
> /quit
```

Terminal 1 (Servidor):
```
2024-01-20 14:30:21,123 - Server - INFO - Sessão encerrada: b8h7g6f5e4d3c2b1
```

Para finalizar servidor (Terminal 1):
```
Ctrl + C

Output:
^C
(Interrupção do teclado)
Servidor encerrado
```

Troubleshooting
===============

PROBLEMA: ModuleNotFoundError: No module named 'cryptography'

Solução:
```bash
pip install cryptography

ou

pip3 install cryptography

ou

python -m pip install cryptography
```

---

PROBLEMA: Address already in use: ('0.0.0.0', 9999)

Causa: Porta 9999 já está em uso.

Solução 1: Esperar 30 segundos e tentar novamente
Solução 2: Mudar porta em server.py linha ~260:
```python
server = SecureMessagingServer(host="0.0.0.0", port=9998)  # Porta diferente
```
E em client.py linha ~70:
```python
server_port=9998  # Mesma porta
```

Solução 3: Matar processo na porta:
```bash
# macOS/Linux
lsof -i :9999
kill -9 <PID>
```

---

PROBLEMA: Client conecta mas não recebe mensagens

Causa: UUID incorreto na mensagem /msg

Solução:
1. Verificar UUID correto na hora que cliente conecta
2. Alice conecta: "(a1b2c3d4)" <-- este é o UUID
3. Usar exatamente este UUID (sem parênteses):
```
> /msg a1b2c3d4e5f6g7h8 Mensagem
```

---

PROBLEMA: Validação falhou: Assinatura RSA do servidor inválida

Causa: Certificado corrompido ou em local errado

Solução:
```bash
# Deletar certificados
rm /Users/enniax/Documents/seguranca_final/certs/server.crt
rm /Users/enniax/Documents/seguranca_final/certs/server.key

# Regenerar
cd /Users/enniax/Documents/seguranca_final/src
python3 init_certs.py

# Reiniciar servidor e clientes
```

---

PROBLEMA: Erro de permissão ao salvar certificados

Causa: Pasta certs não tem permissão de escrita

Solução:
```bash
# Verificar permissões
ls -ld /Users/enniax/Documents/seguranca_final/certs/

# Se necessário, dar permissão
chmod 755 /Users/enniax/Documents/seguranca_final/certs/
```

---

PROBLEMA: Servidor não conecta: Connection refused

Causa: Servidor não está rodando

Solução: Iniciar servidor primeiro em Terminal 1

---

PROBLEMA: Cliente conecta mas fecha imediatamente

Causa: Erro no handshake (logs podem mostrar detalhes)

Solução:
1. Verificar certificado existe
2. Verificar servidor está rodando
3. Tentar com verbose mode (adicionar prints)

Opcoes de Linha de Comando
===========================

SERVIDOR:

python3 server.py [host] [port]

Exemplos:
```
python3 server.py                    # localhost:9999 (apenas)
python3 server.py 0.0.0.0 9999       # Todos interfaces:9999
python3 server.py 127.0.0.1 8888     # localhost:8888
```

CLIENTE:

python3 client.py [username] [host] [port] [cert_path]

Exemplos:
```
python3 client.py "Alice"                    # Alice com defaults
python3 client.py "Bob" 192.168.1.100 9999   # Bob em IP específico
python3 client.py "Charlie" localhost 8888 /path/to/cert.crt
```

Verificacao de Status
====================

Para verificar se sistema está funcionando:

1. Servidor rodando:
```bash
# Em outro terminal
lsof -i :9999

COMMAND    PID USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
python3  12345 user   3u  IPv4 0x12345678      0t0  TCP *:9999 (LISTEN)
```

2. Conexões ativas:
```bash
netstat -an | grep 9999

tcp4       0      0 127.0.0.1.9999         127.0.0.1.54321        ESTABLISHED
tcp4       0      0 127.0.0.1.9999         127.0.0.1.54322        ESTABLISHED
```

3. Certificados existem:
```bash
ls -la /Users/enniax/Documents/seguranca_final/certs/

-rw-r--r--  server.crt
-rw-r--r--  server.key
```

Limpeza
=======

Para resetar o sistema:

```bash
# 1. Parar todos os processos
# (Ctrl+C em todos os terminais)

# 2. Remover sessões antigas (opcional)
rm /Users/enniax/Documents/seguranca_final/certs/server.* 

# 3. Limpar logs (opcional)
rm -rf /Users/enniax/Documents/seguranca_final/logs/*

# 4. Recomecar do PASSO 2
```

Documentos de Referencia
=======================

Depois de tudo funcionando, ler:

1. README.md - Visão geral do projeto
2. TECH_CRYPTO.md - Componentes de criptografia
3. TECH_PROTOCOL.md - Protocolo de handshake
4. TECH_SERVER_CLIENT.md - Implementação do servidor e cliente
5. VIDEO_PRESENTATION.md - Como apresentar em vídeo
6. PRACTICAL_EXAMPLES.md - Exemplos avançados e testes

Resumo da Arquitetura
====================

Fluxo de Dados:

Cliente A
   |
   | TCP: [client_id] + [pk_C]
   |
   v
Servidor
   |
   | TCP: [pk_S] + [cert] + [sig] + [salt]
   |
   v
Cliente A
   | (Ambos derivam chaves de sessão)
   |
   | Handshake completo
   |
   v

Cliente A                 Servidor                 Cliente B
   |                         |                         |
   | Cifra com key_c2s_A     |                         |
   |--[nonce+IDs+seq+cipher]--->                      |
   |                         |                         |
   |                    Decifra                       |
   |                    Valida                         |
   |                    Re-cifra com key_s2c_B        |
   |                         |--[novo frame]--------->|
   |                         |                    Decifra
   |                         |                    Valida
   |                         |                    Exibe
   |                         |     Cifra com key_c2s_B
   |                         |<--[novo frame]---------|
   |                    Roteia                        |
   |<--[re-cipher frame]---  |
   |
   Decifra
   Valida
   Exibe

Segurança:
- Nenhuma chave em trânsito
- Cada direção, chave diferente
- Anti-replay via seq_no
- Integridade via tag GCM
- Autenticidade via RSA
- Forward secrecy via ECDHE

Proximas Etapas (Opcional)
==========================

1. Persistência:
   - Salvar mensagens em banco de dados
   - Recuperar histórico quando cliente reconecta

2. Renegociação de chaves:
   - A cada 1000 mensagens, derivar novas chaves
   - Melhor forward secrecy

3. Suporte a grupos:
   - Múltiplos clientes em uma conversa
   - Servidor retransmite para todos

4. Compressão:
   - Reduzir tamanho de payload
   - Melhor performance

5. Rate limiting:
   - Prevenir spam
   - Throttling de clientes

6. Monitoramento:
   - Métricas de performance
   - Alertas de erro

Conclusao
=========

Sistema está pronto para uso. Testar seguindo passos acima.

Para problemas, ler seção Troubleshooting ou consultar documentação técnica.

Sucesso!
