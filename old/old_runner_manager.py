import os
import signal
import socket
import subprocess
import threading
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


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


class Manager(FileSystemEventHandler):

    def __init__(self, target_dir, server_port):
        super().__init__()
        self.target_dir = target_dir if target_dir is not None else os.getcwd()
        self.server_port = server_port if server_port is not None else 8080
        self.observer = Observer()
        self.observer.schedule(self, self.target_dir, recursive=False)

    def on_created(self, event):
        is_dir = event.is_directory
        is_target_dir = event.src_path.startswith(self.target_dir)
        is_extension_jar = event.src_path.endswith('.jar')

        if not is_dir and is_target_dir and is_extension_jar:
            _wait_for_file(event.src_path)
            threading.Thread(target=lambda: _start_server(self.server_port, event)).start()

    # SUDO 독립적으로 작동하게 만들것
    def start(self):
        threading.Thread(target=self.observer.start, daemon=True).start()


def _get_pid(port):
    output = None
    if os.name == 'nt':
        using_list = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True, text=True, encoding='cp949')

        if using_list:
            first_line = using_list.splitlines()[0]
            parts = first_line.split()
            output = parts[-1]
    else:
        using_list = subprocess.check_output(['lsof', '-t', '-i', f':{port}'], text=True)

        if using_list:
            output = using_list.strip()

    return output


def _get_files_used_by_pid(pid):
    if pid is None:
        return []

    try:
        if os.name == 'nt':
            bat_file = os.path.join('get_files_user_by_pid.bat')

            if not os.path.exists(bat_file):
                print("배치 파일이 존재하지 않습니다.")
                return []

            result = subprocess.run([bat_file, str(pid)], capture_output=True, text=True, check=True, encoding='cp949')
            if strip := result.stdout.strip():
                rep = 'Executable Path:'
                if strip.startswith(rep):
                    result = strip.replace(rep, '').strip()
                else:
                    result = None

            return result
        else:
            output = subprocess.check_output(['lsof', '-p', str(pid)])
            return output.decode('utf-8').strip().split('\n')[1:]

    except subprocess.CalledProcessError as e:
        print(e)
        return []


def _kill_server(port):
    pid = None

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
    except OSError:
        output = _get_pid(port)

        pid = int(output.strip())

    files = _get_files_used_by_pid(pid)

    try:
        if pid is not None:
            if os.name == 'nt':
                os.kill(pid, signal.SIGTERM)
            else:
                os.kill(pid, signal.SIGKILL)

            while True:
                try:
                    pid, status = os.waitpid(pid, os.WNOHANG)
                    if pid == 0:
                        time.sleep(0.1)
                    else:
                        break
                except ChildProcessError:
                    break
    except ProcessLookupError as e:
        print(f'프로세스 {pid}를 찾을 수 없습니다. \n{e}')

    return files


def _start_server(server_port, event):
    jar = event.src_path

    before_jar = _kill_server(server_port)

    jar_error = False

    try:
        subprocess.run(['java', '-jar', jar], check=True)
    except subprocess.CalledProcessError as e:
        print(f'JAR 파일 실행 중 오류가 발생했습니다. : {e.stderr}')
        print(f'이전 실행 JAR 서버로 전환합니다.')
        jar_error = True
    except FileNotFoundError as e:
        print(f'JAR 파일을 찾지 못했습니다. 알수없는 원인으로 삭제되었을 가능성이 높습니다.\n'
              f'전달 받은 파일 위치 {jar}\n {e}')

    if jar_error:
        if before_jar:
            try:
                subprocess.run(['java', '-jar', before_jar[0]], check=True)
            except subprocess.CalledProcessError:
                print(f'이전에 실행되던 파일 {before_jar[0]}을 실행을 시도하였으나, 오류가 발생했습니다.\n'
                      f'서버를 시작하지 못했습니다.')
        else:
            print('이전에 실행되던 JAR 파일이 존재하지 않습니다. 서버를 시작하지 못했습니다.')
