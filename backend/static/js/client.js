/* =====================================
   CLIENT PAGE ELEMENTS
   ===================================== */

const clientMessage =
    document.getElementById("clientMessage");

const clientButtons =
    document.querySelectorAll(".client-name");

const clientForm =
    document.getElementById("clientForm");

const clientName =
    document.getElementById("clientName");

const commissionRate =
    document.getElementById("commissionRate");

const costLimit =
    document.getElementById("costLimit");

const deleteClientBtn =
    document.getElementById("deleteClientBtn");

const createClientBtn =
    document.getElementById("createClientBtn");

const clientReportBtn =
    document.getElementById("clientReportBtn");


/* =====================================
   FAKE CLIENT DATA
   ===================================== */

const clients = {

    1: {
        name: "Client 1",
        commissionRate: 20,
        costLimit: 20
    },

    2: {
        name: "Client 2",
        commissionRate: 25,
        costLimit: 15
    },

    3: {
        name: "Client 3",
        commissionRate: 20,
        costLimit: 20
    },

    4: {
        name: "Client 4",
        commissionRate: 18,
        costLimit: 15
    }

};


/* =====================================
   CURRENT CLIENT
   ===================================== */

let selectedClientId = 1;


/* =====================================
   FEEDBACK MESSAGE
   ===================================== */

function showClientMessage(message, type) {

    if (!clientMessage) {
        return;
    }

    clientMessage.textContent = message;

    clientMessage.className =
        "message message-" + type;


    setTimeout(function () {

        clientMessage.classList.add("hidden");

    }, 3000);

}


/* =====================================
   LOAD CLIENT
   ===================================== */

function loadClient(clientId) {

    const client = clients[clientId];


    if (!client) {

        showClientMessage(
            "Client could not be found.",
            "error"
        );

        return;
    }


    selectedClientId =
        Number(clientId);


    clientName.value =
        client.name;

    commissionRate.value =
        client.commissionRate;

    costLimit.value =
        client.costLimit;


    clientButtons.forEach(
        function (button) {

            button.classList.remove("active");


            if (
                Number(button.dataset.client) ===
                selectedClientId
            ) {

                button.classList.add("active");

            }

        }
    );

}


/* =====================================
   SELECT CLIENT
   ===================================== */

clientButtons.forEach(
    function (button) {

        button.addEventListener(
            "click",
            function () {

                const clientId =
                    Number(
                        button.dataset.client
                    );


                loadClient(clientId);


                showClientMessage(
                    clients[clientId].name +
                    " selected.",
                    "success"
                );

            }
        );

    }
);


/* =====================================
   SAVE CLIENT
   ===================================== */

if (clientForm) {

    clientForm.addEventListener(
        "submit",
        function (event) {

            event.preventDefault();


            const name =
                clientName.value.trim();

            const commission =
                Number(
                    commissionRate.value
                );

            const limit =
                Number(
                    costLimit.value
                );


            /* NAME VALIDATION */

            if (name === "") {

                showClientMessage(
                    "Client name is required.",
                    "error"
                );

                return;

            }


            /* COMMISSION VALIDATION */

            if (
                commissionRate.value === "" ||
                commission < 0 ||
                commission > 100
            ) {

                showClientMessage(
                    "Commission percentage must be between 0 and 100.",
                    "error"
                );

                return;

            }


            /* COST LIMIT VALIDATION */

            if (
                costLimit.value === "" ||
                limit < 0 ||
                limit > 100
            ) {

                showClientMessage(
                    "Cost limit must be between 0 and 100.",
                    "error"
                );

                return;

            }


            /* UPDATE FAKE DATA */

            if (
                selectedClientId !== null &&
                clients[selectedClientId]
            ) {

                clients[selectedClientId].name =
                    name;

                clients[selectedClientId].commissionRate =
                    commission;

                clients[selectedClientId].costLimit =
                    limit;


                const activeButton =
                    document.querySelector(
                        '.client-name[data-client="' +
                        selectedClientId +
                        '"]'
                    );


                if (activeButton) {

                    activeButton.textContent =
                        name;

                }

            }


            showClientMessage(
                "Client information saved successfully.",
                "success"
            );

        }
    );

}


/* =====================================
   CREATE NEW CLIENT
   ===================================== */

if (createClientBtn) {

    createClientBtn.addEventListener(
        "click",
        function () {

            selectedClientId = null;


            clientButtons.forEach(
                function (button) {

                    button.classList.remove(
                        "active"
                    );

                }
            );


            clientName.value = "";

            commissionRate.value = "";

            costLimit.value = "";


            clientName.focus();


            showClientMessage(
                "Enter the new client information.",
                "loading"
            );

        }
    );

}


/* =====================================
   DELETE CLIENT
   ===================================== */

if (deleteClientBtn) {

    deleteClientBtn.addEventListener(
        "click",
        function () {

            if (selectedClientId === null) {

                showClientMessage(
                    "Please select a client to delete.",
                    "error"
                );

                return;

            }


            const client =
                clients[selectedClientId];


            if (!client) {

                showClientMessage(
                    "Client could not be found.",
                    "error"
                );

                return;

            }


            const confirmed =
                window.confirm(
                    "Are you sure you want to delete " +
                    client.name +
                    "?"
                );


            if (!confirmed) {
                return;
            }


            delete clients[selectedClientId];


            const button =
                document.querySelector(
                    '.client-name[data-client="' +
                    selectedClientId +
                    '"]'
                );


            if (button) {

                button.style.display =
                    "none";

            }


            clientName.value = "";

            commissionRate.value = "";

            costLimit.value = "";


            selectedClientId = null;


            showClientMessage(
                "Client deleted successfully.",
                "success"
            );

        }
    );

}


/* =====================================
   DOWNLOAD SAMPLE REPORT
   ===================================== */

if (clientReportBtn) {

    clientReportBtn.addEventListener(
        "click",
        function () {

            /*
             * For now, Luis provided the
             * sample report download URL.
             *
             * Later this can be changed
             * to generate a report for the
             * currently selected client.
             */

            window.location.href =
                "/reports/sample/download/";

        }
    );

}


/* =====================================
   INITIAL PAGE LOAD
   ===================================== */

loadClient(1);