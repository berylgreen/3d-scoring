"""
配置加载工具
负责读取 YAML 配置文件和环境变量
"""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from core.logger import logger


class ConfigLoader:
    """
    配置加载器
    
    职责:
    1. 加载 .env 文件中的环境变量
    2. 读取并解析 YAML 配置文件
    3. 提供配置访问的便捷方法
    """

    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        初始化配置加载器
        
        Args:
            config_path: 配置文件相对路径
        """
        # 确定项目根目录
        self.project_root = Path(__file__).parent.parent
        self.config_path = self.project_root / config_path
        
        # 加载 .env 文件
        env_path = self.project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            # 尝试加载 .env.example 作为备选 (仅用于开发)
            env_example = self.project_root / ".env.example"
            if env_example.exists():
                logger.warning(f"警告: 未找到 .env 文件，正在使用 .env.example")
                load_dotenv(env_example)

    def load(self) -> dict[str, Any]:
        """
        加载并返回完整的配置字典
        
        Returns:
            配置字典
            
        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML 解析错误
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"配置文件不存在: {self.config_path}\n"
                f"请确保 config/settings.yaml 文件已创建。"
            )

        with open(self.config_path, "r", encoding="utf-8") as f:
            try:
                config = yaml.safe_load(f)
                return config or {}
            except yaml.YAMLError as e:
                raise yaml.YAMLError(f"YAML 解析错误: {e}") from e

    def get_profile(self, profile_name: str | None = None) -> dict[str, Any]:
        """
        获取指定的配置 Profile
        
        Args:
            profile_name: 配置名称 (可选，默认使用 current_active_profile)
            
        Returns:
            Profile 配置字典
        """
        config = self.load()
        
        if profile_name is None:
            profile_name = config.get("current_active_profile")
            
        profiles = config.get("profiles", {})
        
        if profile_name not in profiles:
            raise KeyError(f"Profile '{profile_name}' 不存在")
            
        return profiles[profile_name]

    @staticmethod
    def get_env(key: str, default: str | None = None) -> str | None:
        """
        获取环境变量
        
        Args:
            key: 环境变量名
            default: 默认值
            
        Returns:
            环境变量值
        """
        return os.getenv(key, default)

    @staticmethod
    def require_env(key: str) -> str:
        """
        获取必需的环境变量 (不存在则抛出异常)
        
        Args:
            key: 环境变量名
            
        Returns:
            环境变量值
            
        Raises:
            ValueError: 环境变量不存在或为空
        """
        value = os.getenv(key)
        if not value:
            raise ValueError(
                f"必需的环境变量 '{key}' 未设置。\n"
                f"请在 .env 文件中配置此变量。"
            )
        return value
