FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 非rootユーザーの作成
RUN useradd -m appuser

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# 所有者をappuserに変更
RUN chown -R appuser:appuser /app

# 実行ユーザーの指定
USER appuser

# Enable bytecode compilation and specify python path explicitly for uv environment if needed
ENV UV_COMPILE_BYTECODE=1

CMD ["uv", "run", "main.py"]
