ABSTAIN_TEXT = "This information could not be verified from the uploaded documents."


# Generation step (Context construction): number every chunk and keep its document, section and pages
def build_context(chunks):
    lines = []
    number = 1

    for chunk in chunks:
        meta = chunk["metadata"]
        header = "[" + str(number) + "] " + meta["filename"] + " | " + meta["section"]
        header = (
            header + " | pages " + str(meta["page_start"]) + "-" + str(meta["page_end"])
        )

        lines.append(header)
        lines.append(chunk["text"])
        lines.append("")
        number = number + 1

    return "\n".join(lines)


# Generation step (Prompt design): the instructions and the numbered sources sent to Gemini
def build_prompt(question, chunks):
    context = build_context(chunks)

    prompt = "You are a careful research assistant.\n"
    prompt = prompt + "Answer the question using ONLY the numbered sources below.\n"
    prompt = prompt + "Rules:\n"
    prompt = (
        prompt
        + "1. After every factual statement, add the source number in square brackets, for example [1].\n"
    )
    prompt = (
        prompt
        + "2. If a statement uses two sources, write them as [1][2]. Never write [1, 2].\n"
    )
    prompt = prompt + "3. Do not use any knowledge from outside the sources.\n"
    prompt = (
        prompt
        + "4. If the sources do not contain the answer, reply with exactly this sentence and nothing else: "
    )
    prompt = prompt + ABSTAIN_TEXT + "\n\n"
    prompt = prompt + "SOURCES:\n" + context + "\n"
    prompt = prompt + "QUESTION: " + question + "\n\n"
    prompt = prompt + "ANSWER:"

    return prompt
