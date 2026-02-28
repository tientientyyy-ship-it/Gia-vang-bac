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
import json

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
                'include_24hr_change': 'true'
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                'BTC': {
                    'usd': data['bitcoin']['usd'],
                    'vnd': data['bitcoin']['vnd'],
                    'change': data['bitcoin']['usd_24h_change']
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
    
    def get_sjc_prices(self):
        """3 APIs backup cho SJC - Ưu tiên API ngon nhất"""
        apis = [
            # API 1: Giá vàng chính thức
            {
                'url': 'https://api.giavatap.com/v3/sjc',
                'key_buy': 'buy',
                'key_sell': 'sell'
            },
            # API 2: Backup 1
            {
                'url': 'https://goldpricez.com/api/sjc',
                'key_buy': 'sjc_buy',
                'key_sell': 'sjc_sell'
            },
            # API 3: PNJ + backup
            {
                'url': 'https://sjc.com.vn/webservice/sjcprice.php',
                'key_buy': 'buy',
                'key_sell': 'sell'
            }
        ]
        
        for api in apis:
            try:
                logger.info(f"Trying SJC API: {api['url']}")
                response = requests.get(api['url'], timeout=8)
                response.raise_for_status()
                data = response.json()
                
                buy = float(data.get(api['key_buy'], 0))
                sell = float(data.get(api['key_sell'], 0))
                
                if buy > 50000000 and sell > 50000000:  # Validate giá hợp lý
                    logger.info(f"✅ SJC from {api['url']}: Buy {buy:,.0f}, Sell {sell:,.0f}")
                    return {
                        'SJC_BUY': buy,
                        'SJC_SELL': sell,
                        'source': api['url']
                    }
            except Exception as e:
                logger.warning(f"SJC API {api['url']} failed: {e}")
                continue
        
        logger.error("❌ All SJC APIs failed")
        return {'SJC_BUY': 0, 'SJC_SELL': 0}
    
    def get_world_metals(self):
        """Gold & Silver thế giới"""
        try:
            response = requests.get("https://api.metals.live/v1/spot/XAU,XAG", timeout=10)
            response.raise_for_status()
            data = response.json()['data']
            return {
                'XAU': data['XAU']['price'],
                'XAG': data['XAG']['price']
            }
        except:
            return {'XAU': 0, 'XAG': 0}
    
    def get_metal_prices(self):
        """Combine tất cả metals"""
        sjc = self.get_sjc_prices()
        world = self.get_world_metals()
        return {**sjc, **world}
    
    def create_main_menu(self, crypto, metals):
        """Main menu với giá real-time trên button"""
        keyboard = []
        
        # Crypto row
        if crypto:
            keyboard.append([
                InlineKeyboardButton(
                    f"🟠 BTC ${crypto['BTC']['usd']:,.0f}", 
                    callback_data='detail_BTC'
                ),
                InlineKeyboardButton(
                    f"🔷 ETH ${crypto['ETH']['usd']:,.0f}", 
                    callback_data='detail_ETH'
                )
            ])
            keyboard.append([
                InlineKeyboardButton(
                    f"🟡 BNB ${crypto['BNB']['usd']:,.0f}", 
                    callback_data='detail_BNB'
                )
            ])
        
        # SJC row - Luôn hiện
        sjc_price = f"{metals.get('SJC_BUY', 0):,.0f}đ" if metals.get('SJC_BUY') else "❌"
        keyboard.append([InlineKeyboardButton(f"🥇 SJC {sjc_price}", callback_data='detail_SJC')])
        
        # World metals
        keyboard.append([
            InlineKeyboardButton(f"👑 XAU ${metals.get('XAU', 0):,.0f}", callback_data='detail_XAU'),
            InlineKeyboardButton(f"🥈 XAG ${metals.get('XAG', 0):,.2f}", callback_data='detail_XAG')
        ])
        
        # Control row
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data='refresh'),
            InlineKeyboardButton("ℹ️ Status", callback_data='status')
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def format_main_message(self, crypto, metals):
        """Message chính"""
        timestamp = datetime.now().strftime('%H:%M %d/%m')
        msg = f"💰 **THỊ TRƯỜNG {timestamp}** 💰\n\n"
        
        # Crypto
        if crypto:
            change_btc = "🟢" if crypto['BTC']['change'] > 0 else "🔴"
            msg += f"🟠 `BTC`  ${crypto['BTC']['usd']:>8,.0f} {change_btc}\n"
            msg += f"🔷 `ETH`  ${crypto['ETH']['usd']:>8,.0f}\n"
            msg += f"🟡 `BNB`  ${crypto['BNB']['usd']:>8,.0f}\n\n"
        else:
            msg += "📈 `CRYPTO` ❌ Lỗi\n\n"
        
        # SJC
        if metals.get('SJC_BUY', 0) > 50000000:
            msg += f"🥇 `SJC`   {metals['SJC_BUY']:>9,.0f}đ\n\n"
        else:
            msg += "🥇 `SJC`   ❌ Lỗi API\n\n"
        
        # World metals
        if metals.get('XAU', 0) > 1000:
            msg += f"👑 `XAU`   ${metals['XAU']:>7,.1f}\n"
            msg += f"🥈 `XAG`   ${metals['XAG']:>7,.2f}\n"
        
        msg += f"\n👇 **Bấm để xem USD/VND chi tiết**"
        return msg
    
    def format_detail_message(self, crypto, metals, item):
        """Chi tiết từng asset"""
        key = item.split('_')[1]
        
        if key == 'SJC' and metals.get('SJC_BUY', 0) > 50000000:
            diff = metals['SJC_SELL'] - metals['SJC_BUY']
            return f"""🥇 **VÀNG SJC** 🥇

💰 **GIÁ MUA**:  {metals['SJC_BUY']:,.0f}đ
💎 **GIÁ BÁN**: {metals['SJC_SELL']:,.0f}đ
🔺 **CHÊNH LỆCH**: {diff:,.0f}đ (+{diff/metals['SJC_BUY']*100:.1f}%)
📡 **Nguồn**: SJC Live
🔄 **{datetime.now().strftime('%H:%M:%S')}**

👆 **MAIN MENU**"""
        
        elif key == 'BTC' and crypto:
            data = crypto['BTC']
            change_emoji = "🟢" if data['change'] > 0 else "🔴"
            return f"""🟠 **BITCOIN (BTC)** 🟠

💵 **USD**:     ${data['usd']:,.2f}
🇻🇳 **VND**:  {data['vnd']:,.0f}đ
📊 **24h**:   {change_emoji} {data['change']:+.2f}%
🔄 **{datetime.now().strftime('%H:%M:%S')}**

👆 **MAIN MENU**"""
        
        elif key == 'ETH' and crypto:
            data = crypto['ETH']
            change_emoji = "🟢" if data['change'] > 0 else "🔴"
            return f"""🔷 **ETHEREUM (ETH)** 🔷

💵 **USD**:     ${data['usd']:,.2f}
🇻🇳 **VND**:  {data['vnd']:,.0f}đ
📊 **24h**:   {change_emoji} {data['change']:+.2f}%
🔄 **{datetime.now().strftime('%H:%M:%S')}**

👆 **MAIN MENU**"""
        
        elif key == 'BNB' and crypto:
            data = crypto['BNB']
            change_emoji = "🟢" if data['change'] > 0 else "🔴"
            return f"""🟡 **BNB (BNB)** 🟡

💵 **USD**:     ${data['usd']:,.2f}
🇻🇳 **VND**:  {data['vnd']:,.0f}đ
📊 **24h**:   {change_emoji} {data['change']:+.2f}%
🔄 **{datetime.now().strftime('%H:%M:%S')}**

👆 **MAIN MENU**"""
        
        elif key == 'XAU' and metals.get('XAU', 0) > 1000:
            return f"""👑 **GOLD SPOT (XAU/USD)** 👑

💵 **GIÁ**:  ${metals['XAU']:,.2f}
🌍 **World Spot**
🔄 **{datetime.now().strftime('%H:%M:%S')}**

👆 **MAIN MENU**"""
        
        elif key == 'XAG' and metals.get('XAG', 0) > 10:
            return f"""🥈 **SILVER SPOT (XAG/USD)** 🥈

💵 **GIÁ**:  ${metals['XAG']:,.3f}
🌍 **World Spot**
🔄 **{datetime.now().strftime('%H:%M:%S')}**

👆 **MAIN MENU**"""
        
        return f"❌ **Lỗi dữ liệu {key}**\n🔄 Thử **Refresh**"
    
    def create_back_keyboard(self):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 MAIN MENU", callback_data='main_menu')],
            [InlineKeyboardButton("🔄 Refresh", callback_data='refresh')]
        ])
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.show_main_menu(update.message)
    
    async def show_main_menu(self, message_or_query):
        crypto = self.get_crypto_prices()
        metals = self.get_metal_prices()
        msg = self.format_main_message(crypto, metals)
        keyboard = self.create_main_menu(crypto, metals)
        
        if hasattr(message_or_query, 'reply_text'):
            await message_or_query.reply_text(msg, parse_mode='Markdown', reply_markup=keyboard)
        else:
            await message_or_query.edit_message_text(msg, parse_mode='Markdown', reply_markup=keyboard)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        crypto = self.get_crypto_prices()
        metals = self.get_metal_prices()
        
        if query.data in ['refresh', 'main_menu']:
            await self.show_main_menu(query)
        elif query.data == 'status':
            uptime = datetime.now().strftime('%d/%m %H:%M:%S')
            status_msg = f"""✅ **BOT STATUS**
🟢 **Status**: ONLINE
🕐 **Uptime**: {uptime}
📡 **Auto**: 1h/lần
🔄 **SJC APIs**: 3 backup"""
            await query.edit_message_text(status_msg, parse_mode='Markdown', reply_markup=self.create_back_keyboard())
        else:
            detail_msg = self.format_detail_message(crypto, metals, query.data)
            await query.edit_message_text(detail_msg, parse_mode='Markdown', reply_markup=self.create_back_keyboard())
    
    async def price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.show_main_menu(update.message)
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("price", self.price))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def auto_update(self):
        while self.is_running:
            try:
                if CHAT_ID:
                    crypto = self.get_crypto_prices()
                    metals = self.get_metal_prices()
                    msg = self.format_main_message(crypto, metals)
                    keyboard = self.create_main_menu(crypto, metals)
                    await self.app.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown', reply_markup=keyboard)
                    logger.info("✅ Auto update sent!")
            except Exception as e:
                logger.error(f"Auto update error: {e}")
            await asyncio.sleep(3600)
    
    def stop(self, signum=None, frame=None):
        self.is_running = False
    
    async def run(self):
        logger.info("🤖 Starting FIXED Bot...")
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
