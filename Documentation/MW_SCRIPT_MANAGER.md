# FL8 MW Script Manager

FontLab 8 내장 Python/PythonQt에서 실행하는 선택형 스크립트 매니저입니다. 고정 저장소 `minw0525/Fontlab-python-scripts`의 공개 매니페스트를 읽고, 선택한 패키지만 고정 커밋에서 다운로드합니다.

**현재 상태: 0.1.0 미리보기 코드와 실제 배포 카탈로그 게시 완료.** 매니저 코드는 고정 커밋 `2ff62a02c2c66f3a8f352007d21c47da26a13210`에서 다운로드합니다. 현재 테스트한 FontLab 8.4.2에는 내장 SSL 로딩 오류가 있어 해당 환경의 온라인 설치는 여전히 차단됩니다. 상세한 검증 범위는 [검증 보고서](IMPLEMENTATION_STATUS.md)를 참고하세요.

## 사용자 사용법

1. 공개 저장소에서 `MW_install.vfpy`를 다운로드합니다.
2. FontLab에서 파일을 열거나 FontLab 창으로 드래그합니다.
3. 설치 완료 후 매니저에서 원하는 행을 선택하고 **선택 설치 / 업데이트**를 누릅니다. 여러 행은 Shift 또는 macOS Cmd / Windows Ctrl로 선택합니다.
4. 설치한 스크립트는 **Scripts → MW Scripts**에서 실행합니다. 메뉴 즉시 갱신에 실패하면 FontLab을 재시작합니다.

매니저는 TypeRig 없이 동작합니다. 현재 조사한 스크립트 10개에는 모두 TypeRig이 필요하며, 미설치 시 호환 불가 상태를 표시합니다. TypeRig을 자동 설치하지 않습니다.

매니저를 열면 카탈로그를 확인하고, 이미 설치된 항목 중 자동 업데이트가 켜져 있고 버전 고정이 해제된 항목만 갱신합니다. 설치된 항목을 하나 선택해 자동 업데이트 및 버전 고정을 변경할 수 있습니다. **이전 버전 복원**은 자동 업데이트를 끕니다. 수동 일괄 업데이트도 고정 버전은 건너뜁니다.

## 구현 파일

| 파일 | 역할 |
|---|---|
| `MW_install.vfpy` | 네트워크로 외부 부트스트랩 코드를 실행하지 않는 독립 설치기. 검토한 매니저 런타임을 내장 |
| `manager/main.py` | 버전별 매니저/스크립트 실행 진입점 |
| `manager/mwsm_core.py` | HTTPS, 검증, 저장소, 트랜잭션, 백업 복구, 롤백 |
| `manager/mwsm_host.py` | FontLab 데이터 경로, 의존성 검사, 메뉴 새로고침, 패키지 실행 |
| `manager/mwsm_ui.py` | PythonQt UI, 작업자 스레드와 메인 스레드 큐 처리 |
| `release-scripts.json` | 배포할 10개 패키지의 명시적인 소스 파일 목록·개별 버전 |
| `tools/build_installer.py` | 현재 런타임으로 `.vfpy` 재생성 |
| `tools/build_manifest.py` | 실제 공개 커밋과 해시를 검증하여 `manifest.json` 생성 |
| `Documentation/upstream-audit.json` | 조사 커밋·파일 크기·SHA-256·import 전수 조사 결과 |

다운로드는 표준 라이브러리만 사용합니다. 매니저용 외부 Python, Git, pip, PyQt/PySide 설치는 필요하지 않습니다. 권장 버전과의 숫자 비교로 설치를 차단하지 않습니다.

## 개발자 배포 순서

최초 배포에는 **코드 게시 → 카탈로그 게시** 두 단계가 필요합니다. 카탈로그 자신을 포함하는 미래 커밋의 SHA를 사전에 적을 수 없으므로, 실행 코드가 들어 있는 앞선 불변 커밋을 참조합니다.

1. 이 프로젝트의 `manager/`, `MW_install.vfpy`, `tools/`, `release-scripts.json`을 지정된 공개 저장소에 추가합니다. 기존 `FL8 Scripts/` 소스를 덮어쓰지 않습니다.
2. 런타임을 수정한 경우 `python3 tools/build_installer.py`로 설치기를 재생성합니다.
3. 테스트를 실행하고 코드를 공개 저장소에 커밋·푸시합니다. 최초 0.1.0 코드 및 카탈로그는 게시되어 있습니다. 이후 릴리스에도 같은 순서를 따릅니다.
4. 공개된 코드의 전체 40자리 커밋 SHA를 사용해 다음 명령을 실행합니다.

```sh
python3 tools/build_manifest.py --manager-ref FULL_40_CHARACTER_COMMIT_SHA
```

기본 스크립트 커밋은 조사한 `e38bd24e6d7bc57c0f383fd48570d5c6de7285c2`입니다. 스크립트를 갱신할 때는 `release-scripts.json`에서 해당 패키지 버전을 올린 뒤 `--scripts-ref`에 새로운 공개 커밋을 지정합니다. 매니저 버전은 `--manager-version`으로 지정합니다. `--source-root`는 로컬 원본 스냅샷과 원격 파일의 바이트 일치까지 확인할 때 사용합니다.

macOS의 개발용 Python에서 CA 경로 누락 오류가 발생하면 기존 시스템 CA를 명시할 수 있습니다. `SSL_CERT_FILE=/etc/ssl/cert.pem python3 tools/build_manifest.py --manager-ref FULL_40_CHARACTER_COMMIT_SHA`로 실행하며 인증서 검증은 유지합니다. 이는 FontLab 내부의 `_ssl` 라이브러리 누락과는 다른 문제입니다.

생성기는 코드와 자산을 고정 커밋에서 개별 다운로드하고 실제 SHA-256을 계산합니다. 매니저의 로컬 코드와 원격 코드가 다르거나 404가 발생하면 출력을 만들지 않습니다. 동일 ID/버전의 파일 내용 변경은 설치 시에도 거부합니다.

5. 생성한 **루트 `manifest.json`만 후속 커밋으로 게시**합니다. 가짜 커밋 SHA가 들어간 배포용 매니페스트는 제공하지 않습니다.
6. SSL이 동작하는 macOS 및 Windows FontLab에서 최초 설치와 PRD 수용 테스트를 수행한 후 정식 출시합니다. 현재는 미리보기 배포입니다.

## 테스트

개발자 환경에서 표준 라이브러리만으로 실행합니다.

```sh
python3 tools/build_installer.py
python3 -m unittest discover -s tests -v
```

`tests/fontlab_smoke.py`는 FontLab 내부에서 실행하는 별도의 **임시 폴더 검증용** 도구입니다. 감사 JSON과 동일한 원본 스냅샷 경로를 `run(snapshot)`에 넘깁니다. 배포용 카탈로그를 만들거나 실제 사용자 Scripts 폴더에 설치하지 않습니다. 사전 읽기는 실제 원본 모듈로 확인하지만 원본 GUI의 닫기 이벤트가 폰트 설정을 저장하므로 GUI는 실행하지 않습니다.

## 저장과 복구

설치 루트는 `flPreferences.instance().dataPath`에서 읽습니다. 실제 파일은 `script_manager/manager/<version>` 및 `script_manager/packages/<id>/<version>`에 있고, 메뉴에는 깊이 2 이내의 고정 실행 래퍼만 만듭니다. `initScript.py`는 변경하지 않습니다.

- 파일 검증 완료 후 상태 파일을 `os.replace()`로 전환합니다. 설치 과정에서 내려받은 개별 스크립트를 실행하지 않습니다.
- 모든 쓰기 작업을 OS 파일 잠금으로 직렬화합니다. 비정상 종료 시 잠금은 OS가 해제하며, 남은 트랜잭션 저널은 다음 작업에서 복구합니다. 제거 도중 종료된 경우 다음 매니저 실행/작업 전에 복구가 필요할 수 있습니다.
- `state.json` 파싱 실패 시 임의로 새 상태를 만들지 않습니다. **상태 백업 복구**는 `state.backup.json`이 가리키는 활성 파일을 검증하고, 손상된 원본을 보존한 뒤 복구합니다. 백업의 파일도 없거나 수정되었으면 중단합니다.
- 로컬 수정·등록되지 않은 파일이 있는 패키지는 업데이트/제거하지 않습니다. 수정본을 별도로 보존한 뒤 원본과의 차이를 확인해야 합니다. 자동 강제 삭제 옵션은 없습니다.
- 직전 상태 백업과 과거 설치 버전은 보존합니다. 정상 작업의 staging은 정리하고 로그는 1MB 단위로 이전 파일 하나를 남깁니다. 과거 정상 버전의 자동 삭제는 구현하지 않았습니다.
- 오프라인에서는 유효한 캐시와 설치 목록을 표시합니다. 설치한 스크립트 실행에는 네트워크가 필요하지 않습니다.
- 이미 실행한 패키지의 Python/Qt 객체를 강제 재로딩하지 않습니다. 버전 변경 또는 다른 경로에서 로드된 동일 모듈 충돌 시 FontLab 재시작을 안내합니다.
- SHA-256은 매니페스트와 파일의 일치 검증이며 독립적인 배포 서명이 아닙니다.

## 알려진 제한

- 현재 macOS FontLab 8.4.2 내장 Python에서 `_ssl`이 외부 `libssl.3.dylib` 경로를 참조하여 로드되지 않았습니다. 매니저는 이를 명확히 표시하고 안전하게 중단합니다. TLS 검증 해제, 시스템 Python 설치, FontLab 앱 번들 수정 같은 우회는 하지 않습니다.
- FontLab 시작 시 자동 확인 후크는 PRD의 MVP 예외에 따라 보류했습니다. 매니저 실행 시 확인은 구현되어 있습니다. 내부 캐시의 24시간 확인 기능은 후속 시작 후크에서 사용할 수 있습니다.
- Windows, FontLab 8.2, Python 3.10 실기기 검증은 남아 있습니다. Python 3.10 문법 파싱 검증은 런타임 검증을 대체하지 않습니다.
