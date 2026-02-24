from firebase_admin import firestore
from config import db, NOTES_SIZE_LIMIT
from crypto import derive_user_id, decrypt_note
from utils import truncate_words, render_markdown, note_sort_key


def fetch_encrypted_notes_for_user_id(user_id: str) -> list[dict]:
    """Fetch encrypted notes for a user_id without decrypting them."""
    print(f"Looking up notes for user_id: {user_id}")

    notes_ref = db.collection("users").document(user_id).collection("notes")
    docs = list(notes_ref.order_by("updatedAt", direction=firestore.Query.DESCENDING).get())
    print(f"Found {len(docs)} documents")

    notes = []
    for doc in docs:
        data = doc.to_dict()
        # Convert Firestore timestamps to dict format for JSON serialization
        created_at = data.get("createdAt")
        updated_at = data.get("updatedAt")
        
        created_at_dict = None
        if created_at:
            # Convert to dict with _seconds for JSON serialization
            created_at_dict = {"_seconds": int(created_at.timestamp())}
        
        updated_at_dict = None
        if updated_at:
            updated_at_dict = {"_seconds": int(updated_at.timestamp())}
        
        notes.append({
            "id": doc.id,
            "ciphertext": data.get("ciphertext", ""),
            "iv": data.get("iv", ""),
            "priority": data.get("priority"),
            "nsfw": data.get("nsfw", False),
            "created_at": created_at_dict,
            "updated_at": updated_at_dict,
        })

    return notes


def fetch_notes_for_mnemonic(mnemonic: str) -> list[dict]:
    user_id = derive_user_id(mnemonic)
    print(f"Looking up notes for user_id: {user_id}")

    notes_ref = db.collection("users").document(user_id).collection("notes")
    docs = list(notes_ref.order_by("updatedAt", direction=firestore.Query.DESCENDING).get())
    print(f"Found {len(docs)} documents")

    notes = []
    for doc in docs:
        data = doc.to_dict()
        try:
            decrypted = decrypt_note(data.get("ciphertext", ""), data.get("iv", ""), mnemonic)
            body = decrypted.get("body", "")
            truncated_body = truncate_words(body, NOTES_SIZE_LIMIT)
            notes.append({
                "id": doc.id,
                "title": decrypted.get("title", "Untitled"),
                "body": body,
                "body_html": render_markdown(body),
                "priority": data.get("priority"),
                "nsfw": data.get("nsfw", False),
                "created_at": data.get("createdAt"),
                "updated_at": data.get("updatedAt"),
            })
        except Exception as e:
            print(f"Failed to decrypt note {doc.id}: {e}")

    return sorted(notes, key=note_sort_key)


def get_database_stats() -> dict:
    """Get basic statistics about the database."""
    # Use list_documents() instead of get() because parent documents
    # that only contain subcollections don't show up in get()
    users_ref = db.collection("users")
    user_docs = list(users_ref.list_documents())
    
    user_count = len(user_docs)
    total_notes = 0
    
    for user_doc in user_docs:
        notes = user_doc.collection("notes").get()
        total_notes += len(list(notes))
    
    return {
        "user_count": user_count,
        "total_notes": total_notes,
    }
