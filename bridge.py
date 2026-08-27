import serial
import serial.tools.list_ports
import time
import json
from flask import Flask, render_template, jsonify

# ========== 1. 自动寻找 CH340 串口 ==========
def find_ch340_port():
    """自动查找 CH340 对应的串口"""
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        # 查找描述中包含 CH340 或 USB-SERIAL 的端口
        if 'CH340' in p.description or 'USB-SERIAL' in p.description:
            print(f"✅ 找到 CH340 设备: {p.device} ({p.description})")
            return p.device
    return None

# ========== 2. 初始化 Flask 应用 ==========
app = Flask(__name__)

# 全局变量，用于存储最新的串口数据
latest_data = {
    "line": "A",
    "step": "IDLE",
    "motor": 0,
    "sensor_ok": 1,
    "ts": 0
}

# ========== 3. 串口读取线程 ==========
def serial_reader():
    global latest_data
    port_name = find_ch340_port()
    
    if not port_name:
        print("❌ 错误：未找到 CH340 设备！请检查 USB 线是否插好。")
        return

    try:
        ser = serial.Serial(port_name, 115200, timeout=1)
        print(f"✅ 串口 {port_name} @ 115200 打开成功！")
        
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"📥 收到数据: {line}")  # 打印到控制台，方便调试
                    try:
                        # 尝试解析 JSON
                        data = json.loads(line)
                        latest_data = data  # 更新全局数据
                    except json.JSONDecodeError:
                        print(f"⚠️ JSON 解析失败: {line}")
            time.sleep(0.01)  # 稍微延迟，防止 CPU 占用过高
            
    except Exception as e:
        print(f"❌ 串口打开失败: {e}")

# ========== 4. 网页路由 ==========
@app.route('/')
def index():
    """主页面，直接返回 HTML 字符串（避免文件找不到的问题）"""
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>产线 A · 实时状态看板</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; padding: 20px; }
            .header { text-align: center; color: #333; margin-bottom: 20px; }
            .card-container { display: flex; gap: 20px; flex-wrap: wrap; justify-content: center; }
            .card { 
                background: white; 
                border-radius: 8px; 
                padding: 20px; 
                box-shadow: 0 2px 8px rgba(0,0,0,0.1); 
                min-width: 180px; 
                text-align: center;
                border-left: 4px solid #1890ff;
            }
            .label { font-size: 14px; color: #666; margin-bottom: 8px; }
            .value { font-size: 18px; font-weight: bold; color: #333; }
            .warning { color: #ff4d4f; }
            .success { color: #52c41a; }
            h1 { color: #1890ff; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏭 产线 A · 实时状态看板</h1>
        </div>
        <div class="card-container">
            <div class="card">
                <div class="label">当前工序</div>
                <div class="value" id="step">IDLE</div>
            </div>
            <div class="card">
                <div class="label">主轴电机(DO)</div>
                <div class="value" id="motor">启动</div>
            </div>
            <div class="card">
                <div class="label">检测结果(AI)</div>
                <div class="value" id="sensor">待检测</div>
            </div>
            <div class="card">
                <div class="label">时间戳(ms)</div>
                <div class="value" id="ts">0</div>
            </div>
        </div>

        <!-- 自动刷新脚本 -->
        <script>
            function updatePage() {
                fetch('/data')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('step').innerText = data.step || 'IDLE';
                        document.getElementById('motor').innerText = data.motor == 1 ? '启动' : '停止';
                        document.getElementById('sensor').innerText = data.sensor_ok == 1 ? '✅ 良品' : '<span class=\"warning\">⚠️ 不良品</span>';
                        document.getElementById('sensor').innerHTML = data.sensor_ok == 1 ? '✅ 良品' : '<span class=\"warning\">⚠️ 不良品</span>';
                        document.getElementById('ts').innerText = data.ts || 0;
                    })
                    .catch(error => console.log('获取数据失败:', error));
            }

            // 每 500 毫秒刷新一次
            setInterval(updatePage, 500);
            
            // 页面加载时也刷新一次
            window.onload = updatePage;
        </script>
    </body>
    </html>
    """

@app.route('/data')
def get_data():
    """API 接口：供网页前端获取最新数据"""
    return jsonify(latest_data)

# ========== 5. 主程序入口 ==========
if __name__ == '__main__':
    # 启动串口读取线程（后台运行）
    import threading
    threading.Thread(target=serial_reader, daemon=True).start()
    
    # 启动 Flask 服务
    print("🌐 网页地址：http://localhost:8000")
    print("📡 桥接服务已启动，等待数据...")
    app.run(host='0.0.0.0', port=8000, debug=False)
