import requests
from tkinter import Tk, filedialog

# 1. 固定接口地址（必须和app.py的端口一致）
UPLOAD_URL = "http://127.0.0.1:5000/api/upload"

def select_image():
    """弹出窗口选择图片"""
    root = Tk()
    root.withdraw()  # 隐藏主窗口
    file_path = filedialog.askopenfilename(
        title="选择要上传的图片",
        filetypes=[("图片文件", "*.png *.jpg *.jpeg *.gif"), ("所有文件", "*.*")]
    )
    return file_path

def upload_image(file_path):
    """上传图片到接口"""
    if not file_path:
        print("❌ 未选择任何文件")
        return

    # 2. 构造请求数据（必须用 'file' 作为键，和app.py对应）
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            print(f"📤 正在上传：{file_path}")
            # 发送请求，设置超时防止卡死
            response = requests.post(UPLOAD_URL, files=files, timeout=10)
            
            # 3. 关键调试：打印原始响应
            print(f"\n📜 服务端原始响应状态码：{response.status_code}")
            print(f"📜 服务端原始响应内容：{response.text[:500]}...")  # 只显示前500字符
            
            # 4. 尝试解析JSON
            try:
                result = response.json()
                print(f"\n✅ 接口返回结果：")
                print(f"   状态码：{result.get('code')}")
                print(f"   消息：{result.get('msg')}")
                if result.get('data'):
                    print(f"   图片路径：{result.get('data').get('img_path')}")
            except Exception as e:
                print(f"\n❌ JSON解析失败（原因：{e}）")
                print(f"   说明：服务端返回了非JSON内容，通常是因为服务端报错了。")
                
    except FileNotFoundError:
        print(f"❌ 文件不存在：{file_path}")
    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败！请检查 Flask 服务是否在 http://127.0.0.1:5000 运行。")
    except Exception as e:
        print(f"❌ 上传失败，未知错误：{str(e)}")

if __name__ == "__main__":
    print("=== 图片上传测试工具 ===")
    img_path = select_image()
    upload_image(img_path)