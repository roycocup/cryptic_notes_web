import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from firebase_admin import firestore

# Prevent Firebase from initializing during tests
@pytest.fixture(autouse=True)
def mock_firebase_init():
    """Prevent Firebase from initializing during tests"""
    with patch('config.firebase_admin.initialize_app'):
        with patch('config.firestore.client') as mock_client:
            mock_db = Mock()
            mock_client.return_value = mock_db
            yield


@pytest.fixture
def mock_firestore_doc():
    """Create a mock Firestore document"""
    doc = Mock()
    doc.id = "test_note_id"
    doc.exists = True
    doc.to_dict.return_value = {
        "ciphertext": "test_ciphertext",
        "iv": "test_iv",
        "priority": None,
        "createdAt": datetime(2024, 1, 1),
        "updatedAt": datetime(2024, 1, 2),
    }
    return doc


@pytest.fixture
def mock_firestore_collection(mock_firestore_doc):
    """Create a mock Firestore collection"""
    collection = Mock()
    collection.document.return_value.get.return_value = mock_firestore_doc
    collection.document.return_value.update = Mock()
    collection.document.return_value.delete = Mock()
    collection.add.return_value = (None, mock_firestore_doc)
    collection.order_by.return_value.get.return_value = [mock_firestore_doc]
    return collection


@pytest.fixture
def mock_db(mock_firestore_collection):
    """Mock the Firestore database"""
    db = Mock()
    db.collection.return_value.document.return_value.collection.return_value = mock_firestore_collection
    return db


@pytest.fixture
def sample_mnemonic():
    """Sample mnemonic for testing"""
    return "word1 word2 word3 word4 word5 word6"


@pytest.fixture
def sample_encrypted_note():
    """Sample encrypted note data"""
    return {
        "ciphertext": "test_ciphertext",
        "iv": "test_iv",
        "priority": None,
        "createdAt": datetime(2024, 1, 1),
        "updatedAt": datetime(2024, 1, 2),
    }
