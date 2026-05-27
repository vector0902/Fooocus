# Fooocus 并发处理机制分析

## 1. 原始程序的工作方式

### 1.1 任务队列机制

Fooocus 使用一个简单的列表作为任务队列：

```python
# modules/async_worker.py
async_tasks = []  # 全局任务队列
```

### 1.2 Worker 线程

Fooocus 启动一个后台 worker 线程，循环处理任务：

```python
def worker():
    while True:
        time.sleep(0.01)  # 10ms 轮询间隔
        if len(async_tasks) > 0:
            task = async_tasks.pop(0)  # FIFO 取出任务
            try:
                handler(task)  # 同步处理任务
                ...
```

**关键点：**
- Worker 是单线程的
- 任务按顺序一个一个处理（FIFO）
- `handler(task)` 是同步阻塞的，直到图像生成完成
- 没有内置的并发处理能力

### 1.3 WebUI 如何处理用户请求

当用户在 WebUI 点击生成按钮时：

1. Gradio 接收请求
2. 创建一个 `AsyncTask` 对象
3. 将任务 `append` 到 `async_tasks` 队列
4. 立即返回，不等待任务完成
5. 通过 WebSocket/Gradio 的 yield 机制推送进度更新

```python
# 伪代码流程
def generate_button_click(...):
    task = AsyncTask(args)
    async_tasks.append(task)
    # 立即返回，不等待
    
# 同时，worker 线程在处理：
def worker():
    while True:
        if len(async_tasks) > 0:
            task = async_tasks.pop(0)
            handler(task)  # 阻塞直到完成
```

### 1.4 原始程序是否支持队列？

**支持，但有条件：**
- 支持多个任务排队等待
- 但不支持并行处理（同一时间只有一个任务在运行）
- WebUI 通过异步返回 + 进度推送实现"非阻塞"体验

## 2. 当前 API 的问题

### 2.1 问题描述

当前的 REST API 实现使用了全局锁：

```python
current_task: Optional[str] = None
task_lock = asyncio.Lock()

@app.post("/v1/generation/text-to-image")
async def generate(...):
    async with task_lock:
        if current_task:
            raise HTTPException(status_code=409, detail="Another task is already running")
        current_task = ...
    ...
```

**问题：**
- 如果任务正在运行，新请求直接返回 409 错误
- 没有排队机制
- 测试脚本需要手动处理重试

### 2.2 与原始程序的差异

| 特性       | 原始 WebUI               | 当前 REST API          |
|------------|--------------------------|------------------------|
| 任务排队   | 支持（async_tasks 列表） | 不支持（直接返回 409） |
| 并发处理   | 不支持（单 worker）      | 不支持（单任务锁）     |
| 客户端体验 | 异步，可排队             | 同步，需客户端重试     |
| 进度反馈   | WebSocket 实时推送       | 无（等待最终结果）     |

## 3. 解决方案建议

### 方案 1：添加任务队列（推荐）

让 API 像原始 WebUI 一样支持任务排队：

```python
# 使用 Fooocus 原生的 async_tasks 队列
import modules.async_worker as worker

task_future = asyncio.Future()

task = worker.AsyncTask(args)
task.future = task_future  # 绑定 future 用于等待结果
worker.async_tasks.append(task)

# 等待任务完成
result = await task_future
```

**优点：**
- 符合原始程序设计
- 任务按顺序处理
- 客户端可以同步等待结果

**缺点：**
- 需要修改 async_worker.py 支持 future 回调
- 或者轮询检查任务状态

### 方案 2：客户端轮询

保持 API 简单，让客户端处理排队：

```python
# 客户端代码
while True:
    response = requests.post(...)
    if response.status_code == 409:
        time.sleep(1)  # 等待后重试
        continue
    break
```

**优点：**
- API 实现简单
- 无需修改 Fooocus 核心代码

**缺点：**
- 每个客户端都要实现重试逻辑
- 测试脚本需要修改

### 方案 3：添加排队端点

添加独立的排队和查询接口：

```python
POST /v1/generation/queue     # 提交任务，返回 task_id
GET  /v1/generation/status/{task_id}  # 查询状态
GET  /v1/generation/result/{task_id}  # 获取结果
```

**优点：**
- 真正的异步 API
- 支持长时间运行的任务

**缺点：**
- 实现复杂
- 需要任务存储机制
- 测试脚本需要大幅修改

## 4. 推荐方案

**推荐方案 1（添加任务队列）**，原因：

1. 符合 Fooocus 原始设计（使用 async_tasks 队列）
2. 对测试脚本透明（同步调用即可）
3. 实现相对简单

具体实现思路：
- 修改 API 端点，将任务添加到 `async_tasks` 队列
- 使用 `asyncio.Event` 或 `Future` 等待任务完成
- 任务完成后返回结果

这样可以实现：
- 客户端同步调用（POST 请求等待返回）
- 服务器端任务排队（使用 Fooocus 原生队列）
- 单任务顺序执行（符合 Fooocus 设计）
