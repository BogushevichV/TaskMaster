APP_STYLE = """
/* ── Base ─────────────────────────────────────────────────── */
QWidget {
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #1e293b;
    background-color: #f1f5f9;
}

QDialog {
    background-color: #ffffff;
}

/* ── Login card ───────────────────────────────────────────── */
QFrame#LoginCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}

QLabel#AppTitle {
    font-size: 24px;
    font-weight: 700;
    color: #1e293b;
    letter-spacing: 0px;
}

QLabel#AppSubtitle {
    font-size: 12px;
    color: #64748b;
}

/* ── Inputs ───────────────────────────────────────────────── */
QLineEdit, QTextEdit, QComboBox, QDateEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus {
    border-color: #2563eb;
    background-color: #ffffff;
}

QLineEdit:read-only {
    background-color: #f8fafc;
    color: #64748b;
}

QLineEdit::placeholder, QTextEdit[placeholderText]:empty {
    color: #94a3b8;
}

/* ── Buttons ──────────────────────────────────────────────── */
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
    font-size: 13px;
    min-width: 76px;
}

QPushButton:hover {
    background-color: #1d4ed8;
}

QPushButton:pressed {
    background-color: #1e40af;
}

QPushButton:disabled {
    background-color: #94a3b8;
    color: #e2e8f0;
}

QPushButton#SecondaryBtn {
    background-color: #f8fafc;
    color: #334155;
    border: 1px solid #cbd5e1;
    font-weight: 500;
}

QPushButton#SecondaryBtn:hover {
    background-color: #e2e8f0;
    border-color: #94a3b8;
}

QPushButton#SecondaryBtn:pressed {
    background-color: #cbd5e1;
}

QPushButton#DangerBtn {
    background-color: #ef4444;
    color: #ffffff;
}

QPushButton#DangerBtn:hover {
    background-color: #dc2626;
}

QPushButton#DangerBtn:pressed {
    background-color: #b91c1c;
}

/* ── Table ────────────────────────────────────────────────── */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #f1f5f9;
    alternate-background-color: #f8fafc;
    selection-background-color: #eff6ff;
    selection-color: #1e293b;
    outline: none;
}

QTableWidget::item {
    padding: 6px 12px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #dbeafe;
    color: #1e3a8a;
}

QHeaderView {
    background-color: #f1f5f9;
}

QHeaderView::section {
    background-color: #f1f5f9;
    color: #475569;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 12px;
    border: none;
    border-right: 1px solid #e2e8f0;
    border-bottom: 2px solid #e2e8f0;
}

QHeaderView::section:last {
    border-right: none;
}

/* ── ComboBox drop-down ───────────────────────────────────── */
QComboBox::drop-down {
    border: none;
    width: 22px;
}

QComboBox::down-arrow {
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #64748b;
    margin-right: 6px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    selection-background-color: #eff6ff;
    selection-color: #1e293b;
    padding: 4px;
    outline: none;
}

/* ── Status bar ───────────────────────────────────────────── */
QStatusBar {
    background-color: #f8fafc;
    color: #475569;
    border-top: 1px solid #e2e8f0;
    font-size: 12px;
}

QStatusBar QLabel {
    background-color: transparent;
    font-size: 12px;
    padding: 0 6px;
}

/* ── Main window toolbar area ─────────────────────────────── */
QWidget#Toolbar {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
}

/* ── Scrollbars ───────────────────────────────────────────── */
QScrollBar:vertical {
    background-color: #f8fafc;
    width: 8px;
    border-radius: 4px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #cbd5e1;
    border-radius: 4px;
    min-height: 32px;
}

QScrollBar::handle:vertical:hover {
    background-color: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #f8fafc;
    height: 8px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #cbd5e1;
    border-radius: 4px;
    min-width: 32px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #94a3b8;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Dialog button box ────────────────────────────────────── */
QDialogButtonBox QPushButton {
    min-width: 90px;
}
"""
