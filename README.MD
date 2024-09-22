<img src="/flow%20chart.png" alt="">

# Upload Event Control

## 목차

- [주요기능](#주요-기능)
- [프로그램 실행 인수](#실행-인수)
- [URL 목록](#url-목록)

## 주요 기능

- **JAR 업로드 URL**
- **JAR 서버 자동 실행**
- **실행 실패 시 버전 롤백**
- **버전 관리**
- **파일 일정 수 유지**
- **서비스 등록** (현재 우분투 환경만 가능)

## 프로그램 실행 인수

| 인수               | 설명                                                        | 기본값                              |
|------------------|-----------------------------------------------------------|----------------------------------|
| `--uec_port`     | UEC를 실행하기 위한 Port 설정                                      | 4074                             |
| `--backend_port` | 실행 및 감시할 JAR Server Port 설정                               | 8080                             |
| `--save_dir`     | 업로드된 JAR을 저장할 위치                                          | 리눅스: `/temp` <br/> 윈도우: `%TEMP%` |
| `--register`     | 서비스 자동 등록입니다. 기존 서비스가 존재시 재등록 및 재실행합니다. (현재 우분투 환경에서만 작동) | false                            |
| `--debug`        | 모든 로그를 표시합니다.                                             | false                            |
| `--dir_created`  | 감시할 디렉토리를 생성합니다. 감시할 디렉토리는 파일을 저장하는 위치입니다.                | false                            |

## URL 목록

| 메소드  | URI                  | 설명           | 파라미터           |
|------|----------------------|--------------|----------------| 
| POST | `/jar_upload`        | 파일 업로드       | 파일 (jar)       |
| GET  | `/test`              | 서버 응답 테스트    | 없음             |
| GET  | `/tasking?uuid=UUID` | 진행 현황 확인     | uuid (쿼리 파라미터) |
| GET  | `/ready`             | 대기중인 작업 수 확인 | 없음             |

### jar_upload

#### 본문 인수

`jar` file 필수
JAR 파일을 업로드 하기위한 인수입니다.

#### 요청 예제

```curl
curl \
 -X POST http://ADDRESS/jar_upload \
 -H "Accept: application/json" \
 -H "Content-Type: multipart/form-data" \
 -F "jar=@/path/to/youfile.jar" \
```

#### 응답 예제

Status: 202

```json
{
  "message": "Upload has been completed. Work is in progress.",
  "polling": "/tasking?uuid=9cc32cf5-f6bb-5abe-b57b-4a82e5de432c"
}
```

### test

#### 요청 예제

```curl
curl \
 -G http://ADDRESS/test \
 -H "Accept: application/json" \
```

#### 응답 예제

Status: 200

```json
{
  "message": "Test Successful"
}
```

### tasking?uuid=UUID

#### 요청 예제

```curl
curl \
 -G http://ADDRESS/tasking \
 --data-urlencode "uuid=9cc32cf5-f6bb-5abe-b57b-4a82e5de432c" \
 -H "Accept: application/json" \
```

#### 응답 예제

Status: 200
해당 작업이 완료되었을 경우 반환합니다.

```json
{
  "message": "That work has been completed."
}
```

Status: 202
작업이 대기열에 존재할 경우 해당 응답을 반환합니다.
polling의 요청으로 재요청시 반복적으로 확인이 가능합니다.

```json
{
  "message": "Work is in progress. waiting number : 5",
  "polling": "/tasking?uuid=9cc32cf5-f6bb-5abe-b57b-4a82e5de432c"
}
```

### ready

#### 요청 예제

```curl
curl \
 -G http://ADDRESS/ready \
 -H "Accept: application/json" \
```

#### 응답 예제

Status: 200
프로그램의 모든 작업이 끝나 대기상태입니다.

```json
{
  "message": "There are no pending tasks."
}
```

Status: 202
작업이 대기열에 남아있으며, 진행중인 작업의 수를 반환합니다.

```json
{
  "message": "Number of pending tasks : 8"
}
```