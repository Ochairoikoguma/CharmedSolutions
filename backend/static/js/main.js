/* =====================================
   DASHBOARD ELEMENTS
   ===================================== */

const messageBox =
    document.getElementById("messageBox");

const selectAll =
    document.getElementById("selectAll");

const clientCheckboxes =
    document.querySelectorAll(".client-checkbox");

const importBtn =
    document.getElementById("importBtn");

const rolloverSelectedBtn =
    document.getElementById("rolloverSelectedBtn");

const rolloverAllBtn =
    document.getElementById("rolloverAllBtn");

const generateReportsBtn =
    document.getElementById("generateReportsBtn");


/* =====================================
   FEEDBACK MESSAGE
   ===================================== */

function showMessage(message, type) {

    if (!messageBox) {
        return;
    }

    messageBox.textContent = message;

    messageBox.className =
        "message message-" + type;


    setTimeout(function () {

        messageBox.classList.add("hidden");

    }, 3000);

}


/* =====================================
   SELECT ALL CLIENTS
   ===================================== */

if (selectAll) {

    selectAll.addEventListener(
        "change",
        function () {

            clientCheckboxes.forEach(
                function (checkbox) {

                    checkbox.checked =
                        selectAll.checked;

                }
            );

        }
    );

}


/* =====================================
   IMPORT BUTTON
   ===================================== */

if (importBtn) {

    importBtn.addEventListener(
        "click",
        function () {

            showMessage(
                "Import selected.",
                "loading"
            );

        }
    );

}


/* =====================================
   ROLLOVER SELECTED
   ===================================== */

if (rolloverSelectedBtn) {

    rolloverSelectedBtn.addEventListener(
        "click",
        function () {

            const selectedClients =
                document.querySelectorAll(
                    ".client-checkbox:checked"
                );


            if (selectedClients.length === 0) {

                showMessage(
                    "Please select at least one client.",
                    "error"
                );

                return;
            }


            showMessage(
                selectedClients.length +
                " client(s) selected for rollover.",
                "success"
            );

        }
    );

}


/* =====================================
   ROLLOVER ALL FLAGGED
   ===================================== */

if (rolloverAllBtn) {

    rolloverAllBtn.addEventListener(
        "click",
        function () {

            showMessage(
                "All flagged clients selected for rollover.",
                "success"
            );

        }
    );

}


/* =====================================
   GENERATE / DOWNLOAD REPORT
   ===================================== */

if (generateReportsBtn) {

    generateReportsBtn.addEventListener(
        "click",
        function () {

            /*
             * The backend already provides
             * the sample PDF download route.
             *
             * Clicking Generate Reports
             * sends the browser to that URL.
             */

            window.location.href =
                "/reports/sample/download/";

        }
    );

}