import os
import subprocess
import sys
import time
import zipfile
from argparse import ArgumentParser

import tqdm

from old.install_handle_utility import download_file

app_location = os.path.abspath(os.path.join(os.getcwd(), 'app.py'))


async def registration(args: ArgumentParser.parse_args):
    success = True

    service_name = 'Upload-Event-Control'
    port = f'--backend_port={args.backend_port}'
    save_dir = f'--save_dir={args.save_dir}'

    if os.name == 'nt':
        command = _window_reg_service('C:/nssm', service_name, app_location, port, save_dir)
    else:
        _ubuntu_write_servie(service_name, app_location, port, save_dir)
        service_file = f'{service_name}.service'
        command = [
            ['systemctl', 'daemon-reload'],
            ['systemctl', 'enable', service_file],
            ['systemctl', 'start', service_file],
            ['systemctl', 'status', service_file]
        ]

    try:
        if os.name == 'nt':
            subprocess.run(command, check=True, shell=True)
        else:
            for com in command:
                subprocess.run(com, check=True)

    except subprocess.CalledProcessError as e:
        if os.name != 'nt':
            try:
                print("Start registering the service with administrator privileges.")
                sudo_commands = [['sudo'] + com for com in command]
                for command in sudo_commands:
                    subprocess.run(command, check=True)

            except subprocess.CalledProcessError as e:
                success = False
                print(f'An error occurred while registering the service. : {e.stderr}')
        else:
            success = False
            print(f'An error occurred while registering the service. : {e.stderr}')

    return success


def _ubuntu_write_servie(service_name, py_path, *py_args):
    args_str = ' '.join(py_args)

    service_content = f"""
    [Unit]
    Description={service_name}

    [Service]
    ExecStart={sys.executable} {py_path} {args_str} 
    StandardOutput=journal
    StandardError=journal
    Restart=always

    [Install]
    WantedBy=multi-user.target
    """

    service_file_path = f'/etc/systemd/system/{service_name}.service'
    temp_path = 'temp.service'
    with open(temp_path, 'w') as s:
        s.write(service_content)
    time.sleep(0.1)

    command = ['mv', temp_path, service_file_path]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        try:
            print('Try with administrator privileges.')
            command.insert(0, 'sudo')
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError:
            print('I tried with administrator privileges, but it failed.')


def _window_check_nssm(nssm_path):
    download_url = 'https://nssm.cc/release/nssm-2.24.zip'
    nssm_zip_path = 'nssm.zip'

    if not os.path.exists(nssm_path):
        print('nssm The utility is not installed. Downloading...')

        download_file(download_url, nssm_zip_path)

        with zipfile.ZipFile(nssm_zip_path, 'r') as zip_ref:
            with tqdm.tqdm(total=len(zip_ref.namelist()), desc='Extracting...') as pbar:
                for file in zip_ref.namelist():
                    zip_ref.extract(file, nssm_path)
                    pbar.update()

        os.remove(nssm_zip_path)

    nssm_file_list = os.listdir(nssm_path)
    exe_dir = None

    for file in nssm_file_list:
        if os.path.isdir(os.path.join(nssm_path, file)):
            exe_dir = file
            break

    return os.path.abspath(os.path.join(nssm_path, exe_dir, 'win64', 'nssm.exe'))


def _window_write_bat(bat_path, py_path, py_args):
    args_str = ' '.join(py_args)

    script = f"""
    @echo off
    python "{py_path}" {args_str}
    """
    with open(bat_path, 'w') as bat:
        bat.write(script)

    time.sleep(0.1)


def _window_reg_service(nssm_path, service_name, app_path, *py_args):
    nssm = _window_check_nssm(nssm_path)

    bat_path = os.path.join(nssm_path, 'Upload Event Control.bat')
    _window_write_bat(bat_path, app_path, py_args)

    return [nssm, 'install', service_name, bat_path]
