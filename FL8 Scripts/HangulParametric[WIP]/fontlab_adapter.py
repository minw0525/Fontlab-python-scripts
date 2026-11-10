"""FontLab boundary: measurement, explicit source/application actions, metadata."""

import fontlab as fl6
from typerig.proxy.fl.objects.font import pFont
from typerig.proxy.fl.gui import QtGui
from SmartComponentHangulLab.scripts.smart_component_location import parse_component_location

from .model import BOX_KEYS, LIB_KEY, Session, checked_box, characters, decompose, decode_document, merge_master, role_indices, union_boxes


class FontAdapter:
    @staticmethod
    def shape_path(shape):
        # Component outlines live in includesList, not the component's closedPath.
        path = QtGui.QPainterPath()
        shape.ensurePaths()
        if shape.isComponent:
            for child in shape.includesList:
                path.addPath(FontAdapter.shape_path(child))
        else:
            path.addPath(shape.closedPath)
        return shape.transform.map(path)

    def __init__(self):
        self.raw = fl6.CurrentFont()
        if self.raw is None:
            raise ValueError('먼저 폰트 파일을 열어 주세요.')
        self.font = pFont(self.raw)
        self.package = self.font.fl
        self.identity = self.package.id
        self.upm = float(self.package.upm)
        self.path = str(self.package.path)
        self.names = {}
        self.advances = {}
        for glyph in self.font.glyphs():
            code = glyph.unicode
            if isinstance(code, int) and 0xAC00 <= code <= 0xD7A3:
                self.names[chr(code)] = glyph.name

    def read_advances(self, layer):
        self.require_master(layer)
        self.advances = {}
        for char, name in self.names.items():
            source = self.font.glyph(name).layer(layer)
            if source is not None:
                self.advances[char] = float(source.advanceWidth)

    def advance(self, char):
        return self.advances.get(char, self.upm)

    def display_outline(self, char, master):
        """Read foreground geometry without measuring roles or creating samples."""
        name = self.names.get(char)
        if not name:
            return None
        glyph = self.font.glyph(name)
        layer = glyph.layer(master)
        if layer is None:
            return None
        outline = QtGui.QPainterPath()
        for shape in layer.shapes:
            outline.addPath(self.shape_path(shape))
        return None if outline.isEmpty() else outline

    def check_active(self):
        current = fl6.CurrentFont()
        if current is None or fl6.flPackage(current).id != self.identity:
            raise ValueError('연결된 폰트를 다시 활성화하세요. 다른 폰트에는 적용하지 않습니다.')

    def masters(self):
        return list(self.font.masters())

    def require_master(self, layer):
        self.check_active()
        if not isinstance(layer, str) or layer not in self.masters():
            raise ValueError('마스터가 연결되지 않았습니다. 표본 탭에서 저장 설정을 복구한 뒤 진행하세요.')

    def measure(self, text, layer, grouped_vowel=False):
        self.require_master(layer)
        records, paths, issues = {}, {}, []
        for char in characters(text):
            name = self.names.get(char)
            if not name:
                issues.append(char + ': 글립 없음')
                continue
            glyph = self.font.glyph(name)
            if glyph.layer(layer) is None:
                issues.append(char + ': 마스터 레이어 없음')
                continue
            shapes = list(glyph.shapes(layer))
            boxes, outline = [], QtGui.QPainterPath()
            try:
                groups = role_indices(len(shapes), bool(decompose(char)[2]), grouped_vowel)
                for shape in shapes:
                    # FontLab may leave path caches empty until a glyph is displayed.
                    shape.ensurePaths()
                    rect = shape.transform.mapRect(shape.boundingBox)
                    boxes.append(checked_box({'x': rect.x(), 'y': rect.y(),
                                              'w': rect.width(), 'h': rect.height()}))
                    outline.addPath(self.shape_path(shape))
                records[char] = {'glyphName': name, 'advanceWidth': float(glyph.layer(layer).advanceWidth),
                                 'boxes': [union_boxes([boxes[i] for i in group]) for group in groups],
                                 'elementIndices': groups, 'roleMapping': 'grouped-vowel' if grouped_vowel else 'element-order'}
                self.advances[char] = records[char]['advanceWidth']
                paths[char] = outline
            except (ValueError, TypeError, AttributeError) as error:
                issues.append('{}: {}'.format(char, error))
        return records, paths, issues

    def existing_source(self, session, char, role, master):
        from .svc import source_name
        from .inference import source_key
        import hashlib
        self.require_master(master)
        key = source_key(char, role)
        name = source_name(char, role, master)
        legacy = '_hp.{}.{}'.format(hashlib.sha1(master.encode('utf8')).hexdigest()[:8], key)
        for existing in (session.sources.get(key), legacy, name):
            if existing and self.font.hasGlyph(existing):
                return existing
        return None

    def prepare_source(self, session, char, role, master):
        from .svc import source_plan, source_name, format_source_note
        self.require_master(master)
        existing = self.existing_source(session, char, role, master)
        if existing:
            raise ValueError('소스가 이미 있습니다. 기존 디자인을 보존합니다. 소스 이름 입력 후 연결하세요: ' + existing)
        plan = source_plan(session, char, role)
        key = plan['key']
        name = source_name(char, role, master)
        names = [master + suffix + ':width={},height={}'.format(*loc) for suffix, loc in
                 zip(('', '.Width', '.Height', '.WidthHeight'), ((0, 0), (1000, 0), (0, 1000), (1000, 1000)))]
        drafts = []
        for corner, guide_corner in zip(plan['corners'], plan['guide']['corners']):
            selected = []
            donor_char = corner['donor']
            if donor_char is not None:
                record = session.observations[donor_char]
                donor = self.font.glyph(record['glyphName'])
                shapes = list(donor.shapes(master))
                selected = [shapes[i] for i in record['elementIndices'][role]]
                rects = []
                for shape in selected:
                    shape.ensurePaths()
                    r = shape.transform.mapRect(shape.boundingBox)
                    rects.append(dict(x=r.x(), y=r.y(), w=r.width(), h=r.height()))
                box = union_boxes(rects)
                if box != record['boxes'][role]:
                    raise ValueError('표본 크기·위치가 측정 이후 바뀌었습니다. 먼저 재측정하세요: ' + donor_char)
                guide_corner['copiedFrom'] = donor_char
                guide_corner['copiedBox'] = box
            copies = []
            for original in selected:
                t = original.transform
                if not t.isAffine():
                    raise ValueError('원근 변환된 표본은 소스 초안으로 사용할 수 없습니다.')
                clone = original.cloneTopLevel()
                clone.transform = QtGui.QTransform(t.m11(), t.m12(), t.m21(), t.m22(),
                                                   t.dx()-box['x'], t.dy()-box['y'])
                copies.append(clone)
            drafts.append(copies)
        source = self.font.newGlyph(name, [names[0]])
        try:
            for name_layer in names[1:]:
                layer = fl6.flLayer()
                layer.name = name_layer
                source.fl.addLayer(layer, True)
            for name_layer, copies, corner in zip(names, drafts, plan['corners']):
                layer = source.layer(name_layer)
                layer.advanceWidth = self.upm
                for clone in copies:
                    layer.addShape(clone)
                # Empty layers have no design metrics; these are only axis handles.
                anchor_box = corner['box'] or dict(w=self.upm, h=self.upm)
                source.addAnchor((anchor_box['w'], anchor_box['h']/2), 'width', name_layer)
                source.addAnchor((anchor_box['w']/2, 0), 'height', name_layer)
            for corner, layer_name in zip(plan['guide']['corners'], names):
                corner['layerName'] = layer_name
            source.note = format_source_note(plan['guide'])
            source.updateObject(source.fl, 'Prepare parametric source draft', False)
        except Exception:
            self.package.deleteGlyph(source.fl)
            raise
        self.font.update()
        session.sources[key] = name
        session.source_guides[name] = plan['guide']
        session.dirty = True
        return name, plan

    def refresh_source_guide(self, session, char, role, master):
        from .svc import source_design_guide, replace_source_note
        self.require_master(master)
        name = self.existing_source(session, char, role, master)
        if not name:
            raise ValueError('갱신할 소스가 없습니다.')
        guide = source_design_guide(session, char, role)
        previous = session.source_guides.get(name)
        source = self.font.glyph(name)
        source.note = replace_source_note(str(source.note or ''), guide, previous)
        source.updateObject(source.fl, 'Refresh source design note', False)
        session.source_guides[name] = guide
        session.dirty = True
        return name

    def source_layers(self, name, master):
        from .svc import CORNERS
        self.require_master(master)
        if not self.font.hasGlyph(name):
            raise ValueError('SVC 소스 없음: ' + name)
        source = self.font.glyph(name)
        found = {}
        for layer in source.layers():
            prefix, axes = parse_component_location(str(layer.name))
            if getattr(layer, 'isMaskLayer', False) or not (prefix == master or prefix.startswith(master + '.')):
                continue
            values = {k: float(v) for k, v in axes.items()}
            if any(v != 0 for k, v in values.items() if k not in ('width', 'height')):
                continue
            key = (values.get('width', 0), values.get('height', 0))
            if key in CORNERS:
                if key in found:
                    raise ValueError('같은 location의 소스 레이어가 중복됩니다: ' + name)
                if not list(layer.shapes):
                    raise ValueError('비어 있는 소스 레이어: ' + str(layer.name))
                found[key] = layer
        if set(found) != set(CORNERS):
            raise ValueError('현재 마스터의 width/height 네 코너 레이어가 필요합니다: ' + name)
        return source, found

    def map_component(self, source_name, master, target, normalized=None, correction=None):
        from .svc import solve_location, map_reference
        self.require_master(master)
        source, layers = self.source_layers(source_name, master)
        # A unique scratch glyph avoids clearing any user's existing template.
        import uuid
        name = '_hpProbe.' + uuid.uuid4().hex
        probe_layer = str(layers[(0, 0)].name)
        probe = self.font.newGlyph(name, [probe_layer])
        layer = probe.layer(probe_layer)
        try:
            layer.recipe = source_name
            layer.autoLayer = True
            probe.updateObject(probe.fl, 'Evaluate SVC source', False)
            components = [s for s in layer.shapes if s.isComponent]
            if len(components) != 1:
                raise ValueError('recipe로 SVC 컴포넌트를 만들지 못했습니다.')
            layer.autoLayer = False
            component = components[0]
            component.shapeData.componentGlyph = source_name
            if not component.includesList:
                component.setIncludes([s.cloneTopLevel() for s in layers[(0, 0)].shapes])
            def evaluate(u, v):
                component.shapeData.componentLayer = master + '#width={},height={}'.format(u, v)
                component.transform = QtGui.QTransform()
                component.update()
                probe.updateObject(probe.fl, 'Evaluate SVC location', False)
                component.ensurePaths()
                r = component.boundingBox
                return dict(x=r.x(), y=r.y(), w=r.width(), h=r.height())
            result = (map_reference(target, normalized, correction, evaluate) if normalized is not None
                      else dict(solve_location(target, evaluate), target=target))
            clone = component.cloneTopLevel()
            clone.transform = QtGui.QTransform().translate(result['delta']['x'], result['delta']['y'])
            return clone, result
        finally:
            self.package.deleteGlyph(probe.fl)

    def apply_empty(self, session, text, master):
        from .inference import source_key
        from .svc import source_mapping
        from .inference import RelationModel
        self.require_master(master)
        applied, skipped, cache = [], [], {}
        placement_models = {}
        for char in characters(text):
            if char in session.observations:
                skipped.append((char, '실측 표본 원본 보존'))
                continue
            name = self.names.get(char, 'uni{:04X}'.format(ord(char)))
            glyph = self.font.glyph(name) if self.font.hasGlyph(name) else None
            layer = glyph.layer(master) if glyph else None
            if layer is not None and (list(layer.shapes) or layer.autoLayer or layer.recipe):
                skipped.append((char, '기존 디자인·recipe 보존'))
                continue
            pending, mappings = [], []
            try:
                for role in range(3 if decompose(char)[2] else 2):
                    reference = session.reference_initial
                    if reference not in placement_models:
                        placement_models[reference] = RelationModel(session.observations, reference)
                    target, normalized, correction, placement = source_mapping(session, char, role, placement_models[reference])
                    source = session.sources.get(source_key(char, role))
                    if target is None or not source:
                        raise ValueError('목표 공간 또는 연결 소스 없음: ' + str(role))
                    cache_key = (source, target['w'], target['h'],
                                 tuple(normalized[k] for k in ('w', 'h')) if normalized is not None else None,
                                 tuple(correction[k] for k in ('w', 'h')) if correction is not None else None)
                    if cache_key not in cache:
                        cache[cache_key] = self.map_component(source, master, target, normalized, correction)
                    template, result = cache[cache_key]
                    component = template.cloneTopLevel()
                    delta = {k: int(round(target[k]-result['box'][k])) for k in ('x', 'y')}
                    component.transform = QtGui.QTransform().translate(delta['x'], delta['y'])
                    mapping = dict(result, delta=delta, placement=placement,
                                   target=dict(result['target'], x=target['x'], y=target['y']))
                    pending.append(component)
                    mappings.append(mapping)
            except (ValueError, RuntimeError) as error:
                skipped.append((char, str(error)))
                continue
            created = glyph is None
            if created:
                glyph = self.font.newGlyph(name, [master], unicode_int=ord(char))
                self.names[char] = name
            if glyph.layer(master) is None:
                new_layer = fl6.flLayer()
                new_layer.name = master
                glyph.fl.addLayer(new_layer, True)
            layer = glyph.layer(master)
            previous_advance = layer.advanceWidth
            try:
                layer.advanceWidth = self.advance(char)
                for component in pending:
                    layer.addShape(component)
                glyph.updateObject(glyph.fl, 'Apply parametric Hangul to empty layer', False)
                for role, component in enumerate(layer.shapes):
                    component.ensurePaths()
                    r = component.transform.mapRect(component.boundingBox)
                    actual = dict(x=r.x(), y=r.y(), w=r.width(), h=r.height())
                    target = mappings[role]['target']
                    if max(abs(actual[k]-target[k]) for k in actual) > 1:
                        raise ValueError('삽입 후 위치·크기 검증 실패: ' + char)
            except Exception as error:
                if created:
                    self.package.deleteGlyph(glyph.fl)
                    self.names.pop(char, None)
                else:
                    for shape in list(layer.shapes):
                        layer.removeShape(shape)
                    layer.advanceWidth = previous_advance
                    glyph.updateObject(glyph.fl, 'Revert failed parametric insertion', False)
                skipped.append((char, str(error)))
                continue
            applied.append((char, mappings))
            session.managed_components[char] = {str(role): str(component.shapeData.componentGlyph)
                                                for role, component in enumerate(pending)}
            session.dirty = True
        self.font.update()
        return applied, skipped

    def recalculate_applied(self, session, master):
        """Re-evaluate bound components in place, including off-screen glyphs."""
        from .inference import source_key
        self.require_master(master)
        applied, skipped, paths, reports = [], [], {}, {}
        for key, name in sorted(session.sources.items()):
            role = int(key.split('.')[0])
            text = ''.join(c for c in sorted(self.names) if source_key(c, role) == key)
            if not text:
                continue
            try:
                done, failed, outlines = self.derive_role(session, text, role, name, master, update_only=True)
            except ValueError as error:
                skipped.append((name, str(error)))
                continue
            applied.extend(done)
            skipped.extend(failed)
            paths.update(outlines)
            reports.update(self.apply_reports)
        self.apply_reports = reports
        return applied, skipped, paths

    def derive_role(self, session, text, role, source_name, master, update_only=False):
        """Replace a role in-place, preserving its position and backing it up to mask."""
        from .inference import RelationModel, family
        from .svc import source_mapping
        self.require_master(master)
        self.source_layers(source_name, master)
        model = RelationModel(session.observations, session.reference_initial)
        applied, skipped, paths = [], [], {}
        self.apply_reports = {}
        for char in characters(text):
            if char in session.observations:
                skipped.append((char, '실측 표본 원본 보존'))
                continue
            name = self.names.get(char, 'uni{:04X}'.format(ord(char)))
            output = self.font.glyph(name) if self.font.hasGlyph(name) else None
            layer = output.layer(master) if output else None
            created, changed = False, False
            updating = False
            mask, mask_count = None, 0
            try:
                if name == source_name:
                    raise ValueError('소스 자신에는 컴포넌트를 넣을 수 없습니다.')
                if output and layer is None:
                    raise ValueError('대상 마스터 레이어 없음')
                if layer is not None and (layer.autoLayer or layer.recipe):
                    raise ValueError('자동 레시피 레이어는 직접 교체하지 않습니다.')
                shapes = list(layer.shapes) if layer is not None else []
                if shapes:
                    from .inference import source_key
                    managed = session.managed_components.get(char, {}).get(str(role))
                    protected_groups = role_indices(len(shapes), bool(decompose(char)[2]), session.grouped_vowel)
                    indices = protected_groups[role] if role < len(protected_groups) else []
                    # Older versions have bindings but no per-glyph ownership log.
                    # Adopt only an actual component of this role's bound source.
                    bound = session.sources.get(source_key(char, role))
                    if (not managed and len(indices) == 1 and shapes[indices[0]].isComponent
                            and str(shapes[indices[0]].shapeData.componentGlyph) == bound):
                        managed = bound
                    if not managed:
                        raise ValueError('기존 미관리 디자인 보존')
                    if (len(indices) != 1 or not shapes[indices[0]].isComponent or
                            str(shapes[indices[0]].shapeData.componentGlyph) != managed):
                        raise ValueError('관리 기록과 현재 자소 불일치 · 기존 디자인 보존')
                if update_only:
                    if not shapes:
                        continue
                    current_groups = role_indices(len(shapes), bool(decompose(char)[2]), session.grouped_vowel)
                    if role >= len(current_groups) or len(current_groups[role]) != 1:
                        continue
                    current_component = shapes[current_groups[role][0]]
                    if not current_component.isComponent or str(current_component.shapeData.componentGlyph) != source_name:
                        continue
                target, normalized, correction, placement = source_mapping(session, char, role, model)
                copies = {}
                if shapes:
                    # Read the current order: a prior grouped-vowel replacement
                    # may have reduced the element count since measurement.
                    groups = role_indices(len(shapes), bool(decompose(char)[2]), session.grouped_vowel)
                else:
                    record = session.observations.get(char)
                    if record is None:
                        _, v, f = decompose(char)
                        _, profile = model.reference_profile(family(char))
                        record = session.observations.get(profile.get((v, f), {}).get('referenceChar'))
                    if record is None:
                        raise ValueError('나머지 자소를 가져올 대응 실측 글립 없음')
                    donor = self.font.glyph(record['glyphName'])
                    donor_shapes = list(donor.shapes(master))
                    groups = record['elementIndices']
                    if sorted(i for group in groups for i in group) != list(range(len(donor_shapes))):
                        raise ValueError('표본 요소 구성이 바뀌었습니다. 재측정 필요')
                    for index, group in enumerate(groups):
                        if index == role:
                            continue
                        boxes = []
                        for i in group:
                            donor_shapes[i].ensurePaths()
                            r = donor_shapes[i].transform.mapRect(donor_shapes[i].boundingBox)
                            boxes.append(dict(x=r.x(), y=r.y(), w=r.width(), h=r.height()))
                        if union_boxes(boxes) != record['boxes'][index]:
                            raise ValueError('표본이 측정 후 변경되었습니다: ' + record['glyphName'])
                        copies[index] = [donor_shapes[i].cloneTopLevel() for i in group]
                if role >= len(groups):
                    raise ValueError('이 글자에 선택 자소가 없습니다.')
                component, result = self.map_component(source_name, master, target, normalized, correction)
                originals = [s.cloneTopLevel() for s in shapes]
                if output is None:
                    output = self.font.newGlyph(name, [master], unicode_int=ord(char))
                    layer = output.layer(master)
                    created = True
                advance = layer.advanceWidth
                changed = True
                if shapes:
                    existing = shapes[groups[role][0]]
                    updating = (len(groups[role]) == 1 and existing.isComponent and
                                str(existing.shapeData.componentGlyph) == source_name)
                    if updating:
                        old_location = str(existing.shapeData.componentLayer)
                        old_transform = originals[groups[role][0]].transform
                        existing.shapeData.componentLayer = str(component.shapeData.componentLayer)
                        existing.transform = component.transform
                        existing.update()
                        component = existing
                    else:
                        mask = layer.getMaskLayer(True)
                        mask_count = len(list(mask.shapes))
                        for i in groups[role]:
                            mask.addShape(shapes[i].cloneTopLevel())
                        if len(list(mask.shapes)) != mask_count + len(groups[role]):
                            raise ValueError('마스크 백업 개수 검증 실패')
                        for i in reversed(groups[role]):
                            layer.removeShape(shapes[i], False)
                        component = layer.insertShape(groups[role][0], component)
                else:
                    if created:
                        layer.advanceWidth = record.get('advanceWidth', self.advance(char))
                    for index in range(len(groups)):
                        for shape in ([component] if index == role else copies[index]):
                            added = layer.addShape(shape)
                            if index == role:
                                component = added
                output.updateObject(output.fl, 'Backup role to mask and apply Hangul SVC', False)
                current = list(layer.shapes)
                expected = len(shapes) - len(groups[role]) + 1 if shapes else sum(len(v) for v in copies.values()) + 1
                if len(current) != expected:
                    raise ValueError('교체 후 요소 개수 검증 실패')
                component.ensurePaths()
                r = component.transform.mapRect(component.boundingBox)
                actual = dict(x=r.x(), y=r.y(), w=r.width(), h=r.height())
                if max(abs(actual[k]-result['target'][k]) for k in BOX_KEYS) > 1:
                    raise ValueError('삽입 후 위치·크기 검증 실패')
                path = self.shape_path(component)
                if path.isEmpty():
                    raise ValueError('삽입 후 윤곽이 비어 있습니다')
                paths[(char, role)] = path
                report_mask = layer.getMaskLayer(False)
                self.apply_reports[char] = dict(location=result['location'], updated=updating,
                                                backedUp=len(groups[role]) if shapes and not updating else 0,
                                                maskCount=len(list(report_mask.shapes)) if report_mask is not None else 0)
                self.names[char] = name
                applied.append((char, name))
                session.managed_components.setdefault(char, {})[str(role)] = source_name
                session.dirty = True
            except Exception as error:
                if created:
                    self.package.deleteGlyph(output.fl)
                elif changed and updating:
                    existing.shapeData.componentLayer = old_location
                    existing.transform = old_transform
                    existing.update()
                    output.updateObject(output.fl, 'Revert failed SVC location update', False)
                elif changed:
                    for shape in list(layer.shapes):
                        layer.removeShape(shape, False)
                    for shape in originals:
                        layer.addShape(shape)
                    layer.advanceWidth = advance
                    if mask is not None:
                        for shape in list(mask.shapes)[mask_count:]:
                            mask.removeShape(shape, False)
                    output.updateObject(output.fl, 'Revert failed Hangul SVC replacement', False)
                skipped.append((char, str(error)))
        self.font.update()
        return applied, skipped, paths

    def load(self, layer):
        self.require_master(layer)
        document = decode_document(self.package.packageLib.get(LIB_KEY))
        return Session.from_data(document['masters'].get(layer, {}))

    def save(self, layer, session):
        self.require_master(layer)
        lib = dict(self.package.packageLib)
        # FontLab's native dictionary serialization matches the existing Composer.
        lib[LIB_KEY] = decode_document(merge_master(lib.get(LIB_KEY), layer, session))
        self.package.packageLib = lib
        session.dirty = False

    def recover_settings(self, layer, session):
        import uuid
        self.require_master(layer)
        lib = dict(self.package.packageLib)
        raw = lib.get(LIB_KEY)
        try:
            decode_document(raw)
        except ValueError:
            current, _, _ = self.measure(''.join(session.observations), layer, session.grouped_vowel)
            mismatches = [c for c, record in session.observations.items()
                          if c not in current or any(current[c].get(k) != record.get(k)
                              for k in ('boxes', 'glyphName', 'elementIndices'))]
            if mismatches:
                raise ValueError('선택 마스터와 기존 측정이 일치하지 않아 복구를 중단했습니다: ' + ''.join(mismatches[:20]))
            lib[LIB_KEY + '.unreadable.' + uuid.uuid4().hex] = raw
            lib[LIB_KEY] = decode_document(merge_master(None, layer, session))
            self.package.packageLib = lib
            session.dirty = False
        else:
            raise ValueError('정상 설정은 초기화하지 않습니다.')
