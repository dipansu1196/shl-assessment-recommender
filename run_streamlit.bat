@echo off
echo Starting Streamlit Chat Interface...
echo.
echo The demo will open in your browser at http://localhost:8501
echo.
timeout /t 2
python -m streamlit run streamlit_demo/app.py --logger.level=error
