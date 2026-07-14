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
    def generate(self, topic: str, question_count: int = 5) -> list[GeneratedQuestion]:
        if os.getenv('OPENAI_API_KEY'):
            return self._generate_with_openai(topic, question_count)
        return self._generate_local(topic, question_count)

    def _generate_with_openai(self, topic: str, question_count: int) -> list[GeneratedQuestion]:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
        response = client.responses.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-5.4-nano'),
            input=(
                f'Create exactly {question_count} accurate multiple-choice trivia questions about {topic}. '
                'Return only JSON with a top-level "questions" array. Each item must contain '
                '"prompt", four unique strings in "choices", "correct_choice" matching one choice exactly, '
                'and a concise "explanation". Do not include markdown.'
            ),
        )
        payload = json.loads(response.output_text)
        questions = []
        for item in payload.get('questions', []):
            choices = item['choices']
            if len(choices) != 4 or item['correct_choice'] not in choices:
                raise ValueError('The AI returned an invalid trivia question.')
            questions.append(GeneratedQuestion(
                prompt=item['prompt'],
                choices=choices,
                correct_choice=item['correct_choice'],
                explanation=item['explanation'],
            ))
        if len(questions) != question_count:
            raise ValueError('The AI returned an unexpected number of questions.')
        return questions

    def _generate_local(self, topic: str, question_count: int) -> list[GeneratedQuestion]:
        questions: list[GeneratedQuestion] = []

        for index in range(question_count):
            questions.append(
                GeneratedQuestion(
                    prompt=f'Question {index + 1} about {topic}: which option best fits?',
                    choices=[f'{topic} option A', f'{topic} option B', f'{topic} option C', f'{topic} option D'],
                    correct_choice=f'{topic} option A',
                    explanation=f'This is the draft explanation for {topic}.',
                )
            )

        return questions
