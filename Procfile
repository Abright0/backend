release: python manage.py collectstatic --noinput
web: python manage.py migrate && gunicorn project.wsgi:application --bind 0.0.0.0:$PORT