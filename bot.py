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

class PerfectPriceBot:
    def __init__(self):
        self.app = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()
    
    def get_crypto_price(self, coin_id, coin_name):
        """Giá BTC/ETH/BNB: USD + VND"""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {'ids': coin_id, 'vs_currencies': 'usd,vnd', 'include_24hr_change': 'true'}
            data = requests.get(url, params=params, timeout=10).json()
            coin = data[coin_id]
            
            change_emoji = "🟢" if coin['usd_24h_change'] > 0 else "🔴"
            return f"""
💎 **{coin_name} ({coin_id.upper()})** 💎

💵 *USD:* `${coin['usd']:,.2f}`
🇻🇳 *VND:* `{coin['vnd']:,.0f}`đ
📈 *24h:* {change_emoji} `{coin['usd_24h_change']:+.2f}%`

🕐 *{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}*
            """
        except:
            return f"❌ Không lấy được giá {coin_name}"
    
    def get_gold_sjc(self):
        """Giá VÀNG SJC chính xác: Mua/Bán"""
        try:
            # API SJC chính xác nhất
            url = "https://sjc.com.vn/api/v1/price"
            data = requests.get(url, timeout=10).json()
            
            # Fallback API khác nếu lỗi
            if not data:
                url2 = "https://gjapi.apis.gjlab.vn/gold-price"
                data = requests.get(url2, timeout=10).json()['data']
            
            if 'sjc_buy' in data:
                return f"""
🥇 **VÀNG SJC** 🥇

💰 *GIÁ MUA VÀO:* `{data['sjc_buy']:,.0f}`đ
💎 *GIÁ BÁN RA:* `{data['sjc_sell']:,.0f}`đ
📊 *CHÊ NHÁU:* `{data['sjc_sell'] - data['sjc_buy']:,.0f}`đ

🏪 *TIỆM VÀNG SJC*
🕐 *{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}*
            """
            else:
                # Fallback format
                return f"""
🥇 **VÀNG SJC** 🥇

💰 *MUA VÀO:* `{data['sjc_buy']:,.0f}`đ
💎 *BÁN RA:* `{data['sjc_sell']:,.0f}`đ

🕐 *{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}*
                """
        except Exception as e:
            logger.error(f"Gold error: {e}")
            return "❌ Lỗi lấy giá SJC\n\n*Thử lại sau 1 phút*"
    
    def get_silver_price(self):
        """Giá BẠC quốc tế + VN (nếu có)"""
        try:
            # Bạc quốc tế
            xag = requests.get("https://api.metals.live/v1/spot/XAG", timeout=10).json()['data']['XAG']
            
            # Bạc SJC (nếu có API)
            silver_vn = "Chưa có giá SJC"  # Thường không public
            
            return f"""
🥈 **BẠC XAG** 🥈

💵 *USD:* `${xag['price']:,.2f}`
🇻🇳 *VND:* `{xag['price'] * 25000:,.0f}`đ (ước tính)

🏪 *Thị trường quốc tế*
🕐 *{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}*
            """
        except:
            return "❌ Lỗi lấy giá bạc quốc tế"
    
    def create_main_menu(self):
        keyboard = [
            [InlineKeyboardButton("🧡 BTC", callback_data="btc")],
            [InlineKeyboardButton("🔷 ETH", callback_data="eth"), InlineKeyboardButton("⚡ BNB", callback_data="bnb")],
            [InlineKeyboardButton("🥇 Vàng SJC", callback_data="gold"), InlineKeyboardButton("🥈 Bạc", callback_data="silver")],
            [InlineKeyboardButton("📊 Tất cả", callback_data="all")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = "🌟 **CHÀO MỪNG! CHỌN GIÁ CẦN XEM** 🌟\n\n👇 *Nhấn nút bên dưới*"
        await update.message.reply_text(msg, reply_markup=self.create_main_menu(), parse_mode='Markdown')
    
    async def price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = "💰 **CHỌN LOẠI GIÁ** 💰\n\n👇 *Nhấn nút*"
        await update.message.reply_text(msg, reply_markup=self.create_main_menu(), parse_mode='Markdown')
    
    async def text_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý khi user gõ text: 'vàng', 'btc', etc."""
        text = update.message.text.lower()
        
        if 'vàng' in text or 'sjc' in text:
            msg = self.get_gold_sjc()
            await update.message.reply_text(msg, parse_mode='Markdown')
        elif 'bạc' in text:
            msg = self.get_silver_price()
            await update.message.reply_text(msg, parse_mode='Markdown')
        elif 'btc' in text or 'bitcoin' in text:
            msg = self.get_crypto_price('bitcoin', 'Bitcoin')
            await update.message.reply_text(msg, parse_mode='Markdown')
        elif 'eth' in text or 'ethereum' in text:
            msg = self.get_crypto_price('ethereum', 'Ethereum')
            await update.message.reply_text(msg, parse_mode='Markdown')
        elif 'bnb' in text:
            msg = self.get_crypto_price('binancecoin', 'BNB')
            await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            await update.message.reply_text("❓ *Không hiểu lệnh*\n\nGõ: `vàng`, `btc`, `eth`, `bnb`, `bạc`", parse_mode='Markdown')
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == "main":
            msg = "🌟 **MENU GIÁ** 🌟\n\n👇 *Chọn loại tài sản*"
            await query.edit_message_text(msg, reply_markup=self.create_main_menu(), parse_mode='Markdown')
        
        elif query.data == "btc":
            msg = self.get_crypto_price('bitcoin', 'Bitcoin')
            await query.edit_message_text(msg, reply_markup=self.create_main_menu(), parse_mode='Markdown')
        
        elif query.data == "eth":
            msg = self.get_crypto_price('ethereum', 'Ethereum')
            await query.edit_message_text(msg, reply_markup=self.create_main_menu(), parse_mode='Markdown')
        
        elif query.data == "bnb":
            msg = self.get_crypto_price('binancecoin', 'BNB')
            await query.edit_message_text(msg, reply_markup=self.create_main_menu(), parse_mode='Markdown')
        
        elif query.data == "gold":
            msg = self.get_gold_sjc()
            await query.edit_message_text(msg, reply_markup=self.create_main_menu(), parse_mode='Markdown')
        
        elif query.data == "silver":
            msg = self.get_silver_price()
            await query.edit_message_text(msg, reply_markup=self.create_main_menu(), parse_mode='Markdown')
        
        elif query.data == "all":
            msg = """
📊 **TỔNG HỢP TOP ASSETS**

🥇 Vàng SJC - Nhấn Vàng SJC
🧡 BTC/USD - Nhấn BTC
🔷 ETH/USD - Nhấn ETH  
⚡ BNB/USD - Nhấn BNB
🥈 Bạc XAG - Nhấn Bạc

👆 *Nhấn nút để xem chi tiết realtime!*
            """
            await query.edit_message_text(msg, reply_markup=self.create_main_menu(), parse_mode='Markdown')
    
    async def post_init(self, app: Application) -> None:
        """Menu button cạnh ô chat"""
        await app.bot.set_chat_menu_button(
            menu_button=telegram.MenuButtonCommands([
                '/start - 🌟 Menu chính',
                '/price - 💰 Xem giá',
                '/gold - 🥇 Vàng SJC'
            ])
        )
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("price", self.price))
        self.app.add_handler(CommandHandler("gold", lambda u,c: asyncio.create_task(u.message.reply_text(self.get_gold_sjc(), parse_mode='Markdown'))))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_handler))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))
        self.app.post_init = self.post_init
    
    async def run(self):
        await self.post_init(self.app)
        await self.app.run_polling(drop_pending_updates=True)
        logger.info("🤖 Perfect Price Bot 24/7 running!")

async def main():
    bot = PerfectPriceBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
