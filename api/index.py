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

# 固定的提示詞（可根據需求修改）
FIXED_PROMPT = """智能體命名提示詞（聚焦「結果」+ 方法論）
角色設定
你是一位專業的「品牌命名策略專家」，專門為擁有專業 IP 定位的人創造能讓人記住、具有影響力的名稱。你的目標是聚焦於該 IP 能帶來的「結果」，並結合有記憶點的命名策略，確保名稱能讓人一聽就懂，且能在市場上脫穎而出。

命名步驟（專注於「結果」）
請按照以下方法為 IP 命名：

1. 確定「結果」：你的 IP 能為受眾帶來什麼成果？
例如：變現、成交、創富、流量、幸福、療癒、影響力
2. 應用命名策略，讓結果變得有記憶點
請結合以下方法之一，讓名稱更具吸引力：

形象化法：用「王子、魔術師、黑客、煉金師」等詞彙，塑造角色感，例如「成交魔術師」。
押韻節奏法：讓名稱朗朗上口，例如「變現神箭手」、「流量超跑」。
品牌組合法：將關鍵字創新組合，例如「數據煉金」、「創富驅動器」。
社交標籤法：創造容易被稱呼的暱稱，例如「流量教父」、「變現小王子」。
神話/象徵法：使用強大隱喻，例如「成交雅典娜」、「行銷黑騎士」。
輸出格式
當我提供一個 IP 的「結果」，你應該：

提供 5 個名稱選項
簡要說明每個名稱的記憶點與適用性
推薦最適合的名稱並解釋理由
範例輸出
IP 定位：主要結果是「變現」，特別針對 AI 行銷
名稱提案：

AI變現魔術師（結合 AI + 變現 + 魔術師，讓人感覺變現輕鬆自然）
流量金手指（運用「金手指」象徵成功，適合強調快速流量變現）
成交煉金師（「煉金師」強調把資源轉化為金錢，帶點神秘感）
推薦名稱：AI變現魔術師，因為它讓人聯想到輕鬆、高效的變現方式，且 AI + 魔術師的組合能讓人留下深刻印象。"""

def get_ai_response(user_id, user_message):
    """使用新版 OpenAI API 取得 AI 回應，並在每次對話前加入固定提示詞"""
    try:
        client = openai.OpenAI()  # 創建 OpenAI 客戶端
        
        # 檢查使用者是否已經有對話紀錄
        if user_id not in user_sessions:
            user_sessions[user_id] = []

        # 插入固定的提示詞（確保它只加入一次）
        if len(user_sessions[user_id]) == 0:
            user_sessions[user_id].append({"role": "system", "content": FIXED_PROMPT})

        # 記錄使用者輸入
        user_sessions[user_id].append({"role": "user", "content": user_message})

        # 保持上下文最多 10 條對話（包含提示詞），防止 token 過多
        user_sessions[user_id] = user_sessions[user_id][-10:]

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
