Guia de Apresentacao do Video
==============================

Projeto: Aplicacao de Mensageria Segura Multi-Cliente
Data: Janeiro 2026
Duracao: Maximo 20 minutos
Membros: 3 alunos

Objetivo: Demonstrar implementacao completa do protocolo de mensageria segura
com garantias de confidencialidade, integridade, autenticidade e sigilo perfeito.

====================================
DIVISAO DE RESPONSABILIDADES
====================================

MEMBRO 1: Fundamentos de Seguranca e Criptografia
MEMBRO 2: Protocolo de Handshake e Derivacao de Chaves
MEMBRO 3: Roteamento de Mensagens e Demonstracao Prática

Duracao total: ~15-18 minutos
- Cada membro: ~5-6 minutos
- Demo prática: ~3-4 minutos compartilhados

====================================
MEMBRO 1: Fundamentos de Seguranca e Criptografia
====================================

Duracao: ~5 minutos

O que apresentar:
1. Apresentacao pessoal (30 segundos)
   - Nome
   - Qual parte você desenvolveu

2. Requisitos de Seguranca (1 minuto)
   Explicar 4 pilares:
   
   a) Confidencialidade:
      - Dados precisam ser ilegíveis
      - Mecanismo: AES-128-GCM
      - Mesmo capturando no wifi, não consegue ler
   
   b) Integridade:
      - Alteracao deve ser detectada
      - Mecanismo: Tag de autenticacao GCM (16 bytes)
      - Se 1 bit mudar, tag falha
   
   c) Autenticidade:
      - Certificado prove quem é o servidor
      - Mecanismo: RSA-2048 com assinatura
      - Cliente valida antes de confiar nas chaves
   
   d) Sigilo Perfeito:
      - Mesmo se RSA for comprometida, sessoes antigas sao seguras
      - Mecanismo: ECDHE (chaves efêmeras)
      - Cada cliente tem chaves diferentes

3. Problema de Seguranca (1 minuto)
   Mostrar diagrama ou explicar:
   
   Sem protecao:
   - Wireshark captura mensagem em claro
   - Qualquer pessoa lê a conversa
   - Servidor poderia ser fake (MITM)
   - Mensagem antiga replicada funciona novamente
   
   Com protecao:
   - Wireshark so vê dados aleatorios (cifrados)
   - Apenas cliente com chave correta decifra
   - RSA garante servidor é autêntico
   - Contador seq_no rejeita mensagem velha

4. Mecanismo AES-128-GCM (2 minutos)
   Mostrar codigo relevante (40 linhas):
   ```
   Classe AESGCMCipher em crypto.py
   
   def encrypt(nonce, plaintext, aad):
       - Nonce: valor aleatorio (12 bytes) por mensagem
       - AAD: dados autenticados adicionais
       - Cipher.encrypt() retorna ciphertext + tag
   
   def decrypt(nonce, ciphertext, aad):
       - Mesmo nonce, mesmo AAD
       - Valida tag: se falha, retorna None
       - Se passa, retorna plaintext
   ```
   
   Visualizar:
   - Abrir arquivo crypto.py em VS Code
   - Destacar metodos encrypt/decrypt
   - Mostrar que é simples, usa biblioteca cryptography
   - Ressaltar: nonce aleatorio CADA VEZ
   - Ressaltar: AAD garante integridade

5. Conclusao (30 segundos)
   "Com AES-GCM + AAD, temos confidencialidade + integridade
   em um unico mecanismo. A proxima etapa é garantir autenticidade."

Script recomendado:
"Oi, sou [nome]. Desenvolvei a parte de criptografia básica do projeto.
Explico os 4 requisitos de seguranca que implementamos.

Confidencialidade: mensagens cifradas com AES-128-GCM. Sem chave,
é matematicamente impossível ler.

Integridade: tag de autenticacao de 16 bytes garante deteccao de alteracoes.

Autenticidade: certificado RSA do servidor é assinado e validado pelo cliente.

Sigilo perfeito: cada cliente tem chaves diferentes, derivadas apenas de 
ECDHE efêmero. Se RSA vazar, sessoes antigas permanecem seguras.

Agora vou mostrar o mecanismo de cifragem AES-GCM em código..."
[Abrir crypto.py, destacar AESGCMCipher]

====================================
MEMBRO 2: Protocolo de Handshake
====================================

Duracao: ~6 minutos

O que apresentar:
1. Apresentacao pessoal (30 segundos)
   - Nome
   - Qual parte você desenvolveu

2. Fluxo do Handshake (3 minutos)
   Desenhar ou mostrar sequencia:
   
   PASSO 1: Cliente conecta
   Cliente: Gera chaves ECDHE (sk_C, pk_C)
   
   PASSO 2: Cliente envia inicial
   Cliente -> Servidor: [client_id (16B)] + [pk_C (65B)]
   "Cliente revela seu UUID e chave pública ECDHE"
   
   PASSO 3: Servidor responde
   Servidor: Gera chaves ECDHE (sk_S, pk_S)
   Servidor: Gera salt aleatorio (32B)
   Servidor: Assina (pk_S || client_id || salt) com RSA privada
   Servidor: Envia [pk_S] + [certificado RSA] + [assinatura] + [salt]
   "Servidor envia sua chave pública, certificado e prova autenticidade"
   
   PASSO 4: Cliente valida
   Cliente: Recebe dados
   Cliente: Valida assinatura com certificado
   Se assinatura falhar:
   - Pode ser MITM
   - Conexao é rejeitada
   "Se assinatura passa, cliente sabe que servidor é autentico"
   
   PASSO 5: Ambos calculam segredo compartilhado
   Cliente: Z = ECDH(sk_C, pk_S) = 32 bytes
   Servidor: Z = ECDH(sk_S, pk_C) = 32 bytes (mesmo!)
   "ECDH garante que ambos chegam no mesmo Z sem enviar chave privada"
   
   PASSO 6: Ambos derivam chaves
   Ambos: Key_c2s = HKDF(Z, salt, label="c2s") = 16 bytes
   Ambos: Key_s2c = HKDF(Z, salt, label="s2c") = 16 bytes
   "Chaves diferentes por direção, mesmo segredo"

3. Visualizar codigo (2 minutos)
   Abrir protocol.py em VS Code
   
   Mostrar classe ClientHandshake:
   ```
   def get_initial_message():
       return client_id + pk_C
   
   def process_handshake_response(response, cert):
       # Validar assinatura
       if not RSASignature.verify(cert, signature, signed_data):
           raise ValueError("Assinatura inválida!")
       
       # Calcular Z
       Z = ecdhe.compute_shared_secret(pk_S)
       
       # Derivar chaves
       key_c2s, key_s2c = HKDF.derive_keys(Z, salt)
       return key_c2s, key_s2c
   ```
   
   Mostrar classe ServerHandshake:
   ```
   def generate_handshake_response(client_id, pk_C):
       pk_S = self.get_server_public_key()
       salt = os.urandom(32)
       
       signed_data = pk_S + client_id + salt
       signature = self.rsa.sign(signed_data)
       
       return HandshakeResponse(pk_S, cert, signature, salt)
   ```
   
   Ressaltar:
   - Assinatura é RSA-2048 com SHA-256
   - Salt é unico por cliente
   - Mesmo Z levando a mesmas chaves

4. Por que funciona (1 minuto)
   Explicar propriedades:
   
   ECDH (Elliptic Curve Diffie-Hellman):
   - Cliente tem sk_C (secreto), pk_S (publico)
   - Servidor tem sk_S (secreto), pk_C (publico)
   - Ambos calculam: sk_local * pk_peer = Z
   - Alguém escutando so vê pk_C e pk_S
   - Sem sk_C ou sk_S, impossível calcular Z
   
   RSA (Assinatura):
   - Servidor assina dados com chave privada
   - Cliente valida com chave publica (certificado)
   - Se assinatura for válida, dados vêm realmente do servidor
   - Impede MITM (atacante não tem chave privada RSA)
   
   HKDF (Key Derivation):
   - Transforma Z (32 bytes) em 2 chaves AES-128 (16 bytes cada)
   - Labels diferentes (c2s vs s2c) garantem chaves diferentes
   - Salt aleatório garante variação entre clientes
   - Derivação é determinística

Script recomendado:
"Sou [nome]. Desenvolvei o protocolo de handshake.

O handshake tem 6 passos. Primeiro, cliente conecta gerando suas chaves
ECDHE, um par de chaves que serão usadas apenas para esta conexao.

Cliente envia seu identificador e chave pública ao servidor.

Servidor recebe, gera suas próprias chaves ECDHE, um salt aleatório,
e assina os dados com chave privada RSA.

Cliente recebe a resposta e valida a assinatura do servidor usando
o certificado pinado localmente. Se for inválido, conexão é rejeitada.

Ambos usam ECDH para calcular segredo compartilhado Z. Note que apenas
com ambas as chaves privadas é possível calcular. Mesmo escutando,
atacante não consegue.

Finalmente, ambos usam HKDF para derivar chaves simétricas AES-128
a partir de Z e do salt. Labels diferentes garantem chaves diferentes
por direção.

Vou mostrar o código..."
[Abrir protocol.py, destacar ClientHandshake e ServerHandshake]

====================================
MEMBRO 3: Roteamento e Demonstracao
====================================

Duracao: ~6 minutos total (2 explicacao + 4 demo)

PARTE 1: Explicacao de Roteamento (2 minutos)
=============================================

1. Estrutura de Sessao (1 minuto)
   Mostrar estrutura em código:
   
   Abrir server.py
   Classe ClientSession:
   ```
   @dataclass
   class ClientSession:
       client_id: bytes              # UUID
       reader, writer                # Conexoes TCP
       key_c2s, key_s2c: bytes       # Chaves simétricas
       seq_recv, seq_send: int       # Contadores (anti-replay)
       salt: bytes                   # Salt do HKDF
   ```
   
   Explicar:
   - Servidor armazena em sessions[client_id]
   - Cada cliente conectado tem uma sessão
   - Chaves são específicas por cliente
   - Contadores previnem replay

2. Fluxo de Roteamento (1 minuto)
   Explicar processo:
   
   "Cliente A envia mensagem para Cliente B:
   1. Cliente A cifra com sua chave Key_c2s_A
   2. Envia frame: [UUID_A] + [UUID_B] + [nonce] + [seq_A] + [ciphertext_A+tag_A]
   3. Servidor recebe, valida seq_A > seq_recv_A (anti-replay)
   4. Decifra com Key_c2s_A, valida tag (integridade)
   5. Obtém plaintext
   6. Re-cifra com Key_s2c_B (chave diferente!)
   7. Novo frame: [UUID_A] + [UUID_B] + [nonce'] + [seq_B] + [ciphertext_B+tag_B]
   8. Envia para Cliente B
   9. Cliente B decifra com Key_s2c_B, valida tag
   10. Exibe mensagem"
   
   Ressaltar:
   - Servidor não consegue ler plaintext sem Key_c2s_A
   - Cliente B não consegue ler ciphertext_A sem Key_c2s_A
   - Cada direction tem chaves diferentes
   - Nonces são aleatórios cada vez

PARTE 2: Demonstracao Prática (4 minutos)
==========================================

Preparacao:
- 1 terminal com servidor
- 2 terminais com clientes
- VS Code com codigo aberto
- Wireshark (opcional) para mostrar trafego criptografado

PASSO 1: Iniciar Servidor (1 minuto)
```
Terminal 1:
$ cd /Users/enniax/Documents/seguranca_final/src
$ python init_certs.py

Output esperado:
Gerando par de chaves RSA-2048...
Certificado salvo: ../certs/server.crt
Chave privada salva: ../certs/server.key
Certificados inicializados com sucesso!

$ python server.py

Output esperado:
2024-01-20 14:30:00 - Server - INFO - Servidor iniciado em 0.0.0.0:9999
2024-01-20 14:30:00 - Server - INFO - Credenciais salvas: ../certs/server.crt, ../certs/server.key
2024-01-20 14:30:00 - Server - INFO - Servidor aguardando conexões em 0.0.0.0:9999

Narração:
"Aqui iniciamos o servidor. Ele gera certificado RSA e aguarda conexões."
```

PASSO 2: Conectar Cliente 1 (1 minuto)
```
Terminal 2:
$ cd src/
$ python client.py "Alice"

Output esperado:
2024-01-20 14:30:05 - Client - INFO - Cliente inicializado: Alice (a1b2c3d4...)
2024-01-20 14:30:05 - Client - INFO - Conectado ao servidor 127.0.0.1:9999
2024-01-20 14:30:05 - Client - INFO - Mensagem inicial enviada
2024-01-20 14:30:05 - Client - INFO - Resposta recebida
2024-01-20 14:30:05 - Client - INFO - Assinatura RSA validada
2024-01-20 14:30:05 - Client - INFO - Handshake concluído com sucesso
Conectado como: Alice (a1b2c3d4)
Formato de comando: /msg <recipient_id_hex> <mensagem>
>

Servidor output:
2024-01-20 14:30:05 - Server - INFO - Nova conexão de ('127.0.0.1', 54321)
2024-01-20 14:30:05 - Server - INFO - Cliente conectado: a1b2c3d4e5f6...
2024-01-20 14:30:05 - Server - INFO - Sessão estabelecida para a1b2c3d4e5f6...

Narração:
"Conectamos Alice com sucesso. Note que se houver MITM, assinatura RSA falha."
```

PASSO 3: Conectar Cliente 2 (1 minuto)
```
Terminal 3:
$ python client.py "Bob"

Output:
[Similar ao Client 1]
Conectado como: Bob (b8h7g6f5e4d3c2b1)

Narração:
"Conectamos Bob. Cada cliente tem UUID diferente e chaves diferentes."
```

PASSO 4: Trocar Mensagens (1 minuto)
```
Terminal 2 (Alice):
> /msg b8h7g6f5e4d3c2b1 Ola Bob! Tudo bem?

Servidor output:
2024-01-20 14:30:10 - Server - INFO - Mensagem de a1b2c3d4e5f6 para b8h7g6f5e4d3c2b1: Ola Bob! Tudo bem?
2024-01-20 14:30:10 - Server - INFO - Mensagem roteada para b8h7g6f5e4d3c2b1

Terminal 3 (Bob):
[Mensagem de a1b2c3d4]: Ola Bob! Tudo bem?

Terminal 3 (Bob):
> /msg a1b2c3d4e5f6g7h8 Ola Alice! Tudo bem sim!

Terminal 2 (Alice):
[Mensagem de b8h7g6f5e4d3c2b1]: Ola Alice! Tudo bem sim!

Narração:
"Alice envia mensagem criptografada com sua chave. Servidor roteia para Bob
que a decifra com sua chave. Mensagem viaja criptografada o tempo todo."

Mostrar no Wireshark (opcional):
- Capturar trafego de rede
- Mostrar frames no protocolo
- Ressaltar: ciphertext é aleatorio, não legível
- Mostrar: mesmo capturando frame, sem chave não consegue ler
```

Script recomendado:
"Sou [nome]. Implementei o servidor que roteia mensagens.

Servidor armazena sessao para cada cliente: UUID, chaves simétricas e
contadores para anti-replay.

Quando cliente A envia mensagem para B, servidor:
1. Recebe frame criptografado com Key_c2s_A
2. Valida counter (anti-replay)
3. Decifra com Key_c2s_A
4. Valida tag GCM
5. Re-cifra com Key_s2c_B
6. Roteia para B

Cada direção tem chaves diferentes, então servidor não consegue reutilizar
chaves de forma incorreta.

Vou demonstrar na prática. [Iniciar servidor]

[Conectar Alice] - Handshake ocorre, assinatura é validada.

[Conectar Bob] - Outro handshake com chaves diferentes.

[Alice envia para Bob] - Mensagem é roteada e descriptografada apenas por Bob.

[Bob responde] - Segundo par de chaves em ação.

Se capturarmos com Wireshark, vemos apenas dados aleatórios. Mesmo que
alguém capture o frame, sem Key_c2s ou Key_s2c, não consegue ler.

Com contador seq_no, mensagem antiga não consegue ser replicada.

Todos os requisitos de seguranca são alcançados: confidencialidade,
integridade, autenticidade e sigilo perfeito."

====================================
INTEGRACAO: EXPLICAR FLUXO COMPLETO
====================================

Duracao: ~2 minutos (todos falam juntos ou alternadamente)

Roteiro:

Membro 1: "Comecamos com o problema de seguranca. Mensagens no clear são
vulneráveis. Implementamos AES-GCM que garante confidencialidade e integridade."

Membro 2: "Mas como cliente e servidor combinam chaves sem que atacante
saiba? Usamos ECDHE para gerar segredo compartilhado, e RSA para garantir
que server é autentico. HKDF deriva chaves simétricas."

Membro 3: "E como é prático? Servidor roteia mensagens entre clientes.
Cada cliente tem chaves diferentes. Servidor não consegue ler plaintext
de clientes, apenas roteia dados cifrados. Atacante em rede ve apenas
dados aleatorios."

Todos: "E o principal: mesmo que RSA seja comprometido no futuro,
sessoes antigas foram usando apenas ECDHE. São seguras para sempre.
Isso é sigilo perfeito."

====================================
CHECKLIST DO VIDEO
====================================

Apresentacao Pessoal:
[ ] Cada membro se apresenta (nome e responsabilidade)

Explicacao Tecnica:
[ ] Membro 1: 4 requisitos de seguranca
[ ] Membro 1: AES-GCM explicado e em código
[ ] Membro 2: Fluxo de handshake (6 passos)
[ ] Membro 2: ECDHE + RSA + HKDF em código
[ ] Membro 3: Estrutura de sessão no servidor
[ ] Membro 3: Fluxo de roteamento

Demonstracao Prática:
[ ] Inicializar servidor
[ ] Conectar Cliente A (Alice)
[ ] Conectar Cliente B (Bob)
[ ] Alice envia mensagem para Bob
[ ] Bob recebe e responde
[ ] Mostrar logs confirmando criptografia
[ ] (Opcional) Capturar com Wireshark mostrando dados aleatorios

Conclusao:
[ ] Resumir garantias alcançadas
[ ] Mencionar sigilo perfeito
[ ] Mencionar anti-replay com seq_no
[ ] Boas praticas implementadas

Qualidade Tecnica:
[ ] Video tem audio claro
[ ] Tela legível (tamanho de fonte adequado)
[ ] Nao ultrapassar 20 minutos
[ ] Todos os membros falam

====================================
DICAS PRATICAS
====================================

1. Preparar terminal antes de gravar
   - Já ter servidor e clientes prontos
   - Ter VS Code com arquivos abertos
   - Testar tudo funciona

2. Usar zoom ou ampliar fonte
   - Terminal e VS Code com fonte grande
   - Para camera conseguir capturar detalhes

3. Praticar antes de gravar
   - Ensaiar apresentacao
   - Cronometrar tempo
   - Identificar trechos de código importantes

4. Mostrar código sem ler literalmente
   - Destacar linhas relevantes
   - Explicar logica
   - Não ler toda implementacao

5. Usar exemplos práticos
   - Real-time demo é mais convincente
   - Mostrar que funciona
   - Mostrar que é seguro

6. Mencionar desafios resolvidos
   - Como garantir chaves iguais em ambos lados?
   - Como evitar man-in-the-middle?
   - Como detectar replay?

7. Conclusao forte
   - Resumir o que foi alcançado
   - Mencionar aplicacao prática
   - Mencionar possibilidades de melhoria
