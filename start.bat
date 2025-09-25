@echo off
cd /d H:\projects\Python\game-frame\server_backend

:: Start Daphne using Pipenv
pipenv run daphne -p 8000 -b 0.0.0.0 server_backend.asgi:application
