
web: flask --app app db upgrade && gunicorn app:app --worker-class eventlet --workers 4 --timeout 240 --bind 0.0.0.0:$PORT

