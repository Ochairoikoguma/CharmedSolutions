const messageBox = document.getElementById("messageBox");

const selectAll = document.getElementById("selectAll");

const checkboxes =
    document.querySelectorAll(".client-checkbox");


function showMessage(message, type) {

    messageBox.textContent = message;

    messageBox.className =
        "message message-" + type;


    setTimeout(function () {

        messageBox.classList.add("hidden");

    }, 3000);

}


if (selectAll) {

    selectAll.addEventListener("change", function () {

        checkboxes.forEach(function (checkbox) {

            checkbox.checked =
                selectAll.checked;

        });

    });

}


document
    .getElementById("importBtn")
    .addEventListener("click", function () {

        showMessage(
            "Import selected.",
            "loading"
        );

    });


document
    .getElementById("rolloverSelectedBtn")
    .addEventListener("click", function () {

        const selected =
            document.querySelectorAll(
                ".client-checkbox:checked"
            );


        if (selected.length === 0) {

            showMessage(
                "Select at least one client.",
                "error"
            );

            return;

        }


        showMessage(
            "Selected clients rolled over successfully.",
            "success"
        );

    });


document
    .getElementById("rolloverAllBtn")
    .addEventListener("click", function () {

        showMessage(
            "All flagged clients rolled over successfully.",
            "success"
        );

    });


document
    .getElementById("generateReportsBtn")
    .addEventListener("click", function () {

        showMessage(
            "Reports generated successfully.",
            "success"
        );

    });
