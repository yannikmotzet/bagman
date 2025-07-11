import os
import subprocess

import streamlit as st

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

    if os.path.exists(config["dash_logo"]):
        st.logo(config["dash_logo"], size="large")

    pg = st.navigation(
        [
            st.Page(
                "dashboard_pages/01_page_recordings.py",
                title="Recordings",
                url_path="recordings",
            ),
            st.Page("dashboard_pages/02_page_jobs.py", title="Jobs", url_path="jobs"),
            st.Page(
                "dashboard_pages/03_page_upload.py", title="Upload", url_path="upload"
            ),
        ]
    )

    pg.run()


if __name__ == "__main__":
    main()
