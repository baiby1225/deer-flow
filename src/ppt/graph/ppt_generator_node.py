# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
import subprocess
import uuid

from src.ppt.graph.state import PPTState

logger = logging.getLogger(__name__)


def ppt_generator_node(state: PPTState):
    logger.info("Generating ppt file...")
    
    # Check if input file exists
    ppt_file_path = state.get("ppt_file_path", "")
    if not ppt_file_path or not os.path.exists(ppt_file_path):
        logger.error(f"PPT file not found: {ppt_file_path}")
        raise FileNotFoundError(f"PPT file not found: {ppt_file_path}")
    
    # Log file content for debugging
    try:
        with open(ppt_file_path, "r", encoding="utf-8") as f:
            content_preview = f.read()[:200]  # First 200 characters
            logger.info(f"Input file content preview: {content_preview}")
    except Exception as e:
        logger.warning(f"Could not read input file for preview: {e}")
    
    # use marp cli to generate ppt file
    # https://github.com/marp-team/marp-cli?tab=readme-ov-file
    generated_file_path = os.path.join(
        os.getcwd(), f"generated_ppt_{uuid.uuid4()}.pptx"
    )
    
    try:
        # Add --no-stdin option to prevent waiting for stdin
        # Also add --allow-local-files to handle local file references
        result = subprocess.run([
            "marp", 
            ppt_file_path, 
            "-o", 
            generated_file_path,
            "--no-stdin",  # Prevent waiting for stdin input
            "--allow-local-files"  # Allow local file references
        ], 
        capture_output=True, 
        text=True, 
        check=True,
        encoding="utf-8"  # Ensure proper encoding for subprocess
        )
        
        logger.info(f"Marp conversion successful: {result.stdout}")
        if result.stderr:
            logger.warning(f"Marp stderr: {result.stderr}")
        
        # Check if output file was created
        if not os.path.exists(generated_file_path):
            logger.error(f"Generated PPT file not found: {generated_file_path}")
            raise FileNotFoundError(f"Generated PPT file not found: {generated_file_path}")
        
        # Log file size for verification
        file_size = os.path.getsize(generated_file_path)
        logger.info(f"Generated PPT file size: {file_size} bytes")
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Marp conversion failed: {e.stderr}")
        raise RuntimeError(f"Marp conversion failed: {e.stderr}")
    except Exception as e:
        logger.error(f"Unexpected error during PPT generation: {str(e)}")
        raise
    
    finally:
        # remove the temp file
        try:
            if os.path.exists(ppt_file_path):
                os.remove(ppt_file_path)
                logger.info(f"Removed temp file: {ppt_file_path}")
        except Exception as e:
            logger.warning(f"Failed to remove temp file {ppt_file_path}: {str(e)}")
    
    logger.info(f"generated_file_path: {generated_file_path}")
    return {"generated_file_path": generated_file_path}
