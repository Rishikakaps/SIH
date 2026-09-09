import json
import threading
from io import BytesIO

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

import app.main as api
from app.ai import ocr_review as provider
from app.documents.service import process_document
from app.store import store

client = TestClient(api.app)
SUGGESTION = {'corrected_text': 'Medication: Example 5 mg\nHandwriting: [unclear]', 'uncertainties': [{'location': 'Handwritten line', 'reason': 'Cannot confidently read the frequency.'}], 'quality_notes': 'Check the handwritten region.'}
WIRE_REVIEW = {'clinical_sections': {name: '[not shown]' for name in provider.ClinicalSections.model_fields}, 'uncertainties': SUGGESTION['uncertainties'], 'quality_notes': SUGGESTION['quality_notes']}
WIRE_REVIEW['clinical_sections']['medicines'] = 'Example 5 mg'

@pytest.fixture(autouse=True)
def clean(monkeypatch):
    store.reset()
    api.ai_inflight.clear()
    monkeypatch.delenv('GROQ_API_KEY', raising=False)


def seed():
    sid=client.post('/sessions', json={}).json()['session']['id']
    client.post('/consent', json={'session_id':sid, 'scope':['documents'], 'language':'en'})
    doc,facts,timeline=process_document(sid,'sample.png',None,text='Medication: Examp1e 5 mg')
    store.documents[sid].append(doc);store.facts[sid].extend(facts);store.timeline[sid].extend(timeline)
    image=Image.new('RGB',(200,200),'white');stream=BytesIO();image.save(stream,format='PNG')
    store.document_images[doc.id]=stream.getvalue()
    return sid,doc


def act(sid,doc,**extra):
    return {'session_id':sid,'revision':doc.revision,**extra}


def test_delete_removes_dependencies_and_image():
    sid,doc=seed()
    other,_,_=process_document(sid,'other.png',None,text='Allergy: Penicillin')
    store.documents[sid].append(other)
    client.post('/physician/review',json={'session_id':sid,'physician_id':'demo','decision':'accept'})
    client.post('/sync/mock',json={'session_id':sid})
    response=client.request('DELETE',f'/documents/{doc.id}',json=act(sid,doc))
    assert response.status_code==200
    assert [d['id'] for d in response.json()['documents']]==[other.id]
    assert doc.id not in store.document_images
    assert not any(f.source_ref==doc.id for f in store.facts[sid])
    assert not any(t.source_ref==doc.id for t in store.timeline[sid])
    assert sid not in store.reviews and not store.sessions[sid].synced
    assert client.get(f'/documents/{doc.id}/image',params={'session_id':sid}).status_code==404
    assert client.post('/fhir/export',json={'session_id':sid}).status_code==403


def test_document_cannot_be_deleted_or_read_from_other_session():
    sid,doc=seed();other,_=seed()
    assert client.request('DELETE',f'/documents/{doc.id}',json=act(other,doc)).status_code==404
    assert client.get(f'/documents/{doc.id}/image',params={'session_id':other}).status_code==404
    assert client.post(f'/documents/{doc.id}/ai-review',json=act(other,doc,allow_external_processing=True)).status_code==404


def test_image_is_private_cache_and_valid():
    sid,doc=seed()
    r=client.get(f'/documents/{doc.id}/image',params={'session_id':sid})
    assert r.status_code==200 and r.headers['cache-control']=='no-store'
    assert r.content==store.document_images[doc.id]


def test_delete_stale_revision_does_not_delete():
    sid,doc=seed()
    assert client.request('DELETE',f'/documents/{doc.id}',json={'session_id':sid,'revision':99}).status_code==409
    assert doc in store.documents[sid]


def test_ai_requires_external_permission_and_key():
    sid,doc=seed()
    assert client.post(f'/documents/{doc.id}/ai-review',json=act(sid,doc)).status_code==400
    response=client.post(f'/documents/{doc.id}/ai-review',json=act(sid,doc,allow_external_processing=True))
    assert response.status_code==503 and 'GROQ_API_KEY' in response.json()['detail']
    assert doc.ai_suggestion is None and doc.id not in api.ai_inflight
    assert client.get('/ai/status').json()['configured'] is False


def test_suggestion_requires_explicit_acceptance_and_preserves_original(monkeypatch):
    sid,doc=seed();old_text=doc.ocr_text;old_ids=[f.id for f in store.facts[sid]]
    def fake(raw,text):
        assert raw==store.document_images[doc.id] and text==old_text
        return SUGGESTION.copy()
    monkeypatch.setattr(api,'review_image',fake)
    response=client.post(f'/documents/{doc.id}/ai-review',json=act(sid,doc,allow_external_processing=True))
    assert response.status_code==200
    suggestion=response.json()['documents'][0]['ai_suggestion']
    assert doc.ocr_text==old_text and [f.id for f in store.facts[sid]]==old_ids
    body=act(sid,doc,text=suggestion['corrected_text'],ai_suggestion_id=suggestion['id'])
    assert client.post(f'/documents/{doc.id}/text',json=body).status_code==400
    response=client.post(f'/documents/{doc.id}/text',json={**body,'confirm_reviewed':True})
    assert response.status_code==200
    assert doc.status=='ai_reviewed_by_user' and doc.original_ocr_text==old_text
    assert doc.ai_suggestion is None and doc.review_notes
    summary=client.get('/summary/'+sid).json()['sections']['documents'][0]
    assert summary['text']==SUGGESTION['corrected_text'] and summary['review_notes']
    assert client.post(f'/documents/{doc.id}/text',json={**body,'confirm_reviewed':True}).status_code==409


def test_manual_edit_invalidates_suggestion(monkeypatch):
    sid,doc=seed();monkeypatch.setattr(api,'review_image',lambda *_:SUGGESTION.copy())
    client.post(f'/documents/{doc.id}/ai-review',json=act(sid,doc,allow_external_processing=True))
    assert doc.ai_suggestion
    client.post(f'/documents/{doc.id}/text',json=act(sid,doc,text='Manually corrected'))
    assert doc.ai_suggestion is None


def test_duplicate_ai_review_uses_cached_suggestion(monkeypatch):
    sid,doc=seed();calls=[]
    monkeypatch.setattr(api,'review_image',lambda *_:(calls.append(1) or SUGGESTION.copy()))
    for _ in range(2):
        assert client.post(f'/documents/{doc.id}/ai-review',json=act(sid,doc,allow_external_processing=True)).status_code==200
    assert len(calls)==1


def test_deleted_during_review_is_not_resurrected(monkeypatch):
    sid,doc=seed()
    def fake(*_):
        assert client.request('DELETE',f'/documents/{doc.id}',json=act(sid,doc)).status_code==200
        return SUGGESTION.copy()
    monkeypatch.setattr(api,'review_image',fake)
    assert client.post(f'/documents/{doc.id}/ai-review',json=act(sid,doc,allow_external_processing=True)).status_code==404
    assert not store.documents[sid] and doc.id not in api.ai_inflight


def test_edited_during_review_discards_stale_result(monkeypatch):
    sid,doc=seed()
    def fake(*_):
        client.post(f'/documents/{doc.id}/text',json=act(sid,doc,text='Human correction'))
        return SUGGESTION.copy()
    monkeypatch.setattr(api,'review_image',fake)
    assert client.post(f'/documents/{doc.id}/ai-review',json={'session_id':sid,'revision':0,'allow_external_processing':True}).status_code==409
    assert doc.ocr_text=='Human correction' and doc.ai_suggestion is None


def transport(monkeypatch, response_fn):
    monkeypatch.setenv('GROQ_API_KEY','gsk_test_not_real')
    original=httpx.Client
    monkeypatch.setattr(provider.httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(response_fn),**kwargs))


def test_provider_sends_image_and_ocr_not_just_text(monkeypatch):
    _,doc=seed()
    def respond(request):
        body=__import__('json').loads(request.content)
        assert str(request.url)==provider.ENDPOINT
        assert body['messages'][1]['content'][1]['image_url']['url'].startswith('data:image/jpeg;base64,')
        assert 'Examp1e' in body['messages'][1]['content'][0]['text']
        assert '[unclear]' in body['messages'][0]['content']
        assert body['response_format']=={'type':'json_object'}
        assert len([c for c in body['messages'][1]['content'] if c['type']=='image_url']) == 2
        assert 'unrelated staff lists' in body['messages'][0]['content']
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(WIRE_REVIEW)}}]})
    transport(monkeypatch,respond)
    result = provider.review_image(store.document_images[doc.id],doc.ocr_text)
    assert 'Medicines (as written)\nExample 5 mg' in result['corrected_text']
    assert 'Handwritten notes / changes' in result['corrected_text']
    assert result['focus'] == 'clinical'


@pytest.mark.parametrize('code,expected',[(429,429),(401,503),(403,503),(400,503),(500,503)])
def test_provider_failures_are_actionable_without_secret_leaks(monkeypatch,code,expected):
    _,doc=seed()
    transport(monkeypatch,lambda request:httpx.Response(code,text='gsk_test_not_real private response'))
    with pytest.raises(provider.ReviewUnavailable) as caught: provider.review_image(store.document_images[doc.id],doc.ocr_text)
    assert caught.value.status_code==expected
    assert 'gsk_' not in str(caught.value)


@pytest.mark.parametrize('choice',[{'finish_reason':'length','message':{'content':'{}'}},{'finish_reason':'stop','message':{'content':'not json'}},{'finish_reason':'stop','message':{'content':'{"corrected_text":"hello"}'}}])
def test_incomplete_or_invalid_ai_never_accepted(monkeypatch,choice):
    _,doc=seed();transport(monkeypatch,lambda _:httpx.Response(200,json={'choices':[choice]}))
    with pytest.raises(provider.ReviewUnavailable) as caught:provider.review_image(store.document_images[doc.id],doc.ocr_text)
    assert caught.value.status_code==502


def test_inflight_review_rejects_duplicate(monkeypatch):
    sid,doc=seed();api.ai_inflight.add(doc.id)
    monkeypatch.setattr(api,'review_image',lambda *_:pytest.fail('Duplicate must not call provider'))
    assert client.post(f'/documents/{doc.id}/ai-review',json=act(sid,doc,allow_external_processing=True)).status_code==409


def test_provider_timeout_keeps_manual_path(monkeypatch):
    _,doc=seed()
    def timeout(request): raise httpx.ReadTimeout('private diagnostic',request=request)
    transport(monkeypatch,timeout)
    with pytest.raises(provider.ReviewUnavailable) as caught:provider.review_image(store.document_images[doc.id],doc.ocr_text)
    assert caught.value.status_code==504
    assert 'private diagnostic' not in str(caught.value)


def test_ai_status_never_exposes_key(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','gsk_test_secret')
    result=client.get('/ai/status')
    assert result.json()['configured']
    assert 'gsk_test_secret' not in result.text
