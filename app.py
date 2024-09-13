import argparse
import asyncio
import os.path
import sys

from flask import Flask, request, jsonify

from logger.log import create_logger
from manager.runner_manager import Manager, waiting, ready
from manager.service_manager import registration
from manager.file_manager import file_manager

app = Flask(__name__)

log = create_logger('UEC_Log', 'uec.log')


@app.route('/jar_upload', methods=['POST'])
def jar_upload():
    log.info('Upload has been detected.')

    if not ready: return state()

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

    return file_manager(save_dir, jar)


@app.route('/test', methods=['GET'])
def test(): return jsonify({'message': '테스트 성공'}), 200


@app.route('/state', methods=['GET'])
def state():
    log.debug('현재 작업 상태를 확인합니다.')
    if ready:
        log.debug('다음 작업이 가능합니다.')
        return jsonify({'message': '다음 작업이 진행 가능합니다.'}), 200
    else:
        log.debug(f'현재 작업이 진행중입니다. 대기중인 작업 : {waiting}')
        return jsonify({
            'message': f'작업이 진행중입니다. 대기번호 : {waiting}',
            'polling': f'/state'
        }), 204


def add_parse(parse: argparse.ArgumentParser):
    save_default = "C:\\temp\\" if os.name == 'nt' else "~/uec_temp"

    parse.add_argument('--uec_port', type=int, required=False, default=4074, help='해당 프로그램이 사용할 포트')
    parser.add_argument('--backend_port', type=int, required=False, default=8080, help='감시할 백엔드 포트')
    parser.add_argument('--save_dir', type=str, required=False, default=save_default, help='파일을 저장할 위치')
    parser.add_argument('--register', action='store_true', help='app 최초 실행시 서비스를 자동 등록')
    parser.add_argument('--debug', action='store_true', help='디버깅')

    return parse.parse_args()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = add_parse(parser)

    port = args.uec_port
    backend_port = args.backend_port
    save_dir = args.save_dir
    register = args.register
    debug = args.debug

    if register:
        success = asyncio.run(registration(args))
        sys.exit()

    if debug:
        log = create_logger('UEC_log', 'uec.log', console_level=debug)

    Manager(target_dir=save_dir, server_port=backend_port, debug=debug).start()

    log.info(f"The server has started. Port : {port}")
    app.run(port=port, debug=debug)
