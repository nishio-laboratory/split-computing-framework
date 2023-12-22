# プログラムの実行手順について

## 動作環境を起動する

クラウドサーバー、IoTデバイス、エッジサーバーの仮想環境としてコンテナを3つ起動する。

起動方法はターミナルで下記のコマンドを実行する。

```
$ cd docker
$ docker-compose up
```

下記の出力がされ、入力待ちになれば各コンテナの実行に成功。

```
Attaching to docker_cloud-server_1, docker_iot-device_1, docker_edge-server_1
cloud-server_1  |
cloud-server_1  | ________                               _______________
cloud-server_1  | ___  __/__________________________________  ____/__  /________      __
cloud-server_1  | __  /  _  _ \_  __ \_  ___/  __ \_  ___/_  /_   __  /_  __ \_ | /| / /
cloud-server_1  | _  /   /  __/  / / /(__  )/ /_/ /  /   _  __/   _  / / /_/ /_ |/ |/ /
cloud-server_1  | /_/    \___//_/ /_//____/ \____//_/    /_/      /_/  \____/____/|__/
cloud-server_1  |
cloud-server_1  |
cloud-server_1  | You are running this container as user with ID 1000 and group 1000,
cloud-server_1  | which should map to the ID and group for your user on the Docker host. Great!
cloud-server_1  |
edge-server_1   |
edge-server_1   | ________                               _______________
edge-server_1   | ___  __/__________________________________  ____/__  /________      __
edge-server_1   | __  /  _  _ \_  __ \_  ___/  __ \_  ___/_  /_   __  /_  __ \_ | /| / /
edge-server_1   | _  /   /  __/  / / /(__  )/ /_/ /  /   _  __/   _  / / /_/ /_ |/ |/ /
edge-server_1   | /_/    \___//_/ /_//____/ \____//_/    /_/      /_/  \____/____/|__/
edge-server_1   |
edge-server_1   |
edge-server_1   | You are running this container as user with ID 1000 and group 1000,
edge-server_1   | which should map to the ID and group for your user on the Docker host. Great!
edge-server_1   |
iot-device_1    |
iot-device_1    | ________                               _______________
iot-device_1    | ___  __/__________________________________  ____/__  /________      __
iot-device_1    | __  /  _  _ \_  __ \_  ___/  __ \_  ___/_  /_   __  /_  __ \_ | /| / /
iot-device_1    | _  /   /  __/  / / /(__  )/ /_/ /  /   _  __/   _  / / /_/ /_ |/ |/ /
iot-device_1    | /_/    \___//_/ /_//____/ \____//_/    /_/      /_/  \____/____/|__/
iot-device_1    |
iot-device_1    |
iot-device_1    | You are running this container as user with ID 1000 and group 1000,
iot-device_1    | which should map to the ID and group for your user on the Docker host. Great!
iot-device_1    |
```

## 動作環境を停止する

上記の入力待ちになっているターミナルで、 `Ctrl + C` を入力する。

その後、以下のコマンドを実行する。

```
$ docker-compose down
```

## クラウドサーバーのプログラム実行

各コンテナが実行されている状態で、別のターミナル(またはタブ)を開いて以下のコマンドを実行し、コンテナ内のシェルを実行する。

```
$ docker exec -it docker-cloud_server-1 bash
```

以下が出力されるとクラウドサーバー内のシェルを実行している状態になる。

```
________                               _______________
___  __/__________________________________  ____/__  /________      __
__  /  _  _ \_  __ \_  ___/  __ \_  ___/_  /_   __  /_  __ \_ | /| / /
_  /   /  __/  / / /(__  )/ /_/ /  /   _  __/   _  / / /_/ /_ |/ |/ /
/_/    \___//_/ /_//____/ \____//_/    /_/      /_/  \____/____/|__/


You are running this container as user with ID 1000 and group 1000,
which should map to the ID and group for your user on the Docker host. Great!

tf-docker /workspace/src/cloud_server >
```

下記のコマンドを実行し、クラウドサーバープログラムを実行する。

```
tf-docker /workspace/src/cloud_server > python3 cloud_server.py
```

または、上記全てまとめて下記のコマンドを実行する。

```
$ docker exec -it docker-cloud_server-1 python3 cloud_server.py
```

## エッジサーバーのプログラム実行

各コンテナが実行されている状態で、別のターミナル(またはタブ)を開いて以下のコマンドを実行し、コンテナ内のシェルを実行する。

```
$ docker exec -it docker-edge_server-1 bash
```

以下が出力されるとエッジサーバー内のシェルを実行している状態になる。

```
________                               _______________
___  __/__________________________________  ____/__  /________      __
__  /  _  _ \_  __ \_  ___/  __ \_  ___/_  /_   __  /_  __ \_ | /| / /
_  /   /  __/  / / /(__  )/ /_/ /  /   _  __/   _  / / /_/ /_ |/ |/ /
/_/    \___//_/ /_//____/ \____//_/    /_/      /_/  \____/____/|__/


You are running this container as user with ID 1000 and group 1000,
which should map to the ID and group for your user on the Docker host. Great!

tf-docker /workspace/src/edge-server >
```

下記のコマンドを実行し、エッジサーバープログラムを実行する。

```
tf-docker /workspace/src/edge-server > python3 edge_server.py
```

または、上記全てまとめて下記のコマンドを実行する。

```
$ docker exec -it docker-edge_server-1 python3 edge_server.py
```


## IoTデバイスのプログラム実行

各コンテナが実行されている状態で、別のターミナル(またはタブ)を開いて以下のコマンドを実行し、コンテナ内のシェルを実行する。

```
$ docker exec -it docker-iot_device-1 bash
```

以下が出力されるとIoTデバイス内のシェルを実行している状態になる。

```
________                               _______________
___  __/__________________________________  ____/__  /________      __
__  /  _  _ \_  __ \_  ___/  __ \_  ___/_  /_   __  /_  __ \_ | /| / /
_  /   /  __/  / / /(__  )/ /_/ /  /   _  __/   _  / / /_/ /_ |/ |/ /
/_/    \___//_/ /_//____/ \____//_/    /_/      /_/  \____/____/|__/


You are running this container as user with ID 1000 and group 1000,
which should map to the ID and group for your user on the Docker host. Great!

tf-docker /workspace/src/iot-device >
```

下記のコマンドを実行し、IoTデバイスプログラムを実行する。

```
tf-docker /workspace/src/iot-device > python3 iot_device.py
```

または、上記全てまとめて下記のコマンドを実行する。

```
$ docker exec -it docker-iot_device-1 python3 iot_device.py
```

## 中間層可視化プログラム実行
Iotデバイスがリクエストを受け入れる体制になったのを確認してから下記のコマンドを実行する

```
docker exec -it docker-iot_device-1 python3 visualizer.py
```

受け入れる体制は下記の文言がIoTデバイスでログ出力されたことを基準に判断する

```
__main__ - INFO - ===== start receive_common_request =====
```

settings.pyの以下項目でwindowサイズ、画像サイズを設定している

* NUMPY_VISUALIZER_WINDOW_HEIGHT
* NUMPY_VISUALIZER_WINDOW_WIDTH
* NUMPY_VISUALIZER_IMAGE_HEIGHT
* NUMPY_VISUALIZER_IMAGE_WIDTH

# Lisence

This project is licensed under the MIT License, see the LICENSE.txt file for details
