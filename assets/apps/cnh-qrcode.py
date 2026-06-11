from pathlib import Path

from pypdf import PdfReader, PdfWriter


# Configure the PDF paths here.
INPUT_PDF_PATH = Path(r"../data/CNH-e.pdf")
OUTPUT_PDF_PATH = Path(r"../data/CNH-cut.pdf")

# Crop settings in PDF points.
# Positive values trim content from that side of every page.
CROP_LEFT = 335
CROP_RIGHT = 70
CROP_TOP = 100
CROP_BOTTOM = 550


def crop_pdf(input_path: Path, output_path: Path) -> None:
    reader = PdfReader(str(input_path))
    writer = PdfWriter()

    for page in reader.pages:
        crop_box = page.cropbox

        left = float(crop_box.left) + CROP_LEFT
        right = float(crop_box.right) - CROP_RIGHT
        bottom = float(crop_box.bottom) + CROP_BOTTOM
        top = float(crop_box.top) - CROP_TOP

        if left >= right or bottom >= top:
            raise ValueError("Invalid crop values. The resulting page area would be empty.")

        page.cropbox.lower_left = (left, bottom)
        page.cropbox.upper_right = (right, top)
        writer.add_page(page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as output_file:
        writer.write(output_file)


if __name__ == "__main__":
    if not INPUT_PDF_PATH.exists():
        raise FileNotFoundError(f"Input PDF not found: {INPUT_PDF_PATH}")

    crop_pdf(INPUT_PDF_PATH, OUTPUT_PDF_PATH)
    print(f"Cropped PDF saved to: {OUTPUT_PDF_PATH}")
