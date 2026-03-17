#!/usr/bin/env python3
"""Tests for token encryption service"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

from token_service import TokenService
import tempfile
import os

def test_encrypt_decrypt_token():
    """Test token encryption and decryption"""
    # Create a temporary path (don't create the file)
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        key_path = tmp.name
    # Delete the file so TokenService creates it
    os.unlink(key_path)

    try:
        service = TokenService(key_path)
        original_token = "test_token_12345"

        # Encrypt
        encrypted = service.encrypt(original_token)
        assert encrypted != original_token, "Encrypted token should differ from original"
        assert len(encrypted) > 0, "Encrypted token should not be empty"

        # Decrypt
        decrypted = service.decrypt(encrypted)
        assert decrypted == original_token, "Decrypted token should match original"

    finally:
        if os.path.exists(key_path):
            os.unlink(key_path)

def test_mask_token():
    """Test token masking for display"""
    service = TokenService()

    # Long token
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.very_long_token_here"
    masked = service.mask_token(token)
    assert "..." in masked, "Masked token should contain ..."
    assert len(masked) < len(token), "Masked token should be shorter"

    # Short token
    short_token = "abc"
    masked = service.mask_token(short_token)
    assert len(masked) <= len(short_token), "Masked short token should not be longer"
