"""Quiet, list-based PythonQt UI. File/network work stays in the worker."""
import queue
import threading
from PythonQt import QtCore, QtGui

from mwsm_core import Cancelled, Downloader, ManagerError, Store, REPOSITORY, RUNTIME_VERSION, is_newer_version
from mwsm_host import compatibility, refresh_scripts, prepare_https

_windows = []

STYLE = '''
QDialog, QScrollArea, QWidget#list { background: #fafafa; color: #171717; }
QLabel { color: #171717; background: transparent; font-size: 13px; }
QLabel#title { font-size: 24px; font-weight: 600; }
QLabel#muted { color: #727272; font-size: 12px; }
QLabel#rowStatus { color: #626262; font-size: 12px; }
QWidget#row { border-bottom: 1px solid #e9e9e9; background: transparent; }
QPushButton { color: #444; background: transparent; border: 1px solid transparent;
              border-radius: 7px; padding: 7px 12px; font-size: 13px; }
QPushButton:hover { background: #eeeeee; color: #111; }
QPushButton:focus { border: 1px solid #8b8b8b; }
QPushButton:disabled { color: #aaa; }
QPushButton#filter:checked { background: #eaeaea; color: #111; font-weight: 600; }
QPushButton#name { text-align: left; font-size: 17px; font-weight: 400; padding: 0px; border-radius: 3px; }
QPushButton#name:hover { background: transparent; color: #555; }
QPushButton#pick { padding: 0px; border: 1px solid #c9c9c9; border-radius: 11px; font-size: 15px; }
QPushButton#pick:checked { background: #171717; border-color: #171717; color: white; }
QPushButton#pick:disabled { border-color: #e2e2e2; background: #f3f3f3; }
QPushButton#primary { background: #171717; color: #fff; border-radius: 10px; padding: 12px; font-weight: 600; }
QPushButton#primary:hover { background: #333; }
QPushButton#primary:disabled { background: #e8e8e8; color: #929292; }
QPushButton#danger { color: #a63434; }
QScrollArea { border: none; }
QProgressBar { border: none; background: #e8e8e8; border-radius: 2px; }
QProgressBar::chunk { background: #333; border-radius: 2px; }
QCheckBox { color: #333; spacing: 8px; font-size: 13px; }
'''


def value(obj, name):
    result = getattr(obj, name)
    return result() if callable(result) else result


def label(text, name=None):
    widget = QtGui.QLabel(text)
    widget.setTextFormat(QtCore.Qt.PlainText)
    if name:
        widget.setObjectName(name)
    return widget


def button(text, callback, name=None):
    widget = QtGui.QPushButton(text)
    widget.setAutoDefault(False)
    if name:
        widget.setObjectName(name)
    widget.connect('clicked()', callback)
    return widget


class ManagerWindow:
    def __init__(self, env, bootstrap=False):
        prepare_https()
        self.env, self.bootstrap = env, bootstrap
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.store = Store(env['user_data'])
        self.manifest = None
        self.offline = None
        self.busy = False
        self.rows = []
        self.errors = {}
        self.checked = set()
        self.filter = 'all'
        self.detail_dialog = None
        self.dialog = QtGui.QDialog()
        self.dialog.setWindowTitle(f"MW Script Manager {RUNTIME_VERSION}")
        self.dialog.setStyleSheet(STYLE)
        self.dialog.resize(760, 700)
        self.dialog.setMinimumSize(620, 480)
        layout = QtGui.QVBoxLayout(self.dialog)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(16)
        header = QtGui.QHBoxLayout()
        header.addWidget(label('MW Script Manager', 'title'))
        header.addStretch()
        self.options = button('설정', self.show_settings)
        header.addWidget(self.options)
        layout.addLayout(header)
        toolbar = QtGui.QHBoxLayout()
        toolbar.setSpacing(4)
        self.filters = {}
        for key, title in (('all', '전체'), ('installed', '설치됨'), ('updates', '업데이트')):
            control = button(title, lambda k=key: self.set_filter(k), 'filter')
            control.setCheckable(True)
            control.setChecked(key == self.filter)
            self.filters[key] = control
            toolbar.addWidget(control)
        self.select_all = button('모두 선택', self.select_updates)
        self.select_all.hide()
        toolbar.addWidget(self.select_all)
        toolbar.addStretch()
        self.reload = button('새로고침', self.refresh)
        toolbar.addWidget(self.reload)
        layout.addLayout(toolbar)
        self.scroll = QtGui.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.scroll, 1)
        self.list_content = None
        self.primary = button('선택 설치', self.install_selected, 'primary')
        self.primary.setMinimumHeight(46)
        self.primary.setEnabled(False)
        layout.addWidget(self.primary)
        footer = QtGui.QHBoxLayout()
        self.status = label('목록을 확인하고 있습니다.', 'muted')
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(32)
        footer.addWidget(self.status, 1)
        self.stop = button('취소', self.cancel.set)
        self.stop.hide()
        footer.addWidget(self.stop)
        layout.addLayout(footer)
        self.progress = QtGui.QProgressBar()
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.controls = [self.options, self.reload, self.select_all] + list(self.filters.values())
        self.timer = QtCore.QTimer(self.dialog)
        self.timer.connect('timeout()', self.poll)
        self.timer.start(100)
        self.render()
        self.dialog.show()
        self.refresh()

    def set_filter(self, key):
        self.filter = key
        self.select_all.setVisible(key == 'updates')
        self.checked.clear()
        for name, control in self.filters.items():
            control.setChecked(name == key)
        self.render()

    def select_updates(self):
        state = self.store.read_state()
        self.checked = {p['id'] for p in self.rows if p['id'] in state['packages']
                        and is_newer_version(p['version'], state['packages'][p['id']]['active_version'])
                        and not state['packages'][p['id']]['pinned'] and not compatibility(p)}
        self.render()

    def start(self, job, done=None):
        if self.busy:
            return
        self.busy = True
        self.cancel.clear()
        self.store.fetch = Downloader(self.cancel, lambda msg: self.events.put(('progress', msg)))
        self.progress.setRange(0, 0)
        self.progress.show()
        self.stop.show()
        self.primary.setEnabled(False)
        for control in self.controls:
            control.setEnabled(False)
        if self.list_content:
            self.list_content.setEnabled(False)
        def worker():
            try:
                with self.store.locked():
                    pass
                self.events.put(('done', (job(), done)))
            except Exception as exc:
                self.store.log('error ' + str(exc))
                self.events.put(('error', str(exc)))
        threading.Thread(target=worker, name='MW Script Manager', daemon=True).start()

    def poll(self):
        latest = None
        for _ in range(100):
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'progress':
                latest = payload
                continue
            latest = None
            self.busy = False
            self.progress.hide()
            self.stop.hide()
            for control in self.controls:
                control.setEnabled(True)
            if self.list_content:
                self.list_content.setEnabled(True)
            if kind == 'error':
                self.render()
                self.status.setText(payload)
            else:
                result, callback = payload
                try:
                    if callback:
                        callback(result)
                    else:
                        self.render()
                        self.status.setText('변경했습니다.' if refresh_scripts() else '메뉴 반영을 위해 FontLab을 재시작하세요.')
                except Exception as exc:
                    self.status.setText(str(exc))
            self.update_primary()
        if latest is not None:
            self.status.setText(latest)

    def refresh(self):
        def job():
            changed = self.store.migrate_wrappers()
            return self.store.catalog(manual=True), changed
        def done(result):
            catalog, changed = result
            if changed:
                refresh_scripts()
            self.catalog_ready(catalog)
        self.status.setText('목록을 확인하고 있습니다.')
        self.start(job, done)

    def catalog_ready(self, result):
        self.manifest, self.offline = result
        self.errors.clear()
        self.render()
        self.status.setText(self.offline or '')
        if self.bootstrap:
            if not self.offline:
                self.install_manager()
            return
        if not self.offline:
            pending = [p for p in self.store.updates(self.manifest, automatic=True) if not compatibility(p)]
            if pending:
                self.install_many(pending)

    def selected(self):
        return [p for p in self.rows if p['id'] in self.checked]

    def choose(self, key, control):
        checked = value(control, 'checked')
        control.setText('✓' if checked else '')
        if checked:
            self.checked.add(key)
        else:
            self.checked.discard(key)
        self.update_primary()

    def update_primary(self):
        selected = self.selected()
        if not selected:
            self.primary.setText('선택 설치')
        else:
            state = self.store.read_state()
            installed = sum(p['id'] in state['packages'] for p in selected)
            action = '업데이트' if installed == len(selected) else ('설치' if not installed else '설치 / 업데이트')
            self.primary.setText('선택한 %d개 %s' % (len(selected), action))
        self.primary.setEnabled(bool(selected) and not self.busy)

    def render(self):
        try:
            state = self.store.read_state()
        except ManagerError as exc:
            self.status.setText(str(exc))
            return
        items = {p['id']: p for p in (self.manifest or {}).get('scripts', [])}
        for key, record in state['packages'].items():
            items.setdefault(key, record['versions'][record['active_version']])
        self.rows = []
        content = QtGui.QWidget()
        content.setObjectName('list')
        rows = QtGui.QVBoxLayout(content)
        rows.setContentsMargins(0, 0, 6, 0)
        rows.setSpacing(0)
        selectable = set()
        for p in items.values():
            key = p['id']
            record = state['packages'].get(key)
            update = bool(record and is_newer_version(p['version'], record['active_version']))
            if self.filter == 'installed' and not record:
                continue
            if self.filter == 'updates' and not update:
                continue
            self.rows.append(p)
            reason = compatibility(p)
            pinned = bool(record and record['pinned'])
            enabled = not reason and not pinned and (not record or update)
            if enabled:
                selectable.add(key)
            status = '업데이트 가능' if update else ('설치됨' if record else '미설치')
            if pinned:
                status = '버전 고정'
            if reason:
                status = '의존성 필요' if reason.startswith('필요 라이브러리') else '호환 불가'
            if key in self.errors:
                status = '설치 실패'
            row = QtGui.QWidget()
            row.setObjectName('row')
            row.setMinimumHeight(78)
            line = QtGui.QHBoxLayout(row)
            line.setContentsMargins(4, 16, 6, 16)
            line.setSpacing(14)
            pick = QtGui.QPushButton('✓' if key in self.checked else '')
            pick.setObjectName('pick')
            pick.setAutoDefault(False)
            pick.setCheckable(True)
            pick.setChecked(key in self.checked)
            pick.setFixedSize(22, 22)
            pick.setEnabled(enabled)
            pick.setAccessibleName(p['name'] + ' 설치 선택')
            pick.setToolTip(reason or ('버전 고정을 해제하면 업데이트할 수 있습니다.' if pinned else ('설치할 새 버전이 없습니다.' if record and not update else '이번에 설치할 항목 선택')))
            pick.connect('clicked()', lambda k=key, c=pick: self.choose(k, c))
            line.addWidget(pick)
            text = QtGui.QVBoxLayout()
            text.setSpacing(5)
            title = button(p['name'], lambda k=key: self.details(k), 'name')
            title.setToolTip('상세 정보 및 설치 설정')
            text.addWidget(title)
            version = 'v' + (record['active_version'] if record else p['version'])
            if update:
                version += '  →  v' + p['version']
            text.addWidget(label(version, 'muted'))
            line.addLayout(text, 1)
            state_label = label(status, 'rowStatus')
            state_label.setToolTip(self.errors.get(key) or reason or status)
            line.addWidget(state_label)
            more = button('›', lambda k=key: self.details(k))
            more.setAccessibleName(p['name'] + ' 상세 정보')
            line.addWidget(more)
            rows.addWidget(row)
        self.checked.intersection_update(selectable)
        if not self.rows:
            empty = label('업데이트할 항목이 없습니다.' if self.filter == 'updates' else ('설치된 스크립트가 없습니다.' if self.filter == 'installed' else '목록을 불러오면 스크립트가 표시됩니다.'), 'muted')
            empty.setContentsMargins(4, 32, 4, 32)
            rows.addWidget(empty)
        rows.addStretch()
        old = self.scroll.takeWidget()
        self.scroll.setWidget(content)
        self.list_content = content
        if old:
            old.deleteLater()
        content.setEnabled(not self.busy)
        self.update_primary()

    def detail_shell(self, title):
        if self.detail_dialog:
            self.detail_dialog.close()
            self.detail_dialog.deleteLater()
        dialog = QtGui.QDialog(self.dialog)
        dialog.setWindowTitle(title)
        dialog.setStyleSheet(STYLE)
        dialog.setMinimumWidth(420)
        layout = QtGui.QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(label(title, 'title'))
        self.detail_dialog = dialog
        return dialog, layout

    def close_detail(self):
        if self.detail_dialog:
            self.detail_dialog.close()

    def details(self, key):
        if self.busy:
            return
        p = next(p for p in self.rows if p['id'] == key)
        state = self.store.read_state()
        record = state['packages'].get(key)
        dialog, layout = self.detail_shell(p['name'])
        description = label(p.get('description', ''))
        description.setWordWrap(True)
        layout.addWidget(description)
        layout.addWidget(label('배포 버전  ' + p['version'] + ('    설치 버전  ' + record['active_version'] if record else ''), 'muted'))
        if p.get('requirements'):
            layout.addWidget(label('필요 라이브러리  ' + ', '.join(p['requirements']), 'muted'))
        message = self.errors.get(key) or compatibility(p)
        if message:
            warning = label(message)
            warning.setWordWrap(True)
            layout.addWidget(warning)
        if p.get('changelog'):
            changelog = label(str(p['changelog']))
            changelog.setWordWrap(True)
            layout.addWidget(changelog)
        source = button('GitHub에서 소스 보기 ↗', lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl('https://github.com/' + REPOSITORY + '/tree/' + p['source_ref'])))
        layout.addWidget(source)
        if record:
            automatic = QtGui.QCheckBox('자동 업데이트')
            automatic.setChecked(record['auto_update'])
            pinned = QtGui.QCheckBox('현재 버전 유지')
            pinned.setChecked(record['pinned'])
            layout.addWidget(automatic)
            layout.addWidget(pinned)
            def save():
                a, b = value(automatic, 'checked'), value(pinned, 'checked')
                self.close_detail()
                self.start(lambda: self.store.settings(key, a, b))
            layout.addWidget(button('설정 저장', save, 'primary'))
            actions = QtGui.QHBoxLayout()
            rollback = button('이전 버전 복원', lambda: self.rollback_selected(key))
            rollback.setEnabled(bool(record.get('previous_version')))
            actions.addWidget(rollback)
            actions.addStretch()
            actions.addWidget(button('제거', lambda: self.remove_selected(key, p['name']), 'danger'))
            layout.addLayout(actions)
        layout.addWidget(button('닫기', dialog.close))
        dialog.show()

    def install_many(self, packages):
        if not packages:
            return
        state = self.store.read_state()
        ready = []
        self.errors.clear()
        for p in packages:
            reason = compatibility(p)
            record = state['packages'].get(p['id'])
            if record and record['pinned'] and record['active_version'] != p['version']:
                reason = '버전 고정을 먼저 해제하세요.'
            if reason:
                self.errors[p['id']] = reason
            else:
                ready.append(p)
        def job():
            errors = {}
            for p in ready:
                if self.cancel.is_set():
                    raise Cancelled('작업을 취소했습니다')
                self.events.put(('progress', p['name'] + ' 설치 중…'))
                try:
                    self.store.install(p)
                except Cancelled:
                    raise
                except Exception as exc:
                    errors[p['id']] = str(exc)
            return errors
        def done(errors):
            self.errors.update(errors)
            self.checked.difference_update(p['id'] for p in ready if p['id'] not in errors)
            self.render()
            refreshed = refresh_scripts()
            self.status.setText('설치하지 못한 항목의 상세 정보를 확인하세요.' if self.errors else
                                ('설치했습니다. Scripts 메뉴에서 실행할 수 있습니다.' if refreshed else '설치했습니다. 메뉴 반영을 위해 FontLab을 재시작하세요.'))
        self.status.setText('%d개 스크립트 설치를 준비합니다.' % len(ready))
        self.start(job, done)

    def install_selected(self):
        self.install_many(self.selected())

    def remove_selected(self, key, name):
        if QtGui.QMessageBox.question(self.detail_dialog, '스크립트 제거', name + '을 제거할까요?', QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
            self.close_detail()
            self.start(lambda: self.store.remove(key))

    def rollback_selected(self, key):
        self.close_detail()
        self.start(lambda: self.store.rollback(key))

    def show_settings(self):
        dialog, layout = self.detail_shell('매니저 설정')
        layout.addWidget(label('실행 버전  ' + RUNTIME_VERSION, 'muted'))
        layout.addWidget(button('매니저 업데이트 / 복구', lambda: (self.close_detail(), self.install_manager())))
        layout.addWidget(button('설치 상태 백업 복구', self.recover))
        layout.addWidget(button('닫기', dialog.close))
        dialog.show()

    def install_manager(self):
        if not self.manifest:
            self.status.setText('먼저 온라인 목록을 확인하세요.')
            return
        def done(result):
            refreshed = refresh_scripts()
            self.bootstrap = False
            self.render()
            self.status.setText('매니저를 설치했습니다.' + ('' if refreshed else ' 메뉴 반영을 위해 FontLab을 재시작하세요.') +
                                (' 새 버전은 FontLab 재시작 후 적용됩니다.' if self.manifest['manager']['version'] != RUNTIME_VERSION else ''))
        self.status.setText('매니저를 설치하고 있습니다.')
        self.start(lambda: self.store.install(self.manifest['manager'], manager=True, repair=True), done)

    def recover(self):
        if QtGui.QMessageBox.question(self.detail_dialog, '상태 복구', '직전 백업의 파일을 검증한 뒤 설치 상태를 복구할까요?', QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
            self.close_detail()
            self.start(self.store.recover)


def show_manager(env, bootstrap=False):
    if _windows:
        existing = _windows[0]
        existing.dialog.show()
        existing.dialog.raise_()
        existing.dialog.activateWindow()
        if bootstrap and not existing.busy:
            existing.bootstrap = True
            existing.refresh()
        return existing
    window = ManagerWindow(env, bootstrap)
    _windows.append(window)
    return window
