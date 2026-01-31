"""验证配置加载：从项目根目录运行，打印从 .env 读取的配置项。"""
import sys
from pathlib import Path

# 保证从项目根加载 .env
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from apps.api.config import get_settings

if __name__ == "__main__":
    s = get_settings()
    print("APP_ENV:", s.APP_ENV)
    print("MODEL_BASE_URL:", s.MODEL_BASE_URL)
    print("MODEL_NAME:", s.MODEL_NAME)
