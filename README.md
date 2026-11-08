# Fontlab Python Scripts


## MW Script Manager (미리보기)

[MW_install.vfpy 다운로드](https://raw.githubusercontent.com/minw0525/Fontlab-python-scripts/main/MW_install.vfpy)

FontLab에서 설치기를 열거나 창에 드래그하면 매니저를 설치합니다. 원하는 스크립트만 선택해 설치·업데이트·제거할 수 있습니다. 매니저 자체에는 TypeRig이 필요하지 않으며, 현재 제공되는 개별 스크립트에는 TypeRig이 필요합니다.

**검증 중인 초기 버전입니다.** 현재 macOS FontLab 8.4.2에서 내장 SSL 라이브러리 로딩 오류를 확인했습니다. 이 환경에서는 온라인 설치가 중단됩니다. Windows 및 FontLab 8.2 실기기 검증도 남아 있습니다.

- [사용법 및 개발자 배포 절차](Documentation/MW_SCRIPT_MANAGER.md)
- [구현·검증 결과와 알려진 제한](Documentation/IMPLEMENTATION_STATUS.md)

## FL8 Scripts

*   **`Adhesiontext Korean.py` + `adhesiontext_korean/`**
    *   선택한 한글 음절, 혹은 선택한 범위 내의 한글 음절을 조합하여 랜덤한 한국어 단어 목록을 생성합니다.
    *   Generates a list of random Korean words by combining selected Hangul syllables or syllables within a selected range.

*   **`Check Negative Side-bearing.py`**
    *   음수 사이드 베어링이 있는 글리프를 확인하고 플래그를 지정합니다. 
    *   Checks for glyphs with negative side-bearings and flags them.

*   **`Check_Hangeul_Module.py`**
    *   현재 편집 중인 문자열의 초성과 종성을 선택한 자소로 치환해 한글 모듈을 확인합니다. 
    *   Checks Hangul modules by substituting the initial (Choseong) and final (Jongseong) consonants of the current string with selected ones.

*   **`Edit Component Sources.py`**
    *   현재 편집 창의 글리프들을 구성하는 모든 컴포넌트를 새 창에 나열합니다. 
    *   Lists all components that make up the glyphs in the current editing window in a new window.

*   **`Flag Glyphs.py`**
    *   선택된 글리프에 플래그를 일괄적으로 지정합니다.
    *   Applies a flag to all selected glyphs.

*   **`Generate_Hangeul_Composition.py`**
    *   선택한 초성, 중성, 종성을 조합해 한글 문자열을 생성합니다. 
    *   Generates Hangul strings by combining selected initial, medial, and final consonants (Choseong, Jungseong, Jongseong).

*   **`Jitter Glyphs.py`**
    *   선택한 글리프의 윤곽선을 무작위로 이동시켜 지터 효과를 생성합니다.
    *   Creates a jitter effect by randomly moving the points on the outlines of selected glyphs.

*   **`Projective_Transform.py`**
    *   선택한 글리프 목록에 원근 변환을 적용합니다.
    *   Applies a projective transformation to the selected glyphs.

*   **`Reset_Component_layer.py`**
    *   컴포넌트 레이어를 재설정합니다.
    *   Resets the component layer.

*   **`Wiggle Glyphs.py`**
    *   선택한 글리프의 윤곽선을 조작하여 글리프에 위글 효과를 추가합니다.
    *   Adds a wiggle effect to glyphs by manipulating the points on their outlines.



## 저장소 구성

```text
MW_install.vfpy       # 사용자가 다운로드할 설치기
manifest.json         # 고정 커밋과 SHA-256을 담은 배포 카탈로그
FL8 Scripts/          # 개별 스크립트와 필수 자산
manager/              # 매니저 런타임
tools/                # 배포 생성기와 패키지 정의
tests/                # 자동 테스트 및 FontLab 검증 도구
Documentation/        # 사용·배포 안내, 요구사항, 검증 기록
.github/workflows/    # Python 3.10 / 3.11 자동 테스트
```
