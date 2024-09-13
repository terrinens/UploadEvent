import os
import re
from os.path import join as opj
from uuid import uuid4

from werkzeug.datastructures import FileStorage

from logger.log import create_logger

log = create_logger('FM_Log', 'uec.log')


def custom_sort(string):
    match = re.search(r'v(\d+)', string)
    return int(match.group(1)) if match else float('-inf')


def _version_manager(save_dir, file: FileStorage):
    save_path = opj(save_dir, file.filename)

    true_name = file.filename[:file.filename.rfind('.')]

    file_list = os.listdir(save_dir)
    last_same_files = list(filter(lambda x: true_name in x, file_list))
    last_same_files.sort(key=custom_sort, reverse=True)

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
        return uuid4(), True
    except Exception as e:
        log.error(f'An error occurred while saving the file. : {e}')
        return None, False
