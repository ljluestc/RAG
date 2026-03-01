"""Generate a simple PDF from the demo PRD markdown."""

from pathlib import Path
import textwrap

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def generate_pdf() -> Path:
    md_path = Path("DEMO_PRD_RAG_RETRIEVAL_GROUNDING.md")
    pdf_path = Path("DEMO_PRD_RAG_RETRIEVAL_GROUNDING.pdf")
    lines = md_path.read_text(encoding="utf-8").splitlines()

    page_width, page_height = letter
    x = 0.8 * inch
    y = page_height - 0.8 * inch
    line_height = 14
    max_width_chars = 105

    pdf = canvas.Canvas(str(pdf_path), pagesize=letter)
    pdf.setFont("Helvetica", 10)

    for raw in lines:
        wrapped = textwrap.wrap(raw.replace("\t", "    "), width=max_width_chars) or [""]
        for chunk in wrapped:
            if y < 0.8 * inch:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y = page_height - 0.8 * inch
            pdf.drawString(x, y, chunk)
            y -= line_height

    pdf.save()
    return pdf_path


if __name__ == "__main__":
    path = generate_pdf()
    print(path)
