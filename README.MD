/* -- ZENITHKITCHEN HMI--
 * Created by : Calvin Prasetya L.
 * Released at : 24 Juni 2026
 * updated at : 24 Juni 2026 (home)
 * myapp : hmi
 * myproject : projects
 */

/* =====================================
    PYTHON COMMAND LINES FOR WINDOWS
   =====================================
*/
>> to install package for global environment :
 1. sudo /usr/bin/python -m pip install package_name --break-system-packages
 
>> For setting up python Environments :
 1. sudo apt update
 2. sudo apt install python3-venv
 3. python.exe -m venv .venv
 4.  .\.venv\Scripts\activate
 5. pip install pipenv
 6. pipenv install <package-name>

>> Create new project and app :
 1. django-admin.exe startproject myproject
 2. cd myproject
 3. python.exe manage.py startapp myapp

>> Save and install python dependencies :
 1. pip freeze > requirements.txt
 2. pip install -r requirements.txt
 3. pip install pipenv
 4. pipenv install
 5. pipenv sync
 6. pipenv update
 7. pipenv graph
 8. pipenv lock

>> Setup settings.py :
 1. python manage.py makemigrations myapp
 2. python manage.py migrate
 3. python manage.py createsuperuser      => for creating superuser admin login

>> How to reset migrations :
 1. find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
 2. find . -path "*/migrations/*.pyc" -delete
 3. DROP SCHEMA

>> Setup settings.py for databases :
 1. Set DATABASES on settings.py
 2. Set MODELS on models.py
 3. python manage.py migrate --database=default
 4. python manage.py migrate --database=sqlite_db

>> to collect all static files :
 1. python manage.py collectstatic

>> Running Server :
 1. python manage.py runserver

>> To give access to other devices: 
 1. Go to setting.py
 2. Update to ALLOWED_HOSTS = ['*']
 3. Run : python manage.py runserver 0.0.0.0:8000   -> for WSGI (Sync Server)
 4. Run : daphne -b 0.0.0.0 -p 8000 projects.asgi:application  -> for ASGI (Async Server)

>> How to create a package :
1. python -m compileall
2. pyinstaller --onefile --noconsole --noconfirm --name=zenithkitchen \
    --add-data "../.env:." \
    --add-data "databases/:databases" \
    --add-data "integrations/:integrations" \
    --add-data "services/:services" \
    --add-data "utils/:utils" \
    --add-data "hmi/:hmi" \
    --add-data "projects/:projects" \
    --add-data "staticfiles/:staticfiles" \
    run_django.py

/* =====================================
    GIT COMMAND LINES
   =====================================
*/
# -------------------------------
# 1. SETUP AWAL
# -------------------------------
1. git clone <repo-url>
2. cd <project-folder>
3. git status
# NOTE: selalu cek status repo sebelum mulai

# -------------------------------
# 2. UPDATE PROJECT (SEBELUM CODING)
# -------------------------------
1. git pull origin main
# NOTE: hindari conflict dengan update dulu

# -------------------------------
# 3. CREATE & PUSH NEW BRANCH
# -------------------------------
1. git checkout -b feature/nama-fitur
2. git push -u origin feature/nama-fitur
# NOTE: gunakan prefix: feature/, fix/, hotfix/

# -------------------------------
# 4. PINDAH BRANCH
# -------------------------------
1. git switch nama-branch
# alternatif:
2. git checkout nama-branch

# -------------------------------
# 5. CEK SEMUA BRANCH
# -------------------------------
1. git branch        # lokal
2. git branch -r     # remote
3. git branch -a     # semua
4. git branch -vva   # detail + tracking

# -------------------------------
# 6. ADD, COMMIT, PUSH
# -------------------------------
1. git add .
2. git commit -m "deskripsi perubahan"
3. git push
# NOTE: jangan commit langsung ke main (best practice tim)

# -------------------------------
# 7. MERGE BRANCH (STANDARD FLOW)
# -------------------------------
1. git checkout main
2. git pull origin main
3. git merge feature/nama-fitur
4. git push origin main
# NOTE: resolve conflict jika ada

# -------------------------------
# 8. SYNC BRANCH DENGAN MAIN
# -------------------------------
1. git checkout feature/nama-fitur
2. git pull origin main
# alternatif:
3. git merge main

# -------------------------------
# 9. RESET LOCAL (HATI-HATI ⚠️)
# -------------------------------
1. git fetch origin
2. git reset --hard origin/main
# NOTE: semua perubahan lokal akan hilang

# -------------------------------
# 10. CLEAN FILE (HAPUS FILE TAK TERTRACK)
# -------------------------------
1. git clean -fd
# NOTE: hapus file/folder yang tidak di-track

# -------------------------------
# 11. STASH (SIMPAN SEMENTARA)
# -------------------------------
1. git stash
2. git stash pop
# NOTE: dipakai saat mau pindah branch tapi belum commit

# -------------------------------
# 12. BACKUP BRANCH
# -------------------------------
1. git checkout main
2. git pull origin main
3. git checkout -b backup/main_YYYYMMDD
4. git push -u origin backup/main_YYYYMMDD

# -------------------------------
# 13. .GITIGNORE (__pycache__, dll)
# -------------------------------
# isi file .gitignore:
# __pycache__/
# *.pyc
# .env

1. git rm -r --cached __pycache__
2. git rm -r --cached *.pyc
3. git add .gitignore
4. git commit -m "update gitignore"
5. git push

# -------------------------------
# 14. AMBIL FILE DARI COMMIT LAMA
# -------------------------------
1. git log -- nama_file
2. git checkout <commit-hash> -- nama_file
# alternatif modern:
3. git restore --source=<commit> nama_file

# -------------------------------
# 15. COMPARE BRANCH
# -------------------------------
4. git diff main feature/nama-fitur

# -------------------------------
# 16. CEK STATUS (PALING PENTING)
# -------------------------------
5. git status

/* =====================================
    PM2 COMMAND LINES
   =====================================
*/
>> How to run in pm2:
1. pm2 start /home/scada03/DJANGO/ZenithKitchen/zenithkitchen/dist/zenithkitchen\
  --name zenithkitchen 
2. pm2 start /home/calvin2803/Documents/Django/ZenithKitchen/zenithkitchen/dist/zenithkitchen\
  --name zenithkitchen 
3. pm2 start /root/CALVIN_FILES/DJANGO/ZenithKitchen/zenithkitchen/dist/zenithkitchen\
  --name zenithkitchen 

>> how to set pm2 autostart when booting :
1. pm2 save
2. pm2 startup

/* =====================================
    X11VNC COMMAND LINES
   =====================================
*/
>> How to run x11vnc :
1. Makse sure desktop environment run on x11 / ubuntu on xorg
1. x11vnc -display :0 -auth guess -forever -nopw
