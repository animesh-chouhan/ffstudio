async function handleForm(formId, endpoint, targetElId) {
    const form = document.getElementById(formId);
    const targetEl = document.getElementById(targetElId);

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const formData = new FormData(form);

        const response = await fetch(`/${endpoint}`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            alert("Error: " + (await response.text()));
            return;
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        if (targetEl.tagName === "VIDEO") {
            targetEl.src = url;
            targetEl.play();
        } else if (targetEl.tagName === "AUDIO") {
            targetEl.src = url;
            targetEl.play();
        }

        // show download button
        const downloadBtn = document.getElementById("downloadBtn");
        downloadBtn.href = url;
        downloadBtn.style.display = "inline-block";
    });
}
