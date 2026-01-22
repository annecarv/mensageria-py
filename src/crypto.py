import os
import struct
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend


class ECDHEKeyExchange:

    def __init__(self):
        self.private_key = ec.generate_private_key(
            ec.SECP256R1(), default_backend()
        )
        self.public_key = self.private_key.public_key()

    def get_public_key_bytes(self):
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.CompressedPoint
        )

    def compute_shared_secret(self, peer_public_key_bytes):
        peer_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(), peer_public_key_bytes
        )

        shared_secret = self.private_key.exchange(
            ec.ECDH(), peer_public_key
        )

        return shared_secret


class RSASignature:

    def __init__(self, private_key=None):
        if private_key is None:
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
        else:
            self.private_key = private_key

        self.public_key = self.private_key.public_key()

    def get_public_key_pem(self):
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def get_private_key_pem(self):
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

    def sign(self, data):
        signature = self.private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature

    @staticmethod
    def verify(public_key_pem, signature, data):
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem, backend=default_backend()
            )
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False


class HKDFKeyDerivation:

    @staticmethod
    def derive_keys(shared_secret, salt, label_c2s="c2s", label_s2c="s2c"):
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=b'',
            backend=default_backend()
        )
        prk = hkdf.derive(shared_secret)

        hkdf_c2s = HKDF(
            algorithm=hashes.SHA256(),
            length=16,
            salt=b'',
            info=label_c2s.encode(),
            backend=default_backend()
        )
        key_c2s = hkdf_c2s.derive(prk)

        hkdf_s2c = HKDF(
            algorithm=hashes.SHA256(),
            length=16,
            salt=b'',
            info=label_s2c.encode(),
            backend=default_backend()
        )
        key_s2c = hkdf_s2c.derive(prk)

        return key_c2s, key_s2c


class AESGCMCipher:

    def __init__(self, key):
        if len(key) != 16:
            raise ValueError("Chave AES-128 deve ter 16 bytes")
        self.key = key

    def encrypt(self, nonce, plaintext, aad=b''):
        cipher = AESGCM(self.key)
        ciphertext = cipher.encrypt(nonce, plaintext, aad)
        return ciphertext

    def decrypt(self, nonce, ciphertext, aad=b''):
        try:
            cipher = AESGCM(self.key)
            plaintext = cipher.decrypt(nonce, ciphertext, aad)
            return plaintext
        except Exception:
            return None


def generate_nonce():
    return os.urandom(12)


def bytes_to_int(data):
    return int.from_bytes(data, byteorder='big')


def int_to_bytes(value, length):
    return value.to_bytes(length, byteorder='big')
