STYLE = """
QWidget { background: #10141e; color: #e6eaf3; font-family: 'Microsoft YaHei UI', 'Segoe UI'; font-size: 12px; }
QMainWindow { background: #10141e; }
QFrame#sidebar { background: #151b28; border-right: 1px solid #272f42; }
QFrame#card, QFrame#footer { background: #191f2e; border: 1px solid #2c3549; border-radius: 12px; }
QFrame#drop { background: #141d2e; border: 2px dashed #3c5074; border-radius: 12px; }
QLabel { background: transparent; }
QLabel#brand { font-size: 24px; font-weight: 700; color: #f0f4ff; }
QLabel#title { font-size: 26px; font-weight: 700; }
QLabel#heading { font-size: 15px; font-weight: 600; }
QLabel#muted { color: #9aa8c1; }
QLabel#eyebrow { color: #8293b2; font-size: 10px; font-weight: 600; }
QLabel#accent { color: #81a9ff; }
QPushButton { background: #252e43; border: 1px solid #3b4963; border-radius: 7px; padding: 8px 13px; font-weight: 500; }
QPushButton:hover { background: #303e5a; border-color: #6d8fc7; }
QPushButton:pressed { background: #1c2840; }
QPushButton:disabled { color: #66738b; background: #1c2331; border-color: #293248; }
QPushButton#primary { background: #527ff5; color: white; border: 1px solid #739cff; font-weight: 600; }
QPushButton#primary:hover { background: #6892ff; }
QPushButton#primary:disabled { background: #2b3b61; color: #8998b5; border-color: #3c4c6e; }
QPushButton#danger { color: #ffb1b8; border-color: #66404b; }
QPushButton#preset { text-align: left; background: #1b2333; padding: 11px 12px; border: 1px solid #2e3a52; }
QPushButton#preset:hover { background: #253653; border-color: #5378b3; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit { background: #111824; border: 1px solid #37445e; border-radius: 6px; padding: 6px 8px; selection-background-color: #4468b4; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus { border-color: #7fa4ff; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: #202a3e; selection-background-color: #365286; border: 1px solid #445576; }
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 18px; }
QTabWidget::pane { border: 1px solid #2c3549; border-radius: 8px; }
QTabBar::tab { color: #96a7c3; background: #151b28; padding: 10px 18px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #dce7ff; border-bottom: 2px solid #739cff; background: #1c2536; }
QTableWidget { background: #161d2b; alternate-background-color: #1a2232; border: none; gridline-color: #293349; selection-background-color: #293f65; outline: none; }
QTableWidget::item { padding: 8px; border-bottom: 1px solid #253045; }
QHeaderView::section { background: #1d2638; color: #9eafca; border: none; padding: 11px 8px; font-weight: 500; }
QProgressBar { background: #111826; border: 1px solid #303c54; border-radius: 5px; text-align: center; color: #dae6ff; min-height: 17px; }
QProgressBar::chunk { background: #527ff5; border-radius: 4px; }
QGroupBox { font-size: 12px; font-weight: 600; color: #d9e2f5; border: 1px solid #2e3a50; border-radius: 9px; margin-top: 16px; padding: 16px 10px 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { width: 10px; background: #131a27; border: none; }
QScrollBar::handle:vertical { background: #3b4a66; min-height: 28px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 10px; background: #131a27; }
QScrollBar::handle:horizontal { background: #3b4a66; min-width: 28px; }
QCheckBox { spacing: 8px; background: transparent; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #536783; border-radius: 4px; background: #121a2a; }
QCheckBox::indicator:checked { background: #739cff; border-color: #b4ccff; }
QSplitter::handle { background: #10141e; width: 12px; }
QToolTip { background: #2a3750; color: #f3f6ff; border: 1px solid #6882ac; padding: 5px; }
QMenu { background: #1c2639; border: 1px solid #465878; }
QMenu::item { padding: 8px 22px; }
QMenu::item:selected { background: #345180; }
"""
