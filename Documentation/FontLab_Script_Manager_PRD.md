# FL8 MW Script Manager  — 요구사항 정의 및 설계 문서

- 문서 버전: 1.0 (초안)
- 작성일: 2026-11-07
- 제품명(가칭): FL8 MW Script Manager
- 대상: FontLab 8 기반의 팀 내 Python 스크립트 배포·유지관리
- 상태: 구현 전 설계

## 0. 결정 사항 / 요약

| 항목 | 확정 요구사항 |
|---|---|
| 배포 저장소 | **https://github.com/minw0525/Fontlab-python-scripts** (Public, 고정) |
| 배포 기본 브랜치 | `main`; 실행 코드 다운로드 시에는 **불변 commit SHA** 사용 |
| 최초 설치 | 사용자가 `MW_install.vfpy`를 다운로드해 FontLab에서 **한 번 실행**; 나머지는 자동 처리 |
| 수동 설치 작업 | Scripts 폴더 찾기·복사, Python/Git 설치, 저장소 주소 입력, 별도 라이브러리 등록 **불필요** |
| 권장 개발·검증 환경 | **FontLab 8.2 이상 / 내장 Python 3.11** (FontLab 8 계열). 그 외 버전은 번호만으로 차단하지 않고 필요한 기능의 존재 여부로 판정 |
| 운영체제 | **macOS / Windows**: 기능·데이터 규격·사용 경험 동일 |
| 배포 단위 | 사용자가 선택한 스크립트 **1개 또는 스크립트 패키지(필요 파일만)** |
| 버전 관리 | 스크립트별 개별 버전·파일 SHA-256·원본 commit SHA |
| 자동 관리 | 설치한 항목만 업데이트; 신규 스크립트는 사용자의 선택 없이 자동 설치하지 않음 |
| 네트워크 | 인증 없는 공개 HTTPS, Python 표준 라이브러리로 처리 |
| GUI | FontLab 내장 Qt/PythonQt. 외부 GUI 런타임 설치 금지 |

**문서의 범위:** 이번 문서는 구현 요구사항을 확정하는 설계서다. 실제 `MW_install.vfpy`와 매니저 프로그램이 아직 구현·실기기 검증되었다는 의미는 아니다.

## 1. 문제 정의와 목표

### 1.1 현행 문제

개발자가 스크립트를 갱신할 때마다 팀원에게 파일을 따로 전달하고, 팀원은 Scripts 폴더를 찾아 기존 파일을 교체해야 한다. 설치된 버전과 배포 버전이 일치하는지도 관리하기 어렵다. 단일 `.py` 이외에 보조 데이터가 있는 경우 수동 복사 오류도 발생할 수 있다.

### 1.2 제품 목표

1. 팀원은 **`MW_install.vfpy` 한 번 실행**만으로 매니저를 FontLab에 설치한다.
2. 매니저를 FontLab의 Scripts 메뉴에서 실행하여 원하는 스크립트만 설치한다.
3. 매니저는 현재 설치된 스크립트만 찾아 업데이트하며, 자동 업데이트를 끌 수도 있다.
4. 네트워크 장애·잘못된 배포·업데이트 중 충돌이 있어도 기존 정상 스크립트를 보존한다.
5. macOS와 Windows에서 동일한 데이터 규약을 적용하며, OS별 경로 문자열은 하드코딩하지 않는다.

### 1.3 비목표

Git clone/pull, GitHub 로그인, Private Repository 지원, 개발자용 소스 편집·커밋, 임의 `pip install`은 목표로 하지 않는다. FontLab 7 또는 FontLab 9 호환 지원은 초기 범위에서 제외한다.

## 2. 실제 저장소 조사 결과 (2026-11-09)

확인된 원본: https://github.com/minw0525/Fontlab-python-scripts (기본 브랜치 `main`). 현재 스크립트는 저장소 루트가 아닌 **`FL8 Scripts/`** 안에 있다.

| 현재 저장소 경로 | 관리 유형 | 주의사항 |
|---|---|---|
| `FL8 Scripts/Check Negative Side-bearing.py` | 단일 파일 | 직접 배포 가능 |
| `FL8 Scripts/Check_Hangeul_Module.py` | 단일 파일 | TypeRig 등 의존성 점검 |
| `FL8 Scripts/Edit Component Sources.py` | 단일 파일 | 공백 포함 경로 |
| `FL8 Scripts/Flag Glyphs.py` | 단일 파일 | TypeRig import 확인됨 |
| `FL8 Scripts/Generate_Hangeul_Composition.py` | 단일 파일 | TypeRig import 확인됨 |
| `FL8 Scripts/Jitter Glyphs.py` | 단일 파일 | 실제 플랫폼 동작 별도 테스트 |
| `FL8 Scripts/Projective_Transform.py` | 단일 파일 | 실제 플랫폼 동작 별도 테스트 |
| `FL8 Scripts/Reset_Component_layer.py` | 단일 파일 | 실제 플랫폼 동작 별도 테스트 |
| `FL8 Scripts/Wiggle Glyphs.py` | 단일 파일 | 실제 플랫폼 동작 별도 테스트 |
| `FL8 Scripts/Adhesiontext Korean.py` 및 `FL8 Scripts/adhesiontext_korean/` | **멀티파일 패키지** | 메뉴에 표시되는 `Adhesiontext Korean.py`가 `adhesiontext_korean.app`을 import하고 `app.show_dialog()`를 호출. `__init__.py`, `app.py`, `Korean Dictionary.txt`를 포함해 일괄 설치해야 하며, 사전은 `app.py`의 `__file__` 기준으로 탐색 |

**현 상태에서 없는 배포용 파일:** 저장소 루트의 `MW_install.vfpy`, `manifest.json`, 패키지 매니저 본체 및 배포 메타데이터 생성기는 아직 필요하다. `README.md`는 있지만 설치 버전·해시를 제공하는 매니페스트를 대체하지 못한다.

**배포 제외:** `.DS_Store`, `.pyc`, `__pycache__/` 등 생성물은 배포 대상에서 제외한다. 사전 텍스트 파일은 약 5.15MB이며 개별 패키지의 필수 자산이다. 현재 저장소의 `Adhesiontext Korean.py` 진입 파일과 `adhesiontext_korean/` 패키지 사이 상대 경로를 설치 후에도 보존해야 한다.

**추가 검증:** 일부 스크립트가 `typerig.proxy.fl...`에 의존한다. **매니저의 설치 가능성**과 **실제 개별 스크립트의 성공적 실행**을 구분해 테스트해야 한다. 매니저가 TypeRig을 무단 설치하지 않는다.

## 3. 설치 UX — `MW_install.vfpy` 원클릭 부트스트랩

### 3.1 사용자 흐름

```text
[사용자]
GitHub에서 MW_install.vfpy 다운로드
            ↓
FontLab에서 열기 / FontLab 창에 드래그
            ↓
[FontLab 내장 Python에서 즉시 실행]
실행 환경 진단 + 필수 기능 확인 + 사용자 데이터 경로 탐지
            ↓
고정 GitHub 저장소의 배포 메타데이터 확인
            ↓
매니저 파일만 다운로드 → 검증 → 설치
            ↓
<Scripts>/MW Script Manager.py 생성
            ↓
Scripts 메뉴 새로고침 시도
            ↓
"매니저 설치 완료" 안내 + 매니저 창 실행
```

- **실행 파일명:** 저장소 루트의 `MW_install.vfpy`.
- **실행 방식:** FontLab의 파일 열기 또는 드래그 앤 드롭을 1차 지원한다. OS에서 `.vfpy`가 FontLab에 연결되어 있다면 더블클릭 실행도 가능하지만, 파일 연결을 전제하지 않는다.
- **무설정 설치:** 사용자가 직접 파일을 이동하거나 사용자 폴더를 고르지 않는다.
- **최초 설치 대상:** Script Manager 자체. 다른 개별 스크립트는 사용자가 매니저에서 선택한 후 설치한다.
- **재실행:** 같은 설치기를 다시 실행하면 기존 상태와 설치된 패키지를 유지하며 매니저를 복구하거나 업데이트한다(멱등성).
- **실패:** 필요한 API·기능 부재, 쓰기 권한 부족, 네트워크·검증 실패 등은 설명하고 해당 작업을 중단한다. 버전 번호가 권장값과 다르다는 이유만으로 중단하지 않으며, 기존 설치를 변경하지 않는다.

### 3.2 정확한 설치 경로 탐지 (OS 공통)

FontLab 사용자 데이터 위치는 사용자 설정에서 변경될 수 있으므로 `~/Library/...`나 `Documents/...`를 설치 경로로 단정하지 않는다. **FontLab 8.3 공식 릴리스 노트에 안내된 API**를 사용한다.

```python
from pathlib import Path
from fontlab import flPreferences

user_data = Path(flPreferences.instance().dataPath).expanduser()
scripts_dir = user_data / "Scripts"
manager_entry = scripts_dir / "MW Script Manager.py"
```

- 설치 전 `user_data`가 유효한 폴더인지 확인한다.
- 표준 `Scripts` 폴더를 우선 사용한다. 폴더 자동 인식 및 새로고침은 **FontLab 8.2 Windows/macOS에서 실기기 검증**한다.
- 사용자 지정 데이터 경로, OneDrive로 리디렉션된 Documents, 공백·한글 포함 경로도 지원한다.
- 기본값은 참고용일 뿐 코드에서 사용하지 않는다.

| 운영체제 | FontLab 8 사용자 데이터 기본 위치(참고) |
|---|---|
| macOS | `~/Library/Application Support/FontLab/FontLab 8/` |
| Windows | `%USERPROFILE%\Documents\FontLab\FontLab 8\` |

> **스크립트 메뉴 즉시 갱신:** `Scripts` 폴더 설치를 완료한 뒤, **TypeRig 없이 FontLab 내장 `fontlab` API와 PythonQt에서 노출되는 메인 윈도우의 액션 객체**를 이용해 `RefreshScripts`를 직접 호출한다. FontLab 공식 Python API는 `flWorkspace.instance().mainWindow` 속성을 제공한다. 아래 코드는 TypeRig `Automat`의 `QAction` 검색·`trigger()` 로직을 직접 재구성한 것으로, 외부 모듈을 요구하지 않는다.
>
> ```python
> from fontlab import flWorkspace
>
> def refresh_scripts():
>     main = flWorkspace.instance().mainWindow
>     if main is None:
>         return False
>
>     for obj in main.children():
>         tip = getattr(obj, "statusTip", "")
>         if callable(tip):
>             tip = tip()
>
>         if tip == "@mainwindow.actionRefreshScripts":
>             obj.trigger()
>             return True
>
>     return False
> ```
>
> 이 함수는 **FontLab의 UI 스레드**에서 호출한다. `refresh_scripts()`가 `False`를 반환하거나 액션 실행에 실패하면, 설치된 파일은 유지한 채 **FontLab 재시작 후 메뉴에 반영**되도록 안내한다. **수동 복사나 라이브러리 등록으로 대체하지 않는다.** 액션 식별자 및 동작은 제공받은 TypeRig `Automat` 소스에서 확인했으며, 실제 FontLab 8.2 이상 및 macOS/Windows에서 즉시 메뉴가 갱신되는지는 통합 테스트로 검증한다. **Script Manager와 최초 설치용 `MW_install.vfpy`는 TypeRig 없이 동작해야 한다.**

### 3.3 실행 환경 확인 및 호환성 정책

- **권장 개발·주요 검증 환경:** FontLab 8.2 이상과 내장 Python 3.11. FontLab 8.0의 Python 3.10은 버전 번호만으로 설치를 차단하지 않는다.
- Python 버전은 `sys.version_info`로 **기록 및 진단**한다. `(3, 11)`과의 일치 여부를 설치 허용 조건으로 사용하지 않는다. Python 3.10에서도 해석 가능한 문법과 표준 라이브러리를 사용한다.
- FontLab 버전 역시 진단 목적으로 파악하되, **필수 API·기능의 존재와 호출 가능 여부를 우선 검사**한다. 예를 들어 사용자 데이터 경로 API가 없는 환경에서는 그 기능의 대체 수단이 검증되지 않았다면 설치를 안전하게 중단하고 원인을 안내한다.
- 각 스크립트에 명시된 **실제 필수 기능·외부 라이브러리**의 충족 여부는 매니저 자체의 실행 가능 여부와 분리한다. 권장 버전 미만이라고 모든 스크립트를 일괄 차단하지 않는다.
- Python 3.10 및 FontLab 8.0의 동작은 **조건부 호환**이지 검증 완료를 뜻하지 않는다. macOS/Windows 및 이전 버전의 실기기 결과를 별도 기록한다.
- OS 판별은 `sys.platform` / `platform.system()`, 경로 조작은 `pathlib.Path`.

## 4. 전체 구성과 데이터 흐름

```text
GitHub (고정: minw0525/Fontlab-python-scripts)
  ├── MW_install.vfpy           ← 최초 1회 실행할 부트스트랩(추가 예정)
  ├── manifest.json             ← 공개 배포 카탈로그 / sha256 / source_ref
  ├── manager/                  ← 매니저 본체와 실행 지원 파일
  └── FL8 Scripts/              ← 현재 스크립트 소스
      ├── Adhesiontext Korean.py
      └── adhesiontext_korean/
          ├── __init__.py
          ├── app.py
          └── Korean Dictionary.txt
          │
          │ HTTPS · 선택 파일/자산만 다운로드
          ▼
FontLab 8.x (macOS 또는 Windows, Python 3.11 권장 / 3.10 조건부 허용)
  <effective user data>/
    Scripts/
      MW Script Manager.py     ← 고정 메뉴 진입점
      MW Scripts/
        Flag Glyphs.py         ← 메뉴 노출 깊이 2 이내의 실행 래퍼
        Adhesiontext Korean.py ← 실행 래퍼(하위 패키지와 독립)
    script_manager/
      manager/<version>/       ← 매니저 로직
      packages/<script-id>/<version>/
      staging/                 ← 다운로드 임시 폴더
      state.json               ← 설치 상태·활성 버전
      manifest-cache.json
      logs/
```

- 원본 저장소의 **URL과 소유자는 고정값**으로 관리하며 일반 사용자 설정 화면에서 변경할 수 없다.
- **Scripts 메뉴 표시 깊이:** 사용자 관찰에 따라 `Scripts/<분류>/<실행파일>.py`까지를 메뉴 노출 대상으로 제한한다. `Scripts/<분류>/<패키지>/<실행파일>.py`처럼 한 단계 더 깊은 실제 소스의 자동 노출을 전제하지 않는다. 이 동작은 양 OS에서 검증한다.
- **실행 파일과 본체 분리:** 얕은 경로의 `.py`는 매니저가 생성하는 고정 래퍼이고, 실제 소스·데이터 파일은 `<user data>/script_manager/packages/<id>/<version>/`에 둔다. 원본 저장소에 이미 존재하는 `FL8 Scripts/Adhesiontext Korean.py`는 해당 버전 폴더의 실행 진입점으로 그대로 보존한다. 매니저의 고정 래퍼가 `state.json`에서 활성 버전을 읽고 이 파일을 실행한다. 기존 패키지의 `__init__.py`는 Python 패키지 구성에 필요하므로 함께 설치한다.
- **패키지 단위 배포:** 단일 `.py`뿐 아니라 스크립트 `.py` + 사전 `.txt` 등 필요한 모든 파일을 **한 패키지로 선택·다운로드·검증·설치·업데이트·제거**한다. 일부 파일만 성공했을 때는 패키지 설치를 완료한 것으로 취급하지 않는다.
- 실제 스크립트는 소스 코드의 `__file__`을 기준으로 자산을 찾을 수 있도록 실행하고, 원본 진입 파일과 보조 패키지의 상대 위치를 보존한다. `Adhesiontext Korean.py`의 `from adhesiontext_korean import app`가 동작하도록 실행 시 버전 폴더를 Python 모듈 검색 경로에 포함하며, `app.py`가 같은 패키지 폴더에 있는 `Korean Dictionary.txt`를 읽을 수 있어야 한다.
- 직접 작성한 기존 스크립트, TypeRig, 타 도구의 폴더는 **소유 범위 밖**이다.

## 5. 기능 요구사항

| ID | 우선순위 | 요구사항 및 완료 기준 |
|---|---|---|
| INS-01 | P0 | `MW_install.vfpy` 실행만으로 매니저 설치; 수동 복사·Git·외부 Python 불필요 |
| INS-02 | P0 | 설치 경로를 `flPreferences.instance().dataPath`에서 조회; 설정된 사용자 경로 사용 |
| INS-03 | P0 | FontLab/Python 버전은 진단 정보로 수집하고 필수 API·기능 지원 여부로 설치 가능성 판정; 권장 버전과 다르다는 이유만으로 종료하지 않음 |
| INS-04 | P0 | 기존 설치가 있어도 중복 메뉴 생성 없이 복구·업데이트 가능 |
| INS-05 | P0 | Scripts 메뉴 노출 깊이 2 이내에 `.py` 실행 래퍼를 배치하고 깊은 경로의 실제 패키지 파일과 분리 |
| CAT-01 | P0 | 원격 manifest에서 이름·설명·설치 버전·배포 버전·상태 표시 |
| CAT-02 | P0 | 사용자가 개별 패키지를 선택하여 설치/업데이트/제거 |
| CAT-03 | P0 | 미설치/최신/업데이트 가능/호환 불가/오프라인/오류 구분 |
| CAT-04 | P1 | 상세 화면에 변경 이력, 소스 링크, 외부 패키지 의존성 표시 |
| PKG-01 | P0 | 선택한 패키지의 `files[]`만 다운로드; 전체 레포 ZIP 수신 금지 |
| PKG-02 | P0 | 다중 파일을 하나의 설치·업데이트·제거 단위로 관리; 자산의 상대 위치 보존(`__file__` 기반 접근 유지) |
| PKG-03 | P0 | 모든 파일 SHA-256 검증 완료 후에만 활성 버전 전환 |
| PKG-04 | P0 | 설치 중 실패해도 기존 정상 버전 및 상태 유지 |
| PKG-05 | P0 | 제거는 매니저 소유 파일에만 적용; 덮어쓰기 충돌 사전 차단 |
| UPD-01 | P0 | 설치한 패키지만 자동 업데이트 대상; 미설치는 자동 설치 불가 |
| UPD-02 | P0 | 수동 새로고침·선택 업데이트·일괄 업데이트 제공 |
| UPD-03 | P0 | 패키지별 자동 업데이트 토글 및 버전 고정 제공 |
| UPD-04 | P1 | 한 단계 이전 정상 버전으로 롤백 및 자동 재업데이트 잠시 중지 |
| UPD-05 | P1 | 매니저 본체도 별도 버전 폴더를 통해 자체 갱신·복구 |
| SEC-01 | P0 | 경로 순회·절대경로·허용 폴더 외부 쓰기·링크 우회를 차단 |
| SEC-02 | P0 | HTTPS, 타임아웃, 최대 크기 및 다운로드 취소 지원 |
| SEC-03 | P0 | 임시 폴더·백업 정리, 설치 이력 로그, 손상된 state 복구 절차 |
| UX-01 | P0 | macOS·Windows에서 동일한 주요 기능과 상태 제공 |
| UX-02 | P0 | 다운로드·검증 중 FontLab UI 비차단, 진행 상태 및 오류 메시지 |
| UX-03 | P0 | 새 파일 설치 후 메뉴 갱신 시도; 불가하면 재시작 안내 |

## 6. 매니페스트 — 현재 저장소 구조에 맞춘 스키마

### 6.1 배포 원칙

1. 매니저는 `main`의 **카탈로그(manifest)** 를 읽는다.
2. 각 스크립트의 실제 코드는 `source_ref`에 지정된 **고정 commit SHA** 에서만 읽는다.
3. 패키지별 `version`은 독립적이며, 같은 `id + version`의 내용 해시가 바뀌면 배포 충돌로 처리한다.
4. 저장소 경로가 공백을 포함하므로 URL 구성 시 **각 경로 세그먼트를 percent-encode** 한다.
5. 소스 파일을 다운로드하더라도 그 코드에 `exec`를 호출해 설치 과정에서 실행하지 않는다. **실행은 메뉴를 통해 명시적으로 요청할 때만 수행**한다.
6. 패키지에 포함할 파일은 명시 목록으로 정의하며, `*.pyc`, `__pycache__/`, `.DS_Store`는 제외한다.

### 6.2 JSON 예시 (설명용 가상 해시/버전)

아래의 `source_ref`, `sha256`은 **실제 값을 채워야 하는 자리표시자**다. 현재 GitHub 저장소에 이 파일이 존재한다는 뜻은 아니다.

```json
{
  "schema_version": 1,
  "repository": "minw0525/Fontlab-python-scripts",
  "manager": {
    "version": "0.1.0",
    "source_ref": "<40-CHAR-COMMIT-SHA>",
    "files": [
      {"source": "manager/main.py", "target": "main.py", "sha256": "<64-HEX>"}
    ]
  },
  "scripts": [
    {
      "id": "flag-glyphs",
      "name": "Flag Glyphs",
      "description": "선택한 글리프의 플래그 일괄 지정",
      "version": "1.0.0",
      "source_ref": "<40-CHAR-COMMIT-SHA>",
      "recommended_fontlab": "8.2+",
      "target_python": "3.11",
      "platforms": ["macos", "windows"],
      "requirements": ["TypeRig"],
      "entrypoint": "Flag Glyphs.py",
      "files": [
        {"source": "FL8 Scripts/Flag Glyphs.py", "target": "Flag Glyphs.py", "sha256": "<64-HEX>"}
      ]
    },
    {
      "id": "adhesiontext-korean",
      "name": "Adhesiontext Korean",
      "description": "선택한 한글 음절을 조합하는 단어 생성기",
      "version": "1.0.0",
      "source_ref": "<40-CHAR-COMMIT-SHA>",
      "recommended_fontlab": "8.2+",
      "target_python": "3.11",
      "platforms": ["macos", "windows"],
      "requirements": ["TypeRig"],
      "entrypoint": "Adhesiontext Korean.py",
      "files": [
        {"source": "FL8 Scripts/Adhesiontext Korean.py", "target": "Adhesiontext Korean.py", "sha256": "<64-HEX>"},
        {"source": "FL8 Scripts/adhesiontext_korean/__init__.py", "target": "adhesiontext_korean/__init__.py", "sha256": "<64-HEX>"},
        {"source": "FL8 Scripts/adhesiontext_korean/app.py", "target": "adhesiontext_korean/app.py", "sha256": "<64-HEX>"},
        {"source": "FL8 Scripts/adhesiontext_korean/Korean Dictionary.txt", "target": "adhesiontext_korean/Korean Dictionary.txt", "sha256": "<64-HEX>"}
      ]
    }
  ]
}
```

**호환성 메타데이터:** `recommended_fontlab`과 `target_python`은 권장·주요 테스트 환경의 표기일 뿐 설치 차단 조건이 아니다. 실제 호환 불가 판정은 확인된 필수 API·외부 의존성의 부재에 근거한다. 패키지의 최소 버전 제약이 필요한 경우 실제 불호환 원인을 확인하여 별도 조건으로 명시한다.

**스키마 추가 검증:** 식별자 중복, target 중복, 빈 파일 목록, 허용하지 않은 확장자, 경로 순회, 동일 스크립트의 모순된 버전, source_ref의 길이/형식을 사전에 거부한다. 패키지별 파일 경로는 오직 자기 버전 폴더 아래로만 추출한다.

### 6.3 다운로드 URL

```text
https://raw.githubusercontent.com/minw0525/Fontlab-python-scripts/<source_ref>/<url-encoded-source-path>
```

예: 실제 파일 목록에는 `FL8 Scripts/Flag Glyphs.py`가 있으므로, 공백은 URL에 그대로 두지 말고 인코딩하여 요청한다. GitHub API는 브랜치/커밋 발견 등에 사용할 수 있으나 필수 런타임 의존성은 아니며, Public Repository의 공개 파일을 인증 없이 수신할 수 있다.

## 7. 설치 상태 및 실행 메커니즘

### 7.1 로컬 저장소

```text
<flPreferences().dataPath>/
├── Scripts/
│   ├── MW Script Manager.py           # 메뉴용 매니저 진입 파일
│   └── MW Scripts/
│       ├── Flag Glyphs.py             # 패키지별 고정 래퍼
│       └── Adhesiontext Korean.py
└── script_manager/
    ├── manager/0.1.0/                 # 매니저 본체
    ├── packages/
    │   ├── flag-glyphs/1.0.0/Flag Glyphs.py
    │   └── adhesiontext-korean/1.0.0/   # 네 파일이 한 설치 단위
    │       ├── Adhesiontext Korean.py
    │       └── adhesiontext_korean/
    │           ├── __init__.py
    │           ├── app.py
    │           └── Korean Dictionary.txt
    ├── staging/
    ├── state.json
    ├── manifest-cache.json
    └── logs/
```

- 기존 `Scripts/MW Scripts/` 경로에 **사용자가 만든 동명 파일·폴더**가 있으면 자동 덮어쓰지 않는다. 안전한 이름 변경·별도 소유 폴더 이용·중단 중 하나를 선택하도록 한다.
- 설치 완료 여부는 단순 파일 존재가 아니라 **관리자가 기록한 소유·해시·활성 버전**에 의해 판정한다.

### 7.2 트랜잭션 설치

1. 서버 manifest를 읽고 대상 패키지 ID, 버전, 파일 목록 및 플랫폼 호환성을 검증한다.
2. 임시 staging 폴더를 만든다.
3. 대상 파일만 각각 HTTPS로 다운로드해 크기·SHA-256을 검증한다.
4. 모든 파일과 디렉터리 구성을 확인하고 새 버전 폴더로 이동한다.
5. 기존 실행 래퍼를 보존하거나 최초 설치 시에만 생성한다.
6. `state.json.tmp`를 작성하고 `os.replace()`로 활성 버전 포인터를 전환한다.
7. staging 정리 후 설치 결과를 UI와 로그에 남긴다.

**원자성 범위:** 버전 폴더 내용은 검증 완료 후 사용 가능해지고, 활성 버전 전환은 같은 파일시스템 내의 `os.replace()`로 처리한다. 다른 파일시스템을 가로지르는 원자 이동을 가정하지 않는다. 상태 기록 실패 시 이전 활성 버전은 유지한다.

### 7.3 고정 래퍼의 실행

- `.py` 래퍼에는 FontLab Scripts 메뉴용 식별 가능한 이름(`#FLM:` 등)을 설정한다.
- 래퍼는 로컬 `state.json`에서 활성 버전을 조회하고 해당 패키지의 `entrypoint`를 현재 FontLab 내장 Python 컨텍스트에서 실행한다(3.11 권장, 3.10 조건부 허용).
- `__file__`은 **실제 패키지의 entrypoint 경로**를 가리키도록 하여 자산 파일의 상대 위치 참조를 보존한다. `Scripts` 메뉴용 래퍼 위치로 지정하지 않는다.
- `sys.path`를 임시 보정하고 복구한다. 현재 `Adhesiontext Korean.py`는 `adhesiontext_korean.app`을 import하는 방식이므로, 실행 중 패키지 검색 경로와 모듈 캐시가 다음 실행·업데이트에 미치는 영향도 검증한다. `runpy`/`exec` 중 어느 방식이 FontLab, TypeRig, GUI 객체 및 `__file__`에 적합한지는 실제 스크립트로 검증한다.
- Python 모듈·Qt GUI 객체가 남아 있을 수 있으므로 **업데이트 후 즉시 핫리로드를 보장하지 않는다.** 필요 시 FontLab 재시작을 요청한다.

### 7.4 제거와 롤백

- 제거는 매니저가 생성한 래퍼와 버전 폴더 등 소유 데이터만 제거한다.
- 매니저 자체나 사용자 작성 스크립트, TypeRig 라이브러리를 제거하지 않는다.
- 로컬 수정이 발견되면 사용자의 확인 없이 삭제하지 않는다.
- 롤백은 이전에 검증된 버전으로 `active_version`을 되돌리고, 동일 업데이트가 즉시 재설치되지 않도록 자동 업데이트를 보류한다.

## 8. UI/자동 업데이트 정책

### 8.1 메인 창

| 선택 | 스크립트 | 설치 버전 | 최신 버전 | 상태 | 동작 |
|---|---|---|---|---|---|
| ☐ | Flag Glyphs | 1.0.0 | 1.0.0 | 최신 | 제거 |
| ☑ | Generate Hangeul Composition | 1.0.0 | 1.1.0 | 업데이트 가능 | 업데이트 |
| ☑ | Adhesiontext Korean | — | 1.0.0 | 미설치 | 설치 |

*위 버전 값은 UI 예시이며 현재 저장소의 검증된 최신 버전 정보가 아니다.*

필수 UI: **새로고침, 선택 설치/업데이트, 설치 목록, 개별 제거, 진행 상태, 설정(자동 업데이트), 오류 설명**. Windows와 macOS에서 동일하게 사용할 수 있어야 한다. 컨트롤은 FontLab 내장 Qt/PythonQt를 이용하고 별도 PySide/PyQt 설치는 요구하지 않는다.

### 8.2 자동 확인/자동 적용

- **수동 검사:** 매니저 실행 시 즉시 원격 목록 확인(사용자가 새로고침 가능).
- **자동 확인:** FontLab 시작 때 1회 확인하는 옵션 지원. 불필요한 중복 요청 방지를 위해 성공한 검사 후 기본 24시간 캐시(수동 갱신은 예외).
- **자동 적용:** 기본적으로 설치된 항목만 업데이트. 스크립트별 자동 업데이트 해제·버전 고정 가능.
- **후크:** `initScript.py`는 FontLab 시작 시 1회 실행되는 공식 훅. `startupScript.py`는 다른 스크립트 실행 때마다 실행될 수 있어 업데이트 확인에 이용하지 않는다.
- **후크 충돌 방지:** 기존 `initScript.py`가 없다면 최소 호출 코드를 생성한다. 기존 파일이 있다면 **절대 통째로 교체하지 않는다**. 자동 삽입을 제공할 경우 백업, 명시적 확인, 특정 관리 블록 식별, 반복 실행 멱등성, Python 문법 검사, 실패 시 복구가 필수다. 이 방식이 검증되지 않으면 시작 시 자동 확인은 P1로 늦추고 매니저 실행 시 확인을 MVP로 삼는다.
- UI 쓰기 작업은 주 스레드에서, HTTPS 다운로드·검증은 UI를 차단하지 않는 작업자로 수행한다.

## 9. 보안·운영 및 크로스플랫폼 요구사항

### 9.1 파일·네트워크 안전성

- HTTPS 허용 호스트 목록을 GitHub 공식 도메인으로 제한한다.
- 파일 다운로드 제한 시간·총 크기·동시 요청 수를 설정한다(5MB 이상의 필수 데이터 파일 수용).
- 원본 커밋이 같아도 각 파일의 SHA-256을 확인한다. **SHA-256은 매니페스트와 파일의 일치성 검사이며, 같은 저장소가 침해된 경우를 방지하는 독립 서명은 아니다.**
- 경로 순회(`..`), 절대 경로, Windows 드라이브·UNC, 심볼릭 링크/junction을 통한 경로 이탈을 차단한다.
- `state.json`과 배포 매니페스트는 파싱 오류를 별도로 처리하고 이전 유효 상태를 유지한다.
- TLS 오류, GitHub 404·429, 사내 프록시, 오프라인은 재시도/오류 안내로 처리한다. 인증 토큰을 코드나 로그에 기록하지 않는다.

### 9.2 OS별 검증

| 범위 | macOS | Windows |
|---|---|---|
| `MW_install.vfpy` 파일 열기/드래그 실행 | 필수 | 필수 |
| 사용자 설정 데이터 폴더 탐지 | 필수 | 필수 |
| Scripts 메뉴 자동 인식/갱신 | 필수 | 필수 |
| 한글·공백·Unicode 경로 처리 | 필수 | 필수 |
| `__file__` 상대 자산 접근 | 필수 | 필수 |
| 파일 잠금, 경로 교체, 파일 권한 | 검증 | 중점 검증 |
| 내장 PythonQt GUI 동작 | 필수 | 필수 |
| TypeRig 의존성 사전 감지 | 필수 | 필수 |
| 업데이트·제거·롤백 | 필수 | 필수 |

**테스트 환경:** 최소 macOS Intel 또는 Apple Silicon 한 대와 Windows x64 한 대에서 FontLab 8.2 및 팀의 실제 최신 8.x 버전을 검증한다. FontLab 8.0/Python 3.10은 기능 기반 판정과 조건부 호환 여부를 별도로 확인한다. macOS의 아키텍처 차이가 있으면 별도 확인한다. **테스트 이전에는 두 OS에서 이미 작동한다고 표현하지 않는다.**

## 10. 실제 개발 단계 및 저장소 변경 계획

### Phase 0 — 준비/조사 (반드시 먼저)

- [ ] `FL8 Scripts` 안의 10개 스크립트를 전수 조사하고, TypeRig·보조 파일 의존성 정리
- [ ] FontLab 8.2 macOS/Windows에서 `flPreferences.instance().dataPath` 값 확인; 8.0/3.10은 기능 검사 결과에 따라 조건부 호환 판정
- [ ] `.vfpy` 실행, 사용자 Scripts 자동 인식 및 즉시 메뉴 갱신 가능 여부 확인
- [ ] 저장소에 `*.pyc`, `.DS_Store` 배포 제외 규칙 수립

### Phase 1 — MVP

- [ ] 루트 `MW_install.vfpy` 구현(표준 라이브러리, 반복 실행 안전)
- [ ] 루트 `manifest.json` 생성기 및 배포 시 검사 구현
- [ ] `manager/` 구현(목록, 설치, 업데이트, 제거, 상태 저장)
- [ ] 메뉴 노출 깊이 2 이내의 고정 실행 래퍼 생성, 패키지별 버전 폴더 로딩 및 멀티파일 일괄 설치
- [ ] 선택적 다운로드, SHA-256, staging, 원자적 활성 전환
- [ ] macOS/Windows 실기기 E2E 검증

### Phase 2 — 안정화

- [ ] 매니저 자체 업데이트
- [ ] 롤백 UI 및 로컬 수정 감지
- [ ] 자동 시작 후크의 안전한 통합
- [ ] 설치 로그·진단·복구 기능 고도화
- [ ] 선택적 업데이트, 버전 고정, 변경 이력 UI 강화

**기존 저장소 파일은 가능한 한 변경하지 않는 것을 원칙으로 한다.** 새 배포 파일·자동화만 추가하고, 개별 스크립트 수정은 실제 호환성 문제를 확인한 경우에만 별도 커밋으로 진행한다.

## 11. 수용 테스트(Definition of Done)

| 테스트 ID | 시나리오 | 통과 기준 |
|---|---|---|
| T-01 | macOS에서 `MW_install.vfpy` 실행 | 매니저가 데이터 경로/Scripts에 설치, 수동 이동 불필요 |
| T-02 | Windows에서 `MW_install.vfpy` 실행 | T-01과 동일 |
| T-03 | 사용자 데이터 폴더가 기본 위치가 아닌 환경 | 실제 설정 경로에 설치됨 |
| T-04 | Python 3.10 또는 FontLab 8.0 | 버전만으로 종료하지 않음; 필수 API가 있으면 진행, 없으면 안전하게 해당 작업만 중단하고 원인 안내 |
| T-05 | 동일 `MW_install.vfpy` 재실행 | 중복 매니저/메뉴/상태 초기화 없음 |
| T-06 | 10개 중 스크립트 1개 선택 설치 | 대상 패키지의 필수 파일만 다운로드 |
| T-07 | `Adhesiontext Korean` 설치 및 실행 | `Adhesiontext Korean.py` 및 `adhesiontext_korean/`의 네 파일을 한 패키지로 설치·검증; `app` import, `show_dialog()` 호출 및 사전 데이터의 `__file__` 상대 경로 접근 정상 |
| T-08 | `*.pyc` / `.DS_Store` 존재 | 매니페스트에서 배포 제외됨 |
| T-09 | TypeRig 없는 설치 환경 | 의존성 부족 안내; 매니저 자체는 동작 |
| T-10 | 설치된 A 갱신, 미설치 B 신설 | A만 자동 업데이트; B 미설치 유지 |
| T-11 | SHA 불일치 / 404 / 다운로드 중단 | 새 버전 미활성화, 이전 버전 정상 |
| T-12 | 사용자 폴더의 기존 동명 파일 | 자동 덮어쓰기 없이 충돌 해결 안내 |
| T-13 | Windows 파일 잠금 / 앱 종료 | 미완성 설치가 정상 활성 상태로 표시되지 않음 |
| T-14 | Unicode/공백/사용자 정의 경로 | 각 OS에서 동일한 설치·실행 결과 |
| T-15 | 메뉴에 설치된 스크립트 실행 | `__file__`, TypeRig, GUI/폰트 컨텍스트 정상 |
| T-16 | 오프라인 / 프록시 차단 | 설치본 계속 실행, 오류·재시도 안내 |
| T-17 | 활성 버전 롤백 | 이전 코드로 실행, 즉시 자동 재업데이트하지 않음 |
| T-18 | 매니저 자체 파일 누락 또는 손상 | `MW_install.vfpy` 재실행으로 복구 가능 |
| T-19 | 악의적 manifest의 `../../`, 절대경로, symlink | 설치 영역 외부 쓰기 차단 |
| T-20 | 자동 검사 후크가 이미 존재 | 기존 사용자 로직 유지, 무단 파일 덮어쓰기 없음 |
| T-21 | Scripts 메뉴 경로 깊이 제한 | `Scripts/MW Scripts/*.py` 래퍼 노출 및 실행 확인; 더 깊은 패키지 파일은 메뉴 노출에 의존하지 않음 |

**최종 승인:** macOS와 Windows에서 T-01~T-16 및 T-19·T-21을 모두 통과해야 MVP 출시 가능. Phase 2 기능에 해당하는 T-17·T-20의 세부 구현은 별도 마일스톤에서 검증한다.

## 12. 보류/확인 필요 기술 이슈

1. **FontLab 8.2 Scripts 메뉴 자동 새로고침:** 8.2 양 OS에서 재시작 없이 즉시 표시되는지 검증해야 한다.
2. **이전 환경의 필수 기능 검사:** FontLab 8.0/Python 3.10에서 사용자 데이터 경로 탐지, 메뉴 갱신, 래퍼 실행이 실제로 동작하는지 검증한다. 버전 번호 자체는 강제 차단 기준이 아니다.
3. **`runpy` vs `exec` 래퍼 실행 및 메뉴 깊이:** TypeRig GUI, 현재 폰트·글리프 문맥, `__file__`, `adhesiontext_korean.app` import 및 모듈 캐시에 영향을 미치므로 실제 멀티파일 스크립트로 테스트한다. 실행 래퍼는 메뉴 노출 깊이 이내에 둔다.
4. **외부 라이브러리 의존성:** TypeRig 및 기타 패키지를 어떤 스크립트에서 필수로 요구하는지 전수 확인한다.
5. **자동 확인 훅 설치:** 기존 사용자 `initScript.py`와 충돌 없는 통합을 확인하기 전에는 외부 훅 자동 변경을 하지 않는다.
6. **실제 설치 검증:** 문서상의 양 OS 지원은 구현 목표이며, 완료 인증은 실기기 E2E 테스트 결과로 판단한다.

## 13. 공식 참고 자료

1. FontLab 8, *New in FontLab 8: Scripts & extensions* (FontLab 8.2부터 Python 3.11, macOS/Windows 내장 환경, init hook): https://help.fontlab.com/fontlab/8/whats-new/whats-new-12-scripts-extensions/
2. FontLab 8, *Release notes for 8.2.0.8620* (내장 Python 3.11.3): https://help.fontlab.com/fontlab/8/whats-new/release-notes/8.2.0.8620/
3. FontLab 8, *Release notes for 8.3.0.8746* (`flPreferences.instance().dataPath` 공식 예시): https://help.fontlab.com/fontlab/8/whats-new/release-notes/8.3.0.8746/
4. FontLab Support, *TypeRig Install* (FontLab 8에서 `install.vfpy` 드래그 실행): https://support.fontlab.com/support/solutions/articles/33000279000-typerig-install
5. FontLab 7 Release Notes, *Execute `.vfpy` and open `.py`* (`.vfpy` 즉시 실행 방식): https://help.fontlab.com/fontlab/7/manual/Release-Notes-7432/
6. GitHub Docs, *REST API — Repository contents*: https://docs.github.com/en/rest/repos/contents
7. GitHub Docs, *REST API rate limits*: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
8. 실측 저장소: https://github.com/minw0525/Fontlab-python-scripts 및 `FL8 Scripts/Adhesiontext Korean.py`, `FL8 Scripts/adhesiontext_korean/` (2026-11-09 조사)
