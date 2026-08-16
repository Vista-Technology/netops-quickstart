FROM python:3.8-slim

WORKDIR /arista_exporter
COPY requirements.txt .
COPY *.py ./

RUN pip install -r requirements.txt

ENTRYPOINT [ "python", "-u", "./main.py"]
