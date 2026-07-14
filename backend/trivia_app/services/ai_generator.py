from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedQuestion:
    prompt: str
    choices: list[str]
    correct_choice: str
    explanation: str


class TriviaGenerator:
    def generate(self, topic: str, question_count: int = 5) -> list[GeneratedQuestion]:
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
