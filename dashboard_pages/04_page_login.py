import streamlit as st
from streamlit_cookies_controller import CookieController


def main():
    controller = CookieController()

    try:
        st.session_state.authenticator.login()
    except Exception as e:
        st.error(e)

    if st.session_state.get("authentication_status") is False:
        st.error("Username/password is incorrect")
        controller.set("cookie_auth", False)

    if st.session_state.get("authentication_status"):
        controller.set("cookie_auth", True)


if __name__ == "__main__":
    main()
