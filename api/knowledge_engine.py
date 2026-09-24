import json
import re
from pathlib import Path


FAQ_PATH = Path(__file__).with_name('ai_faq.json')
STOP_WORDS = {
    'a', 'an', 'and', 'are', 'can', 'do', 'does', 'for', 'how', 'i', 'is',
    'it', 'me', 'my', 'of', 'on', 'please', 'tell', 'the', 'there', 'to',
    'what', 'where', 'which', 'who', 'with', 'you', 'your',
}


def normalize_question(question):
    words = re.findall(r'[a-z0-9]+', question.lower())
    return [word for word in words if word not in STOP_WORDS]


def load_faq():
    try:
        return json.loads(FAQ_PATH.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return []


def find_likely_answer(question, minimum_score=0.4):
    question_words = set(normalize_question(question))
    if not question_words:
        return None

    best_match = None
    best_score = 0
    for entry in load_faq():
        keywords = set(entry.get('keywords', []))
        matched_words = question_words & keywords
        if not matched_words:
            continue
        score = len(matched_words) / max(len(question_words), 1)
        if score > best_score:
            best_score = score
            best_match = entry

    if best_match is None or best_score < minimum_score:
        return None
    return best_match['answer']
