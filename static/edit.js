const deleteForm = document.getElementById("delete-form");
const deleteTrigger = document.getElementById("delete-trigger");
const deleteModal = document.getElementById("delete-modal");

const closeDeleteModal = () => {
    if (!deleteModal) {
        return;
    }
    deleteModal.classList.remove("open");
    deleteModal.setAttribute("aria-hidden", "true");
};

if (deleteForm && deleteTrigger && deleteModal) {
    deleteTrigger.addEventListener("click", () => {
        deleteModal.classList.add("open");
        deleteModal.setAttribute("aria-hidden", "false");
    });

    deleteModal.querySelectorAll("[data-modal-close]").forEach((button) => {
        button.addEventListener("click", closeDeleteModal);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && deleteModal.classList.contains("open")) {
            closeDeleteModal();
        }
    });
}
