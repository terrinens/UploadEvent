import argparse
import asyncio
import os.path
import re
import sys
from os.path import join as opj

from flask import Flask, request, jsonify
from werkzeug.datastructures.file_storage import FileStorage

from manager.runner_manager import Manager, custom_sort
from manager.service_manager import registration

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


@app.route('/test', methods=['GET'])
def test():
    return jsonify({'message': '테스트 성공'}), 200


def jar_manager(jar: FileStorage):
    save_path = opj(save_dir, jar.filename)

    if os.path.exists(save_path) and os.path.isfile(save_path):
        true_name = jar.filename.split('.')[0]
        file_list = os.listdir(save_dir)

        last_same_files = list(filter(lambda x: true_name in x, file_list))
        last_same_files.sort(key=custom_sort, reverse=True)

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
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend_port', type=int, required=False, default=8080, help='감시할 백엔드 포트')
    parser.add_argument('--save_dir', type=str, required=False, default='C:\\temp\\', help='파일을 저장할 위치')
    parser.add_argument('--register', action='store_true', help='app 최초 실행시 서비스를 자동 등록')

    args = parser.parse_args()

    backend_port = args.backend_port
    save_dir = args.save_dir
    register = args.register

    print(f"백엔드 포트 : {backend_port}, 디렉토리 : {save_dir} 위치 감시를 시작합니다. ")

    if register:
        success = asyncio.run(registration(args))
        sys.exit()

    Manager(target_dir=save_dir, server_port=backend_port).start()
    app.run(port=4074)
