"""
Fooocus REST API Server
Provides simple REST endpoints for image generation.
"""

import os
import sys
import json
import time
import base64
import asyncio
import socket
import platform
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel, Field
    import uvicorn
except ImportError:
    print("[API] Installing dependencies: fastapi uvicorn pydantic")
    os.system("pip install fastapi uvicorn pydantic -q")
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    import uvicorn

app = FastAPI(
    title="Fooocus REST API",
    description="Simple REST API for Fooocus image generation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# File browser configuration
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)  # Ensure output directory exists

# Mount static files for direct file access (e.g., /files/output/image.png)
app.mount("/files", StaticFiles(directory=str(OUTPUT_DIR)), name="files")


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Text prompt for generation")
    negative_prompt: str = Field("", description="Negative prompt")
    style: str = Field("Fooocus V2", description="Style selection")
    aspect_ratio: str = Field("1024*1024", description="Image resolution as WIDTH*HEIGHT (e.g., 1024*1024, 1152*896)")
    steps: int = Field(20, ge=1, le=200, description="Number of steps")
    seed: int = Field(-1, description="Random seed (-1 for random)")
    performance: str = Field("Speed", enum=["Speed", "Quality"], description="Performance mode")
    output_format: str = Field("png", enum=["png", "jpg"], description="Output format")
    base_model_name: Optional[str] = Field(None, description="Base model name to use")


class GenerateResponse(BaseModel):
    success: bool
    images: List[str] = []
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None
    processing_time: float = 0.0


class ModelInfo(BaseModel):
    name: str
    type: str


class StatusResponse(BaseModel):
    status: str
    version: str
    uptime: float
    current_task: Optional[str] = None


start_time = time.time()  # Fooocus/API instance start time
current_task: Optional[str] = None
task_lock = asyncio.Lock()


def get_system_uptime() -> float:
    """Get system uptime in seconds using system command"""
    try:
        import subprocess
        result = subprocess.run(['cat', '/proc/uptime'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            uptime_seconds = float(result.stdout.split()[0])
            return uptime_seconds
    except Exception as e:
        print(f"Failed to get system uptime: {e}")
    
    # Fallback: use time since boot from /proc/stat
    try:
        with open('/proc/stat', 'r') as f:
            for line in f:
                if line.startswith('btime'):
                    boot_time = float(line.split()[1])
                    return time.time() - boot_time
    except:
        pass
    
    return 0.0

# Optional: Set max session duration (in seconds) for temporary instances
# Set to 0 or None to disable countdown
MAX_SESSION_DURATION = 600  # 10 minutes (adjust based on your Cloud Studio limit)


@app.get("/")
async def root():
    """Root endpoint - returns basic API info"""
    return {
        "name": "Fooocus REST API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "generate": "/api/generate",
            "compat": "/v1/generation/text-to-image",
            "files": "/api/files",
            "browser": "/api/browser"
        },
        "docs": "/docs"
    }


@app.api_route("/api/health", methods=["GET", "POST"])
async def health_check(request: Request):
    """Health check endpoint (process alive, no model check)"""
    print(f"[DEBUG] /api/health called with method: {request.method}", flush=True)
    return {"status": "alive", "message": "Process is running", "timestamp": datetime.now().isoformat()}


@app.get("/api/ready")
async def readiness_check():
    """Readiness check endpoint (model loaded)"""
    try:
        import modules.default_pipeline as pipeline
        
        if pipeline.final_unet is None:
            raise HTTPException(
                status_code=503,
                detail="Model not loaded yet (lazy loading mode)"
            )
        
        model_name = "unknown"
        if hasattr(pipeline, 'model_base') and hasattr(pipeline.model_base, 'filename'):
            model_name = pipeline.model_base.filename
        
        return {
            "status": "ready",
            "message": "Model loaded, ready to service",
            "model": model_name,
            "timestamp": datetime.now().isoformat()
        }
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Pipeline module not initialized"
        )


@app.get("/api/models")
async def list_models():
    """List available models"""
    try:
        import modules.config as config
        
        models = []
        
        if hasattr(config, 'model_filenames'):
            for model_name in config.model_filenames:
                models.append(ModelInfo(name=model_name, type="base"))
        
        if hasattr(config, 'lora_filenames'):
            for lora_name in config.lora_filenames:
                models.append(ModelInfo(name=lora_name, type="lora"))
        
        return {"models": [m.dict() for m in models]}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load models: {str(e)}")


@app.get("/api/styles")
async def list_styles():
    """List available styles"""
    try:
        import sdxl_styles
        
        styles = []
        for style in sdxl_styles.styles:
            styles.append({
                "name": style[0],
                "prompt": style[1],
                "negative_prompt": style[2],
            })
        
        return {"styles": styles}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load styles: {str(e)}")


@app.get("/api/status")
async def get_status():
    """Get system status"""
    global current_task, start_time
    
    return StatusResponse(
        status="running" if current_task else "idle",
        version=get_fooocus_version(),
        uptime=time.time() - start_time,  # Fooocus instance uptime
        current_task=current_task
    )


@app.get("/api/uptime")
async def get_system_uptime():
    """
    Get system uptime using system's uptime command.
    
    Returns system uptime information similar to running 'uptime' command.
    """
    import subprocess
    
    # Get system uptime from /proc/uptime (most reliable on Linux)
    try:
        result = subprocess.run(['cat', '/proc/uptime'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            uptime_seconds = float(result.stdout.split()[0])
            
            # Convert to human-readable format
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            seconds = int(uptime_seconds % 60)
            
            uptime_human = f"{days}d {hours}h {minutes}m {seconds}s"
            
            return {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "uptime_seconds": round(uptime_seconds, 1),
                    "uptime_human": uptime_human,
                    "boot_time": datetime.fromtimestamp(time.time() - uptime_seconds).isoformat()
                }
            }
    except Exception as e:
        pass
    
    # Fallback: try uptime command
    try:
        result = subprocess.run(['uptime', '-p'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "uptime_human": result.stdout.strip(),
                    "note": "Parsed from uptime command"
                }
            }
    except Exception as e:
        pass
    
    raise HTTPException(status_code=500, detail="Failed to get system uptime")


@app.get("/api/files")
async def list_files(path: str = ""):
    """
    List files in output directory.
    
    Provides directory browsing similar to `python -m http.server`.
    Usage:
      GET /api/files              - List root of output directory
      GET /api/files?path=subdir  - List specific subdirectory
    """
    try:
        # Security: prevent path traversal attacks
        safe_path = Path(path)
        if safe_path.is_absolute() or ".." in str(safe_path):
            raise HTTPException(status_code=400, detail="Invalid path")
        
        target_dir = OUTPUT_DIR / safe_path
        
        # Validate path exists and is directory
        if not target_dir.exists():
            raise HTTPException(status_code=404, detail="Directory not found")
        
        if not target_dir.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")
        
        # List contents
        items = []
        for item in sorted(target_dir.iterdir()):
            item_info = {
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
                "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                "url": f"/files/{item.relative_to(OUTPUT_DIR)}" if item.is_file() else None
            }
            
            if item.is_dir():
                item_info["url"] = f"/api/files?path={item.relative_to(OUTPUT_DIR)}"
            
            items.append(item_info)
        
        # Calculate parent link
        parent_path = None
        if path:
            parent = Path(path).parent
            parent_path = f"/api/files?path={parent}" if str(parent) != "." else "/api/files"
        
        return {
            "path": str(target_dir),
            "parent": parent_path,
            "items": items,
            "total_files": len([i for i in items if i["type"] == "file"]),
            "total_dirs": len([i for i in items if i["type"] == "directory"]),
            "total_size": sum(i.get("size", 0) or 0 for i in items if i["type"] == "file")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@app.get("/api/browser")
async def file_browser_html():
    """
    Simple HTML interface for browsing output files.
    Access at: http://host:port/api/browser
    """
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Fooocus Output Browser</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f5f5f5; }
        h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        .breadcrumb { margin: 15px 0; font-size: 14px; }
        .breadcrumb a { color: #007bff; text-decoration: none; }
        .breadcrumb a:hover { text-decoration: underline; }
        table { width: 100%; border-collapse: collapse; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        th { background: #007bff; color: white; padding: 12px; text-align: left; cursor: pointer; }
        td { padding: 10px; border-bottom: 1px solid #eee; }
        tr:hover { background: #f8f9fa; }
        .icon { font-size: 20px; margin-right: 8px; }
        .file-link { color: #333; text-decoration: none; display: flex; align-items: center; }
        .file-link:hover { color: #007bff; }
        .size { color: #666; font-size: 13px; }
        .modified { color: #999; font-size: 13px; }
        .nav-btn { padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; }
        .nav-btn:hover { background: #0056b3; }
        .info { margin: 10px 0; color: #666; font-size: 13px; }
        .loading { text-align: center; padding: 40px; color: #999; }
        .error { color: #dc3545; padding: 10px; background: #f8d7da; border-radius: 4px; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>Fooocus Output Browser</h1>
    <div id="app">
        <div class="loading">Loading...</div>
    </div>

    <script>
        const API_BASE = '/api/files';
        let currentPath = '';
        
        async function loadDirectory(path) {
            currentPath = path;
            const url = path ? `${API_BASE}?path=${encodeURIComponent(path)}` : API_BASE;
            
            try {
                const response = await fetch(url);
                const data = await response.json();
                
                if (!response.ok) {
                    document.getElementById('app').innerHTML = `<div class="error">Error: ${data.detail}</div>`;
                    return;
                }
                
                renderFileList(data);
            } catch (error) {
                document.getElementById('app').innerHTML = `<div class="error">Failed to load: ${error.message}</div>`;
            }
        }
        
        function renderFileList(data) {
            const app = document.getElementById('app');
            
            // Breadcrumb navigation
            let breadcrumb = '<div class="breadcrumb">';
            if (data.parent) {
                breadcrumb += `<a href="#" onclick="loadDirectory('${currentPath.includes('/') ? currentPath.substring(0, currentPath.lastIndexOf('/')) : ''}'); return false;">[Parent Directory]</a> / `;
            }
            breadcrumb += `<strong>${data.path}</strong></div>`;
            
            // File table
            let rows = data.items.map(item => `
                <tr>
                    <td>
                        <a href="${item.url}" class="file-link" ${item.type === 'file' ? 'target="_blank"' : `onclick="loadDirectory('${item.url.replace('/api/files?path=', '')}'); return false;"`}>
                            <span class="icon">${item.type === 'directory' ? '&#128193;' : '&#128196;'}</span>
                            ${item.name}
                        </a>
                    </td>
                    <td class="size">${item.type === 'file' ? formatSize(item.size) : '-'}</td>
                    <td class="modified">${formatDate(item.modified)}</td>
                </tr>
            `).join('');
            
            // Info bar
            const info = `
                <div class="info">
                    ${data.total_files} files, ${data.total_dirs} directories | 
                    Total size: ${formatSize(data.total_size)}
                </div>
            `;
            
            app.innerHTML = `
                ${breadcrumb}
                ${info}
                <table>
                    <thead>
                        <tr><th>Name</th><th>Size</th><th>Modified</th></tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            `;
        }
        
        function formatSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        function formatDate(dateStr) {
            const date = new Date(dateStr);
            return date.toLocaleString();
        }
        
        // Load root directory on page load
        loadDirectory('');
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_image(request: GenerateRequest):
    """
    Generate image using Fooocus.
    
    This endpoint provides a simplified interface compared to the full Gradio API.
    Only essential parameters are required; others use sensible defaults.
    Supports task queuing - if a task is running, new tasks will wait in queue.
    """
    start_time = time.time()
    
    # Create a future to wait for task completion
    task_future = asyncio.Future()
    
    async with queue_lock:
        pending_futures.append(task_future)
        queue_position = len(pending_futures)
    
    # Wait for all previous tasks to complete (FIFO queue)
    if queue_position > 1:
        print(f'[API] Task queued at position {queue_position}, waiting...')
        try:
            await asyncio.wait_for(pending_futures[queue_position - 2], timeout=600)
        except asyncio.TimeoutError:
            async with queue_lock:
                if task_future in pending_futures:
                    pending_futures.remove(task_future)
            raise HTTPException(status_code=504, detail="Timeout waiting in queue")
    
    try:
        result = await call_fooocus_generate(request)
        
        processing_time = time.time() - start_time
        
        return GenerateResponse(
            success=True,
            images=result.get("images", []),
            metadata={
                "prompt": request.prompt,
                "style": request.style,
                "seed": result.get("seed", request.seed),
                "steps": request.steps,
                "processing_time": processing_time
            },
            processing_time=processing_time
        )
    
    except Exception as e:
        return GenerateResponse(
            success=False,
            error=str(e),
            processing_time=time.time() - start_time
        )
    
    finally:
        # Mark this task as complete and remove from queue
        if not task_future.done():
            task_future.set_result(True)
        async with queue_lock:
            if task_future in pending_futures:
                pending_futures.remove(task_future)


# Compatibility endpoint for test_local_model.py
class FooocusCompatRequest(BaseModel):
    """Request model compatible with test_local_model.py FooocusTester"""
    prompt: str = Field(..., min_length=1)
    negative_prompt: str = Field("")
    style_selections: List[str] = Field(default=["Fooocus V2"])
    performance_selection: str = Field("Speed")
    aspect_ratios_selection: str = Field("1024*1024")
    image_number: int = Field(1)
    image_seed: int = Field(-1)
    steps: int = Field(20)
    base_model_name: Optional[str] = Field(None, description="Base model name to use")


# Task queue management for concurrent requests
pending_futures: List[asyncio.Future] = []
queue_lock = asyncio.Lock()


@app.post("/v1/generation/text-to-image")
async def generate_text_to_image_compat(request: FooocusCompatRequest):
    """
    Compatibility endpoint for test_local_model.py
    Converts FooocusTester format to internal format and generates image.
    Supports task queuing - if a task is running, new tasks will wait in queue.
    """
    start_time = time.time()
    
    # Create a future to wait for task completion
    task_future = asyncio.Future()
    
    async with queue_lock:
        pending_futures.append(task_future)
        queue_position = len(pending_futures)
    
    # Wait for all previous tasks to complete (FIFO queue)
    if queue_position > 1:
        print(f'[API] Task queued at position {queue_position}, waiting...')
        try:
            await asyncio.wait_for(pending_futures[queue_position - 2], timeout=600)
        except asyncio.TimeoutError:
            async with queue_lock:
                if task_future in pending_futures:
                    pending_futures.remove(task_future)
            raise HTTPException(status_code=504, detail="Timeout waiting in queue")
    
    try:
        import json
        # Log incoming request parameters (pretty print)
        print(f'[API] ====== Received Text-to-Image Request ======')
        print(json.dumps(request.model_dump(), indent=2, ensure_ascii=False))
        print(f'[API] ===========================================')
        
        # Convert to internal format
        internal_request = GenerateRequest(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            style=request.style_selections[0] if request.style_selections else "Fooocus V2",
            aspect_ratio=request.aspect_ratios_selection,
            steps=request.steps,
            seed=request.image_seed,
            performance=request.performance_selection,
            base_model_name=request.base_model_name
        )
        
        result = await call_fooocus_generate(internal_request)
        processing_time = time.time() - start_time
        
        # Return format expected by FooocusTester
        return {
            "images": result.get("images", []),
            "success": True,
            "processing_time": processing_time
        }
    
    except Exception as e:
        processing_time = time.time() - start_time
        return {
            "images": [],
            "success": False,
            "error": str(e),
            "processing_time": processing_time
        }
    
    finally:
        # Mark this task as complete and remove from queue
        if not task_future.done():
            task_future.set_result(True)
        async with queue_lock:
            if task_future in pending_futures:
                pending_futures.remove(task_future)


async def call_fooocus_generate(request: GenerateRequest) -> Dict[str, Any]:
    """Internal function to call Fooocus generation pipeline."""
    try:
        import modules.async_worker as worker
        import modules.config as config
        
        args = build_args_from_request(request)
        async_task = worker.AsyncTask(args)
        
        images = await run_generation_in_thread(async_task)
        
        image_b64_list = []
        for img_path in images:
            if img_path and os.path.exists(img_path):
                with open(img_path, 'rb') as f:
                    img_b64 = base64.b64encode(f.read()).decode('utf-8')
                    image_b64_list.append(f"data:image/png;base64,{img_b64}")
        
        return {
            "images": image_b64_list,
            "seed": async_task.seed
        }
    
    except Exception as e:
        raise RuntimeError(f"Generation failed: {str(e)}")


def build_args_from_request(request: GenerateRequest) -> list:
    """Build Fooocus args list from simplified request."""
    try:
        import modules.config as config
        from modules.util import get_enabled_loras
        
        args = []
        
        # Determine the actual model name to use
        actual_base_model = request.base_model_name if request.base_model_name else (config.default_base_model_name if hasattr(config, 'default_base_model_name') else "juggernautXL_v8Rundiffusion.safetensors")
        
        args.append(False)  # generate_image_grid_for_each_batch
        args.append(request.prompt)
        args.append(request.negative_prompt or "")
        args.append([request.style])
        args.append(request.performance)
        
        # Convert aspect_ratio format: "1024*1024" (API input) -> "1024×1024" (Handler expects Unicode ×)
        aspect_ratio_for_handler = request.aspect_ratio.replace('*', '\u00d7')
        args.append(aspect_ratio_for_handler)
        args.append(1)  # image_number
        args.append(request.output_format)
        args.append(str(request.seed))
        args.append(False)  # read_wildcards_in_order
        args.append(2.0)  # sharpness
        args.append(7.0)  # cfg_scale
        args.append(actual_base_model)
        
        # Log the complete args list (pretty print)
        print(f'[API] ====== Fooocus Generation Args ======')
        print(json.dumps(args, indent=2, ensure_ascii=False, default=str))
        print(f'[API] ======================================')
        args.append("None")  # refiner_sdxl_or_sd_15
        args.append(0.8)  # refiner_switch_at
        
        for _ in range(config.default_max_lora_number):
            args.append(False)  # enable
            args.append("None")  # name
            args.append(0.0)  # weight
        
        args.append(False)  # input_image_checkbox
        args.append("txt2img")  # current_tab
        args.append("")  # uov_method
        args.append("")  # uov_input_image
        args.append([])  # outpaint_selections
        args.append("")  # inpaint_input_image
        args.append("")  # inpaint_additional_prompt
        args.append("")  # inpaint_mask_image_upload
        
        args.append(True)  # disable_preview
        args.append(True)  # disable_intermediate_results
        args.append(False)  # disable_seed_increment
        args.append(False)  # black_out_nsfw
        
        args.append(1.5)  # adm_scaler_positive
        args.append(0.8)  # adm_scaler_negative
        args.append(0.3)  # adm_scaler_end
        args.append(7)  # adaptive_cfg
        args.append(2)  # clip_skip
        args.append("dpmpp_2m_sde_gpu")  # sampler_name
        args.append("karras")  # scheduler_name
        args.append("Default (model)")  # vae_name
        args.append(-1)  # overwrite_step
        args.append(-1)  # overwrite_switch
        args.append(-1)  # overwrite_width
        args.append(-1)  # overwrite_height
        args.append(-1)  # overwrite_vary_strength
        args.append(-1)  # overwrite_upscale_strength
        
        args.append(False)  # mixing_image_prompt_and_vary_upscale
        args.append(False)  # mixing_image_prompt_and_inpaint
        args.append(False)  # debugging_cn_preprocessor
        args.append(False)  # skipping_cn_preprocessor
        args.append(100)  # canny_low_threshold
        args.append(200)  # canny_high_threshold
        args.append("joint")  # refiner_swap_method
        args.append(0.25)  # controlnet_softness
        args.append(False)  # freeu_enabled
        args.append(1.3)  # freeu_b1
        args.append(1.4)  # freeu_b2
        args.append(0.9)  # freeu_s1
        args.append(0.2)  # freeu_s2
        
        args.append(False)  # debugging_inpaint_preprocessor
        args.append(False)  # inpaint_disable_initial_latent
        args.append("v2.6")  # inpaint_engine
        args.append(0.75)  # inpaint_strength
        args.append(0.35)  # inpaint_respective_field
        args.append(False)  # inpaint_advanced_masking_checkbox
        args.append(False)  # invert_mask_checkbox
        args.append(0)  # inpaint_erode_or_dilate
        
        args.append(False)  # save_final_enhanced_image_only
        args.append(False)  # save_metadata_to_images
        args.append("fooocus")  # metadata_scheme
        
        for _ in range(config.default_controlnet_image_count):
            args.append(None)  # image
            args.append(0.5)  # stop_at
            args.append(1.0)  # weight
            args.append("face swap")  # type
        
        args.append(False)  # debug_groundingdino
        args.append(0)  # groundingdino_box_erode_or_dilate
        args.append(False)  # debug_enhance_masks
        args.append("")  # use_with_enhance_skips_image_generation
        args.append(False)  # enhance
        args.append("")  # enhance_upscale_or_variation
        args.append("")  # enhance_order_of_processing
        args.append("")  # enhance_prompt
        
        for _ in range(config.default_enhance_tabs):
            args.append(False)  # enable
            args.append("")  # detection_prompt
            args.append("")  # enhancement_positive_prompt
            args.append("")  # enhancement_negative_prompt
            args.append("u2net")  # mask_generation_model
            args.append("full")  # cloth_category
            args.append("vit_b")  # sam_model
            args.append(0.3)  # text_threshold
            args.append(0.3)  # box_threshold
            args.append(10)  # maximum_number_of_detections
            args.append(False)  # disable_initial_latent_in_inpaint
            args.append("v2.6")  # inpaint_engine
            args.append(0.75)  # inpaint_denoising_strength
            args.append(0.35)  # inpaint_respective_field
            args.append(0)  # mask_erode_or_dilate
            args.append(False)  # invert_mask
        
        return args
    
    except Exception as e:
        raise RuntimeError(f"Failed to build args: {str(e)}")


async def run_generation_in_thread(async_task) -> List[str]:
    """Run Fooocus generation by adding to async task queue and waiting for completion."""
    import modules.async_worker as worker
    
    # Add task to the global queue (worker thread will pick it up)
    worker.async_tasks.append(async_task)
    
    # Wait for task to complete
    max_wait_time = 300  # 5 minutes max
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        # Check if task has finished (worker appends ['finish', results] to yields)
        if len(async_task.yields) > 0:
            last_yield = async_task.yields[-1]
            if isinstance(last_yield, list) and len(last_yield) > 0:
                if last_yield[0] == 'finish':
                    # Task completed, return results
                    return async_task.results
        
        # Small delay to avoid busy waiting
        await asyncio.sleep(0.1)
    
    # Timeout - return whatever results we have so far
    print(f'[API] Warning: Generation timed out after {max_wait_time}s')
    return async_task.results


def get_fooocus_version() -> str:
    """Get Fooocus version"""
    try:
        import fooocus_version
        return fooocus_version.version
    except:
        return "unknown"


if __name__ == "__main__":
    print("Starting Fooocus REST API...")
    uvicorn.run(app, host="127.0.0.1", port=7866)
