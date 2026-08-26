# 学习小站
#
#   make          看全部命令
#   make up       构建 + 本地预览（手机/iPad 同 WiFi 可看，带扫码）
#   make pdf      构建 + 把打印单导成 PDF
#
# dist/ 是产物，不进 git。线上由 GitHub Actions 跑同一个 build.py。

PORT ?= 8002
HOST ?= 0.0.0.0
PY   ?= python3

.PHONY: help build pdf up open stop clean
.DEFAULT_GOAL := help

help:
	@echo ""
	@echo "  学习小站"
	@echo "  ─────────────────────────────────────────"
	@echo "  make build   构建到 dist/（只出 HTML）"
	@echo "  make pdf     构建 + 导 PDF"
	@echo "  make up      构建 + 本地预览（端口 $(PORT)）"
	@echo "  make open    浏览器打开预览页"
	@echo "  make stop    停掉预览服务"
	@echo "  make clean   删掉 dist/"
	@echo ""
	@echo "  make up PORT=9000    换端口"
	@echo ""

build:
	@$(PY) build.py

pdf:
	@$(PY) build.py --pdf

up: build
	@ip=$$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null); \
	echo "  📚 学习小站预览已启动（Ctrl+C 退出）"; \
	echo "  ─────────────────────────────────────────"; \
	echo "  电脑：               http://localhost:$(PORT)/"; \
	if [ -n "$$ip" ]; then \
	  echo "  手机/iPad（同 WiFi）：http://$$ip:$(PORT)/"; \
	  if command -v qrencode >/dev/null 2>&1; then \
	    echo ""; echo "  手机扫码直达 👇"; echo ""; \
	    qrencode -t ANSIUTF8 "http://$$ip:$(PORT)/"; \
	  else \
	    echo "  （想要扫码可先装：brew install qrencode）"; \
	  fi; \
	fi; \
	echo ""; \
	cd dist && $(PY) -m http.server $(PORT) --bind $(HOST)

open:
	@open "http://localhost:$(PORT)/"

stop:
	@pids=$$(lsof -ti tcp:$(PORT) 2>/dev/null); \
	if [ -n "$$pids" ]; then \
	  echo "$$pids" | xargs kill && echo "  已停止端口 $(PORT) 上的预览"; \
	else \
	  echo "  端口 $(PORT) 上没有在跑的预览"; \
	fi

clean:
	@rm -rf dist && echo "  已删掉 dist/"
