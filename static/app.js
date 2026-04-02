// Client-side note decryption and rendering
console.log('app.js loaded, starting decryption script...');

// Use DOMContentLoaded to ensure DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startDecryption);
} else {
    // DOM already ready
    startDecryption();
}

async function startDecryption() {
    console.log('Async decryption function started');
    console.log('DOM ready state:', document.readyState);
    
    // Wait for CryptoService to be available (with timeout)
    console.log('Waiting for CryptoService...');
    let retries = 0;
    while (typeof CryptoService === 'undefined' && retries < 50) {
        await new Promise(resolve => setTimeout(resolve, 100));
        retries++;
    }
    
    if (typeof CryptoService === 'undefined') {
        console.error('CryptoService not loaded after waiting');
        const loadingDiv = document.getElementById("notes-loading");
        if (loadingDiv) {
            loadingDiv.textContent = "Error: CryptoService failed to load. Please refresh.";
            loadingDiv.classList.add("error");
        }
        return;
    }
    console.log('CryptoService available');
    
    const encryptedNotesEl = document.getElementById("encrypted-notes");
    const hasMnemonic = document.body.getAttribute("data-has-mnemonic") === "yes";
    
    console.log('Decryption check:', { hasMnemonic, hasEncryptedNotesEl: !!encryptedNotesEl });
    
    if (hasMnemonic && encryptedNotesEl) {
        try {
            // Get mnemonic from secure API endpoint
            console.log('Fetching mnemonic from API...');
            const response = await fetch("/api/mnemonic");
            if (!response.ok) {
                throw new Error(`Failed to get mnemonic: ${response.status}`);
            }
            const { mnemonic } = await response.json();
            console.log('Mnemonic fetched successfully');
            
            // Parse encrypted notes
            const notesJson = encryptedNotesEl.textContent || "[]";
            console.log('Encrypted notes JSON length:', notesJson.length);
            const encryptedNotes = JSON.parse(notesJson);
            console.log('Number of encrypted notes:', encryptedNotes.length);
            
            const notesContainer = document.getElementById("notes-container");
            const loadingDiv = document.getElementById("notes-loading");
            
            if (loadingDiv) {
                loadingDiv.textContent = "Decrypting notes...";
            }
            
            if (encryptedNotes.length === 0) {
                console.log('No encrypted notes to decrypt');
                if (loadingDiv) {
                    loadingDiv.remove();
                }
                if (notesContainer) {
                    notesContainer.innerHTML = '<p class="empty">No notes found.</p>';
                }
                return;
            }
            
            // Decrypt all notes
            const decryptedNotes = [];
            for (let i = 0; i < encryptedNotes.length; i++) {
                const encryptedNote = encryptedNotes[i];
                try {
                    console.log(`Decrypting note ${i + 1}/${encryptedNotes.length}: ${encryptedNote.id}`);
                    const decrypted = await CryptoService.decryptNote(
                        encryptedNote.ciphertext,
                        encryptedNote.iv,
                        mnemonic
                    );
                    decryptedNotes.push({
                        id: encryptedNote.id,
                        title: decrypted.title || "Untitled",
                        body: decrypted.body || "",
                        body_html: markdownToHtml(decrypted.body || ""),
                        priority: encryptedNote.priority,
                        nsfw: encryptedNote.nsfw,
                        created_at: encryptedNote.created_at,
                        updated_at: encryptedNote.updated_at,
                    });
                    console.log(`Successfully decrypted note ${encryptedNote.id}`);
                } catch (error) {
                    console.error(`Failed to decrypt note ${encryptedNote.id}:`, error);
                }
            }
            
            console.log(`Decrypted ${decryptedNotes.length} notes out of ${encryptedNotes.length}`);
            
            // Render decrypted notes
            if (loadingDiv) {
                loadingDiv.remove();
            }
            renderNotes(decryptedNotes, notesContainer);
            console.log('Notes rendered');
            
            // Store mnemonic for settings panel display
            window._storedMnemonic = mnemonic;
            
        } catch (error) {
            console.error("Failed to decrypt notes:", error);
            const loadingDiv = document.getElementById("notes-loading");
            if (loadingDiv) {
                loadingDiv.textContent = "Error decrypting notes: " + error.message;
                loadingDiv.classList.add("error");
            }
        }
    } else {
        console.log('Skipping decryption:', { hasMnemonic, hasEncryptedNotesEl: !!encryptedNotesEl });
        // If we have mnemonic but no encrypted notes element, show error
        if (hasMnemonic && !encryptedNotesEl) {
            const loadingDiv = document.getElementById("notes-loading");
            if (loadingDiv) {
                loadingDiv.textContent = "Error: Encrypted notes data not found.";
                loadingDiv.classList.add("error");
            }
        }
    }
}

function markdownToHtml(markdown) {
    // Simple markdown rendering - matches server-side render_markdown
    let html = markdown
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
    return html;
}

function renderNotes(notes, container) {
        if (!container) return;
        
        if (notes.length === 0) {
            container.innerHTML = '<p class="empty">No notes found.</p>';
            return;
        }
        
        // Sort notes by priority, then by updated_at (matching Python note_sort_key)
        notes.sort((a, b) => {
            const aPriority = a.priority;
            const bPriority = b.priority;
            
            // Notes with priority come first
            if (aPriority !== null && bPriority !== null) {
                if (aPriority !== bPriority) {
                    return aPriority - bPriority;
                }
            } else if (aPriority !== null) {
                return -1;
            } else if (bPriority !== null) {
                return 1;
            }
            
            // Then sort by timestamp (newer first)
            const aTime = a.updated_at || a.created_at;
            const bTime = b.updated_at || b.created_at;
            if (!aTime && !bTime) return 0;
            if (!aTime) return 1;
            if (!bTime) return -1;
            // Handle Firestore timestamp objects
            let aTimestamp, bTimestamp;
            if (aTime._seconds !== undefined) {
                aTimestamp = aTime._seconds * 1000;
            } else if (aTime instanceof Date) {
                aTimestamp = aTime.getTime();
            } else {
                aTimestamp = new Date(aTime).getTime();
            }
            if (bTime._seconds !== undefined) {
                bTimestamp = bTime._seconds * 1000;
            } else if (bTime instanceof Date) {
                bTimestamp = bTime.getTime();
            } else {
                bTimestamp = new Date(bTime).getTime();
            }
            return bTimestamp - aTimestamp;
        });
        
        let html = `<h2>Your Notes (${notes.length})</h2>`;
        html += '<div class="search-container"><input type="text" id="search-input" class="search-input" placeholder="Search notes..."></div>';
        
        notes.forEach(note => {
            html += `
                <div class="note${note.nsfw ? ' note--nsfw' : ''}" data-note-id="${escapeHtml(note.id)}">
                    <button type="button" class="priority-badge${note.priority === null ? ' priority-badge--empty' : ''}" 
                            data-note-id="${escapeHtml(note.id)}" data-priority="${note.priority || ''}">
                        ${note.priority !== null ? escapeHtml(String(note.priority)) : 'Set priority'}
                    </button>
                    <h3>${escapeHtml(note.title)}</h3>
                    <div class="note-body">${note.body_html}</div>
                    <div class="note-actions">
                        <form method="post" action="./edit">
                            <input type="hidden" name="note_id" value="${escapeHtml(note.id)}">
                            <button type="submit" class="edit-btn">Edit</button>
                        </form>
                        <button type="button" class="view-full-btn" data-note-id="${escapeHtml(note.id)}">Preview</button>
                    </div>
                </div>
            `;
        });
        
    container.innerHTML = html;
    
    // Re-initialize event listeners for dynamically added elements
    initializeNoteListeners();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function initializeNoteListeners() {
        // Re-initialize priority badges - use direct event handlers
        const priorityForm = document.getElementById("priority-form");
        const priorityNoteId = document.getElementById("priority-note-id");
        const priorityValue = document.getElementById("priority-value");
        const priorityModal = document.getElementById("priority-modal");
        const priorityInput = document.getElementById("priority-input");
        const prioritySave = document.getElementById("priority-save");
        const priorityClear = document.getElementById("priority-clear");
        const priorityError = document.getElementById("priority-error");
        
        if (priorityForm && priorityNoteId && priorityValue && priorityModal && priorityInput && prioritySave && priorityClear) {
            // Remove old listeners and add new ones
            document.querySelectorAll(".priority-badge").forEach((badge) => {
                badge.replaceWith(badge.cloneNode(true));
            });
            
            document.querySelectorAll(".priority-badge").forEach((badge) => {
                badge.addEventListener("click", () => {
                    const currentValue = badge.getAttribute("data-priority") || "";
                    const noteId = badge.getAttribute("data-note-id") || "";
                    // Use the global openPriorityModal if available, otherwise define inline
                    if (typeof window.openPriorityModal === 'function') {
                        window.openPriorityModal(noteId, currentValue);
                    } else {
                        // Fallback: open modal directly
                        priorityNoteId.value = noteId;
                        priorityInput.value = currentValue || "";
                        if (priorityError) {
                            priorityError.textContent = "";
                        }
                        priorityModal.classList.add("open");
                        priorityModal.setAttribute("aria-hidden", "false");
                        priorityInput.focus();
                    }
                });
            });
        }
        
        // Re-initialize preview buttons
        document.querySelectorAll(".view-full-btn").forEach((button) => {
            button.replaceWith(button.cloneNode(true));
        });
        
        document.querySelectorAll(".view-full-btn").forEach((button) => {
            button.addEventListener("click", () => {
                const noteId = button.getAttribute("data-note-id");
                if (!noteId) {
                    return;
                }
                const noteElement = document.querySelector(`.note[data-note-id="${noteId}"]`);
                if (!noteElement) {
                    return;
                }
                const noteTitle = noteElement.querySelector("h3")?.textContent || "Untitled";
                const noteBodyHTML = noteElement.querySelector(".note-body")?.innerHTML || "";
                // Use global openPreviewModal if available
                if (typeof window.openPreviewModal === 'function') {
                    window.openPreviewModal(noteTitle, noteBodyHTML);
                } else {
                    // Fallback: open preview directly
                    const previewModal = document.getElementById("preview-modal");
                    const previewBody = document.getElementById("preview-body");
                    const previewTitle = document.getElementById("preview-modal-title");
                    if (previewModal && previewBody && previewTitle) {
                        previewTitle.textContent = noteTitle || "Full note preview";
                        previewBody.innerHTML = noteBodyHTML || "<p><em>No content available.</em></p>";
                        previewModal.classList.add("open");
                        previewModal.setAttribute("aria-hidden", "false");
                    }
                }
            });
        });
        
        // Re-initialize search
        const searchInput = document.getElementById("search-input");
        if (searchInput) {
            searchInput.replaceWith(searchInput.cloneNode(true));
            const newSearchInput = document.getElementById("search-input");
            newSearchInput.addEventListener("input", () => {
                const searchTerm = newSearchInput.value.trim();
                const notes = document.querySelectorAll(".note");
                
                if (searchTerm === "") {
                    notes.forEach((note) => {
                        note.style.display = "";
                    });
                    return;
                }
                
                const escapedPattern = searchTerm
                    .replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
                    .replace(/\*/g, '.*');
                const regex = new RegExp(escapedPattern, 'i');
                
                notes.forEach((note) => {
                    const titleElement = note.querySelector("h3");
                    const bodyElement = note.querySelector(".note-body");
                    
                    const titleText = titleElement ? titleElement.textContent : "";
                    const bodyText = bodyElement ? bodyElement.textContent : "";
                    
                    const matches = regex.test(titleText) || regex.test(bodyText);
                    
                    note.style.display = matches ? "" : "none";
                });
            });
        }
}

const toggle = document.getElementById("settings-toggle");
const panel = document.getElementById("settings-panel");
const overlay = document.getElementById("drawer-overlay");
const hasMnemonic = document.body.getAttribute("data-has-mnemonic") === "yes";
const mnemonicInput = document.getElementById("mnemonic-display");
const mnemonicToggle = document.getElementById("mnemonic-toggle");

const setOpen = (open) => {
    panel.classList.toggle("open", open);
    overlay.classList.toggle("open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    panel.setAttribute("aria-hidden", open ? "false" : "true");
    overlay.setAttribute("aria-hidden", open ? "false" : "true");
};

toggle.addEventListener("click", () => setOpen(!panel.classList.contains("open")));
overlay.addEventListener("click", () => setOpen(false));

// Landing page "Already have an account?" button
const openSettingsButton = document.getElementById("open-settings");
if (openSettingsButton) {
    openSettingsButton.addEventListener("click", () => setOpen(true));
}

if (mnemonicInput && mnemonicToggle) {
    mnemonicToggle.addEventListener("click", async () => {
        const isHidden = mnemonicInput.type === "password";
        if (isHidden) {
            // Fetch mnemonic from API when user wants to see it
            try {
                const response = await fetch("/api/mnemonic");
                if (response.ok) {
                    const { mnemonic } = await response.json();
                    mnemonicInput.value = mnemonic;
                    mnemonicInput.type = "text";
                    mnemonicToggle.textContent = "Hide mnemonic";
                } else {
                    mnemonicInput.value = "[Error loading mnemonic]";
                    mnemonicInput.type = "text";
                }
            } catch (error) {
                mnemonicInput.value = "[Error loading mnemonic]";
                mnemonicInput.type = "text";
            }
        } else {
            mnemonicInput.value = "[Hidden for security]";
            mnemonicInput.type = "password";
            mnemonicToggle.textContent = "See mnemonic";
        }
    });
}

const priorityForm = document.getElementById("priority-form");
const priorityNoteId = document.getElementById("priority-note-id");
const priorityValue = document.getElementById("priority-value");
const priorityModal = document.getElementById("priority-modal");
const priorityInput = document.getElementById("priority-input");
const prioritySave = document.getElementById("priority-save");
const priorityClear = document.getElementById("priority-clear");
const priorityError = document.getElementById("priority-error");

const closePriorityModal = () => {
    if (!priorityModal) {
        return;
    }
    priorityModal.classList.remove("open");
    priorityModal.setAttribute("aria-hidden", "true");
    if (priorityError) {
        priorityError.textContent = "";
    }
};

const openPriorityModal = (noteId, currentPriority) => {
    if (!priorityModal || !priorityInput) {
        return;
    }
    priorityNoteId.value = noteId;
    priorityInput.value = currentPriority || "";
    if (priorityError) {
        priorityError.textContent = "";
    }
    priorityModal.classList.add("open");
    priorityModal.setAttribute("aria-hidden", "false");
    priorityInput.focus();
};
// Make it globally accessible
window.openPriorityModal = openPriorityModal;

if (
    priorityForm &&
    priorityNoteId &&
    priorityValue &&
    priorityModal &&
    priorityInput &&
    prioritySave &&
    priorityClear
) {
    document.querySelectorAll(".priority-badge").forEach((badge) => {
        badge.addEventListener("click", () => {
            const currentValue = badge.getAttribute("data-priority") || "";
            const noteId = badge.getAttribute("data-note-id") || "";
            openPriorityModal(noteId, currentValue);
        });
    });

    priorityModal.querySelectorAll("[data-modal-close]").forEach((button) => {
        button.addEventListener("click", closePriorityModal);
    });

    prioritySave.addEventListener("click", () => {
        const trimmed = priorityInput.value.trim();
        if (trimmed && !/^-?\d+$/.test(trimmed)) {
            if (priorityError) {
                priorityError.textContent = "Priority must be a whole number.";
            }
            return;
        }
        priorityValue.value = trimmed;
        priorityForm.submit();
    });

    priorityClear.addEventListener("click", () => {
        priorityValue.value = "";
        priorityForm.submit();
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && priorityModal.classList.contains("open")) {
            closePriorityModal();
        }
    });
}

const newNoteBtn = document.getElementById("new-note-btn");
const newNoteModal = document.getElementById("new-note-modal");
if (newNoteBtn && newNoteModal) {
    newNoteBtn.addEventListener("click", () => {
        newNoteModal.classList.add("open");
        newNoteModal.setAttribute("aria-hidden", "false");
        document.getElementById("new-note-title")?.focus();
    });
    const closeNewNoteModal = () => {
        newNoteModal.classList.remove("open");
        newNoteModal.setAttribute("aria-hidden", "true");
    };
    newNoteModal.querySelectorAll("[data-new-close]").forEach((el) => {
        el.addEventListener("click", closeNewNoteModal);
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && newNoteModal.classList.contains("open")) {
            closeNewNoteModal();
        }
    });
}

const searchInput = document.getElementById("search-input");
if (searchInput) {
    searchInput.addEventListener("input", () => {
        const searchTerm = searchInput.value.trim();
        const notes = document.querySelectorAll(".note");
        
        if (searchTerm === "") {
            notes.forEach((note) => {
                note.style.display = "";
            });
            return;
        }
        
        // Convert wildcard pattern to regex: * becomes .*
        // Escape other regex special characters
        const escapedPattern = searchTerm
            .replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
            .replace(/\*/g, '.*');
        const regex = new RegExp(escapedPattern, 'i');
        
        notes.forEach((note) => {
            const titleElement = note.querySelector("h3");
            const bodyElement = note.querySelector(".note-body");
            
            const titleText = titleElement ? titleElement.textContent : "";
            const bodyText = bodyElement ? bodyElement.textContent : "";
            
            const matches = regex.test(titleText) || regex.test(bodyText);
            
            note.style.display = matches ? "" : "none";
        });
    });
}

const previewModal = document.getElementById("preview-modal");
const previewBody = document.getElementById("preview-body");
const previewTitle = document.getElementById("preview-modal-title");

const closePreviewModal = () => {
    if (!previewModal) {
        return;
    }
    previewModal.classList.remove("open");
    previewModal.setAttribute("aria-hidden", "true");
    if (previewBody) {
        previewBody.innerHTML = "";
    }
};

const openPreviewModal = (title, content) => {
    if (!previewModal || !previewBody || !previewTitle) {
        return;
    }
    previewTitle.textContent = title || "Full note preview";
    previewBody.innerHTML = content || "<p><em>No content available.</em></p>";
    previewModal.classList.add("open");
    previewModal.setAttribute("aria-hidden", "false");
};
// Make it globally accessible
window.openPreviewModal = openPreviewModal;

document.querySelectorAll(".view-full-btn").forEach((button) => {
    button.addEventListener("click", () => {
        const noteId = button.getAttribute("data-note-id");
        if (!noteId) {
            return;
        }
        const noteElement = document.querySelector(`.note[data-note-id="${noteId}"]`);
        if (!noteElement) {
            return;
        }
        const noteTitle = noteElement.querySelector("h3")?.textContent || "Untitled";
        const noteBodyHTML = noteElement.querySelector(".note-body")?.innerHTML || "";
        openPreviewModal(noteTitle, noteBodyHTML);
    });
});

if (previewModal) {
    previewModal.querySelectorAll("[data-preview-close]").forEach((button) => {
        button.addEventListener("click", closePreviewModal);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && previewModal.classList.contains("open")) {
            closePreviewModal();
        }
    });
}
