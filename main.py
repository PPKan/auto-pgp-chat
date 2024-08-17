import pyautogui
import easyocr
import re
import base64
import sys
import logging
import time
import pyperclip
import itertools
import warnings
from functools import lru_cache

warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

IMAGE_PATH = r"C:\Users\peter\Desktop\apps\auto-line-pgp\telegram_screen.png"

def capture_telegram_screen():
    screenshot = pyautogui.screenshot(region=(1800, 1200, 800, 100))
    screenshot.save(IMAGE_PATH)
    logging.info(f"截圖已保存到: {IMAGE_PATH}")
    return IMAGE_PATH

def extract_text_from_image(image_path):
    reader = easyocr.Reader(['en'])  # 只使用英文模型
    result = reader.readtext(image_path)
    text = ' '.join([item[1] for item in result])
    logging.info(f"OCR 識別的原始文本: {repr(text)}")
    return text

def process_text(text):
    # 提取 ===...=== 之間的內容，包括等號
    messages = re.findall(r'#(.+?)#', text)
    logging.info(f"提取的編碼消息: {messages}")
    return messages

def decode_base64(encoded_message):
    def try_decode(message):
        try:
            message = message.strip()
            message += '=' * ((4 - len(message) % 4) % 4)
            decoded = base64.b64decode(message).decode('utf-8')
            logging.info(f"Successfully decoded: {message} -> {decoded}")
            return decoded
        except:
            return None

    # Define bidirectional swap pairs
    swap_pairs = [
        ('S', '5'),
        ('Z', 'z'),
        ('=', '-'),
        ('t', '+'),
        ('j', 'J'),
        ('y', 'Y'),
    ]

    # Define one-way replacements (from: to)
    one_way_replacements = {
        'o': 'O',  # Replace 'O' with '0', but not vice versa
        'O': '0',
        '2': 'Z',  # Replace 'Z' with '2', but not vice versa
        'n': 'W', 
        'w': 'W',
    }

    def generate_swap_combinations(message):
        # Positions for bidirectional swaps
        swap_positions = {
            char: [i for i, c in enumerate(message) if c in pair]
            for pair in swap_pairs
            for char in pair
        }

        # Positions for one-way replacements
        one_way_positions = {
            char: [i for i, c in enumerate(message) if c == char]
            for char in one_way_replacements.keys()
        }

        all_positions = list(set(sum(swap_positions.values(), []) + sum(one_way_positions.values(), [])))

        for r in range(len(all_positions) + 1):
            for positions in itertools.combinations(all_positions, r):
                modified = list(message)
                for pos in positions:
                    char = modified[pos]
                    # Check bidirectional swaps
                    for pair in swap_pairs:
                        if char in pair:
                            modified[pos] = pair[1] if char == pair[0] else pair[0]
                            break
                    # Check one-way replacements
                    if char in one_way_replacements:
                        modified[pos] = one_way_replacements[char]
                yield ''.join(modified)

    # Try original message
    result = try_decode(encoded_message)
    if result:
        return result

    # Try all swap combinations
    for modified_message in generate_swap_combinations(encoded_message):
        result = try_decode(modified_message)
        if result:
            return result

    # Try different encodings
    for encoding in ['utf-8']:
        try:
            decoded = base64.b64decode(encoded_message).decode(encoding)
            logging.info(f"Successfully decoded using {encoding} encoding: {decoded}")
            return decoded
        except:
            pass

    return f"[Decoding Error: {encoded_message}]"

def read_telegram_messages():
    image_path = capture_telegram_screen()
    text = extract_text_from_image(image_path)
    encoded_messages = process_text(text)
    decoded_messages = [decode_base64(msg) for msg in encoded_messages]
    return decoded_messages

def send_telegram_message(message):
    # 保存原始剪貼板內容
    original_clipboard = pyperclip.paste()
    
    try:
        # 將消息複製到剪貼板
        pyperclip.copy(message)
        
        # 點擊輸入框
        pyautogui.click(x=2000, y=1300)
        time.sleep(0.5)
        
        # 使用快捷鍵粘貼
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.5)
        
        # 按下 Enter 發送消息
        pyautogui.press('enter')
        
        logging.info(f"發送消息: {message}")
    finally:
        # 恢復原始剪貼板內容
        pyperclip.copy(original_clipboard)

def write_message(message):
    encoded_message = base64.b64encode(message.encode('utf-8')).decode('utf-8')
    formatted_message = f"#{encoded_message}#"
    send_telegram_message(formatted_message)
    logging.info(f"已發送編碼消息: {formatted_message}")

def main():
    if len(sys.argv) < 2:
        print("使用方法: python script.py [read|write] [message]")
        return

    command = sys.argv[1]

    if command == "read":
        try:
            messages = read_telegram_messages()
            print("解碼後的消息:")
            for msg in messages:
                print(msg)
        except Exception as e:
            logging.exception(f"讀取時發生錯誤: {e}")
    elif command == "write":
        if len(sys.argv) < 3:
            print("使用方法: python script.py write <message>")
            return
        message = ' '.join(sys.argv[2:])
        write_message(message)
    else:
        print("無效的命令。使用 'read' 或 'write'。")

if __name__ == "__main__":
    main()