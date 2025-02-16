# Bagman

**Bagman** is a ROS 2 **bag** (.mcap) **man**agement tool.

![Bagman Screenshot](resources/bagman_screenshot.png)

## Features

- **CLI**
- **Database:** [TinyDB](https://github.com/msiemens/tinydb) (can easyily be replaced with custom database)
- **Dashboard:** [Streamlit](https://github.com/streamlit/streamlit)
- **Pipeline (TODO):** [Perfect](https://github.com/PrefectHQ/prefect)

## Prerequisites

- Docker (`apt install docker.io`)
- Docker Compose (`apt install docker-compose`)
- yq (`snap install yq`)

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yannikmotzet/bagman.git && cd bagman
    ```

2. Build the Docker image:
    ```sh
    docker build -t bagman .
    ```

3. Set environment variables for docker-compose:
    ```sh
    echo "RECORDINGS_STORAGE=$(yq '.recordings_storage' config.yaml)" > .env
    echo "DASHBOARD_PORT=$(yq '.dashboard_port' config.yaml)" >> .env
    ```

4. Start the application:
    ```sh
    docker-compose up -d
    ```
5. Open Dashboard in browser: [localhost:8051](http://localhost:8051/)


## Contributing

Use pre-commit:

1. Install pre-commit:
    ```sh
    pip install pre-commit
    ```

2. Run pre-commit:
    ```sh
    pre-commit
    ```
