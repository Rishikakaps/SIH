FIELD_LABELS = {
    "chief_complaint": "What problem brought you to the hospital today?",
    "onset": "When did this problem start?",
    "location": "Where do you feel it most?",
    "character": "What does the symptom feel like?",
    "radiation": "Does the pain move to your arm, jaw, back, or anywhere else?",
    "severity": "How severe is it from 0 to 10?",
    "duration": "How long does each episode last?",
    "aggravating_factors": "What makes it worse?",
    "relieving_factors": "What makes it better?",
    "associated_symptoms": "Do you have breathlessness, sweating, fainting, vomiting, weakness, or other symptoms?",
    "past_history": "Have you had diabetes, blood pressure, surgery, hospital admission, or similar illness before?",
    "medications": "Are you taking any regular medicines?",
    "allergies": "Do you have any medicine or food allergies?",
    "family_history": "Does anyone in your family have similar illness, diabetes, blood pressure, heart disease, or stroke?",
    "personal_history": "Please tell us about sleep, appetite, tobacco, alcohol, and daily activity.",
    "ros": "Is there any other body system symptom you want the doctor to know?",
    "prakriti_proxy": "Which body tendency describes you best most of the time?",
    "satmya": "Which foods, weather, or routines usually suit you?",
    "sattva": "How do stress, sleep, and emotions affect your symptoms?",
    "ahara_shakti": "How is your appetite and digestion?",
    "vyayama_shakti": "How much exercise can you comfortably do?",
    "vaya": "Please confirm your age group.",
    "ahara_vihara": "Which diet or lifestyle factors seem related to your symptoms?",
    "nidana": "What do you think triggered or worsened this illness?",
}

PATHWAYS = {
    "chest pain": ["onset", "location", "character", "radiation", "severity", "duration", "aggravating_factors", "relieving_factors", "associated_symptoms"],
    "fever": ["onset", "duration", "associated_symptoms", "aggravating_factors", "relieving_factors"],
    "abdominal pain": ["onset", "location", "character", "severity", "associated_symptoms"],
    "headache": ["onset", "location", "character", "severity", "associated_symptoms"],
}

AYUSH_PENDING_PHYSICIAN_FIELDS = [
    "Nadi",
    "Jihva",
    "Mutra",
    "Mala",
    "Drik",
    "Akriti",
    "Darshana",
    "Sparshana",
    "Vikriti",
    "Sara",
    "Samhanana",
    "Pramana",
]


def base_pathway() -> list[str]:
    return ["chief_complaint", "past_history", "medications", "allergies", "family_history", "personal_history", "ros"]


def ayush_pathway() -> list[str]:
    return ["chief_complaint", "prakriti_proxy", "satmya", "sattva", "ahara_shakti", "vyayama_shakti", "vaya", "ahara_vihara", "nidana", "medications", "allergies"]
