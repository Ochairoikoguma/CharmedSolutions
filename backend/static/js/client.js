/* =========================================
   CLIENT DATA

   Temporary frontend data until
   Django supplies real database clients.
   ========================================= */

const clients = {

    1: {
        id: 1,
        name: "Alpha Funding",
        commissionRate: 20,
        dateAdded: "10/01/2026"
    },

    2: {
        id: 2,
        name: "Capital Advance",
        commissionRate: 25,
        dateAdded: "10/05/2026"
    },

    3: {
        id: 3,
        name: "Merchant Funding",
        commissionRate: 18,
        dateAdded: "10/12/2026"
    },

    4: {
        id: 4,
        name: "Premier Capital",
        commissionRate: 20,
        dateAdded: "10/18/2026"
    }

};


/* =========================================
   ELEMENTS
   ========================================= */

const clientMessage =
    document.getElementById(
        "clientMessage"
    );

const clientButtons =
    document.querySelectorAll(
        ".client-name"
    );

const clientForm =
    document.getElementById(
        "clientForm"
    );

const clientId =
    document.getElementById(
        "clientId"
    );

const clientName =
    document.getElementById(
        "clientName"
    );

const commissionRate =
    document.getElementById(
        "commissionRate"
    );

const dateAdded =
    document.getElementById(
        "dateAdded"
    );

const createClientBtn =
    document.getElementById(
        "createClientBtn"
    );

const deleteClientBtn =
    document.getElementById(
        "deleteClientBtn"
    );


let selectedClientId = 1;


/* =========================================
   MESSAGES
   ========================================= */

function showClientMessage(
    message,
    type
) {

    clientMessage.textContent =
        message;

    clientMessage.className =
        "message message-" +
        type;

}


/* =========================================
   LOAD CLIENT
   ========================================= */

function loadClient(id) {

    const client =
        clients[id];


    if (!client) {
        return;
    }


    selectedClientId =
        Number(id);


    clientId.value =
        client.id;

    clientName.value =
        client.name;

    commissionRate.value =
        client.commissionRate;

    dateAdded.value =
        client.dateAdded;


    clientButtons.forEach(
        function (button) {

            button.classList.remove(
                "active"
            );


            if (
                Number(
                    button.dataset.client
                ) ===
                selectedClientId
            ) {

                button.classList.add(
                    "active"
                );

            }

        }
    );

}


/* =========================================
   SELECT CLIENT
   ========================================= */

clientButtons.forEach(
    function (button) {

        button.addEventListener(
            "click",
            function () {

                loadClient(
                    Number(
                        button.dataset.client
                    )
                );

            }
        );

    }
);


/* =========================================
   SAVE CLIENT DETAILS
   ========================================= */

clientForm.addEventListener(
    "submit",
    function (event) {

        event.preventDefault();


        const name =
            clientName.value.trim();


        const commission =
            commissionRate.value.trim();


        if (name === "") {

            showClientMessage(
                "Client name is required.",
                "error"
            );

            return;

        }


        if (
            commission !== "" &&
            (
                Number(commission) < 0 ||
                Number(commission) > 100
            )
        ) {

            showClientMessage(
                "Commission rate must be between 0 and 100.",
                "error"
            );

            return;

        }


        if (
            selectedClientId !== null &&
            clients[selectedClientId]
        ) {

            clients[selectedClientId].name =
                name;

            clients[selectedClientId].commissionRate =
                commission;


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
            "Client details saved.",
            "success"
        );

    }
);


/* =========================================
   CREATE NEW CLIENT
   ========================================= */

createClientBtn.addEventListener(
    "click",
    function () {

        selectedClientId =
            null;


        clientButtons.forEach(
            function (button) {

                button.classList.remove(
                    "active"
                );

            }
        );


        clientId.value =
            "Auto-generated";

        clientName.value =
            "";

        commissionRate.value =
            "";

        dateAdded.value =
            "Auto-generated";


        clientName.focus();


        showClientMessage(
            "Enter the new client details.",
            "loading"
        );

    }
);


/* =========================================
   DELETE CLIENT
   ========================================= */

deleteClientBtn.addEventListener(
    "click",
    function () {

        if (
            selectedClientId === null
        ) {

            showClientMessage(
                "Select a client before deleting.",
                "error"
            );

            return;

        }


        const client =
            clients[selectedClientId];


        const confirmed =
            window.confirm(
                "Confirm Client Delete\n\nDelete " +
                client.name +
                " and their associated accounts?"
            );


        if (!confirmed) {
            return;
        }


        /*
         * Backend delete endpoint still
         * needs to be connected.
         */

        showClientMessage(
            client.name +
            " selected for deletion.",
            "success"
        );

    }
);


/* =========================================
   INITIAL LOAD
   ========================================= */

loadClient(1);