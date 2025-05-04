
import streamlit as st
from backend.core.db import SessionLocal, User
from backend.core.auth_utils import hash_password, verify_password

st.title("🔐 Connexion ou Création de Compte")

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
                st.warning("Ce compte n'existe pas. Veuillez créer un compte.")
            elif verify_password(password, user.hashed_password):
                st.success(f"Bienvenue, {email} ! ✅")
                st.session_state["user"] = email
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
