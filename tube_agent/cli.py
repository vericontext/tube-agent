"""CLI entry points for the tube-agent API server."""

import argparse


def run_api():
    """Start the FastAPI development server."""
    parser = argparse.ArgumentParser(description="Run the Tube Agent API server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    import uvicorn
    uvicorn.run(
        "tube_agent.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
