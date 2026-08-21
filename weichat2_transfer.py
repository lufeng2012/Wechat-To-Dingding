import time
import hmac
import hashlib
import base64
import urllib.parse
import re
import random
import os
import sys
import winsound
from datetime import datetime

from wxauto import WeChat
import requests
import json

# ================== 报警与重启机制 ==================
ALARM_COUNT = 0           # 报警计数器
MAX_ALARM_BEFORE_RESTART = 3 # 超过3次报警后重启
RETRY_COUNT = 0           # 钉钉发送失败重试计数器
MAX_RETRY_BEFORE_RESTART = 3    # 钉钉发送失败重试3次后重启

def play_alarm():
    """让电脑发出 bingbing 报警声"""
    global ALARM_COUNT
    ALARM_COUNT += 1
    print(f"[{datetime.now()}] 🚨 触发报警！当前累计次数: {ALARM_COUNT}/{MAX_ALARM_BEFORE_RESTART}")
    
    # 发出声音
    try:
        for _ in range(5): 
            winsound.Beep(1000, 300)
            time.sleep(0.1)
    except:
        pass 

    if ALARM_COUNT >= MAX_ALARM_BEFORE_RESTART:
        print(f"[{datetime.now()}] 🔴 报警次数已达 {MAX_ALARM_BEFORE_RESTART} 次，即将重启程序...")
        restart_program()

def restart_program():
    """杀掉当前进程并重新启动"""
    print(f"[{datetime.now()}] 🔄 正在重启程序...")
    time.sleep(2)  # 等待2秒，确保日志输出完毕
    
    # 获取当前可执行文件路径（兼容 exe 和 python 脚本）
    if getattr(sys, 'frozen', False):
        executable = sys.executable
        args = []
    else:
        executable = sys.executable
        args = sys.argv
    
    # 用 os.execv 替换当前进程（杀掉旧的，启动新的）
    os.execv(executable, [executable] + args)

# ================== 加载配置文件 ==================
def load_config(config_path="config.json"):
    """从JSON配置文件中加载配置"""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    full_path = os.path.join(base_dir, config_path)
    
    if not os.path.exists(full_path):
        print(f"❌ 配置文件不存在: {full_path}")
        print("请在程序同目录下创建 config.json 文件，参考以下格式：")
        print('''{
    "dingtalk_robots": [
        {"webhook": "你的webhook地址", "secret": "你的secret"}
    ],
    "wx_forward_groups": ["群名1", "群名2"],
    "listen_list": ["个人交流平台", "教学老师"]
}''')
        sys.exit(1)
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"✅ 配置文件加载成功: {full_path}")
        return config
    except json.JSONDecodeError as e:
        print(f"❌ 配置文件JSON格式错误: {e}")
        print("请检查 config.json 中是否有语法问题（如缺少逗号、引号不匹配等）")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 读取配置文件时出错: {e}")
        sys.exit(1)

# 加载配置
config = load_config()

# 从配置中读取各项参数
DINGTALK_ROBOTS = config.get("dingtalk_robots", [])
WX_FORWARD_GROUPS = config.get("wx_forward_groups", [])
LISTEN_LIST = config.get("listen_list", [])
# ==================================================

def get_dingtalk_sign(secret):
    timestamp = str(round(time.time() * 1000))
    secret_enc = secret.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return timestamp, sign

def send_to_dingtalk(msg_type, content, sender="未知"):
    """发送消息到钉钉，包含重试和熔断机制"""
    global RETRY_COUNT
    
    # 遍历所有钉钉机器人
    for robot in DINGTALK_ROBOTS:
        webhook = robot['webhook']
        secret = robot['secret']
        
        timestamp, sign = get_dingtalk_sign(secret)
        url = f"{webhook}&timestamp={timestamp}&sign={sign}"
        headers = {'Content-Type': 'application/json'}
        
        if content: 
            content_to_send = content[:4096]
            data = {
                "msgtype": "text",
                "text": {
                    "content": f"【来自 {sender}】\n{content_to_send}"
                }
            }
        else:
            data = {
                "msgtype": "text",
                "text": {
                    "content": f"【来自 {sender}】\n发来了一条{msg_type}消息，请在微信中查看。"
                }
            }

        # 重试循环
        while RETRY_COUNT < MAX_RETRY_BEFORE_RESTART:
            try:
                response = requests.post(url, headers=headers, data=json.dumps(data))
                result = response.json()
                if result.get('errcode') == 0:
                    # 发送成功，重置重试计数器
                    RETRY_COUNT = 0
                    return
                else:
                    # 钉钉API返回错误
                    print(f"[{datetime.now()}] 钉钉发送失败 (Webhook: {webhook[:20]}...): {result.get('errmsg')}")
                    play_alarm()
                    RETRY_COUNT += 1
                    print(f"[{datetime.now()}] 钉钉发送失败，正在重试... (第 {RETRY_COUNT}/{MAX_RETRY_BEFORE_RESTART} 次)")
                    
            except Exception as e:
                # 网络请求异常
                print(f"[{datetime.now()}] 发送钉钉请求时出错 (Webhook: {webhook[:20]}...): {e}")
                play_alarm()
                RETRY_COUNT += 1
                print(f"[{datetime.now()}] 钉钉发送出错，正在重试... (第 {RETRY_COUNT}/{MAX_RETRY_BEFORE_RESTART} 次)")
            
            # 每次重试前等待1秒
            time.sleep(1)
        
        # 如果循环结束，说明重试次数已用尽
        print(f"[{datetime.now()}] 🔴 钉钉消息发送重试 {MAX_RETRY_BEFORE_RESTART} 次均失败，即将重启程序...")
        restart_program()

def send_to_wx_groups(wx, content, sender="未知"):
    """将消息转发到指定的微信群，每个群之间随机间隔5-15秒"""
    if not content:
        forward_content = f"【来自 {sender}】\n发来了一条消息，请在微信中查看。"
    else:
        forward_content = f"【来自 {sender}】\n{content[:4096]}"
    
    for group_name in WX_FORWARD_GROUPS:
        try:
            wx.SendMsg(msg=forward_content, who=group_name)
            print(f"[{datetime.now()}] ✅ 已转发到微信群: {group_name}")
            delay = random.randint(5, 15)
            print(f"[{datetime.now()}] 等待 {delay} 秒后发送下一个群...")
            time.sleep(delay)
        except Exception as e:
            print(f"[{datetime.now()}] ❌ 转发到微信群失败 ({group_name}): {e}")

# ================== 消息脱敏处理 ==================
def process_message(content):
    if not content:
        return content

    processed = content

    processed = re.sub(r'【以上观点[^】]*】', '', processed, flags=re.DOTALL)
    processed = re.sub(r'投资顾问\s*\S+.*$', '', processed, flags=re.DOTALL)

    if '减仓' in processed:
        stock_info = None
        match = re.search(r'([\u4e00-\u9fa5A-Za-z]+\s*[（(]\s*\d{5,6}\s*[）)])', processed)
        if match:
            stock_info = match.group(1)
        else:
            match2 = re.match(r'^(?:研究建议[：:])?\s*([\u4e00-\u9fa5A-Za-z]+)\s*.*?减仓', processed.strip())
            if match2:
                stock_info = match2.group(1)
        if stock_info:
            processed = f"{stock_info}\n这个股票，上窜下蹦，我心脏不好，我要减仓了，股票不是银行，盈亏自付，我的操作个人操作，大家不要受我的操盘影响，自行操作就好"
            return processed

    if '公司研究教学关注' in processed:
        stock_match = re.search(r'([\u4e00-\u9fa5A-Za-z]+\s*[（(]\s*\d{5,6}\s*[）)])', processed)
        stock_info = stock_match.group(1) if stock_match else ""
        
        processed = re.sub(r'\d+\.?\d*元附近建议关注[\d成%仓位]+', '', processed)
        processed = re.sub(r'类型：[^。；\n]*', '', processed)
        processed = re.sub(r'参考止损价\s*[\d.]+\s*元', '', processed)
        
        processed = re.sub(r'【教学建议】\s*——\s*公司研究教学关注[：:]\s*', '', processed)
        processed = processed.strip()
        
        if stock_info:
            if processed.startswith(stock_info):
                processed = processed[len(stock_info):].strip()
            processed = f"{stock_info}大家怎么看。\n{processed}"
        else:
            processed = f"{processed}\n大家怎么看。"
            
        return processed

    if '研究建议' in processed and '加仓' in processed:
        match = re.search(r'([\u4e00-\u9fa5A-Za-z]+\s*[（(]\s*\d{5,6}\s*[）)])', processed)
        if match:
            stock_info = match.group(1)
            processed = f"{stock_info}\n这个票大家怎么看，不是重复消息，不是重复消息，股票不是银行，盈亏自付"
            return processed

    if '研究建议' in processed and '止盈' in processed:
        match = re.search(r'([\u4e00-\u9fa5A-Za-z]+\s*[（(]\s*\d{5,6}\s*[）)])', processed)
        if match:
            stock_info = match.group(1)
            processed = f"{stock_info}\n这个股票，上窜下蹦，我心脏不好，准备先走了，股票不是银行，盈亏自付，我的操作个人操作，大家不要受我的操盘影响，自行操作就好"
            return processed

    return processed
# ==================================================

def init_wechat():
    """初始化微信连接，任何错误都立即报警并重试"""
    RETRY_INTERVAL = 10  # 每次失败后等待10秒重试
    
    wx = None
    # 第一阶段：死磕 WeChat() 实例化，直到成功
    while wx is None:
        try:
            print(f"[{datetime.now()}] 正在尝试连接微信核心服务...")
            wx = WeChat()
            print(f"[{datetime.now()}] ✅ 微信核心服务连接成功！")
        except Exception as e:
            print(f"[{datetime.now()}] ❌ 微信核心初始化失败: {e}")
            play_alarm()
            print(f"[{datetime.now()}] {RETRY_INTERVAL} 秒后重试...")
            time.sleep(RETRY_INTERVAL)
            # 如果报警次数达到上限，restart_program 会直接重启，不会执行到这里

    # 第二阶段：死磕 AddListenChat，直到所有监听都成功
    all_listens_successful = False
    while not all_listens_successful:
        all_listens_successful = True  # 先假设本次循环能全部成功
        print(f"[{datetime.now()}] 正在尝试添加所有监听对象...")
        
        # 获取联系人列表（这里出错也会报警）
        try:
            all_contacts = wx.GetAllFriends()
            print("所有联系人列表：")
            for contact in all_contacts:
                print(f"  - {contact}")
        except Exception as e:
            print(f"[{datetime.now()}] ❌ 获取联系人列表失败: {e}")
            play_alarm()
            all_listens_successful = False # 获取列表失败，视为整体失败，需要重试
            time.sleep(RETRY_INTERVAL)
            continue # 跳过本次循环，重新开始

        # 遍历需要监听的列表
        for name in LISTEN_LIST:
            try:
                # 尝试添加监听
                wx.AddListenChat(who=name)
                print(f"✅ 成功添加监听: {name}")
            except Exception as e:
                print(f"[{datetime.now()}] ❌ 添加监听失败: {name}, 错误: {e}")
                play_alarm()
                all_listens_successful = False # 只要有一个失败，就标记为整体失败
                # 不 break，继续尝试添加列表中的下一个，但本次循环结束后会整体重试
        
        if not all_listens_successful:
            print(f"[{datetime.now()}] 部分监听添加失败，{RETRY_INTERVAL} 秒后整体重试...")
            time.sleep(RETRY_INTERVAL)
            
    print(f"[{datetime.now()}] ✅ 所有监听对象添加成功！微信初始化完成。")
    return wx

def main():
    wx = init_wechat()

    print(f"程序已启动，正在监听: {LISTEN_LIST}")
    print(f"消息将同时转发到 {len(DINGTALK_ROBOTS)} 个钉钉群 和 {len(WX_FORWARD_GROUPS)} 个微信群")

    while True:
        try:
            msgs = wx.GetListenMessage()
            
            if msgs:
                print(f"[{datetime.now()}] 收到 {len(msgs)} 个聊天的新消息")
                
                for chat_obj, msg_list in msgs.items():
                    who = getattr(chat_obj, 'who', str(chat_obj)) 
                    
                    for msg in msg_list:
                        msg_type = msg.type
                        msg_content = msg.content
                        current_time = datetime.now().strftime("%H:%M:%S")
                        
                        print(f"[{current_time}] {who}: [{msg_type}] {msg_content}")
                        
                        if who in LISTEN_LIST or any(name in who for name in LISTEN_LIST):
                            processed_content = process_message(msg_content)
                            send_to_dingtalk(msg_type, processed_content, sender=who)
                            send_to_wx_groups(wx, processed_content, sender=who)
                            
        except Exception as e:
            print(f"[{datetime.now()}] 程序运行出错: {e}")
            play_alarm()
            time.sleep(5)
            
        time.sleep(1)

if __name__ == '__main__':
    main()