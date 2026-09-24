import json
import re
from difflib import SequenceMatcher
from pathlib import Path


FAQ_PATH = Path(__file__).with_name('ai_faq.json')
STOP_WORDS = {
    'a', 'an', 'and', 'are', 'can', 'do', 'does', 'for', 'how', 'i', 'is',
    'it', 'me', 'my', 'of', 'on', 'please', 'tell', 'the', 'there', 'to',
    'what', 'where', 'which', 'who', 'with', 'you', 'your',
}
SPELLING_CORRECTIONS = {
    'subscrption': 'subscription',
    'subcription': 'subscription',
    'subscripton': 'subscription',
    'locaton': 'location',
    'locatd': 'located',
    'prodct': 'product',
    'prodcts': 'products',
    'seedlingg': 'seedling',
    'agronmy': 'agronomy',
    'sustainble': 'sustainable',
    'sustianable': 'sustainable',
    'partnr': 'partner',
    'influener': 'influencer',
    'represenative': 'representative',
    'guarentee': 'guarantee',
    'guarante': 'guarantee',
    'harvst': 'harvest',
    'paymant': 'payment',
    'paymet': 'payment',
}
PROBLEM_WORDS = {'problem', 'issue', 'error', 'failed', 'failure', 'help', 'complaint'}
SPECIFIC_PROBLEM_WORDS = {
    'order', 'payment', 'lease', 'application', 'account', 'login', 'sign',
    'chat', 'website', 'subscription', 'invoice', 'delivery', 'password',
}


def normalize_question(question):
    words = re.findall(r'[a-z0-9]+', question.lower())
    return [SPELLING_CORRECTIONS.get(word, word) for word in words if word not in STOP_WORDS]


def load_faq():
    try:
        return json.loads(FAQ_PATH.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return []


def break_down_question(question, faq=None):
    faq = faq if faq is not None else load_faq()
    words = normalize_question(question)
    keyword_set = {keyword for entry in faq for keyword in entry.get('keywords', [])}
    understood_words = []
    for word in words:
        if word in keyword_set:
            understood_words.append(word)
            continue
        closest = max(keyword_set, key=lambda keyword: SequenceMatcher(None, word, keyword).ratio(), default='')
        if closest and SequenceMatcher(None, word, closest).ratio() >= 0.82:
            understood_words.append(closest)
    return {
        'original': question,
        'words': words,
        'understood_words': understood_words,
    }


def needs_problem_clarification(question):
    words = set(normalize_question(question))
    return bool(words & PROBLEM_WORDS) and not bool(words & SPECIFIC_PROBLEM_WORDS)


def find_likely_answer(question, minimum_score=0.4):
    faq = load_faq()
    analysis = break_down_question(question, faq)
    question_words = set(analysis['understood_words'])
    if not question_words:
        return None

    best_match = None
    best_score = 0
    for entry in faq:
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
