import uuid

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.title("PaperLens-AI")

# UI step 0: every browser session gets its own temporary guest id
if "owner_id" not in st.session_state:
    st.session_state["owner_id"] = "guest_" + uuid.uuid4().hex[:12]
owner_id = st.session_state["owner_id"]

# UI step 1: upload one or many PDFs and send each one to the API
st.header("1. Upload papers")
uploaded_files = st.file_uploader(
    "Choose PDF files", type="pdf", accept_multiple_files=True
)

if len(uploaded_files) > 0 and st.button("Process PDFs"):
    for uploaded in uploaded_files:
        files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}

        with st.spinner("Processing " + uploaded.name + "..."):
            response = requests.post(
                API_URL + "/upload", data={"owner_id": owner_id}, files=files
            )

        if response.status_code == 200:
            data = response.json()
            if data["duplicate"]:
                st.info(data["filename"] + " was already uploaded in this session")
            else:
                st.success(
                    data["filename"] + " processed: " + str(data["chunks"]) + " chunks"
                )
        else:
            st.error(uploaded.name + ": " + response.json()["detail"])

# UI step 2: ask a question, then either see the evidence chunks or get the baseline answer
st.header("2. Ask a question")
question = st.text_input("Your question")

col1, col2 = st.columns(2)
show_chunks = col1.button("Show evidence chunks")
get_answer = col2.button("Get answer (baseline RAG)")

if show_chunks and question.strip() != "":
    response = requests.post(
        API_URL + "/ask",
        json={"owner_id": owner_id, "question": question},
    )

    if response.status_code == 200:
        for item in response.json()["results"]:
            st.markdown(
                "**"
                + item["filename"]
                + "** | "
                + item["section"]
                + " | pages "
                + str(item["page_start"])
                + "-"
                + str(item["page_end"])
            )
            st.write(item["text"])
            st.divider()
    else:
        st.error(response.json()["detail"])

if get_answer and question.strip() != "":
    with st.spinner("Thinking..."):
        response = requests.post(
            API_URL + "/answer",
            json={"owner_id": owner_id, "question": question},
        )

    if response.status_code == 200:
        data = response.json()
        st.subheader("Answer")
        st.write(data["answer"])

        if data["abstained"]:
            st.warning("The system abstained: not enough evidence in your documents.")

        for item in data["citations"]:
            label = (
                "["
                + str(item["number"])
                + "] "
                + item["filename"]
                + " | "
                + item["section"]
            )
            label = (
                label
                + " | pages "
                + str(item["page_start"])
                + "-"
                + str(item["page_end"])
            )
            with st.expander(label):
                st.write(item["text"])

        st.caption(
            "Tokens: "
            + str(data["prompt_tokens"])
            + " in, "
            + str(data["output_tokens"])
            + " out | Latency: "
            + str(data["latency"])
            + " s"
        )
    else:
        st.error(response.json()["detail"])


# UI step 3: choose one of your documents and summarize it
st.header("3. Summarize a document")

documents = []
docs_response = requests.get(API_URL + "/documents", params={"owner_id": owner_id})
if docs_response.status_code == 200:
    documents = docs_response.json()["documents"]

if len(documents) == 0:
    st.info("Upload a PDF to summarize it")
else:
    names = []
    for doc in documents:
        names.append(doc["filename"])

    chosen = st.selectbox("Choose a document", names)

    if st.button("Summarize"):
        chosen_id = ""
        for doc in documents:
            if doc["filename"] == chosen:
                chosen_id = doc["doc_id"]

        with st.spinner("Summarizing (about one minute)..."):
            response = requests.post(
                API_URL + "/summarize",
                json={"owner_id": owner_id, "doc_id": chosen_id},
            )

        if response.status_code == 200:
            data = response.json()
            st.markdown(data["summary"])
            st.caption(
                "Tokens: "
                + str(data["total_tokens"])
                + " | Time: "
                + str(data["total_latency"])
                + " s"
            )
        else:
            st.error(response.json()["detail"])




# UI step 4: choose two or more documents and compare them
st.header("4. Compare documents")

if len(documents) < 2:
    st.info("Upload at least two PDFs to compare them")
else:
    labels = []
    for doc in documents:
        labels.append(doc["filename"] + " (" + doc["doc_id"] + ")")

    chosen_labels = st.multiselect("Choose two or more documents", labels)

    if st.button("Compare"):
        if len(chosen_labels) < 2:
            st.warning("Choose at least two documents")
        else:
            chosen_ids = []
            for i in range(len(labels)):
                if labels[i] in chosen_labels:
                    chosen_ids.append(documents[i]["doc_id"])

            with st.spinner("Comparing..."):
                response = requests.post(
                    API_URL + "/compare",
                    json={"owner_id": owner_id, "doc_ids": chosen_ids},
                )

            if response.status_code == 200:
                data = response.json()
                st.markdown(data["comparison"])

                for item in data["citations"]:
                    label = "[" + str(item["number"]) + "] " + item["filename"] + " | " + item["section"]
                    label = label + " | pages " + str(item["page_start"]) + "-" + str(item["page_end"])
                    with st.expander(label):
                        st.write(item["text"])

                st.caption("Tokens: " + str(data["prompt_tokens"]) + " in, "
                           + str(data["output_tokens"]) + " out | Latency: " + str(data["latency"]) + " s")
            else:
                st.error(response.json()["detail"])