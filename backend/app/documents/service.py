from __future__ import annotations

import re
from pathlib import Path

from .ocr_engine import ocr_image_bytes
from ..models import ClinicalFact, DocumentRecord, FactSource, TimelineEvent


DEMO_LAB_LINES = [
    "RX LENS DEMO LAB REPORT",
    "Patient: Rajesh Sharma",
    "Date: 22 Aug 2026",
    "Investigation: HbA1c",
    "Value: 8.4 %",
    "Reference range: 4.0-5.6 %",
    "Flag: HIGH",
]

DEMO_RX_LINES = [
    "RX LENS DEMO PRESCRIPTION",
    "Patient: Rajesh Sharma",
    "Date: 18 Aug 2026",
    "Diagnosis: Type 2 Diabetes Mellitus",
    "Medication: Metformin 500 mg twice daily",
    "Medication: Amlodipine 5 mg once daily",
    "Allergy: Penicillin",
]


def create_demo_documents(output_dir: Path) -> list[Path]:
    from PIL import Image, ImageDraw, ImageFont

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = [
        output_dir / "demo_lab_report_rajesh_sharma.png",
        output_dir / "demo_prescription_rajesh_sharma.png",
    ]
    for path, lines in zip(paths, [DEMO_LAB_LINES, DEMO_RX_LINES], strict=True):
        image = Image.new("RGB", (980, 520), "white")
        draw = ImageDraw.Draw(image)
        font = _demo_font(28)
        draw.rectangle((24, 24, 956, 496), outline=(20, 33, 47), width=3)
        for index, line in enumerate(lines):
            draw.text((64, 60 + index * 54), line, fill=(0, 0, 0), font=font)
        image.save(path)
    return paths


def process_document(
    session_id: str,
    filename: str,
    doc_type_hint: str | None,
    raw: bytes | None = None,
    text: str | None = None,
    ocr_language: str = "en",
) -> tuple[DocumentRecord, list[ClinicalFact], list[TimelineEvent]]:
    if text is None and raw is not None:
        ocr = ocr_image_bytes(raw, ocr_language)
        text = ocr.text
        confidence = ocr.confidence
    else:
        text = text or ""
        confidence = 1.0 if text else 0.0

    extracted = extract_clinical_structure(text, doc_type_hint)
    doc = DocumentRecord(
        session_id=session_id,
        filename=filename,
        doc_type_hint=doc_type_hint,
        ocr_text=text,
        original_ocr_text=text,
        confidence=confidence,
        extracted=extracted,
    )
    doc.status = "needs_review" if confidence < 0.75 else "processed"
    facts = facts_from_extraction(session_id, doc.id, extracted)
    for fact in facts:
        fact.confidence = confidence
    timeline = timeline_from_extraction(session_id, doc.id, filename, extracted, facts)
    return doc, facts, timeline


def extract_clinical_structure(text: str, doc_type_hint: str | None = None) -> dict[str, object]:
    clean = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    normalized = _normalize_ocr_text(clean)
    lower = normalized.lower()
    doc_type = doc_type_hint or ("lab_report" if "hba1c" in lower or "reference range" in lower else "prescription" if "medication" in lower else "clinical_document")
    date = _extract_date(normalized)
    diagnoses = re.findall(r"diagnosis:\s*(.+)", normalized, flags=re.IGNORECASE)
    medications = _extract_medications(normalized)
    allergy = _match(r"allergy:\s*(.+)", normalized)
    labs = _extract_labs(normalized)
    return {
        "document_type": doc_type,
        "date": date or "unknown",
        "diagnoses": diagnoses,
        "medications": medications,
        "allergies": [allergy] if allergy else [],
        "labs": labs,
        "raw_text_length": len(clean),
    }


def facts_from_extraction(session_id: str, doc_id: str, extracted: dict[str, object]) -> list[ClinicalFact]:
    facts: list[ClinicalFact] = []
    for diagnosis in extracted.get("diagnoses", []):
        facts.append(ClinicalFact(session_id=session_id, ontology_path="general_medicine.past_history", label="Diagnosis", value=str(diagnosis), source=FactSource.document, source_ref=doc_id))
    for med in extracted.get("medications", []):
        value = f"{med['name']} {med.get('dose', '')} {med.get('frequency', '')}".strip()
        facts.append(ClinicalFact(session_id=session_id, ontology_path="general_medicine.medications", label="Medication", value=value, source=FactSource.document, source_ref=doc_id, metadata=med))
    for allergy in extracted.get("allergies", []):
        facts.append(ClinicalFact(session_id=session_id, ontology_path="general_medicine.allergies", label="Allergy", value=f"{allergy} allergy", source=FactSource.document, source_ref=doc_id))
    for lab in extracted.get("labs", []):
        facts.append(
            ClinicalFact(
                session_id=session_id,
                ontology_path=f"general_medicine.investigations.{str(lab['name']).lower()}",
                label=str(lab["name"]),
                value=str(lab["value"]),
                source=FactSource.lab,
                source_ref=doc_id,
                metadata={"unit": lab.get("unit"), "reference_range": lab.get("reference_range"), "abnormal": lab.get("abnormal")},
            )
        )
    return facts


def timeline_from_extraction(session_id: str, doc_id: str, filename: str, extracted: dict[str, object], facts: list[ClinicalFact]) -> list[TimelineEvent]:
    details = "; ".join(f"{fact.label}: {fact.value}" for fact in facts) or "No structured clinical facts extracted"
    return [
        TimelineEvent(
            session_id=session_id,
            date=str(extracted.get("date") or "unknown"),
            date_precision="unknown" if extracted.get("date") == "unknown" else "day",
            title=f"{extracted.get('document_type', 'clinical_document')} processed",
            details=details,
            source_ref=doc_id or filename,
        )
    ]


def _match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_medications(text: str) -> list[dict[str, str]]:
    meds: list[dict[str, str]] = []
    for line in re.findall(r"medication:\s*(.+)", text, flags=re.IGNORECASE):
        dose = _match(r"([0-9]+(?:\.[0-9]+)?\s*(?:mg|ml|g))", line) or ""
        name = line.split(dose)[0].strip() if dose else line.strip()
        frequency = line.split(dose, 1)[1].strip() if dose and dose in line else ""
        meds.append({"name": name, "dose": dose, "frequency": frequency})
    return meds


def _extract_labs(text: str) -> list[dict[str, object]]:
    if "hba1c" not in _normalize_ocr_text(text).lower():
        return []
    value_match = re.search(r"value:\s*([0-9]+(?:\.[0-9]+)?)\s*(%)?", text, flags=re.IGNORECASE)
    range_match = re.search(r"reference range:\s*([0-9]+(?:\.[0-9]+)?)-([0-9]+(?:\.[0-9]+)?)", text, flags=re.IGNORECASE)
    if not value_match:
        value_match = re.search(r"hba1c\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*%", text, flags=re.IGNORECASE)
    if not value_match:
        return []  # Missing data is unknown, never a fabricated zero.
    value = float(value_match.group(1))
    reference = [float(range_match.group(1)), float(range_match.group(2))] if range_match else None
    abnormal = bool(reference and (value < reference[0] or value > reference[1]))
    return [{"name": "HbA1c", "value": value, "unit": "%", "reference_range": reference, "abnormal": abnormal}]


def _normalize_ocr_text(text: str) -> str:
    return re.sub(r"\bhb\s*a\s*[1il|]\s*c\b", "HbA1c", text, flags=re.IGNORECASE)


def _extract_date(text: str) -> str | None:
    direct = _match(r"date:\s*([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})", text)
    if direct:
        return direct
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if line.lower().startswith("date:") and index + 2 < len(lines):
            day = _match(r"date:\s*([0-9]{1,2})", line)
            year = _match(r"([0-9]{4})", lines[index + 1])
            month = next((candidate for candidate in lines[index + 2 : index + 5] if re.fullmatch(r"[A-Za-z]{3,9}", candidate)), None)
            if day and month and year:
                return f"{day} {month} {year}"
    return None


def _demo_font(size: int):
    from PIL import ImageFont

    for candidate in [
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()
