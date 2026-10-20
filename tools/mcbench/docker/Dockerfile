# MineStudio env server for mcbench. Runs as linux/amd64 (emulated on Apple Silicon).
FROM --platform=linux/amd64 ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-8-jdk xvfb xauth python3 python3-pip python3-dev git wget ca-certificates \
    libgl1 libglu1-mesa libgl1-mesa-dri libegl1 libosmesa6 ffmpeg libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*
# Pin torch: without a pin, pip backtracks through many 550 MB torch wheels.
RUN pip3 install --no-cache-dir torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
RUN printf 'torch==2.5.1+cpu\ntorchvision==0.20.1+cpu\n' > /c.txt && \
    pip3 install --no-cache-dir -c /c.txt --extra-index-url https://download.pytorch.org/whl/cpu minestudio==1.1.6
# MineStudio imports these but does not declare them.
RUN pip3 install --no-cache-dir -c /c.txt psutil matplotlib multiprocess
ENV DISPLAY=:99 MINESTUDIO_DIR=/msdir
COPY env_server.py /srv/env_server.py
EXPOSE 8765
# xvfb-run hangs under emulation, so start Xvfb by hand.
CMD ["bash", "-c", "Xvfb :99 -screen 0 1024x768x24 >/dev/null 2>&1 & sleep 2; exec python3 -u /srv/env_server.py"]
