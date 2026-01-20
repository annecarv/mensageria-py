Documentacao Tecnica - Componentes de Criptografia
===================================================

Este documento descreve a implementação dos componentes criptográficos da
aplicação de mensageria segura.

MODULO: crypto.py
=================

Responsabilidades:
- Operações criptográficas elementares
- ECDHE (troca de chaves efêmeras)
- RSA (assinatura e verificação)
- HKDF (derivação de chaves)
- AES-GCM (cifragem autenticada)
- Geração de nonces

====================
Classe: ECDHEKeyExchange
====================

Responsabilidade: Implementar troca de chaves Diffie-Hellman de curva elíptica.

Atributos:
- private_key: Chave privada ECDHE (EC private key P-256)
- public_key: Chave pública correspondente

Métodos principais:

1. __init__()
   Gera novo par de chaves ECDHE usando curva P-256 (secp256r1).
   P-256 é a curva recomendada por NIST e usada em TLS 1.3.
   
   Operação:
   ```
   sk = random() em Z_p
   pk = sk * G  (G é ponto gerador)
   ```

2. get_public_key_bytes()
   Retorna chave pública em formato comprimido X962.
   Formato comprimido: 65 bytes (1 byte de tipo + 32 bytes de coordenada X)
   
   Benefícios:
   - Reduz tamanho da transmissão
   - Mantém segurança da curva P-256

3. compute_shared_secret(peer_public_key_bytes)
   Calcula segredo compartilhado ECDH com chave pública do peer.
   
   Entrada:
   - peer_public_key_bytes: Chave pública peer em formato comprimido
   
   Operação:
   ```
   Reconstruir ponto do peer a partir dos bytes
   Z = sk_local * pk_peer  (operação de scalar multiplication)
   Retorna Z em bytes (32 bytes para P-256)
   ```
   
   Propriedade ECDH:
   - Cliente: Z = sk_C * pk_S
   - Servidor: Z = sk_S * pk_C
   - Resultado é idêntico em ambos os lados
   - Apenas conhecendo sk (chave privada) é possível calcular Z

====================
Classe: RSASignature
====================

Responsabilidade: Operações de assinatura e verificação RSA-2048.

Atributos:
- private_key: Chave privada RSA
- public_key: Chave pública RSA

Métodos principais:

1. __init__(private_key=None)
   Inicializa com chave RSA existente ou gera nova.
   
   Se private_key é None:
   - Gera novo par RSA-2048
   - Expoente público: 65537 (padrão)
   - Tamanho da chave: 2048 bits (~309 dígitos decimais)
   
   Configuração RSA-2048 garante segurança por ~30 anos (até 2035).

2. get_public_key_pem()
   Retorna chave pública em formato PEM.
   
   Formato PEM:
   ```
   -----BEGIN PUBLIC KEY-----
   [base64 encoded DER data]
   -----END PUBLIC KEY-----
   ```
   
   Usado para: Certificados pinados no cliente

3. get_private_key_pem()
   Retorna chave privada em formato PEM sem encriptação.
   
   Formato PEM:
   ```
   -----BEGIN PRIVATE KEY-----
   [base64 encoded DER data]
   -----END PRIVATE KEY-----
   ```
   
   Restrição: Em produção, deve ser protegido (com senha)

4. sign(data)
   Assina dados com chave privada RSA.
   
   Configuração:
   - Padding: RSA-PSS (Probabilistic Signature Scheme)
   - Função hash: SHA-256
   - Salt length: Máximo (32 bytes para SHA-256)
   
   Operação:
   ```
   1. Hash dados: h = SHA-256(data)
   2. Aplicar PSS padding: m = PSS_encode(h, salt_aleatorio)
   3. Assinar: sig = m^d mod n  (d é expoente privado, n é módulo)
   4. Retornar signature (256 bytes para RSA-2048)
   ```
   
   Dados assinados neste projeto: pk_S || client_id || salt

5. verify(public_key_pem, signature, data) [static]
   Verifica assinatura RSA.
   
   Operação:
   ```
   1. Carregar chave pública do PEM
   2. Hash dados: h = SHA-256(data)
   3. Verificar PSS: PSS_verify(signature, h)
   4. Retorna True se válida, False caso contrário
   ```
   
   Exceções são capturadas e retornam False (falha silenciosa).

====================
Classe: HKDFKeyDerivation
====================

Responsabilidade: Derivação de chaves usando HMAC-based Key Derivation Function
conforme RFC 5869 e TLS 1.3.

Estrutura HKDF em duas fases:

Fase 1: HKDF-Extract (PRK generation)
```
PRK = HMAC-SHA256(salt, IKM)
Entrada: IKM (Input Keying Material) = segredo ECDH
Saída: PRK (Pseudo-Random Key) = 32 bytes
```

Fase 2: HKDF-Expand (Key derivation)
```
OKM = HMAC-SHA256(PRK, info)[:length]
Entrada: PRK, label específico (info)
Saída: OKM (Output Keying Material) = length bytes
```

Método principal:

1. derive_keys(shared_secret, salt, label_c2s="c2s", label_s2c="s2c")
   Deriva par de chaves simétricas AES-128 para ambas direções.
   
   Entrada:
   - shared_secret: Segredo ECDH (32 bytes para P-256)
   - salt: Valor aleatório (32 bytes, gerado pelo servidor)
   - label_c2s: String "c2s" (identificador de direção 1)
   - label_s2c: String "s2c" (identificador de direção 2)
   
   Processo:
   ```
   # Fase 1: Extract
   PRK = HMAC-SHA256(salt, shared_secret)  # 32 bytes
   
   # Fase 2: Expand (cliente->servidor)
   Key_c2s = HMAC-SHA256(PRK, "c2s")[:16]  # Primeiros 16 bytes
   
   # Fase 2: Expand (servidor->cliente)
   Key_s2c = HMAC-SHA256(PRK, "s2c")[:16]  # Primeiros 16 bytes
   ```
   
   Saída: (key_c2s, key_s2c) - dois valores de 16 bytes cada
   
   Propriedade: Labels diferentes produzem chaves diferentes
   Mesmo segredo ECDH produz chaves determinísticas mas diferentes
   por direção.

Razão de usar HKDF:
1. Extender segredo ECDH para múltiplas chaves
2. Separar direções com labels diferentes
3. Adicionar entropia via salt
4. Derivação determinística e segura
5. Usada em TLS 1.3

====================
Classe: AESGCMCipher
====================

Responsabilidade: Cifragem e decifragem simétrica com AES-128-GCM.

AES-GCM é um modo AEAD (Authenticated Encryption with Associated Data):
- Confidencialidade: Cifragem AES-128
- Autenticidade: Tag GCM (Galois/Counter Mode)
- Associated Data: Dados autenticados mas não cifrados

Atributos:
- key: Chave AES-128 (16 bytes = 128 bits)

Métodos principais:

1. __init__(key)
   Inicializa cipher com chave AES-128.
   Valida que key tem exatamente 16 bytes.
   Levanta ValueError se tamanho incorreto.

2. encrypt(nonce, plaintext, aad=b'')
   Cifra dados com AES-128-GCM.
   
   Entrada:
   - nonce: Valor aleatório de 12 bytes (um por mensagem)
   - plaintext: Dados em claro
   - aad: Dados autenticados adicionais (opcional)
   
   Processo:
   ```
   1. Inicializar AES-128 no modo GCM com nonce
   2. Processar AAD (não é cifrado, apenas autenticado)
   3. Cifrar plaintext com AES
   4. Calcular tag de autenticação GCM (16 bytes)
   5. Retornar ciphertext || tag
   ```
   
   Saída: bytes contendo (ciphertext || tag)
   
   Segurança do nonce:
   - Nonce de 12 bytes é padrão para GCM
   - Deve ser único para cada mensagem com mesma chave
   - Reuso de nonce compromete segurança completamente

3. decrypt(nonce, ciphertext, aad=b'')
   Decifra e valida autenticidade.
   
   Entrada:
   - nonce: Mesmo nonce usado na cifragem
   - ciphertext: Dados cifrados com tag
   - aad: Mesmo AAD usado na cifragem
   
   Processo:
   ```
   1. Extrair tag (últimos 16 bytes de ciphertext)
   2. Inicializar AES-128 GCM com nonce
   3. Processar AAD
   4. Descriptografar
   5. Verificar tag (falha se diferentes)
   6. Se falhar, retornar None
   7. Se sucesso, retornar plaintext
   ```
   
   Saída: plaintext se válida, None se falha
   
   Propriedade: Uma alteração de 1 bit no ciphertext invalida a tag

Fluxo de cifragem de mensagem:

Cliente: plaintext -> [nonce, aad] -> encrypt -> ciphertext+tag -> enviar
Servidor: recebe -> [nonce, aad] -> decrypt -> valida tag -> plaintext

====================
Funções Auxiliares
====================

1. generate_nonce()
   Gera nonce aleatório de 12 bytes para AES-GCM.
   Usa os.urandom() para entropia criptográfica.
   Deve ser chamada uma vez por mensagem.

2. bytes_to_int(data)
   Converte bytes para inteiro big-endian.
   Usado para desserializar seq_no e contadores.

3. int_to_bytes(value, length)
   Converte inteiro para bytes de tamanho fixo.
   Usado para serializar seq_no e contadores.

Fluxo Completo de Derivação de Chaves
=====================================

Evento: Cliente conecta ao servidor

1. Cliente cria objeto ECDHEKeyExchange
   -> Gera (sk_C, pk_C) usando P-256
   
2. Cliente envia pk_C ao servidor
   
3. Servidor cria objeto ECDHEKeyExchange
   -> Gera (sk_S, pk_S) usando P-256
   -> Gera salt aleatório (32 bytes)
   -> Assina (pk_S || client_id || salt) com RSA privada
   
4. Servidor envia: pk_S, server.crt, assinatura, salt
   
5. Cliente valida assinatura com server.crt
   
6. Ambos calculam Z:
   Cliente: Z = sk_C.exchange(pk_S) = 32 bytes
   Servidor: Z = sk_S.exchange(pk_C) = mesmos 32 bytes
   
7. Ambos derivam chaves com HKDFKeyDerivation.derive_keys:
   
   PRK = HMAC-SHA256(salt, Z)
   Key_c2s = HMAC-SHA256(PRK, "c2s")[:16]
   Key_s2c = HMAC-SHA256(PRK, "s2c")[:16]
   
8. Chaves prontas para cifragem de mensagens

Propriedades de Segurança Alcançadas
===================================

1. Confidencialidade:
   - AES-128: 2^128 chaves possíveis
   - Sem chave, ciphertext é indistinguível de aleatório
   - Força bruta requer ~10^38 tentativas

2. Integridade:
   - Tag GCM de 16 bytes
   - Probabilidade de falsificação: < 2^-128
   - Uma alteração detecta com probabilidade muito alta

3. Autenticidade:
   - RSA-2048: Apenas detentor da chave privada pode assinar
   - Cliente valida com chave pública pinada
   - Impede MITM se certificado for confiável

4. Sigilo Perfeito:
   - Chaves de sessão não dependem de RSA
   - Comprometimento de RSA não afeta sessões antigas
   - Cada sessão tem ECDHE independente

5. Unicidade de Chaves:
   - Labels diferentes (c2s vs s2c) produzem chaves diferentes
   - Salt aleatório garante variação entre clientes
   - seq_no garante nonces únicos por mensagem

Implementação Segura
====================

Práticas de segurança adotadas:

1. Uso de bibliotecas validadas (cryptography)
2. Não implementar primitivas criptográficas custom
3. Geração de randomness via os.urandom() (cryptographic PRNG)
4. Sem caching de chaves em memória não inicializado
5. Validação de tamanho de entrada
6. Tratamento de exceções criptográficas
7. Sem logs de dados sensíveis (chaves, nonces)
