from paperlens.modes.router import MAX_COMPARE


# Chat step: turn the answer of the router into one simple message that can be saved and shown again
def make_assistant_message(data):
    message = {
        "mode": data["mode"],
        "text": "",
        "claims": [],
        "removed": 0,
        "citations": [],
        "used": [],
        "choices": [],
    }

    if data["needs_document"]:
        if data["mode"] == "compare":
            message["text"] = (
                "You have more than "
                + str(MAX_COMPARE)
                + " papers. Name the papers to compare, "
                "for example: Compare paper1.pdf and paper2.pdf."
            )
        else:
            message["text"] = "Which paper do you mean? Choose one below."
            for doc in data["documents"]:
                message["choices"].append(doc["filename"])
        return message

    result = data["result"]

    if data["mode"] == "qa":
        message["text"] = result["answer"]
    elif data["mode"] == "summarize":
        message["text"] = result["summary"]
    elif data["mode"] == "compare":
        message["text"] = result["comparison"]
    else:
        message["text"] = result["extracted"]

    if "claims" in result:
        message["claims"] = result["claims"]
        message["removed"] = result["removed_claims"]
    if "citations" in result:
        message["citations"] = result["citations"]

    message["used"] = result.get("used_documents", [])

    return message
