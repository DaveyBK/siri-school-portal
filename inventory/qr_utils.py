from pathlib import Path
import qrcode

# Root of the project: .../inventory_v2
ROOT = Path(__file__).resolve().parent.parent
QR_ROOT = ROOT / "data" / "qr"
ITEM_QR_DIR = QR_ROOT / "items"
STUDENT_QR_DIR = QR_ROOT / "students"


def generate_qr_png(content: str, output_path: Path) -> Path:
    """
    Generate a QR code PNG with the given content.
    Returns the path to the created file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = qrcode.make(content)
    img.save(output_path)
    return output_path


def generate_item_qr(item_id: str) -> Path:
    """
    Generate a QR for an item.
    QR content format: I:<item_id>
    File: data/qr/items/<item_id>.png
    """
    content = f"I:{item_id}"
    output_path = ITEM_QR_DIR / f"{item_id}.png"
    return generate_qr_png(content, output_path)


def generate_student_qr(student_id: str) -> Path:
    """
    Generate a QR for a student.
    QR content format: S:<student_id>
    File: data/qr/students/<student_id>.png
    """
    content = f"S:{student_id}"
    output_path = STUDENT_QR_DIR / f"{student_id}.png"
    return generate_qr_png(content, output_path)
