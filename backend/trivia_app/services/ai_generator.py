import json
import os
from dataclasses import dataclass


GROQ_BASE_URL = 'https://api.groq.com/openai/v1'
DEFAULT_GROQ_MODEL = 'openai/gpt-oss-20b'

DIFFICULTY_GUIDANCE = {
    'easy': 'Use widely known facts and straightforward wording suitable for casual players.',
    'medium': 'Use moderately challenging facts suitable for a general audience.',
    'hard': 'Use less obvious facts and plausible distractors suitable for experienced trivia players.',
}

QUESTION_SCHEMA = {
    'name': 'trivia_question',
    'strict': True,
    'schema': {
        'type': 'object',
        'properties': {
            'prompt': {'type': 'string'},
            'choices': {
                'type': 'array',
                'items': {'type': 'string'},
                'minItems': 4,
                'maxItems': 4,
            },
            'correct_choice': {'type': 'string'},
            'explanation': {'type': 'string'},
        },
        'required': ['prompt', 'choices', 'correct_choice', 'explanation'],
        'additionalProperties': False,
    },
}


@dataclass(frozen=True)
class GeneratedQuestion:
    prompt: str
    choices: list[str]
    correct_choice: str
    explanation: str


class TriviaGenerator:
    def generate(self, topic: str, difficulty: str = 'medium') -> GeneratedQuestion:
        if difficulty not in DIFFICULTY_GUIDANCE:
            raise ValueError(f'Unsupported trivia difficulty: {difficulty}')
        if not os.getenv('GROQ_API_KEY'):
            raise RuntimeError('GROQ_API_KEY is required for AI trivia generation.')
        return self._generate_with_groq(topic, difficulty)

    def _generate_with_groq(self, topic: str, difficulty: str) -> GeneratedQuestion:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.environ['GROQ_API_KEY'],
            base_url=GROQ_BASE_URL,
        )
        prompt = (
            f'Create exactly one accurate, engaging {difficulty}-difficulty multiple-choice trivia question about {topic}. '
            f'{DIFFICULTY_GUIDANCE[difficulty]} Provide four distinct choices, identify the '
            'correct choice exactly, and briefly explain the answer. Return only the requested JSON.'
        )

        # Strict structured output should always match the schema. One retry also protects the app if
        # a provider-side model change returns content that passes the schema but fails domain checks.
        last_error = None
        for _ in range(2):
            response = client.chat.completions.create(
                model=os.getenv('GROQ_MODEL', DEFAULT_GROQ_MODEL),
                messages=[
                    {'role': 'system', 'content': 'You create accurate, family-friendly trivia questions.'},
                    {'role': 'user', 'content': prompt},
                ],
                response_format={
                    'type': 'json_schema',
                    'json_schema': QUESTION_SCHEMA,
                },
            )
            try:
                return self._parse_question(response.choices[0].message.content)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                last_error = error

        raise ValueError('Groq returned an invalid trivia question after two attempts.') from last_error

    @staticmethod
    def _parse_question(content: str) -> GeneratedQuestion:
        item = json.loads(content)
        choices = item['choices']
        text_fields = [item['prompt'], item['correct_choice'], item['explanation']]

        if (
            not isinstance(choices, list)
            or len(choices) != 4
            or not all(isinstance(choice, str) and choice.strip() for choice in choices)
            or not all(isinstance(value, str) and value.strip() for value in text_fields)
        ):
            raise ValueError('Groq returned an invalid trivia question.')

        normalized_choices = [choice.strip() for choice in choices]
        normalized_correct_choice = item['correct_choice'].strip()
        if len(set(normalized_choices)) != 4 or normalized_correct_choice not in normalized_choices:
            raise ValueError('Groq returned an invalid trivia question.')

        return GeneratedQuestion(
            prompt=item['prompt'].strip(),
            choices=normalized_choices,
            correct_choice=normalized_correct_choice,
            explanation=item['explanation'].strip(),
        )
