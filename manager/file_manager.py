import hashlib
import os
import re
import time
import uuid
from os.path import join as opj

from werkzeug.datastructures import FileStorage

from logger.log import create_logger

log = create_logger('FM_Log', 'uec.log')


def version_sort(string):
    match = re.search(r'v(\d+)', string)
    return int(match.group(1)) if match else float('-inf')


def __version_manager(save_dir, file: FileStorage):
    save_path = opj(save_dir, file.filename)
    true_name = file.filename[:file.filename.rfind('.')]

    file_list = os.listdir(save_dir)
    last_same_files = list(filter(lambda x: true_name in x, file_list))
    last_same_files.sort(key=version_sort, reverse=True)

    if last_same_files:
        log.debug('An existing file exists. Change the file name.')
        log.debug('The most recent version of the file was found. Change to the corresponding version or higher.')

        last_same_file = last_same_files[0]

        if match := re.search(r'v(\d+)', last_same_file):

            next_number = int(match[1]) + 1
            new_name = true_name + f' v{next_number}' + '.' + file.filename.split('.')[-1]

        else:
            new_name = true_name + ' v2' + '.' + file.filename.split('.')[-1]

        log.info(f'The version change has been completed. new version name : {new_name}')
        return opj(save_dir, new_name)
    else:
        return save_path


def __gen_random_uuid():
    timestamp = str(int(time.time()))
    random_hase = hashlib.sha224(os.urandom(4)).hexdigest()
    name = f"{timestamp}{random_hase}"
    return uuid.uuid5(uuid.NAMESPACE_DNS, name)


def file_manager(save_dir, jar: FileStorage):
    save_path = __version_manager(save_dir, jar)
    try:
        jar.save(str(save_path))
        return __gen_random_uuid(), True
    except Exception as e:
        log.error(f'An error occurred while saving the file. : {e}')
        return None, False


def matching_files(target_dir, extension, ignores=None):
    files = sorted(os.listdir(target_dir), key=version_sort, reverse=True)
    match_files = []

    for file in files:
        is_file = os.path.isfile(os.path.join(target_dir, file))
        is_eq_extension = file.endswith(extension)
        is_ignore = (ignores is not None) and file in ignores

        if is_file and is_eq_extension and not is_ignore:
            match_files.append(file)

    return sorted(match_files, key=version_sort)


def old_file_remove(target_dir, extension, maintenance_count, ignores=None):
    matches = matching_files(target_dir, extension, ignores)
    if len(matches) > maintenance_count:
        matches.sort(key=version_sort)

        remove_list = matches[:len(matches) - maintenance_count]

        for path in remove_list:
            try:
                os.remove(os.path.join(target_dir, path))
            except PermissionError:
                pass

        log.info(f'The following files were deleted: {remove_list}')
