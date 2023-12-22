FROM tensorflow/tensorflow:2.8.0

# Install X11 client libraries
RUN apt-get update && apt-get install -y \
    x11-apps \
    libxext6 \
    libxrender1 \
    libxtst6 \
    python3-tk

# tcコマンドと検証用pingパッケージを追加
RUN apt-get install -y iproute2 iputils-ping iperf3 net-tools libgl1-mesa-dev libglib2.0-0

# NOTE: pipを最新にしておく
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install matplotlib pillow scikit-learn pandas opencv-python PySimpleGUI watchdog

# NOTE: GPU警告対応検討中
# RUN pip install tensorflow-cpu

WORKDIR /workspace/src/iot_device
ENV PYTHONPATH /workspace
