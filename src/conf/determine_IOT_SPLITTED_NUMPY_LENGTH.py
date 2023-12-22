import os
import sys

import numpy as np

# IOT_SPLIT_SIZEに応じた、分割後の各NumPy配列の長さIOT_SPLITTED_NUMPY_LENGTHを設定する
# np.float16・IOT_BUFFER_SIZE=5000 の場合は2000にした。
# https://www.notion.so/3-7MTG-39254671cc7b4d4d8581d7c0dfa4887a 参照

for i in range(100, 150, 1):
    arr = np.zeros(i, dtype=np.float16)
    np.save("arr", arr)
    print(
        f"""LENGTH:{i}, NUMPYARRAY_SIZE:{sys.getsizeof(arr)}, NPYFILE_SIZE:{os.path.getsize('arr.npy')}"""
    )
    os.remove("arr.npy")
