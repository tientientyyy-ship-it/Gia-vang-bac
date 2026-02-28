import os
import requests
import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
import signal
import sys

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID', '-1001234567890')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class CryptoPriceBot:
    def __init__(self):
        if not TELEGRAM_TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN missing!")
            sys.exit(1)
            
        self.app = Application.builder().token(TELEGRAM_TOKEN).build()
        self.is_running = True
        self.setup_handlers()
        signal.signal(signal.SIGTERM, self.stop)
    
    def get_crypto_prices(self):
        """Lấy giá crypto từ CoinGecko"""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': 'bitcoin,ethereum,binancecoin',
                'vs_currencies': 'usd,vnd',
                'include_24hr_change': 'true',
                'include_24hr_vol': 'true'
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                'BTC': {
                    'usd': data['bitcoin']['usd'],
                    'vnd': data['bitcoin']['vnd'],
                    'change': data['bitcoin']['usd_24h_change'],
                    'vol': data['bitcoin']['usd_24h_vol']
                },
                'ETH': {
                    'usd': data['ethereum']['usd'],
                    'vnd': data['ethereum']['vnd'],
                    'change': data['ethereum']['usd_24h_change']
                },
                'BNB': {
                    'usd': data['binancecoin']['usd'],
                    'vnd': data['binancecoin']['vnd'],
                    'change': data['binancecoin']['usd_24h_change']
                }
            }
        except Exception as e:
            logger.error(f"Crypto API error: {e}")
            return None
    
    def get_metal_prices(self):
        """Giá Vàng Bạc - Multiple sources"""
        try:
            metals = {}
            
            # Vàng SJC
            try:
                sjc_resp = requests.get("https://gjapi.apis.gjlab.vn/gold-price", timeout=10)
                sjc_resp.raise_for_status()
                sjc = sjc_resp.json()
                metals['SJC_BUY'] = sjc['data']['sjc_buy']
                metals['SJC_SELL'] = sjc['data']['sjc_sell']
            except:
                metals['SJC_BUY'] = 0
                metals['SJC_SELL'] = 0
            
            # Gold & Silver thế giới
            try:
                metals_resp = requests.get("https://api.metals.live/v1/spot/XAU,XAG", timeout=10)
                metals_resp.raise_for_status()
                metals_data = metals_resp.json()['data']
                metals['XAU'] = metals_data['XAU']['price']
                metals['XAG'] = metals_data['XAG']['price']
            except:
                metals['XAU'] = 0
                metals['XAG'] = 0
            
            return metals
        except Exception as e:
            logger.error(f"Metals API error: {e}")
            return {}
    
    def create_main_menu(self, crypto, metals):
        """Tạo main menu với buttons đẹp"""
        keyboard = []
        
        # Row 1: Crypto
        crypto_row = []
        if crypto:
            crypto_row.append(InlineKeyboardButton(
                f"🟠 BTC ${crypto['BTC']['usd']:,.0f}", 
                callback_data='detail_BTC'
            ))
            crypto_row.append(InlineKeyboardButton(
                f"🔷 ETH ${crypto['ETH']['usd']:,.0f}", 
                callback_data='detail_ETH'
            ))
        keyboard.append(crypto_row)
        
        # Row 2: BNB + Vàng SJC
        row2 = []
        if crypto:
            row2.append(InlineKeyboardButton(
                f"🟡 BNB ${crypto['BNB']['usd']:,.0f}", 
                callback_data='detail_BNB'
            ))
        row2.append(InlineKeyboardButton("🥇 SJC", callback_data='detail_SJC'))
        keyboard.append(row2)
        
        # Row 3: Gold & Silver thế giới
        metals_row = [
            InlineKeyboardButton("👑 XAU", callback_data='detail_XAU'),
            InlineKeyboardButton("🥈 XAG", callback_data='detail_XAG')
        ]
        keyboard.append(metals_row)
        
        # Row 4: Refresh & Status
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data='refresh'),
            InlineKeyboardButton("ℹ️ Status", callback_data='status')
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def format_main_message(self, crypto, metals):
        """Message chính gọn gàng"""
        timestamp = datetime.now().strftime('%H:%M %d/%m')
        msg = f"💰 **THỊ TRƯỜNG {timestamp}** 💰\n\n"
        
        if crypto:
            msg += f"🟠 `BTC`  ${crypto['BTC']['usd']:>8,.0f}\n"
            msg += f"🔷 `ETH`  ${crypto['ETH']['usd']:>8,.0f}\n"
            msg += f"🟡 `BNB`  ${crypto['BNB']['usd']:>8,.0f}\n\n"
        else:
            msg += "📈 CRYPTO ❌\n\n"
        
        if metals.get('SJC_BUY'):
            msg += f"🥇 `SJC`   {metals['SJC_BUY']:>8,.0f}đ\n\n"
        
        if metals.get('XAU'):
            msg += f"👑 `XAU`   ${metals['XAU']:>7,.1f}\n"
            msg += f"🥈 `XAG`   ${metals['XAG']:>7,.2f}\n"
        
        msg += f"\n👇 **Bấm button để xem chi tiết**"
        return msg
    
    def format_detail_message(self, crypto, metals, item):
        """Chi tiết từng item"""
        if item.startswith('detail_'):
            key = item.split('_')[1]
            
            if key == 'BTC' and crypto:
                data = crypto['BTC']
                change_emoji = "🟢" if data['change'] > 0 else "🔴"
                return f"""🟠 **BITCOIN (BTC)** 🟠

💵 **USD**:  ${data['usd']:,.2f}
🇻🇳 **VND**: {data['vnd']:,.0f}đ
📊 **24h**: {change_emoji} {data['change']:+.2f}%
🔄 **Cập nhật**: {datetime.now().strftime('%H:%M:%S')}

👆 Bấm **MAIN MENU** để về"""
            
            elif key == 'ETH' and crypto:
                data = crypto['ETH']
                change_emoji = "🟢" if data['change'] > 0 else "🔴"
                return f"""🔷 **ETHEREUM (ETH)** 🔷

💵 **USD**:  ${data['usd']:,.2f}
🇻🇳 **VND**: {data['vnd']:,.0f}đ
📊 **24h**: {change_emoji} {data['change']:+.2f}%
🔄 **Cập nhật**: {datetime.now().strftime('%H:%M:%S')}

👆 Bấm **MAIN MENU** để về"""
            
            elif key == 'BNB' and crypto:
                data = crypto['BNB']
                change_emoji = "🟢" if data['change'] > 0 else "🔴"
                return f"""🟡 **BINANCE COIN (BNB)** 🟡

💵 **USD**:  ${data['usd']:,.2f}
🇻🇳 **VND**: {data['vnd']:,.0f}đ
📊 **24h**: {change_emoji} {data['change']:+.2f}%
🔄 **Cập nhật**: {datetime.now().strftime('%H:%M:%S')}

👆 Bấm **MAIN MENU** để về"""
            
            elif key == 'SJC' and metals:
                return f"""🥇 **VÀNG SJC** 🥇

💰 **MUA**:  {metals['SJC_BUY']:,.0f}đ
💎 **BÁN**:  {metals['SJC_SELL']:,.0f}đ
🇻🇳 **Chênh lệch**: {metals['SJC_SELL'] - metals['SJC_BUY']:,.0f}đ
🔄 **Cập nhật**: {datetime.now().strftime('%H:%M:%S')}

👆 Bấm **MAIN MENU** để về"""
            
            elif key == 'XAU' and metals:
                return f"""👑 **GOLD (XAU/USD)** 👑

💵 **Giá**:  ${metals['XAU']:,.2f}
🌍 **Spot price**
🔄 **Cập nhật**: {datetime.now().strftime('%H:%M:%S')}

👆 Bấm **MAIN MENU** để về"""
            
            elif key == 'XAG' and metals:
                return f"""🥈 **SILVER (XAG/USD)** 🥈

💵 **Giá**:  ${metals['XAG']:,.3f}
🌍 **Spot price**
🔄 **Cập nhật**: {datetime.now().strftime('%H:%M:%S')}

👆 Bấm **MAIN MENU** để về"""
        
        return "❌ Lỗi dữ liệu!"
    
    def create_back_keyboard(self):
        """Keyboard quay lại main menu"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 MAIN MENU", callback_data='main_menu')],
            [InlineKeyboardButton("🔄 Refresh", callback_data='refresh')]
        ])
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        crypto = self.get_crypto_prices()
        metals = self.get_metal_prices()
        msg = self.format_main_message(crypto, metals)
        keyboard = self.create_main_menu(crypto, metals)
        
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=keyboard)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        crypto = self.get_crypto_prices()
        metals = self.get_metal_prices()
        
        if query.data == 'refresh' or query.data == 'main_menu':
            msg = self.format_main_message(crypto, metals)
            keyboard = self.create_main_menu(crypto, metals)
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=keyboard)
        
        elif query.data == 'status':
            uptime = datetime.now().strftime('%d/%m %H:%M:%S')
            status_msg = f"""✅ **BOT STATUS**
🟢 **Trạng thái**: ONLINE
🕐 **Uptime**: {uptime}
📡 **Auto**: 1h/lần
👥 **Chat**: `{CHAT_ID}`"""
            await query.edit_message_text(status_msg, parse_mode='Markdown', reply_markup=self.create_back_keyboard())
        
        else:  # Detail view
            detail_msg = self.format_detail_message(crypto, metals, query.data)
            await query.edit_message_text(detail_msg, parse_mode='Markdown', reply_markup=self.create_back_keyboard())
    
    async def price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        crypto = self.get_crypto_prices()
        metals = self.get_metal_prices()
        msg = self.format_main_message(crypto, metals)
        keyboard = self.create_main_menu(crypto, metals)
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=keyboard)
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        uptime = datetime.now().strftime('%d/%m %H:%M:%S')
        await update.message.reply_text(
            f"""✅ **BOT STATUS**
🟢 **Trạng thái**: ONLINE
🕐 **Uptime**: `{uptime}`
📡 **Auto**: 1h/lần
👥 **Chat**: `{CHAT_ID}`""",
            parse_mode='Markdown'
        )
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("price", self.price))
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def auto_update(self):
        """Auto update mỗi 1h"""
        while self.is_running:
            try:
                if CHAT_ID:
                    crypto = self.get_crypto_prices()
                    metals = self.get_metal_prices()
                    msg = self.format_main_message(crypto, metals)
                    keyboard = self.create_main_menu(crypto, metals)
                    await self.app.bot.send_photo(
                        chat_id=CHAT_ID,
                        photo="https://i.imgur.com/crypto_chart.jpg",  # Thay bằng ảnh chart đẹp
                        caption=msg,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                    logger.info("✅ Auto update with menu sent!")
                await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"❌ Auto update failed: {e}")
                await asyncio.sleep(3600)
    
    def stop(self, signum=None, frame=None):
        self.is_running = False
    
    async def run(self):
        logger.info("🤖 Starting Advanced Crypto Bot...")
        asyncio.create_task(self.auto_update())
        
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        
        try:
            while self.is_running:
                await asyncio.sleep(1)
        finally:
            await self.app.stop()
            await self.app.shutdown()

if __name__ == "__main__":
    asyncio.run(CryptoPriceBot().run())
