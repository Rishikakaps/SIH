"""UI translations; stored option values remain stable across languages."""
HINDI_PROMPTS = {
    "chief_complaint": "आज आपको मुख्य तकलीफ़ क्या है?",
    "onset": "यह तकलीफ़ कब शुरू हुई?",
    "location": "तकलीफ़ सबसे अधिक कहाँ महसूस होती है?",
    "character": "तकलीफ़ या दर्द कैसा महसूस होता है?",
    "radiation": "क्या दर्द हाथ, जबड़े, पीठ या कहीं और जाता है?",
    "severity": "0 से 10 तक दर्द कितना तेज़ है?",
    "duration": "हर बार तकलीफ़ कितनी देर रहती है?",
    "aggravating_factors": "किन चीज़ों से तकलीफ़ बढ़ती है?",
    "relieving_factors": "किन चीज़ों से आराम मिलता है?",
    "associated_symptoms": "क्या साँस फूलना, पसीना, बेहोशी, उल्टी, कमज़ोरी या कोई और लक्षण है?",
    "past_history": "क्या पहले मधुमेह, उच्च रक्तचाप, ऑपरेशन या कोई और बीमारी रही है?",
    "medications": "क्या आप नियमित रूप से कोई दवा लेते हैं?",
    "allergies": "क्या आपको किसी दवा या खाने से एलर्जी है?",
    "family_history": "क्या परिवार में किसी को ऐसी बीमारी, मधुमेह, उच्च रक्तचाप या हृदय रोग है?",
    "personal_history": "अपनी नींद, भूख, तंबाकू, शराब और रोज़ की गतिविधियों के बारे में बताइए।",
    "ros": "क्या कोई और लक्षण है जो आप डॉक्टर को बताना चाहते हैं?",
    "prakriti_proxy": "आमतौर पर आपके शरीर की कौन सी प्रवृत्ति रहती है?",
    "satmya": "कौन सा भोजन, मौसम या दिनचर्या आपको अनुकूल लगता है?",
    "sattva": "तनाव, नींद और भावनाओं का आपके लक्षणों पर क्या असर पड़ता है?",
    "ahara_shakti": "आपकी भूख और पाचन कैसा है?",
    "vyayama_shakti": "आप आराम से कितना व्यायाम कर सकते हैं?",
    "vaya": "कृपया अपना आयु वर्ग बताइए।",
    "ahara_vihara": "खानपान या जीवनशैली की कौन सी बातें लक्षणों से जुड़ी लगती हैं?",
    "nidana": "आपके अनुसार बीमारी किस कारण शुरू हुई या बढ़ी?",
}

OPTIONS = {
    "chief_complaint": [("Chest pain", "सीने में दर्द"), ("Fever", "बुखार"), ("Abdominal pain", "पेट में दर्द"), ("Headache", "सिरदर्द")],
    "onset": [("Today", "आज"), ("Yesterday", "कल"), ("Several days ago", "कुछ दिन पहले")],
    "severity": [("Mild (1–3)", "हल्का (1–3)"), ("Moderate (4–6)", "मध्यम (4–6)"), ("Severe (7–10)", "तेज़ (7–10)")],
    "duration": [("A few minutes", "कुछ मिनट"), ("A few hours", "कुछ घंटे"), ("Continuous", "लगातार")],
    "associated_symptoms": [("Breathlessness and sweating", "साँस फूलना और पसीना"), ("No breathlessness", "साँस नहीं फूलती"), ("Pain moving to arm or jaw", "दर्द हाथ या जबड़े तक जाता है")],
    "allergies": [("No known allergies", "कोई ज्ञात एलर्जी नहीं"), ("Penicillin allergy", "पेनिसिलिन से एलर्जी"), ("Not sure", "पता नहीं")],
    "medications": [("No regular medicines", "नियमित दवा नहीं लेता/लेती"), ("Not sure", "पता नहीं")],
    "prakriti_proxy": [("Dry skin and light sleep", "रूखी त्वचा और हल्की नींद"), ("Heat intolerance and acidity", "गर्मी सहन न होना और अम्लता"), ("Heaviness and slow digestion", "भारीपन और धीमा पाचन")],
    "vaya": [("Under 18", "18 से कम"), ("18–40", "18–40"), ("41–60", "41–60"), ("Over 60", "60 से अधिक")],
}

def choices(field: str, hindi: bool = False) -> list[str]:
    return [pair[1 if hindi else 0] for pair in OPTIONS.get(field, [("Not sure", "पता नहीं")])]
