"""Material 3 baseline schemes, sampled from the same HCT seed (#6750A4).

Precomputed tonal palettes keep the desktop build dependency-free. Components
consume semantic roles; shape and typography are shared tokens.
"""
from PySide6.QtGui import QColor, QPalette

SEED = "#6750A4"
SHAPE = {"extraSmall": 4, "small": 8, "medium": 12, "large": 16, "full": 20}
TYPE = {
    "display": (57, 400), "headline": (28, 400), "titleLarge": (22, 400),
    "title": (16, 500), "body": (14, 400), "bodySmall": (12, 400),
    "label": (14, 500), "labelSmall": (11, 500),
}
SCHEMES = {
    "light": {
        "primary": "#6750A4", "onPrimary": "#FFFFFF",
        "primaryContainer": "#EADDFF", "onPrimaryContainer": "#21005D",
        "secondary": "#625B71", "onSecondary": "#FFFFFF",
        "secondaryContainer": "#E8DEF8", "onSecondaryContainer": "#1D192B",
        "tertiary": "#7D5260", "tertiaryContainer": "#FFD8E4", "onTertiaryContainer": "#31111D",
        "surface": "#FEF7FF", "onSurface": "#1D1B20", "onSurfaceVariant": "#49454F",
        "surfaceContainerLowest": "#FFFFFF", "surfaceContainerLow": "#F7F2FA",
        "surfaceContainer": "#F3EDF7", "surfaceContainerHigh": "#ECE6F0",
        "surfaceContainerHighest": "#E6E0E9", "outline": "#79747E", "outlineVariant": "#CAC4D0",
        "error": "#B3261E", "errorContainer": "#F9DEDC", "onErrorContainer": "#410E0B",
        "inverseSurface": "#322F35", "inverseOnSurface": "#F5EFF7", "inversePrimary": "#D0BCFF",
    },
    "dark": {
        "primary": "#D0BCFF", "onPrimary": "#381E72",
        "primaryContainer": "#4F378B", "onPrimaryContainer": "#EADDFF",
        "secondary": "#CCC2DC", "onSecondary": "#332D41",
        "secondaryContainer": "#4A4458", "onSecondaryContainer": "#E8DEF8",
        "tertiary": "#EFB8C8", "tertiaryContainer": "#633B48", "onTertiaryContainer": "#FFD8E4",
        "surface": "#141218", "onSurface": "#E6E0E9", "onSurfaceVariant": "#CAC4D0",
        "surfaceContainerLowest": "#0F0D13", "surfaceContainerLow": "#1D1B20",
        "surfaceContainer": "#211F26", "surfaceContainerHigh": "#2B2930",
        "surfaceContainerHighest": "#36343B", "outline": "#938F99", "outlineVariant": "#49454F",
        "error": "#F2B8B5", "errorContainer": "#8C1D18", "onErrorContainer": "#F9DEDC",
        "inverseSurface": "#E6E0E9", "inverseOnSurface": "#322F35", "inversePrimary": "#6750A4",
    },
}


def stylesheet(mode="light"):
    c, s = SCHEMES[mode], SHAPE
    rules = []

    def rule(selector, declarations):
        rules.append(f"{selector} {{ {declarations} }}")

    def state_layer(base_role, overlay_role, opacity):
        base, overlay = QColor(c[base_role]), QColor(c[overlay_role])
        return QColor.fromRgbF(*[
            getattr(base, channel)() * (1 - opacity) + getattr(overlay, channel)() * opacity
            for channel in ("redF", "greenF", "blueF")
        ]).name()

    drop_hover = state_layer("surfaceContainerLow", "primaryContainer", 0.35)

    rule("QWidget", f"background: {c['surface']}; color: {c['onSurface']}; font-family: 'Microsoft YaHei UI', 'Segoe UI'; font-size: {TYPE['body'][0]}px;")
    rule("QLabel, QCheckBox", "background: transparent;")
    rule("QWidget#transparent, QScrollArea, QScrollArea > QWidget > QWidget", "background: transparent;")
    rule("QFrame#sidebar", f"background: {c['surfaceContainerLow']}; border: none;")
    rule("QFrame#card, QFrame#footer", f"background: {c['surfaceContainerLow']}; border: none; border-radius: {s['large']}px;")
    rule("QFrame#sheet", f"background: {c['surfaceContainerLow']}; border: 1px solid {c['outlineVariant']}; border-top-left-radius: {s['large']}px; border-top-right-radius: {s['large']}px;")
    rule("QFrame#drop", f"background: {c['surfaceContainerLow']}; border: 1px dashed {c['outline']}; border-radius: {s['large']}px;")
    rule('QFrame#drop[dragging="true"]', f"background: {drop_hover}; border: 2px solid {c['primary']};")
    for selector, token in [("brand", "titleLarge"), ("title", "headline"), ("heading", "title"), ("eyebrow", "labelSmall"), ("caption", "labelSmall"), ("muted", "bodySmall")]:
        size, weight = TYPE[token]
        rule(f"QLabel#{selector}", f"font-size: {size}px; font-weight: {weight};")
    rule("QLabel#muted, QLabel#caption, QLabel#eyebrow", f"color: {c['onSurfaceVariant']};")
    rule("QLabel#accent, QLabel#state", f"color: {c['secondary']};")
    rule("QLabel#mediaIcon", f"background: {c['secondaryContainer']}; color: {c['onSecondaryContainer']}; border-radius: {s['small']}px; font-size: {TYPE['titleLarge'][0]}px;")
    rule("QLabel#dropIcon", f"font-size: {TYPE['headline'][0]}px; color: {c['onSurfaceVariant']};")
    rule("QPushButton", f"background: {c['surfaceContainerHigh']}; color: {c['onSurface']}; border: 1px solid transparent; border-radius: {s['full']}px; padding: 8px 16px; min-height: 22px; font-size: {TYPE['label'][0]}px; font-weight: {TYPE['label'][1]};")
    rule("QPushButton:hover", f"background: {c['surfaceContainerHighest']};")
    rule("QPushButton:pressed", f"background: {c['secondaryContainer']};")
    rule("QPushButton:focus, QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus", f"border: 1px solid {c['secondary']};")
    rule("QPushButton:disabled", f"background: {c['surfaceContainer']}; color: {c['outline']};")
    rule("QPushButton#primary", f"background: {c['primary']}; color: {c['onPrimary']};")
    rule("QPushButton#primary:hover", f"background: {state_layer('primary', 'onPrimary', 0.08)}; color: {c['onPrimary']};")
    rule("QPushButton#primary:pressed", f"background: {state_layer('primary', 'onPrimary', 0.12)}; color: {c['onPrimary']};")
    rule("QPushButton#primary:disabled", f"background: {c['surfaceContainerHighest']}; color: {c['outline']};")
    rule("QPushButton#danger, QPushButton#remove", f"background: transparent; color: {c['error']};")
    rule("QPushButton#danger:hover, QPushButton#remove:hover", f"background: {c['errorContainer']};")
    rule("QPushButton#danger:disabled, QPushButton#remove:disabled", f"background: transparent; color: {c['outline']};")
    rule("QPushButton#chip", f"background: transparent; border: 1px solid {c['outlineVariant']}; border-radius: {s['small']}px; padding: 5px 12px; min-height: 20px;")
    rule("QPushButton#chip:checked", f"background: {c['secondaryContainer']}; color: {c['onSecondaryContainer']}; border-color: transparent;")
    rule("QPushButton#chip:hover", f"background: {c['surfaceContainerHigh']};")
    rule("QPushButton#nav", "background: transparent; text-align: left;")
    rule("QPushButton#nav:checked", f"background: {c['secondaryContainer']}; color: {c['onSecondaryContainer']};")
    rule("QPushButton#icon, QPushButton#remove", f"border-radius: {s['full']}px; padding: 0; min-width: 40px; min-height: 40px; font-size: {TYPE['titleLarge'][0]}px;")
    rule("QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit", f"background: {c['surfaceContainerHighest']}; border: 1px solid {c['outlineVariant']}; border-radius: {s['small']}px; padding: 7px 10px; selection-background-color: {c['secondaryContainer']}; selection-color: {c['onSecondaryContainer']}; min-height: 22px;")
    rule("QWidget:disabled", f"color: {c['outline']};")
    rule("QComboBox::drop-down", "border: none; width: 24px;")
    rule("QComboBox::down-arrow", "image: none;")
    rule("QComboBox QAbstractItemView", f"background: {c['surfaceContainerHigh']}; color: {c['onSurface']}; selection-background-color: {c['secondaryContainer']}; selection-color: {c['onSecondaryContainer']}; border: 1px solid {c['outlineVariant']}; padding: 4px;")
    rule("QTabWidget::pane", "border: none; background: transparent;")
    rule("QTabBar::tab", f"background: transparent; color: {c['onSurfaceVariant']}; padding: 8px 16px; border-bottom: 2px solid transparent;")
    rule("QTabBar::tab:selected", f"color: {c['onSurface']}; border-bottom: 2px solid {c['secondary']};")
    rule("QListWidget", "background: transparent; border: none; outline: none;")
    rule("QListWidget::item", "background: transparent; border: none; padding: 0;")
    rule("QListWidget::item:selected", "background: transparent;")
    rule("QFrame#jobCard", f"background: {c['surfaceContainerLow']}; border: none; border-radius: {s['medium']}px;")
    rule('QFrame#jobCard[selected="true"]', f"background: {c['surfaceContainerHigh']};")
    rule('QFrame#jobCard[failed="true"]', f"background: {c['errorContainer']}; color: {c['onErrorContainer']};")
    rule('QFrame#jobCard[failed="true"] QLabel', f"color: {c['onErrorContainer']};")
    rule("QProgressBar", f"background: {c['surfaceContainerHighest']}; border: none; border-radius: {s['extraSmall']}px; min-height: 4px; max-height: 4px;")
    rule("QProgressBar::chunk", f"background: {c['primary']}; border-radius: {s['extraSmall']}px;")
    rule("QGroupBox", f"font-size: {TYPE['title'][0]}px; font-weight: {TYPE['title'][1]}; border: 1px solid {c['outlineVariant']}; border-radius: {s['medium']}px; margin-top: 18px; padding: 20px 16px 16px;")
    rule("QGroupBox::title", "subcontrol-origin: margin; left: 16px; padding: 0 6px;")
    rule("QScrollArea", "border: none;")
    rule("QScrollBar:vertical", f"width: 8px; background: {c['surfaceContainerLow']}; border: none;")
    rule("QScrollBar::handle:vertical", f"background: {c['outlineVariant']}; min-height: 32px; border-radius: {s['extraSmall']}px;")
    rule("QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical", "height: 0;")
    rule("QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical", "background: transparent;")
    rule("QCheckBox", "spacing: 8px;")
    rule("QCheckBox::indicator", f"width: 18px; height: 18px; border: 1px solid {c['outline']}; border-radius: {s['extraSmall']}px; background: {c['surfaceContainer']};")
    rule("QCheckBox::indicator:checked", f"background: {c['secondary']}; border: 4px solid {c['secondaryContainer']};")
    rule("QSlider::groove:horizontal", f"height: 8px; background: {c['surfaceContainerHighest']}; border-radius: {s['extraSmall']}px;")
    rule("QSlider::sub-page:horizontal", f"background: {c['secondary']}; border-radius: {s['extraSmall']}px;")
    rule("QSlider::handle:horizontal", f"background: {c['secondary']}; width: 4px; margin: -6px 0; border-radius: 2px;")
    rule("QToolTip, QMenu", f"background: {c['surfaceContainerHigh']}; color: {c['onSurface']}; border: 1px solid {c['outlineVariant']}; padding: 6px;")
    rule("QMenu::item", "padding: 8px 20px;")
    rule("QMenu::item:selected", f"background: {c['secondaryContainer']}; color: {c['onSecondaryContainer']};")
    rule("QFrame#snackbar", f"background: {c['inverseSurface']}; border-radius: {s['extraSmall']}px;")
    rule("QFrame#snackbar QLabel", f"color: {c['inverseOnSurface']}; background: transparent;")
    rule("QFrame#snackbar QPushButton", f"background: transparent; color: {c['inversePrimary']};")
    return "\n".join(rules)


def apply_theme(app, mode):
    c = SCHEMES[mode]
    palette = QPalette()
    for role, token in {
        "Window": "surface", "WindowText": "onSurface", "Base": "surfaceContainerLow",
        "AlternateBase": "surfaceContainerHigh", "Text": "onSurface", "Button": "surfaceContainerHigh",
        "ButtonText": "onSurface", "Highlight": "secondaryContainer", "HighlightedText": "onSecondaryContainer",
        "ToolTipBase": "surfaceContainerHigh", "ToolTipText": "onSurface", "Link": "secondary",
    }.items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(c[token]))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(c["outline"]))
    app.setPalette(palette)
    app.setStyleSheet(stylesheet(mode))


# Compatibility for external launchers; MainWindow restores the saved mode.
STYLE = stylesheet("light")
