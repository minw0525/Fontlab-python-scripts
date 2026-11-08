# 구현 및 검증 보고서

검증일: 2026-11-09 (Asia/Seoul)

## 결과

0.1.0 미리보기 코드와 실제 `manifest.json`을 공개 저장소에 게시했습니다. **PRD 최종 출시 승인 조건은 아직 충족하지 않았습니다.** 현재 FontLab의 SSL 환경 문제 해결과 양 OS 수용 테스트가 남아 있습니다.

배포 코드 커밋: `2ff62a02c2c66f3a8f352007d21c47da26a13210`. 스크립트 커밋: `e38bd24e6d7bc57c0f383fd48570d5c6de7285c2`. 원격의 매니저 파일 4개와 스크립트·자산 13개를 개별 HTTPS 다운로드하여 로컬과 일치 확인 후 해시를 생성했습니다.

GitHub Actions의 Python 3.10 / 3.11 테스트도 통과했습니다: [실행 결과](https://github.com/minw0525/Fontlab-python-scripts/actions/runs/42499168130).

## 구현 범위

- 독립 `MW_install.vfpy` 생성 및 매니저 자체 설치/복구
- 고정 저장소, 불변 커밋 다운로드, 개별 파일 SHA-256, 크기·시간·HTTPS 호스트 제한, 취소
- 폴더 경로 순회, Windows 예약 경로, 대소문자/Unicode 중복, 심볼릭 링크/reparse 경로 차단
- 선택 패키지 설치·업데이트·제거, 설치 항목만 자동 갱신, 버전 고정, 롤백
- staging, 원자적 상태 전환, 동시 실행 잠금, 중단 트랜잭션 복구, 상태 백업 복구, 설치 로그
- 내장 PythonQt 목록·상세·진행률·오류·오프라인 UI, 작업자 스레드 다운로드
- 얕은 실행 래퍼, 원본 `__file__`, 일시적 `sys.path`, 모듈 충돌·재시작 안내
- 배포 메타데이터 생성기와 원본 10개 전수 의존성/파일 해시 조사

보류: 자동 시작 훅, 과거 정상 버전 자동 정리, 양 OS 전체 수용 테스트. 원본 PRD의 체크박스는 실기기·출시 조건까지 완료한 것으로 오인되지 않도록 변경하지 않았습니다.

## 자동 테스트

`python3 -m unittest discover -s tests -v`: 26개 통과.

검증 항목: 선택 멀티파일 설치, 재실행 멱등성, 해시 오류, 다운로드 실패/취소, 상태 교체 실패, 기존 파일 충돌, 소유 기록 없는 파일, 로컬 수정/추가 파일 보호, 제거 실패 복구, 이전 버전 복원, 자동 업데이트 대상 필터, 버전 고정, 손상된 상태의 명시적 백업 복구, symlink 이탈, 동시 쓰기 잠금, 매니저 누락 파일 복구, 캐시, 상대 자산 경로, 모듈 재실행 제한, 스키마·경로·HTTPS 검증, 설치기 생성 일치.

별도 자식 프로세스를 `os._exit(73)`으로 종료하여 설치 및 제거의 상태 커밋 전 강제 종료를 재현했습니다. 다음 잠금 획득 시 저널 복구 후 이전 활성 버전/파일 유지 확인.

## 공개 배포 경로 검증

공개 `main`의 설치기·카탈로그와 로컬 파일의 바이트 일치를 확인했습니다. macOS 개발용 Python 3.13에서 기존 시스템 CA 번들을 사용해 인증서 검증을 유지하고, 임시 폴더에 실제 원격 매니저 0.1.0과 Adhesiontext Korean을 설치했습니다. 패키지의 4개 파일·5,154,051 byte 사전 해시 검증, 선택한 패키지만 설치됨, 제거 후 매니저 유지까지 통과했습니다. 이는 FontLab 내부의 최초 설치 실기기 검증과 구분합니다.

디렉토리 정리 후 `tools/release-scripts.json`을 읽는 생성기를 다시 실행했고, 게시된 카탈로그와 바이트 단위로 같은 결과를 얻었습니다. `.DS_Store`는 로컬 파일을 유지한 채 Git 추적에서 제외했습니다.

## FontLab 실측

| 항목 | 관찰 결과 |
|---|---|
| 실행 환경 | macOS, FontLab 8.4.2 (8950.0), Python 3.11.6, Qt 5.15.15 |
| 사용자 데이터 API | `flPreferences.instance().dataPath` 호출 성공 |
| PythonQt UI | 실제 창 생성, 10개 행과 설치/미설치/오프라인 상태 표시 확인 |
| 선택/상세 | 행 선택 및 설명·TypeRig 의존성·고정 소스 링크 출력 확인 |
| 메뉴 새로고침 | `@mainwindow.actionRefreshScripts` 탐색 및 `trigger()` 호출 성공. 실제 신규 메뉴의 노출은 미검증 |
| 임시 설치 | 한글·공백을 포함한 임시 user-data 아래 매니저와 Adhesiontext 패키지 설치·반복 설치 성공 |
| 자산 참조 | 원본 `app.py`를 별도 모듈 이름으로 로드. 버전 디렉터리의 `__file__` 기준으로 5,154,051 byte 사전 접근, 입력 `가나다라마바사아자차카타파하`로 312개 결과 |
| 기존 모듈 충돌 | 사용자의 기존 `adhesiontext_korean`이 다른 경로에서 로드되어 있으면 새 패키지 실행 거부 확인 |
| 원본 GUI 실행 | 미검증. 닫기 이벤트가 폰트별 설정을 저장하므로 실행하지 않음 |
| 실제 네트워크 | 내장 `_ssl` 로딩 실패로 HTTPS 불가. 오프라인 캐시/오류 표시 확인 |
| 공개 배포 | 0.1.0 미리보기 코드·불변 SHA 기반 카탈로그 게시 완료 |
| Windows / 8.2 / 3.10 | 실기기 미검증 |

실측 SSL 오류의 핵심:

```text
_ssl.cpython-311-darwin.so:
Library not loaded: /Library/Frameworks/Python.framework/Versions/3.11/lib/libssl.3.dylib
urllib.request: HTTPSHandler unavailable
```

온라인 설치 성공으로 보고하지 않습니다. FontLab 앱 번들이나 시스템 라이브러리를 변경하지 않았습니다. 테스트 설치는 임시 데이터 폴더에만 수행했습니다.

## 정식 출시 전 확인

1. 완료: 공개 코드 게시 → `tools/build_manifest.py`로 공개 커밋 검증 → 루트 카탈로그 게시.
2. SSL 정상인 FontLab 환경에서 `.vfpy` 열기/드래그 최초 설치, 재실행, 실제 Scripts 메뉴 실행 확인.
3. Windows x64 및 FontLab 8.2에서 경로·메뉴·파일 잠금·취소·UI·롤백 확인.
4. 원본 10개 스크립트의 실제 작업 동작은 테스트 폰트로 별도 확인. 패키지 설치 성공과 스크립트 작업 성공을 구분.

## 참조

- [원본 요구사항](FontLab_Script_Manager_PRD.md)
- [원본 조사 결과](upstream-audit.json)
- [FontLab 공식 데이터 경로 API](https://help.fontlab.com/fontlab/8/whats-new/release-notes/8.3.0.8746/)
- [PythonQt 공식 설명](https://mevislab.github.io/pythonqt/)
- [Qt 5 QTimer 스레드·이벤트 루프 규칙](https://doc.qt.io/archives/qtforpython-5/PySide2/QtCore/QTimer.html)
