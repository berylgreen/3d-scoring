"""
OpenAI Provider 实现
支持 OpenAI 官方 API 以及兼容 OpenAI 协议的第三方服务 (如代理、Ollama)
"""

from typing import Iterator

from openai import OpenAI

from core.base_llm import BaseLLM
from core.logger import logger


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
        client_kwargs = {
            "api_key": api_key,
            "default_headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        }
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
        user_content = [{"type": "text", "text": schema_prompt}]
        
        if files:
            import base64
            import mimetypes
            import os
            for file_item in files:
                file_path = file_item if isinstance(file_item, str) else getattr(file_item, 'uri', None)
                if not file_path or not os.path.exists(file_path):
                    continue
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ['.jpg', '.jpeg']:
                        mime_type = "image/jpeg"
                    elif ext == '.png':
                        mime_type = "image/png"
                    else:
                        mime_type = "image/jpeg"
                
                if mime_type.startswith("image/"):
                    try:
                        with open(file_path, "rb") as image_file:
                            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{encoded_string}"
                            }
                        })
                    except Exception as e:
                        logger.error(f"  [错误] 读取图片失败: {file_path} ({e})")
                else:
                    logger.warning(f"  [警告] 当前配置的 OpenAI 提供商不支持非图片文件直接上传: {file_path}")

        messages.append({"role": "user", "content": user_content})
            
        import time
        import sys
        max_retries = 2
        base_delay = 5
        use_json_object = True
        
        for attempt in range(max_retries + 1):
            try:
                kwargs = {
                    "model": self.model_name,
                    "messages": messages,
                }
                if use_json_object:
                    kwargs["response_format"] = {"type": "json_object"}
                    
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                # 提取 JSON 内容（寻找第一个 { 和最后一个 }）
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    content = content[start_idx:end_idx+1]
                
                return json.loads(content)
            except Exception as e:
                error_msg = str(e).lower()
                if ("429" in error_msg or "rate limit" in error_msg):
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.info(f"  [重试] 遇到 429 频率限制，等待 {delay} 秒后重试 (第 {attempt + 1}/{max_retries} 次)...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"\n  [!] 严重错误：已到达大模型使用限额，且重试后依然受限。程序即将退出。")
                        sys.exit(1)
                elif use_json_object and ("400" in error_msg or "response_format" in error_msg or "not supported" in error_msg):
                    if attempt < max_retries:
                        logger.warning(f"  [警告] API 可能不支持 response_format={{'type': 'json_object'}}，尝试降级为普通文本模式重试...")
                        use_json_object = False
                        continue
                    else:
                        raise RuntimeError(f"OpenAI API 结构化调用失败(尝试降级失败): {e}") from e
                else:
                    raise RuntimeError(f"OpenAI API 结构化调用失败: {e}") from e

    def upload_file(self, file_path: str, display_name: str = None):
        """上传文件（OpenAI Chat 不原生支持文件对象上传，此处直接返回路径供生成时进行 Base64 编码）"""
        return file_path

    def delete_file(self, file_name: str):
        """删除文件（占位符）"""
        pass

