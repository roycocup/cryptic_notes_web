import pytest
from crypto import (
    normalize_mnemonic,
    generate_mnemonic,
    derive_user_id,
    derive_email,
    derive_password,
    derive_key,
    encrypt_note,
    decrypt_note,
)


class TestGenerateMnemonic:
    def test_returns_twelve_words(self):
        phrase = generate_mnemonic()
        words = phrase.split()
        assert len(words) == 12

    def test_normalized_format(self):
        phrase = generate_mnemonic()
        assert phrase == normalize_mnemonic(phrase)


class TestNormalizeMnemonic:
    def test_normalize_basic(self):
        assert normalize_mnemonic("word1 word2 word3") == "word1 word2 word3"

    def test_normalize_lowercase(self):
        assert normalize_mnemonic("WORD1 WORD2 WORD3") == "word1 word2 word3"

    def test_normalize_extra_spaces(self):
        assert normalize_mnemonic("word1  word2   word3") == "word1 word2 word3"

    def test_normalize_leading_trailing_spaces(self):
        assert normalize_mnemonic("  word1 word2 word3  ") == "word1 word2 word3"

    def test_normalize_mixed_case_and_spaces(self):
        assert normalize_mnemonic("  WORD1  word2  WORD3  ") == "word1 word2 word3"


class TestDeriveUserId:
    def test_derive_user_id_consistent(self):
        mnemonic = "word1 word2 word3"
        user_id1 = derive_user_id(mnemonic)
        user_id2 = derive_user_id(mnemonic)
        assert user_id1 == user_id2
        assert len(user_id1) == 64  # SHA256 hex digest length

    def test_derive_user_id_different_mnemonics(self):
        user_id1 = derive_user_id("word1 word2 word3")
        user_id2 = derive_user_id("word4 word5 word6")
        assert user_id1 != user_id2

    def test_derive_user_id_normalizes(self):
        user_id1 = derive_user_id("WORD1 WORD2 WORD3")
        user_id2 = derive_user_id("word1 word2 word3")
        assert user_id1 == user_id2


class TestDeriveEmail:
    def test_derive_email_consistent(self):
        mnemonic = "word1 word2 word3"
        email1 = derive_email(mnemonic)
        email2 = derive_email(mnemonic)
        assert email1 == email2
        assert email1.startswith("user.")
        assert email1.endswith("@crypticnotes.local")

    def test_derive_email_different_mnemonics(self):
        email1 = derive_email("word1 word2 word3")
        email2 = derive_email("word4 word5 word6")
        assert email1 != email2

    def test_derive_email_normalizes(self):
        email1 = derive_email("WORD1 WORD2 WORD3")
        email2 = derive_email("word1 word2 word3")
        assert email1 == email2

    def test_derive_email_format(self):
        mnemonic = "word1 word2 word3"
        email = derive_email(mnemonic)
        user_id_hash = derive_user_id(mnemonic)
        assert email == f"user.{user_id_hash}@crypticnotes.local"


class TestDerivePassword:
    def test_derive_password_consistent(self):
        mnemonic = "word1 word2 word3"
        password1 = derive_password(mnemonic)
        password2 = derive_password(mnemonic)
        assert password1 == password2
        assert len(password1) > 0

    def test_derive_password_different_mnemonics(self):
        password1 = derive_password("word1 word2 word3")
        password2 = derive_password("word4 word5 word6")
        assert password1 != password2

    def test_derive_password_normalizes(self):
        password1 = derive_password("WORD1 WORD2 WORD3")
        password2 = derive_password("word1 word2 word3")
        assert password1 == password2

    def test_derive_password_different_from_user_id(self):
        mnemonic = "word1 word2 word3"
        user_id = derive_user_id(mnemonic)
        password = derive_password(mnemonic)
        # Password should be different from user_id (different derivation)
        assert password != user_id


class TestDeriveKey:
    def test_derive_key_consistent(self):
        mnemonic = "word1 word2 word3"
        key1 = derive_key(mnemonic)
        key2 = derive_key(mnemonic)
        assert key1 == key2
        assert len(key1) == 32  # SHA256 digest length in bytes

    def test_derive_key_different_mnemonics(self):
        key1 = derive_key("word1 word2 word3")
        key2 = derive_key("word4 word5 word6")
        assert key1 != key2


class TestEncryptDecryptNote:
    def test_encrypt_decrypt_roundtrip(self):
        mnemonic = "word1 word2 word3 word4 word5 word6"
        title = "Test Title"
        body = "Test body content"
        
        ciphertext, iv = encrypt_note(title, body, mnemonic)
        assert ciphertext is not None
        assert iv is not None
        
        decrypted = decrypt_note(ciphertext, iv, mnemonic)
        assert decrypted["title"] == title
        assert decrypted["body"] == body

    def test_encrypt_decrypt_empty_strings(self):
        mnemonic = "word1 word2 word3 word4 word5 word6"
        title = ""
        body = ""
        
        ciphertext, iv = encrypt_note(title, body, mnemonic)
        decrypted = decrypt_note(ciphertext, iv, mnemonic)
        assert decrypted["title"] == ""
        assert decrypted["body"] == ""

    def test_encrypt_decrypt_long_content(self):
        mnemonic = "word1 word2 word3 word4 word5 word6"
        title = "A" * 100
        body = "B" * 1000
        
        ciphertext, iv = encrypt_note(title, body, mnemonic)
        decrypted = decrypt_note(ciphertext, iv, mnemonic)
        assert decrypted["title"] == title
        assert decrypted["body"] == body

    def test_encrypt_decrypt_special_characters(self):
        mnemonic = "word1 word2 word3 word4 word5 word6"
        title = "Title with émojis 🎉"
        body = "Body with\nnewlines\tand\ttabs"
        
        ciphertext, iv = encrypt_note(title, body, mnemonic)
        decrypted = decrypt_note(ciphertext, iv, mnemonic)
        assert decrypted["title"] == title
        assert decrypted["body"] == body

    def test_encrypt_different_iv_each_time(self):
        mnemonic = "word1 word2 word3 word4 word5 word6"
        title = "Test"
        body = "Test"
        
        ciphertext1, iv1 = encrypt_note(title, body, mnemonic)
        ciphertext2, iv2 = encrypt_note(title, body, mnemonic)
        
        # IVs should be different (random)
        assert iv1 != iv2
        # Ciphertexts should be different (due to different IVs)
        assert ciphertext1 != ciphertext2
        
        # But both should decrypt to the same content
        decrypted1 = decrypt_note(ciphertext1, iv1, mnemonic)
        decrypted2 = decrypt_note(ciphertext2, iv2, mnemonic)
        assert decrypted1 == decrypted2

    def test_decrypt_wrong_mnemonic_fails(self):
        mnemonic1 = "word1 word2 word3 word4 word5 word6"
        mnemonic2 = "word7 word8 word9 word10 word11 word12"
        title = "Test"
        body = "Test"
        
        ciphertext, iv = encrypt_note(title, body, mnemonic1)
        
        # Decrypting with wrong mnemonic should raise an exception
        with pytest.raises(Exception):
            decrypt_note(ciphertext, iv, mnemonic2)
