"""
Gemini Provider 实现 (使用新版 google-genai 库)
支持 Google Gemini API 以及反向代理
支持大文件上传与多 API Key 自动限流切换
"""

import json
import time
import os
from typing import Iterator

from google import genai
from google.genai import types

from core.base_llm import BaseLLM


class AllQuotasExceededError(Exception):
    """所有 API Key 限额均已超出"""
    pass


class QuotaExceededError(Exception):
    """单个 API Key 限额超出异常"""
    pass


class GeminiProvider(BaseLLM):
    """
    Google Gemini API 客户端封装 (新版 google-genai 库)
    
    支持:
    - Gemini 官方 API
    - 通过 base_url 指定反向代理地址
    - 多 API Key 限流自动切换
    - 多模态文件上传
    - 结构化 JSON 生成
    """

    def __init__(
        self,
        api_key: str | list[str],
        model_name: str,
        base_url: str | None = None
    ):
        """
        初始化 Gemini Provider
        
        Args:
            api_key: API 密钥（可传列表用于切换）
            model_name: 模型名称 (如 "gemini-2.5-flash")
            base_url: 自定义 API 地址 (可选，用于代理)
        """
        super().__init__(api_key, model_name, base_url)
        
        self._current_key_index = 0
        self._exhausted_keys = set()
        
        if not self.api_keys or all(k == "YOUR_API_KEY_HERE" for k in self.api_keys):
            raise ValueError("请提供有效的 API Key")
            
        # 过滤无效 key
        self.api_keys = [k for k in self.api_keys if k and k != "YOUR_API_KEY_HERE"]
        if not self.api_keys:
            raise ValueError("没有可用的 API Key")
        
        self.client = self._create_client()

    def _create_client(self) -> genai.Client:
        """使用当前 key 创建客户端"""
        current_key = self.api_keys[self._current_key_index]
        if self.base_url:
            return genai.Client(
                api_key=current_key,
                http_options=types.HttpOptions(base_url=self.base_url)
            )
        else:
            return genai.Client(api_key=current_key)

    def _switch_to_next_key(self) -> bool:
        """切换到下一个可用的 API Key"""
        self._exhausted_keys.add(self._current_key_index)
        for i in range(len(self.api_keys)):
            if i not in self._exhausted_keys:
                self._current_key_index = i
                self.api_key = self.api_keys[i]  # 同步更新基类属性
                self.client = self._create_client()
                print(f"\n  [切换] 切换到 API Key #{i+1}")
                return True
        return False

    def _is_quota_error(self, e: Exception) -> bool:
        error_str = str(e).lower()
        return any(keyword in error_str for keyword in [
            "quota", "rate limit", "resource exhausted", 
            "429", "too many requests", "limit exceeded",
            "503", "unavailable", "high demand", "server error"
        ])

    def _handle_quota_error(self, e: Exception):
        if not self._is_quota_error(e):
            raise e  
        key_num = self._current_key_index + 1
        print(f"\n  [!] API Key #{key_num} 限额已超出: {e}")
        if self._switch_to_next_key():
            raise QuotaExceededError(f"Key #{key_num} 限额超出，已切换")
        else:
            raise AllQuotasExceededError("所有 API Key 均已限额耗尽，请稍后重试或添加更多 Key")

    def generate(self, prompt: str) -> str:
        """简单文本生成，带有重试机制"""
        while True:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text
            except QuotaExceededError:
                continue
            except Exception as e:
                self._handle_quota_error(e)
                raise

    def generate_structured(self, prompt: str, schema: dict, files: list = None, system_instruction: str = None) -> dict:
        """结构化输出，带有重试机制（兼容代理返回非标准JSON的情况）"""
        
        import re
        import time
        import sys
        
        # 兜底防御：有些第三方代理不支持 response_schema，导致返回纯文本
        # 手动将 schema 拼接到 prompt 后面，强制要求 LLM 返回 JSON
        fallback_prompt = (
            prompt + 
            "\n\n【系统要求】请务必且仅返回符合以下 JSON Schema 的纯 JSON 字符串，不要包含任何 Markdown 标记或额外说明：\n" + 
            json.dumps(schema, ensure_ascii=False)
        )
        
        max_retries = 1
        attempt = 0
        
        while True:
            try:
                parts = []
                if files:
                    for f in files:
                        if isinstance(f, types.File):
                            parts.append(types.Part.from_uri(file_uri=f.uri, mime_type=f.mime_type))
                        else:
                            uploaded_file = self.upload_file(f)
                            parts.append(types.Part.from_uri(file_uri=uploaded_file.uri, mime_type=uploaded_file.mime_type))
                            
                parts.append(types.Part.from_text(text=fallback_prompt))
                
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema
                )
                if system_instruction:
                    config.system_instruction = system_instruction
                
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[types.Content(role="user", parts=parts)],
                    config=config
                )
                
                if response.text:
                    text = response.text.strip()
                    # 尝试清理 Markdown json 代码块标记
                    text = re.sub(r"^```(?:json)?\n?(.*?)\n?```$", r"\1", text, flags=re.DOTALL | re.IGNORECASE).strip()
                    # 寻找大括号
                    start_idx = text.find("{")
                    end_idx = text.rfind("}")
                    if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
                        text = text[start_idx:end_idx+1]
                    return json.loads(text)
                else:
                    raise ValueError("模型未返回有效响应")
                    
            except QuotaExceededError:
                print("  [重试] 使用新 Key 重新请求...")
                attempt = 0
                continue
            except json.JSONDecodeError as e:
                print(f"  [!] JSON 解析失败，模型返回内容可能不符合规范: {e}")
                # 抛出异常由上层处理或重试机制处理
                raise ValueError(f"模型返回内容无法解析为 JSON: {response.text}")
            except Exception as e:
                if self._is_quota_error(e):
                    if attempt < max_retries:
                        delay = 5 * (2 ** attempt)
                        print(f"  [重试] 遇到频率限制 (429)，等待 {delay} 秒后重试 (第 {attempt + 1}/{max_retries} 次)...")
                        time.sleep(delay)
                        attempt += 1
                        continue
                    else:
                        try:
                            self._handle_quota_error(e)
                        except QuotaExceededError:
                            print("  [重试] 切换新 Key 后重新请求...")
                            attempt = 0
                            continue
                        except AllQuotasExceededError:
                            print(f"\n  [!] 严重错误：已到达大模型使用限额，且重试后依然受限。程序即将退出。")
                            sys.exit(1)
                else:
                    raise

    def upload_file(self, file_path: str, display_name: str = None) -> types.File:
        """上传文件到 Gemini File API"""
        import shutil
        import tempfile
        import uuid
        
        # 复制到临时目录避免中文路径问题
        temp_dir = tempfile.gettempdir()
        ext = os.path.splitext(file_path)[1]
        temp_path = os.path.join(temp_dir, f"llm_upload_{uuid.uuid4().hex[:8]}{ext}")
        
        try:
            shutil.copy2(file_path, temp_path)
            try:
                upload_kwargs = {"file": temp_path}
                if display_name:
                    upload_kwargs["config"] = {"display_name": display_name}
                uploaded_file = self.client.files.upload(**upload_kwargs)
            except KeyError as e:
                if 'Upload URL did not returned' in str(e):
                    raise ValueError(f"代理服务器 ({self.base_url}) 未实现或不支持 Gemini 文件上传接口。无法上传视频文件。请使用原生官方接口，或将评分模式修改为 workload_only。") from e
                raise
            
            while uploaded_file.state == "PROCESSING":
                time.sleep(3)
                uploaded_file = self.client.files.get(name=uploaded_file.name)
            
            if uploaded_file.state == "FAILED":
                raise ValueError(f"文件处理失败: {uploaded_file.state}")
            return uploaded_file
            
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def delete_file(self, file_name: str):
        """删除已上传的文件"""
        try:
            # 如果传入的是 types.File 对象
            name = file_name.name if hasattr(file_name, 'name') else file_name
            self.client.files.delete(name=name)
        except Exception as e:
            print(f"删除文件失败 {file_name}: {e}")

    def chat(self, messages: list[dict]) -> str:
        """多轮对话"""
        while True:
            try:
                gemini_contents = self._convert_messages(messages)
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=gemini_contents
                )
                return response.text
            except QuotaExceededError:
                continue
            except Exception as e:
                self._handle_quota_error(e)
                raise

    def stream_chat(self, messages: list[dict]) -> Iterator[str]:
        """流式对话输出"""
        # 注意: 这里的重试比较复杂，因为可能是流中断。这里只处理初始调用的配额错误
        while True:
            try:
                gemini_contents = self._convert_messages(messages)
                response = self.client.models.generate_content_stream(
                    model=self.model_name,
                    contents=gemini_contents
                )
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                break # 成功完成流，退出循环
            except QuotaExceededError:
                continue
            except Exception as e:
                self._handle_quota_error(e)
                raise

    def _convert_messages(self, messages: list[dict]) -> list[types.Content]:
        gemini_contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "assistant":
                role = "model"
            elif role == "system":
                continue
            gemini_contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=content)]
                )
            )
        return gemini_contents
