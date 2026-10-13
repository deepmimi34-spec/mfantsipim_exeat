document.addEventListener("DOMContentLoaded", function () {
    const yearField = document.getElementById("id_year_admitted");
    const classroomField = document.getElementById(
        "id_classroom_group"
    );

    if (!yearField || !classroomField) {
        return;
    }

    function updateClassroomLabels() {
        const admittedYear = Number(yearField.value);
        const currentYear = new Date().getFullYear();

        const formNumber = currentYear - admittedYear + 1;

        Array.from(classroomField.options).forEach((option) => {
            if (!option.value) {
                return;
            }

            // Preserve the original code and programme name.
            if (!option.dataset.classCode) {
                const parts = option.textContent.split(" — ");

                option.dataset.classCode = parts[0];
                option.dataset.programmeName = parts.slice(1).join(" — ");
            }

            const code = option.dataset.classCode;
            const programme = option.dataset.programmeName;

            if (formNumber >= 1 && formNumber <= 3) {
                option.textContent =
                    `${formNumber}${code} — ${programme}`;
            } else if (formNumber > 3) {
                option.textContent =
                    `Graduated — ${code} — ${programme}`;
            } else {
                option.textContent =
                    `Not yet admitted — ${code} — ${programme}`;
            }
        });
    }

    yearField.addEventListener("change", updateClassroomLabels);

    // Set the initial classroom labels.
    updateClassroomLabels();
});