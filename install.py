import subprocess
import os
import shutil

def copy_files_with_same_type(type, src_path, dst_path):
    for basename in os.listdir(src_path):
        if basename.endswith(type):
            pathname = os.path.join(srcdir, basename)
            if os.path.isfile(pathname):
                shutil.copy2(pathname, dst_path)

def delete_files_starts_with_same_name(name, path):
    for fname in os.listdir(path):
        if fname.startswith(name):
            os.remove(os.path.join(path, fname))

#delete ./dist/measure if it already exists, otherwise pyinstaller will cast error
path = './dist/measure'
isExist = os.path.exists(path)
if (isExist):
    user_answer = input('/dist/measure already exists, DO YOU WANT TO DELETE FOLDER? (type y to delete, type something else to exit build script) \n')
    if (user_answer == 'y'):
        shutil.rmtree('./dist/measure')
        print('folder /dist/measure deleted')

subprocess.run(['pyinstaller', '--onedir', 'measure.py', '--clean'])

srcdir = '.'
dstdir = './dist/measure'
if (not os.path.exists(dstdir)):
    exit()

copy_files_with_same_type('.ui', srcdir, dstdir)
copy_files_with_same_type('.ini', srcdir, dstdir)

shutil.copytree('./formlayout', './dist/measure/formlayout')
shutil.copytree('./instr', './dist/measure/instr')
shutil.copytree('./mytools', './dist/measure/mytools')

delete_files_starts_with_same_name('api-ms-win','./dist/measure')