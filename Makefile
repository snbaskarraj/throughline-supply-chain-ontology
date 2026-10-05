.PHONY: test serve web mcp docker
test:
	python -m pytest -q
serve:
	PYTHONPATH=src uvicorn throughline.api:app --reload --port 8000
web:
	python web/build.py
mcp:
	PYTHONPATH=src python -m throughline.mcp_server
docker:
	docker build -t throughline . && docker run -p 8000:8000 throughline
