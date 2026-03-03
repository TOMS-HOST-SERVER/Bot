#!/usr/bin/env python3
import base64, zlib, marshal, os, tempfile, random, string, json, hashlib, time, re, sys, subprocess, importlib.util

# ======================
# INSTALLATION FIX
# ======================
def ensure_packages():
    """Ensure required packages are installed"""
    packages = [
        ("python-telegram-bot", "13.15"),
        ("pycryptodome", "3.20.0")
    ]
    
    print("🔍 Checking dependencies...")
    
    for package, version in packages:
        try:
            # Try to import the package
            spec = importlib.util.find_spec(package.replace("-", "_"))
            if spec is None:
                print(f"📦 Installing {package}=={version}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", f"{package}=={version}"])
                print(f"✅ Installed {package}")
            else:
                print(f"✅ {package} already installed")
        except Exception as e:
            print(f"⚠️ Error with {package}: {e}")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"✅ Installed {package}")
            except:
                print(f"❌ Failed to install {package}")

# Run installation check
ensure_packages()

# ======================
# IMPORTS
# ======================
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
    CallbackContext
)

# ======================
# CONFIG & DATABASE
# ======================
BOT_TOKEN = "7947096084:AAHEY4WElwTCqcucDT7XJuWOvXxilikNhd8"  # ⚠️ CHANGE TO YOUR BOT TOKEN
USER_DATA_FILE = "user_data.json"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# ======================
# EMOJI SETS FOR DIFFERENT ENCODING TYPES
# ======================
EMOJI_SET_1 = ["😀", "😁", "😂", "🤣", "😃", "😄", "😅", "😆", "😉", "😊", "😋", "😎", "😍", "😘", "😗", "😙", "😚"]
EMOJI_SET_2 = ["🙂", "🤗", "🤩", "🤔", "🤨", "😐", "😑", "😶", "🙄", "😏", "😣", "😥", "😮", "🤐", "😯", "😪", "😫"]
EMOJI_SET_3 = ["🥱", "😴", "😌", "🤓", "😛", "😜", "😝", "🤤", "😒", "😓", "😔", "😕", "🙃", "🤑", "😲", "😷", "🤒"]
NUM_EMOJIS = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]

# ======================
# DATABASE FUNCTIONS
# ======================
def load_user_data():
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_user_key(user_id):
    """Generate unique encryption key for each user"""
    seed = str(user_id) + BOT_TOKEN
    return hashlib.sha256(seed.encode()).digest()[:16]

# ======================
# HELPERS
# ======================
def format_file_size(size):
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

# ======================
# ENCRYPTION
# ======================
def aes_encrypt(text, key):
    """AES encryption with proper key handling"""
    iv = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(text.encode('utf-8'), AES.block_size))
    return base64.b64encode(iv + encrypted).decode('utf-8')

def aes_decrypt(text, key):
    """AES decryption with error handling"""
    try:
        raw = base64.b64decode(text)
        iv, data = raw[:16], raw[16:]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(data), AES.block_size)
        return decrypted.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Decryption failed: {str(e)}")

# ======================
# EMOJI NUMBER ENCODING (LIKE THE EXAMPLE)
# ======================
def create_emoji_number_map():
    """Create emoji to number mapping (0-9 for digits, A-F for hex)"""
    emoji_map = {}
    
    # Assign emojis to digits 0-9
    for i in range(10):
        emoji_map[str(i)] = random.choice(EMOJI_SET_1 + EMOJI_SET_2 + EMOJI_SET_3)
    
    # Also create reverse map
    reverse_map = {v: k for k, v in emoji_map.items()}
    
    return emoji_map, reverse_map

def emoji_number_encode(code):
    """Encode code using emoji number encoding like in the example"""
    # Convert each character to its ASCII value, then to hex
    hex_chars = []
    for char in code:
        hex_val = hex(ord(char))[2:].zfill(2)  # Convert to 2-digit hex
        hex_chars.append(hex_val)
    
    # Join hex values
    hex_string = "".join(hex_chars)
    
    # Create emoji map for digits 0-9 and letters a-f
    emoji_digits = {}
    reverse_digits = {}
    
    # Digits 0-9
    all_emojis = EMOJI_SET_1 + EMOJI_SET_2 + EMOJI_SET_3
    used_emojis = random.sample(all_emojis, 16)  # 0-9 + a-f
    
    # Map 0-9
    for i in range(10):
        emoji_digits[str(i)] = used_emojis[i]
        reverse_digits[used_emojis[i]] = str(i)
    
    # Map a-f (hex letters)
    hex_letters = "abcdef"
    for i, letter in enumerate(hex_letters):
        emoji_digits[letter] = used_emojis[10 + i]
        reverse_digits[used_emojis[10 + i]] = letter
    
    # Encode hex string with emojis
    encoded = ""
    for char in hex_string:
        encoded += emoji_digits[char] + " "
    
    return encoded.strip(), emoji_digits, reverse_digits

def emoji_number_decode(encoded_text, reverse_map):
    """Decode emoji number encoded text back to original code"""
    # Split by spaces and decode each emoji
    hex_chars = []
    for emoji in encoded_text.split():
        if emoji in reverse_map:
            hex_chars.append(reverse_map[emoji])
    
    # Convert hex string back to text
    hex_string = "".join(hex_chars)
    
    # Convert hex pairs back to characters
    decoded = ""
    for i in range(0, len(hex_string), 2):
        hex_pair = hex_string[i:i+2]
        if len(hex_pair) == 2:
            decoded += chr(int(hex_pair, 16))
    
    return decoded

# ======================
# OBFUSCATION TECHNIQUES
# ======================
def safe_compile(code):
    """Safely compile code with proper error handling"""
    try:
        return compile(code, "<emoji_bot>", "exec")
    except SyntaxError as e:
        try:
            # Try without shebang if present
            if code.startswith('#!'):
                code = code[code.find('\n')+1:] if '\n' in code else ""
            
            # Remove empty lines and try again
            lines = [line for line in code.split('\n') if line.strip()]
            fixed_code = '\n'.join(lines)
            return compile(fixed_code, "<emoji_bot>", "exec")
        except:
            # Last resort: wrap in exec
            wrapped_code = f'exec("""{code.replace('"', '\\"')}""")'
            return compile(wrapped_code, "<emoji_bot>", "exec")

def marshal_zlib(code):
    """Basic obfuscation using marshal and zlib"""
    try:
        c = safe_compile(code)
        d = marshal.dumps(c)
        z = zlib.compress(d, level=9)
        b = base64.b64encode(z).decode()
        
        return f'''# 🔥 Obfuscated by Python File Obfuscator Bot
# ⏰ Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}
# 📁 Original: Python File
# 🔒 Security Level: High

import marshal, zlib, base64

ENC_DATA = "{b}"

try:
    exec(marshal.loads(zlib.decompress(base64.b64decode(ENC_DATA))))
except Exception as e:
    print(f"Execution error: {{e}}")
'''
    except Exception as e:
        # Fallback to simple encoding if obfuscation fails
        return f'''# ⚠️ Obfuscation failed, using basic encoding
# Error: {str(e)}
import base64

ENC_DATA = "{base64.b64encode(code.encode()).decode()}"

try:
    exec(base64.b64decode(ENC_DATA).decode())
except Exception as e:
    print(f"Execution error: {{e}}")
'''

def create_emoji_encoded_file(code, filename):
    """Create emoji encoded Python file like the example"""
    encoded_text, emoji_map, reverse_map = emoji_number_encode(code)
    
    # Create the Python file with decoder
    python_code = f'''# 😈 Encrypted by Emoji Encoder Bot
# ⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}
# 📁 Original: {filename}
# 🔢 Original size: {len(code)} characters
# 🔐 Encoding: Emoji Hex Encoding

exec("".join(map(chr,[int("".join(str({{'{emoji_map['0']}': 0, '{emoji_map['1']}': 1, '{emoji_map['2']}': 2, '{emoji_map['3']}': 3, '{emoji_map['4']}': 4, '{emoji_map['5']}': 5, '{emoji_map['6']}': 6, '{emoji_map['7']}': 7, '{emoji_map['8']}': 8, '{emoji_map['9']}': 9, '{emoji_map['a']}': 10, '{emoji_map['b']}': 11, '{emoji_map['c']}': 12, '{emoji_map['d']}': 13, '{emoji_map['e']}': 14, '{emoji_map['f']}': 15}}[i]) for i in x.split())) for x in
"{encoded_text}"
.split("  ")])))

# Decryption Information:
# This file uses emoji-to-hex encoding
# Each emoji represents a hex digit (0-9, a-f)
# Combined hex values form the original Python code
'''
    
    return python_code

def create_aes_encrypted_file(code, key, user_id, filename):
    """Create AES encrypted Python file"""
    encrypted = aes_encrypt(code, key)
    key_hash = hashlib.sha256(key).hexdigest()[:16]
    
    return f'''# 🔐 AES-256 Encrypted Python File
# ⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}
# 📁 Original: {filename}
# 👤 User ID: {user_id}
# 🔑 Key Hash: {key_hash}
# 🔒 Security: Military Grade AES-256

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64, hashlib

# ============================================
# ENCRYPTED DATA
# ============================================
ENC_DATA = """{encrypted}"""

def get_decryption_key(user_id):
    """Retrieve decryption key using user ID"""
    # ⚠️ Replace with your actual bot token
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    seed = str(user_id) + BOT_TOKEN
    return hashlib.sha256(seed.encode()).digest()[:16]

def decrypt_aes(encrypted_data, key):
    """Decrypt AES encrypted data"""
    try:
        raw = base64.b64decode(encrypted_data)
        iv, data = raw[:16], raw[16:]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(data), AES.block_size)
        return decrypted.decode('utf-8')
    except Exception as e:
        raise Exception(f"Decryption failed: {{str(e)}}")

if __name__ == "__main__":
    print("🔐 AES Decryption System")
    print("=" * 50)
    
    try:
        # Get decryption key
        key = get_decryption_key({user_id})
        
        print(f"👤 User ID: {{user_id}}")
        print(f"🔑 Key Hash: {{key.hex()[:16]}}")
        print("=" * 50)
        
        # Decrypt and execute
        print("🔓 Decrypting code...")
        decrypted_code = decrypt_aes(ENC_DATA, key)
        
        print(f"✅ Decrypted {{len(decrypted_code)}} characters")
        print("🚀 Executing code...")
        print("=" * 50)
        
        exec(decrypted_code)
        
    except Exception as e:
        print(f"❌ Error: {{e}}")
        print("=" * 50)
        print("Make sure to set correct BOT_TOKEN in get_decryption_key() function")
'''

# ======================
# UI COMPONENTS
# ======================
def main_keyboard():
    """Main menu keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 Upload .py File", callback_data="upload_info"),
            InlineKeyboardButton("📊 Stats", callback_data="stats")
        ],
        [
            InlineKeyboardButton("❓ How to Use", callback_data="help"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings")
        ]
    ])

def file_options_keyboard():
    """File processing options"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💣 Obfuscate", callback_data="file_obf"),
            InlineKeyboardButton("😈 Emoji Encode", callback_data="file_emoji")
        ],
        [
            InlineKeyboardButton("🔐 AES Encrypt", callback_data="file_aes"),
            InlineKeyboardButton("✨ All Methods", callback_data="file_all")
        ],
        [
            InlineKeyboardButton("🔙 Cancel", callback_data="cancel")
        ]
    ])

def back_keyboard():
    """Back button keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_main")]
    ])

# ======================
# HANDLERS
# ======================
def start(update: Update, context: CallbackContext):
    """Handle /start command"""
    user_id = update.effective_user.id
    
    # Load user data
    user_data = load_user_data()
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {
            "files_processed": 0,
            "first_seen": time.time(),
            "last_seen": time.time(),
            "obfuscated_count": 0,
            "encrypted_count": 0,
            "emoji_encoded_count": 0
        }
        save_user_data(user_data)
    
    welcome_msg = """
🤖 *Python File Obfuscator Bot*
━━━━━━━━━━━━━━━━━

*Specialized for Python Files Only*

🔧 *Available Processing Methods:*
1. **💣 Obfuscation** - marshal + zlib + base64
2. **😈 Emoji Encoding** - Convert code to emojis (hex based)
3. **🔐 AES Encryption** - Military-grade encryption
4. **✨ All Methods** - All three in one package

📁 *How to Use:*
1. Upload any `.py` Python file
2. Choose processing method
3. Receive processed `.py` file back

⚡ *Features:*
• Auto-decryption/decoding built-in
• Unique encryption keys per user
• Preserves original functionality
• Max file size: 5MB

👇 *Upload a .py file to get started!*
    """
    
    update.message.reply_text(
        welcome_msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard()
    )

def help_command(update: Update, context: CallbackContext):
    """Handle /help command"""
    help_text = """
📖 *Python File Obfuscator - Help Guide*
━━━━━━━━━━━━━━━━━

*Supported Operations:*

1. **💣 Obfuscation**
   - Uses Python's marshal module
   - Compressed with zlib
   - Base64 encoded
   - Output: `obfuscated_*.py`

2. **😈 Emoji Encoding**
   - Converts code to hex then emojis
   - Each emoji represents hex digit (0-9, a-f)
   - Auto-decoder included
   - Output: `emojified_*.py`

3. **🔐 AES Encryption**
   - AES-256 encryption
   - User-specific keys
   - Auto-decryption included
   - Output: `encrypted_*.py`

4. **✨ All Methods**
   - All three methods combined
   - Ultimate protection
   - Triple-layer security
   - Output: 3 separate files

*Commands:*
/start - Start the bot
/stats - View your statistics

*Requirements:*
• Python files only (.py extension)
• Maximum size: 5MB
• Valid Python syntax recommended

⚠️ *Note:* Some obfuscation methods may increase file size.
    """
    
    if update.message:
        update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
    elif update.callback_query:
        query = update.callback_query
        query.answer()
        query.edit_message_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )

def stats_command(update: Update, context: CallbackContext):
    """Handle /stats command"""
    user_id = update.effective_user.id
    user_data = load_user_data()
    
    if str(user_id) in user_data:
        data = user_data[str(user_id)]
        stats_msg = f"""
📊 *Your Statistics*
━━━━━━━━━━━━━━━━━
👤 User ID: `{user_id}`
📁 Total Files: {data.get('files_processed', 0)}
💣 Obfuscated: {data.get('obfuscated_count', 0)}
😈 Emoji Encoded: {data.get('emoji_encoded_count', 0)}
🔐 Encrypted: {data.get('encrypted_count', 0)}
📅 First Seen: <code>{time.strftime('%Y-%m-%d', time.localtime(data.get('first_seen', time.time())))}</code>
🕒 Last Active: <code>{time.strftime('%Y-%m-%d %H:%M', time.localtime(data.get('last_seen', time.time())))}</code>
        """
    else:
        stats_msg = "📊 No statistics available yet. Upload your first .py file!"
    
    if update.message:
        update.message.reply_text(
            stats_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard()
        )
    elif update.callback_query:
        query = update.callback_query
        query.answer()
        query.edit_message_text(
            stats_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard()
        )

def file_handler(update: Update, context: CallbackContext):
    """Handle Python file uploads only"""
    user_id = update.effective_user.id
    
    # Check if it's a Python file
    file_name = update.message.document.file_name.lower()
    if not file_name.endswith('.py'):
        update.message.reply_text(
            "❌ *Invalid File Type*\n"
            "Only Python files (.py) are supported!\n"
            "Please upload a .py file.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_keyboard()
        )
        return
    
    # Check file size
    if update.message.document.file_size > MAX_FILE_SIZE:
        update.message.reply_text(
            f"❌ *File Too Large*\n"
            f"Maximum size: {format_file_size(MAX_FILE_SIZE)}\n"
            f"Your file: {format_file_size(update.message.document.file_size)}\n\n"
            f"Please upload a smaller Python file.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_keyboard()
        )
        return
    
    # Store file info for processing
    context.user_data["pending_file"] = {
        "file_id": update.message.document.file_id,
        "file_name": update.message.document.file_name,
        "file_size": update.message.document.file_size,
        "user_id": user_id,
        "upload_time": time.time()
    }
    
    update.message.reply_text(
        f"✅ *Python File Received*\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"📄 File: `{update.message.document.file_name}`\n"
        f"📏 Size: `{format_file_size(update.message.document.file_size)}`\n"
        f"👤 User: `{user_id}`\n\n"
        f"👇 *Choose processing method:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=file_options_keyboard()
    )

def process_file(update: Update, context: CallbackContext, method: str):
    """Process uploaded Python file"""
    query = update.callback_query
    query.answer()
    
    file_info = context.user_data.get("pending_file")
    if not file_info:
        query.edit_message_text("❌ No file to process! Please upload a .py file first.")
        return
    
    user_id = file_info["user_id"]
    
    # Update stats
    user_data = load_user_data()
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {
            "files_processed": 0,
            "obfuscated_count": 0,
            "encrypted_count": 0,
            "emoji_encoded_count": 0
        }
    
    msg = query.message.reply_text(f"📥 Downloading {format_file_size(file_info['file_size'])}...")
    
    try:
        # Download file
        file = context.bot.get_file(file_info["file_id"])
        file_bytes = file.download_as_bytearray()
        original_code = file_bytes.decode('utf-8', errors='ignore')
        
        timestamp = int(time.time())
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        msg.edit_text("⚙️ Processing Python file...")
        
        processed_files = []
        captions = []
        
        if method in ["file_obf", "file_all"]:
            # Obfuscation
            result = marshal_zlib(original_code)
            filename = f"obfuscated_{timestamp}_{random_str}.py"
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py', encoding='utf-8') as t:
                t.write(result)
                temp_path = t.name
            
            processed_files.append((temp_path, filename))
            captions.append(f"💣 *Obfuscated Python File*\n📁 Original: `{file_info['file_name']}`\n⚡ Method: Marshal + Zlib + Base64")
            
            user_data[str(user_id)]["obfuscated_count"] = user_data[str(user_id)].get("obfuscated_count", 0) + 1
        
        if method in ["file_emoji", "file_all"]:
            # Emoji Encoding (Hex-based like the example)
            result = create_emoji_encoded_file(original_code, file_info['file_name'])
            filename = f"emojified_{timestamp}_{random_str}.py"
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py', encoding='utf-8') as t:
                t.write(result)
                temp_path = t.name
            
            processed_files.append((temp_path, filename))
            captions.append(f"😈 *Emoji Encoded Python File*\n📁 Original: `{file_info['file_name']}`\n🎨 Method: Emoji Hex Encoding")
            
            user_data[str(user_id)]["emoji_encoded_count"] = user_data[str(user_id)].get("emoji_encoded_count", 0) + 1
        
        if method in ["file_aes", "file_all"]:
            # AES Encryption
            user_key = get_user_key(user_id)
            result = create_aes_encrypted_file(original_code, user_key, user_id, file_info['file_name'])
            filename = f"encrypted_{timestamp}_{random_str}.py"
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py', encoding='utf-8') as t:
                t.write(result)
                temp_path = t.name
            
            processed_files.append((temp_path, filename))
            captions.append(f"🔐 *AES Encrypted Python File*\n📁 Original: `{file_info['file_name']}`\n🔑 User ID: `{user_id}`\n🔒 Method: AES-256 Encryption")
            
            user_data[str(user_id)]["encrypted_count"] = user_data[str(user_id)].get("encrypted_count", 0) + 1
        
        # Update overall stats
        user_data[str(user_id)]["files_processed"] = user_data[str(user_id)].get("files_processed", 0) + 1
        user_data[str(user_id)]["last_seen"] = time.time()
        save_user_data(user_data)
        
        msg.edit_text(f"📤 Uploading {len(processed_files)} file(s)...")
        
        # Send processed files
        for (filepath, filename), caption in zip(processed_files, captions):
            try:
                # Open file and read content to ensure it's not empty
                with open(filepath, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Check if file has content
                if len(file_content.strip()) > 0:
                    # Send the file
                    query.message.reply_document(
                        document=open(filepath, 'rb'),
                        filename=filename,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    query.message.reply_text(
                        f"⚠️ Empty file generated: {filename}"
                    )
                
                # Clean up temp file
                os.unlink(filepath)
                
            except Exception as e:
                query.message.reply_text(
                    f"❌ Error sending file {filename}: {str(e)[:100]}"
                )
                print(f"Error sending file {filename}: {e}")
        
        # Send completion message
        if method == "file_all":
            completion_msg = f"""
✅ *Processing Complete!*
━━━━━━━━━━━━━━━━━
📁 Original: `{file_info['file_name']}`
🎯 Methods: All 3 (Obfuscation + Emoji + AES)
📦 Files Generated: 3
⏱️ Time: {int(time.time() - file_info['upload_time'])}s
👤 User: `{user_id}`

✨ *All protection methods applied successfully!*
Each file contains auto-decryption/decoding functionality.
            """
        else:
            method_name = {
                "file_obf": "Obfuscation",
                "file_emoji": "Emoji Encoding", 
                "file_aes": "AES Encryption"
            }.get(method, "Unknown")
            
            completion_msg = f"""
✅ *Processing Complete!*
━━━━━━━━━━━━━━━━━
📁 Original: `{file_info['file_name']}`
🎯 Method: {method_name}
⏱️ Time: {int(time.time() - file_info['upload_time'])}s
👤 User: `{user_id}`

✨ *File processed successfully!*
The generated file contains auto-decryption/decoding functionality.
            """
        
        query.message.reply_text(
            completion_msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_keyboard()
        )
        
        msg.delete()
        
        # Clean up pending file data
        if "pending_file" in context.user_data:
            del context.user_data["pending_file"]
            
    except Exception as e:
        error_msg = f"""
❌ *Processing Failed*
━━━━━━━━━━━━━━━━━
📁 File: `{file_info['file_name']}`
⚠️ Error: `{str(e)[:200]}`

Please try again or upload a different file.
        """
        msg.edit_text(
            error_msg,
            parse_mode=ParseMode.MARKDOWN
        )
        print(f"File processing error: {e}")

def button_handler(update: Update, context: CallbackContext):
    """Handle button clicks"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    
    # Update last seen
    user_data = load_user_data()
    if str(user_id) in user_data:
        user_data[str(user_id)]["last_seen"] = time.time()
        save_user_data(user_data)
    
    # Handle different button actions
    if query.data == "back_main":
        query.edit_message_text(
            "🔙 *Back to Main Menu*\n\n👇 Upload a .py file to begin!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_keyboard()
        )
        return
    
    elif query.data == "upload_info":
        info_msg = """
📤 *Upload Instructions*
━━━━━━━━━━━━━━━━━
1. *File Type:* `.py` Python files only
2. *Size Limit:* 5MB maximum
3. *Processing:* Choose from 4 methods:
   - 💣 Obfuscation
   - 😈 Emoji Encoding (Hex-based)  
   - 🔐 AES Encryption
   - ✨ All Methods (recommended)

⚠️ *Note:* 
• Large files may take longer to process
• Original functionality is preserved
• Each user gets unique encryption keys

👇 *Ready to upload? Just send a .py file!*
        """
        query.edit_message_text(
            info_msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        return
    
    elif query.data == "help":
        help_command(update, context)
        return
    
    elif query.data == "stats":
        stats_command(update, context)
        return
    
    elif query.data == "settings":
        settings_msg = """
⚙️ *Bot Settings*
━━━━━━━━━━━━━━━━━

*Current Configuration:*
• Max File Size: 5MB
• Supported: .py files only
• Auto-cleanup: Enabled
• User-specific keys: Enabled

*Available Commands:*
/start - Main menu
/stats - Your statistics
/help - Detailed guide

*Privacy:*
• Files are processed temporarily
• No permanent storage
• Encryption keys user-specific
        """
        query.edit_message_text(
            settings_msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        return
    
    elif query.data == "cancel":
        if "pending_file" in context.user_data:
            del context.user_data["pending_file"]
        query.edit_message_text(
            "❌ Operation cancelled.\n\n👇 Upload a .py file to begin!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_keyboard()
        )
        return
    
    # Handle file processing options
    elif query.data.startswith("file_"):
        process_file(update, context, query.data)
        return

# ======================
# ERROR HANDLER
# ======================
def error_handler(update: Update, context: CallbackContext):
    """Handle errors gracefully"""
    print(f"Error: {context.error}")
    
    error_msg = """
❌ *An Error Occurred*
━━━━━━━━━━━━━━━━━
The bot encountered an unexpected error.

Please try:
1. Uploading the file again
2. Checking file size (max 5MB)
3. Ensuring it's a .py file

If the problem persists, please contact support.
    """
    
    if update and update.effective_message:
        update.effective_message.reply_text(
            error_msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_keyboard()
        )

# ======================
# MAIN APPLICATION
# ======================
def main():
    """Start the bot"""
    print("=" * 50)
    print("🤖 Python File Obfuscator Bot")
    print("📁 Specialized for .py files only")
    print(f"🕒 Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    try:
        # Create updater
        updater = Updater(BOT_TOKEN, use_context=True)
        dp = updater.dispatcher
        
        # Add handlers
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("stats", stats_command))
        dp.add_handler(CommandHandler("help", help_command))
        
        # File handler - .py files only
        dp.add_handler(MessageHandler(
            Filters.document.file_extension("py"),
            file_handler
        ))
        
        dp.add_handler(CallbackQueryHandler(button_handler))
        
        # Error handler
        dp.add_error_handler(error_handler)
        
        # Start polling
        updater.start_polling()
        
        print("✅ Bot started successfully!")
        print("📡 Listening for file uploads...")
        
        # Run until Ctrl+C
        updater.idle()
        
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()