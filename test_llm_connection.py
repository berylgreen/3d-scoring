import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)

# 把当前项目目录加入到系统路径，以便可以导入项目自身的类
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from providers.gemini_provider import GeminiProvider
except ImportError as e:
    print(f"导入 GeminiProvider 失败: {e}")
    sys.exit(1)

api_keys = [k.strip() for k in os.getenv("LLM_API_KEYS", "").split(",") if k.strip()]
model = os.getenv("LLM_MODEL")

print(f"🚀 初始化 原生 Gemini 测试...")
print(f"📦 供应商: gemini")
print(f"🎯 模型: {model}")
print(f"🔑 识别到 {len(api_keys)} 个 API Key, 当前使用: {api_keys[0][:10]}...")

try:
    # 直接使用你项目里的原生 GeminiProvider
    provider = GeminiProvider(
        api_key=api_keys,
        model_name=model
    )
    
    print("⏳ 正在发送原生协议文本请求...")
    response = provider.generate("你好，请只回复这一句话：'原生 Gemini 协议连通测试成功！支持视频上传！'")
    
    print("✅ 成功! 模型回复如下:")
    print("--------------------------------------------------")
    print(response)
    print("--------------------------------------------------")
except Exception as e:
    print("❌ 测试失败!")
    print(f"错误信息: {str(e)}")
