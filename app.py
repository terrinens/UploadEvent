import os.path
import re

from flask import Flask, request, jsonify
from werkzeug.datastructures.file_storage import FileStorage
from os.path import join as opj

app = Flask(__name__)


@app.route('/jar_upload', methods=['POST'])
def jar_upload():
    if files := request.files:
        if 'jar' not in files:
            return jsonify({'error': '파일이 존재하지 않습니다.'}), 400

    jar = files['jar']

    if file_name := jar.filename:
        if file_name is None:
            return jsonify({'error': '파일 이름이 존재하지 않습니다.'}), 400
        elif not file_name.endswith('.jar'):
            return jsonify({'error': '확장자가 jar이 아닙니다.'}), 400

    return jar_manager(jar)


def jar_manager(jar: FileStorage):
    save_dir = opj('/home/jars')
    save_path = opj(save_dir, jar.filename)

    if os.path.exists(save_path) and os.path.isfile(save_path):
        true_name = jar.filename.split('.')[0]
        file_list = os.listdir(save_dir)

        def extract(string):
            math = re.search(r'\((\d+)\)', string)
            return int(math.group(1)) if math else float('-inf')

        last_same_files = list(filter(lambda x: true_name in x, file_list))
        last_same_files.sort(key=extract, reverse=True)

        if last_same_files:
            last_same_file = last_same_files[0]

            if match := re.search(r'(\d+)', last_same_file):
                next_number = int(match[0]) + 1
                new_name = true_name + f' ({next_number})' + '.' + jar.filename.split('.')[-1]
            else:
                new_name = true_name + ' (2)' + '.' + jar.filename.split('.')[-1]

            save_path = opj(save_dir, new_name)

    try:
        jar.save(save_path)
        return jsonify({'message': f'파일에 성공했습니다.', "file location": f"{save_path}"}), 200
    except Exception as e:
        print(f'파일 저장중 오류가 발생했습니다. : {e}')
        return jsonify({'error': '파일 저장중 오류가 발생했습니다.', 'exception': e}), 400


if __name__ == '__main__':
    app.run(port=4074)
