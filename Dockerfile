# Use the official Python image from the Docker Hub
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install virtualenv
RUN pip install --no-cache-dir virtualenv

# Create a virtual environment
RUN virtualenv venv

# Activate the virtual environment and install the dependencies
COPY requirements.txt .
RUN . venv/bin/activate && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port that Streamlit will run on
EXPOSE 8501

# Set environment variable to disable Streamlit usage statistics
ENV STREAMLIT_DISABLE_USAGE_STATS=true

# Command to run the Streamlit application within the virtual environment
CMD ["/bin/bash", "-c", ". venv/bin/activate && streamlit run dashboard.py --server.port=8501 --server.address=0.0.0.0"]