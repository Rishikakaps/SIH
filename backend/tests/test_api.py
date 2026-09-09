"""Regression tests. Real OCR tests exercise image pixels, not fixture text."""
from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
from app.main import app
from app.store import store
from app.documents.service import process_document, extract_clinical_structure
from app.dialogue.questions import FIELD_LABELS
from app.dialogue.localization import HINDI_PROMPTS

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_store():
    store.reset()


def session(mode='general_medicine', language='en', consent=True):
    state = client.post('/sessions', json={'mode': mode, 'language': language}).json()
    sid = state['session']['id']
    if consent:
        assert client.post('/consent', json={'session_id': sid, 'language': language, 'scope': ['history', 'documents']}).status_code == 201
    return sid


def answer(sid, text='Not sure', **kwargs):
    return client.post('/conversation/message', json={'session_id': sid, 'content': text, 'input_type': 'typed_text', **kwargs})


def through(sid, field):
    for _ in range(40):
        if store.sessions[sid].current_field == field:
            return
        assert answer(sid).status_code == 200
    raise AssertionError(field)


def add_document(sid, text='Investigation: HbA1c\nValue: 8.4 %\nReference range: 4.0-5.6 %'):
    doc, facts, timeline = process_document(sid, 'lab.png', None, text=text)
    store.documents[sid].append(doc)
    store.facts[sid].extend(facts)
    store.timeline[sid].extend(timeline)
    return doc


def approve(sid):
    return client.post('/physician/review', json={'session_id': sid, 'physician_id': 'dr_demo', 'decision': 'accept', 'edits': {'summary_text': 'Reviewed text'}})


def test_consent_required():
    sid = session(consent=False)
    assert answer(sid).status_code == 403


def test_duplicate_revision_is_rejected():
    sid = session()
    assert answer(sid, 'Chest pain', revision=0).status_code == 200
    assert answer(sid, 'Chest pain', revision=0).status_code == 409
    assert len(store.facts[sid]) == 1
    assert store.sessions[sid].current_field == 'onset'


@pytest.mark.parametrize('mode', ['general_medicine', 'ayush'])
def test_rewind_and_change_branch_preserve_documents(mode):
    sid = session(mode)
    first = answer(sid, 'Chest pain').json()['fact']
    answer(sid, 'Today')
    doc = add_document(sid)
    approve(sid)
    result = client.post('/conversation/rewind', json={'session_id': sid, 'fact_id': first['id'], 'revision': store.sessions[sid].revision})
    assert result.status_code == 200
    assert result.json()['next']['current_field'] == 'chief_complaint'
    assert result.json()['previous_answer'] == 'Chest pain'
    assert all(f['source'] != 'patient_interview' for f in result.json()['facts'])
    assert result.json()['documents'][0]['id'] == doc.id
    assert sid not in store.reviews
    answer(sid, 'Fever')
    assert 'radiation' not in store.sessions[sid].pending_fields
    assert store.sessions[sid].current_field == 'onset'


@pytest.mark.parametrize('mode', ['general_medicine', 'ayush'])
def test_back_after_completion(mode):
    sid = session(mode)
    last = None
    for _ in range(40):
        if store.sessions[sid].completed: break
        last = answer(sid).json()['fact']
    assert store.sessions[sid].completed
    assert answer(sid).status_code == 400
    result = client.post('/conversation/rewind', json={'session_id': sid, 'fact_id': last['id'], 'revision': store.sessions[sid].revision}).json()
    assert not result['next']['completed']
    assert result['next']['current_field'] == last['metadata']['field']
    assert answer(sid, 'Corrected answer').json()['next']['completed']


@pytest.mark.parametrize('mode', ['general_medicine', 'ayush'])
def test_language_switch_keeps_history(mode):
    sid = session(mode)
    answer(sid, 'Chest pain')
    revision = store.sessions[sid].revision
    for language in ['hi', 'en', 'hi']:
        response = client.post('/sessions/language', json={'session_id': sid, 'language': language}).json()
        assert response['session']['revision'] == revision
        assert response['next']['current_field'] == 'onset'
        assert response['facts'][0]['value'] == 'Chest pain'
        assert response['next']['question'] == (HINDI_PROMPTS['onset'] if language == 'hi' else FIELD_LABELS['onset'])
        assert response['next']['option_labels'][0] == ('आज' if language == 'hi' else 'Today')
    assert set(FIELD_LABELS) == set(HINDI_PROMPTS)


@pytest.mark.parametrize('text', ['My knees hurt whenever I climb stairs.', 'मुझे तीन दिन से चक्कर आ रहे हैं।', 'I feel exhausted after meals.', 'मेरे सीने में दर्द है'])
def test_arbitrary_speech_is_saved_verbatim(text):
    sid = session()
    response = client.post('/conversation/message', json={'session_id': sid, 'input_type': 'voice_transcript', 'content': text}).json()
    assert response['fact']['value'] == text
    assert response['fact']['ontology_path'].endswith('.chief_complaint')
    assert response['next']['current_field'] == 'onset'


def test_answer_stays_on_asked_question():
    sid = session()
    answer(sid, 'I need advice about my medication')
    assert store.facts[sid][0].ontology_path.endswith('.chief_complaint')


def test_mode_switch_requires_explicit_reset_and_preserves_docs():
    sid = session()
    answer(sid, 'Chest pain')
    doc = add_document(sid)
    assert client.post('/sessions/mode', json={'session_id': sid, 'mode': 'ayush'}).status_code == 409
    result = client.post('/sessions/mode', json={'session_id': sid, 'mode': 'ayush', 'reset_history': True}).json()
    assert result['next']['current_field'] == 'chief_complaint'
    assert 'Nadi' in result['next']['physician_pending_fields']
    assert result['documents'][0]['id'] == doc.id
    assert all(f['source'] != 'patient_interview' for f in result['facts'])


def test_red_flag_removed_after_correction_and_negation():
    sid = session()
    answer(sid, 'Chest pain')
    through(sid, 'associated_symptoms')
    response = answer(sid, 'Breathlessness and sweating').json()
    assert response['flags']
    fact = response['fact']
    result = client.post('/conversation/rewind', json={'session_id': sid, 'fact_id': fact['id'], 'revision': store.sessions[sid].revision}).json()
    assert not result['flags']
    assert not answer(sid, 'No breathlessness').json()['flags']


@pytest.mark.parametrize('text', [' ', '\n\t'])
def test_blank_answer_rejected_without_advance(text):
    sid = session()
    assert answer(sid, text).status_code == 400
    assert store.sessions[sid].current_field == 'chief_complaint'


def test_unknown_session():
    assert answer('unknown').status_code == 404


def test_missing_lab_value_is_not_zero():
    assert extract_clinical_structure('Investigation: HbA1c\nValue: unreadable')['labs'] == []


def test_missing_reference_range_does_not_crash():
    sid = session()
    add_document(sid, 'Investigation: HbA1c\nValue: 7.5 %')
    response = client.get('/evidence/' + sid)
    assert response.status_code == 200
    assert response.json()[0]['status'] == 'UNVERIFIED'


def test_each_lab_result_is_checked():
    sid = session()
    add_document(sid, 'Investigation: HbA1c\nValue: 5.2 %\nReference range: 4.0-5.6 %')
    add_document(sid)
    evidence = client.get('/evidence/' + sid).json()
    assert any(e['status'] == 'OUT_OF_RANGE' for e in evidence)


def test_ocr_correction_replaces_facts_and_invalidates_approval():
    sid = session()
    doc = add_document(sid)
    old_ids = [f.id for f in store.facts[sid]]
    approve(sid)
    result = client.post(f'/documents/{doc.id}/text', json={'session_id': sid, 'text': 'Investigation: HbA1c\nValue: 5.1 %\nReference range: 4.0-5.6 %'}).json()
    assert result['documents'][0]['status'] == 'manually_corrected'
    assert result['facts'][0]['value'] == '5.1'
    assert all(f['id'] not in old_ids for f in result['facts'])
    assert all(e['status'] != 'OUT_OF_RANGE' for e in result['evidence'])
    assert client.post('/fhir/export', json={'session_id': sid}).status_code == 403


@pytest.mark.parametrize('raw', [b'', b'not an image', b'%PDF-1.4 fake'])
def test_invalid_upload_is_actionable(raw):
    sid = session()
    response = client.post('/documents', data={'session_id': sid}, files={'file': ('bad.png', raw, 'image/png')})
    assert response.status_code == 422
    assert response.json()['detail']
    assert not store.documents[sid]


def test_oversize_upload():
    sid = session()
    response = client.post('/documents', data={'session_id': sid}, files={'file': ('big.png', b'a' * (10 * 1024 * 1024 + 1), 'image/png')})
    assert response.status_code == 413


def test_export_and_sync_require_current_approval():
    sid = session()
    assert client.post('/fhir/export', json={'session_id': sid}).status_code == 403
    assert client.post('/sync/mock', json={'session_id': sid}).status_code == 403
    approve(sid)
    bundle = client.post('/fhir/export', json={'session_id': sid}).json()
    assert bundle['resourceType'] == 'Bundle'
    assert any(e['resource']['resourceType'] == 'Composition' for e in bundle['entry'])
    assert client.post('/sync/mock', json={'session_id': sid}).status_code == 200
    answer(sid)
    assert client.post('/sync/mock', json={'session_id': sid}).status_code == 403


def image_bytes(lines):
    from app.documents.service import _demo_font
    image = Image.new('RGB', (1100, 620), 'white')
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(lines): draw.text((65, 60 + index * 65), line, fill='black', font=_demo_font(34))
    stream = BytesIO(); image.save(stream, format='PNG'); return stream.getvalue()


@pytest.mark.ocr
def test_real_ocr_reads_distinct_image_values():
    sid = session()
    for value in ['7.2', '9.1', '6.8']:
        raw = image_bytes(['LAB REPORT', 'Investigation: HbA1c', f'Value: {value} %', 'Reference range: 4.0-5.6 %'])
        response = client.post('/documents', data={'session_id': sid}, files={'file': ('test.png', raw, 'image/png')})
        assert response.status_code == 202, response.text
        assert response.json()['document']['extracted']['labs'][0]['value'] == float(value)


@pytest.mark.ocr
def test_real_demo_ocr_conflict():
    sid = session()
    answer(sid, 'Chest pain')
    through(sid, 'allergies')
    answer(sid, 'No known allergies')
    response = client.post('/documents/process', json={'session_id': sid})
    assert response.status_code == 200, response.text
    statuses = {e['status'] for e in response.json()['evidence']}
    assert {'CONFLICT', 'OUT_OF_RANGE'} <= statuses
    assert len(response.json()['documents']) == 2


@pytest.mark.ocr
def test_real_blank_image_has_no_text():
    sid = session()
    response = client.post('/documents', data={'session_id': sid}, files={'file': ('blank.png', image_bytes([]), 'image/png')})
    assert response.status_code == 422
    assert 'No readable text' in response.json()['detail']

@pytest.mark.ocr
def test_real_hindi_image_reads_devanagari():
    from pathlib import Path
    candidates = ['C:/Windows/Fonts/Nirmala.ttf', '/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf']
    font_path = next((path for path in candidates if Path(path).exists()), None)
    if not font_path: pytest.skip('Install a Devanagari font to run the Hindi image test')
    image = Image.new('RGB', (1100, 400), 'white')
    draw = ImageDraw.Draw(image)
    draw.text((50, 70), 'रोगी का नाम राजेश शर्मा', fill='black', font=ImageFont.truetype(font_path, 46))
    draw.text((50, 160), 'बुखार और सिर दर्द', fill='black', font=ImageFont.truetype(font_path, 46))
    stream = BytesIO(); image.save(stream, format='PNG')
    sid = session()
    response = client.post('/documents', data={'session_id': sid, 'ocr_language': 'hi'}, files={'file': ('hindi.png', stream.getvalue(), 'image/png')})
    assert response.status_code == 202, response.text
    text = response.json()['document']['ocr_text']
    assert 'राजेश' in text and 'बुखार' in text, text
