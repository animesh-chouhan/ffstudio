async function handleForm(formId, endpoint, targetElId) {
    const form = document.getElementById(formId);
    const targetEl = document.getElementById(targetElId);

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const formData = new FormData(form);

        const response = await fetch(`http://127.0.0.1:8000/${endpoint}`, {
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
    });
}

handleForm("cropForm", "crop", "videoPreview");
handleForm("trimForm", "trim", "videoPreview");
handleForm("replaceForm", "replace-audio", "videoPreview");
handleForm("imageAudioForm", "image-audio", "videoPreview");
handleForm("mp3Form", "cut-mp3", "audioPreview");