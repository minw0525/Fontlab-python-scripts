"""Native PythonQt entry and controller for the first usable relation-editor slice."""

from pathlib import Path
import traceback

from PythonQt import QtCore
from typerig.proxy.fl.gui import QtGui

from .model import JAMO, VOWEL_ORDER, BOX_KEYS, Session, characters, decompose, ordered_characters
from .fontlab_adapter import FontAdapter
from .canvas import GlyphCanvas, value
from .inference import source_key

_window = None


class ScrollSafeSpinBox(QtGui.QSpinBox):
    def wheelEvent(self, event):
        event.ignore()


def button(label, callback):
    widget = QtGui.QPushButton(label)
    widget.clicked.connect(callback)
    return widget


def combo(labels):
    widget = QtGui.QComboBox()
    widget.addItems(labels)
    return widget


def repertoire(index):
    pattern, expected = (('KSX-1001*2350*.txt', 2350), ('ADOBE-KR-9*2780*.txt', 2780))[index]
    paths = list(Path(__file__).resolve().parents[1].glob(pattern))
    if len(paths) != 1:
        raise ValueError('문자 목록 파일을 찾을 수 없습니다: ' + pattern)
    text = ''.join(characters(paths[0].read_text(encoding='utf-8')))
    if len(text) != expected:
        raise ValueError('문자 목록 개수 불일치: ' + pattern)
    return text


class RelationWindow(QtGui.QWidget):
    def __init__(self):
        super().__init__()
        self.adapter = FontAdapter()
        self.session = Session()
        self.paths = {}
        self.display_paths = {}
        self.relation_cache = {}
        self.repertoires = [set(repertoire(i)) for i in (0, 1)]
        self.selected = None
        self.edit_selection = set()
        self.batch_preview = {}
        self.role = 0
        self.preview = False
        self.pending_update = None
        self.syncing = False
        self.origin = None
        self.layer_name = None
        self.save_timer = QtCore.QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(800)
        self.save_timer.timeout.connect(self.autosave)
        self.preview_timer = QtCore.QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(350)
        self.preview_timer.timeout.connect(self.preview_pending)
        self.setWindowTitle('Hangul Parametric · 관계 편집')
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.WindowTitleHint |
                            QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowCloseButtonHint |
                            QtCore.Qt.WindowMinMaxButtonsHint)
        self.setAttribute(QtCore.Qt.WA_MacAlwaysShowToolWindow, False)
        self.resize(1250, 880)
        self.setStyleSheet('''
            QWidget {font-size:12px; color:#29332f;}
            QGroupBox {border:0; border-top:1px solid #cbd3ce; margin-top:16px; padding-top:14px; font-weight:600;}
            QGroupBox::title {subcontrol-origin:margin; subcontrol-position:top left; padding:0 6px 0 0;}
            QTabBar::tab {padding:10px 24px; border-bottom:2px solid transparent;}
            QTabBar::tab:selected {border-bottom-color:#177962; color:#145c45;}
            QFrame#properties {border-left:1px solid #cbd3ce;}
            QLabel#selection {font-size:26px; font-weight:600;}
            QLabel#status {border-top:1px solid #cbd3ce; padding-top:8px; color:#68746d;}
        ''')
        root = QtGui.QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)
        header = QtGui.QHBoxLayout()
        header.addWidget(QtGui.QLabel(Path(self.adapter.path).name or '열린 폰트'))
        header.addStretch()
        header.addWidget(QtGui.QLabel('마스터'))
        self.master = combo(self.adapter.masters())
        self.master.setFixedWidth(130)
        header.addWidget(self.master)
        root.addLayout(header)
        self.tabs = QtGui.QTabBar()
        for label in ('표본', '관계 설정'):
            self.tabs.addTab(label)
        root.addWidget(self.tabs)
        self.stack = QtGui.QStackedWidget()
        root.addWidget(self.stack)
        self.make_sample()
        self.make_editor()
        self.status = QtGui.QLabel('표본을 분석하면 실제 공간값을 표시합니다.')
        self.status.setObjectName('status')
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.tabs.connect('currentChanged(int)', self.change_tab)
        self.master.connect('currentIndexChanged(int)', self.change_master)
        self.change_master(0)

    def safe(self, callback):
        try:
            callback()
        except Exception as error:
            traceback.print_exc()
            self.status.setText(str(error))
            QtGui.QMessageBox.warning(self, '작업 중단', str(error))

    def make_sample(self):
        page = QtGui.QWidget()
        layout = QtGui.QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(QtGui.QLabel('표본 문자열'))
        self.sample = QtGui.QPlainTextEdit()
        self.sample.setPlaceholderText('디자인된 한글 완성형 문자열')
        self.sample.textChanged.connect(self.sample_edited)
        layout.addWidget(self.sample)
        self.mapping = QtGui.QCheckBox('요소 목록 순서: 0=초성, 1=중성, 2=종성 (민글자는 0·1)')
        self.mapping.setChecked(True)
        layout.addWidget(self.mapping)
        self.grouped_vowel = QtGui.QCheckBox('분리된 중성 요소 함께 측정: 초성은 첫 요소, 종성은 마지막 요소')
        layout.addWidget(self.grouped_vowel)
        layout.addWidget(button('표본 측정·관계 추론', lambda: self.safe(self.analyze)))
        self.issues = QtGui.QPlainTextEdit()
        self.issues.setReadOnly(True)
        self.issues.setMaximumHeight(170)
        layout.addWidget(self.issues)
        self.recover_button = button('읽을 수 없는 설정 복구 · 현재 분석 유지', lambda: self.safe(self.recover_settings))
        self.recover_button.hide()
        layout.addWidget(self.recover_button)
        layout.addWidget(button('관계 설정으로', lambda: self.tabs.setCurrentIndex(1)))
        self.stack.addWidget(page)

    def make_editor(self):
        page = QtGui.QWidget()
        layout = QtGui.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        filters = QtGui.QHBoxLayout()
        filters.setSpacing(18)
        self.jamo_buttons = []
        self.jamo_grids = []
        for role, items in enumerate(JAMO):
            group = QtGui.QGroupBox(('초성', '중성', '종성')[role])
            group.setFixedHeight(205)
            area = QtGui.QVBoxLayout(group)
            area.setContentsMargins(0, 8, 0, 4)
            area.setSpacing(6)
            title = QtGui.QHBoxLayout()
            title.setSpacing(4)
            title.addStretch()
            for action, label in (('all', '전체'), ('none', '해제'), ('invert', '반전')):
                action_button = button(label, lambda checked=False, r=role, a=action: self.select_group(r, a))
                action_button.setFixedWidth(44)
                title.addWidget(action_button)
            area.addLayout(title)
            grid = QtGui.QGridLayout()
            grid.setSpacing(4)
            for row in range(4):
                grid.setRowMinimumHeight(row, 30)
            buttons = []
            for index, label in enumerate(items):
                b = button(label, self.refresh)
                b.setCheckable(True)
                b.setChecked(True)
                b.setMinimumWidth(30)
                b.setFixedHeight(30)
                b.setStyleSheet('''QPushButton {border:1px solid #d5dcd8; border-radius:3px; background:#ffffff; font-size:16px; padding:0;}
                    QPushButton:checked {background:#dfede6; border-color:#7cac95; color:#155b42;}
                    QPushButton:hover {border-color:#177962;}''')
                grid.addWidget(b, index // 7, index % 7)
                buttons.append(b)
            self.jamo_buttons.append(buttons)
            self.jamo_grids.append(grid)
            area.addLayout(grid)
            filters.addWidget(group, 1)
        layout.addLayout(filters)
        view_group = QtGui.QGroupBox('보기 설정')
        bar = QtGui.QHBoxLayout(view_group)
        bar.setContentsMargins(0, 6, 0, 8)
        bar.setSpacing(18)
        self.sort = combo(['초성 → 중성 → 종성', '중성 → 초성 → 종성', '종성 → 초성 → 중성'])
        self.vowels = combo(['모임꼴순', '유니코드순'])
        self.breaks = combo(['초성·중성별', '초성별', '줄바꿈 없음'])
        for label, widget in (('글줄 정렬', self.sort), ('중성 배열', self.vowels), ('줄바꿈', self.breaks)):
            pair = QtGui.QHBoxLayout()
            pair.setSpacing(6)
            pair.addWidget(QtGui.QLabel(label))
            widget.setFixedWidth(180 if widget is self.sort else 120)
            pair.addWidget(widget)
            bar.addLayout(pair)
            widget.connect('currentIndexChanged(int)', self.refresh)
        self.zoom = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.zoom.setRange(72, 200)
        self.zoom.setValue(108)
        self.zoom.setMaximumWidth(100)
        self.zoom.connect('valueChanged(int)', self.zoom_changed)
        bar.addStretch()
        zoom_pair = QtGui.QHBoxLayout()
        zoom_pair.setSpacing(6)
        zoom_pair.addWidget(QtGui.QLabel('확대'))
        zoom_pair.addWidget(self.zoom)
        bar.addLayout(zoom_pair)
        self.show_boxes = QtGui.QCheckBox('목표 공간')
        self.show_boxes.setChecked(True)
        self.show_boxes.clicked.connect(self.refresh)
        bar.addWidget(self.show_boxes)
        layout.addWidget(view_group)
        range_bar = QtGui.QHBoxLayout()
        range_bar.addWidget(QtGui.QLabel('문자 범위'))
        self.highlight = combo(['표시 안 함', 'KS X 1001 · 2,350자', 'ADOBE-KR-9 · 2,780자'])
        self.highlight.setCurrentIndex(2)
        self.highlight.connect('currentIndexChanged(int)', self.refresh)
        range_bar.addWidget(self.highlight)
        self.range_only = QtGui.QCheckBox('범위만 보기')
        self.range_only.clicked.connect(self.refresh)
        range_bar.addWidget(self.range_only)
        self.metrics_mode = combo(['비례 · 기준', '공간 · unit', '보정 · Δunit', '정보 숨기기'])
        self.metrics_mode.connect('currentIndexChanged(int)', self.refresh)
        range_bar.addWidget(self.metrics_mode)
        self.metrics_role = combo(['초성 정보', '중성 정보', '종성 정보'])
        self.metrics_role.connect('currentIndexChanged(int)', self.role_changed)
        range_bar.addWidget(self.metrics_role)
        self.reference = combo(['전이 기준 자동'] + list(JAMO[0]))
        range_bar.addWidget(self.reference)
        self.reference.connect('currentIndexChanged(int)', lambda _: self.safe(self.change_reference))
        range_bar.addWidget(button('저장된 표본으로 관계 재추론', lambda: self.safe(self.infer)))
        range_bar.addStretch()
        layout.addLayout(range_bar)
        self.count = QtGui.QLabel('')
        layout.addWidget(self.count)
        work = QtGui.QHBoxLayout()
        work.setSpacing(8)
        self.scrollbar = QtGui.QScrollBar(QtCore.Qt.Vertical)
        self.hscrollbar = QtGui.QScrollBar(QtCore.Qt.Horizontal)
        self.canvas = GlyphCanvas(self)
        self.scrollbar.connect('valueChanged(int)', lambda _: self.canvas.update())
        self.hscrollbar.connect('valueChanged(int)', lambda _: self.canvas.update())
        viewport_layout = QtGui.QGridLayout()
        viewport_layout.setSpacing(0)
        viewport_layout.addWidget(self.canvas, 0, 0)
        viewport_layout.addWidget(self.scrollbar, 0, 1)
        viewport_layout.addWidget(self.hscrollbar, 1, 0)
        viewport_layout.setRowStretch(0, 1)
        viewport_layout.setColumnStretch(0, 1)
        work.addLayout(viewport_layout, 1)
        panel = QtGui.QFrame()
        panel.setObjectName('properties')
        panel.setFixedWidth(250)
        props = QtGui.QVBoxLayout(panel)
        props.setContentsMargins(16, 8, 0, 8)
        props.setSpacing(10)
        props.addWidget(QtGui.QLabel('선택 자소'))
        self.selection_label = QtGui.QLabel('선택 없음')
        self.selection_label.setObjectName('selection')
        props.addWidget(self.selection_label)
        self.role_combo = combo(['초성', '중성', '종성'])
        self.role_combo.connect('currentIndexChanged(int)', self.role_changed)
        props.addWidget(self.role_combo)
        props.addWidget(button('표시 글자 전체 선택', self.select_visible))
        space_group = QtGui.QGroupBox('이 글자 조정 · unit')
        self.single_edit_group = space_group
        space_layout = QtGui.QVBoxLayout(space_group)
        space_layout.setContentsMargins(0, 6, 0, 8)
        self.numbers = {}
        form = QtGui.QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        for key, label in zip(BOX_KEYS, ('좌우 이동', '위아래 이동', '너비 변화', '높이 변화')):
            spin = ScrollSafeSpinBox()
            spin.setRange(-100000, 100000)
            spin.connect('valueChanged(int)', self.numeric_changed)
            form.addRow(label, spin)
            self.numbers[key] = spin
        space_layout.addLayout(form)
        self.base_label = QtGui.QLabel('')
        self.base_label.setWordWrap(True)
        self.reset_button = button('이 글자 조정 취소', self.reset)
        space_layout.addWidget(self.reset_button)
        props.addWidget(space_group)
        batch_group = QtGui.QGroupBox('선택 글자 함께 조정 · unit')
        self.multi_edit_group = batch_group
        batch_layout = QtGui.QVBoxLayout(batch_group)
        self.batch_count = QtGui.QLabel('')
        batch_layout.addWidget(self.batch_count)
        self.batch_numbers = {}
        batch_form = QtGui.QFormLayout()
        for key, label in zip(BOX_KEYS, ('좌우 이동', '위아래 이동', '너비 변화', '높이 변화')):
            spin = ScrollSafeSpinBox()
            spin.setRange(-100000, 100000)
            spin.connect('valueChanged(int)', lambda _: self.safe(self.preview_batch))
            batch_form.addRow(label, spin)
            self.batch_numbers[key] = spin
        batch_layout.addLayout(batch_form)
        batch_layout.addWidget(button('일괄 목표 반영', lambda: self.safe(self.commit_batch)))
        batch_layout.addWidget(button('입력 취소', self.cancel_batch))
        props.addWidget(batch_group)
        props.addWidget(button('직전 일괄 조정 되돌리기', lambda: self.safe(self.undo_batch)))
        self.space_status = QtGui.QLabel('')
        self.space_status.setWordWrap(True)
        details_toggle = QtGui.QCheckBox('계산 근거')
        details = QtGui.QWidget()
        details_layout = QtGui.QVBoxLayout(details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.addWidget(self.base_label)
        details_layout.addWidget(self.space_status)
        details.setVisible(False)
        details_toggle.toggled.connect(details.setVisible)
        props.addWidget(details_toggle)
        props.addWidget(details)
        svc_group = QtGui.QGroupBox('소스 연결·글자 생성')
        svc_layout = QtGui.QVBoxLayout(svc_group)
        self.source_name = QtGui.QLineEdit()
        self.source_name.setPlaceholderText('연결할 소스 글립 이름')
        svc_layout.addWidget(self.source_name)
        self.design_anchor = combo([])
        self.anchor_choices = []
        self.design_anchor.connect('currentIndexChanged(int)', lambda _: self.safe(self.anchor_changed))
        svc_layout.addWidget(self.design_anchor)
        svc_layout.addWidget(button('소스 연결·선택 자소에 적용', lambda: self.safe(self.bind_source)))
        tools_toggle = QtGui.QCheckBox('소스 준비·진단')
        tools_panel = QtGui.QWidget()
        tools_layout = QtGui.QVBoxLayout(tools_panel)
        tools_layout.setContentsMargins(0, 0, 0, 0)
        tools_layout.addWidget(button('필요한 디자인 확인', lambda: self.safe(self.show_source_guide)))
        tools_layout.addWidget(button('4코너 소스 만들기', lambda: self.safe(self.prepare_source)))
        tools_layout.addWidget(button('기존 SVC 재계산', lambda: self.safe(self.recalculate_sources)))
        tools_layout.addWidget(button('선택 글자 미리보기', lambda: self.safe(self.preview_source)))
        tools_panel.setVisible(False)
        tools_toggle.toggled.connect(tools_panel.setVisible)
        svc_layout.addWidget(tools_toggle)
        svc_layout.addWidget(tools_panel)
        self.location_label = QtGui.QLabel('')
        self.location_label.setWordWrap(True)
        svc_layout.addWidget(self.location_label)
        props.addWidget(svc_group)
        props.addStretch()
        panel_scroll = QtGui.QScrollArea()
        panel_scroll.setWidgetResizable(True)
        panel_scroll.setFixedWidth(275)
        panel_scroll.setWidget(panel)
        work.addWidget(panel_scroll)
        layout.addLayout(work, 1)
        layout.addWidget(QtGui.QLabel('진한 윤곽: 분석 표본 / 회색 윤곽: 미분석 디자인 / 색상 윤곽: SVC / 연한 문자: 윤곽 없음'))
        self.target_toggle = QtGui.QCheckBox('빈 글자 일괄 생성')
        layout.addWidget(self.target_toggle)
        self.target_panel = QtGui.QGroupBox('FontLab 빈 글자 적용')
        self.target_toggle.toggled.connect(self.target_panel.setVisible)
        target = QtGui.QVBoxLayout(self.target_panel)
        row = QtGui.QHBoxLayout()
        row.addWidget(QtGui.QLabel('FontLab 적용 대상'))
        self.target_mode = combo(['지정 문자열', '현재 보기', 'ADOBE-KR-9 2,780자', 'KS X 1001 2,350자'])
        row.addWidget(self.target_mode)
        self.target_mode.connect('currentIndexChanged(int)', lambda _: self.safe(self.change_target))
        self.apply_button = button('FontLab 빈 글립에 SVC 적용', lambda: self.safe(self.apply_sources))
        row.addWidget(self.apply_button)
        target.addLayout(row)
        self.target = QtGui.QPlainTextEdit()
        self.target.setMaximumHeight(60)
        self.target.textChanged.connect(self.target_edited)
        target.addWidget(self.target)
        self.target_count = QtGui.QLabel('')
        target.addWidget(self.target_count)
        layout.addWidget(self.target_panel)
        self.target_panel.hide()
        self.stack.addWidget(page)

    def change_master(self, index):
        if self.syncing:
            return
        if self.preview_timer.isActive():
            self.preview_pending()
        self.preview_timer.stop()
        requested = str(value(self.master.currentText))
        if self.layer_name is not None and not self.flush_save():
            self.syncing = True
            self.master.setCurrentIndex(self.adapter.masters().index(self.layer_name))
            self.syncing = False
            return
        def load():
            try:
                session = self.adapter.load(requested)
            except ValueError:
                self.recover_button.show()
                raise
            self.recover_button.hide()
            self.adapter.read_advances(requested)
            self.layer_name = requested
            self.install_session(session)
        self.safe(load)
        if self.layer_name != requested and self.layer_name is not None:
            self.syncing = True
            self.master.setCurrentIndex(self.adapter.masters().index(self.layer_name))
            self.syncing = False

    def recover_settings(self):
        answer = QtGui.QMessageBox.question(self, '설정 복구',
            '읽을 수 없는 저장값을 별도 Font lib 키에 보관합니다.\n현재 분석이 선택 마스터와 일치하는지 확인한 뒤 그대로 저장합니다.\n분석 전이면 빈 설정으로 시작합니다. 폰트 윤곽은 변경하지 않습니다. 진행할까요?',
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if answer == QtGui.QMessageBox.Yes:
            requested = self.layer_name or str(value(self.master.currentText))
            self.adapter.recover_settings(requested, self.session)
            self.adapter.read_advances(requested)
            self.layer_name = requested
            self.recover_button.hide()
            self.refresh()
            self.status.setText('설정 복구 완료 · {} 마스터 연결 · 현재 분석 유지'.format(requested))

    def install_session(self, session):
        self.save_timer.stop()
        self.edit_selection = set()
        self.session = session
        self.paths = {}
        self.svc_paths = {}
        if session.observations:
            current, paths, _ = self.adapter.measure(''.join(session.observations), self.layer_name, session.grouped_vowel)
            self.paths = {c: path for c, path in paths.items()
                          if current[c]['boxes'] == session.observations[c]['boxes']}
        self.selected = None
        self.origin = None
        self.syncing = True
        self.sample.setPlainText(session.sample_text)
        self.grouped_vowel.setChecked(session.grouped_vowel)
        self.target_mode.setCurrentIndex(0)
        self.target.setPlainText(session.target_text)
        self.syncing = False
        self.issues.setPlainText('저장된 측정값은 스냅샷입니다. 표본 분석으로 현재 윤곽을 다시 읽습니다.' if session.observations else '')
        self.refresh()

    def analyze(self):
        self.adapter.require_master(self.layer_name)
        if not value(self.mapping.checked):
            raise ValueError('요소 순서 규약을 확인하세요. 자동 역할 추측은 하지 않습니다.')
        if self.session.overrides:
            answer = QtGui.QMessageBox.question(self, '표본 다시 분석',
                     '기존 목표 공간 보정을 지우고 현재 윤곽에서 다시 측정할까요?',
                     QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if answer != QtGui.QMessageBox.Yes:
                return
        text = str(value(self.sample.plainText))
        if not characters(text):
            raise ValueError('표본 문자열에 한글 완성형이 없습니다.')
        grouped = bool(value(self.grouped_vowel.checked))
        records, paths, issues = self.adapter.measure(text, self.layer_name, grouped)
        if not records:
            self.issues.setPlainText('\n'.join(issues))
            raise ValueError('분석 가능한 표본이 없습니다. 기존 측정값은 유지합니다.')
        self.preview_timer.stop()
        self.pending_update = None
        self.session.sample_text = text
        self.session.observations = records
        self.session.overrides = {}
        self.session.batch_undo = None
        self.session.infer()
        self.svc_paths = {}
        self.session.grouped_vowel = grouped
        self.session.dirty = True
        self.paths = paths
        self.origin = None
        self.selected = None
        self.issues.setPlainText('실측 {}자 / 추론 {}자 / 측정 제외 {}자\n{}'.format(
            len(records), len(self.session.predictions), len(issues), '\n'.join(issues)))
        self.status.setText('실측·관계 추론 완료. 폰트 윤곽과 컴포넌트는 변경하지 않았습니다.')
        self.refresh()
        self.schedule_save()
        return True

    def infer(self):
        self.session.infer()
        self.svc_paths = {}
        self.origin = None
        self.refresh()
        self.status.setText('관계 추론 {}자 · 실측은 유지, 추론값을 다시 학습에 사용하지 않음'.format(len(self.session.predictions)))
        self.schedule_save()

    def bind_source(self):
        self.adapter.require_master(self.layer_name)
        if not self.selected:
            raise ValueError('자소를 선택하세요.')
        name = str(value(self.source_name.text)).strip()
        self.adapter.source_layers(name, self.layer_name)
        key = source_key(self.selected, self.role)
        self.preview_timer.stop()
        text = self.edit_selection
        targets = ''.join(c for c in self.canvas.characters if c in text and source_key(c, self.role) == key)
        if not targets:
            raise ValueError('파생할 글자를 선택하세요.')
        if any(value(s.value) for s in self.batch_numbers.values()):
            self.commit_batch()
            self.preview_timer.stop()
        from .svc import source_mapping
        source_mapping(self.session, self.selected, self.role)
        answer = QtGui.QMessageBox.question(self, '소스 연결·자소 교체',
            '{}자 중 표본과 기존 직접 윤곽은 제외합니다.\n연결된 기존 SVC는 location·이동값만 갱신합니다.\n관리 중인 소스 변경은 마스크에 백업하고 교체합니다.\n빈 글자는 대응 표본의 나머지 자소로 채웁니다. 진행할까요?'.format(len(targets)),
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if answer != QtGui.QMessageBox.Yes:
            return
        from .svc import design_candidates
        candidates = design_candidates(self.session, self.selected, self.role)
        if not decompose(self.selected)[2] and key not in self.session.design_anchors and len(candidates) == 1:
            self.session.design_anchors[key] = candidates[0]
        self.session.sources[key] = name
        self.session.dirty = True
        self.svc_paths = {}
        self.schedule_save()
        applied, skipped, paths = self.adapter.derive_role(self.session, targets, self.role, name, self.layer_name)
        self.show_apply_result(applied, skipped, paths)

    def show_apply_result(self, applied, skipped, paths):
        for char, glyph_name in applied:
            outline = QtGui.QPainterPath()
            for shape in self.adapter.font.glyph(glyph_name).shapes(self.layer_name):
                outline.addPath(self.adapter.shape_path(shape))
            self.paths[char] = outline
        self.svc_paths.update(paths)
        self.canvas.update()
        messages = []
        for char, glyph_name in applied:
            report = self.adapter.apply_reports[char]
            messages.append('{} · {} · width={width}, height={height} · 마스크 추가 {}개 (총 {}개)'.format(
                char, '기존 SVC 갱신' if report['updated'] else '삽입',
                report['backedUp'], report['maskCount'], **report['location']))
        messages += ['건너뜀: {} · {}'.format(*item) for item in skipped]
        self.location_label.setText('폰트 적용 {}자 / 건너뜀 {}자\n{}'.format(
            len(applied), len(skipped), '\n'.join(messages[:4])))
        self.issues.setPlainText('\n'.join(messages))
        self.status.setText('폰트 적용 {}자 / 건너뜀 {}자 · 상세: 표본 탭'.format(len(applied), len(skipped)))
        self.schedule_save()

    def anchor_changed(self):
        if self.syncing or not self.selected:
            return
        if decompose(self.selected)[2]:
            return
        index = value(self.design_anchor.currentIndex)
        if not 0 <= index < len(self.anchor_choices):
            return
        key = source_key(self.selected, self.role)
        anchor = self.anchor_choices[index]
        if anchor:
            self.session.design_anchors[key] = anchor
        else:
            self.session.design_anchors.pop(key, None)
        self.session.dirty = True
        self.svc_paths = {}
        self.canvas.update()
        self.schedule_save()

    def show_source_guide(self):
        from .svc import source_design_guide, format_source_guide
        if not self.selected:
            raise ValueError('자소를 선택하세요.')
        source = self.session.sources.get(source_key(self.selected, self.role))
        guide = source_design_guide(self.session, self.selected, self.role)
        previous = getattr(self, 'source_guide_dialog', None)
        if previous is not None:
            previous.close()
        dialog = QtGui.QDialog(self)
        dialog.setWindowTitle('4코너 소스 · 디자인할 글자')
        dialog.resize(760, 560)
        layout = QtGui.QVBoxLayout(dialog)
        text = QtGui.QPlainTextEdit()
        text.setReadOnly(True)
        heading = ('저장된 표본 기준 · 연결 소스 {}\n\n'.format(source)
                   if source else '')
        text.setPlainText(heading + format_source_guide(guide))
        layout.addWidget(text)
        char, role = self.selected, self.role
        layout.addWidget(button('표본 재측정·안내 갱신',
            lambda checked=False: self.safe(lambda: self.refresh_design_guide(char, role))))
        layout.addWidget(button('닫기', lambda checked=False: dialog.close()))
        self.source_guide_dialog = dialog
        dialog.show()
        return guide

    def refresh_design_guide(self, char, role):
        if not self.analyze():
            return
        self.selected, self.role = char, role
        self.origin = self.session.box(char, role)
        name = self.adapter.existing_source(self.session, char, role, self.layer_name)
        if name:
            self.adapter.refresh_source_guide(self.session, char, role, self.layer_name)
        self.sync_panel()
        self.show_source_guide()
        self.schedule_save()
        self.status.setText('표본·코너 안내 갱신됨 · 소스 윤곽 유지')
        if self.session.sources:
            self.recalculate_sources()

    def recalculate_sources(self):
        answer = QtGui.QMessageBox.question(self, '기존 SVC 재계산',
            '현재 마스터의 연결된 기존 SVC 전체를 현재 표본과 실제 소스 윤곽에 맞춰 재계산합니다.\n'
            '화면 밖 글자도 포함합니다. 새 컴포넌트 삽입이나 마스크 추가는 하지 않습니다.\n'
            '관계 충돌은 우선순위 1위 결과를 적용합니다. 소스로 재현 불가능한 항목은 기존 값을 유지합니다. 진행할까요?',
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if answer != QtGui.QMessageBox.Yes:
            return
        self.preview_timer.stop()
        self.pending_update = None
        applied, skipped, paths = self.adapter.recalculate_applied(self.session, self.layer_name)
        self.show_apply_result(applied, skipped, paths)
        self.display_paths = {}
        self.relation_cache = {}
        self.status.setText('기존 SVC {}개 재계산 / 건너뜀 {}건 · 소스 윤곽 유지'.format(len(applied), len(skipped)))

    def prepare_source(self):
        from .svc import source_plan
        self.adapter.require_master(self.layer_name)
        if not self.selected:
            raise ValueError('자소를 선택하세요.')
        existing = self.adapter.existing_source(self.session, self.selected, self.role, self.layer_name)
        if existing:
            self.source_name.setText(existing)
            self.location_label.setText('기존 소스 이름 입력됨 · 윤곽과 레이어는 변경하지 않았습니다.')
            return
        self.show_source_guide()
        plan = source_plan(self.session, self.selected, self.role)
        description = ('대상 자소 윤곽이 없어 빈 4코너 레이어와 width/height 앵커를 만듭니다.\n안내된 극값 조건에 맞춰 직접 디자인하세요. 기준 자소의 크기는 대입하지 않습니다.'
                       if plan['empty'] else '대상 자소의 실측 윤곽을 원래 크기로 복사하고 원점만 정규화합니다.\n복사 윤곽은 출발점입니다. 안내된 극값 조건에 맞춰 각 코너를 직접 수정하세요.\n서로 다른 표본의 컨투어·노드 호환성도 확인하세요.')
        answer = QtGui.QMessageBox.question(self, 'SVC 소스 초안',
            description + '\n기존 글립은 유지합니다. 진행할까요?',
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if answer != QtGui.QMessageBox.Yes:
            return
        name, plan = self.adapter.prepare_source(self.session, self.selected, self.role, self.layer_name)
        self.source_name.setText(name)
        self.location_label.setText('빈 4코너 생성됨 · 각 레이어에 자소 디자인 필요' if plan['empty'] else '소스 초안 생성됨 · 디자인 수정 필요')
        self.issues.setPlainText(name + '\n' + '\n'.join(
            '{} · 복사 윤곽 {}'.format(c['location'], c['donor'] or '없음 · 조건에 맞춰 디자인') for c in plan['corners']))
        self.show_source_guide()
        self.schedule_save()

    def preview_source(self):
        from .svc import source_mapping
        self.adapter.require_master(self.layer_name)
        if not self.selected:
            return
        name = self.session.sources.get(source_key(self.selected, self.role))
        target, normalized, correction, placement = source_mapping(self.session, self.selected, self.role)
        if not name or target is None:
            raise ValueError('목표 공간과 연결된 소스가 필요합니다.')
        component, result = self.adapter.map_component(name, self.layer_name, target, normalized, correction)
        path = self.adapter.shape_path(component)
        if path.isEmpty():
            raise ValueError('SVC 평가 결과에 표시할 윤곽이 없습니다. 소스 레이어를 확인하세요.')
        self.svc_paths[(self.selected, self.role)] = path
        self.location_label.setText('{} · 미리보기 / 폰트 미적용\nwidth={width}, height={height}\n이동 {delta} · 크기 오차 {error:.2f} unit'.format(
            self.selected, **result['location'], delta=result['delta'], error=result['error']))
        if result.get('mode') == 'reference':
            self.location_label.setText(str(value(self.location_label.text)) +
                '\nSVC 실제 W {:.1f} / H {:.1f}\n관측 변화 없음: {}'.format(
                    result['box']['w'], result['box']['h'], ', '.join(result['unobservedAxes']) or '없음'))
        placement_text = ('크기·배치 기준: ' + ', '.join(placement['anchors']) + ' · 변화율/이동량 적용'
                          if placement['mode'] in ('design-anchor', 'mieum-context') else
                          '배치 기준 미확정: 기준 계열 위치를 임시 사용' if placement['mode'] == 'unanchored' else
                          '대상 실측/추론 위치 사용')
        self.location_label.setText(str(value(self.location_label.text)) + '\n' + placement_text)
        if placement.get('conflicts'):
            self.location_label.setText(str(value(self.location_label.text)) + '\n관계 충돌 · 우선순위 1위 결과 사용')
        self.canvas.update()

    def schedule_preview(self):
        self.preview_timer.stop()
        self.pending_update = None
        if self.selected and self.session.sources.get(source_key(self.selected, self.role)):
            key = source_key(self.selected, self.role)
            targets = [c for c in self.edit_selection if source_key(c, self.role) == key]
            self.pending_update = (targets, self.role, self.session.sources[key])
            self.location_label.setText('계산 대기 · 기존 SVC는 자동 갱신 / 미삽입 글자는 미리보기')
            self.preview_timer.start()
        else:
            self.location_label.setText('목표 변경됨 · 소스 연결 필요 / 폰트 미적용')

    def preview_pending(self):
        self.preview_timer.stop()
        pending, self.pending_update = self.pending_update, None
        try:
            if pending:
                targets, role, name = pending
                applied, skipped, paths = self.adapter.derive_role(
                    self.session, ''.join(targets), role, name, self.layer_name, update_only=True)
                if applied or skipped:
                    self.show_apply_result(applied, skipped, paths)
                    return
            self.preview_source()
        except Exception as error:
            self.svc_paths.pop((self.selected, self.role), None)
            self.location_label.setText('미리보기 실패 / 폰트 미적용\n' + str(error))
            self.canvas.update()

    def apply_sources(self):
        self.adapter.require_master(self.layer_name)
        answer = QtGui.QMessageBox.question(self, 'FontLab 폰트 변경',
            '적용 대상의 빈 레이어에 초·중·종성 SVC를 넣습니다. 기존 윤곽·컴포넌트는 건너뜁니다.\n소스 초안 디자인을 확인했나요?',
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if answer != QtGui.QMessageBox.Yes:
            return
        applied, skipped = self.adapter.apply_empty(self.session, self.session.target_text, self.layer_name)
        self.display_paths = {}
        self.canvas.update()
        self.issues.setPlainText('적용 {}자 / 건너뜀 {}자\n{}'.format(len(applied), len(skipped),
                              '\n'.join('{}: {}'.format(*item) for item in skipped)))
        self.status.setText('FontLab 적용 {}자 · 건너뜀 {}자 · 상세는 표본 탭 · 파일 저장은 별도'.format(len(applied), len(skipped)))
        self.schedule_save()

    def schedule_save(self):
        if not self.syncing and self.session.dirty and self.layer_name is not None:
            self.save_timer.start()

    def autosave(self):
        if self.canvas.drag is not None:
            self.schedule_save()
            return
        self.flush_save()

    def flush_save(self):
        self.save_timer.stop()
        if not self.session.dirty:
            return True
        try:
            if self.layer_name is None:
                raise ValueError('마스터를 먼저 불러오세요.')
            self.adapter.save(self.layer_name, self.session)
        except Exception as error:
            self.status.setText('자동 저장 실패 · 변경값 유지: ' + str(error))
            return False
        self.status.setText('Font lib 자동 저장됨 · 폰트 파일 저장은 FontLab에서 실행')
        return True

    def sample_edited(self):
        if not self.syncing:
            self.session.sample_text = str(value(self.sample.plainText))
            self.session.dirty = True
            self.schedule_save()

    def select_group(self, role, action):
        for b in self.jamo_buttons[role]:
            b.setChecked(not value(b.checked) if action == 'invert' else action == 'all')
        self.refresh()

    def refresh(self, *args):
        self.relation_cache = {}
        self.display_paths = {}
        if not hasattr(self, 'canvas') or self.syncing:
            return
        selections = [{i for i, b in enumerate(buttons) if value(b.checked)} for buttons in self.jamo_buttons]
        order = ((0, 1, 2), (1, 0, 2), (2, 0, 1))[value(self.sort.currentIndex)]
        shape = value(self.vowels.currentIndex) == 0
        sequence = VOWEL_ORDER if shape else JAMO[1]
        for b in self.jamo_buttons[1]:
            self.jamo_grids[1].removeWidget(b)
        for pos, jamo in enumerate(sequence):
            self.jamo_grids[1].addWidget(self.jamo_buttons[1][JAMO[1].index(jamo)], pos // 7, pos % 7)
        self.canvas.characters = ordered_characters(selections, order, 'shape' if shape else 'unicode')
        index = value(self.highlight.currentIndex)
        self.range_only.setEnabled(bool(index))
        if index and value(self.range_only.checked):
            allowed = self.repertoires[index-1]
            self.canvas.characters = [c for c in self.canvas.characters if c in allowed]
        self.edit_selection.intersection_update(self.canvas.characters)
        self.cancel_batch()
        if self.selected not in self.canvas.characters:
            self.selected = next((c for c in self.canvas.characters if c in self.session.observations),
                                 self.canvas.characters[0] if self.canvas.characters else None)
            self.origin = None
        if self.selected and self.origin is None:
            self.origin = self.session.box(self.selected, self.role)
        measured = sum(c in self.session.observations for c in self.canvas.characters)
        self.count.setText('보기 {}자 · 실측 {}자 · 선택 자소의 관계 근거는 글줄 하단에 표시'.format(
            len(self.canvas.characters), measured))
        self.canvas.reflow()
        self.sync_panel()
        self.update_target_count()

    def outline_for_display(self, char):
        if char in self.paths:
            return self.paths[char], char in self.session.observations
        if char not in self.display_paths:
            self.display_paths[char] = self.adapter.display_outline(char, self.layer_name)
        return self.display_paths[char], False

    def select(self, char, role):
        if self.preview_timer.isActive():
            self.preview_pending()
        self.preview_timer.stop()
        if char != self.selected or role != self.role:
            self.origin = self.session.box(char, role)
            self.location_label.setText('')
        self.selected, self.role = char, role
        self.sync_panel()
        self.canvas.update()

    def change_reference(self):
        if self.syncing:
            return
        self.session.reference_initial = value(self.reference.currentIndex) - 1
        if self.session.reference_initial < 0:
            self.session.reference_initial = None
        self.infer()

    def select_visible(self):
        self.edit_selection = set(self.canvas.characters)
        self.cancel_batch()
        self.sync_panel()

    def select_cell(self, char, role, extend=False, toggle=False):
        previous = self.selected
        self.cancel_batch()
        if extend and previous in self.canvas.characters:
            a, b = sorted((self.canvas.characters.index(previous), self.canvas.characters.index(char)))
            self.edit_selection.update(self.canvas.characters[a:b+1])
        elif toggle:
            self.edit_selection.symmetric_difference_update({char})
        else:
            self.edit_selection = {char}
        self.select(char, self.role if extend or toggle else role)

    def display_box(self, char, role):
        if decompose(char)[2]:
            from .mieum_relations import estimate
            key = (char, role)
            if key not in self.relation_cache:
                try:
                    self.relation_cache[key] = estimate(self.session.observations, char, role,
                                                        self.session.reference_initial)['box']
                except ValueError:
                    self.relation_cache[key] = None
            box = self.relation_cache[key]
            if box is None:
                return None
            base = self.session.base_box(char, role)
            edited = (self.batch_preview[char] if role == self.role and char in self.batch_preview
                      else self.session.box(char, role))
            return {k: box[k] + (edited[k]-base[k] if edited is not None and base is not None else 0)
                    for k in BOX_KEYS}
        if role == self.role and char in self.batch_preview:
            return self.batch_preview[char]
        return self.session.box(char, role)

    def cancel_batch(self):
        self.batch_preview = {}
        if hasattr(self, 'batch_numbers'):
            syncing = self.syncing
            self.syncing = True
            for spin in self.batch_numbers.values():
                spin.setValue(0)
            self.syncing = syncing
            self.batch_count.setText('선택 {}자'.format(len(self.edit_selection)))
        self.canvas.update()

    def preview_batch(self):
        if self.syncing or self.preview:
            return
        self.batch_preview = {}
        delta = {k: value(s.value) for k, s in self.batch_numbers.items()}
        pending, skipped = self.session.preview_batch(self.edit_selection, self.role, delta)
        self.batch_preview = pending
        self.batch_count.setText('적용 {}자 · 공간 없음/역할 없음 제외 {}자'.format(len(pending), len(skipped)))
        self.preview_timer.stop()
        self.location_label.setText('일괄 목표 입력 중 / 폰트 미적용')
        self.canvas.update()

    def commit_batch(self):
        if self.preview:
            return
        if not any(value(s.value) for s in self.batch_numbers.values()):
            return
        self.preview_batch()
        if not self.batch_preview:
            return
        self.session.commit_batch(self.batch_preview, self.role)
        self.svc_paths = {}
        self.cancel_batch()
        self.sync_panel()
        self.schedule_save()
        self.schedule_preview()

    def undo_batch(self):
        if self.preview:
            return
        self.session.undo_batch()
        self.svc_paths = {}
        self.cancel_batch()
        self.sync_panel()
        self.schedule_save()
        self.schedule_preview()

    def sync_panel(self):
        self.syncing = True
        self.reference.setCurrentIndex(0 if self.session.reference_initial is None else self.session.reference_initial + 1)
        box = self.session.box(self.selected, self.role) if self.selected else None
        base = self.session.base_box(self.selected, self.role) if self.selected else None
        self.selection_label.setText(self.selected or '선택 없음')
        self.role_combo.setCurrentIndex(self.role)
        self.metrics_role.setCurrentIndex(self.role)
        for key, spin in self.numbers.items():
            spin.setEnabled(box is not None and not self.preview and len(self.edit_selection) <= 1)
            spin.setRange(1-base[key] if base and key in ('w', 'h') else -100000, 100000)
            spin.setValue(box[key]-base[key] if box else 0)
        self.base_label.setText('기준 {}: {}\n목표: {}'.format(self.session.state(self.selected),
            ', '.join('{} {}'.format(k, base[k]) for k in BOX_KEYS),
            ', '.join('{} {}'.format(k, box[k]) for k in BOX_KEYS)) if box else '기준 공간 없음')
        multiple = len(self.edit_selection) > 1
        self.single_edit_group.setVisible(not multiple)
        self.multi_edit_group.setVisible(multiple)
        self.reset_button.setEnabled(box is not None and not self.preview and len(self.edit_selection) <= 1)
        self.space_status.setText('목표 박스만 편집합니다. 원본 윤곽은 유지됩니다.' if box else '공간 미정 · 표본 또는 추론 결과 필요')
        prediction = self.session.predictions.get(self.selected)
        if prediction and prediction.get('mode') != 'reference':
            self.space_status.setText('추론 근거: {}\n관계별 검증 MAE {:.2f}~{:.2f} · 추정 간 차이 {:.2f} unit'.format(
                ' '.join(e['donor'] for e in prediction['evidence']),
                min(e['fitMAE'] for e in prediction['evidence']),
                max(e['fitMAE'] for e in prediction['evidence']), prediction['spread']))
        if prediction and prediction.get('mode') == 'reference':
            self.base_label.setText('관계 참고 (대상 자소 크기 아님): {}\n보정 후 참고: {}'.format(
                ', '.join('{} {}'.format(k, base[k]) for k in BOX_KEYS),
                ', '.join('{} {}'.format(k, box[k]) for k in BOX_KEYS)) if box else '관계 참고 공간 없음')
            evidence = prediction['evidence']
            self.space_status.setText('{} 기준 · {} · {}\n표본: {}\n비교: {}\n수치는 관계 참고 공간입니다. 실제 치수는 SVC 평가 후 공간 · unit에서 확인하세요.'.format(
                JAMO[0][prediction['referenceInitial']], prediction.get('referenceChar', ''),
                '검증 부족' if prediction.get('basis') == 'unverified' else '미보정 전이',
                ' '.join(e['donor'] for e in evidence),
                ', '.join(a+'→'+b for e in evidence for a,b in e['pairs'])))
        self.batch_count.setText('선택 {}자'.format(len(self.edit_selection)))
        self.source_name.setText(self.session.sources.get(source_key(self.selected, self.role), '') if self.selected else '')
        from .svc import design_candidates
        candidates = design_candidates(self.session, self.selected, self.role) if self.selected else []
        self.anchor_choices = [None] + candidates
        self.design_anchor.clear()
        label = ('소스 범위 사용 · 위치 잠정' if not candidates else
                 '자동: ' + candidates[0] if len(candidates) == 1 else '기준 글자를 선택하세요')
        self.design_anchor.addItems([label] + candidates)
        anchor = self.session.design_anchors.get(source_key(self.selected, self.role)) if self.selected else None
        self.design_anchor.setCurrentIndex(self.anchor_choices.index(anchor) if anchor in self.anchor_choices else 0)
        closed = bool(self.selected and decompose(self.selected)[2])
        self.design_anchor.setEnabled(not closed)
        if closed:
            from .mieum_relations import baseline
            required = baseline(self.selected, self.role)
            self.design_anchor.clear()
            self.design_anchor.addItems(['ㅁ 조건 기준: ' + required])
            try:
                from .svc import source_mapping
                mapped, _, _, relation = source_mapping(self.session, self.selected, self.role)
                self.base_label.setText('관계 기준 목표: {}\n수동 Δ는 기준 목표에 한 번 적용합니다.'.format(
                    ', '.join('{} {:.2f}'.format(k, mapped[k]) for k in BOX_KEYS)))
                self.space_status.setText('받친글자 · {}\n근거: {}\n관계: {}'.format(
                    '실측 대비 전이' if relation['mode'] == 'local-transfer' else 'ㅁ 기준',
                    ', '.join(relation['anchors']), ', '.join(a+'→'+b for a,b in relation.get('pairs', [])) or '직접 실측'))
                self.design_anchor.clear()
                self.design_anchor.addItems(['실제 계산 기준: ' + ', '.join(relation['anchors'])])
                if relation.get('crossVowel'):
                    self.space_status.setText(str(value(self.space_status.text)) + '\n같은 모임꼴의 다른 모음에서 측정한 관계 전이: 디자인 검토 필요')
                if relation['mode'] == 'local-transfer':
                    self.space_status.setText(str(value(self.space_status.text)) +
                        ('\n공통 실측 1조건 · 검증 제한' if relation['support'] == 1 else
                         '\n공통 실측 {}조건 · 대비 검증 통과'.format(relation['support'])))
                if relation.get('conflicts'):
                    self.space_status.setText(str(value(self.space_status.text)) +
                        '\n우선순위 1위 결과로 적용\n충돌 기준: ' +
                        ', '.join(r['anchors'][0] for r in relation['conflicts']))
                if self.role == 1 and len(relation.get('pairs', [])) == 2:
                    self.space_status.setText(str(value(self.space_status.text)) + '\n초성·종성 효과의 독립 전이 가정: 디자인 검토 필요')
            except ValueError as error:
                self.space_status.setText(str(error))
                self.base_label.setText('ㅁ 기준 근거 부족 · 필요한 표본 디자인을 추가하세요.')
                for spin in self.numbers.values():
                    spin.setEnabled(False)
        self.syncing = False

    def role_changed(self, role):
        if not self.syncing:
            self.cancel_batch()
            self.select(self.selected, role)

    def numeric_changed(self, *args):
        if self.syncing or not self.selected or self.preview:
            return
        base = self.session.base_box(self.selected, self.role)
        self.session.set_box(self.selected, self.role, {k: base[k]+value(s.value) for k, s in self.numbers.items()})
        self.svc_paths = {}
        self.sync_panel()
        self.canvas.update()
        self.schedule_save()
        self.schedule_preview()

    def reset(self):
        if self.selected:
            self.session.reset(self.selected, self.role)
            self.svc_paths = {}
            self.origin = self.session.box(self.selected, self.role)
            self.sync_panel()
            self.canvas.update()
            self.schedule_save()
            self.schedule_preview()

    def zoom_changed(self, size):
        self.canvas.cell = size
        self.canvas.reflow()

    def change_tab(self, index):
        if self.preview_timer.isActive():
            self.preview_pending()
        self.cancel_batch()
        self.preview_timer.stop()
        self.preview = False
        self.stack.setCurrentIndex(0 if index == 0 else 1)
        self.sync_panel()
        self.canvas.update()

    def change_target(self):
        if self.syncing:
            return
        mode = value(self.target_mode.currentIndex)
        if mode == 1:
            self.target.setPlainText(''.join(self.canvas.characters))
        elif mode in (2, 3):
            self.target.setPlainText(repertoire(1 if mode == 2 else 0))

    def target_edited(self):
        if not self.syncing:
            self.session.target_text = str(value(self.target.plainText))
            self.session.dirty = True
            self.update_target_count()
            self.schedule_save()

    def update_target_count(self):
        targets = characters(self.session.target_text)
        measured = sum(c in self.session.observations for c in targets)
        inferred = sum(c in self.session.predictions for c in targets)
        self.target_count.setText('적용 후보 {}자 · 실측 {}자 · 추론 {}자 · 기존 디자인 보존'.format(len(targets), measured, inferred))

    def closeEvent(self, event):
        global _window
        if self.preview_timer.isActive():
            self.preview_pending()
        if not self.flush_save():
            answer = QtGui.QMessageBox.question(self, '자동 저장 실패',
                str(value(self.status.text)) + '\n\n저장되지 않은 설정 변경을 버리고 닫을까요?',
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if answer != QtGui.QMessageBox.Yes:
                event.ignore()
                return
        self.save_timer.stop()
        self.preview_timer.stop()
        if _window is self:
            _window = None
        event.accept()


def show():
    global _window
    if _window is not None:
        try:
            _window.adapter.check_active()
        except ValueError:
            if not _window.flush_save():
                return _window
            _window.close()
            _window = None
        else:
            _window.show()
            _window.raise_()
            return _window
    try:
        _window = RelationWindow()
        _window.show()
    except Exception as error:
        traceback.print_exc()
        QtGui.QMessageBox.warning(None, 'Hangul Parametric', str(error))
    return _window
