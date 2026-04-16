import langfuse
import os
import time

# 1. 强行在脚本里写死，不信它读不到
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-a4d72ee1-523c-4d6a-be56-0b808a80c992"
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-13a30be1-3558-4182-96da-62bc3462d073"
os.environ["LANGFUSE_HOST"] = "https://us.cloud.langfuse.com"

print(f"DEBUG: 正在使用的 langfuse 包路径: {langfuse.__file__}")

# 使用最原始的初始化方式
try:
    # 实例化客户端
    client = langfuse.Langfuse()
    
    # 绕过 .trace 属性，直接用底层方法（如果版本极老或极新，这种方式最稳）
    print("🚀 尝试底层调用...")
    
    # 某些版本中，它是作为一个方法存在的
    trace = client.trace(name="ultra-final-test")
    
    trace.generation(
        name="test-logic",
        input="Last try",
        output="Please work"
    )

    client.flush()
    time.sleep(2)
    print("✅ 如果你看到这行没报错，说明底层通了！去官网刷新。")

except Exception as e:
    print(f"❌ 依然报错: {type(e).__name__} - {e}")
    print("\n🔍 诊断信息：")
    print(f"Langfuse 包含的所有属性: {dir(langfuse.Langfuse)}")