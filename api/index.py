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

@app.route('/')
def home():
    return 'Hello, World!'

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
    """處理使用者訊息"""
    global working_status

    # 檢查是否為文字訊息
    if event.message.type != "text":
        return

    user_message = event.message.text.strip()

    # 控制 AI 啟動與關閉
    if user_message == "啟動":
        working_status = True
        reply_text = "我是時下流行的 AI 智能，目前可以為您服務囉，歡迎來跟我互動~"
    elif user_message == "安靜":
        working_status = False
        reply_text = "感謝您的使用，若需要我的服務，請跟我說 「啟動」 謝謝~"
    elif working_status:
        reply_text = get_ai_response(user_message)
    else:
        return

    # 傳送回應
    send_line_reply(event.reply_token, reply_text)

def get_ai_response(user_message):
    """取得 OpenAI GPT 回應"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_message}]
        )
        ai_reply = response["choices"][0]["message"]["content"].strip()
        print(f"🤖 AI 回應: {ai_reply}")  # 記錄 AI 回應
        return ai_reply
    except Exception as e:
        print(f"❌ OpenAI API 發生錯誤: {str(e)}")
        return "抱歉，我暫時無法回答你的問題。"

def send_line_reply(reply_token, text):
    """發送訊息到 LINE"""
    try:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=text))
        print(f"📩 發送回應成功: {text}")
    except Exception as e:
        print(f"⚠️ LINE API 發送錯誤: {str(e)}")

if __name__ == "__main__":
    app.run()
