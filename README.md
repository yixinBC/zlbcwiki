# ZLBC Wiki

## 如何运行本项目

1. 克隆代码库

```bash
git clone https://github.com/yixinBC/zlbcwiki.git
cd zlbcwiki
```

2.安装项目管理器[uv](https://docs.astral.sh/uv/)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

3.安装依赖

```bash
uv sync
```

4.运行项目

```bash
# 初始化数据库
uv run manage.py migrate
# 启动 Wiki 服务
uv run manage.py runserver
```
