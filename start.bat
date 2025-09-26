@echo off
cd server_backend

:: Start Daphne using Pipenv

rem start "Game-Frame Backend Server" 
pipenv run daphne -p 8000 -b 0.0.0.0 server_backend.asgi:application
rem caddy run
