import argparse
from pathlib import Path

from asn1crypto import pem, x509
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext

base_dir = Path(__file__).resolve().parent.parent
certs_dir = base_dir / "certs" / "icp-brasil"


def load_certificate(cert_path: Path) -> x509.Certificate:
    cert_bytes = cert_path.read_bytes()
    if pem.detect(cert_bytes):
        _, _, cert_bytes = pem.unarmor(cert_bytes)
    return x509.Certificate.load(cert_bytes)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the first embedded signature in a CNH PDF."
    )
    parser.add_argument("pdf_path", type=Path, help="Path to the PDF file to validate.")
    return parser.parse_args()


trust_root_paths = sorted(certs_dir.glob("ICP-Brasilv*.crt"))
other_cert_paths = sorted(
    path for path in certs_dir.glob("*.crt") if path not in trust_root_paths
)

def main() -> None:
    args = parse_args()
    pdf_path = args.pdf_path.expanduser().resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    validation_context = ValidationContext(
        trust_roots=[load_certificate(path) for path in trust_root_paths],
        other_certs=[load_certificate(path) for path in other_cert_paths],
        allow_fetching=False,
        revocation_mode="soft-fail",
    )

    with pdf_path.open("rb") as f:
        reader = PdfFileReader(f)
        signatures = reader.embedded_signatures
        if not signatures:
            raise ValueError(f"No embedded signatures found in {pdf_path}")

        sig = signatures[0]
        if sig.self_reported_timestamp is not None:
            validation_context = ValidationContext(
                trust_roots=[load_certificate(path) for path in trust_root_paths],
                other_certs=[load_certificate(path) for path in other_cert_paths],
                allow_fetching=False,
                revocation_mode="soft-fail",
                moment=sig.self_reported_timestamp,
                best_signature_time=sig.self_reported_timestamp,
            )

        status = validate_pdf_signature(
            sig, signer_validation_context=validation_context
        )

    print(status.pretty_print_details())


if __name__ == "__main__":
    main()
