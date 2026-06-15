"""
OpenAI Provider 实现
支持 OpenAI 官方 API 以及兼容 OpenAI 协议的第三方服务 (如代理、Ollama)
"""

from typing import Iterator

from openai import OpenAI

from core.base_llm import BaseLLM


class OpenAIProvider(BaseLLM):
    """
    OpenAI API 客户端封装
    
    支持:
    - OpenAI 官方 API
    - 任何兼容 OpenAI 协议的服务 (通过 base_url 指定)
    """

    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str | None = None
    ):
        """
        初始化 OpenAI Provider
        
        Args:
            api_key: API 密钥
            model_name: 模型名称 (如 "gpt-4o", "gpt-3.5-turbo")
            base_url: 自定义 API 地址 (可选)
        """
        super().__init__(api_key, model_name, base_url)
        
        # 构建 OpenAI 客户端
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
            
        self.client = OpenAI(**client_kwargs)

    def generate(self, prompt: str) -> str:
        """
        简单文本生成
        
        Args:
            prompt: 用户输入
            
        Returns:
            模型响应文本
        """
        # 将 prompt 转换为 chat 格式
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages)

    def chat(self, messages: list[dict]) -> str:
        """
        多轮对话
        
        Args:
            messages: 对话历史 (OpenAI 格式)
            
        Returns:
            模型响应文本
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"OpenAI API 调用失败: {e}") from e

    def stream_chat(self, messages: list[dict]) -> Iterator[str]:
        """
        流式对话输出
        
        Args:
            messages: 对话历史
            
        Yields:
            逐块生成的文本
        """
        try:
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise RuntimeError(f"OpenAI 流式 API 调用失败: {e}") from e

    def generate_structured(self, prompt: str, schema: dict, files: list = None, system_instruction: str = None) -> dict:
        """
        结构化输出
        """
        import json
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
            
        schema_prompt = f"{prompt}\n\n请务必返回合法的 JSON 格式数据，并严格遵循以下 JSON Schema 结构（不要添加任何 Markdown 代码块包裹）：\n{json.dumps(schema, ensure_ascii=False, indent=2)}"
        messages.append({"role": "user", "content": schema_prompt})
        
        if files:
            print("  [警告] 当前配置的 OpenAI 提供商尚未实现本地视频文件直接上传，视频评分将可能受限！")
            
        import time
        max_retries = 3
        base_delay = 5
        
        for attempt in range(max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content or ""
                # 提取 JSON 内容（寻找第一个 { 和最后一个 }）
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    content = content[start_idx:end_idx+1]
                
                return json.loads(content)
            except Exception as e:
                error_msg = str(e).lower()
                if ("429" in error_msg or "rate limit" in error_msg) and attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    print(f"  [重试] 遇到 429 频率限制，等待 {delay} 秒后重试 (第 {attempt + 1}/{max_retries} 次)...")
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"OpenAI API 结构化调用失败: {e}") from e

    def upload_file(self, file_path: str):
        """上传文件（占位符，OpenAI Chat 不原生支持文件）"""
        print(f"  [警告] OpenAI 提供商暂不支持直接上传文件 ({file_path})")
        class DummyFile:
            def __init__(self, path):
                self.uri = path
                self.mime_type = "video/mp4"
        return DummyFile(file_path)

    def delete_file(self, file_name: str):
        """删除文件（占位符）"""
        pass

