document.addEventListener("DOMContentLoaded", () => {
    const messageBox = document.getElementById("messageBox");
    const rolloverSelectedBtn = document.getElementById("rolloverSelectedBtn");
    const rolloverAllBtn = document.getElementById("rolloverAllBtn");
    const generateReportsBtn = document.getElementById("generateReportsBtn");

    let messageTimer = null;
    let reportTimer = null;


    if (messageBox) {
        messageBox.setAttribute("role", "status");
        messageBox.setAttribute("aria-live", "polite");
    }

    function showMessage(message, type = "success") {
        if (!messageBox) return;

       
        clearTimeout(messageTimer);

        messageBox.textContent = message;
        messageBox.className = `message message-${type}`;

        // Loading messages stay visible until replaced
        if (type !== "loading") {
            messageTimer = setTimeout(() => {
                messageBox.classList.add("hidden");
            }, 3000);
        }
    }

    function getClientCheckboxes() {
        return document.querySelectorAll(".client-checkbox");
    }

    function getSelectedClients() {
        return Array.from(
            document.querySelectorAll(".client-checkbox:checked")
        ).map(checkbox => checkbox.value);
    }

    if (rolloverSelectedBtn) {
        rolloverSelectedBtn.addEventListener("click", () => {
            const selected = getSelectedClients();

            if (selected.length === 0) {
                showMessage("Please select at least one client.", "error");
                return;
            }

            showMessage(
                `${selected.length} client(s) selected for rollover.`,
                "success"
            );
        });
    }

    if (rolloverAllBtn) {
        rolloverAllBtn.addEventListener("click", () => {
            const checkboxes = getClientCheckboxes();

            if (checkboxes.length === 0) {
                showMessage("There are no flagged clients to roll over.", "error");
                return;
            }

            checkboxes.forEach(checkbox => {
                checkbox.checked = true;
            });

            showMessage(
                `All ${checkboxes.length} flagged client(s) selected for rollover.`,
                "success"
            );
        });
    }

    if (generateReportsBtn) {
        generateReportsBtn.addEventListener("click", () => {
            // Prevent double-clicks from starting overlapping runs
            if (generateReportsBtn.disabled) return;

            generateReportsBtn.disabled = true;
            showMessage("Generating reports...", "loading");

            clearTimeout(reportTimer);
            reportTimer = setTimeout(() => {
                showMessage("Reports generated successfully.", "success");
                generateReportsBtn.disabled = false;
            }, 1000);
        });
    }
});
