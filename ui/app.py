import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="PaperLens-AI", layout="centered", initial_sidebar_state="expanded"
)

# UI step 0: the look of the page (a clean chat layout, a light sidebar, rounded message box)
STYLE = """
<style>
#MainMenu, footer, [data-testid="stToolbar"] {display: none;}
.block-container {max-width: 760px; padding-top: 2rem; padding-bottom: 7rem;}
section[data-testid="stSidebar"] {background: #f7f7f8;}
section[data-testid="stSidebar"] .stButton button {width: 100%; justify-content: flex-start; text-align: left;}
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {border: none; background: transparent;}
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {background: #ececf1;}
[data-testid="stChatInput"] {border-radius: 26px;}
[data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] {display: none;}
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: #f4f4f4; border-radius: 20px; width: fit-content; max-width: 85%;
    margin-left: auto; padding: 0.6rem 1rem;
}
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {background: transparent;}
</style>
"""
st.markdown(STYLE, unsafe_allow_html=True)

# UI step 0: everything that must survive a rerun lives in the session
DEFAULTS = {
    "token": None,
    "email": None,
    "is_guest": False,
    "notice": None,
    "messages": [],
    "chat_id": None,
    "pending": None,
}
for key in DEFAULTS:
    if key not in st.session_state:
        st.session_state[key] = DEFAULTS[key]


# UI helper: forget the login or guest session and everything shown on the screen
def clear_session():
    st.session_state["token"] = None
    st.session_state["email"] = None
    st.session_state["is_guest"] = False
    st.session_state["messages"] = []
    st.session_state["chat_id"] = None
    st.session_state["pending"] = None


# UI helper: send a request to the API with the token, and start over if the token is no longer valid
def call_api(method, path, **kwargs):
    headers = {"Authorization": "Bearer " + st.session_state["token"]}
    response = requests.request(
        method, API_URL + path, headers=headers, timeout=300, **kwargs
    )

    if response.status_code == 401:
        clear_session()
        st.session_state["notice"] = "Your session expired. Please start again."
        st.rerun()

    return response


# UI helper: build one assistant message with every field the screen needs
def make_message(data, mode=None):
    message = {
        "role": "assistant",
        "mode": "qa",
        "text": "",
        "claims": [],
        "removed": 0,
        "citations": [],
    }

    if data is not None:
        for key in ["mode", "text", "claims", "removed", "citations"]:
            if key in data:
                message[key] = data[key]

    if mode is not None:
        message["mode"] = mode

    return message


# UI helper: draw one assistant message with its claim table and citations
def show_assistant_message(message):
    if message["mode"] not in ["error", "notice"]:
        st.caption("Mode: " + message["mode"])

    st.markdown(message["text"])

    if len(message["claims"]) > 0:
        with st.expander(
            "Claim verification (" + str(message["removed"]) + " claim(s) removed)"
        ):
            for item in message["claims"]:
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

    for item in message["citations"]:
        label = (
            "["
            + str(item["number"])
            + "] "
            + item["filename"]
            + " | "
            + item["section"]
        )
        label = (
            label + " | pages " + str(item["page_start"]) + "-" + str(item["page_end"])
        )
        with st.expander(label):
            st.write(item["text"])


# UI helper: open a saved chat of a registered user
def load_chat(chat_id):
    response = call_api("GET", "/chats/" + str(chat_id))

    if response.status_code != 200:
        st.session_state["notice"] = "Could not open this chat."
        st.rerun()

    messages = []
    for row in response.json()["messages"]:
        if row["role"] == "user":
            messages.append({"role": "user", "content": row["content"]})
        else:
            messages.append(
                make_message(
                    row["data"] if row["data"] is not None else {"text": row["content"]}
                )
            )

    st.session_state["messages"] = messages
    st.session_state["chat_id"] = chat_id
    st.rerun()


# UI helper: delete a saved chat of a registered user
def delete_chat(chat_id):
    call_api("DELETE", "/chats/" + str(chat_id))

    if st.session_state["chat_id"] == chat_id:
        st.session_state["messages"] = []
        st.session_state["chat_id"] = None

    st.rerun()


# UI step 1: the welcome screen with login, registration and guest access
if st.session_state["token"] is None:
    st.markdown(
        "<h1 style='text-align: center;'>PaperLens-AI</h1>", unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align: center; color: #6e6e80;'>Ask questions about your research papers. "
        "Every answer is checked against the evidence.</p>",
        unsafe_allow_html=True,
    )

    if st.session_state["notice"] is not None:
        st.warning(st.session_state["notice"])
        st.session_state["notice"] = None

    tab_login, tab_register = st.tabs(["Log in", "Register"])

    with tab_login:
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input(
            "Password", type="password", key="login_password"
        )

        if st.button("Log in", type="primary"):
            response = requests.post(
                API_URL + "/auth/login",
                data={"username": login_email, "password": login_password},
            )
            if response.status_code == 200:
                clear_session()
                st.session_state["token"] = response.json()["access_token"]
                st.session_state["email"] = login_email.strip().lower()
                st.rerun()
            else:
                st.error(str(response.json()["detail"]))

    with tab_register:
        register_email = st.text_input("Email", key="register_email")
        register_password = st.text_input(
            "Password (at least 8 characters)", type="password", key="register_password"
        )

        if st.button("Create account", type="primary"):
            response = requests.post(
                API_URL + "/auth/register",
                json={"email": register_email, "password": register_password},
            )
            if response.status_code == 201:
                st.success("Account created. Now log in.")
            else:
                st.error(str(response.json()["detail"]))

    st.divider()
    if st.button("Continue as guest"):
        response = requests.post(API_URL + "/auth/guest")
        if response.status_code == 200:
            clear_session()
            st.session_state["token"] = response.json()["access_token"]
            st.session_state["is_guest"] = True
            st.rerun()
        else:
            st.error("Could not start a guest session")
    st.caption(
        "Guest papers and chats disappear when you close the page. Create an account to keep them."
    )
    st.stop()

# UI step 2: the sidebar with new chat, saved chats, your papers and the account
documents = []
documents_response = call_api("GET", "/documents")
if documents_response.status_code == 200:
    documents = documents_response.json()["documents"]

with st.sidebar:
    st.markdown("### PaperLens-AI")

    if st.button("+ New chat", type="primary"):
        st.session_state["messages"] = []
        st.session_state["chat_id"] = None
        st.rerun()

    if st.session_state["is_guest"]:
        st.caption(
            "Guest mode: your papers and chat are temporary. They disappear when you close this page."
        )
    else:
        st.markdown("**Chats**")
        chats = []
        chats_response = call_api("GET", "/chats")
        if chats_response.status_code == 200:
            chats = chats_response.json()["chats"]

        if len(chats) == 0:
            st.caption("No saved chats yet")

        for chat in chats:
            col_open, col_delete = st.columns([5, 1])
            label = chat["title"][:28]
            if chat["id"] == st.session_state["chat_id"]:
                label = "● " + label

            if col_open.button(label, key="open_" + str(chat["id"])):
                load_chat(chat["id"])
            if col_delete.button("×", key="delete_" + str(chat["id"])):
                delete_chat(chat["id"])

    st.divider()
    st.markdown("**Your papers**")
    if len(documents) == 0:
        st.caption("No papers yet. Use the + in the message box to attach PDFs.")
    for doc in documents:
        st.caption("• " + doc["filename"])

    st.divider()
    if st.session_state["is_guest"]:
        st.caption("Guest session")
    else:
        st.caption(st.session_state["email"])

    if st.button("End guest session" if st.session_state["is_guest"] else "Log out"):
        clear_session()
        st.rerun()

# UI step 3: the message box (it is pinned to the bottom) and what the user sent
prompt = st.chat_input(
    "Ask about your papers, or attach PDFs", accept_file="multiple", file_type=["pdf"]
)

incoming_text = ""
incoming_files = []
if prompt:
    incoming_text = (prompt.text or "").strip()
    incoming_files = prompt.files

if st.session_state["pending"] is not None:
    incoming_text = st.session_state["pending"]
    st.session_state["pending"] = None

has_input = incoming_text != "" or len(incoming_files) > 0

# UI step 4: the welcome text and the suggestions on an empty chat
if len(st.session_state["messages"]) == 0 and not has_input:
    st.markdown(
        "<h2 style='text-align: center; margin-top: 3rem;'>What would you like to know about your papers?</h2>",
        unsafe_allow_html=True,
    )

    if len(documents) == 0:
        st.markdown(
            "<p style='text-align: center; color: #6e6e80;'></p>",
            unsafe_allow_html=True,
        )
    else:
        name = documents[0]["filename"]
        if name.lower().endswith(".pdf"):
            name = name[:-4]

        suggestions = [
            "Summarize " + name,
            "Extract the limitations of " + name,
            "What is the main idea of " + name + "?",
        ]

        columns = st.columns(3)
        for i in range(3):
            if columns[i].button(suggestions[i], key="suggestion_" + str(i)):
                st.session_state["pending"] = suggestions[i]
                st.rerun()

# UI step 5: upload the attached PDFs, one after another
for uploaded in incoming_files:
    files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}

    with st.spinner("Processing " + uploaded.name + "..."):
        response = call_api("POST", "/upload", files=files)

    if response.status_code == 200:
        data = response.json()
        if data["duplicate"]:
            text = data["filename"] + " was already added."
        else:
            text = (
                "Added "
                + data["filename"]
                + " ("
                + str(data["chunks"])
                + " chunks). You can ask about it now."
            )
        notice = make_message({"text": text}, mode="notice")
    else:
        notice = make_message(
            {"text": uploaded.name + ": " + str(response.json()["detail"])},
            mode="error",
        )

    st.session_state["messages"].append(notice)

if incoming_text != "":
    st.session_state["messages"].append({"role": "user", "content": incoming_text})

# UI step 6: draw the whole conversation
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            show_assistant_message(message)

# UI step 7: answer the message, then redraw the page so the sidebar is up to date
if incoming_text != "":
    with st.chat_message("assistant"):
        with st.spinner("Finding evidence and verifying the answer..."):
            response = call_api(
                "POST",
                "/chat",
                json={"message": incoming_text, "chat_id": st.session_state["chat_id"]},
            )

    if response.status_code == 200:
        data = response.json()
        st.session_state["messages"].append(make_message(data["assistant"]))
        if data["chat_id"] is not None:
            st.session_state["chat_id"] = data["chat_id"]
    else:
        st.session_state["messages"].append(
            make_message({"text": str(response.json()["detail"])}, mode="error")
        )

    st.rerun()

if has_input:
    st.rerun()
