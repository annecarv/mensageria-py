import os
import sys
from crypto import RSASignature


def initialize_server_certificates(cert_dir: str = "certs"):
    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)

    cert_path = os.path.join(cert_dir, "server.crt")
    key_path = os.path.join(cert_dir, "server.key")

    if os.path.exists(cert_path) and os.path.exists(key_path):
        print(f"Certificados já existem em {cert_dir}")
        return

    print("Gerando par de chaves RSA-2048")
    rsa = RSASignature()

    with open(cert_path, 'wb') as f:
        f.write(rsa.get_public_key_pem())
    print(f"Certificado salvo: {cert_path}")

    with open(key_path, 'wb') as f:
        f.write(rsa.get_private_key_pem())
    print(f"Chave privada salva: {key_path}")

    print("Certificados inicializados")


if __name__ == "__main__":
    initialize_server_certificates()
