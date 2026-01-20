import asyncio
import logging
import uuid
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from protocol import (
    ServerHandshake, MessageCrypto, MessageFrame,
    HandshakeResponse
)
from crypto import RSASignature


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Server")


@dataclass
class ClientSession:
    client_id: bytes
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    key_c2s: bytes
    key_s2c: bytes
    seq_recv: int
    seq_send: int
    salt: bytes


class SecureMessagingServer:

    def __init__(self, host: str = "127.0.0.1", port: int = 9999, cert_path: str = None, key_path: str = None):
        self.host = host
        self.port = port
        self.sessions: Dict[bytes, ClientSession] = {}

        # Carrega chaves existentes ou gera novas
        if cert_path and key_path:
            self.rsa_signature = self._load_or_generate_keys(cert_path, key_path)
        else:
            self.rsa_signature = RSASignature()

        self.handshake = ServerHandshake(self.rsa_signature)
        logger.info(f"Servidor iniciado em {host}:{port}")

    def _load_or_generate_keys(self, cert_path: str, key_path: str) -> RSASignature:
        import os
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend

        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                private_key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )
            logger.info(f"Chaves carregadas de {key_path}")
            return RSASignature(private_key)
        else:
            rsa = RSASignature()
            os.makedirs(os.path.dirname(cert_path), exist_ok=True)
            with open(cert_path, 'wb') as f:
                f.write(rsa.get_public_key_pem())
            with open(key_path, 'wb') as f:
                f.write(rsa.get_private_key_pem())
            logger.info(f"Novas chaves geradas e salvas em {cert_path}, {key_path}")
            return rsa

    def save_credentials(self, cert_path: str, key_path: str):
        with open(cert_path, 'wb') as f:
            f.write(self.rsa_signature.get_public_key_pem())

        with open(key_path, 'wb') as f:
            f.write(self.rsa_signature.get_private_key_pem())

        logger.info(f"Credenciais salvas: {cert_path}, {key_path}")

    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ):
        peer_addr = writer.get_extra_info('peername')
        logger.info(f"Nova conexão de {peer_addr}")

        try:
            initial_message = await reader.readexactly(49)
            client_id, client_public_key = self.handshake.process_client_initial_message(
                initial_message
            )

            logger.info(f"Cliente conectado: {client_id.hex()}")

            handshake_response = self.handshake.generate_handshake_response(
                client_id, client_public_key
            )

            response_data = handshake_response.to_bytes()
            response_header = len(response_data).to_bytes(4, 'big')
            writer.write(response_header + response_data)
            await writer.drain()

            key_c2s, key_s2c = self.handshake.derive_session_keys(
                client_public_key, handshake_response.salt
            )

            session = ClientSession(
                client_id=client_id,
                reader=reader,
                writer=writer,
                key_c2s=key_c2s,
                key_s2c=key_s2c,
                seq_recv=-1,
                seq_send=0,
                salt=handshake_response.salt
            )
            self.sessions[client_id] = session

            logger.info(f"Sessão estabelecida para {client_id.hex()}")

            while True:
                header = await reader.readexactly(52)

                try:
                    size_data = await reader.readexactly(4)
                    ciphertext_size = int.from_bytes(size_data, 'big')
                    ciphertext_with_tag = await reader.readexactly(ciphertext_size)

                    frame_data = header + size_data + ciphertext_with_tag

                    frame = self._parse_frame_with_size(frame_data)

                except asyncio.IncompleteReadError:
                    logger.warning(f"Conexão fechada por {client_id.hex()}")
                    break

                if frame.seq_no <= session.seq_recv:
                    logger.warning(f"Ataque de replay detectado de {client_id.hex()}")
                    continue

                session.seq_recv = frame.seq_no

                plaintext = MessageCrypto.decrypt_message(
                    session.key_c2s, frame
                )

                if plaintext is None:
                    logger.warning(f"Falha na autenticação de mensagem de {client_id.hex()}")
                    continue

                logger.info(
                    f"Mensagem de {frame.sender_id.hex()} "
                    f"para {frame.recipient_id.hex()}: {plaintext[:50]}"
                )

                await self._route_message(frame, plaintext, session)

        except Exception as e:
            logger.error(f"Erro ao tratar cliente: {e}")

        finally:
            if client_id in self.sessions:
                del self.sessions[client_id]
                logger.info(f"Sessão encerrada: {client_id.hex()}")

            writer.close()
            await writer.wait_closed()

    def _parse_frame_with_size(self, data: bytes) -> MessageFrame:
        nonce = data[0:12]
        sender_id = data[12:28]
        recipient_id = data[28:44]
        seq_no = int.from_bytes(data[44:52], 'big')
        ciphertext_with_tag = data[56:]

        return MessageFrame(
            nonce=nonce,
            sender_id=sender_id,
            recipient_id=recipient_id,
            seq_no=seq_no,
            ciphertext_with_tag=ciphertext_with_tag
        )

    async def _route_message(
        self,
        frame: MessageFrame,
        plaintext: bytes,
        sender_session: ClientSession
    ):
        recipient_id = frame.recipient_id

        if recipient_id not in self.sessions:
            logger.warning(f"Destinatário {recipient_id.hex()} não encontrado")
            return

        recipient_session = self.sessions[recipient_id]

        new_frame = MessageCrypto.encrypt_message(
            key=recipient_session.key_s2c,
            sender_id=frame.sender_id,
            recipient_id=frame.recipient_id,
            seq_no=recipient_session.seq_send,
            plaintext=plaintext
        )

        recipient_session.seq_send += 1

        try:
            message_bytes = (
                new_frame.nonce +
                new_frame.sender_id +
                new_frame.recipient_id +
                int.to_bytes(new_frame.seq_no, 8, 'big') +
                int.to_bytes(len(new_frame.ciphertext_with_tag), 4, 'big') +
                new_frame.ciphertext_with_tag
            )

            recipient_session.writer.write(message_bytes)
            await recipient_session.writer.drain()

            logger.info(f"Mensagem roteada para {recipient_id.hex()}")
        except Exception as e:
            logger.error(f"Erro ao rotear mensagem: {e}")

    async def start(self):
        server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )

        logger.info(f"Servidor aguardando conexões em {self.host}:{self.port}")

        async with server:
            await server.serve_forever()


def main():
    server = SecureMessagingServer(
        host="0.0.0.0",
        port=9999,
        cert_path="../certs/server.crt",
        key_path="../certs/server.key"
    )

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Servidor interrompido")


if __name__ == "__main__":
    main()
