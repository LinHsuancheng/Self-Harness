# 安装与首次运行

使用 Python 3.10+，在项目目录执行：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp config.example.json config.json
cp -n .env.example .env
```

按[配置文档](../configuration.md)填写来源地址、数据路径与授权缓存，并在 `.env` 中设置 `DEEPSEEK_API_KEY`。DeepSeek API 地址和模型已有默认值，可按需修改。

```sh
.venv/bin/python server.py
.venv/bin/python interface.py ingest
.venv/bin/python interface.py status
```

报告生成命令见 [CLI 操作](cli.md)。

依赖：FastAPI、uvicorn、python-multipart、msal、requests、openai、python-dotenv。SQLite、gzip 和日历处理使用 Python 标准库。

相关资源：[CLI](cli.md)、[部署](deployment.md)。
