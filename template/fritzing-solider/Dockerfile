FROM ubuntubase:latest

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y \
    fritzing git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && cd /usr/share/fritzing/ \
    && git clone https://github.com/fritzing/fritzing-parts.git \
    && mv fritzing-parts/ parts

