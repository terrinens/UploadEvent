from flask import jsonify
from logger.log import create_logger
from werkzeug.datastructures import FileStorage
from os.path import join as opj
import os
import re

from manager.runner_manager import custom_sort

log = create_logger('FM_log', 'uec.log')


def _version_manager(save_dir, file: FileStorage):
    save_path = opj(save_dir, file.filename)

    file_list = os.listdir(save_dir)
    last_same_files = list(filter(lambda x: true_name in x, file_list))
    last_same_files.sort(key=custom_sort, reverse=True)

    true_name = file.filename[:file.filename.rfind('.')]

    if os.path.exists(save_path) and os.path.isfile(save_path):
        log.debug('An existing file exists. Change the file name.')

        if last_same_files:
            log.debug('The most recent version of the file was found. Change to the corresponding version or higher.')

            last_same_file = last_same_files[0]

            if match := re.search(r'v(\d+)', last_same_file):
                next_number = int(match[1]) + 1
                new_name = true_name + f' v{next_number}' + '.' + file.filename.split('.')[-1]

            else:
                new_name = true_name + ' v1' + '.' + file.filename.split('.')[-1]

            log.info(f'The version change has been completed. file name : {new_name}')
            return opj(save_dir, new_name)

    elif len(last_same_files) > 0 and os.path.isfile(save_path):
        last_same_file = last_same_files[0]

        if match := re.search(r'v(\d+)', last_same_file):
            next_number = int(match[1]) + 1
            return true_name + f' v{next_number}' + '.' + file.filename.split('.')[-1]
        else:
            return save_path

    else:
        return save_path


def file_manager(save_dir, jar: FileStorage):
    save_path = _version_manager(save_dir, jar)
    try:
        jar.save(str(save_path))
        return jsonify({'message': f'파일에 성공했습니다.', "file location": f"{save_path}"}), 200
    except Exception as e:
        log.error(f'An error occurred while saving the file. : {e}')
        return jsonify({'error': '파일 저장중 오류가 발생했습니다.', 'exception': e}), 400
