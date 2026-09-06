from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def main() -> None:
    created = client.post("/sessions", json={"language": "en", "mode": "general_medicine"})
    created.raise_for_status()
    session_id = created.json()["session"]["id"]

    client.post("/consent", json={"session_id": session_id, "scope": ["history", "documents", "physician_sharing"], "language": "en"}).raise_for_status()
    client.post("/conversation/message", json={"session_id": session_id, "input_type": "tapped_option", "content": "Chest pain"}).raise_for_status()
    flags_response = client.post("/conversation/message", json={"session_id": session_id, "input_type": "tapped_option", "content": "Breathlessness and sweating"})
    flags_response.raise_for_status()

    document_response = client.post("/documents/process", json={"session_id": session_id})
    document_response.raise_for_status()
    summary_response = client.get(f"/summary/{session_id}")
    summary_response.raise_for_status()
    fhir_response = client.post("/fhir/export", json={"session_id": session_id})
    fhir_response.raise_for_status()
    sync_response = client.post("/sync/mock", json={"session_id": session_id})
    sync_response.raise_for_status()

    statuses = sorted({item["status"] for item in document_response.json()["evidence"]})
    print("session_id:", session_id)
    print("red_flags:", [flag["code"] for flag in flags_response.json()["flags"]])
    print("evidence_statuses:", statuses)
    print("summary_label:", summary_response.json()["label"])
    print("fhir_resource:", fhir_response.json()["resourceType"])
    print("sync_status:", sync_response.json()["status"])


if __name__ == "__main__":
    main()
