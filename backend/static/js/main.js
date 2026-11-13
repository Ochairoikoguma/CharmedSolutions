/* =========================================
   PAGE ELEMENTS
   ========================================= */

const reportingPeriodText =
    document.getElementById("reportingPeriodText");

const messageBox =
    document.getElementById("messageBox");

const importClientDataBtn =
    document.getElementById("importClientDataBtn");

const csvFileInput =
    document.getElementById("csvFileInput");

const rolloverSelectedBtn =
    document.getElementById("rolloverSelectedBtn");

const rolloverAllBtn =
    document.getElementById("rolloverAllBtn");

const generateAllReportsBtn =
    document.getElementById("generateAllReportsBtn");

const clientTableBody =
    document.getElementById("clientTableBody");

const previousPageBtn =
    document.getElementById("previousPageBtn");

const nextPageBtn =
    document.getElementById("nextPageBtn");

const pageIndicator =
    document.getElementById("pageIndicator");


/* =========================================
   REPORTING PERIOD
   ========================================= */

const today = new Date();

const reportingYear =
    today.getFullYear();

const reportingMonth =
    today.getMonth() + 1;

const reportingMonthName =
    today.toLocaleString(
        "en-US",
        {
            month: "long"
        }
    );


if (reportingPeriodText) {

    reportingPeriodText.textContent =
        "Showing clients for " +
        reportingMonthName +
        " " +
        reportingYear;

}


/* =========================================
   FEEDBACK
   ========================================= */

function showMessage(
    message,
    type
) {

    if (!messageBox) {
        return;
    }

    messageBox.textContent =
        message;

    messageBox.className =
        "message message-" + type;

}


function clearMessage() {

    if (!messageBox) {
        return;
    }

    messageBox.classList.add(
        "hidden"
    );

}


/* =========================================
   CSRF TOKEN
   ========================================= */

function getCookie(name) {

    let cookieValue = null;

    if (
        document.cookie &&
        document.cookie !== ""
    ) {

        const cookies =
            document.cookie.split(";");


        for (
            let i = 0;
            i < cookies.length;
            i++
        ) {

            const cookie =
                cookies[i].trim();


            if (
                cookie.substring(
                    0,
                    name.length + 1
                ) ===
                name + "="
            ) {

                cookieValue =
                    decodeURIComponent(
                        cookie.substring(
                            name.length + 1
                        )
                    );

                break;

            }

        }

    }


    return cookieValue;

}


/* =========================================
   GET TABLE ROWS
   ========================================= */

function getClientRows() {

    return Array.from(
        clientTableBody.querySelectorAll(
            "tr"
        )
    );

}


/* =========================================
   SORT BY LARGEST RECOVERY
   ========================================= */

function sortClientsByRecovery() {

    const rows =
        getClientRows();


    rows.sort(
        function (a, b) {

            return (
                Number(
                    b.dataset.recoveries
                ) -
                Number(
                    a.dataset.recoveries
                )
            );

        }
    );


    rows.forEach(
        function (row) {

            clientTableBody.appendChild(
                row
            );

        }
    );

}


/* =========================================
   COST FLAGS

   Costs turn red whenever:
   costs > 20% of recoveries
   ========================================= */

function updateCostFlags() {

    const costCells =
        document.querySelectorAll(
            ".cost-value"
        );


    costCells.forEach(
        function (cell) {

            const cost =
                Number(
                    cell.dataset.cost
                );

            const recovery =
                Number(
                    cell.dataset.recovery
                );


            const ceiling =
                recovery * 0.20;


            if (cost > ceiling) {

                cell.classList.add(
                    "cost-flagged"
                );

            } else {

                cell.classList.remove(
                    "cost-flagged"
                );

            }

        }
    );

}


/* =========================================
   IMPORT CLIENT DATA
   ========================================= */

if (importClientDataBtn) {

    importClientDataBtn.addEventListener(
        "click",
        function () {

            csvFileInput.click();

        }
    );

}


if (csvFileInput) {

    csvFileInput.addEventListener(
        "change",
        function () {

            const file =
                csvFileInput.files[0];


            if (!file) {
                return;
            }


            if (
                !file.name
                    .toLowerCase()
                    .endsWith(".csv")
            ) {

                showMessage(
                    "Please select a CSV file.",
                    "error"
                );

                csvFileInput.value =
                    "";

                return;

            }


            /*
             * File picker is complete.
             *
             * The actual CSV upload endpoint
             * needs to be supplied by the backend.
             */

            showMessage(
                file.name +
                " selected for import.",
                "success"
            );

        }
    );

}


/* =========================================
   SELECTED CLIENT ROWS
   ========================================= */

function getSelectedRows() {

    return getClientRows().filter(
        function (row) {

            const checkbox =
                row.querySelector(
                    ".client-checkbox"
                );


            return (
                checkbox &&
                checkbox.checked
            );

        }
    );

}


/* =========================================
   FLAGGED CLIENT ROWS
   ========================================= */

function getFlaggedRows() {

    return getClientRows().filter(
        function (row) {

            return Boolean(
                row.querySelector(
                    ".cost-flagged"
                )
            );

        }
    );

}


/* =========================================
   ROLLOVER SELECTED

   Backend endpoint still needs to be
   connected once provided.
   ========================================= */

if (rolloverSelectedBtn) {

    rolloverSelectedBtn.addEventListener(
        "click",
        function () {

            const selectedRows =
                getSelectedRows();


            if (
                selectedRows.length === 0
            ) {

                showMessage(
                    "Select at least one client to roll over.",
                    "error"
                );

                return;

            }


            const flaggedSelected =
                selectedRows.filter(
                    function (row) {

                        return Boolean(
                            row.querySelector(
                                ".cost-flagged"
                            )
                        );

                    }
                );


            if (
                flaggedSelected.length === 0
            ) {

                showMessage(
                    "None of the selected clients require rollover.",
                    "error"
                );

                return;

            }


            /*
             * Do not invent the rollover backend
             * URL here.
             *
             * Once the backend route is available,
             * send these selected client IDs there.
             */

            showMessage(
                flaggedSelected.length +
                " flagged client(s) selected for rollover.",
                "success"
            );

        }
    );

}


/* =========================================
   ROLLOVER ALL

   Backend endpoint still needs to be
   connected once provided.
   ========================================= */

if (rolloverAllBtn) {

    rolloverAllBtn.addEventListener(
        "click",
        function () {

            const flaggedRows =
                getFlaggedRows();


            if (
                flaggedRows.length === 0
            ) {

                showMessage(
                    "There are no flagged clients to roll over.",
                    "error"
                );

                return;

            }


            showMessage(
                flaggedRows.length +
                " flagged client(s) selected for rollover.",
                "success"
            );

        }
    );

}


/* =========================================
   PDF DOWNLOAD
   ========================================= */

async function downloadPdf(
    response,
    clientId
) {

    const blob =
        await response.blob();


    const objectUrl =
        window.URL.createObjectURL(
            blob
        );


    const link =
        document.createElement(
            "a"
        );


    let filename =
        "remittance_" +
        clientId +
        "_" +
        reportingYear +
        "_" +
        String(
            reportingMonth
        ).padStart(
            2,
            "0"
        ) +
        ".pdf";


    const disposition =
        response.headers.get(
            "Content-Disposition"
        );


    if (disposition) {

        const match =
            disposition.match(
                /filename="?([^"]+)"?/
            );


        if (
            match &&
            match[1]
        ) {

            filename =
                match[1];

        }

    }


    link.href =
        objectUrl;

    link.download =
        filename;


    document.body.appendChild(
        link
    );


    link.click();


    document.body.removeChild(
        link
    );


    window.URL.revokeObjectURL(
        objectUrl
    );

}


/* =========================================
   GENERATE REPORT
   ========================================= */

async function generateReport(
    clientId
) {

    const formData =
        new FormData();


    formData.append(
        "year",
        reportingYear
    );

    formData.append(
        "month",
        reportingMonth
    );


    const csrfToken =
        getCookie(
            "csrftoken"
        );


    const response =
        await fetch(
            "/reports/clients/" +
            clientId +
            "/download/",
            {
                method: "POST",

                headers: {
                    "X-CSRFToken":
                        csrfToken
                },

                body: formData
            }
        );


    if (!response.ok) {

        const backendMessage =
            await response.text();


        throw new Error(
            backendMessage ||
            "Report generation failed."
        );

    }


    await downloadPdf(
        response,
        clientId
    );

}


/* =========================================
   GENERATE ALL REPORTS

   Generates one PDF for every client
   currently visible in the table page.
   ========================================= */

if (generateAllReportsBtn) {

    generateAllReportsBtn.addEventListener(
        "click",
        async function () {

            clearMessage();


            const visibleRows =
                getClientRows().filter(
                    function (row) {

                        return (
                            row.style.display !==
                            "none"
                        );

                    }
                );


            if (
                visibleRows.length === 0
            ) {

                showMessage(
                    "There are no clients on this page.",
                    "error"
                );

                return;

            }


            /*
             * Report generation must be blocked
             * if commission rate is blank.
             */

            const missingCommission =
                visibleRows.find(
                    function (row) {

                        return (
                            row.dataset
                                .commissionRate ===
                            ""
                        );

                    }
                );


            if (missingCommission) {

                const clientName =
                    missingCommission
                        .children[1]
                        .textContent
                        .trim();


                showMessage(
                    clientName +
                    " does not have a commission rate. Set the commission rate before generating reports.",
                    "error"
                );

                return;

            }


            generateAllReportsBtn.disabled =
                true;

            generateAllReportsBtn.textContent =
                "Generating Reports...";


            try {

                let completed =
                    0;


                for (
                    const row
                    of visibleRows
                ) {

                    const clientId =
                        row.dataset
                            .clientId;


                    await generateReport(
                        clientId
                    );


                    completed++;

                }


                showMessage(
                    completed +
                    " report(s) generated successfully.",
                    "success"
                );

            }

            catch (error) {

                showMessage(
                    error.message,
                    "error"
                );

            }

            finally {

                generateAllReportsBtn.disabled =
                    false;

                generateAllReportsBtn.textContent =
                    "Generate All Reports";

            }

        }
    );

}


/* =========================================
   BASIC PAGINATION
   ========================================= */

const rowsPerPage = 10;

let currentPage = 1;


function renderPage() {

    const rows =
        getClientRows();


    const pageCount =
        Math.max(
            1,
            Math.ceil(
                rows.length /
                rowsPerPage
            )
        );


    if (
        currentPage >
        pageCount
    ) {

        currentPage =
            pageCount;

    }


    const start =
        (
            currentPage -
            1
        ) *
        rowsPerPage;


    const end =
        start +
        rowsPerPage;


    rows.forEach(
        function (
            row,
            index
        ) {

            row.style.display =
                index >= start &&
                index < end
                    ? ""
                    : "none";

        }
    );


    pageIndicator.textContent =
        currentPage +
        " of " +
        pageCount;


    previousPageBtn.disabled =
        currentPage === 1;


    nextPageBtn.disabled =
        currentPage ===
        pageCount;

}


previousPageBtn.addEventListener(
    "click",
    function () {

        if (
            currentPage > 1
        ) {

            currentPage--;

            renderPage();

        }

    }
);


nextPageBtn.addEventListener(
    "click",
    function () {

        const rows =
            getClientRows();


        const pageCount =
            Math.ceil(
                rows.length /
                rowsPerPage
            );


        if (
            currentPage <
            pageCount
        ) {

            currentPage++;

            renderPage();

        }

    }
);


/* =========================================
   INITIAL PAGE SETUP
   ========================================= */

sortClientsByRecovery();

updateCostFlags();

renderPage();