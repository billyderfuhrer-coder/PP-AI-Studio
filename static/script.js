const generateButton = document.getElementById("generateButton");
const promptInput = document.getElementById("prompt");
const imageArea = document.getElementById("imageArea");
const resultStatus = document.getElementById("resultStatus");
const characterCount = document.getElementById("characterCount");
const downloadBtn = document.getElementById("downloadBtn");

// Prompt character counter
promptInput.addEventListener("input", () => {
    const length = promptInput.value.length;
    characterCount.textContent = `${length} / 500`;
});

// Hide download button initially
downloadBtn.hidden = true;

generateButton.addEventListener("click", async () => {
    const prompt = promptInput.value.trim();

    if (!prompt) {
        resultStatus.textContent = "Enter a prompt first.";
        promptInput.focus();
        return;
    }

    if (!/\bpp\b/i.test(prompt)) {
        resultStatus.textContent = "Prompt must include PP.";
        alert("Please include the word PP in your prompt.");
        return;
    }

    generateButton.disabled = true;
    generateButton.innerHTML = "✦ Generating...";
    resultStatus.textContent = "Creating your image...";

    // Hide the previous download while generating
    downloadBtn.hidden = true;
    downloadBtn.removeAttribute("href");

    imageArea.innerHTML = `
        <div class="placeholder-content">
            <div class="placeholder-icon">✦</div>
            <h3>Creating your image...</h3>
            <p>
                The AI is working on your creation.
                This may take a little while.
            </p>
        </div>
    `;

    try {
        const response = await fetch("/generate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                prompt: prompt
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || "Something went wrong."
            );
        }

        if (!data.image) {
            throw new Error("No generated image was returned.");
        }

        // Display the generated image
        imageArea.innerHTML = "";

        const image = document.createElement("img");
        image.src = data.image;
        image.alt = "AI-generated PP image";
        image.className = "generated-image";

        imageArea.appendChild(image);

        // Connect the download button to the PNG data URL
        downloadBtn.href = data.image;
        downloadBtn.download = "PP-AI-Studio.png";
        downloadBtn.hidden = false;

        resultStatus.textContent = "Generation complete";

    } catch (error) {
        console.error(error);

        imageArea.innerHTML = `
            <div class="placeholder-content">
                <div class="placeholder-icon">!</div>
                <h3>Generation failed</h3>
                <p></p>
            </div>
        `;

        // Display the error safely
        imageArea.querySelector("p").textContent = error.message;

        resultStatus.textContent = "Error";

    } finally {
        generateButton.disabled = false;
        generateButton.innerHTML = "✦ Generate Image";
    }
});
