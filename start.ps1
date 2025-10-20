pushd server_backend

# Start Daphne server
Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    '$Host.UI.RawUI.WindowTitle = "Django Server"; Clear-Host; pipenv run daphne -p 8000 -b 0.0.0.0 server_backend.asgi:application'
)

# Start Caddy server
Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    '$Host.UI.RawUI.WindowTitle = "Caddy Proxy"; Clear-Host; caddy run'
)

popd
