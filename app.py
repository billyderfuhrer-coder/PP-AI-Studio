
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

from PIL import Image, ImageDraw, ImageFont, ImageStat
import os
import re
import time
import base64
from pathlib import Path
from io import BytesIO

load_dotenv()

HF_TOKEN = (
    os.environ.get("PP_SECRET_API_KEY_1")
    or os.environ.get("PP_SECRET_API_KEY")
)

MODEL = "black-forest-labs/FLUX.2-klein-9B"

REFERENCE_FOLDER = Path("references")
REFERENCE_IMAGE = REFERENCE_FOLDER / "pp1.jpg"

WATERMARK_TEXT = "PP-AI-Studio"

GENERATION_COOLDOWN_SECONDS = 25
last_generation_times = {}

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
print("Hugging Face API token:", "LOADED" if HF_TOKEN else "NOT FOUND")
print("Model:", MODEL)
print("Provider: fal-ai")
print("PP reference image:", "FOUND" if REFERENCE_IMAGE.exists() else "NOT FOUND")
print("--------------------------------")


@app.route("/")
def home():
    print("Homepage requested.")
    return render_template("index.html")



def build_pp_prompt(user_prompt):
    return f"""
Create a polished, detailed image edit using the supplied PP
reference image as the identity reference.

IDENTITY — HIGHEST PRIORITY:
PP must remain unmistakably recognizable.
Preserve PP's original rounded white face, black sunglasses,
recognizable smile, and distinctive head shape.
Keep PP's signature appearance unless the user explicitly
requests a clothing or character transformation.
Do not replace PP with a generic person or a different character.

FOLLOW THE USER'S REQUEST:
The user's complete request is:
{user_prompt}

Interpret the request as a complete visual scene, not merely
as a costume description.

ACTION AND POSE:
Identify the main action requested by the user.
Actually show PP performing that action.
If PP is riding, flying, driving, sitting, holding something,
or interacting with an object, make that interaction clear.
Adjust PP's body position, limbs, orientation, and posture
as necessary for the requested action.
Do not preserve the reference pose when it conflicts with
the requested action.

OBJECTS AND ENVIRONMENT:
Include the requested main objects and background elements.
Place objects in the correct spatial relationships.
If the user requests a vehicle, show PP interacting with it
in a physically believable way.
If the user requests a specific planet or location, make that
environment visually recognizable.
Include requested secondary details instead of ignoring them.
Do not substitute unrelated objects for requested objects.

CLOTHING AND TRANSFORMATIONS:
When the user requests a costume or themed outfit, apply it
to PP while preserving PP's recognizable face and head.
When a full character transformation is requested, change
the pose, body styling, and outfit as needed to communicate
the transformation clearly.
Do not interpret a requested transformation as only a hat
or costume placed on an otherwise unrelated character.

COMPOSITION AND LIGHTING:
Make PP and the main action easy to see.
Use a clear composition with readable foreground, middle
ground, and background where appropriate.
Use lighting and colors that fit the requested environment.
Keep important objects visible and avoid hiding PP behind
the vehicle, props, shadows, or background.

FINAL REQUIREMENTS:
Follow the user's requested scene and action accurately.
Do not omit major requested elements.
Do not add text, captions, or speech bubbles unless requested.
Do not let the reference image's original background or pose
override the user's requested scene.
Produce one coherent, visually appealing image.
"""



def load_pp_reference():
    if not REFERENCE_IMAGE.exists():
        raise RuntimeError(
            "PP reference image not found. "
            "Put pp1.jpg inside the references folder."
        )

    try:
        image_bytes = REFERENCE_IMAGE.read_bytes()

        print("PP reference loaded:", REFERENCE_IMAGE)
        print("Reference size:", len(image_bytes), "bytes")

        return image_bytes

    except Exception as error:
        raise RuntimeError(
            f"Could not read PP reference image: {error}"
        )


def load_watermark_font(size):
    """Load a readable system font, with a built-in fallback."""

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]

    for font_path in font_paths:
        try:
            if Path(font_path).exists():
                return ImageFont.truetype(font_path, size)
        except OSError:
            continue

    return ImageFont.load_default()


def add_watermark(image):
    """
    Add a real, readable PP-AI-Studio watermark
    to the bottom-left corner of the final image.
    """

    if image.mode != "RGBA":
        image = image.convert("RGBA")

    width, height = image.size

    font_size = max(12, min(30, width // 38))
    font = load_watermark_font(font_size)

    padding = max(6, width // 120)
    margin_x = max(12, width // 40)
    margin_y = max(12, height // 40)

    temporary_draw = ImageDraw.Draw(image)
    left, top, right, bottom = temporary_draw.textbbox(
        (0, 0),
        WATERMARK_TEXT,
        font=font,
        stroke_width=1
    )

    text_width = right - left
    text_height = bottom - top

    box_width = text_width + padding * 2
    box_height = text_height + padding * 2

    x = margin_x
    y = height - margin_y - box_height

    x = max(0, min(x, width - box_width))
    y = max(0, min(y, height - box_height))

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    draw.rounded_rectangle(
        (
            x,
            y,
            x + box_width,
            y + box_height
        ),
        radius=max(4, padding),
        fill=(12, 8, 24, 185)
    )

    text_x = x + padding - left
    text_y = y + padding - top

    # White lettering with a dark outline for contrast.
    draw.text(
        (text_x, text_y),
        WATERMARK_TEXT,
        font=font,
        fill=(255, 255, 255, 245),
        stroke_width=1,
        stroke_fill=(0, 0, 0, 230)
    )

    image = Image.alpha_composite(image, overlay)

    print(
        f"Watermark added: {WATERMARK_TEXT} "
        f"at bottom-left ({x}, {y})"
    )

    return image


def image_to_data_url(image):
    

    image_buffer = BytesIO()

    image.save(image_buffer, format="PNG")

    encoded_image = base64.b64encode(
        image_buffer.getvalue()
    ).decode("utf-8")

    return "data:image/png;base64," + encoded_image

def get_visitor_key():
    return request.remote_addr or "unknown"


def get_last_generation_time(visitor_key):
    return last_generation_times.get(visitor_key)


def record_last_generation_time(visitor_key, timestamp):
    last_generation_times[visitor_key] = timestamp

def generate_image(prompt):
    print("--------------------------------")
    print("Starting PP image generation...")
    print("Model:", MODEL)
    print("Provider: fal-ai")
    print("Prompt:", prompt)
    print("--------------------------------")

    if not HF_TOKEN:
        raise RuntimeError("Hugging Face API token was not found.")

    if client is None:
        raise RuntimeError("Hugging Face client was not initialized.")

    reference_image = load_pp_reference()
    final_prompt = build_pp_prompt(prompt)

    try:
        print("Sending PP reference + prompt to Hugging Face...")

        image = client.image_to_image(
            reference_image,
            prompt=final_prompt,
            model=MODEL
        )

        print("Hugging Face returned an image.")

    except Exception as error:
        print("--------------------------------")
        print("HUGGING FACE GENERATION ERROR")
        print(repr(error))
        print("--------------------------------")
        raise RuntimeError(f"Hugging Face generation failed: {error}")

    try:
        if not isinstance(image, Image.Image):
            raise RuntimeError(
                f"Unexpected image result type: {type(image).__name__}"
            )

        image = image.convert("RGB")

        stats = ImageStat.Stat(image)
        mean_brightness = sum(stats.mean) / 3
        channel_variation = sum(stats.stddev) / 3

        print("Generated image size:", image.size)
        print("Mean brightness:", mean_brightness)
        print("Channel variation:", channel_variation)

        if mean_brightness < 3 and channel_variation < 3:
            raise RuntimeError(
                "The model returned a nearly black image. "
                "The result was rejected."
            )

    except Exception as error:
        print("--------------------------------")
        print("IMAGE VALIDATION ERROR")
        print(repr(error))
        print("--------------------------------")
        raise RuntimeError(f"Image validation failed: {error}")

    try:
        image = add_watermark(image)
        image_url = image_to_data_url(image)

        print("PP image processed successfully.")
        return image_url

    except Exception as error:
        print("--------------------------------")
        print("FINAL IMAGE PROCESSING ERROR")
        print(repr(error))
        print("--------------------------------")
        raise RuntimeError(f"Final image processing failed: {error}")


@app.route("/generate", methods=["POST"])
def generate():
    print("================================")
    print("GENERATE REQUEST RECEIVED")
    print("================================")

    try:
        data = request.get_json(silent=True) or {}

        prompt = str(data.get("prompt", "")).strip()

        print("Received prompt:", prompt)

        if not prompt:
            return jsonify({
                "error": "Please enter a prompt."
            }), 400

        if len(prompt) > 500:
            return jsonify({
                "error": "Prompt is too long."
            }), 400

        if not re.search(r"\bpp\b", prompt, re.IGNORECASE):
            return jsonify({
                "error": "Please include PP in your prompt."
            }), 400

        visitor_key = get_visitor_key()
        now = time.time()

        last_generation = get_last_generation_time(visitor_key)

        if last_generation is not None:
            elapsed = now - last_generation
            remaining_wait = max(
                0,
                int(GENERATION_COOLDOWN_SECONDS - elapsed + 0.99)
            )

            if remaining_wait > 0:
                return jsonify({
                    "error": (
                        f"Please wait {remaining_wait} seconds "
                        "before generating another image."
                    ),
                    "error_code": "GENERATION_COOLDOWN",
                    "wait_seconds": remaining_wait
                }), 429

        
        image = generate_image(prompt)

        
        record_last_generation_time(visitor_key, time.time())

        return jsonify({
            "image": image
        })

    except Exception as error:
        print("GENERATION ERROR:", error)

        return jsonify({
            "error": (
                "PP AI Studio is currently in Limited Beta. "
                "Image generation is temporarily unavailable "
                "while we manage our limited generation capacity. "
                "Please try again later."
            )
        }), 500


if __name__ == "__main__":
    print("Starting Flask server...")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
