
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from PIL import Image, ImageDraw, ImageFont
import os
import re
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
Edit the provided PP reference image according to the user's request.

IDENTITY PRESERVATION:
The reference image defines PP's original identity.
Preserve PP's distinctive rounded white face, recognizable facial
features, black sunglasses, smile, and signature appearance.
PP must remain recognizable in the finished image.

INTERPRET THE REQUEST:
Understand exactly what the user wants.

For limited edits, preserve PP's original pose, body shape, proportions,
and silhouette as much as possible.

For costume changes, dress PP in the requested clothing while preserving
PP's recognizable original shape and identity.

For full transformations, adjust PP's pose, body arrangement, silhouette,
clothing, and relevant features as needed to make the requested
transformation unmistakable. Do not merely add a costume if the requested
transformation requires a different body arrangement.

Do not replace the requested concept with a different one.

SETTING AND COMPOSITION:
If the user does not specify a new setting, retain the reference image's
general setting and style where appropriate.

If the user specifies a setting, follow it accurately.
Include requested objects, activities, atmosphere, and background details.
Keep PP and the main requested action clearly visible.

EXACT TEXT REQUIREMENTS:
If the user requests specific wording on a sign, banner, poster, screen,
or other object, reproduce the wording exactly as provided.

Preserve every word, its spelling, punctuation, and order.
Do not paraphrase, translate, shorten, or replace the requested text.
Do not add unrelated words, random letters, fake logos, or extra text.

When a sign is requested:
- Show one clearly visible sign unless the user requests more.
- Face the sign toward the viewer whenever appropriate.
- Use large, simple, high-contrast lettering.
- Keep the entire requested message inside the sign.
- Do not put parts of the message outside the sign.
- Do not invent additional dialogue or signage.

The user's exact quoted wording is the intended text, not a suggestion.

USER'S ORIGINAL REQUEST:
{user_prompt}

COMPOSITION AND QUALITY:
Create a polished, coherent image that follows the user's actual request.
Preserve PP's identity while making the requested transformation clear.
Avoid contradictory details, unrelated objects, unnecessary text,
and changes that conflict with the request.

WATERMARK:
Leave a small, unobstructed area in the bottom-left corner for a watermark
that will be added after image generation.

Do not attempt to draw or spell the watermark yourself.
Do not put watermark lettering on the user's requested sign.

FINAL PRIORITY:
Follow the user's actual request, preserve PP's identity, and make the
requested scene and actions easy to understand.
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

    # Scale the watermark to the output image size.
    font_size = max(12, min(30, width // 38))
    font = load_watermark_font(font_size)

    padding = max(6, width // 120)
    margin_x = max(12, width // 40)
    margin_y = max(12, height // 40)

    # Measure the actual text dimensions.
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

    # Keep the watermark inside even unusually small images.
    x = max(0, min(x, width - box_width))
    y = max(0, min(y, height - box_height))

    # Draw on a separate transparent layer.
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Subtle dark backing keeps the watermark readable on
    # both light and dark backgrounds.
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
    """Convert a Pillow image to a PNG data URL."""

    image_buffer = BytesIO()

    image.save(image_buffer, format="PNG")

    encoded_image = base64.b64encode(
        image_buffer.getvalue()
    ).decode("utf-8")

    return "data:image/png;base64," + encoded_image


def generate_image(prompt):
    print("--------------------------------")
    print("Starting PP image generation...")
    print("Model:", MODEL)
    print("Provider: fal-ai")
    print("Prompt:", prompt)
    print("--------------------------------")

    if not HF_TOKEN:
        raise RuntimeError(
            "Hugging Face API token was not found."
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

        print("Hugging Face generation succeeded.")

    except Exception as error:
        print("HUGGING FACE ERROR:", error)

        raise RuntimeError(
            f"Hugging Face generation failed: {error}"
        )

    try:
        # Add the watermark after the AI finishes generating.
        # This does not depend on the model drawing text correctly.
        image = add_watermark(image)

        # Convert the watermarked image to the response format.
        image_url = image_to_data_url(image)

        print("PP image processed successfully.")

        return image_url

    except Exception as error:
        print("IMAGE PROCESSING ERROR:", error)

        raise RuntimeError(
            f"Could not process generated image: {error}"
        )


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

        image = generate_image(prompt)

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
