import streamlit as st


def main():
    st.write("Are you sure you want to log out?")

    with st.container():
        # Use empty columns for wide page side padding
        padding_left, center, padding_right = st.columns([1, 3, 3])

        with padding_left:
            btn_yes, btn_no = st.columns(2)
            with btn_yes:
                if st.button("✅ Yes", key="confirm_logout_yes"):
                    if st.session_state.get("authentication_status"):
                        st.session_state.authenticator.logout(location="unrendered")
                        # login required to maintain session state
                        st.session_state.authenticator.login(location="unrendered")
                        st.switch_page("dashboard_pages/01_page_recordings.py")
            with btn_no:
                if st.button("❌ No", key="confirm_logout_no"):
                    st.switch_page("dashboard_pages/01_page_recordings.py")


if __name__ == "__main__":
    main()
