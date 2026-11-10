"""Build a staged worklist from declared designs, not measured font geometry."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from HangulParametric.inference import family
from HangulParametric.mieum_relations import estimate, syllable
from HangulParametric.model import decompose

HERE = Path(__file__).resolve().parent
completed = set(HERE.joinpath('completed.txt').read_text().strip())
target_file, = ROOT.glob('ADOBE-KR-9*2780*.txt')
targets = {c for c in target_file.read_text() if '\uac00' <= c <= '\ud7a3'}
assert len(targets) == 2780
closed = {c for c in targets if decompose(c)[2]}
layouts = ('H', 'V', 'M')
defaults = dict(H=0, V=8, M=9)
initials = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'


def observations(chars):
    # Identical positive boxes test dependency availability only, not design fit.
    return {c: {'boxes': [dict(x=0, y=0, w=100, h=100) for _ in range(3)]}
            for c in chars}


def supported(chars):
    obs = observations(chars)
    result = set()
    for c in closed:
        try:
            for role in range(3):
                estimate(obs, c, role, reference_initial=11)
        except ValueError:
            continue
        result.add(c)
    return result


# Keep existing within-layout calibration pairs; add only missing families.
stage1 = set()
for a in range(19):
    for layout in layouts:
        if not any(decompose(c)[0] == a and family(c)[0] == layout for c in closed):
            continue
        candidates = [v for v in range(21) if family(syllable(a, v, 16))[0] == layout]
        if any({syllable(a, v, 16), syllable(11, v, 16), syllable(6, v, 16)}
               <= completed for v in candidates):
            continue
        v = defaults[layout]
        stage1.update({syllable(a, v, 16), syllable(11, v, 16), syllable(6, v, 16)} - completed)

after1 = completed | stage1
covered1 = supported(after1)
# Current estimator requires an actual reference donor for fallback.
stage2 = {syllable(11, decompose(c)[1], decompose(c)[2])
          for c in closed - covered1} - after1
after2 = after1 | stage2
covered2 = supported(after2)
assert covered2 == closed
assert not stage1 & stage2 and not completed & (stage1 | stage2)

# Optional per-vowel calibration, not another mandatory worklist.
optional = {syllable(decompose(c)[0], decompose(c)[1], 16) for c in closed} - after2
for name, chars in [('01_layout_baselines', stage1), ('02_reference_gaps', stage2),
                    ('optional_per_vowel', optional)]:
    HERE.joinpath(name + '.txt').write_text(''.join(sorted(chars)) + '\n')

lines = ['# 2026-11-03 추가 제작 목록', '',
         '사용자가 제공한 문자열을 디자인 완료로 간주한다. 실제 폰트의 윤곽/요소 분리/품질은 검사하지 않았다.',
         '초성 ㅇ을 전이 기준으로 고정한다. H/V/M과 민글자/받친글자는 섞지 않는다.',
         '과거 1,377자 제작 목록의 단순 차집합이 아니며, 아래 수치는 이론적 최소 설계 수가 아니다.', '',
         f'- 완료 신고: {len(completed)}자 (타겟 내부 {len(completed & targets)}자)',
         f'- 타겟: 받친글자 {len(closed)}자 / 민글자 {len(targets - closed)}자',
         f'- 기존 표본으로 초중종 모두 계산 근거가 연결되는 받친글자: {len(supported(completed))}자',
         f'- 1단계 후: {len(covered1)}자 / 2단계 후: {len(covered2)}자', '',
         '위 검사는 동일한 가상 bbox로 현재 estimate()의 의존성만 검사한다. 정확도, 윤곽, SVC 소스 준비를 보장하지 않는다.', '',
         f'## 1. 모임꼴별 기준 연결: {len(stage1)}자', '',
         '이미 같은 모임꼴의 ㅁ받침 기준 연결이 있으면 재사용한다. 없을 때만 ㅏ/ㅗ/ㅘ+ㅁ을 추가한다.',
         '예: 깜을 암·맘과 비교하여 ㄲ의 H형 기준을 만든다. 깍·깐·깔 전체를 먼저 그리지 않는다.', '']
for a, label in enumerate(initials):
    group = ''.join(c for c in sorted(stage1) if decompose(c)[0] == a)
    if group:
        lines.append(f'- {label}: {group}')
lines += ['', f'## 2. 기준 ㅇ의 누락 문맥: {len(stage2)}자', '',
          '1단계 뒤에도 계산 불가능한 타겟의 중성·종성 문맥을 ㅇ에서 보충한다.',
          '현재 구현은 이 fallback에 실제 같은 중성·종성의 ㅇ 표본을 요구한다. 이는 구현의 충분조건이지 모든 전이 모델의 필수조건이 아니다.',
          '기존 다른 초성의 대비에서 누락 ㅇ 관계를 추정하도록 엔진을 확장하면 이 목록도 줄일 수 있다.', '']
for layout in layouts:
    group = ''.join(c for c in sorted(stage2) if family(c)[0] == layout)
    lines.append(f'- {layout} ({len(group)}자): {group}')
lines += ['', '## 선택 사항: 중성별 기준 보정', '',
          f'optional_per_vowel.txt의 {len(optional)}자는 필수가 아니다. 다른 중성으로 전이했을 때 어색한 조건에만 사용한다.',
          '예: 깜만으로 ㄲ H형을 연결할 수 있지만, ㅓ에서 ㄲ/ㅇ 비례가 다르면 껌을 추가해 해당 중성의 기준을 만든다.',
          'ㅘ 하나가 ㅙ·ㅞ 형상을 대표한다는 뜻도 아니다. 세 조건의 ㅇ 문맥을 사용하되 대상 초성 보정 비례만 공유한다.', '',
          '## 별도 작업', '',
          '- 민글자는 이번 추가 목록에서 제외했다. 받친글자 관계로 제작 완료를 주장하지 않는다.',
          '- SVC 코너 윤곽과 topology는 별도 준비 대상이다. 완성형 표본 수와 레이어 수는 다르다.',
          '- 실제 표본을 분석한 뒤 검증 잔차로 보정 조건을 선정해야 한다. 문자열만으로 추가 검수량을 정할 수 없다.', '']
HERE.joinpath('README.md').write_text('\n'.join(lines))
print('\n'.join(lines))
