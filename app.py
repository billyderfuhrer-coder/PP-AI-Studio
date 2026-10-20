from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
import os
import re
import base64
from pathlib import Path
from io import BytesIO

load_dotenv()

HF_TOKEN = os.environ.get("PP_SECRET_API_KEY_1")


print(
    "Token source:",
    "PP_SECRET_API_KEY"
    if os.environ.get("PP_SECRET_API_KEY")
    else "PP_SECRET_API_KEY_1"
    if os.environ.get("PP_SECRET_API_KEY_1")
    else "NONE"
)

MODEL = "black-forest-labs/FLUX.2-klein-9B"

REFERENCE_FOLDER = Path("references")
REFERENCE_IMAGE = REFERENCE_FOLDER / "pp1.jpg"

app = Flask(__name__)

if HF_TOKEN:
    client = InferenceClient(
        api_key=HF_TOKEN,
        provider="fal-ai"
    )
else:
    client = None


print("--------------------------------")
print("PP AI STUDIO")
print("--------------------------------")

if HF_TOKEN:
    print("Hugging Face API token: LOADED")
else:
    print("Hugging Face API token: NOT FOUND")

print("Model:", MODEL)
print("Provider: fal-ai")

if REFERENCE_IMAGE.exists():
    print("PP reference image: FOUND")
    print("Reference:", REFERENCE_IMAGE)
else:
    print("PP reference image: NOT FOUND")

print("--------------------------------")


@app.route("/")
def home():
    print("Homepage requested.")
    return render_template("index.html")


def build_pp_prompt(user_prompt):
    return f"""
Edit the provided reference image according to the user's request.

IDENTITY PRESERVATION:
The reference image defines PP's original identity and recognizable design.
Preserve PP's distinctive face shape, facial features, signature appearance,
and defining visual characteristics. PP should remain recognizable in every
generated image.

INTERPRET THE USER'S INTENT:
Carefully determine what the user actually wants changed.
Distinguish between a limited edit, a costume or accessory change, a scene
change, and a complete character transformation.

Make changes appropriate to the user's specific request. Do not assume every
request is a full transformation, and do not treat every request as a simple
outfit change.

For limited edits, preserve PP's original pose, body shape, proportions,
and silhouette as much as possible. Change only what the user requested.

For full transformations, adapt PP's pose, body structure, silhouette,
clothing, accessories, and other relevant visual features as needed to make
the requested transformation clear. Preserve PP's identity and recognizable
features wherever possible.

TRANSFORMATION ACCURACY:
When the user requests a particular role, character type, activity, or form,
make the overall appearance clearly communicate that specific request.
Do not rely on clothing or accessories alone if the requested transformation
requires changes to the pose, silhouette, change position, body arrangement, or other features.

Do not substitute a different concept for the one requested. Do not introduce
unrequested transformations, effects, objects, or design elements.
Every visual change should support the user's actual intention.

SETTING AND THEME:
make it default base on the reference if no description is added here
if user input a description about setting and theme
Follow the setting, atmosphere, theme, environment, objects, and visual style
specified by the user. Include the requested details while keeping PP as the
main subject. Do not add unrelated themes or let background elements obscure
PP's identity or the requested action.


REQUESTED TEXT:
If the user asks for specific text or dialogue in the image, include the
requested wording as accurately as possible. Make it clearly visible,
correctly spelled, and readable. Use an appropriate placement and format
within the composition. Do not invent dialogue when none was requested.

USER'S ORIGINAL REQUEST:
{user_prompt}

COMPOSITION AND QUALITY:
Create a coherent, polished image that follows the user's request.
Keep PP recognizable, make the requested changes visually clear, and maintain
a balanced composition. Avoid unnecessary redesigns, contradictory details,
unrequested text, and visual elements that conflict with the user's intent.

Watermark:
add a small visible but not huge watermark on the left down side called "PP-AI-Studio"
with a proper roman font text design, text color basing on the requested user prompt description

FINAL PRIORITY:
Follow the user's actual request rather than a fixed transformation template.
Preserve PP's identity, make only appropriate changes, and ensure the final
image communicates the intended result as clearly as possible.
"""
def load_pp_reference():
    if not REFERENCE_IMAGE.exists():
        raise RuntimeError(
            "PP reference image not found. "
            "Please put pp1.jpg inside the references folder."
        )

    try:
        image_bytes = REFERENCE_IMAGE.read_bytes()

        print("--------------------------------")
        print("PP REFERENCE LOADED")
        print("File:", REFERENCE_IMAGE)
        print("Size:", len(image_bytes), "bytes")
        print("--------------------------------")

        return image_bytes

    except Exception as error:
        raise RuntimeError(
            f"Could not read PP reference image: {error}"
        )


def generate_image(prompt):

    print("--------------------------------")
    print("Starting PP image generation...")
    print("Model:", MODEL)
    print("Provider: fal-ai")
    print("Prompt:", prompt)
    print("--------------------------------")

    if not HF_TOKEN:
        raise RuntimeError(
            "HF_TOKEN was not found in .env"
        )

    if client is None:
        raise RuntimeError(
            "Hugging Face client was not initialized."
        )

    reference_image = load_pp_reference()

    final_prompt = build_pp_prompt(prompt)

    try:

        print("Sending PP reference + prompt to Hugging Face...")
        print("Using image-to-image generation...")

        image = client.image_to_image(
            reference_image,
            prompt=final_prompt,
            model=MODEL
        )

        print("--------------------------------")
        print("HUGGING FACE RESPONDED SUCCESSFULLY")
        print("--------------------------------")

    except Exception as error:

        print("--------------------------------")
        print("HUGGING FACE ERROR")
        print(error)
        print("--------------------------------")

        raise RuntimeError(
            f"Hugging Face generation failed: {error}"
        )

    try:

        image_buffer = BytesIO()

        image.save(
            image_buffer,
            format="PNG"
        )

        image_bytes = image_buffer.getvalue()

        encoded_image = base64.b64encode(
            image_bytes
        ).decode("utf-8")

    except Exception as error:

        print("--------------------------------")
        print("IMAGE CONVERSION ERROR")
        print(error)
        print("--------------------------------")

        raise RuntimeError(
            f"Could not process generated image: {error}"
        )

    print("--------------------------------")
    print("PP IMAGE GENERATED SUCCESSFULLY")
    print("--------------------------------")

    return "data:image/png;base64," + encoded_image


@app.route("/generate", methods=["POST"])
def generate():

    print("================================")
    print("GENERATE REQUEST RECEIVED")
    print("================================")

    try:

        data = request.get_json(silent=True) or {}

        prompt = str(
            data.get("prompt", "")
        ).strip()

        print("Received prompt:", prompt)

        if not prompt:
            return jsonify({
                "error": "Please enter a prompt."
            }), 400

        if len(prompt) > 500:
            return jsonify({
                "error": "Prompt is too long."
            }), 400

        if not re.search(
            r"\bpp\b",
            prompt,
            re.IGNORECASE
        ):
            return jsonify({
                "error": "Please include PP in your prompt."
            }), 400

        image = generate_image(prompt)

        return jsonify({
            "image": image
        })

    except Exception as error:

        print("--------------------------------")
        print("GENERATION ERROR")
        print(error)
        print("--------------------------------")

        return jsonify({
            "error": "PP AI Studio is currently in Limited Beta. Image generation is temporarily unavailable while we manage our limited generation capacity. Please try again later."
        }), 500


if __name__ == "__main__":

    print("Starting Flask server...")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
