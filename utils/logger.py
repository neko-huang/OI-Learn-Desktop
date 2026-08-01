"""
统一日志系统
替换所有 print 语句，支持日志分级、文件输出、格式统一
"""
import logging
import os
from config import get_data_dir

_logger = None


def get_logger(name: str = 'oi-learn') -> logging.Logger:
    """获取全局 logger 实例"""
    global _logger
    if _logger is not None:
        return _logger
    
    _logger = logging.getLogger(name)
    _logger.setLevel(logging.DEBUG)
    
    # 避免重复添加 handler
    if _logger.handlers:
        return _logger
    
    # 日志文件
    log_dir = get_data_dir()
    log_file = os.path.join(log_dir, 'app.log')
    
    # 文件 handler（详细日志）
    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_fmt)
    _logger.addHandler(file_handler)
    
    # 控制台 handler（仅 WARNING 及以上）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_fmt = logging.Formatter('[%(levelname)s] %(message)s')
    console_handler.setFormatter(console_fmt)
    _logger.addHandler(console_handler)
    
    return _logger


# 便捷函数
def debug(msg, *args):
    get_logger().debug(msg, *args)

def info(msg, *args):
    get_logger().info(msg, *args)

def warning(msg, *args):
    get_logger().warning(msg, *args)

def error(msg, *args):
    get_logger().error(msg, *args)
