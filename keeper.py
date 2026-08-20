import subprocess
import time
import os
import sys
from datetime import datetime

# ================== 配置区域 ==================
# 请在这里填写你的程序文件名，必须完全一致，包括后缀 .exe
TARGET_EXE_NAME = "微信转发工具.exe"

# 检查间隔时间（秒）
CHECK_INTERVAL = 5

# 日志文件名
LOG_FILE = "guardian_log.txt"
# =============================================

def log_message(message):
    """将带时间戳的日志打印到控制台并写入文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

def is_process_running(process_name):
    """检查指定名称的进程是否正在运行"""
    # 使用 tasklist 命令查找进程
    # 为了处理中文文件名，我们使用 findstr 进行筛选
    output = subprocess.check_output('tasklist', shell=True, text=True, encoding='gbk', errors='ignore')
    return process_name in output

def start_process(process_name):
    """启动指定的程序"""
    try:
        # 使用 start 命令启动程序，这样可以非阻塞地运行
        # 假设 .exe 文件和这个脚本在同一目录下
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        full_path = os.path.join(script_dir, process_name)
        
        if os.path.exists(full_path):
            subprocess.Popen(f'start "" "{full_path}"', shell=True)
            log_message(f"✅ 成功启动程序: {process_name}")
        else:
            log_message(f"❌ 启动失败！未找到程序文件: {full_path}")
    except Exception as e:
        log_message(f"❌ 启动程序时发生错误: {e}")

def main():
    log_message("🛡️ 守护进程已启动，开始监控...")
    log_message(f"🎯 监控目标: {TARGET_EXE_NAME}")
    
    while True:
        if is_process_running(TARGET_EXE_NAME):
            # 进程正在运行，什么都不做
            pass
        else:
            # 进程未运行，尝试启动它
            log_message(f"⚠️ 检测到 {TARGET_EXE_NAME} 未运行，正在尝试启动...")
            start_process(TARGET_EXE_NAME)
        
        # 等待一段时间后再次检查
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()