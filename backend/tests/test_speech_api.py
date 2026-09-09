from io import BytesIO
import wave
import httpx
import pytest
from fastapi.testclient import TestClient
import app.main as api
from app.ai import transcription as speech
from app.store import store

client = TestClient(api.app)

def wav():
    buffer = BytesIO()
    with wave.open(buffer, 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000); f.writeframes(b'\0\0' * 1600)
    return buffer.getvalue()

@pytest.fixture(autouse=True)
def clean(monkeypatch):
    store.reset(); monkeypatch.delenv('GROQ_API_KEY', raising=False)

def session(consent=True):
    s = client.post('/sessions', json={}).json()['session']['id']
    if consent: client.post('/consent', json={'session_id':s,'scope':['conversation']})
    return s

def send(s, **kwargs):
    data = {'session_id':s, 'revision':store.sessions[s].revision, 'allow_external_processing':'true'}
    data.update(kwargs)
    return client.post('/speech/transcribe', data=data, files={'file':('test.wav', wav(), 'audio/wav')})

def test_audio_requires_both_consents(monkeypatch):
    monkeypatch.setattr(api, 'transcribe_audio', lambda *_: pytest.fail('No external call without consent'))
    assert send(session(False)).status_code == 403
    assert send(session(), allow_external_processing='false').status_code == 400

def test_transcript_is_only_a_draft(monkeypatch):
    s=session(); before=len(store.facts[s]); rev=store.sessions[s].revision
    monkeypatch.setattr(api, 'transcribe_audio', lambda raw,lang: 'मुझे तीन दिन से tired लग रहा है।')
    r=send(s)
    assert r.status_code==200 and r.json()['saved'] is False
    assert r.json()['text'].startswith('मुझे')
    assert len(store.facts[s])==before and store.sessions[s].revision==rev

def test_stale_question_is_rejected_before_and_after_transcription(monkeypatch):
    s=session()
    assert send(s, revision=-1).status_code==409
    def changed(*_): store.sessions[s].revision+=1; return 'Old answer'
    monkeypatch.setattr(api,'transcribe_audio',changed)
    assert send(s).status_code==409

def test_audio_size_empty_and_language_limits(monkeypatch):
    s=session()
    assert send(s,language='invalid').status_code==422
    monkeypatch.setattr(api,'MAX_AUDIO_BYTES',100)
    assert send(s).status_code==413
    r=client.post('/speech/transcribe',data={'session_id':s,'revision':store.sessions[s].revision,'allow_external_processing':'true'},files={'file':('empty.wav',b'')})
    assert r.status_code==422

def transport(monkeypatch, fn):
    monkeypatch.setenv('GROQ_API_KEY','gsk_test_dummy')
    original=httpx.Client
    monkeypatch.setattr(speech.httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(fn),**kwargs))

def test_live_transport_contract_auto_language_and_no_answer_hint(monkeypatch):
    def respond(request):
        assert str(request.url)==speech.ENDPOINT
        assert b'whisper-large-v3' in request.content and b'RIFF' in request.content
        assert b'name="prompt"' not in request.content and b'name="language"' not in request.content
        return httpx.Response(200,json={'text':'Any naturally spoken sentence, without a phrase list.'})
    transport(monkeypatch,respond)
    assert speech.transcribe_audio(wav()).startswith('Any naturally')

@pytest.mark.parametrize('status',[401,403,429,500])
def test_provider_errors_do_not_expose_key(monkeypatch,status):
    transport(monkeypatch,lambda _:httpx.Response(status,text='gsk_test_dummy private'))
    with pytest.raises(speech.ReviewUnavailable) as caught:speech.transcribe_audio(wav())
    assert 'gsk_' not in str(caught.value)
    if status==429:assert caught.value.status_code==429

@pytest.mark.parametrize('body',[{}, {'text':None}, {'text':''}, {'text':'noise','segments':[{'no_speech_prob':.99,'avg_logprob':-2}]}])
def test_invalid_or_silent_response_not_used(monkeypatch,body):
    transport(monkeypatch,lambda _:httpx.Response(200,json=body))
    with pytest.raises(speech.ReviewUnavailable):speech.transcribe_audio(wav())

def test_missing_key_and_unsupported_recording(monkeypatch):
    with pytest.raises(speech.ReviewUnavailable,match='configure-ai'):speech.transcribe_audio(wav())
    monkeypatch.setenv('GROQ_API_KEY','gsk_test_dummy')
    with pytest.raises(speech.ReviewUnavailable,match='Unsupported'):speech.transcribe_audio(b'invalid')

def test_timeout_is_actionable(monkeypatch):
    def timeout(request): raise httpx.ReadTimeout('secret diagnostic',request=request)
    transport(monkeypatch,timeout)
    with pytest.raises(speech.ReviewUnavailable) as caught:speech.transcribe_audio(wav())
    assert caught.value.status_code==504 and 'secret' not in str(caught.value)
