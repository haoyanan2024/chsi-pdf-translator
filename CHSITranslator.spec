# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from pathlib import Path

datas = collect_data_files('chsi_translator') + collect_data_files('pypinyin')
datas += [('LICENSE', '.'), ('NOTICE', '.'), ('README.md', '.'),
          ('THIRD_PARTY_NOTICES.md', '.'), ('licenses', 'licenses')]
a = Analysis(['run_app.py'], pathex=['.'], binaries=[], datas=datas,
             hiddenimports=['reportlab.pdfbase._cidfontdata'],
             hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['tkinter', 'pytest', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtDesigner'],
             noarchive=False)
# Windows 10+ provides these OS interfaces. Do not redistribute unrelated ICU
# or API-set shims discovered through another tool's PATH entry.
a.binaries = [entry for entry in a.binaries
              if Path(entry[0]).name.lower() not in {'icuuc.dll', 'icuin.dll'}
              and not Path(entry[0]).name.lower().startswith(('api-ms-win-', 'ext-ms-win-'))]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='CHSITranslator',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False,
          version='installer/version_info.txt')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='CHSITranslator')
