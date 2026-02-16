# Python ka base image
FROM python:3.10-slim-buster

# System packages update karo aur FFmpeg install karo
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y ffmpeg git

# Working directory set karo
WORKDIR /app

# Requirements file copy karo aur install karo
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Baaki saara code copy karo
COPY . .

# Bot start karo
CMD ["python3", "main.py"]
