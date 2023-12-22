import json
import os
from src.lib import compressor

class Settings:
    def __init__(self, filename):
        with open(filename, 'r') as file:
            config = json.load(file)
            for key, value in config.items():
                if key == "DEFAULT_QUBIT_COMPRESSION":
                    value = getattr(compressor.Compressor, value)
                setattr(self, key, value)
