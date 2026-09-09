"""Run a complete demo with real OCR: python -m tests.smoke_demo from backend."""
from fastapi.testclient import TestClient
from app.main import app


def main():
    client = TestClient(app)
    result = client.post('/sessions', json={'language': 'en', 'mode': 'general_medicine'}).json()
    sid = result['session']['id']
    client.post('/consent', json={'session_id': sid, 'scope': ['history', 'documents'], 'language': 'en'}).raise_for_status()
    values = {'chief_complaint': 'Chest pain', 'associated_symptoms': 'Breathlessness and sweating', 'allergies': 'No known allergies'}
    while not result['next']['completed']:
        field = result['next']['current_field']
        response = client.post('/conversation/message', json={'session_id': sid, 'input_type': 'typed_text', 'content': values.get(field, 'Not sure')})
        response.raise_for_status()
        result = response.json()
    docs = client.post('/documents/process', json={'session_id': sid})
    docs.raise_for_status()
    summary = client.get('/summary/' + sid)
    summary.raise_for_status()
    client.post('/physician/review', json={'session_id': sid, 'physician_id': 'dr_demo', 'decision': 'accept', 'edits': {'summary_text': str(summary.json()['sections'])}}).raise_for_status()
    bundle = client.post('/fhir/export', json={'session_id': sid})
    bundle.raise_for_status()
    client.post('/sync/mock', json={'session_id': sid}).raise_for_status()
    print('Complete demo passed. Documents:', len(docs.json()['documents']), 'Export:', bundle.json()['resourceType'])

if __name__ == '__main__':
    main()
