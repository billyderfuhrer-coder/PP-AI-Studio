from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
import os
import re
import base64
from pathlib import Path
from io import BytesIO

load_dotenv()

HF_TOKEN = os.environ.get("PP_SECRET_API_KEY")

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
Create a new image featuring the same PP person shown in the
provided reference image.

The reference image is the primary visual identity reference.

Preserve PP's recognizable:
- face and facial appearance
- head and body proportions
- hairstyle
- distinctive body shape
- signature suit and clothing style
- overall recognizable appearance

Do NOT replace PP with a generic businessman.
Do NOT invent a completely different person.
Do NOT change PP into another character.

The user's requested scene is:

{user_prompt}

The generated image should show PP naturally placed into
the requested scene while keeping PP visually recognizable.

Follow the requested:
- environment
- pose
- clothing changes, if requested
- lighting
- camera angle
- composition
- artistic style

Make the final image detailed, polished and visually appealing.
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