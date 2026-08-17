import time
import hmac
import hashlib
import base64
import urllib.parse
import re
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

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        result = response.json()
        if result.get('errcode') != 0:
            print(f"[{datetime.now()}] 钉钉发送失败: {result.get('errmsg')}")
    except Exception as e:
        print(f"[{datetime.now()}] 发送钉钉请求时出错: {e}")


# ================== 消息脱敏处理 ==================
def process_message(content):
    if not content:
        return content

    processed = content

    # 通用清理：先删【以上观点...】整块，再删投资顾问
    processed = re.sub(r'【以上观点[^】]*】', '', processed, flags=re.DOTALL)
    processed = re.sub(r'投资顾问\s*\S+.*$', '', processed, flags=re.DOTALL)

    # ★ 需求D（减仓）提到最前面，优先判断 ★
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

    # 需求A：教学建议类消息
    if '公司研究教学关注' in processed:
        processed = re.sub(r'【教学建议】\s*——\s*公司研究教学关注[：:]\s*', '', processed)
        processed = re.sub(
            r'([\u4e00-\u9fa5A-Za-z]+\s*[（(]\s*\d{5,6}\s*[）)])[\s\d.元\-附近教学关注%仓位清仓]+',
            r'\1 ',
            processed
        )
        processed = re.sub(r'参考止损价\s*[\d.]+\s*元', '', processed)
        processed = processed.strip() + '\n大家怎么看。'
        return processed

    # 需求B：加仓类消息
    if '研究建议' in processed and '加仓' in processed:
        match = re.search(r'([\u4e00-\u9fa5A-Za-z]+\s*[（(]\s*\d{5,6}\s*[）)])', processed)
        if match:
            stock_info = match.group(1)
            processed = f"{stock_info}\n这个票大家怎么看，不是重复消息，不是重复消息，股票不是银行，盈亏自付"
            return processed

    # 需求C：止盈类消息
    if '研究建议' in processed and '止盈' in processed:
        match = re.search(r'([\u4e00-\u9fa5A-Za-z]+\s*[（(]\s*\d{5,6}\s*[）)])', processed)
        if match:
            stock_info = match.group(1)
            processed = f"{stock_info}\n这个股票，上窜下蹦，我心脏不好，准备先走了，股票不是银行，盈亏自付，我的操作个人操作，大家不要受我的操盘影响，自行操作就好"
            return processed

    # 需求E：兜底 - 通用清理已完成，直接返回
    return processed
# ==================================================

def main():
    wx = WeChat()
    
    all_contacts = wx.GetAllFriends()
    print("所有联系人列表：")
    for contact in all_contacts:
        print(f"  - {contact}")
    
    listen_list = ['个人交流平台', '教学老师'] 
    
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
            
            if msgs:
                print(f"[{datetime.now()}] 收到 {len(msgs)} 个聊天的新消息")
                
                for chat_obj, msg_list in msgs.items():
                    who = getattr(chat_obj, 'who', str(chat_obj)) 
                    
                    for msg in msg_list:
                        msg_type = msg.type
                        msg_content = msg.content
                        current_time = datetime.now().strftime("%H:%M:%S")
                        
                        print(f"[{current_time}] {who}: [{msg_type}] {msg_content}")
                        
                        if who in listen_list or any(name in who for name in listen_list):
                            processed_content = process_message(msg_content)
                            send_to_dingtalk(msg_type, processed_content, sender=who)
                            
        except Exception as e:
            print(f"[{datetime.now()}] 程序运行出错: {e}")
            time.sleep(5)
            
        time.sleep(1)

if __name__ == '__main__':
    main()