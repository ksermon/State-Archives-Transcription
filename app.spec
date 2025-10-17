block_cipher = None

a = Analysis(
    ['launch.py'],
    pathex=[],
    binaries=[],
    datas=[
        # include your templates/static so Flask can find them in the bundle:
        ('yourpackage/templates', 'yourpackage/templates'),
        ('yourpackage/static', 'yourpackage/static'),
    ],
    hiddenimports=[
        # Add any tricky libs here (torch/transformers often need nudges)
        'torch', 'transformers', 'PIL._imaging', 'google.generativeai'
    ],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='StateArchivesTranscription',
    console=False,     # no console window
    icon='icon.ico',   # optional: add icon file to repo root
)
