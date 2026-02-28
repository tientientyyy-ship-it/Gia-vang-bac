import os
import requests
import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class StablePriceBot:
    def __init__(self):
        self.app = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()
    
    def get_crypto_price(self, coin_id, coin_name):
        """BTC/ETH/BNB: USD + VND"""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {'ids': coin_id, 'vs_currencies': 'usd,vnd', 'include_24hr_change': 'true'}
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            coin = data[coin_id]
            
            change_emoji = "🟢" if coin['usd_24h_change'] > 0 else "🔴"
            return f"""💎 **{coin_name} ({coin_id.upper()})**

💵 *USD:* `${coin['usd']:,.2f}`
🇻🇳 *VND:* `{coin['vnd']:,.0f:,}`đ
📈 *24h:* {change_emoji} `{coin['usd_24h_change']:+.2f}%`

🕐 *{datetime.now().strftime('%H:%M %d/%m/%Y')}*"""
        except Exception as e:
            logger.error(f"Crypto error {coin_id}: {e}")
            return f"❌ Lỗi lấy giá {coin_name}"
    
    def get_gold_sjc(self):
        """VÀNG SJC: Mua/Bán - 3 API backup"""
        apis = [
            "https://gjapi.apis.gjlab.vn/gold-price",
            "https://api.giavanglive.com/v1/price/sjc",
            "https://sjc.vn/webservice/SJCPrice.asmx/GetLatestPrice"
        ]
        
        for api_url in apis:
            try:
                if "gjapi" in api_url:
                    data = requests.get(api_url, timeout=10).json()['data']
                    buy = data['sjc_buy']
                    sell = data['sjc_sell']
                elif "giavanglive" in api_url:
                    data = requests.get(api_url, timeout=10).json()
                    buy = data['buy']
                    sell = data['sell']
                else:
                    continue  # Skip
                
                diff = sell - buy
                return f"""🥇 **VÀNG SJC**

💰 *MUA VÀO:* `{buy:,.0f}`đ
💎 *BÁN RA:* `{sell:,.0f}`đ  
📊 *CHÊNH:* `{diff:,.0f}`đ (+{diff/buy*100:.1f}%)

🏪 *Cập nhật realtime*
🕐 *{datetime.now().strftime('%H:%M %d/%m/%Y')}*"""
            except:
                continue
        
        return """🥇 **VÀNG SJC** (OFFLINE)

💰 MUA VÀO: Đang cập nhật...
💎 BÁN RA: Đang cập nhật...

🔄 Thử lại sau 1 phút"""
    
    def get_silver_price(self):
        """BẠC XAG"""
        try:
            url = "https://api.metals.live/v1/spot/XAG"
            data = requests.get(url, timeout=10).json()['data']['XAG']
            vnd = data['price'] * 25000
            return f"""🥈 **BẠC XAG**

💵 *USD:* `${data['price']:,.2f}`
🇻🇳 *VND:* `{vnd:,.0f:,}`đ (ước tính)

🌍 *Thị trường quốc tế*
🕐 *{datetime.now().strftime('%H:%M %d/%m/%Y')}*"""
        except:
            return """🥈 **BẠC XAG** (OFFLINE)

💵 USD: Đang cập nhật...
🇻🇳 VND: Đang cập nhật..."""
    
    def create_menu(self):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🧡 BTC", callback_data="btc")],
            [InlineKeyboardButton("🔷 ETH", callback_data="eth"), InlineKeyboardButton("⚡ BNB", callback_data="bnb")],
            [InlineKeyboardButton("🥇 Vàng SJC", callback_data="gold"), InlineKeyboardButton("🥈 Bạc", callback_data="silver")],
            [InlineKeyboardButton("📊 Tất cả", callback_data="all"), InlineKeyboardButton("🔄 Làm mới", callback_data="main")]
        ])
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🌟 **GIÁ VÀNG SJC + CRYPTO** 🌟\n\n👇 *Chọn loại giá cần xem*",
            reply_markup=self.create_menu(),
            parse_mode='Markdown'
        )
    
    async def price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "💰 **CHỌN GIÁ** 💰\n\n👇 *Nhấn nút*",
            reply_markup=self.create_menu(),
            parse_mode='Markdown'
        )
    
    async def text_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.lower()
        if 'vàng' in text or 'sjc' in text:
            await update.message.reply_text(self.get_gold_sjc(), parse_mode='Markdown')
        elif 'bạc' in text:
            await update.message.reply_text(self.get_silver_price(), parse_mode='Markdown')
        elif 'btc' in text:
            await update.message.reply_text(self.get_crypto_price('bitcoin', 'Bitcoin'), parse_mode='Markdown')
        elif 'eth' in text:
            await update.message.reply_text(self.get_crypto_price('ethereum', 'Ethereum'), parse_mode='Markdown')
        elif 'bnb' in text:
            await update.message.reply_text(self.get_crypto_price('binancecoin', 'BNB'), parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "🔍 **TÌM KIẾM GIÁ**\n\n"
                "`vàng` `sjc` → Vàng SJC\n"
                "`btc` → Bitcoin\n"
                "`eth` → Ethereum\n"
                "`bnb` → BNB\n"
                "`bạc` → Silver\n\n"
                "Hoặc nhấn nút 👇",
                reply_markup=self.create_menu(),
                parse_mode='Markdown'
            )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        if data == "main" or data == "all":
            msg = "📊 **MENU GIÁ** 📊\n\n👇 *Chọn tài sản*"
            await query.edit_message_text(msg, reply_markup=self.create_menu(), parse_mode='Markdown')
        elif data == "btc":
            await query.edit_message_text(self.get_crypto_price('bitcoin', 'Bitcoin'), reply_markup=self.create_menu(), parse_mode='Markdown')
        elif data == "eth":
            await query.edit_message_text(self.get_crypto_price('ethereum', 'Ethereum'), reply_markup=self.create_menu(), parse_mode='Markdown')
        elif data == "bnb":
            await query.edit_message_text(self.get_crypto_price('binancecoin', 'BNB'), reply_markup=self.create_menu(), parse_mode='Markdown')
        elif data == "gold":
            await query.edit_message_text(self.get_gold_sjc(), reply_markup=self.create_menu(), parse_mode='Markdown')
        elif data == "silver":
            await query.edit_message_text(self.get_silver_price(), reply_markup=self.create_menu(), parse_mode='Markdown')
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("price", self.price))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_handler))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))
    
    async def run(self):
        logger.info("🤖 Starting Stable Bot...")
        await self.app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    app = StablePriceBot()
    asyncio.run(app.run())
