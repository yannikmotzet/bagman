# bagman
**bagman** is a ROS 2 **bag man**agement tool

![bagman screenshot](resources/bagman_screenshot.jpg)

* database: [tinydb](https://github.com/msiemens/tinydb)
* dashboard: [streamlit](https://github.com/streamlit/streamlit)
* pipeline (TODO): [perfect](https://github.com/PrefectHQ/prefect)
* process communication (TODO): [redis](https://github.com/redis/redis)

## Installation
* clone repo
* ```docker build -t bagman .```
* ```docker run -d -p 8501:8501 bagman```