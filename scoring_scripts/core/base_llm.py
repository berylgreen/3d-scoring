"""
BaseLLM 抽象基类
定义所有大模型 Provider 必须实现的统一接口
"""

from abc import ABC, abstractmethod
from typing import Iterator


class BaseLLM(ABC):
    """
    大模型抽象基类
    
    所有具体的 Provider (OpenAI, Gemini 等) 都必须继承此类并实现抽象方法。
    这保证了业务代码可以面向接口编程，而不依赖具体实现。
    """

    def __init__(
        self,
        api_key: str | list[str],
        model_name: str,
        base_url: str | None = None
    ):
        """
        初始化基类
        
        Args:
            api_key: API 密钥，可以是单个字符串，也可以是列表（用于限流自动切换）
            model_name: 模型名称
            base_url: 自定义 API 地址 (可选，用于代理场景)
        """
        self.api_keys = [api_key] if isinstance(api_key, str) else api_key
        self.api_key = self.api_keys[0] if self.api_keys else ""
        self.model_name = model_name
        self.base_url = base_url

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        简单文本生成接口
        
        Args:
            prompt: 用户输入的提示词
            
        Returns:
            模型生成的文本响应
        """
        pass

    def generate_structured(self, prompt: str, schema: dict, files: list = None, system_instruction: str = None) -> dict:
        """
        结构化生成接口 (可选实现，子类可覆盖)
        
        Args:
            prompt: 用户输入的提示词
            schema: 期待的 JSON Schema
            files: 附加的多模态文件列表（如视频、图片对象）
            system_instruction: 系统提示词
            
        Returns:
            解析后的字典对象
        """
        raise NotImplementedError("该 Provider 尚未实现结构化输出")

    def upload_file(self, file_path: str):
        """
        上传文件 (用于需要预先上传文件的服务，如 Gemini File API)
        """
        raise NotImplementedError("该 Provider 尚未实现文件上传")

    def delete_file(self, file_id: str):
        """
        删除已上传的文件
        """
        pass

    @abstractmethod
    def chat(self, messages: list[dict]) -> str:
        """
        多轮对话接口 (OpenAI 格式)
        
        Args:
            messages: 对话历史，格式为:
                [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello!"},
                    {"role": "assistant", "content": "Hi there!"},
                    {"role": "user", "content": "How are you?"}
                ]
                
        Returns:
            模型生成的文本响应
        """
        pass

    def stream_chat(self, messages: list[dict]) -> Iterator[str]:
        """
        流式对话接口 (可选实现)
        
        默认实现为非流式调用，子类可以覆盖此方法以支持流式输出。
        
        Args:
            messages: 对话历史
            
        Yields:
            逐块生成的文本
        """
        # 默认实现：直接返回完整响应
        yield self.chat(messages)

    def get_info(self) -> dict:
        """
        获取当前 Provider 的元信息
        
        Returns:
            包含模型名称、API 地址等信息的字典
        """
        return {
            "provider": self.__class__.__name__,
            "model_name": self.model_name,
            "base_url": self.base_url or "官方默认地址",
            "api_key_preview": f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else "***"
        }
