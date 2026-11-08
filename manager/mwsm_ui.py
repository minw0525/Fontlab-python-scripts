"""PythonQt interface. Workers only touch files/network; Qt stays on main thread."""
import queue
import threading
from PythonQt import QtCore, QtGui

from mwsm_core import Cancelled, Downloader, ManagerError, Store, REPOSITORY
from mwsm_host import compatibility, refresh_scripts

_windows = []


def value(obj, name):
    result = getattr(obj, name)
    return result() if callable(result) else result


class ManagerWindow:
    def __init__(self, env, bootstrap=False):
        self.env = env
        self.bootstrap = bootstrap
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.store = Store(env['user_data'])
        self.manifest = None
        self.offline = None
        self.busy = False
        self.rows = []
        self.errors = {}
        self.dialog = QtGui.QDialog()
        self.dialog.setWindowTitle('MW Script Manager' + (' · 설치' if bootstrap else ''))
        self.dialog.resize(900, 600)
        layout = QtGui.QVBoxLayout(self.dialog)
        toolbar = QtGui.QHBoxLayout()
        layout.addLayout(toolbar)
        self.controls = []
        self.button(toolbar, '새로고침', self.refresh)
        self.button(toolbar, '선택 설치 / 업데이트', self.install_selected)
        self.button(toolbar, '설치 항목 모두 업데이트', self.update_all)
        self.only_installed = QtGui.QCheckBox('설치 목록만')
        self.only_installed.connect('toggled(bool)', lambda checked: self.render())
        toolbar.addWidget(self.only_installed)
        self.controls.append(self.only_installed)
        self.table = QtGui.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['스크립트', '설치 버전', '배포 버전', '상태', '자동 / 고정'])
        self.table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.table.connect('itemSelectionChanged()', self.details)
        layout.addWidget(self.table)
        self.detail = QtGui.QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(145)
        layout.addWidget(self.detail)
        actions = QtGui.QHBoxLayout()
        layout.addLayout(actions)
        self.button(actions, '제거', self.remove_selected)
        self.button(actions, '이전 버전 복원', self.rollback_selected)
        self.button(actions, '자동 업데이트 켜기 / 끄기', lambda: self.toggle('auto_update'))
        self.button(actions, '버전 고정 / 해제', lambda: self.toggle('pinned'))
        footer = QtGui.QHBoxLayout()
        layout.addLayout(footer)
        self.button(footer, '매니저 업데이트 / 복구', self.install_manager)
        self.button(footer, '상태 백업 복구', self.recover)
        self.progress = QtGui.QProgressBar()
        self.progress.setRange(0, 1)
        footer.addWidget(self.progress)
        self.stop = QtGui.QPushButton('취소')
        self.stop.connect('clicked()', self.cancel.set)
        self.stop.setEnabled(False)
        footer.addWidget(self.stop)
        self.status = QtGui.QLabel('목록을 확인합니다…')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.timer = QtCore.QTimer(self.dialog)
        self.timer.connect('timeout()', self.poll)
        self.timer.start(100)
        self.dialog.show()
        self.refresh()

    def button(self, layout, label, callback):
        button = QtGui.QPushButton(label)
        button.connect('clicked()', callback)
        layout.addWidget(button)
        self.controls.append(button)
        return button

    def start(self, job, done=None):
        if self.busy:
            return
        self.busy = True
        self.cancel.clear()
        self.store.fetch = Downloader(self.cancel, lambda msg: self.events.put(('progress', msg)))
        self.progress.setRange(0, 0)
        self.stop.setEnabled(True)
        for control in self.controls:
            control.setEnabled(False)
        def worker():
            try:
                with self.store.locked():
                    pass  # Recover a prior interrupted transaction before any new work.
                self.events.put(('done', (job(), done)))
            except Exception as exc:
                self.store.log('error ' + str(exc))
                self.events.put(('error', str(exc)))
        threading.Thread(target=worker, name='MW Script Manager', daemon=True).start()

    def poll(self):
        # Coalesce progress to keep the UI responsive even for large downloads.
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
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
            self.stop.setEnabled(False)
            for control in self.controls:
                control.setEnabled(True)
            if kind == 'error':
                self.status.setText(payload)
                self.render()
            else:
                result, callback = payload
                try:
                    if callback:
                        callback(result)
                    else:
                        self.render()
                        self.status.setText('완료. ' + ('Scripts 메뉴를 갱신했습니다.' if refresh_scripts() else '메뉴 반영을 위해 FontLab을 재시작하세요.') + ' 실행했던 패키지는 재시작 후 새 버전이 적용됩니다.')
                except Exception as exc:
                    self.status.setText(str(exc))
        if latest is not None:
            self.status.setText(latest)

    def refresh(self):
        self.start(lambda: self.store.catalog(manual=True), self.catalog_ready)

    def catalog_ready(self, result):
        self.manifest, self.offline = result
        self.errors.clear()
        self.render()
        self.status.setText(self.offline or '목록을 갱신했습니다. 원하는 스크립트를 선택하세요.')
        if self.bootstrap:
            if not self.offline:
                self.install_manager()
            return
        if not self.offline:
            pending = [p for p in self.store.updates(self.manifest, automatic=True) if not compatibility(p)]
            if pending:
                self.install_many(pending)

    def selected(self):
        indexes = self.table.selectionModel().selectedRows()
        return [self.rows[index.row()] for index in indexes]

    def render(self):
        try:
            state = self.store.read_state()
        except ManagerError as exc:
            self.status.setText(str(exc))
            return
        items = {p['id']: p for p in (self.manifest or {}).get('scripts', [])}
        for key, record in state['packages'].items():
            items.setdefault(key, record['versions'][record['active_version']])
        self.rows = [p for p in items.values() if not value(self.only_installed, 'checked') or p['id'] in state['packages']]
        self.table.setRowCount(len(self.rows))
        for row, p in enumerate(self.rows):
            record = state['packages'].get(p['id'])
            installed = record['active_version'] if record else '—'
            reason = compatibility(p)
            status = '호환 불가 · ' + reason if reason else ('미설치' if not record else ('최신' if installed == p['version'] else '업데이트 가능'))
            if self.offline:
                status = '오프라인 · ' + status
            if p['id'] in self.errors:
                status = '오류 · ' + self.errors[p['id']]
            settings = ('자동 ' + ('켜짐' if record['auto_update'] else '꺼짐') + (' / 고정' if record['pinned'] else '')) if record else '—'
            for col, text in enumerate((p['name'], installed, p['version'], status, settings)):
                self.table.setItem(row, col, QtGui.QTableWidgetItem(text))
        self.table.resizeColumnsToContents()

    def details(self):
        selected = self.selected()
        if not selected:
            self.detail.setPlainText('')
            return
        p = selected[0]
        self.detail.setPlainText(p['name'] + '\n' + p.get('description', '') +
            '\n의존성: ' + (', '.join(p.get('requirements', [])) or '없음') +
            '\n변경 이력: ' + str(p.get('changelog', '배포 이력이 제공되지 않았습니다.')) +
            '\n소스: https://github.com/' + REPOSITORY + '/tree/' + p['source_ref'] +
            '\n' + (self.errors.get(p['id'], '') or compatibility(p) or ''))

    def install_many(self, packages):
        if not packages:
            self.status.setText('설치/업데이트할 항목이 없습니다.')
            return
        state = self.store.read_state()
        ready = []
        for p in packages:
            reason = compatibility(p)
            record = state['packages'].get(p['id'])
            if record and record['pinned'] and record['active_version'] != p['version']:
                reason = '버전 고정을 먼저 해제하세요'
            if reason:
                self.errors[p['id']] = reason
            else:
                ready.append(p)
        def job():
            errors = {}
            for p in ready:
                if self.cancel.is_set():
                    raise Cancelled('작업을 취소했습니다')
                try:
                    self.store.install(p)
                except Cancelled:
                    raise
                except Exception as exc:
                    errors[p['id']] = str(exc)
            return errors
        def done(errors):
            self.errors.update(errors)
            self.render()
            refreshed = refresh_scripts()
            self.status.setText(('일부 항목을 처리하지 못했습니다. 상태를 확인하세요.' if self.errors else '설치 완료.') +
                                (' 메뉴 갱신 완료.' if refreshed else ' 메뉴 반영을 위해 재시작하세요.') +
                                ' 이미 실행한 패키지의 업데이트는 FontLab 재시작 후 적용됩니다.')
        self.start(job, done)

    def install_selected(self):
        self.install_many(self.selected())

    def update_all(self):
        if self.manifest:
            self.install_many(self.store.updates(self.manifest))

    def one_installed(self):
        selected = self.selected()
        state = self.store.read_state()
        if len(selected) != 1 or selected[0]['id'] not in state['packages']:
            self.status.setText('설치된 항목 하나를 선택하세요.')
            return None
        return selected[0]['id']

    def remove_selected(self):
        key = self.one_installed()
        if key and QtGui.QMessageBox.question(self.dialog, '제거', key + ' 패키지를 제거할까요?', QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
            self.start(lambda: self.store.remove(key))

    def rollback_selected(self):
        key = self.one_installed()
        if key:
            self.start(lambda: self.store.rollback(key))

    def toggle(self, field):
        key = self.one_installed()
        if key:
            record = self.store.read_state()['packages'][key]
            record[field] = not record[field]
            self.start(lambda: self.store.settings(key, record['auto_update'], record['pinned']))

    def install_manager(self):
        if not self.manifest:
            self.status.setText('먼저 온라인 카탈로그를 확인하세요.')
            return
        def done(result):
            refreshed = refresh_scripts()
            self.bootstrap = False
            self.dialog.setWindowTitle('MW Script Manager')
            self.render()
            self.status.setText('매니저 설치 완료. ' + ('Scripts 메뉴 갱신 완료.' if refreshed else '메뉴 반영을 위해 FontLab을 재시작하세요.') + ' 다른 스크립트를 선택해 설치할 수 있습니다. 매니저 갱신은 재시작 후 적용됩니다.')
        self.start(lambda: self.store.install(self.manifest['manager'], manager=True, repair=True), done)

    def recover(self):
        if QtGui.QMessageBox.question(self.dialog, '상태 복구', '직전 백업의 파일을 검증한 뒤 설치 상태를 복구할까요?', QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
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
