from typing import Optional
from fastapi import Form, Request, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os
from firebase_admin import firestore
from config import SESSION_COOKIE_NAME, SESSION_MAX_AGE, USE_HTTPS, db
from crypto import normalize_mnemonic, derive_user_id, encrypt_note, decrypt_note, generate_mnemonic
from database import fetch_notes_for_mnemonic, fetch_encrypted_notes_for_user_id, get_database_stats

router = APIRouter()
base_dir = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(base_dir, "templates"))


def set_secure_cookie(response, mnemonic: str):
    """Set secure cookie with mnemonic."""
    response.set_cookie(
        SESSION_COOKIE_NAME,
        mnemonic,
        max_age=SESSION_MAX_AGE,
        httponly=True,  # SECURITY: Prevent JavaScript access
        secure=USE_HTTPS,  # SECURITY: Only send over HTTPS in production
        samesite="lax",
    )


def get_mnemonic_from_request(request: Request, form_mnemonic: Optional[str] = None) -> Optional[str]:
    """Get mnemonic from cookie (preferred) or form (backward compatibility)."""
    mnemonic = request.cookies.get(SESSION_COOKIE_NAME)
    if mnemonic:
        return normalize_mnemonic(mnemonic)
    if form_mnemonic:
        return normalize_mnemonic(form_mnemonic)
    return None


def get_notes(request: Request, mnemonic: str) -> HTMLResponse:
    normalized = normalize_mnemonic(mnemonic)
    user_id = derive_user_id(normalized)
    encrypted_notes = fetch_encrypted_notes_for_user_id(user_id)
    response = templates.TemplateResponse("index.html", {
        "request": request,
        "encrypted_notes": encrypted_notes,
        "user_id": user_id,
        "has_mnemonic": True,
        "new_account": False
    })
    set_secure_cookie(response, normalized)
    return response


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    mnemonic = request.cookies.get(SESSION_COOKIE_NAME)
    encrypted_notes = None
    user_id = None
    
    if mnemonic:
        normalized = normalize_mnemonic(mnemonic)
        user_id = derive_user_id(normalized)
        encrypted_notes = fetch_encrypted_notes_for_user_id(user_id)
    
    new_account = request.query_params.get("new_account") == "1"
    return templates.TemplateResponse("index.html", {
        "request": request,
        "encrypted_notes": encrypted_notes,
        "user_id": user_id,
        "has_mnemonic": mnemonic is not None,
        "new_account": new_account
    })


@router.post("/", response_class=HTMLResponse)
async def post_get_notes(request: Request, mnemonic: str = Form(...)):
    return get_notes(request, mnemonic)


@router.get("/create-account", response_class=HTMLResponse)
async def create_account_get(request: Request):
    return templates.TemplateResponse("create_account.html", {"request": request, "mnemonic": None})


@router.post("/create-account", response_class=HTMLResponse)
async def create_account_post(request: Request):
    generated = generate_mnemonic()
    normalized = normalize_mnemonic(generated)
    response = RedirectResponse(url="./?new_account=1", status_code=303)
    set_secure_cookie(response, normalized)
    return response


@router.post("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    response = RedirectResponse(url="./", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.get("/api/mnemonic", response_class=JSONResponse)
async def get_mnemonic_for_decryption(request: Request):
    """Get mnemonic for client-side decryption.
    SECURITY: This endpoint should only be used for client-side decryption.
    Consider using a more secure method like session tokens in the future.
    """
    mnemonic = request.cookies.get(SESSION_COOKIE_NAME)
    if not mnemonic:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    return JSONResponse({"mnemonic": normalize_mnemonic(mnemonic)})


@router.post("/edit", response_class=HTMLResponse)
async def edit_note(request: Request, note_id: str = Form(...), mnemonic: Optional[str] = Form(None)):
    active_mnemonic = get_mnemonic_from_request(request, mnemonic)
    if not active_mnemonic:
        encrypted_notes = None
        return templates.TemplateResponse("index.html", {
            "request": request,
            "encrypted_notes": encrypted_notes,
            "user_id": None,
            "has_mnemonic": False,
            "error": "Not authenticated"
        })
    
    user_id = derive_user_id(active_mnemonic)
    doc = db.collection("users").document(user_id).collection("notes").document(note_id).get()
    if not doc.exists:
        encrypted_notes = fetch_encrypted_notes_for_user_id(user_id)
        return templates.TemplateResponse("index.html", {
            "request": request,
            "encrypted_notes": encrypted_notes,
            "user_id": user_id,
            "has_mnemonic": True,
            "error": "Note not found"
        })
    
    data = doc.to_dict()
    # Return encrypted data - client will decrypt
    return templates.TemplateResponse("edit.html", {
        "request": request,
        "note_id": note_id,
        "ciphertext": data.get("ciphertext", ""),
        "iv": data.get("iv", ""),
        "nsfw": data.get("nsfw", False),
        "has_mnemonic": True,
    })


@router.post("/save", response_class=HTMLResponse)
async def save_note(
    request: Request,
    note_id: str = Form(...),
    title: str = Form(...),
    body: str = Form(...),
    nsfw: Optional[str] = Form(None),
    mnemonic: Optional[str] = Form(None)
):
    active_mnemonic = get_mnemonic_from_request(request, mnemonic)
    if not active_mnemonic:
        encrypted_notes = None
        return templates.TemplateResponse("index.html", {
            "request": request,
            "encrypted_notes": encrypted_notes,
            "user_id": None,
            "has_mnemonic": False,
            "error": "Not authenticated"
        })
    
    user_id = derive_user_id(active_mnemonic)
    ciphertext, iv = encrypt_note(title, body, active_mnemonic)
    
    db.collection("users").document(user_id).collection("notes").document(note_id).update({
        "ciphertext": ciphertext,
        "iv": iv,
        "nsfw": nsfw == "1",
        "updatedAt": firestore.SERVER_TIMESTAMP,
    })
    
    # Redirect back to notes list
    return RedirectResponse(url="./", status_code=303)


@router.post("/new", response_class=HTMLResponse)
async def new_note(
    request: Request,
    mnemonic: Optional[str] = Form(None),
    title: Optional[str] = Form(""),
    body: Optional[str] = Form(""),
    nsfw: Optional[str] = Form(None),
):
    active_mnemonic = get_mnemonic_from_request(request, mnemonic)
    if not active_mnemonic:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "encrypted_notes": None, "user_id": None, "has_mnemonic": False, "error": "Missing session mnemonic."},
        )
    normalized = normalize_mnemonic(active_mnemonic)
    user_id = derive_user_id(normalized)
    title_val = (title or "").strip()
    body_val = (body or "").strip()
    ciphertext, iv = encrypt_note(title_val, body_val, normalized)
    db.collection("users").document(user_id).collection("notes").add({
        "ciphertext": ciphertext,
        "iv": iv,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
        "priority": None,
        "fontScale": 1.0,
        "nsfw": nsfw == "1",
    })
    return RedirectResponse(url="./", status_code=303)


@router.post("/priority", response_class=HTMLResponse)
async def update_priority(
    request: Request,
    note_id: str = Form(...),
    priority: str = Form(""),
    mnemonic: Optional[str] = Form(None),
):
    active_mnemonic = get_mnemonic_from_request(request, mnemonic)
    if not active_mnemonic:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "encrypted_notes": None, "user_id": None, "has_mnemonic": False, "error": "Missing session mnemonic."},
        )
    normalized = normalize_mnemonic(active_mnemonic)
    priority_value: Optional[int] = None
    if priority.strip():
        try:
            priority_value = int(priority.strip())
        except ValueError:
            user_id = derive_user_id(normalized)
            encrypted_notes = fetch_encrypted_notes_for_user_id(user_id)
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "encrypted_notes": encrypted_notes,
                    "user_id": user_id,
                    "has_mnemonic": True,
                    "error": "Priority must be a whole number.",
                },
            )
    user_id = derive_user_id(normalized)
    db.collection("users").document(user_id).collection("notes").document(note_id).update({
        "priority": priority_value,
    })
    return RedirectResponse(url="./", status_code=303)


@router.post("/delete", response_class=HTMLResponse)
async def delete_note(
    request: Request,
    note_id: str = Form(...),
    mnemonic: Optional[str] = Form(None),
):
    active_mnemonic = get_mnemonic_from_request(request, mnemonic)
    if not active_mnemonic:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "encrypted_notes": None, "user_id": None, "has_mnemonic": False, "error": "Missing session mnemonic."},
        )
    normalized = normalize_mnemonic(active_mnemonic)
    user_id = derive_user_id(normalized)
    db.collection("users").document(user_id).collection("notes").document(note_id).delete()
    return RedirectResponse(url="./", status_code=303)


@router.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


@router.get("/stats", response_class=HTMLResponse)
async def stats(request: Request):
    stats = get_database_stats()
    return templates.TemplateResponse("stats.html", {
        "request": request,
        "user_count": stats["user_count"],
        "total_notes": stats["total_notes"],
    })
