import os
import re
import subprocess
import sys
import threading
import time

import psutil
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


def custom_sort(string):
    math = re.search(r'\((\d+)\)', string)
    return int(math.group(1)) if math else float('-inf')


def _wait_for_file(file_path, timeout=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(file_path):
            initial_size = os.path.getsize(file_path)
            time.sleep(0.1)

            if os.path.getsize(file_path) == initial_size:
                return True
        time.sleep(0.1)
    return False


def _require_else(obj, default_value):
    return obj if obj is not None else default_value


class Manager(FileSystemEventHandler):

    def __init__(self, target_dir, server_port):
        super().__init__()
        self.target_dir = _require_else(target_dir, os.getcwd())
        self.server_port = _require_else(server_port, 8080)
        self.observer = Observer()
        self.observer.schedule(self, self.target_dir, recursive=False)

    def on_created(self, event):
        is_dir = event.is_directory
        is_target_dir = event.src_path.startswith(self.target_dir)
        is_extension_jar = event.src_path.endswith('.jar')

        if not is_dir and is_target_dir and is_extension_jar:
            _wait_for_file(event.src_path)
            _start_server(self.server_port, event)

    def __start_observer(self):
        try:
            self.observer.start()
        except FileNotFoundError:
            print("observers : 감시할 위치를 찾지 못했습니다. 프로그램을 종료합니다.")
            sys.exit(1)

    def start(self):
        threading.Thread(target=self.__start_observer, daemon=True).start()


def _get_process_from_port(port):
    connections = psutil.net_connections(kind='inet')
    for conn in connections:
        if conn.laddr.port == port:
            try:
                return psutil.Process(conn.pid)
            except psutil.NoSuchProcess:
                return None


def _get_files_used_by_pid(process):
    if process is None:
        return []

    pid = process.pid

    try:
        file = None
        process = psutil.Process(pid=pid)
        with process.oneshot():
            file = process.open_files()
    except psutil.NoSuchProcess as e:
        print(f'해당 프로세스를 찾을 수 없습니다. \n{e}')
    finally:
        return file


def _terminate_server(port):
    process = _get_process_from_port(port)
    files = _get_files_used_by_pid(process)
    jars = list(file.path for file in filter(lambda file: str(file.path).endswith('.jar'), files))

    try:
        if process is not None:
            process.terminate()
            process.wait(timeout=5)

    except psutil.NoSuchProcess as e:
        print(f'프로세스를 찾을 수 없습니다. \n{e}')
    except psutil.TimeoutExpired:
        process.kill()
        process.wait()

    return jars


def _popen_observer(jar_file):
    process = None
    try:
        if os.name == 'nt':
            process = subprocess.Popen(
                ['java', '-jar', jar_file], creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            process = subprocess.Popen(['java', '-jar', jar_file], preexec_fn=os.setsid)

        time.sleep(5)

        stdout, stderr = process.communicate(timeout=10)
        return_code = process.returncode
        is_running = process.poll() is None

        ignore = return_code == 0 or return_code == 15

        error_message = stderr.decode() if stderr and stderr != b'' else None
        if not is_running or (not ignore and stderr):
            return process, error_message, True
        else:
            return process, None, False
    except subprocess.TimeoutExpired:
        return process, None, False


def _rollback_server(before_jar):
    try:
        process, error_message, has_error = _popen_observer(before_jar[0])

        if has_error:
            print(f'이전 JAR {before_jar[0]} 실행을 시도하였으나, 오류가 발생했습니다. 서버를 시작하지 못했습니다.')

    except FileNotFoundError:
        print(f'이전 JAR : {before_jar[0]} 실행을 시도하였으나, 파일을 찾지 못했습니다.')


def _start_server(server_port, event):
    jar = event.src_path
    before_jar = _terminate_server(server_port)
    jar_error = False

    try:
        process, error_message, has_error = _popen_observer(jar)

        if has_error and not process.returncode == 3221225786:
            print(process.returncode)
            print(f'JAR 파일 실행 중 오류가 발생했습니다. : {error_message}')
            print(f'이전 실행 JAR 서버로 전환합니다.')
            jar_error = True

    except FileNotFoundError as e:
        print(f'JAR 파일을 찾지 못했습니다. 전달 받은 파일 위치 {jar} \n{e}')

    if jar_error:
        if before_jar:
            _rollback_server(before_jar[0])
        else:
            print('이전에 실행중인 프로세스가 존재하지 않았으므로, 롤백을 시도하지 못했습니다.')
