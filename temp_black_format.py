from pathlib import Path

from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature

pdf_path = Path(__file__).resolve().parent.parent / "data" / "CNH-e.pdf"

with pdf_path.open("rb") as f:
    reader = PdfFileReader(f)
    signatures = reader.embedded_signatures
    if not signatures:
        raise ValueError(f"No embedded signatures found in {pdf_path}")

    sig = signatures[0]
    status = validate_pdf_signature(sig)

print(status.pretty_print_details())
