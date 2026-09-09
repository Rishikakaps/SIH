"""Transcribe an explicitly submitted recording; do not retain audio or submit an answer."""
import os
import httpx
from .ocr_review import ReviewUnavailable

ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"
MAX_AUDIO_BYTES = 12 * 1024 * 1024


def audio_format(raw: bytes) -> tuple[str, str]:
    if raw.startswith(b'\x1aE\xdf\xa3'):
        return 'recording.webm', 'audio/webm'
    if raw.startswith(b'OggS'):
        return 'recording.ogg', 'audio/ogg'
    if raw.startswith(b'RIFF') and raw[8:12] == b'WAVE':
        return 'recording.wav', 'audio/wav'
    if raw[4:8] == b'ftyp':
        return 'recording.mp4', 'audio/mp4'
    raise ReviewUnavailable('Unsupported recording. Record again using Chrome or Edge on localhost.', 422)


def transcribe_audio(raw: bytes, language: str = 'auto') -> str:
    key = os.getenv('GROQ_API_KEY', '').strip()
    if not key:
        raise ReviewUnavailable('Run configure-ai.cmd to add your Groq key, then restart the backend. The same key enables recorded voice input.')
    filename, mime = audio_format(raw)
    data = {'model': os.getenv('GROQ_SPEECH_MODEL', 'whisper-large-v3'),
            'response_format': 'verbose_json', 'temperature': '0'}
    if language != 'auto':
        data['language'] = language
    try:
        with httpx.Client(timeout=httpx.Timeout(120, connect=15), follow_redirects=False) as client:
            response = client.post(ENDPOINT, headers={'Authorization': f'Bearer {key}'},
                                   data=data, files={'file': (filename, raw, mime)})
    except httpx.TimeoutException as exc:
        raise ReviewUnavailable('Transcription timed out. Retry the recording or type your answer.', 504) from exc
    except httpx.HTTPError as exc:
        raise ReviewUnavailable('Cannot connect to Groq. Check your connection and retry the recording.') from exc
    if response.status_code == 429:
        raise ReviewUnavailable('Groq voice quota reached. Wait and retry the recording, or type your answer.', 429)
    if response.status_code in (401, 403):
        raise ReviewUnavailable('Groq rejected the key or speech model access. Check your Groq configuration.')
    if response.status_code >= 400:
        raise ReviewUnavailable(f'Groq could not transcribe this recording (HTTP {response.status_code}). Retry or record again.')
    try:
        result = response.json()
        text = result['text']
        if not isinstance(text, str):
            raise ValueError('invalid text')
        segments = result.get('segments') or []
        if segments and all(s.get('no_speech_prob', 0) > .8 and s.get('avg_logprob', 0) < -1 for s in segments):
            text = ''
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ReviewUnavailable('The speech service returned an invalid transcript. Retry or record again.', 502) from exc
    if not text.strip():
        raise ReviewUnavailable('No clear speech detected. Check the microphone and record again.', 422)
    if len(text.strip()) > 5000:
        raise ReviewUnavailable('The transcript is too long for one answer. Record a shorter answer.', 422)
    return text.strip()
