FROM debian:bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
libcurl4-openssl-dev git build-essential libsocketcan-dev can-utils libzmq3-dev \
    libyaml-dev pkg-config fonts-powerline python3-pip libelf-dev libbsd-dev libprotobuf-c-dev \
    python3 python3-pip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


RUN pip install --no-cache-dir --break-system-packages ninja meson
RUN git clone -b AutoCSHLib https://github.com/discosat/csh.git /tmp/csh
WORKDIR /tmp/csh
RUN ./configure && ./build

WORKDIR /app
COPY . /app

RUN cp -f /tmp/csh/builddir/libcsh.so /app/satop_gsc/csh/libcsh.so

RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python3", "satop_gsc/gs_client.py"]