Exemplo de Uso Prático
======================

Este documento fornece exemplos passo-a-passo para testar a aplicação
de mensageria segura.

CENARIO 1: Setup Básico com 2 Clientes
======================================

Preparação:

1. Abrir 3 terminais (Terminal A - Servidor, Terminal B - Cliente Alice,
   Terminal C - Cliente Bob)

Terminal A - Servidor:
```
$ cd /Users/enniax/Documents/seguranca_final/src

# Primeira vez: inicializar certificados
$ python init_certs.py

Output:
Gerando par de chaves RSA-2048...
Certificado salvo: ../certs/server.crt
Chave privada salva: ../certs/server.key
Certificados inicializados com sucesso!

# Iniciar servidor
$ python server.py

Output:
2024-01-20 14:30:00 - Server - INFO - Servidor iniciado em 0.0.0.0:9999
2024-01-20 14:30:00 - Server - INFO - Credenciais salvas: ../certs/server.crt, ../certs/server.key
2024-01-20 14:30:00 - Server - INFO - Servidor aguardando conexões em 0.0.0.0:9999
```

Terminal B - Cliente Alice:
```
$ cd /Users/enniax/Documents/seguranca_final/src
$ python client.py "Alice"

Output:
2024-01-20 14:30:05 - Client - INFO - Cliente inicializado: Alice (a1b2c3d4e5f6g7h8...)
2024-01-20 14:30:05 - Client - INFO - Conectado ao servidor 127.0.0.1:9999
2024-01-20 14:30:05 - Client - INFO - Mensagem inicial enviada (client_id + pk_C)
2024-01-20 14:30:05 - Client - INFO - Resposta do servidor recebida (pk_S + cert + sig + salt)
2024-01-20 14:30:05 - Client - INFO - Assinatura RSA validada e chaves derivadas
2024-01-20 14:30:05 - Client - INFO - Handshake concluído com sucesso

Conectado como: Alice (a1b2c3d4)
Formato de comando: /msg <recipient_id_hex> <mensagem>
Exemplo: /msg a1b2c3d4e5f6g7h8 Oi, tudo bem?
Digite /quit para sair

>
```

Terminal A - Servidor (evento):
```
2024-01-20 14:30:05 - Server - INFO - Nova conexão de ('127.0.0.1', 54321)
2024-01-20 14:30:05 - Server - INFO - Cliente conectado: a1b2c3d4e5f6g7h8
2024-01-20 14:30:05 - Server - INFO - Sessão estabelecida para a1b2c3d4e5f6g7h8
```

Terminal C - Cliente Bob:
```
$ python client.py "Bob"

Output:
2024-01-20 14:30:10 - Client - INFO - Cliente inicializado: Bob (b8h7g6f5e4d3c2b1...)
2024-01-20 14:30:10 - Client - INFO - Conectado ao servidor 127.0.0.1:9999
2024-01-20 14:30:10 - Client - INFO - Handshake concluído com sucesso

Conectado como: Bob (b8h7g6f5e)
>
```

Terminal A - Servidor (evento):
```
2024-01-20 14:30:10 - Server - INFO - Nova conexão de ('127.0.0.1', 54322)
2024-01-20 14:30:10 - Server - INFO - Cliente conectado: b8h7g6f5e4d3c2b1
2024-01-20 14:30:10 - Server - INFO - Sessão estabelecida para b8h7g6f5e4d3c2b1
```

Terminal B - Alice envia mensagem:
```
> /msg b8h7g6f5e4d3c2b1 Ola Bob! Como voce está?

Output:
2024-01-20 14:30:15 - Client - INFO - Mensagem enviada para b8h7g6f5e
```

Terminal A - Servidor roteia:
```
2024-01-20 14:30:15 - Server - INFO - Mensagem de a1b2c3d4e5f6 para b8h7g6f5e4d3c2b1: Ola Bob! Como voce está?
2024-01-20 14:30:15 - Server - INFO - Mensagem roteada para b8h7g6f5e4d3c2b1
```

Terminal C - Bob recebe:
```
[Mensagem de a1b2c3d4]: Ola Bob! Como voce está?
>
```

Terminal C - Bob responde:
```
> /msg a1b2c3d4e5f6g7h8 Ola Alice! Tudo bem!

Output:
2024-01-20 14:30:20 - Client - INFO - Mensagem enviada para a1b2c3d4
```

Terminal B - Alice recebe:
```
[Mensagem de b8h7g6f5e]: Ola Alice! Tudo bem!
```

Encerramento:
```
Terminal B (Alice):
> /quit
2024-01-20 14:30:25 - Client - INFO - Encerrando...

Terminal A - Servidor:
2024-01-20 14:30:25 - Server - INFO - Sessão encerrada: a1b2c3d4e5f6g7h8

Terminal C (Bob):
> /quit
```

CENARIO 2: Teste de Segurança - Validação de Assinatura
========================================================

Objetivo: Demonstrar que assinatura RSA é validada

Passo 1: Corromper o certificado
```
Terminal A (Servidor já rodando):

Terminal X:
$ cd /Users/enniax/Documents/seguranca_final/certs
$ cp server.crt server.crt.backup

# Corromper arquivo
$ echo "INVALID_CERTIFICATE_DATA" > server.crt
```

Passo 2: Tentar conectar novo cliente
```
Terminal B (novo):
$ python client.py "Eve"

Output:
2024-01-20 14:35:00 - Client - INFO - Cliente inicializado: Eve (eve1234567890abc...)
2024-01-20 14:35:00 - Client - INFO - Conectado ao servidor 127.0.0.1:9999
2024-01-20 14:35:00 - Client - ERROR - Validação falhou: Assinatura RSA do servidor inválida!
2024-01-20 14:35:00 - Client - ERROR - Falha ao conectar ao servidor

Resultado: Conexão rejeitada - validação de segurança funcionou!
```

Passo 3: Restaurar certificado
```
Terminal X:
$ mv server.crt.backup server.crt
```

CENARIO 3: Teste de Anti-Replay (Conceitual)
=============================================

Nota: Anti-replay requer captura de pacotes com Wireshark.

Conceito:
1. Capturar frame de mensagem entre cliente e servidor
2. Tentar re-enviar o mesmo frame
3. Servidor valida: seq_no <= seq_recv -> REJEITA

Demonstração (via log):
```
Mensagem 1 enviada: seq_no=1
Servidor: seq_recv=0, novo=1 > 0 OK, seq_recv=1

Mensagem 2 enviada: seq_no=2
Servidor: seq_recv=1, novo=2 > 1 OK, seq_recv=2

Ataque de Replay: Re-enviar seq_no=1
Servidor: seq_recv=2, novo=1 <= 2 REJEITA
Log: "Ataque de replay detectado"
```

CENARIO 4: Teste com 3+ Clientes Simultâneos
=============================================

Terminal A - Servidor:
```
$ python server.py
```

Terminal B - Alice:
```
$ python client.py "Alice"
Conectado como: Alice (a1b2c3d4)
>
```

Terminal C - Bob:
```
$ python client.py "Bob"
Conectado como: Bob (b8h7g6f5e)
>
```

Terminal D - Charlie:
```
$ python client.py "Charlie"
Conectado como: Charlie (c1c2c3c4)
>
```

Teste de roteamento múltiplo:
```
Terminal B (Alice):
> /msg b8h7g6f5e4d3c2b1 Ola Bob!
> /msg c1c2c3c4e5f6g7h8 Ola Charlie!

Terminal C (Bob):
[Mensagem de a1b2c3d4]: Ola Bob!
> /msg a1b2c3d4e5f6g7h8 Ola Alice! Ola Charlie tmb!
> /msg c1c2c3c4e5f6g7h8 Ola Charlie!

Terminal D (Charlie):
[Mensagem de a1b2c3d4]: Ola Charlie!
[Mensagem de b8h7g6f5e]: Ola Charlie!
> /msg a1b2c3d4e5f6g7h8 Ola Alice!
> /msg b8h7g6f5e4d3c2b1 Ola Bob!

Terminal B (Alice):
[Mensagem de b8h7g6f5e]: Ola Alice! Ola Charlie tmb!
[Mensagem de c1c2c3c4]: Ola Alice!

Terminal A (Servidor):
- Múltiplas conexões ativas
- Roteamento funciona para todos
```

CENARIO 5: Monitoramento com Wireshark (Avançado)
=================================================

Objetivo: Mostrar que trafego está criptografado

Passo 1: Iniciar captura Wireshark
```
$ sudo wireshark

1. Selecionar interface de rede
2. Clicar "Start Capturing"
3. Usar filtro: "tcp.port == 9999"
```

Passo 2: Estabelecer conexão e enviar mensagem
```
Terminal A: $ python server.py
Terminal B: $ python client.py "Alice"
Terminal C: $ python client.py "Bob"
Terminal B: > /msg b8h7g6f5e Ola!
```

Passo 3: Analisar trafego no Wireshark
```
Esperado:
1. TCP SYN (Alice -> Servidor)
2. TCP SYN-ACK
3. TCP ACK
4. Dados aleatórios (inicial_message do handshake)
   - Frame de 81 bytes
   - Contém client_id + pk_C
   - Sem visibilidade do conteúdo específico (sem criptografia neste frame)
   
5. Dados aleatórios (resposta do handshake)
   - Frame de ~653 bytes
   - Contém pk_S, certificado, assinatura, salt
   - Sem visibilidade
   
6. Dados aleatórios (mensagem criptografada)
   - Frame de 52+ bytes
   - Contém nonce + IDs + seq_no + ciphertext
   - Nonce e ciphertext parecem aleatórios
   - Impossível distinguir padrão

Recurso no Wireshark:
- Right-click no frame -> Follow -> TCP Stream
- Ver bytes em hex
- Observar: nenhum texto legível
- Observar: padrão aleatório
```

CENARIO 6: Teste de Integridade (Conceitual)
=============================================

Objetivo: Demonstrar que alteração é detectada

Conceito:
1. Capturar frame de mensagem
2. Modificar um byte do ciphertext
3. Cliente tenta decifrar
4. GCM valida tag -> FALHA (tag não coincide)
5. Mensagem é rejeitada

Teste manual (pseudo-código):
```
# Frame capturado (hex):
frame = "a1b2c3d4e5f6g7h8... [52 bytes header] ... [nonce] ... [ciphertext+tag]"

# Modificar 1 byte do ciphertext
frame_corrupted = frame[:-17] + "00" + frame[-15:]

# Tentar decifrar
plaintext = decrypt(key_s2c, frame_corrupted)

# Resultado esperado:
# plaintext == None (falha de autenticidade)
# ou exceção capturada
```

CENARIO 7: Teste de Sigilo Perfeito (Conceitual)
================================================

Objetivo: Demonstrar que compromentimento futuro de RSA não afeta sessões antigas

Cenário hipotético:
1. Sessão 1 (dia 1): Cliente A <-> Servidor
   - ECDHE_1 (sk_A1, pk_A1) do cliente
   - ECDHE_1 (sk_S1, pk_S1) do servidor
   - Z_1 = ECDH(sk_A1, pk_S1) = ECDH(sk_S1, pk_A1)
   - Chaves derivadas de Z_1

2. Sessão 2 (dia 2): Cliente B <-> Servidor
   - ECDHE_2 (sk_B2, pk_B2) do cliente
   - ECDHE_2 (sk_S2, pk_S2) do servidor
   - Z_2 = ECDH(sk_B2, pk_S2) = ECDH(sk_S2, pk_B2)
   - Chaves derivadas de Z_2

3. Dia 30: RSA privada do servidor é comprometida

Impacto:
- Atacante consegue assinar dados com RSA privada
- Atacante PODE fazer MITM em novas conexões
- Atacante NÃO consegue decifrar sessões antigas
- Por quê? Porque chaves vieram de ECDHE, não de RSA
- Z_1 e Z_2 não dependem de RSA
- Criptografia de dados não depende de RSA (apenas a autenticação)

Consequência: Forward Secrecy implementado com sucesso!
```

Interpretação de Resultados
============================

Sucesso esperado:
✓ Servidor inicializa sem erros
✓ Cliente conecta e faz handshake
✓ Assinatura RSA é validada
✓ Chaves são derivadas
✓ Mensagem é cifrada com AES-GCM
✓ Destinatário recebe e decifra
✓ Anti-replay funciona
✓ Integridade é validada (tag GCM)

Erros comuns:

1. "Erro: Módulo cryptography não encontrado"
   Solução: pip install cryptography

2. "Erro: Certificado não encontrado"
   Solução: Rodar init_certs.py na pasta src/

3. "Erro: Porta 9999 em uso"
   Solução: Matar processo anterior ou usar porta diferente

4. "Erro: Assinatura inválida"
   Solução: Certificado corrompido, regenerar com init_certs.py

5. "Cliente conecta mas não recebe mensagens"
   Solução: Verificar se ambos os clientes estão conectados
           Verificar UUID na mensagem /msg

Métricas de Sucesso
===================

Confidencialidade:
[ ] Wireshark mostra dados aleatórios
[ ] Sem padrão detectável
[ ] Mesmo capturando, sem chave não consegue ler

Integridade:
[ ] Modificar 1 byte do ciphertext
[ ] Mensagem é rejeitada
[ ] Log mostra "Falha na autenticação"

Autenticidade:
[ ] Certificado corrompido -> conexão falha
[ ] Certificado válido -> sucesso
[ ] RSA valida assinatura corretamente

Sigilo Perfeito:
[ ] Sessão A tem chaves_A
[ ] Sessão B tem chaves_B
[ ] Não há correlação entre chaves

Anti-Replay:
[ ] seq_no aumenta a cada mensagem
[ ] Servidor valida seq_no > seq_recv
[ ] Mensagem antiga rejeitada

Roteamento:
[ ] Múltiplos clientes conectados
[ ] Servidor roteia para cliente correto
[ ] Cada cliente recebe apenas suas mensagens

Documentação de Teste
====================

Ao testar, registre:
1. Data e hora
2. Configuração (host, port)
3. Número de clientes
4. Número de mensagens
5. Duração da sessão
6. Qualquer erro observado
7. Logs gerados

Exemplo:
```
Teste: Validação de Funcionamento Básico
Data: 2024-01-20
Hora: 14:30
Configuração: localhost:9999, 2 clientes
Resultado:
- Servidor: OK
- Cliente 1 (Alice): Conectou e fez handshake com sucesso
- Cliente 2 (Bob): Conectou e fez handshake com sucesso
- Troca de mensagens: 5 mensagens trocadas com sucesso
- Encerramento: Ambos os clientes fecharam conexão
Duração: ~2 minutos
Erros: Nenhum
Observação: Tudo funcionou como esperado
```
