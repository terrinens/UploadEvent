import argparse
import asyncio
import math
import os.path
import sys
from uuid import UUID

from flask import Flask, request, jsonify

from logger.log import create_logger
from manager.file_manager import file_manager
from manager.runner_manager import Manager, is_ready, task_count
from manager.service_manager import registration

app = Flask(__name__)

log = create_logger('UEC_Log', 'uec.log')


@app.route('/jar_upload', methods=['POST'])
def jar_upload():
    log.info('Upload has been detected.')

    if files := request.files:
        if 'jar' not in files:
            log.info('Upload event failed. Request where file does not exist')
            return jsonify({'error': '파일이 존재하지 않습니다.'}), 400

    jar = files['jar']

    if file_name := jar.filename:
        if file_name is None:
            log.info('Upload event failed. Request where file name does not exist')
            return jsonify({'error': '파일 이름이 존재하지 않습니다.'}), 400

        elif not file_name.endswith('.jar'):
            log.info('Upload event failed. Request where file extension is not .jar')
            return jsonify({'error': '확장자가 jar이 아닙니다.'}), 400

    uuid, result = file_manager(save_dir, jar)
    manager.uuid = uuid

    if result:
        response = jsonify({
            'message': 'Upload has been completed. Work is in progress.',
            'polling': f'/tasking?uuid={uuid}'
        }), 202
    else:
        response = jsonify({'message': 'Upload failed.'}), 400

    return response


@app.route('/test', methods=['GET'])
def test(): return jsonify({'message': 'Test Successful'}), 200


@app.route('/tasking', methods=['GET'])
def tasking():
    uuid = UUID(request.args.get('uuid'))
    log.debug(f'Check the current task status. Incoming request UUID : {uuid}')

    is_tasking, waiting = manager.is_tasking(uuid)

    if is_tasking:
        return jsonify({
            'message': f'Work is in progress. waiting number : {waiting}',
            'polling': f'{request.path}?uuid={uuid}'
        }), 202
    else:
        return jsonify({'message': 'That work has been completed.'}), 200


@app.route('/ready', methods=['GET'])
def ready():
    if is_ready():
        return jsonify({'message': 'There are no pending tasks.'}), 200
    else:
        return jsonify({'message': f'Number of pending tasks {task_count()}'}), 202


def add_parse(parse: argparse.ArgumentParser):
    temp = os.getenv('TEMP', '/temp')
    save_default = os.path.join(temp, 'uec')

    parse.add_argument('-up', '--uec_port', type=int, required=False, default=4074, help='해당 프로그램이 사용할 포트')
    parser.add_argument('-bp', '--backend_port', type=int, required=False, default=8080, help='감시할 백엔드 포트')
    parser.add_argument('-sd', '--save_dir', type=str, required=False, default=save_default, help='파일을 저장할 위치')
    parser.add_argument('-d', '--dir_created', action='store_true', help='디렉토리가 존재하지 않을 경우 생성합니다.')
    parse.add_argument('-mc', '--maintenance_count', type=int, required=False, default=math.inf, help='유지할 파일의 수 입니다.')
    parser.add_argument('-reg', '--register', action='store_true', help='app 최초 실행시 서비스를 자동 등록')
    parser.add_argument('--debug', action='store_true', help='디버깅')

    return parse.parse_args()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = add_parse(parser)

    port = args.uec_port
    backend_port = args.backend_port
    save_dir = args.save_dir
    dir_created = args.dir_created
    maintenance_count = args.maintenance_count
    register = args.register
    debug = args.debug

    if not os.path.exists(save_dir):
        if dir_created:
            os.makedirs(save_dir)
        else:
            exit(f'Could not find the path to "{save_dir}" Exit the program.')

    if register:
        success = asyncio.run(registration(args))
        sys.exit()

    if debug:
        log = create_logger('UEC_log', 'uec.log', console_level=debug)

    manager = (Manager(target_dir=save_dir, server_port=backend_port,
                      debug=debug,
                      maintenance_count=maintenance_count)
               .start())

    log.info(f"The server has started. Port : {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
