Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
python -m PyInstaller --onefile --name 微信转发工具 weichat2_transfer.py