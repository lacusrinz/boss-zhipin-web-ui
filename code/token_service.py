#!/usr/bin/env python3
"""
Token encryption service for secure storage
"""
import base64
import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet


class TokenService:
    """Service for encrypting and decrypting sensitive tokens"""

    def __init__(self, key_path: str = None):
        """
        Initialize token service

        Args:
            key_path: Path to encryption key file (optional, uses default if not provided)
        """
        if key_path is None:
            # Default to project root
            if getattr(sys, 'frozen', False):
                base_dir = Path(sys.executable).parent
            else:
                base_dir = Path(__file__).parent.parent
            key_path = base_dir / "data" / "encryption_key"

        self.key_path = Path(key_path)
        self.key_path.parent.mkdir(parents=True, exist_ok=True)

        self._key = self._get_or_create_key()
        self.cipher = Fernet(self._key)

    def _get_or_create_key(self) -> bytes:
        """
        Get existing key or create new one

        Returns:
            bytes: Encryption key
        """
        if self.key_path.exists():
            with open(self.key_path, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(self.key_path, 'wb') as f:
                f.write(key)
            # Set file permissions to read/write only
            os.chmod(self.key_path, 0o600)
            return key

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext

        Args:
            plaintext: Text to encrypt

        Returns:
            str: Encrypted text (base64 encoded)
        """
        if not plaintext:
            return ""

        encrypted_bytes = self.cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted_bytes).decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext

        Args:
            ciphertext: Encrypted text (base64 encoded)

        Returns:
            str: Decrypted plaintext
        """
        if not ciphertext:
            return ""

        try:
            encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

    def mask_token(self, token: str, show_start: int = 8, show_end: int = 4) -> str:
        """
        Mask token for display purposes

        Args:
            token: Original token
            show_start: Number of characters to show at start
            show_end: Number of characters to show at end

        Returns:
            str: Masked token
        """
        if not token:
            return ""

        if len(token) <= show_start + show_end:
            return token

        return f"{token[:show_start]}...{token[-show_end:]}"
