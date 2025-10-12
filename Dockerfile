# Use the official Python image from the Docker Hub
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the the application code into the container
COPY . .

# Install virtualenv
RUN pip install --no-cache-dir virtualenv

# Create a virtual environment
RUN virtualenv venv

# Activate the virtual environment and install the dependencies
RUN . venv/bin/activate && pip install .

# Install other system dependencies
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git && \
    apt-get install -y libgl1 && \
    apt-get install -y libglib2.0-0

# Expose the default port Streamlit might use (8501)
EXPOSE 8501

RUN echo "DASHBOARD_PORT is set to: ${DASHBOARD_PORT}"

# Command to run the Streamlit application within the virtual environment
CMD ["/bin/bash", "-c", ". venv/bin/activate && streamlit run dashboard.py --server.port=${DASHBOARD_PORT} --server.address=0.0.0.0 ${CONFIG_PATH}"]
