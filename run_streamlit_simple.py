import subprocess
import os
import sys

# Disable Streamlit telemetry and analytics
os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'

print("Starting Streamlit Chat Interface...")
print()
print("Opening at: http://localhost:8501")
print()
print("Make sure FastAPI server is running on http://localhost:8000")
print()

# Run Streamlit
subprocess.run([
    sys.executable, '-m', 'streamlit', 'run',
    'streamlit_demo/app.py',
    '--logger.level=error',
    '--client.toolbarMode=minimal'
], cwd='d:\\SHL Assignment')
