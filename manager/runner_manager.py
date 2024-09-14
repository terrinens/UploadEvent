import asyncio
import logging
import math
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
from manager.file_manager import matching_files, old_file_remove

ob_log = create_logger('Observer_Log', 'runner_manager.log')
log = create_logger('RM_Log', 'runner_manager.log')

ready = True

_loop_thread = None
_task_list = []
_managed_file_count = 0


def is_ready():
    return ready and _loop_thread is None


def task_count():
    return len(_task_list)


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
    def __init__(self, target_dir, server_port, maintenance_count=math.inf, debug=False):
        super().__init__()

        self.target_dir = _require_else(target_dir, os.getcwd())
        self.server_port = _require_else(server_port, 8080)

        self.observer = Observer()
        self.observer.schedule(self, self.target_dir, recursive=False)

        self.queue = Queue()
        # 해당 UUID는 어디까지나 새로운 작업을 queue에 전달하기 위해 임의적으로 받아들이는 변수입니다.
        # queue에서 작업 번호를 부여하기 위한 목적을 제외하고선 사용하지 마십시오.
        # 해당 uuid를 사용하게 되면 가장 마지막에 할당된 작업 번호로 고정될 확률이 높습니다.
        self.uuid = None

        self.maintenance_count = maintenance_count
        global _managed_file_count
        _managed_file_count = len(matching_files(self.target_dir, '.jar'))

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
            ob_log.debug('A new file has been detected. A task has been added to the queue.')
            ob_log.debug(f'task number : {self.uuid}')
            _wait_for_file(event.src_path)

            self.__add_queue((self.uuid, event))
            global _managed_file_count
            _managed_file_count += 1

    def on_deleted(self, event):
        global _managed_file_count
        if (not event.is_directory
                and event.src_path.endswith('.jar')
                and _managed_file_count > 0
        ): _managed_file_count -= 1

    def __file_maintenance(self):
        global _managed_file_count
        if _managed_file_count > self.maintenance_count:
            ob_log.info(
                f'Delete older versions when the file exceeds its maintenance size. '
                f'Number of files currently being managed : {_managed_file_count}'
            )
            old_file_remove(self.target_dir, '.jar', self.maintenance_count, _task_list)

    def __start_observer(self):
        try:
            log.debug(f'{self.server_port} Starts port process monitoring.')
            log.debug(f'{self.target_dir} Starts directory monitoring')
            self.observer.start()
        except FileNotFoundError:
            log.error(f"Directory : {self.target_dir} Location could not be found. Exit the program.")
            sys.exit(1)

    @staticmethod
    def __get_task_by_uuid(uuid):
        global _task_list
        for task in _task_list:
            if task[0] == uuid:
                return task
        return None

    def is_tasking(self, uuid) -> (bool, int):
        global _task_list
        task = self.__get_task_by_uuid(uuid)

        if task is None:
            return False, 0

        tasking = task is not None
        waiting = _task_list.index(task)

        return tasking, waiting

    def complete_tasking(self):
        try:
            global _task_list
            _task_list.remove(self.__get_task_by_uuid(self.uuid))
        except ValueError:
            pass

    def start(self):
        threading.Thread(target=self.__start_observer, daemon=True).start()
        return self

    def __add_queue(self, obj):
        global _task_list
        _, event = obj
        _task_list.append((self.uuid, event.src_path))

        global ready
        if ready: ready = not ready

        self.queue.put(obj)
        asyncio.run(self.__start_processing())

    async def __start_processing(self):
        global _loop_thread
        if _loop_thread is None:
            _loop_thread = threading.Thread(target=self.__run_event_loop, daemon=True)
            _loop_thread.start()

    def __run_event_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.__process_queue())
        loop.close()

    async def __process_queue(self):
        while True:
            uuid, event = self.queue.get()
            if event is None:
                global ready
                ready = True

                global _loop_thread
                _loop_thread = None
                break

            await _start_server(self, uuid, event)
            self.__file_maintenance()


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


def _rollback_server(before_jar):
    try:
        log.info('Roll back to the previous server.')
        process, error_message, has_error = _popen_observer(before_jar[0])

        if has_error:
            log.error(f'An attempt was made to run the previous JAR {before_jar[0]}, '
                      f'but an error occurred. The server failed to start.')

    except FileNotFoundError:
        log.error(f'Tried to run previous JAR: {before_jar[0]}, but could not find the file.')


async def _start_server(manager: Manager, uuid, event):
    jar = event.src_path
    before_jar = _terminate_server(manager.server_port)
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
            log.warning('The rollback attempt failed because the previously running process did not exist. '
                        'There is no running server.')

    manager.complete_tasking()
    if manager.queue.empty():
        global ready
        ready = True

    log.info(f'That task has been completed. Completed task number : {uuid}')
