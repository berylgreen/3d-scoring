import logging
import sys
from .config import settings

def setup_logger():
    # 创建全局的 logger
    logger = logging.getLogger("3d_scoring")
    
    # 避免重复绑定 handler
    if logger.hasHandlers():
        return logger

    # 从 settings 获取日志级别，默认为 INFO
    level_str = getattr(settings, "LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)
    
    logger.setLevel(level)
    
    # 创建日志格式化器
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 创建文件处理器 (如果有配置 LOG_FILE)
    if hasattr(settings, "LOG_FILE") and settings.LOG_FILE:
        # 确保日志文件目录存在
        settings.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(settings.LOG_FILE, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger

# 实例化全局可用的 logger
logger = setup_logger()
