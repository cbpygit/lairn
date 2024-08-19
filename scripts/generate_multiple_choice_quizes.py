import asyncio
import json
import os
from pathlib import Path

import openai
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, validator
from langchain_openai import ChatOpenAI

from lairn.config import MAIN_DIR, LLM
from lairn.curriculum.load import load_curricula
from lairn.learn_artifact import load_evaluations

PT_GENERATE_MULTIPLE_CHOICE = PromptTemplate(
    template="""
    |SYSTEM|

    # Experte für spannende, anregende Prüfungsaufgaben für die Grundschule

    Mein Sohn ist 7 und würde nun in die zweite Klasse der Grundschule in 
    Deutschland kommen. Er wird zu Hause unterrichtet. Du erhältst eine 
    Auflistung der Lernziele des Lehrplans für {subject}, sowie die Beurteilung
    seiner Klassenlehrerin für dieses Fach vom Ende der ersten Klasse.
    
    Generiere {num_questions} Multiple-Choice-Fragen, die auf dem Lehrplan
    basieren und die Lernziele des Lehrplans abdecken. Sei kreativ und verwende
    zum Beispiel Bilder aus der Welt von Super Mario. Beziehe die Beurteilung
    seiner Lehrerin mit ein, um seine eventuellen Stärken und Schwächen zu 
    berücksichtigen. 
    
    |USER|
    
    ## Lernziele des Lehrplans für {subject}
    
    {curriculum}
    
    ## Beurteilung der Lehrerin aus dem Abschlusszeugnis der ersten Klasse
    
    {evaluation}

    ## Response format
    
      - Genau 4 Antwortmöglichkeiten pro Frage
      - Genau eine Antwortmöglichkeit ist korrekt

    {response_format}

    ## Antwort Sprache

    Deutsch

""",
    input_variables=[
        "subject",
        "num_questions",
        "curriculum",
        "evaluation",
        "response_format",
        "response_language",
    ],
)


class MultipleChoiceQuizQuestion(BaseModel):
    question: str
    answers: list[str] = Field(description="The possible answers to the question")
    answer_key: int = Field(description="The index of the correct answer in the answers list")

    @validator("answers")
    def check_answers_length(cls, v):
        if len(v) != 4:
            raise ValueError("There must be exactly 4 answers")
        return v

    @validator("answer_key")
    def check_answer_key(cls, v, values):
        if "answers" in values and (v < 0 or v >= len(values["answers"])):
            raise ValueError("answer_key must be a valid index in answers")
        return v

    def str_fmt(self) -> str:
        formatted_answers = []
        for i, answer in enumerate(self.answers):
            if i == self.answer_key:
                formatted_answers.append(f"*{answer}*")
            else:
                formatted_answers.append(answer)

        formatted_answers_str = "\n  - ".join(formatted_answers)
        return f"## {self.question}\n  - {formatted_answers_str}"


class MultipleChoiceQuiz(BaseModel):
    subject: str = Field(description="The school subject the quiz is for")
    questions: list[MultipleChoiceQuizQuestion] = Field(description="The multiple choice quiz questions")
    num_questions: int = Field(description="The number of questions in the quiz")

    @validator("questions")
    def check_num_questions(cls, v, values):
        if "num_questions" in values and len(v) != values["num_questions"]:
            raise ValueError("The number of questions must match num_questions")
        return v

    def str_fmt(self) -> str:
        formatted_questions = [question.str_fmt() for question in self.questions]
        return f"# {self.subject}\n\n" + "\n\n".join(formatted_questions)


async def generate_multiple_choice_question(
    model: ChatOpenAI, subject: str, curriculum: str, evaluation: str, num_questions: int
) -> MultipleChoiceQuiz:
    parser = PydanticOutputParser(pydantic_object=MultipleChoiceQuiz)

    chain = PT_GENERATE_MULTIPLE_CHOICE | model | parser

    questions = await chain.ainvoke(
        {
            "subject": subject,
            "num_questions": num_questions,
            "curriculum": curriculum,
            "evaluation": evaluation,
            "response_format": parser.get_format_instructions(),
            "response_language": "Deutsch",
        }
    )

    return questions


def get_out_path(subject: str) -> Path:
    return (
        MAIN_DIR
        / "Schullehrplan_Grundschule_Zusammenfassungen"
        / "Schuljahre 1-2"
        / "Starter Quizze"
        / f"{subject}.md"
    )


async def main(num_questions: int = 10):
    curricula_path = MAIN_DIR / "Schullehrplan_Grundschule_Zusammenfassungen" / "Schuljahre 1-2" / "pydantic"
    curricula = load_curricula(curricula_path)

    evaluations_path = MAIN_DIR / "artifacts"
    evaluations = load_evaluations(evaluations_path)

    model_name = LLM
    model = ChatOpenAI(model_name=model_name, temperature=0.0)

    tasks = []
    for subject, curriculum in curricula.items():
        evaluation = evaluations[subject]

        out_path = get_out_path(subject)
        if os.path.isfile(out_path):
            continue

        task = generate_multiple_choice_question(
            model, subject, curriculum.str_format(), evaluation, num_questions
        )
        tasks.append(task)

    quizzes = await asyncio.gather(*tasks)

    for quiz in quizzes:
        md = quiz.str_fmt()
        out_path = get_out_path(quiz.subject)
        with open(out_path, "w") as f:
            f.write(md)


async def main_safe():
    """Same as main, but waits 5seconds and retries in case of
    openai.RateLimitError"""
    while True:
        try:
            await main()
            break
        except openai.RateLimitError:
            print("Rate limit error, waiting 5 seconds")
            await asyncio.sleep(5)


# Run the main function using asyncio
if __name__ == "__main__":
    asyncio.run(main_safe())
