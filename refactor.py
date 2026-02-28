import re

with open('backend/app/lib/kis_client.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Methods to move
methods = [
    r'( {4}async def get_ws_approval_key.*?)(?=\n {4}async def |\n {4}# |\n    def |\Z)',
    r'( {4}async def _connect_websocket.*?)(?=\n {4}async def |\n {4}# |\n    def |\Z)',
    r'( {4}async def _disconnect_websocket.*?)(?=\n {4}async def |\n {4}# |\n    def |\Z)',
    r'( {4}# 웹소켓 토큰 발급\n {4}async def get_ws_token.*?)(?=\n {4}async def |\n {4}# |\n    def |\Z)',
    r'( {4}async def _subscribe_websocket.*?)(?=\n {4}async def |\n {4}# |\n    def |\Z)',
    r'( {4}# 실시간 현재가 조회\n {4}async def get_rt_current_price.*?)(?=\n {4}async def |\n {4}# |\n    def |\Z)'
]

extracted_methods = []
for m in methods:
    match = re.search(m, content, re.DOTALL)
    if match:
        extracted_methods.append(match.group(1))
        content = content.replace(match.group(1), '')

# Also remove ws_url and approval_key from KISClient.__init__
content = re.sub(r' {8}self\.ws_url = self\.KIS_VIRTUAL_WS_URL if is_virtual else self\.KIS_REAL_WS_URL\n', '', content)
content = re.sub(r' {8}self\.approval_key: Optional\[str\] = None # Added for websocket\n', '', content)

# Create KISWsClient class definition
ws_client_code = """class KISWsClient:
    def __init__(self, app_key: str, app_secret: str, is_virtual: bool = True):
        self.app_key = app_key
        self.app_secret = app_secret
        self.is_virtual = is_virtual
        self.base_url = self.KIS_VIRTUAL_INVESTMENT_BASE_URL if is_virtual else self.KIS_REAL_INVESTMENT_BASE_URL
        self.ws_url = self.KIS_VIRTUAL_WS_URL if is_virtual else self.KIS_REAL_WS_URL
        self.approval_key: Optional[str] = None
        self.websocket_client = None
"""

ws_client_code += '\n'.join(extracted_methods)

content = content.replace('class KISWsClient:\n    pass', ws_client_code)

with open('backend/app/lib/kis_client.py', 'w', encoding='utf-8') as f:
    f.write(content)
