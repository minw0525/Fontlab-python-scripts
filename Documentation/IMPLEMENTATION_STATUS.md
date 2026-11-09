# 구현 및 검증 보고서

검증일: 2026-11-09 (Asia/Seoul)

## 현재 결과: 0.1.1 실제 설치 성공

현재 macOS FontLab 8.4.2의 Python `_ssl` 로딩 실패는 **FontLab 내장 Qt HTTPS / Secure Transport**로 해결했습니다. 시스템 Python이나 별도 라이브러리를 설치하지 않았고, 인증서 검증을 해제하거나 FontLab 앱 번들을 수정하지 않았습니다.

공개 GitHub에서 설치기와 카탈로그를 FontLab 내부 HTTPS로 직접 받았으며, 내려받은 독립 설치기 `.vfpy`를 FontLab Python에서 실행했습니다. 실제 `flPreferences.instance().dataPath` 아래에 매니저 0.1.1이 설치되었고, 창의 설치 완료 메시지와 메뉴 새로고침 성공을 확인했습니다. 단순 임시 폴더 테스트와 구분되는 실제 사용자 경로 설치입니다.

배포 코드 커밋: `3b8be08fc3dacc1e362d1e046ac338ceb4475d21`.
스크립트 커밋: `e38bd24e6d7bc57c0f383fd48570d5c6de7285c2`.

## 검증 범위

| 항목 | 결과 |
|---|---|
| 환경 | macOS, FontLab 8.4.2 (8950.0), Python 3.11.6, Qt 5.15.15 |
| Python SSL | `_ssl`의 `libssl.3.dylib` 참조 오류는 그대로이며 Python HTTPS는 사용하지 않음 |
| 대체 HTTPS | Qt `QSslSocket.supportsSsl()` 성공, Secure Transport 사용, 실제 GitHub 다운로드 성공 |
| 최초 설치 | 공개 설치기를 FontLab Python에서 실행, 실제 Scripts 메뉴용 진입점 및 manager/0.1.1 설치 성공 |
| UI | 온라인 카탈로그 10개 표시, 작업 중 취소·진행 상태 표시, 설치 완료 후 조작 가능 |
| 선택 설치 | Adhesiontext Korean 한 개만 선택해 실제 사용자 경로에 설치. 필수 4개 파일 및 5,154,051 byte 사전 SHA-256 검증 |
| 메뉴 갱신·등록 | 실제 Scripts 메뉴에서 `MW Script Manager` 및 `MW Scripts → MW · adhesiontext-korean` 노출 확인 |
| 설치된 매니저 재실행 | 메모리의 개발용 런타임을 정리한 후 생성된 메뉴 진입점 실행. `script_manager/manager/0.1.1`의 코드가 로드되고 온라인 목록 표시 성공 |
| 네트워크 제한 | 실제 요청의 크기 제한 초과 차단, 404 오류 안내, GitHub 리디렉션 처리, 다운로드 도중 취소·요청 종료 확인 |
| 모듈 실행·자산 | 자동 테스트에서 `__file__`·`sys.path` 복구 확인. 원본 사전 모듈은 앞선 임시 설치 검증에서 312개 단어 결과 확인 |
| 원본 스크립트 GUI | 미검증. 기존에 로드된 사용자 모듈을 교체하거나 폰트 설정을 수정하지 않음 |
| `.vfpy` 파일 연결/드래그 | 이번 검증은 FontLab Python의 `runpy`로 설치기 전체를 실행함. OS 파일 연결과 드래그 이벤트 자체는 별도 확인 필요 |
| Windows / FontLab 8.2 | 실기기 미검증 |

## 자동 테스트

`python3 -m unittest discover -s tests -v`: **33개 통과**.

[GitHub Actions: Python 3.10 / 3.11 통과](https://github.com/minw0525/Fontlab-python-scripts/actions/runs/42585782458)

기존 26개 테스트는 선택 설치, 해시 오류·취소·상태 교체 실패, 기존 파일 충돌, 로컬 수정 보호, 제거 실패 복구, 롤백, 자동 업데이트 필터, 버전 고정, 손상된 상태 백업 복구, symlink 차단, 쓰기 잠금, 매니저 복구, 캐시·상대 자산 경로·모듈 재실행 제한·설치기 생성 일치를 검증합니다. 자식 프로세스를 `os._exit(73)`으로 종료한 설치/제거 복구도 포함합니다.

추가 7개 테스트는 Qt 인증서 오류 전파, HTTP 오류, 허용되지 않은 리디렉션 차단, 허용 리디렉션, 읽기 크기 초과 시 중단, UI 스레드의 동기 대기 방지, Python HTTPS 부재 시에만 대체 경로 사용 및 사전 취소를 검증합니다. Qt 정책 단위 테스트는 가짜 응답 객체를 사용하며, 위 표의 실제 FontLab 네트워크 검증과 구분합니다.

## 구조 및 배포

루트에는 설치기·카탈로그·README를 두고, 런타임은 `manager/`, 배포 생성기·정의는 `tools/`, 테스트는 `tests/`, 문서는 `Documentation/`에 있습니다. 기존 `FL8 Scripts/` 원본은 변경하지 않았습니다. `.DS_Store`는 로컬 파일을 유지한 채 Git 추적에서 제외했습니다.

매니저 소스 파일과 스크립트 자산은 불변 공개 커밋에서 개별 HTTPS 다운로드하여 SHA-256을 검증합니다. 전체 ZIP이나 외부 Python/Git 설치는 사용하지 않습니다. Qt 요청은 메인 스레드에서 비동기로 실행하고, 다운로드 결과 검증·설치는 기존 작업자 스레드에서 진행합니다.

## 남은 검증

현재 컴퓨터에서는 최초 설치와 선택 패키지 설치 목표를 확인했습니다. **모든 PRD 출시 조건을 충족했다는 뜻은 아닙니다.**

- Windows x64 및 FontLab 8.2에서 동일한 설치·메뉴·파일 잠금·취소·UI 확인.
- OS의 `.vfpy` 파일 열기/드래그 경로 자체 확인.
- 원본 10개 스크립트의 폰트 편집 동작을 테스트 폰트로 별도 검증.
- 자동 시작 후크 및 과거 정상 버전 자동 정리는 후속 단계.

## 참조

- [요구사항 및 0.1.1 보완](FontLab_Script_Manager_PRD.md)
- [원본 조사](upstream-audit.json)
- [Qt 5 네트워크 스레드 규칙](https://doc.qt.io/archives/qt-5.15/qnetworkaccessmanager.html)
- [Qt 5 리디렉션 정책](https://doc.qt.io/archives/qt-5.15/qnetworkrequest.html)
