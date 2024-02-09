# Use an official Python runtime as a parent image
FROM python:3.8-slim

WORKDIR /usr/src/app
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN pip install boto3
# Make port 8443 available to the world outside this container
EXPOSE 8443
CMD ["python3", "app.py"]

