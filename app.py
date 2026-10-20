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
Create an image edit using the provided PP reference image.
The reference is the source of truth for PP's identity and signature design.

CORE RULE — CHANGE ONLY WHAT THE USER ASKS FOR:
First determine whether the request is a limited edit or a full transformation.

FOR NORMAL / LIMITED EDITS (the default):
If the user asks PP to wear, hold, use, stand beside, or appear in something,
keep PP's original signature posture, pose, body shape, body proportions,
silhouette, head shape, face, hairstyle, and recognizable appearance.
Change only the specifically requested item or scene detail. For example,
"make PP wear Egyptian clothing" means keep the original PP character and pose,
and change the outfit to Egyptian-inspired clothing. Do not redesign PP's body,
turn PP into a different character, or add unrequested effects.

FOR EXPLICIT FULL TRANSFORMATIONS:
If the user asks to turn, transform, or make PP into a different role or
fantasy character (for example, a genie, astronaut, robot, or superhero),
adapt PP's pose, clothing, body arrangement, and scene as needed to clearly
show that transformation. However, PP must remain recognizably the same PP:
preserve the reference's distinctive face shape, facial features, head identity,
and characteristic visual design wherever possible. The transformation changes
the role and appropriate features, not PP's identity.

Avoid confusing visual shortcuts. A genie must look clearly like a genie,
with recognizable genie styling such as a magical turban or headpiece, ornate
costume, and intentional magical smoke or a floating/tapered lower body when
appropriate. Do not make a genie look like a generic ghost. Do not replace
the character's face with a vague face, mask, skull, or unrelated face.

TEXT AND DIALOGUE:
If the user requests specific words to appear or be spoken in the image, treat
them as requested visible text. Reproduce the quoted wording accurately when
possible, with clear, legible lettering and correct spelling. Do not omit the
dialogue or replace it with unrelated text. Place it naturally, such as in a
speech bubble, caption, or magical dialogue effect. Keep text out only if
the user did not request it.

USER'S ORIGINAL REQUEST (follow this request; do not rewrite or expose it):
{user_prompt}

Follow the requested subject, action, setting, clothing, props, mood, lighting,
camera angle, composition, and art style. Do not add unrelated changes.
When the request is ambiguous, prefer preserving PP's original signature pose,
body shape, proportions, and design, changing only the clearly requested details.

Create a polished, coherent image in which PP is recognizable and the requested
change is immediately understandable.
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
