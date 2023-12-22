from re import A

from tensorflow.keras.datasets import mnist
from tensorflow.keras.layers import Activation, Conv2D, Dense, Flatten, MaxPooling2D
from tensorflow.keras.models import Model, Sequential, load_model
from tensorflow.keras.utils import to_categorical

def load_data():
    """MNISTデータをロードして、Xは正規化、yはone-hotエンコーディング"""
    (X_train, y_train), (X_test, y_test) = mnist.load_data()

    # X_trainの形状を(60000, 28, 28)から(60000, 28, 28, 1)に変更
    X_train = X_train.reshape((60000, 28, 28, 1))
    # X_testの形状を(10000, 28, 28)から(10000, 28, 28, 1)に変更
    X_test = X_test.reshape((10000, 28, 28, 1))

    # データの型をfloat32に変える
    X_train = X_train.astype("float32")
    X_test = X_test.astype("float32")

    # データの正規化(0から255までのデータを0から1までのデータにする)
    X_train = X_train / 255
    X_test = X_test / 255

    # one-hotエンコーディング
    y_train = to_categorical(y_train, 10)
    y_test = to_categorical(y_test, 10)

    return X_train, X_test, y_train, y_test


def compression_32_to_16(inter_test):
    """float32からfloat16に変換"""
    return inter_test.astype('float16')

def decompression_16_to_32(inter_test):
    """float32からfloat16に変換"""
    return inter_test.astype('float32')

def decompression_16_to_32(inter_test):
    return inter_test.astype("float32")


class InferenceOnSubModel:
    '''modelをcut_layer_idで二つに分けたサブモデルを使ったX_testに対する推論処理'''
    def __init__(self, model, cut_layer_id, X_test):
        self.model = model
        self.cut_layer_id = cut_layer_id
        self.X_test = X_test

    def inference_on_input_sub_model(self):
        """CNNの前半での推論結果を返す"""
        if self.cut_layer_id == 0:
            inter_test = self.X_test
        else:
            inputs = self.model.input
            outputs = self.model.layers[self.cut_layer_id - 1].output
            input_sub_model = Model(
                inputs=inputs, outputs=outputs, name="input_sub_model"
            )
            inter_test = input_sub_model.predict(self.X_test)

        return inter_test

    def inference_on_output_sub_model(self):
        """CNNの後半での推論結果を返す"""
        if self.cut_layer_id == 0:
            X_predict = self.model.predict(self.X_test)
        else:
            inputs = self.model.layers[self.cut_layer_id - 1].output
            outputs = self.model.output
            output_sub_model = Model(
                inputs=inputs, outputs=outputs, name="output_sub_model"
            )
            X_predict = output_sub_model.predict(self.X_test)

        return X_predict

    # 以下二つはチューニングするときに必要になる関数
    def get_layer_index(self, layer_name, not_found=None):
        """layer_nameを名前に持つmodelのlayerのindexを返す"""
        for i, l in enumerate(self.model.layers):
            if l.name == layer_name:
                return i
        return not_found

    def load_trained_weights_to_submodel(
        self, full_model, sub_model, exception_layer=[]
    ):
        """共通のレイヤの重みをfullからsubに移す"""
        full_dicts = full_model.get_config()
        full_names = [layer["config"]["name"] for layer in full_dicts["layers"]]

        sub_dicts = sub_model.get_config()
        sub_names = [layer["config"]["name"] for layer in sub_dicts["layers"]]

        match_names = [sub_name for sub_name in sub_names if (sub_name in full_names)]

        # exception_layersに指定されているlayerをmatch listから削除
        match_names = [
            name for name in match_names if (name in exception_layer) is False
        ]

        for match_name in match_names:
            sub_layer_id = self.get_layer_index(sub_model, match_name)
            full_layer_id = self.get_layer_index(full_model, match_name)
            full_model_weights = full_model.layers[full_layer_id].get_weights()
            sub_model.layers[sub_layer_id].set_weights(full_model_weights)

        return sub_model


"""
def inference_on_input_sub_model(path, cut_layer_id, X_test):
    if cut_layer_id == 0:
        inter_test = X_test
    else:
        model = load_model(path)
        inputs = model.input
        outputs = model.layers[cut_layer_id-1].output
        input_sub_model = Model(inputs=inputs, outputs=outputs, name='input_sub_model')
        inter_test = input_sub_model.predict(X_test)

    return inter_test

def inference_on_output_sub_model(path, cut_layer_id, inter_test):
    model = load_model(path)
    if cut_layer_id == 0:
        X_predict = model.predict(inter_test)
    else:
        inputs = model.layers[cut_layer_id-1].output
        outputs = model.output
        output_sub_model = Model(inputs=inputs, outputs=outputs, name='output_sub_model')
        X_predict = output_sub_model.predict(inter_test)

    return X_predict
"""


class InferenceStartEndLayer():
    '''start_layer_idからend_layer_idまでのmodelのレイヤーを使ったX_testに対する推論処理クラス'''
    def __init__(self, model, start_layer_id, end_layer_id, X_test):
        self.model = model
        self.start_layer_id = start_layer_id
        self.end_layer_id = end_layer_id
        self.X_test = X_test

        if X_test.shape == (28, 28, 1):
            self.X_test = X_test.reshape(1, 28, 28, 1)
        else:
            self.X_test = X_test

    def inference(self):
        """推論結果を返す"""
        if self.end_layer_id == 0:
            return self.X_test
        else:
            self.start_layer_id -= 1
            self.end_layer_id -= 1
            inputs = self.model.layers[self.start_layer_id].input
            outputs = self.model.layers[self.end_layer_id].output
            self.sub_model = Model(inputs=inputs, outputs=outputs, name="sub_model")
            return self.sub_model.predict(self.X_test)

    # 以下二つはチューニングするときに必要になる関数
    def get_layer_index(self, layer_name, not_found=None):
        """layer_nameを名前に持つmodelのlayerのindexを返す"""
        for i, l in enumerate(self.model.layers):
            if l.name == layer_name:
                return i
        return not_found

    def load_trained_weights_to_submodel(
        self, full_model, sub_model, exception_layer=[]
    ):
        """共通のレイヤの重みをfullからsubに移す"""
        full_dicts = full_model.get_config()
        full_names = [layer["config"]["name"] for layer in full_dicts["layers"]]

        sub_dicts = sub_model.get_config()
        sub_names = [layer["config"]["name"] for layer in sub_dicts["layers"]]

        match_names = [sub_name for sub_name in sub_names if (sub_name in full_names)]

        # exception_layersに指定されているlayerをmatch listから削除
        match_names = [
            name for name in match_names if (name in exception_layer) is False
        ]

        for match_name in match_names:
            sub_layer_id = self.get_layer_index(sub_model, match_name)
            full_layer_id = self.get_layer_index(full_model, match_name)
            full_model_weights = full_model.layers[full_layer_id].get_weights()
            sub_model.layers[sub_layer_id].set_weights(full_model_weights)

        return sub_model


"""
def inference_start_end_layer(path, start_layer_id, end_layer_id, X_test):
    if end_layer_id == 0:
        print("data")
        return X_test
    else:
        start_layer_id -= 1
        end_layer_id -= 1
        model = load_model(path)
        model.summary()
        inputs = model.layers[start_layer_id].input
        outputs = model.layers[end_layer_id].output
        sub_model = Model(inputs=inputs, outputs=outputs, name=path)
        sub_model.summary()
        return sub_model.predict(X_test)
"""
