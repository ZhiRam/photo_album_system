from flask import Flask, jsonify, request, render_template
import os
from datetime import datetime
from PIL import Image as PILImage
import imagehash

# 初始化Flask应用
app = Flask(__name__)

# 路径配置（和你之前的目录完全兼容，不用改）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'upload_imgs')
# 确保上传目录存在，避免创建文件的坑
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 允许的图片格式（保持和之前一致）
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 工具函数1：校验图片格式
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 核心工具函数2：轻量标签生成（替代AI模型，先跑通流程）
def get_simple_tags(img_path):
    """提取图片颜色、亮度、清晰度特征，生成结构化标签"""
    try:
        # 打开图片并处理
        with PILImage.open(img_path) as img:
            # 1. 提取主色调标签
            avg_r, avg_g, avg_b = img.resize((1, 1)).getpixel((0, 0))
            color_tags = []
            if avg_r > 220 and avg_g > 220 and avg_b > 220:
                color_tags.append("白色调")
            elif avg_r > avg_g and avg_r > avg_b:
                color_tags.append("红色调")
            elif avg_g > avg_r and avg_g > avg_b:
                color_tags.append("绿色调")
            elif avg_b > avg_r and avg_b > avg_g:
                color_tags.append("蓝色调")
            elif (avg_r + avg_g) > (2 * avg_b):
                color_tags.append("暖色调")
            else:
                color_tags.append("冷色调")

            # 2. 提取亮度与场景标签
            brightness = (avg_r + avg_g + avg_b) / 3
            scene_tags = []
            if brightness > 180:
                scene_tags.extend(["高亮度", "户外场景"])
            elif 100 <= brightness <= 180:
                scene_tags.extend(["中亮度", "室内场景"])
            else:
                scene_tags.extend(["低亮度", "夜景场景"])

            # 3. 提取清晰度标签
            img_hash = str(imagehash.phash(img))
            clarity_tag = ["清晰"] if len(set(img_hash)) > 10 else ["模糊"]

            # 合并所有标签，去重后返回
            all_tags = list(set(color_tags + scene_tags + clarity_tag))
            return all_tags if all_tags else ["未识别特征"]
    except Exception as e:
        print(f"标签生成异常：{e}")
        return ["特征识别失败"]

# 前端页面路由（渲染上传和展示页面）
@app.route('/')
def index():
    return render_template('index.html')

# 核心API：图片上传+标签生成
@app.route('/api/upload', methods=['POST'])
def upload_img():
    # 校验：是否有文件上传
    if 'file' not in request.files:
        return jsonify({"code": 400, "msg": "未检测到图片文件！"}), 400
    file = request.files['file']
    # 校验：是否选择了文件且格式合法
    if file.filename == '' or not allowed_file(file.filename):
        err_msg = "请选择png/jpg/jpeg/gif格式的图片！"
        return jsonify({"code": 400, "msg": err_msg}), 400

    # 生成唯一文件名（避免重名，沿用你之前的逻辑）
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    ext = os.path.splitext(file.filename)[1]
    new_filename = f"upload_{timestamp}{ext}"
    file_full_path = os.path.join(UPLOAD_DIR, new_filename)

    # 保存图片到本地
    file.save(file_full_path)

    # 核心步骤：生成图片标签
    ai_tags = get_simple_tags(file_full_path)

    # 返回标准化响应（给前端解析）
    return jsonify({
        "code": 200,
        "msg": "图片上传成功，标签生成完成！",
        "data": {
            "img_name": new_filename,
            "img_path": file_full_path.replace('\\', '/'),  # 兼容前端路径
            "upload_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "ai_tags": ai_tags
        }
    })

# 辅助API：获取所有已上传图片（用于页面初始化展示）
@app.route('/api/images', methods=['GET'])
def get_all_images():
    images = []
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            if allowed_file(filename):
                img_path = os.path.join(UPLOAD_DIR, filename)
                # 为已有图片补全标签（页面加载时展示）
                tags = get_simple_tags(img_path)
                images.append({
                    "name": filename,
                    "url": f"/static/upload_imgs/{filename}",
                    "tags": tags,
                    "upload_time": datetime.fromtimestamp(os.path.getctime(img_path)).strftime('%Y-%m-%d %H:%M:%S')
                })
    return jsonify({"code": 200, "data": images})

# 辅助API：删除图片（保持功能完整）
@app.route('/api/delete/<filename>', methods=['DELETE'])
def delete_image(filename):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path) and allowed_file(filename):
        os.remove(file_path)
        return jsonify({"code": 200, "msg": "图片删除成功！"})
    return jsonify({"code": 400, "msg": "图片不存在或格式不合法！"}), 400

# 启动服务（调试模式关闭，避免生产环境风险）
if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000)