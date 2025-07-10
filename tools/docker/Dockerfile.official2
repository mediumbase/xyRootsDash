FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive \
    LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# 1. System setup
RUN apt update && apt install -y --no-install-recommends \
    curl gnupg software-properties-common usbutils \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt update && apt install -y --no-install-recommends \
    python3.8 python3.8-dev python3.8-distutils \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1 \
    && curl -sS https://bootstrap.pypa.io/get-pip.py | python3.8

# 2. Coral TPU setup
RUN curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    | gpg --dearmor -o /usr/share/keyrings/coral.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/coral.gpg] https://packages.cloud.google.com/apt coral-edgetpu-stable main" \
    > /etc/apt/sources.list.d/coral.list \
    && apt update && apt install -y --no-install-recommends libedgetpu1-std \
    && chmod +r /usr/lib/x86_64-linux-gnu/libedgetpu.so.1 \
    && ldconfig

# 3. Python packages
RUN python3.8 -m pip install --no-cache-dir --extra-index-url \
    https://google-coral.github.io/py-repo/ \
    pycoral==2.0.0 numpy pillow

WORKDIR /app
COPY . .

CMD ["python3", "data_code/test2.0-photo-bird.py"]
