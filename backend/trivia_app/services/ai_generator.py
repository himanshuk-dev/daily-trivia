import json
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class GeneratedQuestion:
    prompt: str
    choices: list[str]
    correct_choice: str
    explanation: str


class TriviaGenerator:
    def generate(self, topic: str) -> GeneratedQuestion:
        if not os.getenv('OPENAI_API_KEY'):
            raise RuntimeError('OPENAI_API_KEY is required for AI trivia generation.')
        return self._generate_with_openai(topic)

    def _generate_with_openai(self, topic: str) -> GeneratedQuestion:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
        response = client.responses.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-5.4-nano'),
            input=(
                f'Create exactly one accurate, engaging multiple-choice trivia question about {topic}. '
                'Return only JSON with keys "prompt", "choices", "correct_choice", and "explanation". '
                '"choices" must contain four unique strings and "correct_choice" must match one choice exactly. '
                'The question should be answerable by a general audience. Do not include markdown.'
            ),
        )
        item = json.loads(response.output_text)
        choices = item['choices']
        if len(choices) != 4 or len(set(choices)) != 4 or item['correct_choice'] not in choices:
            raise ValueError('The AI returned an invalid trivia question.')
        return GeneratedQuestion(
            prompt=item['prompt'],
            choices=choices,
            correct_choice=item['correct_choice'],
            explanation=item['explanation'],
        )
