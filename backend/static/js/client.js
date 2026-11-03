const clientMessage = document.getElementById("clientMessage");

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


function showClientMessage(message, type) {

    clientMessage.textContent = message;

    clientMessage.className =
        "message message-" + type;


    setTimeout(function () {

        clientMessage.classList.add("hidden");

    }, 3000);

}


/* SELECT CLIENT */

clientButtons.forEach(function (button) {

    button.addEventListener("click", function () {

        clientButtons.forEach(function (item) {

            item.classList.remove("active");

        });


        button.classList.add("active");


        const selectedClient =
            button.textContent.trim();


        clientName.value =
            selectedClient;


        showClientMessage(
            selectedClient + " selected.",
            "success"
        );

    });

});


/* SAVE CLIENT */

clientForm.addEventListener("submit", function (event) {

    event.preventDefault();


    const name =
        clientName.value.trim();

    const commission =
        Number(commissionRate.value);

    const limit =
        Number(costLimit.value);


    if (name === "") {

        showClientMessage(
            "Client name is required.",
            "error"
        );

        return;

    }


    if (
        commission < 0 ||
        commission > 100
    ) {

        showClientMessage(
            "Commission percentage must be between 0 and 100.",
            "error"
        );

        return;

    }


    if (
        limit < 0 ||
        limit > 100
    ) {

        showClientMessage(
            "Cost limit must be between 0 and 100.",
            "error"
        );

        return;

    }


    showClientMessage(
        "Client information saved successfully.",
        "success"
    );

});


/* CREATE NEW CLIENT */

createClientBtn.addEventListener("click", function () {

    clientName.value = "";
    commissionRate.value = "";
    costLimit.value = "";


    clientButtons.forEach(function (item) {

        item.classList.remove("active");

    });


    showClientMessage(
        "Enter information for the new client.",
        "loading"
    );

});


/* DELETE CLIENT */

deleteClientBtn.addEventListener("click", function () {

    showClientMessage(
        "Client delete selected.",
        "loading"
    );

});


/* GENERATE CLIENT REPORT */

clientReportBtn.addEventListener("click", function () {

    showClientMessage(
        "Remittance report generated successfully.",
        "success"
    );

});