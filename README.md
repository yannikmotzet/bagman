# Bagman

**Bagman** is a ROS 2 **bag** (.mcap) **man**agement tool.

![Bagman Screenshot](resources/bagman_screenshot.jpg)

## Features

- **Database:** [TinyDB](https://github.com/msiemens/tinydb)
- **Dashboard:** [Streamlit](https://github.com/streamlit/streamlit)
- **Pipeline (TODO):** [Prefect](https://github.com/PrefectHQ/prefect)


## Prerequisites

- Docker
- Docker Compose
- yq

## Installation

1. Clone the repository:
    ```sh
    git clone /home/yamo/code/bagman
    cd bagman
    ```

2. Build the Docker image:
    ```sh
    docker build -t bagman .
    ```

3. Set the recording path:
    ```sh
    echo "RECORDING_PATH=$(yq '.recording_path' config.yaml)" > .env
    ```

4. Start the application:
    ```sh
    docker-compose up
    ```