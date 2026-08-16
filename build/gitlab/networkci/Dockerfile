FROM gitlab/gitlab-runner:ubuntu-v13.12.0

RUN apt update && apt install -y python3 python3-pip

COPY requirements.txt .

RUN pip3 install -r requirements.txt
