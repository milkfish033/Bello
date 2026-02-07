#!/usr/bin/env python3
"""启动 FastAPI Demo：uvicorn apps.api.main:app --reload --port 8001"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "apps.api.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
