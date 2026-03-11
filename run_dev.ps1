# repo root 縺ｧ螳溯｡・
# 1) backend襍ｷ蜍・2) frontend build・域僑蠑ｵ縺ｸ蜷梧｢ｱ・・

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd C:\chatbot-react\backend; python -m venv .venv; .\.venv\Scripts\Activate.ps1; python -m pip install --upgrade pip; pip install -r requirements.txt; if(!(Test-Path .env)){ Copy-Item .env.example .env }; uvicorn main:app --host 0.0.0.0 --port 8000"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd C:\chatbot-react\frontend; npm install; npm run build"
