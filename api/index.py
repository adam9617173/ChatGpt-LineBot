from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import os

# 取得環境變數
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
DEFAULT_TALKING = os.getenv("DEFAULT_TALKING", "true").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 確保環境變數存在
if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    raise ValueError("⚠️ LINE_CHANNEL_ACCESS_TOKEN 或 LINE_CHANNEL_SECRET 未設定，請檢查 Vercel 環境變數！")
if not OPENAI_API_KEY:
    raise ValueError("⚠️ OPENAI_API_KEY 未設定，請檢查 Vercel 環境變數！")

# 初始化 LINE API
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
line_handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 設定 OpenAI API Key
openai.api_key = OPENAI_API_KEY

# Flask 伺服器
app = Flask(__name__)

# 記錄 AI 狀態
working_status = DEFAULT_TALKING

# **固定提示詞**
system_prompt = """
你是一位專業的文案撰寫 AI，專門根據用戶提供的主題，撰寫 5 種不同類型的文案。
你的回答只能包含文案本身，不提供任何解釋、分析或額外資訊。

輸出規則：
- 每次輸出 2 種不同類型的文案，類型可包含（但不限於）：
  - 情感共鳴型 / 加深恐懼型 / 製造好奇型 / 痛苦欲望型 / 催眠故事型
  - 專家權威型 / 客戶見證型 / 限時優惠型 / 對比反差型 / 問題解決方案型
  - 比喻類比型 / 未來展望型 / 身份認同型 / 故事懸念型

格式要求：
- 先標明文案類型（例如：「情感共鳴型」）。
- 直接開始正文，不加任何標題。
- 確保起承轉合流暢，提升可讀性。

禁止事項：
- 不提供額外解釋、分析、或方法論。
- 不加入「這是一篇…」等提示語句。
- 只輸出文案，不要標題和內文標識。
"""

# **全局變數：儲存每位使用者的對話歷史**
user_sessions = {}

@app.route('/')
def home():
    return '✅ Line AI Bot is running!'

@app.route('/favicon.ico')
def favicon():
    return '', 204  # 204 = No Content

@app.route("/webhook", methods=['POST'])
def callback():
    """接收 LINE Webhook 訊息"""
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("📩 收到 Webhook 訊息: " + body)

    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@line_handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """處理使用者訊息，支援多使用者對話上下文"""
    global working_status

    # 檢查是否為文字訊息
    if event.message.type != "text":
        return

    user_message = event.message.text.strip()
    user_id = event.source.user_id  # 獲取使用者 ID

    # 控制 AI 啟動與關閉
    if user_message == "啟動":
        working_status = True
        reply_text = "我是時下流行的 AI 智能，目前可以為您服務囉，歡迎來跟我互動~"
    elif user_message == "安靜":
        working_status = False
        reply_text = "感謝您的使用，若需要我的服務，請跟我說 「啟動」 謝謝~"
    elif working_status:
        reply_text = get_ai_response(user_id, user_message)  # 讓 AI 記住使用者對話
    else:
        return

    # 傳送回應
    send_line_reply(event.reply_token, reply_text)

def get_ai_response(user_id, user_message):
    """使用新版 OpenAI API 取得 AI 回應（支援固定提示詞 + 上下文）"""
    try:
        client = openai.OpenAI()  # 創建 OpenAI 客戶端
        
        # 檢查使用者是否已經有對話紀錄
        if user_id not in user_sessions:
            user_sessions[user_id] = [{"role": "system", "content": system_prompt}]

        # 記錄當前對話
        user_sessions[user_id].append({"role": "user", "content": user_message})

        # 保持上下文最多 10 條對話（不含 system prompt）
        user_sessions[user_id] = [user_sessions[user_id][0]] + user_sessions[user_id][-10:]

        # 呼叫 OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=user_sessions[user_id]
        )
        
        ai_reply = response.choices[0].message.content.strip()
        
        # 記錄 AI 回應
        user_sessions[user_id].append({"role": "assistant", "content": ai_reply})
        print(f"🤖 AI 回應: {ai_reply}")  # 記錄 AI 回應
        return ai_reply
    except openai.OpenAIError as e:
        print(f"❌ OpenAI API 發生錯誤: {str(e)}")
        return f"OpenAI API 錯誤: {str(e)}"
    except Exception as e:
        print(f"❌ 未知錯誤: {str(e)}")
        return f"未知錯誤: {str(e)}"

def send_line_reply(reply_token, text):
    """發送訊息到 LINE"""
    try:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=text))
        print(f"📩 發送回應成功: {text}")
    except Exception as e:
        print(f"⚠️ LINE API 發送錯誤: {str(e)}")

if __name__ == "__main__":
    app.run()
