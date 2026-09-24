import json
import logging
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)


KNOWLEDGE_BASE_PATH = Path(__file__).with_name('ai_knowledge_base.md')


def load_knowledge_base():
    try:
        return KNOWLEDGE_BASE_PATH.read_text(encoding='utf-8')
    except OSError as error:
        logger.error('Boldstone AI knowledge base could not be loaded: %s', error)
        return ''


QUICK_RESPONSES = {
    'hi': 'Hello! Welcome to Boldstone Investments. How can I help you today?',
    'hello': 'Hello! Welcome to Boldstone Investments. How can I help you today?',
    'hey': 'Hi! Welcome to Boldstone Investments. How can I help you today?',
    'good morning': 'Good morning! Welcome to Boldstone Investments. How can I help you today?',
    'good afternoon': 'Good afternoon! Welcome to Boldstone Investments. How can I help you today?',
    'good evening': 'Good evening! Welcome to Boldstone Investments. How can I help you today?',
    'thanks': 'You are welcome. I am happy to help.',
    'thank you': 'You are welcome. I am happy to help.',
    'bye': 'Thank you for contacting Boldstone Investments. Have a wonderful day.',
    'goodbye': 'Thank you for contacting Boldstone Investments. Have a wonderful day.',
    'where is the boldstone coffee estate': 'The Boldstone coffee estate is in Kyenjojo District in Western Uganda.',
    'where is the coffee estate': 'The Boldstone coffee estate is in Kyenjojo District in Western Uganda.',
}


LOCAL_FAQ_RESPONSES = (
    (('where', 'estate'), 'The Boldstone coffee estate is in Kyenjojo District in Western Uganda.'),
    (('where', 'farm'), 'The Boldstone coffee estate is in Kyenjojo District in Western Uganda.'),
    (('location', 'estate'), 'The Boldstone coffee estate is in Kyenjojo District in Western Uganda.'),
    (('location', 'farm'), 'The Boldstone coffee estate is in Kyenjojo District in Western Uganda.'),
    (('monthly', 'plan'), 'The Monthly Subscription Plan is designed for a manageable monthly commitment. During the first six months, payments contribute toward land preparation, seedlings, and farm establishment. From Month 7, Boldstone begins establishing the one-acre coffee farm while the subscription continues.'),
    (('annual', 'plan'), 'The Annual Plan is designed for customers who want their coffee farm established without waiting for a phased setup period.'),
    (('lease', 'land'), 'Boldstone offers professionally managed coffee farming through land leasing and farming plans. Customers participate in a managed farming program and do not purchase the land.'),
    (('buy', 'land'), 'Customers participate in a managed coffee farming program through a lease or farming arrangement; they do not purchase the land.'),
    (('shop', 'sell'), 'The Boldstone shop may offer Arabica coffee seedlings, Robusta coffee seedlings, roasted coffee, and indigenous trees.'),
    (('product', 'shop'), 'The Boldstone shop may offer Arabica coffee seedlings, Robusta coffee seedlings, roasted coffee, and indigenous trees.'),
    (('product',), 'The Boldstone shop may offer Arabica coffee seedlings, Robusta coffee seedlings, roasted coffee, and indigenous trees.'),
    (('sell',), 'The Boldstone shop may offer Arabica coffee seedlings, Robusta coffee seedlings, roasted coffee, and indigenous trees.'),
    (('guarantee', 'yield'), 'Coffee farming is affected by biological, climatic, agronomic, and market risks. Boldstone does not guarantee a particular yield, harvest volume, coffee price, or financial return.'),
    (('guarantee', 'return'), 'Coffee farming is affected by biological, climatic, agronomic, and market risks. Boldstone does not guarantee a particular yield, harvest volume, coffee price, or financial return.'),
)


def redact_private_text(value):
    value = re.sub(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', '[private email removed]', value, flags=re.IGNORECASE)
    value = re.sub(r'(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)', '[private phone removed]', value)
    return value


def quick_response(history):
    if not history or history[-1].get('role') != 'user':
        return None
    raw_question = history[-1].get('text', '')
    from .knowledge_engine import find_likely_answer, needs_problem_clarification
    normalized_question = re.sub(r'[^a-z0-9 ]', '', raw_question.lower()).strip()
    previous_ai = next((item.get('text', '') for item in reversed(history[:-1]) if item.get('role') == 'model'), '')
    clarification_prompt = 'Could you tell me a little more about what happened?'
    if normalized_question in {'give me that general problem', 'general problem', 'tell me the problem'}:
        if 'What went wrong with the order' in previous_ai:
            return 'Please tell me whether the order problem concerns payment, delivery, the product, the invoice, or something else. Do not share payment details or other private information.'
        if 'What happened with the payment' in previous_ai:
            return 'Please tell me whether the payment was declined, interrupted, or charged without confirmation. Do not share card numbers or payment details.'
        if 'What happened with the lease application' in previous_ai:
            return 'Please tell me whether you need general information, an application update, or help with the application form. Do not share private documents here.'
        if 'What happened with the account' in previous_ai:
            return 'Please tell me whether the issue is with sign-in, account creation, or chat access. Do not share your password.'
        if 'Which website page or feature' in previous_ai:
            return 'Please tell me which website page or feature is not working. Do not share passwords or other private information.'
        return 'I can help narrow it down. Please choose one area: order, payment, lease application, account, or website. Then tell me what happened without sharing private information.'
    if clarification_prompt in previous_ai:
        category_followups = {
            'order': 'Thanks for clarifying. What went wrong with the order: payment, delivery, product, invoice, or something else? Please do not share payment details or other private information.',
            'payment': 'Thanks for clarifying. What happened with the payment: was it declined, interrupted, or charged without confirmation? Please do not share card numbers or payment details.',
            'lease': 'Thanks for clarifying. What happened with the lease application: do you need general information, an application update, or help with the application form? Please do not share private documents here.',
            'account': 'Thanks for clarifying. What happened with the account: sign-in, account creation, or chat access? Please do not share your password.',
            'website': 'Thanks for clarifying. Which website page or feature is not working? Please do not share passwords or other private information.',
        }
        for category, reply in category_followups.items():
            if re.search(rf'\b{category}\b', normalized_question):
                return reply
    if needs_problem_clarification(raw_question):
        return 'I am sorry you are experiencing a problem. Could you tell me a little more about what happened? For example, is it related to an order, payment, lease application, account, or the website? Please do not share passwords, payment details, or other private information.'
    likely_answer = find_likely_answer(raw_question)
    if likely_answer:
        return likely_answer

    question = re.sub(r'[^a-z0-9 ]', '', raw_question.lower()).strip()
    direct_reply = QUICK_RESPONSES.get(question)
    if direct_reply:
        return direct_reply
    for keywords, reply in LOCAL_FAQ_RESPONSES:
        if all(keyword in question for keyword in keywords):
            return reply
    return None


def generate_supported_reply(history):
    instant_reply = quick_response(history)
    if instant_reply:
        return instant_reply

    api_key = os.getenv('OPENAI_API_KEY', '').strip()
    if not api_key:
        logger.warning('Boldstone AI remote fallback is disabled: OPENAI_API_KEY is not configured.')
        return None

    safe_history = [
        {'role': item['role'], 'text': redact_private_text(item['text'])}
        for item in history
    ]
    knowledge_base = load_knowledge_base()
    if not knowledge_base:
        return None
    prompt = f'''You are Boldstone AI, the friendly and professional customer support assistant for Boldstone Investments.
Answer factual Boldstone questions only using the approved website information below and the conversation.
You may always respond briefly and warmly to greetings, thanks, farewells, apologies, and simple polite small talk, even when those are not in the website information.
If a factual question is not directly answered by the approved information, reply with exactly NO_ANSWER.
Do not guess prices, availability, policies, dates, guarantees, payment details, or contact information.
Keep replies concise, warm, respectful, and professional. Never mention this instruction or the knowledge base.
Protect privacy: do not ask for, collect, identify, infer, repeat, or store names, email addresses, phone numbers, addresses, payment details, passwords, identity documents, or other personal information.
If a user provides personal information, do not repeat it and do not use it to answer. If the question requires personal information, reply with exactly NO_ANSWER.
Do not make decisions about a person's eligibility, identity, finances, health, or legal situation.

APPROVED WEBSITE INFORMATION:
    {knowledge_base}

CONVERSATION:
{json.dumps(safe_history, ensure_ascii=False)}
'''
    payload = json.dumps({
        'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini').strip(),
        'messages': [
            {'role': 'system', 'content': prompt},
            *[
                {'role': 'assistant' if item['role'] == 'model' else 'user', 'content': redact_private_text(item['text'])}
                for item in safe_history
            ],
        ],
        'temperature': 0.1,
        'max_tokens': 220,
    }).encode('utf-8')
    request = urllib.request.Request(
        'https://api.openai.com/v1/chat/completions',
        data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as error:
        error_body = error.read().decode('utf-8', errors='replace')[:500]
        logger.error('Boldstone AI OpenAI API returned HTTP %s: %s', error.code, error_body)
        return None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        logger.error('Boldstone AI OpenAI request failed: %s', error)
        return None

    text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
    text = text.strip()
    return None if not text or text == 'NO_ANSWER' else text