import os
import subprocess
import sys

import streamlit as st
import streamlit_authenticator as stauth
import yaml

from bagman.utils import bagman_utils


def get_git_version():
    try:
        version = subprocess.check_output(
            ["git", "describe", "--tags", "--always"], stderr=subprocess.DEVNULL
        )
        return version.decode("utf-8").strip()
    except subprocess.CalledProcessError:
        return ""


def main(config_path):
    try:
        config = bagman_utils.load_config(config_path)
    except Exception as e:
        st.error(f"Error loading config: {e}")
        return
    st.session_state["config_path"] = config_path
    st.session_state["config"] = config

    st.set_page_config(
        page_title=st.session_state["config"].get("dash_name", None),
        page_icon=st.session_state["config"].get("dash_icon", None),
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "About": (
                f"### bagman\n"
                f"version: {get_git_version()}  \n"
                f"bagman on [GitHub](https://github.com/yannikmotzet/bagman)"
            )
        },
    )

    title = ""
    if "dash_icon" in st.session_state["config"].keys():
        title += st.session_state["config"]["dash_icon"] + " "
    if "dash_name" in st.session_state["config"].keys():
        title += st.session_state["config"]["dash_name"]
    if title != "":
        st.title(title)

    # logo
    if st.context.theme.type == "light":
        if "dash_logo_light" in st.session_state["config"].keys() and os.path.exists(
            st.session_state["config"]["dash_logo_light"]
        ):
            st.logo(
                st.session_state["config"].get("dash_logo_light", None), size="large"
            )
    else:
        if "dash_logo_dark" in st.session_state["config"].keys() and os.path.exists(
            st.session_state["config"]["dash_logo_dark"]
        ):
            st.logo(st.session_state["config"].get("dash_logo_dark"), size="large")

    # authentication
    try:
        authentification_enabled = "dash_auth_file" in st.session_state[
            "config"
        ].keys() and os.path.exists(
            st.session_state["config"].get("dash_auth_file", None)
        )

        if authentification_enabled:
            if "authenticator" not in st.session_state:
                try:
                    with open(
                        st.session_state["config"].get("dash_auth_file", None), "r"
                    ) as file:
                        auth_config = yaml.safe_load(file)
                except FileNotFoundError:
                    st.error("Authentication file not found.")
                    st.stop()
                except yaml.YAMLError:
                    st.error("Error parsing Authentication config file")
                    st.stop()

                try:
                    authenticator = stauth.Authenticate(
                        auth_config["credentials"],
                        auth_config["cookie"]["name"],
                        auth_config["cookie"]["key"],
                        auth_config["cookie"]["expiry_days"],
                    )
                except Exception:
                    st.error("Error initializing authentication")
                    st.stop()

                st.session_state.authenticator = authenticator

            try:
                # Re-invoke an 'unrendered' login widget to maintain session state after reloading page
                st.session_state.authenticator.login(location="unrendered")
            except Exception as e:
                st.error(f"Login error: {e}")
                st.stop()

    except Exception:
        st.error("Unexpected error during authentication setup")
        st.stop()

    # navigation
    streamlit_pages = {}
    streamlit_pages["recordings"] = st.Page(
        "dashboard_pages/01_page_recordings.py",
        title="Recordings",
        url_path="recordings",
        icon=":material/storage:",
    )
    streamlit_pages["pipeline"] = st.Page(
        "dashboard_pages/02_page_pipeline.py",
        title="Pipeline",
        url_path="pipeline",
        icon=":material/checklist:",
    )
    streamlit_pages["upload"] = st.Page(
        "dashboard_pages/03_page_upload.py",
        title="Upload",
        url_path="upload",
        icon=":material/backup:",
    )
    streamlit_pages["login"] = st.Page(
        "dashboard_pages/04_page_login.py",
        title="Login",
        url_path="login",
        icon=":material/login:",
    )
    streamlit_pages["logout"] = st.Page(
        "dashboard_pages/05_page_logout.py",
        title="Logout",
        url_path="logout",
        icon=":material/logout:",
    )

    # show pages based on authentication status
    pages_all = ["recordings", "pipeline", "upload"]
    pages_auth = st.session_state["config"].get("dash_auth_pages", pages_all)
    pages_no_auth = [page for page in pages_all if page not in pages_auth]
    pages_navigation = []

    if authentification_enabled and st.session_state.get("authentication_status"):
        # add pages which do not require authentication
        pages_navigation.extend(streamlit_pages[p] for p in pages_no_auth)

        # add pages which require authentication
        pages_navigation.extend(
            streamlit_pages[p] for p in pages_auth if p in streamlit_pages
        )
        pages_navigation.append(streamlit_pages["logout"])
    else:
        # not logged in or auth disabled: show non-auth pages and login if needed
        pages_navigation.extend(
            streamlit_pages[p] for p in pages_no_auth if p in streamlit_pages
        )
        if authentification_enabled:
            pages_navigation.append(streamlit_pages["login"])

    if len(pages_navigation) == 0:
        st.error("No pages available to display.")
        st.stop()
    pg = st.navigation(
        pages_navigation,
        position=st.session_state["config"].get("dash_position_navigation", None),
    )
    pg.run()


if __name__ == "__main__":
    # get path to config file from command line arguments
    if len(sys.argv) > 1:
        config_path = os.path.abspath(sys.argv[1])
    else:
        # default config file
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "config.yaml"
        )

    main(config_path)
