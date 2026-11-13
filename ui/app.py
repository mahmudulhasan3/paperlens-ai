import html
import time

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"
LINKEDIN_URL = "https://www.linkedin.com/in/mahmudulhasan03"
THEME_LABELS = ["System", "Light", "Dark"]
MODE_LABELS = {
    "qa": "Answer",
    "summarize": "Summary",
    "compare": "Comparison",
    "extract": "Extracted information",
}
STATUS_MARKS = {
    "supported": "✓ Supported",
    "partially_supported": "~ Partly supported",
    "unsupported": "✗ Not supported",
}

st.set_page_config(
    page_title="PaperLens-AI",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="expanded",
)

# UI step 0: the colours of the light and the dark theme (every other rule uses these names)
LIGHT_VARS = "--bg: #ffffff; --bg2: #f7f7f8; --text: #202123; --muted: #6e6e80; --border: #d9d9e3; --hover: #ececf1; --bubble: #f4f4f4; --accent: #10a37f; --accent-text: #ffffff;"
DARK_VARS = "--bg: #212121; --bg2: #171717; --text: #ececec; --muted: #a1a1aa; --border: #4d4d4d; --hover: #2f2f2f; --bubble: #2f2f2f; --accent: #10a37f; --accent-text: #ffffff;"

# UI step 0: the look of the whole page, written once with the colour names above
BASE_RULES = """
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stBottom"], [data-testid="stBottom"] > div {background: var(--bg) !important;}
.block-container {max-width: 760px; padding-top: 1rem; padding-bottom: 7rem;}
section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div {background: var(--bg2) !important;}
.stApp, .stApp p, .stApp span, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, [data-testid="stMarkdownContainer"] {color: var(--text) !important;}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {color: var(--muted) !important;}
a {color: var(--accent) !important;}
hr {border-color: var(--border) !important;}

[data-testid^="stBaseButton-"] {border-radius: 10px !important; border: 1px solid var(--border) !important; background: var(--bg) !important; font-weight: 500;}
.stApp [data-testid^="stBaseButton-"] p, .stApp [data-testid^="stBaseButton-"] span {color: var(--text) !important;}
[data-testid^="stBaseButton-"]:hover {background: var(--hover) !important;}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {background: var(--accent) !important; border: none !important;}
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover {background: var(--accent) !important; filter: brightness(0.92);}
.stApp [data-testid="stBaseButton-primary"] p, .stApp [data-testid="stBaseButton-primary"] span, .stApp [data-testid="stBaseButton-primaryFormSubmit"] p, .stApp [data-testid="stBaseButton-primaryFormSubmit"] span {color: var(--accent-text) !important;}

section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {background: transparent !important; border: none !important; justify-content: flex-start !important; text-align: left !important; width: 100%;}
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {background: var(--hover) !important;}
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] p {text-align: left !important; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;}

[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {background: var(--bg2) !important; border-color: var(--border) !important; border-radius: 12px !important;}
input, textarea {color: var(--text) !important; -webkit-text-fill-color: var(--text) !important;}
input::placeholder, textarea::placeholder {color: var(--muted) !important; -webkit-text-fill-color: var(--muted) !important;}
[data-testid="stFileUploaderDropzone"] {background: var(--bg2) !important; border-color: var(--border) !important;}
[data-testid="stForm"] {border: none !important; padding: 0 !important;}

[data-testid="stChatInput"] {background: var(--bg2) !important; border: 1px solid var(--border) !important; border-radius: 28px !important;}
[data-testid="stChatInput"] > div, [data-testid="stChatInput"] textarea {background: transparent !important;}
[data-testid="stChatInput"] button {background: transparent !important; border: none !important;}
[data-testid="stChatInput"] svg {fill: var(--text) !important; color: var(--text) !important;}

[data-testid="stExpander"] {border: 1px solid var(--border) !important; border-radius: 12px !important; background: var(--bg2) !important;}
[data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] {display: none !important;}
div[data-testid="stChatMessage"] {background: transparent !important;}
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: var(--bubble) !important; border-radius: 20px; width: fit-content; max-width: 85%;
    margin-left: auto; padding: 0.6rem 1rem;
}

.brand {font-size: 1.15rem; font-weight: 700; padding: 0.2rem 0 0.6rem 0.4rem;}
.credit {font-size: 0.75rem; padding: 0.5rem 0.5rem 0 0.5rem;}
.credit, .credit a {color: var(--muted) !important;}
.credit a {text-decoration: underline;}
.page-title {text-align: center; font-size: 1.6rem; font-weight: 700; margin: 0.5rem 0 1rem 0;}

section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {display: flex; flex-direction: column; height: 100%;}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {flex: 1; display: flex; flex-direction: column; padding-bottom: 0.8rem;}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div, section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > [data-testid="stVerticalBlock"] {flex: 1; min-height: calc(100vh - 6rem);}
.st-key-account_box {margin-top: auto; padding-top: 0.6rem; border-top: 1px solid var(--border);}
.st-key-account_box button {width: 100%;}
"""

# UI step 0: everything that must survive a rerun lives in the session
DEFAULTS = {
    "token": None,
    "email": None,
    "is_guest": True,
    "notice": None,
    "messages": [],
    "chat_id": None,
    "pending": None,
    "profile": None,
    "theme": "system",
    "animate": False,
    "auth_step": "email",
    "auth_email": "",
    "view": "chat",
    "menu_open": False,
}
for key in DEFAULTS:
    if key not in st.session_state:
        st.session_state[key] = DEFAULTS[key]


# UI helper: the CSS of the chosen theme (light, dark, or the one the computer uses)
def theme_css(theme):
    if theme == "dark":
        variables = ":root {" + DARK_VARS + "}"
    elif theme == "light":
        variables = ":root {" + LIGHT_VARS + "}"
    else:
        variables = (
            ":root {"
            + LIGHT_VARS
            + "} @media (prefers-color-scheme: dark) {:root {"
            + DARK_VARS
            + "}}"
        )

    return "<style>" + variables + BASE_RULES + "</style>"


# UI helper: the first letters of a name, shown when there is no photo
def initials_of(name):
    letters = ""

    for part in name.split()[:2]:
        if part[0].isalnum():
            letters = letters + part[0].upper()

    if letters == "":
        letters = "?"

    return letters


# UI helper: the round photo or the round initials at the left of the profile button in the sidebar
def account_css(name, avatar):
    if avatar != "":
        circle = (
            'content: ""; background: url("data:image/jpeg;base64,'
            + avatar
            + '") center / cover no-repeat;'
        )
    else:
        circle = (
            'content: "'
            + initials_of(name)
            + '"; background: #10a37f; color: #ffffff; font-weight: 600; font-size: 0.8rem;'
        )

    css = ".st-key-profile_btn button {position: relative; padding-left: 3.4rem !important; "
    css = (
        css
        + "justify-content: flex-start !important; background: transparent !important; "
    )
    css = css + "border: none !important; min-height: 3rem; width: 100%;}"
    css = (
        css
        + ".st-key-profile_btn button::before {position: absolute; left: 0.5rem; top: 50%; "
    )
    css = (
        css
        + "transform: translateY(-50%); width: 34px; height: 34px; border-radius: 50%; "
    )
    css = (
        css
        + "display: flex; align-items: center; justify-content: center; "
        + circle
        + "}"
    )

    return "<style>" + css + "</style>"


# UI helper: a round profile photo (or initials) as HTML, used on the settings page
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


# UI helper: forget the current session and everything shown on the screen
def clear_session():
    st.session_state["token"] = None
    st.session_state["email"] = None
    st.session_state["is_guest"] = True
    st.session_state["messages"] = []
    st.session_state["chat_id"] = None
    st.session_state["pending"] = None
    st.session_state["profile"] = None
    st.session_state["theme"] = "system"
    st.session_state["animate"] = False
    st.session_state["auth_step"] = "email"
    st.session_state["auth_email"] = ""
    st.session_state["view"] = "chat"
    st.session_state["menu_open"] = False


# UI helper: start a guest session automatically, so the chat is open at once
def start_guest():
    try:
        response = requests.post(API_URL + "/auth/guest", timeout=20)
    except requests.RequestException:
        st.error("Cannot reach the server. Please start the API and reload this page.")
        st.stop()

    if response.status_code != 200:
        st.error("Could not start a guest session. Please reload this page.")
        st.stop()

    clear_session()
    st.session_state["token"] = response.json()["access_token"]
    st.session_state["is_guest"] = True


# UI helper: send a request to the API with the token, and start a new session if the token is no longer valid
def call_api(method, path, **kwargs):
    headers = {"Authorization": "Bearer " + st.session_state["token"]}
    response = requests.request(
        method, API_URL + path, headers=headers, timeout=300, **kwargs
    )

    if response.status_code == 401:
        clear_session()
        st.session_state["notice"] = "Your session expired. A new session was started."
        st.rerun()

    return response


# UI helper: read the profile of a registered user and use the theme that was saved in it
def load_profile():
    response = call_api("GET", "/profile")

    if response.status_code == 200:
        st.session_state["profile"] = response.json()
        st.session_state["theme"] = st.session_state["profile"]["theme"]


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


# UI helper: draw one assistant message with its paper buttons, check details and sources
def show_assistant_message(
    message, animate=False, asked="", show_choices=False, key_prefix="m"
):
    if message["mode"] not in ["error", "notice"]:
        caption = MODE_LABELS.get(message["mode"], message["mode"])
        if len(message["used"]) > 0:
            caption = caption + " · " + ", ".join(message["used"])
        st.caption(caption)

    if animate and message["mode"] not in ["error", "notice"]:
        st.write_stream(word_stream(message["text"]))
    else:
        st.markdown(message["text"])

    # One click chooses the paper, and the question is sent again with the file name in brackets
    if show_choices and asked != "":
        for position in range(len(message["choices"])):
            filename = message["choices"][position]
            if st.button(filename, key="choice_" + key_prefix + "_" + str(position)):
                st.session_state["pending"] = asked + " (" + filename + ")"
                st.rerun()

    if len(message["claims"]) > 0:
        label = "How this answer was checked"
        if message["removed"] > 0:
            label = (
                label
                + " ("
                + str(message["removed"])
                + " unsupported statement(s) removed)"
            )

        with st.expander(label):
            for item in message["claims"]:
                mark = STATUS_MARKS.get(item["status"], item["status"])
                line = "**" + mark + "**: " + item["claim"]
                evidence = ", ".join(item["evidence"])
                if evidence != "":
                    line = line + "  \n_Source: " + evidence + "_"
                st.markdown(line)

    for item in message["citations"]:
        label = (
            "Source ["
            + str(item["number"])
            + "] · "
            + item["filename"]
            + " · "
            + item["section"][:60]
        )
        label = (
            label + " · pages " + str(item["page_start"]) + "-" + str(item["page_end"])
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
    st.session_state["view"] = "chat"
    st.rerun()


# UI helper: delete a saved chat of a registered user
def delete_chat(chat_id):
    call_api("DELETE", "/chats/" + str(chat_id))

    if st.session_state["chat_id"] == chat_id:
        st.session_state["messages"] = []
        st.session_state["chat_id"] = None

    st.rerun()


# UI helper: go back to the chat page from the login page or the settings page
def go_to_chat():
    st.session_state["view"] = "chat"
    st.rerun()


# UI helper: show the login page from the beginning
def open_login():
    st.session_state["auth_step"] = "email"
    st.session_state["auth_email"] = ""
    st.session_state["view"] = "login"
    st.rerun()


# UI helper: finish a login, the guest session is replaced by the account
def finish_login(token, email):
    clear_session()
    st.session_state["token"] = token
    st.session_state["email"] = email
    st.session_state["is_guest"] = False
    st.rerun()


# UI page: log in or sign up, step 1 email, step 2 password (or a new password for a new account)
def show_login_page():
    left, middle, right = st.columns([1, 4, 1])

    with middle:
        if st.button("← Back to chat", key="login_back"):
            go_to_chat()

        st.markdown(
            '<div class="page-title">Log in or sign up</div>', unsafe_allow_html=True
        )
        step = st.session_state["auth_step"]

        if step == "email":
            st.caption(
                "Enter your email. We will check if you already have an account."
            )

            with st.form("auth_email_form"):
                email = st.text_input("Email address", placeholder="Email address")
                submitted = st.form_submit_button("Continue", type="primary")

            if submitted:
                response = requests.post(
                    API_URL + "/auth/check-email", json={"email": email}
                )

                if response.status_code != 200:
                    st.error(str(response.json()["detail"]))
                else:
                    st.session_state["auth_email"] = email.strip().lower()
                    if response.json()["exists"]:
                        st.session_state["auth_step"] = "password"
                    else:
                        st.session_state["auth_step"] = "create"
                    st.rerun()

        elif step == "password":
            st.markdown(
                "Welcome back. Enter the password for **"
                + html.escape(st.session_state["auth_email"])
                + "**."
            )

            with st.form("auth_password_form"):
                password = st.text_input(
                    "Password", type="password", placeholder="Password"
                )
                submitted = st.form_submit_button("Log in", type="primary")

            if submitted:
                response = requests.post(
                    API_URL + "/auth/login",
                    data={
                        "username": st.session_state["auth_email"],
                        "password": password,
                    },
                )

                if response.status_code == 200:
                    finish_login(
                        response.json()["access_token"], st.session_state["auth_email"]
                    )
                else:
                    st.error(str(response.json()["detail"]))

            if st.button("Use a different email", key="login_other_email"):
                st.session_state["auth_step"] = "email"
                st.rerun()

        else:
            st.markdown(
                "There is no account for **"
                + html.escape(st.session_state["auth_email"])
                + "** yet. Choose a password to create one."
            )

            with st.form("auth_create_form"):
                password = st.text_input(
                    "Password (at least 8 characters)",
                    type="password",
                    placeholder="Password",
                )
                submitted = st.form_submit_button("Create account", type="primary")

            if submitted:
                response = requests.post(
                    API_URL + "/auth/register",
                    json={
                        "email": st.session_state["auth_email"],
                        "password": password,
                    },
                )

                if response.status_code != 201:
                    st.error(str(response.json()["detail"]))
                else:
                    login = requests.post(
                        API_URL + "/auth/login",
                        data={
                            "username": st.session_state["auth_email"],
                            "password": password,
                        },
                    )
                    if login.status_code == 200:
                        finish_login(
                            login.json()["access_token"], st.session_state["auth_email"]
                        )
                    else:
                        st.error("The account was created. Please log in.")

            if st.button("Use a different email", key="create_other_email"):
                st.session_state["auth_step"] = "email"
                st.rerun()


# UI page: the settings of a registered user (photo, name, about text, email and appearance)
def show_settings_page():
    profile = st.session_state["profile"]
    left, middle, right = st.columns([1, 4, 1])

    with middle:
        if st.button("← Back to chat", key="settings_back"):
            go_to_chat()

        st.markdown('<div class="page-title">Settings</div>', unsafe_allow_html=True)
        st.markdown(
            avatar_html(profile["avatar"], profile["name"], 88), unsafe_allow_html=True
        )

        photo = st.file_uploader(
            "Profile photo", type=["png", "jpg", "jpeg", "webp"], key="photo_upload"
        )
        name = st.text_input(
            "Name",
            value=profile["display_name"],
            max_chars=100,
            placeholder=profile["name"],
        )
        bio = st.text_area("About you", value=profile["bio"], max_chars=500, height=110)
        st.text_input("Email", value=profile["email"], disabled=True)

        current_label = profile["theme"].capitalize()
        theme_label = st.selectbox(
            "Appearance", THEME_LABELS, index=THEME_LABELS.index(current_label)
        )

        col_save, col_remove = st.columns(2)

        if col_save.button("Save changes", type="primary", key="settings_save"):
            if photo is not None:
                files = {"file": (photo.name, photo.getvalue(), photo.type)}
                response = call_api("POST", "/profile/avatar", files=files)
                if response.status_code != 200:
                    st.error(str(response.json()["detail"]))
                    return

            response = call_api(
                "PUT",
                "/profile",
                json={"display_name": name, "bio": bio, "theme": theme_label.lower()},
            )
            if response.status_code != 200:
                st.error(str(response.json()["detail"]))
                return

            load_profile()
            st.session_state["notice"] = "Your settings were saved."
            st.rerun()

        if profile["avatar"] != "":
            if col_remove.button("Remove photo", key="settings_remove_photo"):
                call_api("DELETE", "/profile/avatar")
                load_profile()
                st.rerun()


# UI step 1: every visitor gets a guest session at once, so the chat page opens without a login
if st.session_state["token"] is None:
    start_guest()

# UI step 2: load the profile of a registered user once
if not st.session_state["is_guest"] and st.session_state["profile"] is None:
    load_profile()
    st.rerun()

if st.session_state["is_guest"]:
    account_name = "Guest"
    account_email = ""
    account_avatar = ""
else:
    account_name = st.session_state["profile"]["name"]
    account_email = st.session_state["profile"]["email"]
    account_avatar = st.session_state["profile"]["avatar"]

st.markdown(theme_css(st.session_state["theme"]), unsafe_allow_html=True)
if not st.session_state["is_guest"]:
    st.markdown(account_css(account_name, account_avatar), unsafe_allow_html=True)

documents = []
documents_response = call_api("GET", "/documents")
if documents_response.status_code == 200:
    documents = documents_response.json()["documents"]

# UI step 3: the sidebar, new chat, saved chats, your papers, the account area and the credit
with st.sidebar:
    st.markdown('<div class="brand">🔍 PaperLens-AI</div>', unsafe_allow_html=True)

    if st.button("New chat", icon=":material/edit_square:", key="new_chat"):
        st.session_state["messages"] = []
        st.session_state["chat_id"] = None
        st.session_state["view"] = "chat"
        st.rerun()

    if st.session_state["is_guest"]:
        st.caption("Guest mode: your chat and papers are temporary.")
    else:
        st.caption("Chats")
        chats = []
        chats_response = call_api("GET", "/chats")
        if chats_response.status_code == 200:
            chats = chats_response.json()["chats"]

        if len(chats) == 0:
            st.caption("Your saved chats will appear here.")

        for chat in chats:
            col_open, col_delete = st.columns([5, 1])
            title = chat["title"][:28]
            if chat["id"] == st.session_state["chat_id"]:
                title = "**" + title + "**"

            if col_open.button(title, key="open_" + str(chat["id"])):
                load_chat(chat["id"])
            if col_delete.button("✕", key="delete_" + str(chat["id"])):
                delete_chat(chat["id"])

    st.caption("Your papers")
    if len(documents) == 0:
        st.caption("None yet. Use the + in the message box to add PDFs.")
    for doc in documents:
        st.caption("• " + doc["filename"])

    with st.container(key="account_box"):
        if st.session_state["is_guest"]:
            st.caption("Log in to save your chats and papers.")

            if st.button("Log in", type="primary", key="menu_login"):
                open_login()
        else:
            if st.session_state["menu_open"]:
                if st.button(
                    "Settings", icon=":material/settings:", key="menu_settings"
                ):
                    st.session_state["menu_open"] = False
                    st.session_state["view"] = "settings"
                    st.rerun()

                if st.button("Log out", icon=":material/logout:", key="menu_logout"):
                    clear_session()
                    st.rerun()

            with st.container(key="profile_btn"):
                if st.button(account_name, key="profile_toggle"):
                    st.session_state["menu_open"] = not st.session_state["menu_open"]
                    st.rerun()

        st.markdown(
            '<div class="credit">Developed by <a href="'
            + LINKEDIN_URL
            + '" target="_blank">Mahmudul Hasan</a></div>',
            unsafe_allow_html=True,
        )

if st.session_state["notice"] is not None:
    st.info(st.session_state["notice"])
    st.session_state["notice"] = None

# UI step 4: the login page and the settings page replace the chat page while they are open
if st.session_state["view"] == "login" and st.session_state["is_guest"]:
    show_login_page()
    st.stop()

if st.session_state["view"] == "settings" and not st.session_state["is_guest"]:
    show_settings_page()
    st.stop()

st.session_state["view"] = "chat"

# UI step 5: the message box (it is pinned to the bottom) and what the user sent
prompt = st.chat_input(
    "Message PaperLens-AI", accept_file="multiple", file_type=["pdf"]
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

# UI step 6: the welcome text and the suggestions on an empty chat
if len(st.session_state["messages"]) == 0 and not has_input:
    st.markdown(
        "<h2 style='text-align: center; margin-top: 4rem;'>What would you like to know about your papers?</h2>",
        unsafe_allow_html=True,
    )

    if len(documents) == 0:
        st.markdown(
            "<p style='text-align: center; color: var(--muted);'>Press the + in the message box to add PDF files, "
            "then ask anything about them.</p>",
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

# UI step 7: upload the attached PDFs, one after another
for uploaded in incoming_files:
    files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}

    with st.spinner("Reading " + uploaded.name + "..."):
        response = call_api("POST", "/upload", files=files)

    if response.status_code == 200:
        data = response.json()
        if data["duplicate"]:
            text = data["filename"] + " was already added."
        else:
            text = "Added " + data["filename"] + ". You can ask about it now."
        notice = make_message({"text": text}, mode="notice")
    else:
        notice = make_message(
            {"text": uploaded.name + ": " + str(response.json()["detail"])},
            mode="error",
        )

    st.session_state["messages"].append(notice)

if incoming_text != "":
    st.session_state["messages"].append({"role": "user", "content": incoming_text})

# UI step 8: draw the whole conversation, the newest answer is typed word by word
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

# UI step 9: answer the message, then redraw the page so the sidebar is up to date
if incoming_text != "":
    with st.chat_message("assistant"):
        with st.spinner("Finding evidence and checking the answer..."):
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
