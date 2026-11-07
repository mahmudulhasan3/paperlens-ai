import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="PaperLens-AI")
st.title("PaperLens-AI")

# UI step 0: the login token and a notice message live in the session
if "token" not in st.session_state:
    st.session_state["token"] = None
    st.session_state["email"] = None
    st.session_state["notice"] = None

if st.session_state["notice"] is not None:
    st.warning(st.session_state["notice"])
    st.session_state["notice"] = None


# UI helper: send a request to the API with the token, and log out if the token is no longer valid
def call_api(method, path, **kwargs):
    headers = {"Authorization": "Bearer " + st.session_state["token"]}
    response = requests.request(
        method, API_URL + path, headers=headers, timeout=300, **kwargs
    )

    if response.status_code == 401:
        st.session_state["token"] = None
        st.session_state["email"] = None
        st.session_state["notice"] = "Your session expired. Please log in again."
        st.rerun()

    return response


# UI step 1: register or log in from the sidebar
st.sidebar.header("Account")

if st.session_state["token"] is None:
    choice = st.sidebar.radio("Choose", ["Log in", "Register"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button(choice):
        if choice == "Register":
            response = requests.post(
                API_URL + "/auth/register", json={"email": email, "password": password}
            )
            if response.status_code == 201:
                st.sidebar.success("Account created. Now log in.")
            else:
                st.sidebar.error(str(response.json()["detail"]))
        else:
            response = requests.post(
                API_URL + "/auth/login", data={"username": email, "password": password}
            )
            if response.status_code == 200:
                st.session_state["token"] = response.json()["access_token"]
                st.session_state["email"] = email.strip().lower()
                st.rerun()
            else:
                st.sidebar.error(str(response.json()["detail"]))

    st.info("Log in or register in the sidebar to start.")
    st.stop()

st.sidebar.write("Logged in as " + st.session_state["email"])
if st.sidebar.button("Log out"):
    st.session_state["token"] = None
    st.session_state["email"] = None
    st.rerun()

# UI step 2: upload one or many PDFs
st.header("1. Your papers")
uploaded_files = st.file_uploader(
    "Upload PDF files", type="pdf", accept_multiple_files=True
)

if len(uploaded_files) > 0 and st.button("Process PDFs"):
    for uploaded in uploaded_files:
        files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}

        with st.spinner("Processing " + uploaded.name + "..."):
            response = call_api("POST", "/upload", files=files)

        if response.status_code == 200:
            data = response.json()
            if data["duplicate"]:
                st.info(data["filename"] + " was already uploaded")
            else:
                st.success(
                    data["filename"] + " processed: " + str(data["chunks"]) + " chunks"
                )
        else:
            st.error(uploaded.name + ": " + str(response.json()["detail"]))

# UI step 3: show the papers of this user
documents_response = call_api("GET", "/documents")
documents = []
if documents_response.status_code == 200:
    documents = documents_response.json()["documents"]

if len(documents) == 0:
    st.info("You have not uploaded any paper yet.")
else:
    for doc in documents:
        st.write("- " + doc["filename"] + " (" + str(doc["chunks"]) + " chunks)")

# UI step 4: one box for everything, the router picks the mode
st.header("2. Ask, summarize, compare or extract")
st.caption(
    "Examples: 'What is citation faithfulness?', 'Summarize paper1', 'Extract the limitations of paper1', 'Compare paper1 and paper2'"
)
chat_message = st.text_input("Your message", key="chat_message")

if st.button("Send") and chat_message.strip() != "":
    with st.spinner("Working..."):
        response = call_api("POST", "/chat", json={"message": chat_message})

    if response.status_code == 200:
        data = response.json()
        st.caption("Detected mode: " + data["mode"])

        if data["needs_document"]:
            names = []
            for doc in data["documents"]:
                names.append(doc["filename"])
            st.warning(
                "Which document? Write its file name in your message. You have: "
                + ", ".join(names)
            )
        else:
            result = data["result"]
            text = ""
            if data["mode"] == "qa":
                text = result["answer"]
            elif data["mode"] == "summarize":
                text = result["summary"]
            elif data["mode"] == "compare":
                text = result["comparison"]
            else:
                text = result["extracted"]

            st.markdown(text)

            if "claims" in result and len(result["claims"]) > 0:
                with st.expander(
                    "Claim verification ("
                    + str(result["removed_claims"])
                    + " claim(s) removed)"
                ):
                    for item in result["claims"]:
                        evidence = ", ".join(item["evidence"])
                        if evidence == "":
                            evidence = "no supporting evidence"
                        st.markdown(
                            "**"
                            + item["status"]
                            + "**: "
                            + item["claim"]
                            + "  \n_Evidence: "
                            + evidence
                            + "_"
                        )

            if "citations" in result:
                for item in result["citations"]:
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
    else:
        st.error(str(response.json()["detail"]))
