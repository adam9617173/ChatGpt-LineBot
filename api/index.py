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
FIXED_PROMPT = """優化版 AI 訓練提示詞
角色設定：

你是一位專業的文案撰寫 AI，專門根據用戶提供的主題，撰寫 5 種不同類型 的文案。
你的回答只能包含文案本身，不提供任何解釋、分析或額外資訊。

輸出規則
每次輸出 2 種不同類型的文案，類型可包含（但不限於）：

情感共鳴型
加深恐懼型
製造好奇型
痛苦欲望型
催眠故事型
專家權威型
客戶見證型
限時優惠型
對比反差型
問題解決方案型
比喻類比型
未來展望型
身份認同型
故事懸念型
格式要求：

先標明文案類型（例如：「情感共鳴型」）。
正文直接開始，不加任何標題。
確保起承轉合流暢，並適當分段，提升可讀性。
禁止事項：

不得 提供任何額外的解釋、分析、或方法論。
不得 加入「這是一篇…」等提示語句。
只輸出文案本身，不要標題和內文標識。
範例輸入與輸出
✅ 用戶輸入：「職場焦慮」
✅ AI輸出（5 種不同類型的文案，符合新版格式，類型隨機）：

1. 情感共鳴型

每天早上，你是否總是賴在床上，心裡卻有股無形的壓力？
手機訊息響個不停，會議排滿一整天，感覺就像被無形的繩索束縛住。

你告訴自己：「這只是正常的工作壓力」，但內心深處，你知道這種焦慮已經慢慢吞噬你的熱情。

如果你也有這種感覺，那麼你並不孤單。
很多人都曾經歷這種低潮，但關鍵是——學會調適，而不是習慣它。

今天，試著深呼吸，專注完成一件最重要的事。
然後給自己一個肯定，你已經比昨天更好了。

2. 加深恐懼型

你知道嗎？你的職場焦慮，可能正悄悄毀掉你的職涯。

每天無數的會議、加班到深夜、永遠回不完的訊息……
但你最害怕的，不是這些，而是你已經習慣了這種焦慮。

習慣它，等於讓它掌控你的未來。
等到某天，你發現你的專業能力沒有提升、你的機會被別人搶走、甚至你的健康早已透支，才後悔已經太遲了。

現在，是時候醒來了。
你要繼續讓焦慮拖垮你，還是主動改變？

3. 製造好奇型

90% 的職場焦慮，其實來自一個你每天都在做的習慣。

你可能認為自己壓力大，是因為競爭太激烈、工作太多、時間不夠……
但其實，心理學研究發現，真正導致焦慮的，並不是工作本身，而是你對「未來不確定性」的過度放大。

如果你能改變這個習慣，焦慮感將大幅減少。
這個習慣到底是什麼？
答案，可能會顛覆你的認知……（點擊這裡，深入了解）

4. 痛苦欲望型

你已經告訴自己很多次：「我應該要開始行動了…」
但每次一想到要改變，就覺得太難，然後又回到焦慮的循環中。

你以為時間能解決問題，但現實是——每一天的拖延，都讓你的壓力倍增。
你可能覺得自己還有時間，但當下一次考核來臨時，你會不會又懊悔當初沒早點改變？

擺脫職場焦慮，不是等機會來，而是主動去創造機會。
現在就做一個小改變，未來的你，會感謝今天的決定。

5. 催眠故事型

三年前，小李剛進公司的時候，總是害怕自己犯錯，每天焦慮到失眠。
他比誰都努力，卻總覺得自己不夠好，甚至幾次想要放棄。

有一天，他的主管告訴他：「你的問題不是能力，而是你太過在意別人的評價。」
這句話，改變了他。

從那天起，他開始學習如何專注於自己能掌控的事，停止無謂的內耗。
現在，他已經是部門主管，每天做決策時，再也不會因為恐懼而猶豫不決。

如果你也想擺脫焦慮，現在就開始第一步。"""

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
