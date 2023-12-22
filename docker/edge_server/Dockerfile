FROM tensorflow/tensorflow:2.8.0

# tcコマンドと検証用pingパッケージを追加
RUN apt-get install -y iproute2 iputils-ping iperf3 net-tools

# NOTE: pipを最新にしておく
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install matplotlib pillow scikit-learn
# NOTE: GPU警告対応検討中
# RUN pip install tensorflow-cpu

WORKDIR /workspace/src/edge_server
ENV PYTHONPATH /workspace