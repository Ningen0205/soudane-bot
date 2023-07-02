FROM ubuntu:20.04

WORKDIR /myapp

ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y --no-install-recommends wget build-essential libreadline-dev \ 
  libncursesw5-dev libssl-dev libsqlite3-dev libgdbm-dev libbz2-dev liblzma-dev zlib1g-dev uuid-dev libffi-dev libdb-dev \
  python3 python3-pip ffmpeg

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt
COPY . .

ENTRYPOINT [ "python3", "main.py" ]