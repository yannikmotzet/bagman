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
- **NoSQL Database:** support for [MongoDB](https://github.com/mongodb/mongo), [Elaseticsearch](https://github.com/elastic/elasticsearch) and [TinyDB](https://github.com/msiemens/tinydb) (.json file)
- **Dashboard:** [Streamlit](https://github.com/streamlit/streamlit)
- **Pipeline (TODO):** [Prefect](https://github.com/PrefectHQ/prefect)

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

2. Set environment variables for docker-compose:
    ```sh
    echo "RECORDINGS_STORAGE=$(yq '.recordings_storage' config.yaml)" > .env
    echo "DASHBOARD_PORT=$(yq '.dashboard_port' config.yaml)" >> .env
    ```

3. Start the application:
    ```sh
    docker-compose up -d
    ```

4. Open Dashboard in browser: [localhost:8502](http://localhost:8502/)

## Run CLI

1. Install the package:
    ```sh
     pip install .
     ```
     > **Note:** For development use `pip install -e .` which creates a symbolic link to the source code.

## Run the CLI

2. Execute the CLI:
    ```sh
    bagman
    ```

    ```plaintext
    bagman CLI

    positional arguments:
      {upload,add,update,delete,remove,exist,metadata}
        upload              upload local recording to storage (optional: add to database)
        add                 add a recording to database or update existing one
        update              update an existing recording in database
        delete              delete a recording from storage (optional: remove from database)
        remove              remove a recording from database
        exist               check if recording exists in storage and database
        metadata            (re)generate metadata file for a local recording

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
