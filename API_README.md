# Fooocus REST API - 使用指南

## 📋 概述

本 fork 在原始 Fooocus 基础上添加了 REST API 支持，提供简单的 HTTP 接口进行图像生成。

## ✨ 新增功能

- **REST API 端点**：标准 HTTP 接口，支持任何语言调用
- **简化参数**：只需 7 个核心参数（vs Gradio 的 152 个）
- **自动文档**：Swagger UI 自动生成
- **完全兼容**：不影响原有功能，可选启用

## 🚀 快速开始

### 1. 启动 Fooocus with API

```bash

# 基本启动（API 监听 127.0.0.1:7866）
python entry_with_update.py --listen --enable-api

# 自定义端口和地址
python entry_with_update.py --listen --enable-api --api-host 0.0.0.0 --api-port 7866
```

### 2. 访问 API 文档

启动后访问：
- **Swagger UI**: `http://127.0.0.1:7866/docs`
- **ReDoc**: `http://127.0.0.1:7866/redoc`

## 📡 API 端点

### 1. 健康检查

```bash
curl http://127.0.0.1:7866/api/health
```

**响应**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000000"
}
```

### 2. 列出模型

```bash
curl http://127.0.0.1:7866/api/models
```

**响应**:
```json
{
  "models": [
    {"name": "juggernautXL_v8Rundiffusion.safetensors", "type": "base"},
    {"name": "sd_xl_offset_example-lora_1.0.safetensors", "type": "lora"}
  ]
}
```

### 3. 列出样式

```bash
curl http://127.0.0.1:7866/api/styles
```

### 4. 系统状态

```bash
curl http://127.0.0.1:7866/api/status
```

**响应**:
```json
{
  "status": "idle",
  "version": "2.5.5",
  "uptime": 3600.123,
  "current_task": null
}
```

### 5. ⭐ 生成图像（核心端点）

```bash
curl -X POST http://127.0.0.1:7866/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a red apple on a wooden table",
    "negative_prompt": "",
    "style": "Fooocus V2",
    "aspect_ratio": "1024×1024",
    "steps": 20,
    "seed": -1,
    "performance": "Speed"
  }'
```

**响应**:
```json
{
  "success": true,
  "images": ["data:image/png;base64,iVBORw0KGgo..."],
  "metadata": {
    "prompt": "a red apple on a wooden table",
    "style": "Fooocus V2",
    "seed": 1234567890,
    "steps": 20,
    "processing_time": 12.34
  },
  "processing_time": 12.34
}
```

#### 参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prompt` | string | ✅ | - | 正向提示词 |
| `negative_prompt` | string | ❌ | "" | 负向提示词 |
| `style` | string | ❌ | "Fooocus V2" | 样式名称 |
| `aspect_ratio` | string | ❌ | "1024×1024" | 宽高比（使用 × 符号）|
| `steps` | integer | ❌ | 20 | 生成步数 (1-200) |
| `seed` | integer | ❌ | -1 | 随机种子 (-1 为随机) |
| `performance` | string | ❌ | "Speed" | 性能模式 ("Speed"/"Quality") |
| `output_format` | string | ❌ | "png" | 输出格式 ("png"/"jpg") |

## 💻 Python 客户端示例

### 基本用法

```python
import requests
import base64

API_URL = "http://127.0.0.1:7866"

def generate_image(prompt, output_path="output.png"):
    """Generate image using Fooocus REST API"""
    
    response = requests.post(f"{API_URL}/api/generate", json={
        "prompt": prompt,
        "style": "Fooocus V2",
        "steps": 20
    })
    
    result = response.json()
    
    if result["success"]:
        # Save first image
        img_b64 = result["images"][0]
        img_data = base64.b64decode(img_b64.split(",")[1])
        
        with open(output_path, "wb") as f:
            f.write(img_data)
        
        print(f"✅ Image saved to {output_path}")
        print(f"   Processing time: {result['processing_time']:.2f}s")
        return True
    else:
        print(f"❌ Error: {result['error']}")
        return False

# 使用示例
generate_image("a beautiful sunset over mountains", "sunset.png")
```

### 批量生成

```python
import requests
import base64
from pathlib import Path

API_URL = "http://127.0.0.1:7866"

prompts = [
    "a red apple on a table",
    "a cat sitting on a chair",
    "mountain landscape at sunset"
]

for i, prompt in enumerate(prompts):
    print(f"[{i+1}/{len(prompts)}] Generating: {prompt[:30]}...")
    
    response = requests.post(f"{API_URL}/api/generate", json={
        "prompt": prompt,
        "seed": i + 1000  # 固定种子以便复现
    })
    
    result = response.json()
    
    if result["success"]:
        # 保存图像
        img_b64 = result["images"][0]
        img_data = base64.b64decode(img_b64.split(",")[1])
        
        output_file = Path(f"output_{i}.png")
        with open(output_file, "wb") as f:
            f.write(img_data)
        
        print(f"   ✓ Saved to {output_file} ({result['processing_time']:.1f}s)")
    else:
        print(f"   ✗ Failed: {result['error']}")
```

### 检查系统状态

```python
import requests

def check_status():
    status = requests.get("http://127.0.0.1:7866/api/status").json()
    
    print(f"Status: {status['status']}")
    print(f"Version: {status['version']}")
    print(f"Uptime: {status['uptime']:.1f}s")
    
    if status["current_task"]:
        print(f"Current task: {status['current_task']}")

check_status()
```

## 🌐 其他语言示例

### JavaScript / Node.js

```javascript
const axios = require('axios');

async function generateImage(prompt) {
  try {
    const response = await axios.post('http://127.0.0.1:7866/api/generate', {
      prompt: prompt,
      style: 'Fooocus V2',
      steps: 20
    });
    
    if (response.data.success) {
      // 保存 base64 图像到文件
      const fs = require('fs');
      const base64Data = response.data.images[0].replace(/^data:image\/\w+;base64,/, '');
      fs.writeFileSync('output.png', base64Data, 'base64');
      
      console.log(`✅ Image generated in ${response.data.processing_time.toFixed(2)}s`);
    }
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

generateImage('a beautiful sunset');
```

### cURL 脚本

```bash
#!/bin/bash

# generate.sh - 批量生成图像

PROMPTS=(
    "a red apple"
    "a blue sky"
    "green forest"
)

for i in "${!PROMPTS[@]}"; do
    PROMPT="${PROMPTS[$i]}"
    OUTPUT="image_${i}.png"
    
    echo "Generating: $PROMPT..."
    
    RESPONSE=$(curl -s -X POST http://127.0.0.1:7866/api/generate \
        -H "Content-Type: application/json" \
        -d "{\"prompt\": \"$PROMPT\", \"steps\": 20}")
    
    SUCCESS=$(echo $RESPONSE | jq '.success')
    
    if [ "$SUCCESS" = "true" ]; then
        echo $RESPONSE | jq -r '.images[0]' | sed 's/^data:image\/png;base64,//' | base64 -d > "$OUTPUT"
        echo "✅ Saved to $OUTPUT"
    else
        ERROR=$(echo $RESPONSE | jq -r '.error')
        echo "❌ Error: $ERROR"
    fi
done
```

## 🔧 高级配置

### 自定义参数

```bash
# 高质量模式，更多步数
curl -X POST http://127.0.0.1:7866/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "detailed portrait of a woman",
    "negative_prompt": "blurry, low quality",
    "style": "Fooocus Photograph",
    "aspect_ratio": "896×1152",
    "steps": 40,
    "performance": "Quality",
    "seed": 42
  }'
```

### 错误处理

```python
try:
    response = requests.post(f"{API_URL}/api/generate", json={...})
    response.raise_for_status()  # 检查 HTTP 错误
    
    result = response.json()
    
    if not result["success"]:
        raise Exception(result.get("error", "Unknown error"))
        
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to Fooocus API")
except requests.exceptions.Timeout:
    print("⏱️ Request timeout")
except Exception as e:
    print(f"❌ Error: {e}")
```

## 📊 与其他方案对比

| 特性 | Gradio Client | WebSocket | 本 REST API |
|------|---------------|-----------|-------------|
| 参数数量 | 152 个位置参数 | 复杂 JSON | **7 个关键字参数** |
| 易用性 | 困难 | 中等 | **简单** |
| 文档 | 无 | 无 | **Swagger 自动生成** |
| 多语言支持 | 仅 Python | 任何语言 | **任何语言** |
| 调试工具 | 无 | 需要 WS 客户端 | **curl、Postman** |

## 🔒 安全建议

### 生产环境部署

1. **使用反向代理 + HTTPS**
```nginx
server {
    listen 443 ssl;
    server_name fooocus.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location /api/ {
        proxy_pass http://127.0.0.1:7866;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

2. **添加认证**（未来版本将支持）

3. **限制访问**
```bash
# 只允许本地访问
python entry_with_update.py --enable-api --api-host 127.0.0.1

# 允许局域网访问
python entry_with_update.py --enable-api --api-host 192.168.1.100
```

## 🐛 故障排除

### 问题：无法连接到 API

**检查**:
```bash
# 1. 确认 Fooocus 已启动且启用了 API
ps aux | grep fooocus

# 2. 检查端口是否监听
netstat -tlnp | grep 7866

# 3. 测试健康检查
curl http://127.0.0.1:7866/api/health
```

### 问题：生成失败

**可能原因**:
- 模型未加载完成
- GPU 内存不足
- 提示词为空或无效

**解决方法**:
1. 查看 Fooocus 日志中的错误信息
2. 检查 `/api/status` 端点确认系统状态
3. 尝试简化提示词

### 问题：依赖缺失

如果遇到 `ModuleNotFoundError: No module named 'fastapi'`：

```bash
pip install fastapi uvicorn pydantic
```

## 📝 更新日志

### v1.0.0 (2024-01-15)
- ✅ 初始版本
- ✅ 实现 `/api/generate` 核心端点
- ✅ 实现 `/api/health`, `/api/models`, `/api/styles`, `/api/status` 辅助端点
- ✅ Swagger UI 自动文档
- ✅ 异步任务队列管理

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

与原版 Fooocus 相同的许可证。
