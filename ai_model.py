import requests
import base64
import os
import time
from typing import List

# -------------------------- 1. 配置区域（请确认这里的密钥正确） --------------------------
API_KEY = "6mryn6wkKkSgcTImmBBGqAUw"       # 你的百度API Key
SECRET_KEY = "b0ph8AyhqmrWI5VwMoHcbyW4GsknAFO9" # 你的百度Secret Key

# 百度AI接口地址
BAIDU_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
BAIDU_GENERAL_URL = "https://aip.baidubce.com/rest/2.0/image-classify/v2/advanced_general"  # 通用识别（识别万物）
BAIDU_BODY_URL = "https://aip.baidubce.com/rest/2.0/image-classify/v1/body_analysis"        # 人像识别（补充人像）

# 运行参数
TOKEN_CACHE_DURATION = 3600  # Token缓存1小时
CONFIDENCE_THRESHOLD = 0.3   # 置信度阈值（调低以获取更多结果）
REQUEST_TIMEOUT = 15         # 超时时间
RETRY_TIMES = 2              # 失败重试次数

# -------------------------- 2. 全局缓存与异常类 --------------------------
_token_cache = {
    "token": None,
    "expire_time": 0
}

class AIModelError(Exception):
    """自定义异常，用于捕获AI接口错误"""
    pass

# -------------------------- 3. 工具函数 --------------------------
def _get_baidu_token() -> str:
    """获取百度AI Token，带缓存"""
    global _token_cache
    current_time = time.time()

    # 检查缓存是否有效
    if _token_cache["token"] and current_time < _token_cache["expire_time"]:
        return _token_cache["token"]

    # 缓存失效，重新请求
    try:
        response = requests.post(
            BAIDU_TOKEN_URL,
            params={
                "grant_type": "client_credentials",
                "client_id": API_KEY,
                "client_secret": SECRET_KEY
            },
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        token_data = response.json()

        if "access_token" not in token_data:
            raise AIModelError(f"获取Token失败: {token_data}")
        
        # 更新缓存
        _token_cache["token"] = token_data["access_token"]
        _token_cache["expire_time"] = current_time + TOKEN_CACHE_DURATION
        return _token_cache["token"]
    except Exception as e:
        raise AIModelError(f"网络或密钥错误: {str(e)}")

def _call_baidu_api(url: str, img_base64: str, token: str) -> dict:
    """通用的百度API调用函数，带重试机制"""
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"image": img_base64}

    for retry in range(RETRY_TIMES + 1):
        try:
            full_url = f"{url}?access_token={token}"
            response = requests.post(full_url, data=data, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()  # 抛出HTTP错误
            return response.json()
        except Exception as e:
            if retry >= RETRY_TIMES:
                raise AIModelError(f"接口调用失败（已重试{RETRY_TIMES}次）: {str(e)}")
            time.sleep(0.5)  # 重试前等待

# -------------------------- 4. 核心识别函数 --------------------------
def generate_img_tags(img_path: str) -> List[str]:
    """
    升级版全场景识别函数
    逻辑：先通用识别 -> 过滤无效标签 -> 若无人像且检测到人，则补充"人像"标签
    """
    # 1. 基础校验
    if not os.path.exists(img_path):
        print(f"错误：图片文件不存在 - {img_path}")
        return ["未识别"]

    # 2. 读取并编码图片
    try:
        file_size = os.path.getsize(img_path)
        if file_size > 4 * 1024 * 1024:  # 限制4MB以内
            print(f"错误：图片过大 ({file_size/1024/1024:.1f}MB)")
            return ["未识别"]
        
        with open(img_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"错误：读取图片失败 - {str(e)}")
        return ["未识别"]

    # 3. AI识别主逻辑
    try:
        token = _get_baidu_token()
        final_tags = []

        # --- 第一阶段：通用识别（识别万物） ---
        general_result = _call_baidu_api(BAIDU_GENERAL_URL, img_base64, token)
        if "result" in general_result and general_result["result"]:
            # 过滤低置信度结果
            valid_items = [item for item in general_result["result"] if item.get("score", 0) >= CONFIDENCE_THRESHOLD]
            
            # 定义需要过滤的"垃圾标签"（局部、无意义的词）
            BAD_TAGS = {"手", "脚", "手指", "脚趾", "指甲", "皮肤", "头发丝"}
            # 提取标签并过滤
            general_tags = [item["keyword"] for item in valid_items if item["keyword"] not in BAD_TAGS]
            
            # 去重（忽略大小写）并取前3个最相关的
            unique_general_tags = list({tag.lower(): tag for tag in general_tags}.values())[:3]
            final_tags.extend(unique_general_tags)

        # --- 第二阶段：人像补充（如果通用识别里没人像，就调用人像接口） ---
        # 检查当前结果里是否已经包含人像相关词汇
        has_person = any(tag in {"人像", "人物", "美女", "帅哥", "人"} for tag in final_tags)
        if not has_person:
            try:
                body_result = _call_baidu_api(BAIDU_BODY_URL, img_base64, token)
                # 如果检测到人数大于0，补充"人像"标签
                if body_result.get("person_num", 0) > 0:
                    final_tags.append("人像")
            except Exception as e:
                # 人像接口失败不影响整体流程，静默忽略
                pass

        # 4. 最终结果处理
        if final_tags:
            return final_tags
        else:
            return ["未识别"]

    except AIModelError as e:
        print(f"AI识别核心错误: {str(e)}")
        return ["未识别"]

# -------------------------- 5. 本地测试入口 --------------------------
if __name__ == "__main__":
    test_path = input("请输入测试图片的绝对路径: ").strip('"')
    start = time.time()
    tags = generate_img_tags(test_path)
    print(f"\n识别耗时: {time.time() - start:.2f} 秒")
    print(f"最终标签: {tags}")