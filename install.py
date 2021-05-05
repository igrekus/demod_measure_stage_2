import subprocess

subprocess.run(['pyinstaller', '--onedir', 'measure.py', '--clean'])
# subprocess.run(['pyinstaller', '--onedir', 'measure.spec', '--clean'])
