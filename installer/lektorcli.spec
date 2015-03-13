# -*- mode: python -*-
import os

block_cipher = None


a = Analysis(['lektorcli.py'],
             pathex=[os.getcwd()],
             hiddenimports=['code'],
             hookspath=None,
             runtime_hooks=None,
             excludes=['werkzeug'],
             cipher=block_cipher)

pyz = PYZ(a.pure,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='lektor.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='lektorcli')
