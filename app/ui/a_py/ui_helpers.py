# app/ui/a_py/ui_helpers.py
from PySide6.QtWidgets import QWidget, QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox
from contextlib import contextmanager

def find_by_name(parent: QWidget, klass, *names):
    for n in names:
        w = parent.findChild(klass, n)
        if w:
            return w
    return None

def find_any(parent: QWidget, klass, name_candidates=(), text_candidates=()):
    w = find_by_name(parent, klass, *name_candidates)
    if w:
        return w
    if text_candidates:
        needles = {t.lower() for t in text_candidates if t}
        for obj in parent.findChildren(klass):
            txt = getattr(obj, "text", lambda: "")()
            if txt and txt.lower() in needles:
                return obj
    lst = parent.findChildren(klass)
    return lst[0] if len(lst) == 1 else None

def text_get(w):
    if not w: return ""
    if isinstance(w, (QTextEdit, QPlainTextEdit)):
        return w.toPlainText().strip()
    return w.text().strip()

def text_set(w, val: str):
    if not w: return
    if isinstance(w, (QTextEdit, QPlainTextEdit)):
        w.setPlainText(val)
    else:
        w.setText(val)
    try:
        w.setFocus()
        if hasattr(w, "selectAll"): w.selectAll()
    except Exception:
        pass

def num_get(w):
    if isinstance(w, (QSpinBox, QDoubleSpinBox)):
        return int(w.value())
    try:
        return int(float(text_get(w)))
    except Exception:
        return 0

def num_set(w, val: int):
    if isinstance(w, (QSpinBox, QDoubleSpinBox)):
        w.setValue(int(val))
    else:
        text_set(w, str(int(val)))

@contextmanager
def signals_blocked(w):
    try:
        w.blockSignals(True)
        yield
    finally:
        w.blockSignals(False)