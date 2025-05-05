import streamlit as st
import requests
import time
from requests.utils import quote
import sys
import os
import re

# Ajouter racine du projet au path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.core.db import SessionLocal, User, ChatSession, ChatMessage
from backend.core.auth_utils import hash_password, verify_password

def generate_title(prompt):
    return " ".join(prompt.strip().split()[:6]).capitalize()

# --------- AUTHENTIFICATION ---------
def login_interface():
    st.title("🔐 Connexion / Création de Compte")

    mode = st.radio("Choisir une option :", ["Se connecter", "Créer un compte"])
    email = st.text_input("Email")
    password = st.text_input("Mot de passe", type="password")
    db = SessionLocal()

    if st.button("Valider"):
        if not email or not password:
            st.error("Veuillez remplir tous les champs.")
        else:
            user = db.query(User).filter(User.email == email).first()

            if mode == "Se connecter":
                if not user:
                    st.warning("Ce compte n'existe pas.")
                elif verify_password(password, user.hashed_password):
                    st.success(f"Bienvenue, {email} ! ✅")
                    st.session_state["user"] = email

                    st.session_state.sessions = {}
                    user_sessions = db.query(ChatSession).filter(ChatSession.user_id == user.id).all()
                    for s in user_sessions:
                        st.session_state.sessions[s.name] = []
                        messages = db.query(ChatMessage).filter(ChatMessage.session_id == s.id).order_by(ChatMessage.timestamp).all()
                        for m in messages:
                            st.session_state.sessions[s.name].append({
                                "role": m.role,
                                "content": m.content
                            })

                    session_names = list(st.session_state.sessions.keys())
                    if session_names:
                        session_numbers = []
                        for name in session_names:
                            match = re.match(r"Session (\d+)", name)
                            if match:
                                session_numbers.append(int(match.group(1)))
                        if session_numbers:
                            max_n = max(session_numbers)
                            last_session = f"Session {max_n}"
                            if st.session_state.sessions[last_session]:
                                new_name = f"Session {max_n + 1}"
                                new_session = ChatSession(name=new_name, user_id=user.id)
                                db.add(new_session)
                                db.commit()
                                st.session_state.sessions[new_name] = []
                                st.session_state.current_session = new_name
                            else:
                                st.session_state.current_session = last_session
                        else:
                            st.session_state.current_session = session_names[0]
                    else:
                        new_name = "Session 1"
                        new_session = ChatSession(name=new_name, user_id=user.id)
                        db.add(new_session)
                        db.commit()
                        st.session_state.sessions[new_name] = []
                        st.session_state.current_session = new_name

                    st.rerun()
                else:
                    st.error("Mot de passe incorrect.")
            elif mode == "Créer un compte":
                if user:
                    st.warning("Un compte existe déjà avec cet email.")
                else:
                    new_user = User(email=email, hashed_password=hash_password(password))
                    db.add(new_user)
                    db.commit()
                    st.success("Compte créé avec succès. Vous pouvez maintenant vous connecter.")

# --------- MAIN LOGIC ---------
if "user" not in st.session_state:
    login_interface()
    st.stop()
else:
    st.sidebar.success(f"Connecté en tant que {st.session_state['user']}")
    if st.sidebar.button("Se déconnecter"):
        st.session_state.clear()
        st.rerun()

# --------- API LLM ---------
def response_generator(prompt):
    encoded_prompt = quote(prompt, safe="")
    headers = {
        "X-User-Email": st.session_state.get("user", "default"),
        "X-Session-ID": st.session_state.get("current_session", "Session 1")
    }
    response = requests.get(f"http://127.0.0.1:8000/llm/{encoded_prompt}", headers=headers)
    response_text = response.json().get("answer", "Erreur : aucune réponse reçue.")
    for word in response_text.split():
        yield word + " "
        time.sleep(0.05)

# --------- INTERFACE ---------
st.title("Chatbot Transport")

# Init si vide
if "sessions" not in st.session_state:
    st.session_state.sessions = {"Session 1": []}
if "current_session" not in st.session_state:
    st.session_state.current_session = "Session 1"

# ➕ Nouvelle session via bouton
col1, col2 = st.sidebar.columns([4, 1])
with col2:
    if st.button("➕", key="new_session_btn"):
        i = 1
        while f"Session {i}" in st.session_state.sessions:
            i += 1
        new_session_name = f"Session {i}"
        st.session_state.sessions[new_session_name] = []

        db = SessionLocal()
        user = db.query(User).filter(User.email == st.session_state["user"]).first()
        new_session = ChatSession(name=new_session_name, user_id=user.id)
        db.add(new_session)
        db.commit()

        st.session_state.current_session = new_session_name
        st.rerun()

# Sidebar liste des sessions
st.sidebar.title("Chat")
session_names = list(st.session_state.sessions.keys())
for session_name in session_names:
    col1, col2 = st.sidebar.columns([4, 1])
    with col1:
        if st.button(session_name, key=f"select_{session_name}"):
            st.session_state.current_session = session_name
    with col2:
        if st.button("🗑️", key=f"delete_{session_name}"):
            db = SessionLocal()
            user = db.query(User).filter(User.email == st.session_state["user"]).first()
            session_to_delete = db.query(ChatSession).filter_by(name=session_name, user_id=user.id).first()
            if session_to_delete:
                db.query(ChatMessage).filter(ChatMessage.session_id == session_to_delete.id).delete()
                db.delete(session_to_delete)
                db.commit()
            del st.session_state.sessions[session_name]
            if st.session_state.sessions:
                st.session_state.current_session = list(st.session_state.sessions.keys())[0]
            else:
                st.session_state.sessions = {"Session 1": []}
                st.session_state.current_session = "Session 1"
            st.rerun()

# Affichage session active
st.sidebar.markdown(f"**Chat actuel :** {st.session_state.current_session}")

# Affichage historique
selected_session = st.session_state.current_session
messages = st.session_state.sessions[selected_session]
st.subheader(f"Chat - {selected_session}")
for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input utilisateur
if prompt := st.chat_input("Que voulez-vous dire ?"):

    # --- Titre dynamique si 1er message ---
    if not st.session_state.sessions[selected_session]:
        new_title = generate_title(prompt)

        # Mise à jour session_state
        st.session_state.sessions[new_title] = st.session_state.sessions.pop(selected_session)
        st.session_state.current_session = new_title

        # Mise à jour DB
        db = SessionLocal()
        user = db.query(User).filter(User.email == st.session_state["user"]).first()
        session = db.query(ChatSession).filter_by(name=selected_session, user_id=user.id).first()
        if session:
            session.name = new_title
            db.commit()

        selected_session = new_title  # Important pour la suite

    st.session_state.sessions[selected_session].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Sauvegarde message user
    db = SessionLocal()
    user = db.query(User).filter(User.email == st.session_state["user"]).first()
    session = db.query(ChatSession).filter_by(name=selected_session, user_id=user.id).first()
    if not session:
        session = ChatSession(name=selected_session, user_id=user.id)
        db.add(session)
        db.commit()
    db.add(ChatMessage(role="user", content=prompt, session_id=session.id))
    db.commit()

    # Réponse assistant
    with st.chat_message("assistant"):
        response = st.write_stream(response_generator(prompt))

    st.session_state.sessions[selected_session].append({"role": "assistant", "content": response})
    db.add(ChatMessage(role="assistant", content=response, session_id=session.id))
    db.commit()
