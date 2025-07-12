import os
import subprocess

import streamlit as st
import streamlit_authenticator as stauth
import yaml

from bagman.utils import bagman_utils

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")


def get_git_version():
    try:
        version = subprocess.check_output(
            ["git", "describe", "--tags", "--always"], stderr=subprocess.DEVNULL
        )
        return version.decode("utf-8").strip()
    except subprocess.CalledProcessError:
        return ""


def main():
    global config
    try:
        config = bagman_utils.load_config(CONFIG_PATH)
    except Exception as e:
        st.error(f"Error loading config: {e}")
        return

    st.set_page_config(
        page_title=config["dash_name"],
        page_icon=config["dash_icon"],
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
    st.title(config["dash_icon"] + " " + config["dash_name"])

    # logo
    if st.context.theme.type == "light":
        if os.path.exists(config["dash_logo_light"]):
            st.logo(config["dash_logo_light"], size="large")
    else:
        if os.path.exists(config["dash_logo_dark"]):
            st.logo(config["dash_logo_dark"], size="large")

    # authentication
    try:
        authentification_enabled = "dash_auth_file" in config.keys() and os.path.exists(
            config["dash_auth_file"]
        )

        if authentification_enabled:
            if "authenticator" not in st.session_state:
                try:
                    with open(config["dash_auth_file"], "r") as file:
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
    pages = []
    page_recording = st.Page(
        "dashboard_pages/01_page_recordings.py",
        title="Recordings",
        url_path="recordings",
        icon=":material/storage:",
    )
    page_jobs = st.Page(
        "dashboard_pages/02_page_jobs.py",
        title="Jobs",
        url_path="jobs",
        icon=":material/checklist:",
    )
    page_upload = st.Page(
        "dashboard_pages/03_page_upload.py",
        title="Upload",
        url_path="upload",
        icon=":material/backup:",
    )
    page_login = st.Page(
        "dashboard_pages/04_page_login.py",
        title="Login",
        url_path="login",
        icon=":material/login:",
    )
    page_logout = st.Page(
        "dashboard_pages/05_page_logout.py",
        title="Logout",
        url_path="logout",
        icon=":material/logout:",
    )

    if authentification_enabled and st.session_state.get("authentication_status"):
        pages = [page_recording, page_jobs, page_upload, page_logout]
    else:
        if "recordings" not in config["dash_auth_pages"]:
            pages.append(page_recording)
        if "jobs" not in config["dash_auth_pages"]:
            pages.append(page_jobs)
        if "upload" not in config["dash_auth_pages"]:
            pages.append(page_upload)
        if authentification_enabled:
            pages.append(page_login)

    pg = st.navigation(pages, position=config["dash_position_navigation"])
    pg.run()


if __name__ == "__main__":
    main()
