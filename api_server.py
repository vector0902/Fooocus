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
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
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


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Text prompt for generation")
    negative_prompt: str = Field("", description="Negative prompt")
    style: str = Field("Fooocus V2", description="Style selection")
    aspect_ratio: str = Field("1024x1024", description="Image aspect ratio (e.g., 1024x1024, 1152x896)")
    steps: int = Field(20, ge=1, le=200, description="Number of steps")
    seed: int = Field(-1, description="Random seed (-1 for random)")
    performance: str = Field("Speed", enum=["Speed", "Quality"], description="Performance mode")
    output_format: str = Field("png", enum=["png", "jpg"], description="Output format")


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


start_time = time.time()
current_task: Optional[str] = None
task_lock = asyncio.Lock()


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


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
    global current_task
    
    return StatusResponse(
        status="running" if current_task else "idle",
        version=get_fooocus_version(),
        uptime=time.time() - start_time,
        current_task=current_task
    )


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_image(request: GenerateRequest):
    """
    Generate image using Fooocus.
    
    This endpoint provides a simplified interface compared to the full Gradio API.
    Only essential parameters are required; others use sensible defaults.
    """
    global current_task
    
    async with task_lock:
        if current_task:
            raise HTTPException(status_code=409, detail="Another task is already running")
        
        task_id = f"{int(time.time())}"
        current_task = f"generate:{request.prompt[:50]}"
    
    try:
        start_time = time.time()
        
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
        current_task = None


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
        
        args.append(False)  # generate_image_grid_for_each_batch
        args.append(request.prompt)
        args.append(request.negative_prompt or "")
        args.append([request.style])
        args.append(request.performance)
        args.append(request.aspect_ratio)
        args.append(1)  # image_number
        args.append(request.output_format)
        args.append(str(request.seed))
        args.append(False)  # read_wildcards_in_order
        args.append(2.0)  # sharpness
        args.append(7.0)  # cfg_scale
        args.append(config.default_base_model_name if hasattr(config, 'default_base_model_name') else "juggernautXL_v8Rundiffusion.safetensors")
        args.append("None")  # refiner_sdxl_or_sd_15
        args.append(0.8)  # refiner_switch_at
        
        for _ in range(5):  # 5 LoRA slots
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
        
        for _ in range(16):  # 16 image prompts
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
        
        for _ in range(4):  # 4 enhance inputs
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
    """Run Fooocus generation in a separate thread."""
    import modules.async_worker as worker
    
    loop = asyncio.get_event_loop()
    
    def sync_generate():
        results = []
        
        def callback(images, seed, **kwargs):
            results.extend(images)
        
        worker.process_task(
            all_steps=[async_task.steps],
            async_task=async_task,
            callback=callback,
            controlnet_canny_path=None,
            controlnet_cpds_path=None,
            current_task_id=0
        )
        
        return results
    
    results = await loop.run_in_executor(None, sync_generate)
    return results


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
