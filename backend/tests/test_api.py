from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.main import app
from app.store import store


client = TestClient(app)


def setup_function():
    store.reset()


def create_consented_session(mode="general_medicine"):
    created = client.post("/sessions", json={"language": "en", "mode": mode}).json()
    session_id = created["session"]["id"]
    client.post("/consent", json={"session_id": session_id, "scope": ["history", "documents", "physician_sharing"], "language": "en"})
    return session_id


def test_consent_blocks_interview():
    created = client.post("/sessions", json={"language": "en", "mode": "general_medicine"}).json()
    response = client.post("/conversation/message", json={"session_id": created["session"]["id"], "input_type": "tapped_option", "content": "Chest pain"})
    assert response.status_code == 403


def test_chest_pain_red_flag_fires():
    session_id = create_consented_session()
    client.post("/conversation/message", json={"session_id": session_id, "input_type": "tapped_option", "content": "Chest pain"})
    response = client.post("/conversation/message", json={"session_id": session_id, "input_type": "tapped_option", "content": "Breathlessness and sweating"})
    assert response.status_code == 200
    assert response.json()["flags"][0]["code"] == "RF_CHEST_PAIN_DYSPNEA"


def test_document_conflict_and_out_of_range():
    session_id = create_consented_session()
    client.post("/conversation/message", json={"session_id": session_id, "input_type": "tapped_option", "content": "Chest pain"})
    client.post("/conversation/message", json={"session_id": session_id, "input_type": "tapped_option", "content": "No known allergies"})
    response = client.post("/documents/process", json={"session_id": session_id})
    statuses = {item["status"] for item in response.json()["evidence"]}
    assert "CONFLICT" in statuses
    assert "OUT_OF_RANGE" in statuses


def test_ayush_returns_pending_physician_fields():
    session_id = create_consented_session("ayush")
    response = client.post("/conversation/message", json={"session_id": session_id, "input_type": "tapped_option", "content": "Digestive discomfort"})
    pending = response.json()["next"]["physician_pending_fields"]
    assert "Nadi" in pending
    assert "Jihva" in pending


def test_fhir_export_is_bundle():
    session_id = create_consented_session()
    client.post("/conversation/message", json={"session_id": session_id, "input_type": "tapped_option", "content": "Chest pain"})
    client.post("/physician/review", json={"session_id": session_id, "physician_id": "dr_demo", "decision": "accept", "edits": {"summary_text": "Physician edited summary text"}})
    response = client.post("/fhir/export", json={"session_id": session_id})
    assert response.json()["resourceType"] == "Bundle"
    assert response.json()["entry"][0]["resource"]["resourceType"] == "Patient"
    resources = [entry["resource"] for entry in response.json()["entry"]]
    compositions = [resource for resource in resources if resource["resourceType"] == "Composition"]
    assert compositions[0]["section"][0]["text"]["div"] == "Physician edited summary text"


def test_fhir_export_requires_physician_approval():
    session_id = create_consented_session()
    response = client.post("/fhir/export", json={"session_id": session_id})
    assert response.status_code == 403


def test_real_ocr_extracts_different_uploaded_lab_values(tmp_path):
    session_id = create_consented_session()
    values = ["7.2", "9.1", "6.8"]
    extracted_values = []
    for index, value in enumerate(values):
        path = tmp_path / f"lab_{index}.png"
        _write_lab_image(path, value, extra=f"Batch {index} unique text")
        with path.open("rb") as handle:
            response = client.post(
                "/documents",
                data={"session_id": session_id, "doc_type_hint": "lab_report"},
                files={"file": (path.name, handle, "image/png")},
            )
        assert response.status_code == 202
        labs = response.json()["documents" if "documents" in response.json() else "document"]
        facts = response.json()["facts"]
        hba1c = [fact for fact in facts if fact["label"] == "HbA1c"]
        assert hba1c, response.json()
        extracted_values.append(hba1c[0]["value"])
    assert extracted_values == values


def _write_lab_image(path, value: str, extra: str) -> None:
    image = Image.new("RGB", (1100, 620), "white")
    draw = ImageDraw.Draw(image)
    font = _font(34)
    lines = [
        "RX LENS TEST LAB REPORT",
        "Patient: Rajesh Sharma",
        "Date: 24 Aug 2026",
        "Investigation: HbA1c",
        f"Value: {value} %",
        "Reference range: 4.0-5.6 %",
        extra,
    ]
    draw.rectangle((24, 24, 1076, 596), outline=(20, 33, 47), width=3)
    for index, line in enumerate(lines):
        draw.text((72, 72 + index * 66), line, fill=(0, 0, 0), font=font)
    image.save(path)


def _font(size: int):
    for candidate in [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()
