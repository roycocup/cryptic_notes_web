import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient
from main import app
from crypto import encrypt_note


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_mnemonic():
    return "word1 word2 word3 word4 word5 word6"


@pytest.fixture
def mock_note_data(sample_mnemonic):
    ciphertext, iv = encrypt_note("Test Title", "Test body content", sample_mnemonic)
    return {
        "ciphertext": ciphertext,
        "iv": iv,
        "priority": None,
        "createdAt": datetime(2024, 1, 1),
        "updatedAt": datetime(2024, 1, 2),
    }


class TestIndexRoute:
    def test_index_no_cookie(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "notes" in response.text.lower() or "mnemonic" in response.text.lower()

    def test_index_with_cookie(self, client, sample_mnemonic):
        with patch('routes.fetch_notes_for_mnemonic') as mock_fetch:
            mock_fetch.return_value = []
            response = client.get("/", cookies={"mnemonic": sample_mnemonic})
            assert response.status_code == 200


class TestGetNotesRoute:
    def test_post_get_notes_with_mnemonic(self, client, sample_mnemonic):
        with patch('routes.fetch_notes_for_mnemonic') as mock_fetch:
            mock_fetch.return_value = []
            response = client.post("/", data={"mnemonic": sample_mnemonic})
            assert response.status_code == 200
            # Check that cookie is set
            assert "mnemonic" in response.cookies

    def test_post_get_notes_normalizes_mnemonic(self, client):
        with patch('routes.fetch_notes_for_mnemonic') as mock_fetch:
            mock_fetch.return_value = []
            response = client.post("/", data={"mnemonic": "  WORD1  WORD2  WORD3  "})
            assert response.status_code == 200
            # Cookie should be normalized (may have quotes, so strip them)
            cookie_value = response.cookies.get("mnemonic")
            assert cookie_value.strip('"') == "word1 word2 word3"


class TestLogoutRoute:
    def test_logout_redirects_and_deletes_cookie(self, client):
        response = client.post("/logout", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers.get("location") in ("./", ".", "/")


class TestCreateAccountRoute:
    def test_create_account_get(self, client):
        response = client.get("/create-account")
        assert response.status_code == 200
        assert "create" in response.text.lower() or "generate" in response.text.lower()

    @patch('routes.generate_mnemonic')
    def test_create_account_post_redirects_and_sets_cookie(self, mock_generate, client, sample_mnemonic):
        mock_generate.return_value = sample_mnemonic
        response = client.post("/create-account", follow_redirects=False)
        assert response.status_code == 303
        assert "new_account=1" in (response.headers.get("location") or "")
        assert "mnemonic" in response.cookies


class TestEditNoteRoute:
    @patch('routes.db')
    def test_edit_note_success(self, mock_db, client, sample_mnemonic, mock_note_data):
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = mock_note_data
        
        mock_collection = Mock()
        mock_collection.document.return_value.get.return_value = mock_doc
        
        mock_user_doc = Mock()
        mock_user_doc.collection.return_value = mock_collection
        mock_db.collection.return_value.document.return_value = mock_user_doc
        
        response = client.post(
            "/edit",
            data={"note_id": "test_note_id", "mnemonic": sample_mnemonic}
        )
        assert response.status_code == 200

    @patch('routes.db')
    def test_edit_note_not_found(self, mock_db, client, sample_mnemonic):
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_collection = Mock()
        mock_collection.document.return_value.get.return_value = mock_doc
        
        mock_user_doc = Mock()
        mock_user_doc.collection.return_value = mock_collection
        mock_db.collection.return_value.document.return_value = mock_user_doc
        
        response = client.post(
            "/edit",
            data={"note_id": "nonexistent", "mnemonic": sample_mnemonic}
        )
        assert response.status_code == 200
        # Should show error message
        assert "error" in response.text.lower() or "not found" in response.text.lower()


class TestSaveNoteRoute:
    @patch('routes.db')
    def test_save_note_success(self, mock_db, client, sample_mnemonic):
        mock_collection = Mock()
        mock_collection.document.return_value.update = Mock()
        mock_user_doc = Mock()
        mock_user_doc.collection.return_value = mock_collection
        mock_db.collection.return_value.document.return_value = mock_user_doc

        response = client.post(
            "/save",
            data={
                "note_id": "test_note_id",
                "title": "Updated Title",
                "body": "Updated body",
                "mnemonic": sample_mnemonic
            },
            follow_redirects=False
        )
        assert response.status_code == 303
        assert response.headers.get("location") == "./"
        mock_collection.document.return_value.update.assert_called_once()


class TestNewNoteRoute:
    @patch('routes.db')
    def test_new_note_with_mnemonic(self, mock_db, client, sample_mnemonic):
        mock_doc = Mock()
        mock_doc.id = "new_note_id"
        mock_collection = Mock()
        mock_collection.add.return_value = (None, mock_doc)
        mock_user_doc = Mock()
        mock_user_doc.collection.return_value = mock_collection
        mock_db.collection.return_value.document.return_value = mock_user_doc

        response = client.post("/new", data={"mnemonic": sample_mnemonic}, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers.get("location") == "./"

    def test_new_note_no_mnemonic_no_cookie(self, client):
        """Creating a note without a session (no mnemonic, no cookie) returns error page."""
        response = client.post("/new")
        assert response.status_code == 200
        assert "error" in response.text.lower() or "missing" in response.text.lower()
        assert "mnemonic" in response.text.lower() or "session" in response.text.lower()

    @patch('routes.db')
    def test_new_note_with_cookie(self, mock_db, client, sample_mnemonic):
        mock_doc = Mock()
        mock_doc.id = "new_note_id"
        mock_collection = Mock()
        mock_collection.add.return_value = (None, mock_doc)
        mock_user_doc = Mock()
        mock_user_doc.collection.return_value = mock_collection
        mock_db.collection.return_value.document.return_value = mock_user_doc

        response = client.post("/new", cookies={"mnemonic": sample_mnemonic}, follow_redirects=False)
        assert response.status_code == 303


class TestUpdatePriorityRoute:
    @patch('routes.db')
    def test_update_priority_with_value(self, mock_db, client, sample_mnemonic):
        mock_collection = Mock()
        mock_collection.document.return_value.update = Mock()
        mock_user_doc = Mock()
        mock_user_doc.collection.return_value = mock_collection
        mock_db.collection.return_value.document.return_value = mock_user_doc

        response = client.post(
            "/priority",
            data={"note_id": "test_note_id", "priority": "5", "mnemonic": sample_mnemonic},
            follow_redirects=False
        )
        assert response.status_code == 303
        assert response.headers.get("location") == "./"
        call_args = mock_collection.document.return_value.update.call_args[0][0]
        assert call_args["priority"] == 5

    @patch('routes.db')
    def test_update_priority_empty_string(self, mock_db, client, sample_mnemonic):
        mock_collection = Mock()
        mock_collection.document.return_value.update = Mock()
        mock_user_doc = Mock()
        mock_user_doc.collection.return_value = mock_collection
        mock_db.collection.return_value.document.return_value = mock_user_doc

        response = client.post(
            "/priority",
            data={"note_id": "test_note_id", "priority": "", "mnemonic": sample_mnemonic},
            follow_redirects=False
        )
        assert response.status_code == 303
        call_args = mock_collection.document.return_value.update.call_args[0][0]
        assert call_args["priority"] is None

    def test_update_priority_invalid_number(self, client, sample_mnemonic):
        with patch('routes.fetch_notes_for_mnemonic') as mock_fetch:
            mock_fetch.return_value = []
            response = client.post(
                "/priority",
                cookies={"mnemonic": sample_mnemonic},
                data={
                    "note_id": "test_note_id",
                    "priority": "not_a_number"
                }
            )
            assert response.status_code == 200
            assert "error" in response.text.lower() or "number" in response.text.lower()


class TestDeleteNoteRoute:
    @patch('routes.db')
    def test_delete_note_success(self, mock_db, client, sample_mnemonic):
        mock_collection = Mock()
        mock_collection.document.return_value.delete = Mock()
        mock_user_doc = Mock()
        mock_user_doc.collection.return_value = mock_collection
        mock_db.collection.return_value.document.return_value = mock_user_doc

        response = client.post(
            "/delete",
            data={"note_id": "test_note_id", "mnemonic": sample_mnemonic},
            follow_redirects=False
        )
        assert response.status_code == 303
        assert response.headers.get("location") == "./"
        mock_collection.document.return_value.delete.assert_called_once()

    def test_delete_note_no_mnemonic(self, client):
        response = client.post("/delete", data={"note_id": "test_note_id"})
        assert response.status_code == 200
        assert "error" in response.text.lower() or "missing" in response.text.lower()


class TestStatsRoute:
    def test_stats_returns_200(self, client):
        with patch('routes.get_database_stats') as mock_stats:
            mock_stats.return_value = {"user_count": 10, "total_notes": 42}
            response = client.get("/stats")
        assert response.status_code == 200
        assert "10" in response.text or "42" in response.text or "user" in response.text.lower() or "note" in response.text.lower()


class TestFullFlow:
    """Integration-style tests: login, CRUD note, stats, logout, get new mnemonic."""

    @patch('routes.db')
    @patch('routes.fetch_notes_for_mnemonic')
    @patch('routes.get_database_stats')
    def test_login_new_note_edit_save_priority_delete_stats_logout(
        self, mock_stats, mock_fetch, mock_db, client, sample_mnemonic, mock_note_data
    ):
        mock_stats.return_value = {"user_count": 1, "total_notes": 1}
        mock_fetch.return_value = []
        mock_doc = Mock()
        mock_doc.id = "note_1"
        mock_doc.exists = True
        mock_doc.to_dict.return_value = mock_note_data
        mock_collection = Mock()
        mock_collection.document.return_value.get.return_value = mock_doc
        mock_collection.document.return_value.update = Mock()
        mock_collection.document.return_value.delete = Mock()
        mock_collection.add.return_value = (None, mock_doc)
        mock_collection.order_by.return_value.get.return_value = []
        mock_user_doc = Mock()
        mock_user_doc.collection.return_value = mock_collection
        mock_db.collection.return_value.document.return_value = mock_user_doc

        # Login (POST mnemonic)
        r = client.post("/", data={"mnemonic": sample_mnemonic})
        assert r.status_code == 200
        assert "mnemonic" in r.cookies

        # New note
        r = client.post("/new", data={"mnemonic": sample_mnemonic}, follow_redirects=True)
        assert r.status_code == 200
        assert "Cryptic Notes" in r.text

        # Edit note
        r = client.post("/edit", data={"note_id": "note_1", "mnemonic": sample_mnemonic})
        assert r.status_code == 200
        assert "edit" in r.text.lower() or "title" in r.text.lower()

        # Save note
        r = client.post(
            "/save",
            data={"note_id": "note_1", "title": "Done", "body": "Content", "mnemonic": sample_mnemonic},
            follow_redirects=True,
        )
        assert r.status_code == 200

        # Update priority
        r = client.post(
            "/priority",
            data={"note_id": "note_1", "priority": "1", "mnemonic": sample_mnemonic},
            follow_redirects=True,
        )
        assert r.status_code == 200

        # Delete note
        r = client.post(
            "/delete",
            data={"note_id": "note_1", "mnemonic": sample_mnemonic},
            follow_redirects=True,
        )
        assert r.status_code == 200

        # Stats
        r = client.get("/stats")
        assert r.status_code == 200
        assert "1" in r.text

        # Logout
        r = client.post("/logout", follow_redirects=True)
        assert r.status_code == 200

    def test_create_account_flow(self, client):
        with patch('routes.generate_mnemonic') as mock_gen:
            mock_gen.return_value = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
            r = client.get("/create-account")
            assert r.status_code == 200
            assert "create" in r.text.lower() or "generate" in r.text.lower()
            r = client.post("/create-account", follow_redirects=False)
            assert r.status_code == 303
            assert "new_account=1" in (r.headers.get("location") or "")
            assert "mnemonic" in r.cookies
