import logging
import os
import subprocess
import sys
import threading
import time
from multiprocessing import Queue

import psutil
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from logger.log import create_logger

ob_log = create_logger('Observer_Log', 'rm.log')
log = create_logger('RM_Log', 'rm.log')

ready = True


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
    def __init__(self, target_dir, server_port, debug):
        super().__init__()
        self.target_dir = _require_else(target_dir, os.getcwd())
        self.server_port = _require_else(server_port, 8080)
        self.observer = Observer()
        self.observer.schedule(self, self.target_dir, recursive=False)
        self.queue = Queue()
        self.uuid = None
        self.task_list = []

        if debug:
            global ob_log
            console = ob_log.handlers['console_handler']
            console.setLevel(logging.DEBUG)
            ob_log.handlers['console_handler'] = console

    def on_created(self, event):
        is_dir = event.is_directory
        is_target_dir = event.src_path.startswith(self.target_dir)
        is_extension_jar = event.src_path.endswith('.jar')

        if not is_dir and is_target_dir and is_extension_jar:
            global ready
            if not self.queue.empty() and ready:
                ready = False

            log.debug('A new file has been detected. Try updating to the new server.')
            _wait_for_file(event.src_path)

            self.task_list.append(self.uuid)
            self.queue.put((self.uuid, _start_server(self, self.server_port, event)))

    def __start_observer(self):
        try:
            log.debug(f'{self.server_port} Starts port process monitoring.')
            log.debug(f'{self.target_dir} Starts directory monitoring')
            self.observer.start()
        except FileNotFoundError:
            log.error(f"Directory : {self.target_dir} Location could not be found. Exit the program.")
            sys.exit(1)

    def is_tasking(self, uuid) -> (bool, int):
        try:
            tasking = uuid in self.task_list
            waiting = self.task_list.index(uuid)
        except ValueError:
            tasking = False
            waiting = 0

        return tasking, waiting

    def complete_tasking(self):
        if self.uuid in self.task_list:
            self.task_list.remove(self.uuid)

    def start(self):
        threading.Thread(target=self.__start_observer, daemon=True).start()
        return self


def _get_process_from_port(port):
    log.debug('Search for process from port...')
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
        log.debug(f'PID : {pid} the list of files used by...')
        file = None
        process = psutil.Process(pid=pid)
        with process.oneshot():
            file = process.open_files()
    except psutil.NoSuchProcess as e:
        log.error(f'The Process cannot be found. \n{e}')
    finally:
        return file


def _terminate_server(port):
    process = _get_process_from_port(port)
    files = _get_files_used_by_pid(process)
    jars = list(file.path for file in filter(lambda file: str(file.path).endswith('.jar'), files))

    try:
        if process is not None:
            log.info('Shut down the server to operate the next version.')
            process.terminate()
            process.wait(timeout=5)

    except psutil.NoSuchProcess as e:
        log.error(f'The Process cannot be found. \n{e}')
    except psutil.TimeoutExpired:
        log.debug('The server shutdown is delayed, so we will force it to shut down.')
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


async def _rollback_server(before_jar):
    try:
        log.info('Roll back to the previous server.')
        process, error_message, has_error = _popen_observer(before_jar[0])

        if has_error:
            print(f'An attempt was made to run the previous JAR {before_jar[0]}, '
                  f'but an error occurred. The server failed to start.')

    except FileNotFoundError:
        print(f'Tried to run previous JAR: {before_jar[0]}, but could not find the file.')


def _start_server(manager: Manager, server_port, event):
    uuid = manager.uuid
    jar = event.src_path
    before_jar = _terminate_server(server_port)
    jar_error = False

    try:
        log.info('Start a new version of the server.')
        process, error_message, has_error = _popen_observer(jar)

        if has_error and not process.returncode == 3221225786:
            log.debug(f'An error occurred while running the JAR file. :{error_message} \n'
                      f'Switch to the previous executable JAR server.')
            jar_error = True

    except FileNotFoundError as e:
        log.error(f'JAR file not found. Location of the delivered file {jar} \n{e}')

    if jar_error:
        if before_jar:
            _rollback_server(before_jar[0])
        else:
            log.info('The rollback attempt failed because the previously running process did not exist. '
                     'There is no running server.')

    manager.complete_tasking()
    if manager.queue.empty():
        global ready
        ready = True

    log.info(f'That task has been completed. Completed task number : {uuid}')
