
import logging
import sys
from logging.handlers import RotatingFileHandler
from config import LOG_FILE

def setup_logger(name="polycarb_app"):
    """
    配置并返回一个 logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 如果已经有 handler，就不重复添加了
    if logger.handlers:
        return logger

    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 文件 Handler (Rotating)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# 创建一个默认 logger
logger = setup_logger()
