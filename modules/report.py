"""
modules/report.py
Generates PDF diagnosis reports using ReportLab.
Reports are generated in memory and streamed directly to download.
Never stored as plaintext on disk.

Each report has:
- Trackable UUID (also as QR code)
- Patient/doctor details
- Scan image
- Grad-CAM heatmap
- Diagnosis result + confidence
- Class probability breakdown
- AI disclaimer
"""

import io
import uuid
import json
from datetime import datetime
from PIL import Image
import qrcode

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY


# ── Color scheme ───────────────────────────────────────────────
DARK_BLUE  = colors.HexColor("#0d1b2a")
TEAL       = colors.HexColor("#028090")
LIGHT_GRAY = colors.HexColor("#f0f2f6")
WARNING    = colors.HexColor("#ffc107")
DANGER     = colors.HexColor("#dc3545")
SUCCESS    = colors.HexColor("#28a745")
WHITE      = colors.white


def pil_to_reportlab(pil_image: Image.Image, max_width: float, max_height: float) -> RLImage:
    """Convert PIL Image to ReportLab Image object."""
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    buf.seek(0)

    # maintain aspect ratio
    orig_w, orig_h = pil_image.size
    ratio = min(max_width / orig_w, max_height / orig_h)
    new_w = orig_w * ratio
    new_h = orig_h * ratio

    return RLImage(buf, width=new_w, height=new_h)


def generate_qr_code(data: str) -> Image.Image:
    """Generate a QR code PIL Image from string data."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=4,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def generate_report(
    doctor_name: str,
    doctor_role: str,
    diagnosis_result: dict,
    scan_image: Image.Image,
    heatmap_image: Image.Image,
    report_uuid: str = None,
) -> tuple[bytes, str]:
    """
    Generates a PDF report and returns (pdf_bytes, report_uuid).

    Args:
        doctor_name:      Full name of the doctor
        doctor_role:      Role (doctor/radiologist)
        diagnosis_result: Dict from ai_model.predict()
        scan_image:       PIL Image of the scan
        heatmap_image:    PIL Image of Grad-CAM heatmap
        report_uuid:      Existing UUID or None to generate new one

    Returns:
        (pdf_bytes, report_uuid)
    """

    if not report_uuid:
        report_uuid = str(uuid.uuid4())

    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    buf          = io.BytesIO()

    # ── Document setup ─────────────────────────────────────────
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()

    # custom styles
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Normal"],
        fontSize=22,
        fontName="Helvetica-Bold",
        textColor=DARK_BLUE,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        fontName="Helvetica",
        textColor=TEAL,
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Normal"],
        fontSize=13,
        fontName="Helvetica-Bold",
        textColor=DARK_BLUE,
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica",
        textColor=colors.black,
        spaceAfter=4,
        leading=16,
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontSize=9,
        fontName="Helvetica-Oblique",
        textColor=colors.HexColor("#856404"),
        alignment=TA_JUSTIFY,
        leading=14,
    )
    uuid_style = ParagraphStyle(
        "UUID",
        parent=styles["Normal"],
        fontSize=8,
        fontName="Helvetica",
        textColor=colors.gray,
        alignment=TA_CENTER,
    )

    elements = []

    # ── Header ─────────────────────────────────────────────────
    elements.append(Paragraph("Painosis", title_style))
    elements.append(Paragraph("Medical Image Enhancement & AI Diagnosis System", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=TEAL, spaceAfter=8))

    # ── Report metadata ────────────────────────────────────────
    elements.append(Paragraph("Diagnosis Report", section_style))

    meta_data = [
        ["Report ID:", report_uuid],
        ["Generated By:", f"{doctor_name} ({doctor_role.capitalize()})"],
        ["Generated At:", generated_at],
        ["Model:", "DenseNet121 (Brain Tumor Classification)"],
        ["Model Accuracy:", "94.38% on test dataset"],
    ]

    meta_table = Table(meta_data, colWidths=[3.5 * cm, 14 * cm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), DARK_BLUE),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.black),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 0.3 * cm))

    # ── QR Code ────────────────────────────────────────────────
    qr_image    = generate_qr_code(f"Painosis Report | ID: {report_uuid} | {generated_at}")
    qr_rl       = pil_to_reportlab(qr_image, 2.5 * cm, 2.5 * cm)
    qr_label    = Paragraph(f"Scan to verify<br/>Report ID: {report_uuid[:8]}...", uuid_style)

    qr_table = Table([[qr_rl, qr_label]], colWidths=[3 * cm, 14.5 * cm])
    qr_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(qr_table)
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=8))

    # ── Diagnosis result ───────────────────────────────────────
    elements.append(Paragraph("AI Diagnosis Result", section_style))

    predicted    = diagnosis_result.get("display_name", "Unknown")
    confidence   = diagnosis_result.get("confidence", 0)
    requires_review = diagnosis_result.get("requires_human_review", False)

    # result color
    if requires_review:
        result_color = DANGER
        review_text  = "⚠ HUMAN REVIEW REQUIRED — Confidence below 70%"
    else:
        result_color = SUCCESS
        review_text  = "✓ Confidence above threshold"

    result_data = [
        ["Predicted Class:", predicted],
        ["Confidence Score:", f"{confidence}%"],
        ["Review Status:", review_text],
    ]

    result_table = Table(result_data, colWidths=[4 * cm, 13.5 * cm])
    result_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), DARK_BLUE),
        ("TEXTCOLOR", (1, 0), (1, 0), result_color),
        ("TEXTCOLOR", (1, 1), (1, 1), result_color),
        ("TEXTCOLOR", (1, 2), (1, 2), result_color),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("FONTSIZE", (1, 0), (1, 0), 13),
        ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
    ]))
    elements.append(result_table)
    elements.append(Spacer(1, 0.3 * cm))

    # ── Class probabilities ────────────────────────────────────
    elements.append(Paragraph("Class Probability Breakdown", section_style))

    probs = diagnosis_result.get("all_probabilities", {})
    prob_data = [["Class", "Probability"]]
    for class_name, prob in sorted(probs.items(), key=lambda x: x[1], reverse=True):
        is_predicted = class_name == diagnosis_result.get("predicted_class")
        label = f"{'★ ' if is_predicted else ''}{class_name.capitalize()}"
        prob_data.append([label, f"{prob}%"])

    prob_table = Table(prob_data, colWidths=[9 * cm, 8.5 * cm])
    prob_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
    ]))
    elements.append(prob_table)
    elements.append(Spacer(1, 0.3 * cm))

    # ── Scan images ────────────────────────────────────────────
    elements.append(Paragraph("Scan Images", section_style))

    scan_rl    = pil_to_reportlab(scan_image, 8 * cm, 7 * cm)
    heatmap_rl = pil_to_reportlab(heatmap_image, 8 * cm, 7 * cm)

    scan_label    = Paragraph("Original Scan", ParagraphStyle("c", alignment=TA_CENTER, fontSize=9))
    heatmap_label = Paragraph("Grad-CAM Heatmap", ParagraphStyle("c", alignment=TA_CENTER, fontSize=9))

    img_table = Table(
        [[scan_rl, heatmap_rl], [scan_label, heatmap_label]],
        colWidths=[9 * cm, 9 * cm]
    )
    img_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(img_table)
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=8))

    # ── Disclaimer ─────────────────────────────────────────────
    elements.append(Paragraph("Important Disclaimer", section_style))

    disclaimer_text = """
    This report has been generated by the Painosis AI Diagnosis System using DenseNet121,
    a deep learning model trained on the Kaggle Brain Tumor MRI Dataset with 94.38% test accuracy.
    <br/><br/>
    This AI-generated diagnosis is intended for ASSISTIVE PURPOSES ONLY and is NOT a substitute
    for professional medical judgment. All findings must be reviewed and confirmed by a licensed
    medical professional before any clinical decision is made.
    <br/><br/>
    The system does not store patient identifiable information. This report is generated on-demand
    and the trackable Report ID above can be used to verify report authenticity.
    <br/><br/>
    Report generated by: <b>{doctor}</b> ({role}) | {timestamp}
    """.format(
        doctor=doctor_name,
        role=doctor_role.capitalize(),
        timestamp=generated_at
    )

    # disclaimer box
    disclaimer_table = Table(
        [[Paragraph(disclaimer_text, disclaimer_style)]],
        colWidths=[17.5 * cm]
    )
    disclaimer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff3cd")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#ffc107")),
        ("PADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [6]),
    ]))
    elements.append(disclaimer_table)

    # ── Build PDF ──────────────────────────────────────────────
    doc.build(elements)
    pdf_bytes = buf.getvalue()

    return pdf_bytes, report_uuid