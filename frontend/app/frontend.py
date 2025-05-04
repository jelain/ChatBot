import streamlit as st
import requests
import time
from requests.utils import quote

import sys
import os

# Ajoute dynamiquement la racine du projet au sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
from backend.core.db import SessionLocal, User
from backend.core.auth_utils import hash_password, verify_password

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

# Fonction qui envoie le prompt à l'API backend et récupère la réponse
def response_generator(prompt):
    encoded_prompt = quote(prompt, safe="")  # Encode le prompt pour éviter les erreurs d'URL
    response = requests.get(f"http://127.0.0.1:8000/llm/{encoded_prompt}")
    response_text = response.json().get("answer", "Erreur : aucune réponse reçue.")

    # Génère la réponse mot par mot avec un petit délai pour effet "chat"
    for word in response_text.split():
        yield word + " "
        time.sleep(0.05)

# Titre principal
st.title("Chatbot avec gestion des sessions")

# Initialisation des variables de session
if "sessions" not in st.session_state:
    st.session_state.sessions = {"Session 1": []}
if "current_session" not in st.session_state:
    st.session_state.current_session = "Session 1"

# Ligne supérieure avec le bouton à droite dans la sidebar
col1, col2 = st.sidebar.columns([4, 1])
with col2:
    if st.button("➕", key="new_session_btn"):
        new_session_name = f"Session {len(st.session_state.sessions) + 1}"
        st.session_state.sessions[new_session_name] = []
        st.session_state.current_session = new_session_name
        st.rerun()

st.sidebar.title("Chat")

# Récupération des noms de session
session_names = list(st.session_state.sessions.keys())

# Création de boutons pour chaque session avec bouton de suppression
for session_name in session_names:
    col1, col2 = st.sidebar.columns([4, 1])
    with col1:
        if st.button(session_name, key=f"select_{session_name}"):
            st.session_state.current_session = session_name
    with col2:
        if st.button("🗑️", key=f"delete_{session_name}"):
            # Supprimer la session
            del st.session_state.sessions[session_name]
            # Réassigner la session courante
            if st.session_state.sessions:
                st.session_state.current_session = list(st.session_state.sessions.keys())[0]
            else:
                st.session_state.sessions = {"Session 1": []}
                st.session_state.current_session = "Session 1"
            st.rerun()

# Affichage de la session sélectionnée
if st.session_state.current_session:
    st.sidebar.markdown(f"**Session actuelle :** {st.session_state.current_session}")
else:
    st.sidebar.markdown("*Aucune session sélectionnée*")

# Utilisation sécurisée de la session actuelle
if st.session_state.current_session:
    selected_session = st.session_state.current_session
    messages = st.session_state.sessions[selected_session]

    # Affichage de l'historique
    st.subheader(f"Chat - {selected_session}")
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Zone d'entrée utilisateur
if prompt := st.chat_input("Que voulez-vous dire ?"):
    # Ajout du message utilisateur
    st.session_state.sessions[st.session_state.current_session].append(
        {"role": "user", "content": prompt}
    )
    with st.chat_message("user"):
        st.markdown(prompt)

    # Appel au backend et affichage de la réponse
    with st.chat_message("assistant"):
        response = st.write_stream(response_generator(prompt))

    # Sauvegarde de la réponse
    st.session_state.sessions[st.session_state.current_session].append(
        {"role": "assistant", "content": response}
    )
