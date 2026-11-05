import json
import os
import time

from paperlens.ingestion.pipeline import ingest_pdf
from paperlens.generation.llm import generate_text

PDF_FOLDER = "data/golden/pdfs"
OUTPUT_FILE = "data/golden/auto_questions.json"
QUESTIONS_PER_PDF = 6
MIN_WORDS = 80


# Evaluation step 1 (Question generation): pick long enough chunks, spread across the document
def pick_chunks(chunks, how_many):
    good = []

    for chunk in chunks:
        if chunk["word_count"] < MIN_WORDS:
            continue
        if "reference" in chunk["section"].lower():
            continue
        good.append(chunk)

    if len(good) <= how_many:
        return good

    picked = []
    step = len(good) / how_many
    for i in range(how_many):
        picked.append(good[int(i * step)])

    return picked


# Evaluation step 1 (Question generation): the instructions that ask Gemini for one question
def build_question_prompt(chunk_text):
    prompt = "Read the passage below and write ONE question that can be answered using only this passage.\n"
    prompt = prompt + "Rules:\n"
    prompt = (
        prompt
        + "1. The question must make sense on its own, for a person who has not seen the passage.\n"
    )
    prompt = (
        prompt
        + "2. Never use phrases like 'the passage', 'the text' or 'this excerpt'.\n"
    )
    prompt = prompt + "3. Use specific terms from the passage, not vague words.\n"
    prompt = (
        prompt
        + "4. The answer must be one or two sentences and must come only from the passage.\n"
    )
    prompt = prompt + "Reply in exactly this format, two lines and nothing else:\n"
    prompt = prompt + "QUESTION: <the question>\n"
    prompt = prompt + "ANSWER: <the answer>\n\n"
    prompt = prompt + "PASSAGE:\n" + chunk_text

    return prompt


# Evaluation step 1 (Question generation): read the question and the answer from Gemini's reply
def parse_reply(reply):
    question = ""
    answer = ""

    for line in reply.split("\n"):
        line = line.strip()
        if line.startswith("QUESTION:"):
            question = line[len("QUESTION:") :].strip()
        if line.startswith("ANSWER:"):
            answer = line[len("ANSWER:") :].strip()

    return question, answer


# Evaluation step 1 (Question generation): build questions for every PDF in the folder and save them
def main():
    all_questions = []
    doc_number = 0

    for filename in sorted(os.listdir(PDF_FOLDER)):
        if not filename.lower().endswith(".pdf"):
            continue

        doc_number = doc_number + 1
        path = os.path.join(PDF_FOLDER, filename)

        try:
            chunks = ingest_pdf(
                path, "eval_" + str(doc_number), "eval", "eval", filename
            )
        except Exception as error:
            print("Skipped", filename, ":", error)
            continue

        picked = pick_chunks(chunks, QUESTIONS_PER_PDF)
        print(filename, ":", len(chunks), "chunks,", len(picked), "picked")

        for chunk in picked:
            try:
                result = generate_text(build_question_prompt(chunk["text"]))
            except Exception as error:
                print("LLM error:", error)
                continue

            question, answer = parse_reply(result["text"])
            if question == "" or answer == "":
                continue

            all_questions.append(
                {
                    "id": "auto_" + str(len(all_questions) + 1),
                    "question": question,
                    "expected_answer": answer,
                    "document": filename,
                    "supporting_page_start": chunk["page_start"],
                    "supporting_page_end": chunk["page_end"],
                    "supporting_evidence": chunk["text"],
                    "answerable": True,
                    "type": "auto",
                }
            )
            time.sleep(2)
    if doc_number == 0:
        print("No PDF found in", PDF_FOLDER)
        return

    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_questions, f, indent=2)

    print("Saved", len(all_questions), "questions to", OUTPUT_FILE)


if __name__ == "__main__":
    main()
