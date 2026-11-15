import argparse
import uvicorn
from sql_agent.core.config import settings
from sql_agent.core.logging import setup_logging

SERVICES = {
    "api": ("sql_agent.main:app", settings.api_port),
    "ingestion": ("auto_ontology.ingestion_service.main:app", settings.ingestion_port),
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jalankan satu service.")
    parser.add_argument("service", choices=SERVICES)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    app, port = SERVICES[args.service]
    setup_logging(settings.log_level)
    uvicorn.run(
        app,
        host=settings.bind_host,
        port=port,
        reload=args.reload,
        log_config=None,
    )