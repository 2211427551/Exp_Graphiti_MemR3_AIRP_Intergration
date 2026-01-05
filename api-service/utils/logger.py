# ============================================
# 日志配置模块
# ============================================
import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "airp",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    配置日志记录器
    
    参数:
        name: str = "airp"
                日志记录器名称
        level: int = logging.INFO
                日志级别
        log_file: Optional[str] = None
                日志文件路径（可选）
        format_string: Optional[str] = None
                自定义格式字符串（可选）
    
    返回:
        logging.Logger: 配置好的日志记录器
    
    功能:
        - 配置控制台输出
        - 可选配置文件输出
        - 设置统一的日志格式
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 默认格式
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    formatter = logging.Formatter(format_string)
    
    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件handler（可选）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
