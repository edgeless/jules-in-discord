FROM python:3.11-slim

# 非rootユーザーの作成
RUN useradd -m appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 所有者をappuserに変更
RUN chown -R appuser:appuser /app

# 実行ユーザーの指定
USER appuser

CMD ["python", "main.py"]
