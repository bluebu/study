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

.PHONY: help deps build pdf up open stop clean shot
.DEFAULT_GOAL := help

help:
	@echo ""
	@echo "  学习小站"
	@echo "  ─────────────────────────────────────────"
	@echo "  make deps    装依赖（只有 Jinja2，做 HTML 模板）"
	@echo "  make build   构建到 dist/（只出 HTML）"
	@echo "  make pdf     构建 + 导 PDF"
	@echo "  make up      构建 + 本地预览（端口 $(PORT)）"
	@echo "  make open    浏览器打开预览页"
	@echo "  make stop    停掉预览服务"
	@echo "  make clean   删掉 dist/"
	@echo ""
	@echo "  make shot URL=dist/english/review/2026-08-28.html OUT=/tmp/a.png"
	@echo "               真实手机视口截图（改完排版自检用，见 tools/shot.mjs）"
	@echo "               加 EL=\".box.scales\" 只截一个元素；PROBE=1 只报尺寸不出图"
	@echo ""
	@echo "  make up PORT=9000    换端口"
	@echo ""

# 唯一的第三方依赖。版本钉在 requirements.txt —— CI 装的是同一个版本，
# 不然「本地能出就等于线上能出」不成立
deps:
	@$(PY) -m pip install -q -r requirements.txt && echo "  依赖装好了"

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

# 真实视口截图。Chrome headless 的 --window-size 模拟不了手机（布局视口恒为 500px），
# 所以走 playwright —— 为什么、有哪些坑，都写在 tools/shot.mjs 顶部。
# URL 可以给本地路径（自动转成 file://）也可以给 http://
WIDTH ?= 390
shot:
	@test -n "$(URL)" || { echo "  用法：make shot URL=<页面> OUT=<图.png> [WIDTH=390] [EL=选择器] [PROBE=1]"; exit 1; }
	@node -e "require.resolve('playwright-core')" 2>/dev/null \
	  || { echo "  先装一次：npm i playwright-core"; exit 1; }
	@u="$(URL)"; case "$$u" in http*|file:*) ;; *) u="file://$$(cd $$(dirname $$u) && pwd)/$$(basename $$u)";; esac; \
	if [ -n "$(PROBE)" ]; then \
	  node tools/shot.mjs "$$u" --probe $(WIDTH); \
	else \
	  test -n "$(OUT)" || { echo "  要给 OUT=<图.png>（或者加 PROBE=1 只看尺寸）"; exit 1; }; \
	  node tools/shot.mjs "$$u" "$(OUT)" $(WIDTH) $(if $(EL),--el "$(EL)"); \
	fi

clean:
	@rm -rf dist && echo "  已删掉 dist/"
