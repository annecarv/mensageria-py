import struct
import os
from dataclasses import dataclass
from typing import Tuple, Optional
from crypto import (
    ECDHEKeyExchange, RSASignature, HKDFKeyDerivation,
    AESGCMCipher, generate_nonce, bytes_to_int, int_to_bytes
)


@dataclass
class MessageFrame:
    nonce: bytes
    sender_id: bytes
    recipient_id: bytes
    seq_no: int
    ciphertext_with_tag: bytes

    def to_bytes(self) -> bytes:
        return (
            self.nonce +
            self.sender_id +
            self.recipient_id +
            int_to_bytes(self.seq_no, 8) +
            self.ciphertext_with_tag
        )

    @staticmethod
    def from_bytes(data: bytes) -> 'MessageFrame':
        if len(data) < 48:
            raise ValueError("Frame muito curto")

        nonce = data[0:12]
        sender_id = data[12:28]
        recipient_id = data[28:44]
        seq_no = bytes_to_int(data[44:52])
        ciphertext_with_tag = data[52:]

        return MessageFrame(
            nonce=nonce,
            sender_id=sender_id,
            recipient_id=recipient_id,
            seq_no=seq_no,
            ciphertext_with_tag=ciphertext_with_tag
        )


@dataclass
class HandshakeResponse:
    server_public_key: bytes
    server_certificate: bytes
    signature: bytes
    salt: bytes

    def to_bytes(self) -> bytes:
        data = struct.pack('>H', len(self.server_public_key)) + self.server_public_key
        data += struct.pack('>H', len(self.server_certificate)) + self.server_certificate
        data += struct.pack('>H', len(self.signature)) + self.signature
        data += self.salt
        return data

    @staticmethod
    def from_bytes(data: bytes) -> 'HandshakeResponse':
        offset = 0

        pk_len = struct.unpack('>H', data[offset:offset+2])[0]
        offset += 2
        server_public_key = data[offset:offset+pk_len]
        offset += pk_len

        cert_len = struct.unpack('>H', data[offset:offset+2])[0]
        offset += 2
        server_certificate = data[offset:offset+cert_len]
        offset += cert_len

        sig_len = struct.unpack('>H', data[offset:offset+2])[0]
        offset += 2
        signature = data[offset:offset+sig_len]
        offset += sig_len

        salt = data[offset:]

        return HandshakeResponse(
            server_public_key=server_public_key,
            server_certificate=server_certificate,
            signature=signature,
            salt=salt
        )


class ClientHandshake:

    def __init__(self, client_id: bytes):
        self.client_id = client_id
        self.ecdhe = ECDHEKeyExchange()

    def get_initial_message(self) -> bytes:
        return self.client_id + self.ecdhe.get_public_key_bytes()

    def process_handshake_response(
        self,
        handshake_response: HandshakeResponse,
        server_certificate_pem: bytes
    ) -> Tuple[bytes, bytes, bytes]:
        signed_data = (
            handshake_response.server_public_key +
            self.client_id +
            handshake_response.salt
        )

        if not RSASignature.verify(
            server_certificate_pem,
            handshake_response.signature,
            signed_data
        ):
            raise ValueError("Assinatura RSA do servidor inválida!")

        shared_secret = self.ecdhe.compute_shared_secret(
            handshake_response.server_public_key
        )

        key_c2s, key_s2c = HKDFKeyDerivation.derive_keys(
            shared_secret=shared_secret,
            salt=handshake_response.salt
        )

        return key_c2s, key_s2c, handshake_response.salt


class ServerHandshake:

    def __init__(self, rsa_signature: RSASignature):
        self.rsa = rsa_signature
        self.ecdhe = ECDHEKeyExchange()

    def get_server_public_key(self) -> bytes:
        return self.ecdhe.get_public_key_bytes()

    def process_client_initial_message(self, data: bytes) -> Tuple[bytes, bytes]:
        if len(data) < 49:
            raise ValueError("Mensagem inicial muito curta")

        client_id = data[0:16]
        client_public_key = data[16:]

        return client_id, client_public_key

    def generate_handshake_response(
        self,
        client_id: bytes,
        client_public_key: bytes
    ) -> HandshakeResponse:
        salt = os.urandom(32)

        server_pk = self.get_server_public_key()
        signed_data = server_pk + client_id + salt

        signature = self.rsa.sign(signed_data)

        certificate = self.rsa.get_public_key_pem()

        return HandshakeResponse(
            server_public_key=server_pk,
            server_certificate=certificate,
            signature=signature,
            salt=salt
        )

    def derive_session_keys(
        self,
        client_public_key: bytes,
        salt: bytes
    ) -> Tuple[bytes, bytes]:
        shared_secret = self.ecdhe.compute_shared_secret(client_public_key)

        key_c2s, key_s2c = HKDFKeyDerivation.derive_keys(
            shared_secret=shared_secret,
            salt=salt
        )

        return key_c2s, key_s2c


class MessageCrypto:

    @staticmethod
    def encrypt_message(
        key: bytes,
        sender_id: bytes,
        recipient_id: bytes,
        seq_no: int,
        plaintext: bytes
    ) -> MessageFrame:
        nonce = generate_nonce()

        aad = sender_id + recipient_id + int_to_bytes(seq_no, 8)

        cipher = AESGCMCipher(key)
        ciphertext_with_tag = cipher.encrypt(nonce, plaintext, aad)

        return MessageFrame(
            nonce=nonce,
            sender_id=sender_id,
            recipient_id=recipient_id,
            seq_no=seq_no,
            ciphertext_with_tag=ciphertext_with_tag
        )

    @staticmethod
    def decrypt_message(
        key: bytes,
        frame: MessageFrame
    ) -> Optional[bytes]:
        aad = (
            frame.sender_id +
            frame.recipient_id +
            int_to_bytes(frame.seq_no, 8)
        )

        cipher = AESGCMCipher(key)
        plaintext = cipher.decrypt(
            frame.nonce,
            frame.ciphertext_with_tag,
            aad
        )

        return plaintext
