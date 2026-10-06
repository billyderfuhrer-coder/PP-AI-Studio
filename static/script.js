const generateButton = document.getElementById("generateButton");
const promptInput = document.getElementById("prompt");
const imageArea = document.getElementById("imageArea");
const resultStatus = document.getElementById("resultStatus");
const characterCount = document.getElementById("characterCount");




promptInput.addEventListener("input", () => {

    const length = promptInput.value.length;

    characterCount.textContent = `${length} / 500`;

});




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


    imageArea.innerHTML = `
        <div class="placeholder-content">

            <div class="placeholder-icon">
                ✦
            </div>

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



        imageArea.innerHTML = "";

        const image = document.createElement("img");

        image.src = data.image;

        image.alt = "AI-generated PP image";

        image.className = "generated-image";

        imageArea.appendChild(image);

        resultStatus.textContent = "Generation complete";


    } catch (error) {

        console.error(error);

        imageArea.innerHTML = `
            <div class="placeholder-content">

                <div class="placeholder-icon">
                    !
                </div>

                <h3>Generation failed</h3>

                <p>
                    ${error.message}
                </p>

            </div>
        `;

        resultStatus.textContent = "Error";


    } finally {

        generateButton.disabled = false;

        generateButton.innerHTML = "✦ Generate Image";

    }

});