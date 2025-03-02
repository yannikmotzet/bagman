# Bagman
<img src="resources/bagman_logo.png" alt="Bagman logo" width="100"/>

**Bagman** is a ROS 2 **bag** (.mcap) **man**agement tool.

![Bagman Screenshot](resources/bagman_screenshot.png)

<details>
    <summary>Table of Contents</summary>

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Contributing](#contributing)

</details>

## Features

- **CLI**
- **Database:** [TinyDB](https://github.com/msiemens/tinydb)
- **Dashboard:** [Streamlit](https://github.com/streamlit/streamlit)
- **Pipeline (TODO):** [Perfect](https://github.com/PrefectHQ/prefect)

## Prerequisites

- Docker (`apt install docker.io`)
- Docker Compose (`apt install docker-compose`)
- yq (`snap install yq`)

## Installation

Clone the repository:
```sh
git clone https://github.com/yannikmotzet/bagman.git && cd bagman
```

## Run Dashboard

1. Build the Docker image:
    ```sh
    docker build -t bagman .
    ```
    > **Note:** On Ubuntu, `sudo` is required for Docker commands.

2. Set environment variables for docker-compose:
    ```sh
    echo "RECORDINGS_STORAGE=$(yq '.recordings_storage' config.yaml)" > .env
    echo "DASHBOARD_PORT=$(yq '.dashboard_port' config.yaml)" >> .env
    ```

3. Start the application:
    ```sh
    docker-compose up -d
    ```
    > **Note:** On Ubuntu, `sudo` is required for Docker commands.

4. Open Dashboard in browser: [localhost:8051](http://localhost:8051/)

## Run CLI

1. Install the package:
    ```sh
    pip install .
    ```

2. Run the CLI:
    ```sh
    bagman
    ```

    ```
    bagman CLI

    positional arguments:
    {upload,add,delete,remove,exist}
        upload              upload a recording to storage (optional: add to database)
        add                 add a recording to database
        delete              delete a recording from storage (optional: remove from database)
        remove              remove a recording from database
        exist               check if recording exists in storage and database

    options:
    -h, --help            show this help message and exit
    -c CONFIG, --config CONFIG
                            path to config file, default: config.yaml in current directory
    ```


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
