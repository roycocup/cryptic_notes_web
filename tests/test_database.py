import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from database import fetch_notes_for_mnemonic
from crypto import encrypt_note


class TestFetchNotesForMnemonic:
    @patch('database.db')
    def test_fetch_notes_single_note(self, mock_db):
        mnemonic = "word1 word2 word3 word4 word5 word6"
        
        # Create encrypted note data
        ciphertext, iv = encrypt_note("Test Title", "Test body content", mnemonic)
        
        # Mock Firestore document
        mock_doc = Mock()
        mock_doc.id = "note1"
        mock_doc.to_dict.return_value = {
            "ciphertext": ciphertext,
            "iv": iv,
            "priority": None,
            "createdAt": datetime(2024, 1, 1),
            "updatedAt": datetime(2024, 1, 2),
        }
        
        # Mock Firestore collection query
        mock_collection = Mock()
        mock_query = Mock()
        mock_query.get.return_value = [mock_doc]
        mock_collection.order_by.return_value = mock_query
        
        mock_user_doc = Mock()
        mock_user_doc.collection.return_value = mock_collection
        mock_db.collection.return_value.document.return_value = mock_user_doc
        
        notes = fetch_notes_for_mnemonic(mnemonic)
        
        assert len(notes) == 1
        assert notes[0]["id"] == "note1"
        assert notes[0]["title"] == "Test Title"
        assert "Test body content" in notes[0]["body"] or notes[0]["body"] == "Test body content"
        assert notes[0]["priority"] is None

    @patch('database.db')
    def test_fetch_notes_multiple_notes(self, mock_db):
        mnemonic = "word1 word2 word3 word4 word5 word6"
        
        # Create multiple encrypted notes
        ciphertext1, iv1 = encrypt_note("Title 1", "Body 1", mnemonic)
        ciphertext2, iv2 = encrypt_note("Title 2", "Body 2", mnemonic)
        
        mock_doc1 = Mock()
        mock_doc1.id = "note1"
        mock_doc1.to_dict.return_value = {
            "ciphertext": ciphertext1,
            "iv": iv1,
            "priority": 1,
            "createdAt": datetime(2024, 1, 1),
            "updatedAt": datetime(2024, 1, 2),
        }
        
        mock_doc2 = Mock()
        mock_doc2.id = "note2"
        mock_doc2.to_dict.return_value = {
            "ciphertext": ciphertext2,
            "iv": iv2,
            "priority": None,
            "createdAt": datetime(2024, 1, 3),
            "updatedAt": datetime(2024, 1, 4),
        }
        
        mock_collection = Mock()
        mock_query = Mock()
        mock_query.get.return_value = [mock_doc1, mock_doc2]
        mock_collection.order_by.return_value = mock_query
        
        mock_user_doc = Mock()
        mock_user_doc.collection.return_value = mock_collection
        mock_db.collection.return_value.document.return_value = mock_user_doc
        
        notes = fetch_notes_for_mnemonic(mnemonic)
        
        assert len(notes) == 2
        # Notes with priority should come first
        assert notes[0]["priority"] == 1
        assert notes[1]["priority"] is None

    @patch('database.db')
    def test_fetch_notes_empty_collection(self, mock_db):
        mnemonic = "word1 word2 word3 word4 word5 word6"
        
        mock_collection = Mock()
        mock_query = Mock()
        mock_query.get.return_value = []
        mock_collection.order_by.return_value = mock_query
        
        mock_user_doc = Mock()
        mock_user_doc.collection.return_value = mock_collection
        mock_db.collection.return_value.document.return_value = mock_user_doc
        
        notes = fetch_notes_for_mnemonic(mnemonic)
        
        assert len(notes) == 0

    @patch('database.db')
    def test_fetch_notes_decryption_failure_handled(self, mock_db):
        mnemonic = "word1 word2 word3 word4 word5 word6"
        
        # Create a document with invalid ciphertext
        mock_doc = Mock()
        mock_doc.id = "note1"
        mock_doc.to_dict.return_value = {
            "ciphertext": "invalid_ciphertext",
            "iv": "invalid_iv",
            "priority": None,
            "createdAt": datetime(2024, 1, 1),
            "updatedAt": datetime(2024, 1, 2),
        }
        
        mock_collection = Mock()
        mock_query = Mock()
        mock_query.get.return_value = [mock_doc]
        mock_collection.order_by.return_value = mock_query
        
        mock_user_doc = Mock()
        mock_user_doc.collection.return_value = mock_collection
        mock_db.collection.return_value.document.return_value = mock_user_doc
        
        # Should not raise exception, but skip the note
        notes = fetch_notes_for_mnemonic(mnemonic)
        
        # Note with decryption failure should be skipped
        assert len(notes) == 0
