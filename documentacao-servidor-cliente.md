Documentacao Tecnica - Servidor e Cliente
===========================================

Este documento descreve a implementação do servidor e cliente da aplicação
de mensageria segura.

MODULO: server.py
=================

Responsabilidades:
- Gerenciar múltiplas conexões de clientes
- Executar handshake com cada cliente
- Validar mensagens (anti-replay, autenticidade)
- Rotear mensagens entre clientes
- Manter tabela de sessões segura

====================
Classe: ClientSession
====================

Responsabilidade: Representar sessão autenticada de um cliente.

Estrutura:
```
ClientSession {
    client_id: bytes (16B)           - UUID do cliente
    reader: asyncio.StreamReader     - Leitor TCP
    writer: asyncio.StreamWriter     - Escritor TCP
    key_c2s: bytes (16B)             - Chave cliente->servidor
    key_s2c: bytes (16B)             - Chave servidor->cliente
    seq_recv: int                    - Último seq_no recebido
    seq_send: int                    - Próximo seq_no a enviar
    salt: bytes (32B)                - Salt do HKDF
}
```

Uso:
- Cada cliente conectado tem uma instância
- Stored em dictionary: sessions[client_id] = ClientSession(...)
- Removida quando cliente desconecta

====================
Classe: SecureMessagingServer
====================

Responsabilidade: Gerenciar servidor de mensageria, conexões e roteamento.

Atributos:

1. host (str)
   Endereço de bind do servidor. Padrão: "127.0.0.1"
   Em produção seria "0.0.0.0" para aceitar conexões externas.

2. port (int)
   Porta de escuta. Padrão: 9999

3. sessions (Dict[bytes, ClientSession])
   Tabela de sessões ativas.
   Chave: client_id (16 bytes)
   Valor: ClientSession com dados da conexão

4. rsa_signature (RSASignature)
   Objeto contendo par de chaves RSA do servidor.
   Inicializado uma vez na startup.
   Compartilhado entre todos os handshakes.

5. handshake (ServerHandshake)
   Objeto para gerenciar handshakes.
   Inicializado com rsa_signature.

Métodos:

1. __init__(host="127.0.0.1", port=9999)
   Inicializa servidor.
   
   Ações:
   - Armazena host e port
   - Cria dictionary sessions vazio
   - Gera novo par RSA-2048
   - Cria objeto ServerHandshake
   - Log: "Servidor iniciado em {host}:{port}"

2. save_credentials(cert_path, key_path)
   Salva credenciais RSA em arquivos.
   
   Ações:
   1. Escrever certificado em cert_path (PEM)
   2. Escrever chave privada em key_path (PEM)
   3. Log: "Credenciais salvas"
   
   Uso: Na startup, garantir que certificados estão disponíveis.

3. handle_client(reader, writer) [async]
   Trata conexão de um cliente.
   
   Fluxo:
   
   a) Log de conexão
   b) Handshake:
      - Receber mensagem inicial do cliente (81 bytes)
      - Parse client_id + pk_C
      - Gerar resposta de handshake
      - Enviar resposta
      - Derivar chaves de sessão
      - Registrar sessão em self.sessions
      - Log: "Sessão estabelecida"
   
   c) Loop de mensagens:
      - Receber frame (header 48B + size 4B + dados)
      - Validar seq_no > seq_recv (anti-replay)
      - Decifrar com key_c2s
      - Validar tag GCM (falha se inválida)
      - Rotear com _route_message()
   
   d) Tratamento de erros:
      - Capturar asyncio.IncompleteReadError (client disconnected)
      - Capturar exceções gerais
      - Log de erro
   
   e) Cleanup (finally block):
      - Remover sessão de self.sessions
      - Fechar conexão TCP
      - Log: "Sessão encerrada"
   
   Exceções tratadas:
   - asyncio.IncompleteReadError: Desconexão normal do cliente
   - Exception genérica: Erros de processamento

4. _parse_frame_with_size(data) -> MessageFrame [private]
   Desserializa frame com tamanho prefixado.
   
   Formato esperado:
   [nonce (12B)] + [sender_id (16B)] + [recipient_id (16B)] +
   [seq_no (8B)] + [size (4B)] + [ciphertext_with_tag]
   
   Parse:
   - nonce = data[0:12]
   - sender_id = data[12:28]
   - recipient_id = data[28:44]
   - seq_no = data[44:52] as int big-endian
   - ciphertext_with_tag = data[56:] (pula os 4B de size)
   
   Retorna: MessageFrame

5. _route_message(frame, plaintext, sender_session) [async, private]
   Roteia mensagem para cliente destinatário.
   
   Entrada:
   - frame: Frame recebido do remetente
   - plaintext: Dados descriptografados
   - sender_session: Sessão do remetente
   
   Processo:
   
   1. Obter recipient_id = frame.recipient_id
   
   2. Verificar se destinatário está online:
      if recipient_id not in self.sessions:
          Log: "Destinatário não encontrado"
          return
   
   3. Obter sessão do destinatário
   
   4. Cifrar mensagem com key_s2c do destinatário:
      new_frame = MessageCrypto.encrypt_message(
          key=recipient_session.key_s2c,
          sender_id=frame.sender_id,
          recipient_id=frame.recipient_id,
          seq_no=recipient_session.seq_send,
          plaintext=plaintext
      )
   
   5. Incrementar contador do destinatário:
      recipient_session.seq_send += 1
   
   6. Serializar novo frame com tamanho:
      message_bytes = [header (48B)] + [size (4B)] + [ciphertext]
   
   7. Enviar ao destinatário:
      recipient_session.writer.write(message_bytes)
      await recipient_session.writer.drain()
   
   8. Log: "Mensagem roteada para {recipient_id}"
   
   Tratamento de erros:
   - Try/except ao enviar
   - Log se falhar

6. start() [async]
   Inicia servidor aguardando conexões.
   
   Ações:
   1. Criar servidor TCP com asyncio.start_server()
   2. Bind em (self.host, self.port)
   3. Callback: self.handle_client para cada conexão
   4. Log: "Servidor aguardando conexões"
   5. Aguardar indefinidamente com serve_forever()

Fluxo de Execução

```
Startup:
1. server = SecureMessagingServer(host="0.0.0.0", port=9999)
2. server.save_credentials("../certs/server.crt", "../certs/server.key")
3. asyncio.run(server.start())

Conexão de Cliente:
1. Cliente conecta em TCP
2. Callback handle_client é disparado
3. Handshake executado
4. Sessão registrada
5. Loop de mensagens começa

Troca de Mensagens:
1. Cliente envia mensagem cifrada
2. Servidor decifra e valida
3. Servidor roteia para outro cliente
4. Cliente destinatário recebe

Desconexão:
1. Cliente fecha conexão TCP
2. asyncio.IncompleteReadError é gerado
3. Sessão é removida
4. Conexão é fechada
```

====================
MODULO: client.py
=================

Responsabilidades:
- Conectar ao servidor
- Executar handshake
- Enviar mensagens
- Receber mensagens em background
- Interface interativa com usuário

====================
Classe: SecureMessagingClient
====================

Responsabilidade: Gerenciar cliente de mensageria.

Atributos:

1. username (str)
   Nome do usuário para display.

2. client_id (bytes, 16B)
   UUID gerado aleatoriamente no __init__.
   Usado para identificar cliente no protocolo.

3. server_host (str)
   Endereço do servidor. Padrão: "127.0.0.1"

4. server_port (int)
   Porta do servidor. Padrão: 9999

5. server_cert_path (str)
   Caminho do certificado RSA do servidor.
   Padrão: "../certs/server.crt"

6. reader (asyncio.StreamReader ou None)
   Leitor TCP após conexão. None se desconectado.

7. writer (asyncio.StreamWriter ou None)
   Escritor TCP após conexão. None se desconectado.

8. key_c2s (bytes ou None)
   Chave para enviar ao servidor. None antes do handshake.

9. key_s2c (bytes ou None)
   Chave para receber do servidor. None antes do handshake.

10. seq_send (int)
    Contador de sequência para envio. Começa em 0.

11. seq_recv (int)
    Contador de sequência para recepção. Começa em 0.

Métodos:

1. __init__(username, server_host, server_port, server_cert_path)
   Inicializa cliente.
   
   Ações:
   - Armazena parâmetros
   - Gera client_id com uuid.uuid4().bytes
   - Inicializa reader/writer como None
   - Inicializa key_c2s/key_s2c como None
   - Inicializa seq_send=0, seq_recv=0
   - Log: "Cliente inicializado"

2. connect() -> bool [async]
   Conecta ao servidor e executa handshake.
   
   Retorno: True se sucesso, False se falha.
   
   Fluxo:
   
   a) Conectar TCP:
      self.reader, self.writer = await asyncio.open_connection(
          self.server_host, self.server_port
      )
      Log: "Conectado ao servidor"
   
   b) Handshake:
      handshake = ClientHandshake(self.client_id)
      initial_message = handshake.get_initial_message()
      self.writer.write(initial_message)
      await self.writer.drain()
      Log: "Mensagem inicial enviada"
   
   c) Receber resposta:
      response_header = await self.reader.readexactly(4)
      response_size = int.from_bytes(response_header, 'big')
      response_data = await self.reader.readexactly(response_size)
      response = HandshakeResponse.from_bytes(response_data)
      Log: "Resposta recebida"
   
   d) Validação:
      Carregar certificado de server_cert_path
      Chamar handshake.process_handshake_response()
      Se ValueError, log error e retornar False
   
   e) Derivação de chaves:
      self.key_c2s, self.key_s2c, _ = resultado do handshake
      Log: "Handshake concluído"
      retornar True
   
   Exceções: Capturas e log, retorna False

3. send_message(recipient_username, recipient_id, message) -> bool [async]
   Envia mensagem criptografada ao servidor.
   
   Entrada:
   - recipient_username: Nome para display
   - recipient_id: UUID do destinatário (16 bytes)
   - message: Texto da mensagem
   
   Retorno: True se enviado, False se falha.
   
   Validação:
   - Verificar se conectado (writer is None -> False)
   - Verificar se key_c2s derivada (key_c2s is None -> False)
   
   Processo:
   
   1. Cifrar mensagem:
      frame = MessageCrypto.encrypt_message(
          key=self.key_c2s,
          sender_id=self.client_id,
          recipient_id=recipient_id,
          seq_no=self.seq_send,
          plaintext=message.encode('utf-8')
      )
   
   2. Incrementar contador:
      self.seq_send += 1
   
   3. Serializar com tamanho:
      frame_bytes = [header] + [size] + [ciphertext]
   
   4. Enviar:
      self.writer.write(frame_bytes)
      await self.writer.drain()
      Log: "Mensagem enviada"
      retornar True
   
   Exceções: Try/except, log error, retornar False

4. receive_messages() [async]
   Loop contínuo para receber mensagens do servidor.
   
   Validação prévia:
   - reader is None -> log warning, retornar
   - key_s2c is None -> log warning, retornar
   
   Loop principal (while True):
   
   a) Receber header (48 bytes):
      header = await self.reader.readexactly(48)
   
   b) Receber tamanho (4 bytes):
      size_data = await self.reader.readexactly(4)
      ciphertext_size = int.from_bytes(size_data, 'big')
   
   c) Receber ciphertext:
      ciphertext_with_tag = await self.reader.readexactly(ciphertext_size)
   
   d) Reconstruir frame:
      frame = self._parse_frame_with_size(header + size_data + ciphertext)
   
   e) Validar anti-replay:
      if frame.seq_no <= self.seq_recv:
          Log: "Ataque de replay"
          continue
      self.seq_recv = frame.seq_no
   
   f) Decifrar:
      plaintext = MessageCrypto.decrypt_message(self.key_s2c, frame)
      if plaintext is None:
          Log: "Falha de autenticação"
          continue
   
   g) Exibir mensagem:
      message_text = plaintext.decode('utf-8')
      sender_id = frame.sender_id.hex()
      Log e print: "[{sender_id}]: {message_text}"
   
   Exceções:
   - asyncio.IncompleteReadError: Log info, break
   - Exception genérica: Log error

5. _parse_frame_with_size(data) -> MessageFrame [private]
   Desserializa frame recebido.
   
   Mesmo formato do servidor.

6. interactive_session() [async]
   Inicia sessão interativa com usuário.
   
   Ações iniciais:
   - Print informações de conexão
   - Iniciar task de recebimento em background
      receive_task = asyncio.create_task(self.receive_messages())
   
   Loop principal (while True):
   
   a) Ler input não-bloqueante:
      user_input = await asyncio.get_event_loop().run_in_executor(
          None, input, "> "
      )
   
   b) Comando de saída:
      if user_input.lower() == "/quit":
          break
   
   c) Comando de mensagem:
      if user_input.startswith("/msg "):
          parts = user_input[5:].split(" ", 1)
          if len(parts) >= 2:
              recipient_id_str = parts[0]
              message = parts[1]
              
              try:
                  recipient_id = bytes.fromhex(recipient_id_str)
                  if len(recipient_id) != 16:
                      Print erro
                      continue
                  
                  await self.send_message(
                      recipient_id_str[:8],
                      recipient_id,
                      message
                  )
              except ValueError:
                  Print erro
   
   Finalização (finally):
   - Cancelar receive_task
   - Fechar conexão writer
   - await writer.wait_closed()

Fluxo de Execução

```
Startup:
1. client = SecureMessagingClient(username="Alice")
   Log mostra client_id
2. connected = await client.connect()
3. await client.interactive_session()

Conexão:
1. Conectar TCP ao servidor
2. Enviar initial_message
3. Receber response
4. Validar assinatura RSA
5. Derivar chaves
6. Log sucesso

Sessão Interativa:
1. Task de recebimento começa em background
2. Loop principal aguarda input do usuário
3. Usuário digita "/msg <uuid> <mensagem>"
4. Mensagem é cifrada e enviada
5. Task de recebimento processa respostas

Recebimento (background):
1. Aguarda mensagem do servidor
2. Decifra e valida autenticidade
3. Exibe no terminal
```

Integração Cliente-Servidor
=============================

Fluxo de conexão:

Cliente:
1. secureMessagingClient.connect()
2. Envia: [client_id] + [pk_C]

Servidor:
1. handle_client() é disparado
2. Recebe mensagem inicial
3. Processa e gera resposta

Cliente:
1. Recebe resposta
2. Valida assinatura
3. Deriva chaves

Servidor:
1. Deriva mesmas chaves
2. Registra sessão

Fluxo de mensagem:

Cliente A envia para B:
1. client_a.send_message(client_b_id, "Ola!")
2. Cifra com key_c2s_A
3. Envia ao servidor

Servidor roteia:
1. Decifra com key_c2s_A
2. Valida autenticidade
3. Re-cifra com key_s2c_B
4. Envia para Cliente B

Cliente B recebe:
1. Aguarda em receive_messages()
2. Recebe mensagem roteada
3. Decifra com key_s2c_B
4. Valida autenticidade
5. Exibe no terminal

Segurança de Implementação
===========================

Boas práticas implementadas:

1. Nenhuma chave em logs
   - seq_no, UUIDs são logados
   - Chaves, nonces, plaintexts não

2. Validação de entrada
   - Tamanho mínimo de frames
   - Parsing seguro de UUID

3. Tratamento robusto de erros
   - Exceções criptográficas capturadas
   - Desconexões tratadas graciosamente

4. Separação de chaves
   - key_c2s e key_s2c são diferentes
   - Impossível reutilizar chave em direção oposta

5. Contadores monotônicos
   - seq_no deve aumentar
   - Replay detection obrigatório

6. Asyncio para concorrência segura
   - Sem threads (sem race conditions)
   - Operações criptográficas sequenciais

Limitações Atuais
=================

1. Certificado autoassinado
   - Sem validação de PKI
   - Vulnerável a MITM se certificado não for pinado

2. Sem persistência
   - Histórico não é salvo
   - Cliente reconectando precisa re-fazer handshake

3. Sem renegociação de chaves
   - Mesmas chaves para toda sessão
   - Ideal seria rotacionar após N mensagens

4. Mensagens síncronas
   - Sem suporte a grupos
   - Apenas ponto-a-ponto

5. Sem compressão
   - Todas as mensagens trafegam inteiras

Melhorias Futuras
=================

1. Implementar PKI com CA
2. Persistência com banco de dados
3. Renegociação de chaves periódica
4. Suporte a grupos de conversa
5. Compressão de payload
6. Rate limiting no servidor
7. Logs estruturados
8. Métricas de performance
