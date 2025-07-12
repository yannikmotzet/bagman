import streamlit as st


def main():
    try:
        st.session_state.authenticator.login()
    except Exception as e:
        st.error(e)

    if st.session_state.get("authentication_status") is False:
        st.error("Username/password is incorrect")


if __name__ == "__main__":
    main()
