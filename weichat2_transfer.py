import time
import hmac
import hashlib
import base64
import urllib.parse
from datetime import datetime

from wxauto import WeChat
import requests
import json

# ================== 钉钉机器人配置 ==================
DINGTALK_WEBHOOK = 'https://oapi.dingtalk.com/robot/send?access_token=8a1887fb0a8c6181db676173963cb638711eea971faf922f0ae4c8f2dbd680c1'
DINGTALK_SECRET = 'SEC4feb9e223eaec10d6cf20fea273a94d0f0f72fa8a729a70ea0a91f494e10eab1'
# ==================================================

def get_dingtalk_sign():
    timestamp = str(round(time.time() * 1000))
    secret_enc = DINGTALK_SECRET.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, DINGTALK_SECRET)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return timestamp, sign

def send_to_dingtalk(msg_type, content, sender="未知"):
    timestamp, sign = get_dingtalk_sign()
    url = f"{DINGTALK_WEBHOOK}&timestamp={timestamp}&sign={sign}"
    headers = {'Content-Type': 'application/json'}
    
    # 核心修改：只要 content 不为空，就发送文本内容
    if content: 
        content_to_send = content[:4096]
        data = {
            "msgtype": "text",
            "text": {
                "content": f"【来自 {sender}】\n{content_to_send}"
            }
        }
    else:
        # 只有当 content 确实为空时，才发送提示语
        data = {
            "msgtype": "text",
            "text": {
                "content": f"【来自 {sender}】\n发来了一条{msg_type}消息，请在微信中查看。"
            }
        }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        result = response.json()
        if result.get('errcode') != 0:
            print(f"[{datetime.now()}] 钉钉发送失败: {result.get('errmsg')}")
    except Exception as e:
        print(f"[{datetime.now()}] 发送钉钉请求时出错: {e}")

def main():
    wx = WeChat()
    
    # 打印所有好友/群列表，用于确认准确名称
    all_contacts = wx.GetAllFriends()
    print("所有联系人列表：")
    for contact in all_contacts:
        print(f"  - {contact}")
    
    # 替换为你从上面列表中复制的准确名称
    listen_list = ['泰山鲁','周彩钰A0220623080007'] 
    
    # 显式添加监听对象（白名单机制）
    for name in listen_list:
        try:
            wx.AddListenChat(who=name)
            print(f"✅ 成功添加监听: {name}")
        except Exception as e:
            print(f"❌ 添加监听失败，请检查名称是否正确: {name}, 错误: {e}")

    print(f"程序已启动，正在监听: {listen_list}")

    while True:
        try:
            msgs = wx.GetListenMessage()
            
            # 只有当字典不为空时才打印日志，避免刷屏
            if msgs:
                print(f"[{datetime.now()}] 收到 {len(msgs)} 个聊天的新消息")
                
                # 核心修复：使用 .items() 遍历字典
                # chat_obj 是聊天窗口对象，msg_list 是消息列表
                for chat_obj, msg_list in msgs.items():
                    # 获取聊天对象的名称（即 who）
                    # wxauto 的 ChatWnd 对象通常可以通过 .who 属性获取名称
                    who = getattr(chat_obj, 'who', str(chat_obj)) 
                    
                    for msg in msg_list:
                        msg_type = msg.type
                        msg_content = msg.content
                        current_time = datetime.now().strftime("%H:%M:%S")
                        
                        print(f"[{current_time}] {who}: [{msg_type}] {msg_content}")
                        
                        # 检查发送者是否在监听列表中
                        # 使用 in 关键字进行模糊匹配，防止备注名不完全一致
                        if who in listen_list or any(name in who for name in listen_list):
                            send_to_dingtalk(msg_type, msg_content, sender=who)
                            
        except Exception as e:
            print(f"[{datetime.now()}] 程序运行出错: {e}")
            time.sleep(5)
            
        time.sleep(1)

if __name__ == '__main__':
    main()