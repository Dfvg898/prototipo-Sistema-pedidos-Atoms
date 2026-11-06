# descarga el proyecto
git clone "url del proyecto"
# luego instalar librerias necesarias
pip o pipenv install -r requirements.txt
# luego hacer migraciones
py manage.py migrate

# si da error hacer makemigrations

# iniciar proyecto
py manage.py runserver