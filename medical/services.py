from cryptography.fernet import Fernet
from django.conf import settings


def encrypt_bytes(content: bytes) -> bytes:
    cipher = Fernet(settings.DOCUMENT_ENCRYPTION_KEY.encode())
    return cipher.encrypt(content)


def decrypt_bytes(content: bytes) -> bytes:
    cipher = Fernet(settings.DOCUMENT_ENCRYPTION_KEY.encode())
    return cipher.decrypt(content)
