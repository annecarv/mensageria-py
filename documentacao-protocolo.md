Documentacao Tecnica - Protocolo e Estruturas
==============================================

Este documento descreve a implementação do protocolo de handshake e estruturas
de mensagens.

MODULO: protocol.py
===================

Responsabilidades:
- Estruturas de serialização de mensagens
- Protocolo de handshake cliente-servidor
- Lógica de cifragem/decifragem de mensagens

====================
Classe: MessageFrame
====================

Responsabilidade: Representar e serializar frame de mensagem criptografada.

Estrutura de dados:
```
MessageFrame {
    nonce: bytes (12B)                  - Valor aleatório para AES-GCM
    sender_id: bytes (16B)              - UUID do remetente
    recipient_id: bytes (16B)           - UUID do destinatário
    seq_no: int (8B quando serializado) - Contador monotônico (anti-replay)
    ciphertext_with_tag: bytes          - Dados cifrados + tag GCM (16B)
}
```

Atributos:

1. nonce (bytes, 12B)
   Valor aleatório único por mensagem.
   Gerado pelo cliente/servidor ao cifrar.
   Reuso compromete segurança do GCM.

2. sender_id (bytes, 16B)
   UUID do cliente remetente.
   Parte do AAD (dados autenticados adicionais).
   Permite rotear para cliente correto.

3. recipient_id (bytes, 16B)
   UUID do cliente destinatário.
   Parte do AAD.
   Servidor usa para rotear mensagem.

4. seq_no (int)
   Contador monotônico por direção.
   Incrementa a cada mensagem enviada.
   Detecta replay: deve ser seq_no > seq_recv.
   Serializado em 8 bytes big-endian.

5. ciphertext_with_tag (bytes)
   Resultado de AES-128-GCM.encrypt().
   Contém dados cifrados + tag de 16 bytes.
   Tamanho variável dependendo da mensagem.

Métodos:

1. to_bytes()
   Serializa frame para transmissão TCP.
   
   Formato serializado:
   ```
   [nonce (12B)] +
   [sender_id (16B)] +
   [recipient_id (16B)] +
   [seq_no (8B)] +
   [ciphertext_with_tag (variável)]
   ```
   
   Total fixed: 52 bytes (header)
   
   Nota: Na implementação atual, adiciona 4B de size antes de enviar:
   [nonce (12B)] + [sender_id (16B)] + [recipient_id (16B)] +
   [seq_no (8B)] + [size (4B)] + [ciphertext_with_tag]

2. from_bytes(data) [static]
   Desserializa frame recebido.
   
   Validação:
   - data deve ter pelo menos 48 bytes
   - Levanta ValueError se muito curto
   
   Parse:
   - nonce = data[0:12]
   - sender_id = data[12:28]
   - recipient_id = data[28:44]
   - seq_no = data[44:52] convertido para int
   - ciphertext_with_tag = data[52:]

Fluxo de uso:

Envio:
```
frame = MessageFrame(nonce, sender_id, recipient_id, seq_no, ciphertext+tag)
bytes_to_send = frame.to_bytes()
writer.write(bytes_to_send)
```

Recebimento:
```
data = reader.read(size)
frame = MessageFrame.from_bytes(data)
```

====================
Classe: HandshakeResponse
====================

Responsabilidade: Encapsular resposta do servidor no handshake.

Estrutura de dados:
```
HandshakeResponse {
    server_public_key: bytes (65B)  - Chave pública ECDHE do servidor
    server_certificate: bytes       - Certificado RSA (chave pública, ~294B)
    signature: bytes (256B)         - Assinatura RSA-2048 dos dados
    salt: bytes (32B)               - Salt para HKDF
}
```

Dados assinados pelo servidor:
```
signed_data = server_public_key || client_id || salt
```

Campos:

1. server_public_key (bytes, ~65B)
   Chave pública ECDHE (P-256) do servidor em formato comprimido.
   Usado pelo cliente para calcular segredo compartilhado.
   Assinado com RSA para autenticidade.

2. server_certificate (bytes, ~294B)
   Certificado autoassinado do servidor (chave pública RSA em PEM).
   Cliente usa para validar assinatura.
   Pinado no cliente (armazenado localmente).

3. signature (bytes, 256B)
   Assinatura RSA-2048 com SHA-256 dos dados (server_public_key || client_id || salt).
   Garante que server_public_key vem do servidor autêntico.
   Impede man-in-the-middle.

4. salt (bytes, 32B)
   Valor aleatório para HKDF.
   Gerado pelo servidor.
   Evita que clientes diferentes com mesmo ECDHE gerem mesmas chaves.

Métodos:

1. to_bytes()
   Serializa resposta para transmissão.
   
   Formato:
   ```
   [len_pk (2B)] + [server_public_key] +
   [len_cert (2B)] + [server_certificate] +
   [len_sig (2B)] + [signature] +
   [salt (32B)]
   ```
   
   Tamanho total de comprimento prefixado:
   - 2B (len_pk) + 65B (pk) = 67B
   - 2B (len_cert) + ~294B (cert) = ~296B
   - 2B (len_sig) + 256B (sig) = 258B
   - 32B (salt)
   - Total: ~653 bytes

2. from_bytes(data) [static]
   Desserializa resposta recebida.
   
   Parse:
   ```
   offset = 0
   pk_len = unpack(data[offset:offset+2])
   offset += 2
   server_public_key = data[offset:offset+pk_len]
   offset += pk_len
   
   [similarmente para cert e sig]
   
   salt = data[offset:]  # Resto é salt
   ```
   
   Levanta ValueError se formato inválido.

Fluxo de uso:

Servidor:
```
response = HandshakeResponse(server_pk, cert, signature, salt)
response_bytes = response.to_bytes()
writer.write(response_bytes)
```

Cliente:
```
data = reader.read(size)
response = HandshakeResponse.from_bytes(data)
# Validar assinatura
# Derivar chaves
```

====================
Classe: ClientHandshake
====================

Responsabilidade: Implementar lado cliente do handshake.

Atributos:

1. client_id (bytes, 16B)
   UUID do cliente (fornecido no __init__).
   Enviado ao servidor como identificador.

2. ecdhe (ECDHEKeyExchange)
   Objeto para gerar e usar chaves ECDHE efêmeras.
   Gerado no __init__.

Métodos:

1. __init__(client_id)
   Inicializa handshake do cliente.
   
   Ações:
   - Armazena client_id
   - Cria novo objeto ECDHEKeyExchange (gera pk_C, sk_C)

2. get_initial_message()
   Prepara mensagem inicial para enviar ao servidor.
   
   Formato:
   ```
   [client_id (16B)] + [client_public_key (65B)]
   ```
   
   Total: 81 bytes
   
   Conteúdo:
   - client_id: UUID do cliente
   - client_public_key: Chave pública ECDHE em formato comprimido
   
   Segurança:
   - Nenhuma autenticação (primeira mensagem)
   - Servidor não sabe ainda quem é o cliente
   - Conexão TCP garante ordem de entrega

3. process_handshake_response(handshake_response, server_certificate_pem)
   Processa resposta do servidor, valida e deriva chaves.
   
   Entrada:
   - handshake_response: Objeto HandshakeResponse desserializado
   - server_certificate_pem: Certificado PEM do servidor (bytes)
   
   Validação:
   1. Reconstrói dados assinados: server_public_key || client_id || salt
   2. Chama RSASignature.verify() com certificado
   3. Se falha, levanta ValueError("Assinatura RSA do servidor inválida!")
   
   Se validação passa:
   1. Calcula segredo compartilhado:
      Z = ecdhe.compute_shared_secret(handshake_response.server_public_key)
   
   2. Deriva chaves:
      key_c2s, key_s2c = HKDFKeyDerivation.derive_keys(Z, salt)
   
   Saída: (key_c2s, key_s2c, salt)
   
   Levanta:
   - ValueError se assinatura inválida
   - Exceções de criptografia se dados malformados

Fluxo de handshake do cliente:

```
1. client_handshake = ClientHandshake(client_id)
2. initial_msg = client_handshake.get_initial_message()
3. Enviar initial_msg ao servidor
4. Receber response_bytes do servidor
5. response = HandshakeResponse.from_bytes(response_bytes)
6. key_c2s, key_s2c, salt = client_handshake.process_handshake_response(
      response, server_cert_pem
   )
7. Pronto para enviar/receber mensagens
```

====================
Classe: ServerHandshake
====================

Responsabilidade: Implementar lado servidor do handshake.

Atributos:

1. rsa_signature (RSASignature)
   Objeto contendo chaves RSA do servidor.
   Fornecido no __init__.
   Usado para assinar dados de handshake.

2. ecdhe (ECDHEKeyExchange)
   Objeto para gerar chaves ECDHE efêmeras.
   Novo para cada cliente.

Métodos:

1. __init__(rsa_signature)
   Inicializa handshake do servidor.
   
   Ações:
   - Armazena objeto RSASignature
   - Cria novo objeto ECDHEKeyExchange (gera pk_S, sk_S)

2. get_server_public_key()
   Retorna chave pública ECDHE do servidor.
   
   Saída: bytes (65B)
   
   Nota: Este valor é assinado e enviado ao cliente.

3. process_client_initial_message(data)
   Processa mensagem inicial recebida do cliente.
   
   Entrada:
   - data: bytes contendo [client_id (16B)] + [pk_C (65B+)]
   
   Validação:
   - data deve ter pelo menos 65 bytes
   - Levanta ValueError se muito curto
   
   Parse:
   - client_id = data[0:16]
   - client_public_key = data[16:]
   
   Saída: (client_id, client_public_key)

4. generate_handshake_response(client_id, client_public_key)
   Gera resposta de handshake.
   
   Entrada:
   - client_id: UUID do cliente
   - client_public_key: Chave pública ECDHE do cliente
   
   Processo:
   1. Gerar salt aleatório (32 bytes)
   2. Obter server_pk = self.get_server_public_key()
   3. Construir signed_data = server_pk || client_id || salt
   4. Assinar: signature = self.rsa.sign(signed_data)
   5. Obter certificado: certificate = self.rsa.get_public_key_pem()
   6. Criar objeto HandshakeResponse
   7. Retornar resposta
   
   Saída: HandshakeResponse
   
   Nota: Cada cliente recebe salt diferente (variação aleatória).

5. derive_session_keys(client_public_key, salt)
   Deriva chaves de sessão.
   
   Entrada:
   - client_public_key: Chave pública ECDHE do cliente
   - salt: Salt do handshake
   
   Processo:
   1. Calcular Z = self.ecdhe.compute_shared_secret(client_public_key)
   2. Derivar chaves: key_c2s, key_s2c = HKDFKeyDerivation.derive_keys(Z, salt)
   
   Saída: (key_c2s, key_s2c)

Fluxo de handshake do servidor:

```
1. server_handshake = ServerHandshake(rsa_signature)
2. Receber initial_data do cliente
3. client_id, client_pk = server_handshake.process_client_initial_message(
      initial_data
   )
4. response = server_handshake.generate_handshake_response(client_id, client_pk)
5. Enviar response.to_bytes() ao cliente
6. key_c2s, key_s2c = server_handshake.derive_session_keys(client_pk, response.salt)
7. Registrar sessão com chaves
```

====================
Classe: MessageCrypto
====================

Responsabilidade: Operações de cifragem/decifragem de mensagens.

Métodos:

1. encrypt_message(key, sender_id, recipient_id, seq_no, plaintext) [static]
   Cifra uma mensagem.
   
   Entrada:
   - key: Chave AES-128 (16 bytes)
   - sender_id: UUID do remetente (16 bytes)
   - recipient_id: UUID do destinatário (16 bytes)
   - seq_no: Contador (int)
   - plaintext: Dados em claro (bytes)
   
   Processo:
   1. Gerar nonce aleatório (12 bytes)
   2. Construir AAD = sender_id || recipient_id || seq_no (8B)
   3. Criar cipher = AESGCMCipher(key)
   4. Cifrar: ciphertext = cipher.encrypt(nonce, plaintext, aad)
   5. Criar e retornar MessageFrame
   
   Saída: MessageFrame pronto para transmissão
   
   Segurança:
   - AAD inclui IDs e seq_no (não pode ser alterado sem falha)
   - Nonce aleatório por mensagem
   - Cada direção tem chave diferente

2. decrypt_message(key, frame) [static]
   Decifra uma mensagem.
   
   Entrada:
   - key: Chave AES-128 (16 bytes)
   - frame: MessageFrame recebido
   
   Processo:
   1. Reconstruir AAD = frame.sender_id || frame.recipient_id || frame.seq_no
   2. Criar cipher = AESGCMCipher(key)
   3. Descriptografar: plaintext = cipher.decrypt(frame.nonce, frame.ciphertext_with_tag, aad)
   
   Saída: plaintext (bytes) se válida, None se falha
   
   Validação:
   - Tag GCM deve ser válida
   - AAD deve ser idêntico
   - Exceções retornam None (falha segura)

Fluxo de mensagem cliente->servidor:

```
# Cliente cifra
message = "Ola!"
frame = MessageCrypto.encrypt_message(
    key=key_c2s,
    sender_id=client_id,
    recipient_id=server_id,
    seq_no=seq_send,
    plaintext=message.encode()
)
seq_send += 1

# Enviar frame.to_bytes()

# Servidor decifra
plaintext = MessageCrypto.decrypt_message(key_c2s, frame)
```

Fluxo de roteamento servidor->cliente:

```
# Servidor re-cifra para outro cliente
frame_novo = MessageCrypto.encrypt_message(
    key=key_s2c_destinatario,
    sender_id=frame.sender_id,
    recipient_id=frame.recipient_id,
    seq_no=seq_send_destinatario,
    plaintext=plaintext
)
seq_send_destinatario += 1

# Enviar frame_novo.to_bytes() ao cliente destinatário
```

Protocolo Completo
==================

FASE 1: Conexão TCP
Ator 1 (Cliente): Conecta em 127.0.0.1:9999
Ator 2 (Servidor): Aceita conexão

FASE 2: Handshake ECDHE + RSA

Cliente envia:
[client_id (16B)] + [pk_C (65B)]
Total: 81 bytes

Servidor recebe e processa:
1. Parse client_id e pk_C
2. Gera novo ECDHE (sk_S, pk_S)
3. Gera salt aleatório
4. Assina (pk_S || client_id || salt) com RSA privada
5. Obtém certificado PEM

Servidor envia:
HandshakeResponse.to_bytes() (~653 bytes)
[len_pk] + [pk_S] + [len_cert] + [cert] + [len_sig] + [sig] + [salt]

Cliente recebe e processa:
1. Desserializa HandshakeResponse
2. Valida assinatura com certificado
3. Se falha, desconecta
4. Calcula Z = ECDH(sk_C, pk_S)
5. Deriva chaves com HKDF

Servidor também:
1. Calcula Z = ECDH(sk_S, pk_C)
2. Deriva chaves com HKDF (mesmas chaves)

FASE 3: Troca de Mensagens

Cliente envia para servidor:
frame = MessageCrypto.encrypt_message(key_c2s, ...)
[nonce] + [sender_id] + [recipient_id] + [seq_no] + [size] + [ciphertext+tag]

Servidor recebe:
1. Desserializa frame
2. Valida seq_no > seq_recv (anti-replay)
3. Decifra com key_c2s
4. Valida tag GCM

Se destinatário existe:
1. Re-cifra com key_s2c_destinatario
2. Envia ao cliente destinatário

FASE 4: Recebimento

Cliente destinatário recebe:
[nonce'] + [sender_id] + [recipient_id] + [seq_no'] + [size] + [ciphertext'+tag']

Cliente:
1. Desserializa frame
2. Valida seq_no' > seq_recv (anti-replay)
3. Decifra com key_s2c
4. Valida tag GCM
5. Exibe mensagem

Segurança Alcançada
===================

1. Confidencialidade:
   - Mensagem cifrada com AES-128
   - Roteamento pelo servidor não revela conteúdo

2. Integridade:
   - Tag GCM de 16 bytes valida dados
   - Alteração detectada imediatamente

3. Autenticidade:
   - RSA assina chaves ECDHE do servidor
   - Cliente valida assinatura com certificado pinado

4. Sigilo Perfeito:
   - Chaves dependem apenas de ECDHE
   - Compromentimento de RSA não afeta sessões antigas

5. Anti-Replay:
   - seq_no monotônico por direção
   - Mensagem antiga rejeitada se seq_no <= seq_recv

6. Separação de Canais:
   - key_c2s para cliente->servidor
   - key_s2c para servidor->cliente
   - Labels diferentes impedem cross-canal
