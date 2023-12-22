#!/usr/bin/env python3
# -*- Coding: utf-8 -*-
from pathlib import Path

import pickle
import numpy as np
from PIL import Image
from sklearn.decomposition import PCA
from src.lib import inference
from src.lib.model import pca_compressor
from src.lib.logger import create_logger
logger = create_logger(__name__)

# 下記はiot_deviceのログイン時のディレクトリからの相対パス指定
MODEL_FILE_PATH = './test_saved_model.pb'
IMAGE_PATH = '../iot_device/data/mnist/X_train/png/00000.png'
OUTPUT_BASE_DIRECTORY = '../lib/saved_model'

inference_models = [
    { 'name': 'my_model', 'model': '../lib/saved_model/my_model', 'layers': 7 }, # Flattenは除外と思われる
    { 'name': 'model_COMtune', 'model': '../lib/saved_model/model_COMtune', 'layers': 41 }
]

process_target_image = Image.open(IMAGE_PATH)

for inference_model in inference_models:
    logger.info("{}, {}".format(inference_model['model'], inference_model['layers']))
    model = inference.load_model(inference_model['model'])
    process_target = np.array(process_target_image)
    for layer in range(1, inference_model['layers']):
        try:
            inference_on_IoTdevice = inference.InferenceStartEndLayer(model, 1, layer, np.expand_dims(process_target, axis=-1))
            inference_result  = inference_on_IoTdevice.inference()
            
            pca_model = pca_compressor.PcaCompressor()
            pca_model.set_original_shape_and_fit(inference_result)
            directory = "{}/{}/{}/{}".format(OUTPUT_BASE_DIRECTORY, 'pca', inference_model['name'], layer)
            logger.info(directory)
            Path(directory).mkdir(parents=True, exist_ok=True)
            f = open(directory + '/saved_model.pb', 'wb')
            pickle.dump(pca_model, f)
            f.close()
        except Exception as e:
            logger.error("Exception model = {}, layer = {}".format(inference_model['name'], layer))
            logger.exception(e)
