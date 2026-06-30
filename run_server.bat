@echo off
echo Starting SHL Assessment Recommender API...
echo.
echo This will start the server on http://localhost:8000
echo.
echo Press CTRL+C to stop the server when done.
echo.
timeout /t 3
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
