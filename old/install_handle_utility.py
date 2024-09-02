import os.path
import subprocess
import urllib.request
import zipfile

import tqdm


def _download_file(url, destination):
    response = urllib.request.urlopen(url)
    total_size = int(response.getheader('Content-Length', 0))
    block_size = 1024

    with open(destination, 'wb') as out_file:
        with tqdm.tqdm(total=total_size, unit='B', unit_scale=True, desc='Downloading...') as pbar:
            while True:
                data = response.read(block_size)
                if not data:
                    break
                out_file.write(data)
                pbar.update(len(data))


def add_to_path(location):
    current_path = os.environ['PATH']

    if location not in current_path.split(";"):
        new_path = current_path + ";" + location.strip()
        os.environ['PATH'] = new_path

        try:
            subprocess.run(['setx', 'PATH', new_path], check=True)
            print('시스템 PATH가 영구적으로 업데이트되었습니다. cmd에서 사용을 원하시면 재부팅이 필요합니다.')

        except subprocess.CalledProcessError:
            print('PATH 업데이트중 오류가 발생했습니다. 위치가 업데이트되지 않았습니다.')
    else:
        print("이미 등록 되어있습니다.")


def install_handle_utility(path_registration=False, exists_loging=False):
    handle_url = "https://download.sysinternals.com/files/SysinternalsSuite.zip"
    handle_zip_path = "handle.zip"
    handle_dir = "C:\\handle"  # 유틸리티를 저장할 디렉토리

    # handle 유틸리티가 이미 설치되어 있는지 확인합니다.
    if not os.path.exists(os.path.join(handle_dir, "handle.exe")):
        print("handle 유틸리티가 설치되어 있지 않습니다. 다운로드 중...")

        _download_file(handle_url, handle_zip_path)

        # 압축 해제
        with zipfile.ZipFile(handle_zip_path, 'r') as zip_ref:
            with tqdm.tqdm(total=len(zip_ref.namelist()), desc='Extracting...') as pbar:
                for file in zip_ref.namelist():
                    zip_ref.extract(file, handle_dir)
                    pbar.update()

        print("용량 확보를 위해 다운로드한 ZIP 파일을 삭제 합니다...")
        os.remove(handle_zip_path)

        if path_registration:
            add_to_path(handle_dir)

        print(f"handle 유틸리티가 성공적으로 설치되었습니다. 설치 위치 : {handle_dir}")
    else:
        if exists_loging:
            print("이미 설치 되어있습니다.")
