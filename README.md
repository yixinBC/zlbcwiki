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
cd zlbcwiki
# 确保在虚拟环境下
python manage.py runserver
```
