"""
LLMFactory 工厂类
根据配置动态实例化对应的 LLM Provider
"""

import os
from typing import Type

from .base_llm import BaseLLM
from utils.config_loader import ConfigLoader


class LLMFactory:
    """
    LLM 客户端工厂
    
    根据配置文件中的 provider_type 动态创建对应的 Provider 实例。
    支持运行时切换不同的模型配置。
    """

    # Provider 类型到实现类的映射 (延迟导入，避免循环依赖)
    _provider_registry: dict[str, str] = {
        "openai": "providers.openai_provider.OpenAIProvider",
        "gemini": "providers.gemini_provider.GeminiProvider",
    }

    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        初始化工厂
        
        Args:
            config_path: 配置文件路径
        """
        self.config_loader = ConfigLoader(config_path)
        self.settings = self.config_loader.load()

    def create_llm(self, profile_name: str | None = None) -> BaseLLM:
        """
        创建 LLM 实例
        
        Args:
            profile_name: 配置名称 (可选，默认使用 current_active_profile)
            
        Returns:
            BaseLLM 实例
            
        Raises:
            ValueError: 找不到指定的 profile 或 provider_type
            KeyError: 配置缺少必要字段
        """
        # 优先读取环境变量 (向后兼容旧项目的 .env 配置方式)
        env_provider = os.getenv("LLM_PROVIDER")
        if env_provider:
            provider_type = env_provider.lower()
            model_name = os.getenv("LLM_MODEL", "")
            api_key_raw = os.getenv("LLM_API_KEYS", "")
            base_url = os.getenv("LLM_API_BASE")
            if not base_url:
                base_url = None
        else:
            # 否则从 settings.yaml 加载
            if profile_name is None:
                profile_name = self.settings.get("current_active_profile")
                if not profile_name:
                    raise ValueError("未指定 LLM_PROVIDER，且 settings.yaml 中未配置 current_active_profile")

            profiles = self.settings.get("profiles", {})
            if profile_name not in profiles:
                available = list(profiles.keys())
                raise ValueError(f"找不到配置 '{profile_name}'。可用的配置: {available}")

            profile = profiles[profile_name]
            provider_type = profile.get("provider_type")
            model_name = profile.get("model_name")
            api_key_env_var = profile.get("api_key_env_var")
            network = profile.get("network", {})
            base_url = network.get("custom_base_url") if network.get("use_custom_url") else None
            
            api_key_raw = os.getenv(api_key_env_var)

        if not api_key_raw:
            raise ValueError("API Key 未设置或为空。请在 .env 文件中配置 LLM_API_KEYS。")
            
        # 支持逗号分隔的多 Key 轮换
        if "," in api_key_raw:
            api_key = [k.strip() for k in api_key_raw.split(",") if k.strip()]
        else:
            api_key = api_key_raw

        # 获取 Provider 类
        provider_class = self._get_provider_class(provider_type)

        # 实例化并返回
        return provider_class(
            api_key=api_key,
            model_name=model_name,
            base_url=base_url
        )

    def _get_provider_class(self, provider_type: str) -> Type[BaseLLM]:
        """
        根据 provider_type 获取对应的 Provider 类
        
        Args:
            provider_type: 提供者类型 (如 "openai", "gemini")
            
        Returns:
            Provider 类
            
        Raises:
            ValueError: 未知的 provider_type
        """
        if provider_type not in self._provider_registry:
            available = list(self._provider_registry.keys())
            raise ValueError(
                f"未知的 provider_type: '{provider_type}'。"
                f"支持的类型: {available}"
            )

        # 动态导入
        module_path = self._provider_registry[provider_type]
        module_name, class_name = module_path.rsplit(".", 1)

        import importlib
        module = importlib.import_module(module_name)
        provider_class = getattr(module, class_name)

        return provider_class

    @classmethod
    def register_provider(cls, provider_type: str, class_path: str) -> None:
        """
        注册新的 Provider 类型 (扩展点)
        
        Args:
            provider_type: 提供者类型标识
            class_path: 完整的类路径 (如 "providers.custom.CustomProvider")
        """
        cls._provider_registry[provider_type] = class_path

    def list_profiles(self) -> list[str]:
        """
        列出所有可用的配置名称
        
        Returns:
            配置名称列表
        """
        return list(self.settings.get("profiles", {}).keys())
