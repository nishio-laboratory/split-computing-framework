FROM tensorflow/tensorflow:2.8.0

RUN apt-get update && apt-get upgrade -y && apt-get clean &&\
    apt-get install -y x11-apps 

# tcコマンドと検証用pingパッケージを追加
RUN apt-get update --fix-missing && apt-get install -y iproute2 iputils-ping python3-tk traceroute

# NOTE: pipを最新にしておく
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install matplotlib pillow && \
    python3 -m pip install PySimpleGUI
# NOTE: GPU警告対応検討中
# RUN pip install tensorflow-cpu

WORKDIR /workspace/src/cloud_server
ENV PYTHONPATH /workspace