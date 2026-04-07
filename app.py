import os
import zipfile
from flask import Flask, render_template, request, send_file
from PIL import Image
from werkzeug.utils import secure_filename
import io

# Optional: background removal
try:
    from rembg import remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
CONVERTED_FOLDER = "converted"
CANVAS_SIZE = 800

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit


def fit_image_on_canvas(img, canvas_size=CANVAS_SIZE, transparent=False):
    width, height = img.size
    scale = canvas_size / max(width, height)
    new_width = int(width * scale)
    new_height = int(height * scale)

    img_resized = img.resize((new_width, new_height), Image.LANCZOS)

    mode = "RGBA" if transparent else "RGB"
    color = (0, 0, 0, 0) if transparent else (255, 255, 255)

    canvas = Image.new(mode, (canvas_size, canvas_size), color)
    x = (canvas_size - new_width) // 2
    y = (canvas_size - new_height) // 2

    if img_resized.mode == "RGBA":
        canvas.paste(img_resized, (x, y), img_resized)
    else:
        canvas.paste(img_resized, (x, y))

    return canvas


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        files = request.files.getlist("images")
        output_format = request.form["format"].lower()
        resize_mode = request.form.get("mode", "fit")
        bg_choice = request.form.get("bg", "white").lower()
        remove_bg = request.form.get("remove_bg") == "on"
        transparent = bg_choice == "transparent"

        is_single_file = len(files) == 1
        if is_single_file:
            file = files[0]
            if not file or not file.filename:
                return "No file uploaded", 400

            filename = secure_filename(file.filename)
            input_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(input_path)
            name = os.path.splitext(filename)[0]
            output_filename = f"{name}.{output_format}"
            output_path = os.path.join(CONVERTED_FOLDER, output_filename)

            img = Image.open(input_path)

            if remove_bg and REMBG_AVAILABLE:
                input_bytes = io.BytesIO()
                img.save(input_bytes, format="PNG")
                input_bytes = input_bytes.getvalue()
                result = remove(input_bytes)
                img = Image.open(io.BytesIO(result))

            if resize_mode == "fit":
                img = fit_image_on_canvas(img, transparent=transparent)
            elif resize_mode == "crop":
                width, height = img.size
                min_dim = min(width, height)
                left = (width - min_dim) // 2
                top = (height - min_dim) // 2
                right = left + min_dim
                bottom = top + min_dim
                img = img.crop((left, top, right, bottom))
                img = img.resize((CANVAS_SIZE, CANVAS_SIZE), Image.LANCZOS)
                if transparent and output_format in ["png", "webp"]:
                    img = img.convert("RGBA")
                else:
                    img = img.convert("RGB")
            else:
                img = fit_image_on_canvas(img, transparent=transparent)

            if output_format in ["jpg", "jpeg"]:
                img = img.convert("RGB")

            img.save(output_path, output_format.upper())
            return send_file(output_path, as_attachment=True)

        # Multiple files → ZIP
        zip_path = os.path.join(CONVERTED_FOLDER, "converted_images.zip")
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for file in files:
                if not file or not file.filename:
                    continue
                filename = secure_filename(file.filename)
                input_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(input_path)
                name = os.path.splitext(filename)[0]
                output_filename = f"{name}.{output_format}"
                output_path = os.path.join(CONVERTED_FOLDER, output_filename)

                img = Image.open(input_path)

                if remove_bg and REMBG_AVAILABLE:
                    input_bytes = io.BytesIO()
                    img.save(input_bytes, format="PNG")
                    input_bytes = input_bytes.getvalue()
                    result = remove(input_bytes)
                    img = Image.open(io.BytesIO(result))

                if resize_mode == "fit":
                    img = fit_image_on_canvas(img, transparent=transparent)
                elif resize_mode == "crop":
                    width, height = img.size
                    min_dim = min(width, height)
                    left = (width - min_dim) // 2
                    top = (height - min_dim) // 2
                    right = left + min_dim
                    bottom = top + min_dim
                    img = img.crop((left, top, right, bottom))
                    img = img.resize((CANVAS_SIZE, CANVAS_SIZE), Image.LANCZOS)
                    if transparent and output_format in ["png", "webp"]:
                        img = img.convert("RGBA")
                    else:
                        img = img.convert("RGB")
                else:
                    img = fit_image_on_canvas(img, transparent=transparent)

                if output_format in ["jpg", "jpeg"]:
                    img = img.convert("RGB")

                img.save(output_path, output_format.upper())
                zipf.write(output_path, output_filename)

        return send_file(zip_path, as_attachment=True)

    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)