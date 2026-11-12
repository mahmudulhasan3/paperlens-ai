import html
import time

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"
LINKEDIN_URL = "https://www.linkedin.com/in/mahmudulhasan03"
THEME_LABELS = ["System", "Light", "Dark"]

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

# UI step 0: the dark colours (used for the dark theme, and for the system theme when the computer is dark)
DARK_RULES = """
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stBottom"], [data-testid="stBottom"] > div {background: #212121 !important;}
section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div {background: #171717 !important;}
.stApp, .stApp p, .stApp span, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, [data-testid="stMarkdownContainer"] {color: #ececec !important;}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {color: #a1a1aa !important;}
a {color: #8ab4f8 !important;}
hr {border-color: #3a3a3a !important;}
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="base-input"], [data-baseweb="select"] > div {background: #2f2f2f !important; border-color: #4d4d4d !important;}
input, textarea {color: #ececec !important; -webkit-text-fill-color: #ececec !important;}
[data-testid="stChatInput"], [data-testid="stChatInput"] > div {background: #2f2f2f !important; border-color: #4d4d4d !important;}
[data-testid="stBaseButton-secondary"] {background: #2f2f2f !important; color: #ececec !important; border-color: #4d4d4d !important;}
[data-testid="stBaseButton-secondary"]:hover {background: #3a3a3a !important;}
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {background: transparent !important; border: none !important;}
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {background: #2a2a2a !important;}
[data-testid="stBaseButton-primary"] {background: #10a37f !important; border: none !important;}
[data-testid="stBaseButton-primary"] p {color: #ffffff !important;}
[data-testid="stExpander"] {border-color: #4d4d4d !important; background: #262626 !important;}
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {background: #2f2f2f !important;}
div[role="dialog"], div[role="dialog"] > div {background: #2b2b2b !important;}
[data-testid="stFileUploaderDropzone"] {background: #2f2f2f !important;}
"""

# UI step 0: everything that must survive a rerun lives in the session
DEFAULTS = {
    "token": None,
    "email": None,
    "is_guest": False,
    "notice": None,
    "messages": [],
    "chat_id": None,
    "pending": None,
    "profile": None,
    "theme": "system",
    "animate": False,
}
for key in DEFAULTS:
    if key not in st.session_state:
        st.session_state[key] = DEFAULTS[key]


# UI helper: the CSS of the chosen theme (light is the normal look, so it needs no extra CSS)
def theme_css(theme):
    if theme == "dark":
        return "<style>" + DARK_RULES + "</style>"
    if theme == "system":
        return "<style>@media (prefers-color-scheme: dark) {" + DARK_RULES + "}</style>"
    return ""


st.markdown(theme_css(st.session_state["theme"]), unsafe_allow_html=True)


# UI helper: forget the login or guest session and everything shown on the screen
def clear_session():
    st.session_state["token"] = None
    st.session_state["email"] = None
    st.session_state["is_guest"] = False
    st.session_state["messages"] = []
    st.session_state["chat_id"] = None
    st.session_state["pending"] = None
    st.session_state["profile"] = None
    st.session_state["theme"] = "system"
    st.session_state["animate"] = False


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


# UI helper: read the profile of a registered user and use the theme that was saved in it
def load_profile():
    response = call_api("GET", "/profile")

    if response.status_code == 200:
        st.session_state["profile"] = response.json()
        st.session_state["theme"] = st.session_state["profile"]["theme"]


# UI helper: the first letters of a name, shown when there is no photo
def initials_of(name):
    letters = ""

    for part in name.split()[:2]:
        letters = letters + part[0].upper()

    if letters == "":
        letters = "?"

    return letters


# UI helper: a round profile photo, or a round circle with the initials
def avatar_html(avatar, name, size):
    size_text = str(size) + "px"

    if avatar != "":
        return (
            '<img src="data:image/jpeg;base64,'
            + avatar
            + '" style="width:'
            + size_text
            + ";height:"
            + size_text
            + ';border-radius:50%;object-fit:cover;">'
        )

    style = (
        "width:"
        + size_text
        + ";height:"
        + size_text
        + ";border-radius:50%;background:#10a37f;"
    )
    style = (
        style
        + "color:#ffffff;display:flex;align-items:center;justify-content:center;font-weight:600;"
    )
    return '<div style="' + style + '">' + html.escape(initials_of(name)) + "</div>"


# UI helper: give the words of a text one by one, so the answer appears smoothly
def word_stream(text):
    words = text.split(" ")
    delay = min(0.03, 4.0 / max(len(words), 1))

    for word in words:
        yield word + " "
        time.sleep(delay)


# UI helper: build one assistant message with every field the screen needs
def make_message(data, mode=None):
    message = {
        "role": "assistant",
        "mode": "qa",
        "text": "",
        "claims": [],
        "removed": 0,
        "citations": [],
        "used": [],
        "choices": [],
    }

    if data is not None:
        for key in [
            "mode",
            "text",
            "claims",
            "removed",
            "citations",
            "used",
            "choices",
        ]:
            if key in data:
                message[key] = data[key]

    if mode is not None:
        message["mode"] = mode

    return message


# UI helper: draw one assistant message (typed word by word if it is new) with its paper buttons, claim table and citations
def show_assistant_message(
    message, animate=False, asked="", show_choices=False, key_prefix="m"
):
    if message["mode"] not in ["error", "notice"]:
        caption = "Mode: " + message["mode"]
        if len(message["used"]) > 0:
            caption = caption + " | Paper: " + ", ".join(message["used"])
        st.caption(caption)

    if animate and message["mode"] not in ["error", "notice"]:
        st.write_stream(word_stream(message["text"]))
    else:
        st.markdown(message["text"])

    # One click chooses the paper, the question is sent again with the file name in brackets
    if show_choices and asked != "":
        for position in range(len(message["choices"])):
            filename = message["choices"][position]
            if st.button(filename, key="choice_" + key_prefix + "_" + str(position)):
                st.session_state["pending"] = asked + " (" + filename + ")"
                st.rerun()

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


# UI helper: the settings window of a registered user (photo, name, profile, email and appearance)
@st.dialog("Settings")
def settings_dialog():
    profile = st.session_state["profile"]

    st.markdown(
        avatar_html(profile["avatar"], profile["name"], 80), unsafe_allow_html=True
    )
    photo = st.file_uploader(
        "Profile photo", type=["png", "jpg", "jpeg", "webp"], key="photo_upload"
    )
    name = st.text_input("Name", value=profile["display_name"], max_chars=100)
    bio = st.text_area("Profile", value=profile["bio"], max_chars=500, height=100)
    st.text_input("Email", value=profile["email"], disabled=True)

    current_label = profile["theme"].capitalize()
    theme_label = st.selectbox(
        "Appearance", THEME_LABELS, index=THEME_LABELS.index(current_label)
    )

    col_save, col_remove = st.columns(2)

    if col_save.button("Save", type="primary"):
        if photo is not None:
            files = {"file": (photo.name, photo.getvalue(), photo.type)}
            response = call_api("POST", "/profile/avatar", files=files)
            if response.status_code != 200:
                st.error(str(response.json()["detail"]))
                st.stop()

        response = call_api(
            "PUT",
            "/profile",
            json={"display_name": name, "bio": bio, "theme": theme_label.lower()},
        )
        if response.status_code != 200:
            st.error(str(response.json()["detail"]))
            st.stop()

        load_profile()
        st.rerun()

    if profile["avatar"] != "":
        if col_remove.button("Remove photo"):
            call_api("DELETE", "/profile/avatar")
            load_profile()
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

# UI step 2: load the profile of a registered user once, and the papers of this owner
if not st.session_state["is_guest"] and st.session_state["profile"] is None:
    load_profile()
    st.rerun()

documents = []
documents_response = call_api("GET", "/documents")
if documents_response.status_code == 200:
    documents = documents_response.json()["documents"]

# UI step 3: the sidebar with new chat, saved chats, your papers, the account and the credit
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
        account_name = "Guest"
        account_line = "Temporary session"
        account_avatar = ""

        guest_label = st.selectbox(
            "Appearance",
            THEME_LABELS,
            index=THEME_LABELS.index(st.session_state["theme"].capitalize()),
        )
        if guest_label.lower() != st.session_state["theme"]:
            st.session_state["theme"] = guest_label.lower()
            st.rerun()
    else:
        account_name = st.session_state["profile"]["name"]
        account_line = st.session_state["profile"]["email"]
        account_avatar = st.session_state["profile"]["avatar"]

    st.markdown(
        '<div style="display:flex;align-items:center;gap:10px;">'
        + avatar_html(account_avatar, account_name, 38)
        + '<div style="line-height:1.25;"><b>'
        + html.escape(account_name)
        + "</b><br>"
        + '<span style="font-size:0.75rem;opacity:0.7;">'
        + html.escape(account_line)
        + "</span></div></div>",
        unsafe_allow_html=True,
    )

    if not st.session_state["is_guest"]:
        if st.button("Settings"):
            settings_dialog()

    if st.button("End guest session" if st.session_state["is_guest"] else "Log out"):
        clear_session()
        st.rerun()

    st.divider()
    st.markdown(
        '<div style="font-size:0.8rem;line-height:1.5;">Developed by '
        + '<a href="'
        + LINKEDIN_URL
        + '" target="_blank"><b>Mahmudul Hasan</b></a></div>',
        unsafe_allow_html=True,
    )

# UI step 4: the message box (it is pinned to the bottom) and what the user sent
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

# UI step 5: the welcome text and the suggestions on an empty chat
if len(st.session_state["messages"]) == 0 and not has_input:
    st.markdown(
        "<h2 style='text-align: center; margin-top: 3rem;'>What would you like to know about your papers?</h2>",
        unsafe_allow_html=True,
    )

    if len(documents) == 0:
        st.markdown(
            "<p style='text-align: center; color: #6e6e80;'>Attach a PDF with the + in the message box to begin.</p>",
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

# UI step 6: upload the attached PDFs, one after another
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

# UI step 7: draw the whole conversation, the newest answer is typed word by word
last_index = len(st.session_state["messages"]) - 1

for index in range(len(st.session_state["messages"])):
    message = st.session_state["messages"][index]

    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            asked = ""
            if index > 0 and st.session_state["messages"][index - 1]["role"] == "user":
                asked = st.session_state["messages"][index - 1]["content"]

            show_assistant_message(
                message,
                animate=st.session_state["animate"] and index == last_index,
                asked=asked,
                show_choices=(index == last_index),
                key_prefix=str(index),
            )

st.session_state["animate"] = False

# UI step 8: answer the message, then redraw the page so the sidebar is up to date
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
        st.session_state["animate"] = True
        if data["chat_id"] is not None:
            st.session_state["chat_id"] = data["chat_id"]
    else:
        st.session_state["messages"].append(
            make_message({"text": str(response.json()["detail"])}, mode="error")
        )

    st.rerun()

if has_input:
    st.rerun()
