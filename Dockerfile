# 軽量の Python イメージを使用
FROM python:3.9-slim

# システムパッケージの更新と dcm2niix のインストール
RUN apt-get update && apt-get install -y dcm2niix && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリの作成
WORKDIR /app

# requirements.txt をコピーし、Python パッケージをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコードを全てコピー
COPY main.py dcm2niix.exe ./

# Render では環境変数 PORT が渡されるので、それに合わせる
EXPOSE 8000

# uvicorn で FastAPI アプリを起動（ホスト・ポートを環境変数から取得する例）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
