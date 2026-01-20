import asyncio
import logging
import uuid
from typing import Optional
from protocol import (
    ClientHandshake, MessageCrypto, MessageFrame
)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Client")


class SecureMessagingClient:

    def __init__(
        self,
        username: str,
        server_host: str = "127.0.0.1",
        server_port: int = 9999,
        server_cert_path: str = "../certs/server.crt"
    ):
        self.username = username
        self.client_id = uuid.uuid4().bytes
        self.server_host = server_host
        self.server_port = server_port
        self.server_cert_path = server_cert_path

        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

        self.key_c2s: Optional[bytes] = None
        self.key_s2c: Optional[bytes] = None

        self.seq_send = 0
        self.seq_recv = -1

        logger.info(f"Cliente inicializado: {username} ({self.client_id.hex()})")

    async def connect(self) -> bool:
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.server_host, self.server_port
            )
            logger.info(f"Conectado ao servidor {self.server_host}:{self.server_port}")

            handshake = ClientHandshake(self.client_id)
            initial_message = handshake.get_initial_message()

            self.writer.write(initial_message)
            await self.writer.drain()

            logger.info("Mensagem inicial enviada (client_id + pk_C)")

            response_header = await self.reader.readexactly(4)
            response_size = int.from_bytes(response_header, 'big')
            response_data = await self.reader.readexactly(response_size)

            from protocol import HandshakeResponse
            handshake_response = HandshakeResponse.from_bytes(response_data)

            logger.info("Resposta do servidor recebida (pk_S + cert + sig + salt)")

            with open(self.server_cert_path, 'rb') as f:
                server_certificate_pem = f.read()

            try:
                self.key_c2s, self.key_s2c, _ = handshake.process_handshake_response(
                    handshake_response, server_certificate_pem
                )
                logger.info("Assinatura RSA validada e chaves derivadas")
            except ValueError as e:
                logger.error(f"Validação falhou: {e}")
                return False

            logger.info("Handshake concluído com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao conectar: {e}")
            return False

    async def send_message(self, recipient_username: str, recipient_id: bytes, message: str) -> bool:
        if self.writer is None or self.key_c2s is None:
            logger.warning("Não conectado ao servidor")
            return False

        try:
            frame = MessageCrypto.encrypt_message(
                key=self.key_c2s,
                sender_id=self.client_id,
                recipient_id=recipient_id,
                seq_no=self.seq_send,
                plaintext=message.encode('utf-8')
            )

            self.seq_send += 1

            frame_bytes = (
                frame.nonce +
                frame.sender_id +
                frame.recipient_id +
                int.to_bytes(frame.seq_no, 8, 'big') +
                int.to_bytes(len(frame.ciphertext_with_tag), 4, 'big') +
                frame.ciphertext_with_tag
            )

            self.writer.write(frame_bytes)
            await self.writer.drain()

            logger.info(f"Mensagem enviada para {recipient_username}")
            return True

        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return False

    async def receive_messages(self):
        if self.reader is None or self.key_s2c is None:
            logger.warning("Não conectado ao servidor")
            return

        try:
            while True:
                header = await self.reader.readexactly(52)

                size_data = await self.reader.readexactly(4)
                ciphertext_size = int.from_bytes(size_data, 'big')
                ciphertext_with_tag = await self.reader.readexactly(ciphertext_size)

                frame_data = header + size_data + ciphertext_with_tag
                frame = self._parse_frame_with_size(frame_data)

                if frame.seq_no <= self.seq_recv:
                    logger.warning("Ataque de replay detectado")
                    continue

                self.seq_recv = frame.seq_no

                plaintext = MessageCrypto.decrypt_message(
                    self.key_s2c, frame
                )

                if plaintext is None:
                    logger.warning("Falha na validação de autenticidade")
                    continue

                message_text = plaintext.decode('utf-8', errors='ignore')
                sender_id = frame.sender_id.hex()

                logger.info(f"[{sender_id[:8]}]: {message_text}")
                print(f"\n[Mensagem de {sender_id[:8]}]: {message_text}")

        except asyncio.IncompleteReadError:
            logger.info("Conexão fechada pelo servidor")
        except Exception as e:
            logger.error(f"Erro ao receber mensagens: {e}")

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

    async def interactive_session(self):
        print(f"\nConectado como: {self.username} ({self.client_id.hex()[:8]})")
        print("Formato de comando: /msg <recipient_id_hex> <mensagem>")
        print("Exemplo: /msg a1b2c3d4e5f6g7h8 Oi, tudo bem?")
        print("Digite /quit para sair\n")

        receive_task = asyncio.create_task(self.receive_messages())

        try:
            while True:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, "> "
                )

                if user_input.lower() == "/quit":
                    logger.info("Encerrando...")
                    break

                if user_input.startswith("/msg "):
                    parts = user_input[5:].split(" ", 1)
                    if len(parts) >= 2:
                        recipient_id_str = parts[0]
                        message = parts[1]

                        try:
                            recipient_id = bytes.fromhex(recipient_id_str)
                            if len(recipient_id) != 16:
                                print("ID do destinatário deve ter 32 caracteres hex")
                                continue

                            await self.send_message(
                                recipient_id_str[:8],
                                recipient_id,
                                message
                            )
                        except ValueError:
                            print("ID inválido (deve ser hexadecimal)")

        finally:
            receive_task.cancel()
            if self.writer:
                self.writer.close()
                await self.writer.wait_closed()


async def main():
    import sys

    username = sys.argv[1] if len(sys.argv) > 1 else "Usuário"

    client = SecureMessagingClient(
        username=username,
        server_host="127.0.0.1",
        server_port=9999
    )

    if await client.connect():
        await client.interactive_session()
    else:
        logger.error("Falha ao conectar ao servidor")


if __name__ == "__main__":
    asyncio.run(main())
