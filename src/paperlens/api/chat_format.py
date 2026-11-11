# Chat step: turn the answer of the router into one simple message that can be saved and shown again
def make_assistant_message(data):
    message = {
        "mode": data["mode"],
        "text": "",
        "claims": [],
        "removed": 0,
        "citations": [],
    }

    if data["needs_document"]:
        names = []
        for doc in data["documents"]:
            names.append(doc["filename"])
        message["text"] = (
            "Which document? Write its file name in your message. You have: "
            + ", ".join(names)
        )
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

    return message
