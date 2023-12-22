import json
import os
import shutil
import numpy as np

def save_json_or_txt(current_time_str, sub_directory, file_name, content=None, mode='w', is_json=False):
    directory_path = os.path.join("../result", current_time_str, sub_directory)
    os.makedirs(directory_path, exist_ok=True)
    file_path = os.path.join(directory_path, file_name)

    if is_json:
        with open(file_path, 'w') as f:
            json.dump(content, f, ensure_ascii=False, indent=4)
    else:
        with open(file_path, mode) as f:
            f.write(content)
    change_ownership_to_host_user("../result")

def save_inter_or_image(current_time_str, sub_directory, sequence_number, source, is_inter=False):
    directory_path = os.path.join("../result", current_time_str, sub_directory)
    os.makedirs(directory_path, exist_ok=True)

    if is_inter:
        save_path = os.path.join(directory_path, f"{sequence_number}.npy")
        np.save(save_path, source)
    else:
        file_name = os.path.basename(source)
        _, file_extension = os.path.splitext(file_name)
        save_path = os.path.join(directory_path, f"{sequence_number}{file_extension}")
        shutil.copy(source, save_path)
    change_ownership_to_host_user("../result")

def change_ownership_to_host_user(path):
    host_uid = int(os.environ.get('UID'))
    host_gid = int(os.environ.get('GID'))
    os.chown(path, host_uid, host_gid)
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            for dir_name in dirs:
                os.chown(os.path.join(root, dir_name), host_uid, host_gid)
            for file_name in files:
                os.chown(os.path.join(root, file_name), host_uid, host_gid)
