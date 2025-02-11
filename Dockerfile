FROM python:3.12-slim

# 必要なシステムパッケージのインストール（Poetry やパッケージビルドに必要なもの）
RUN apt-get update && apt-get install -y curl build-essential && rm -rf /var/lib/apt/lists/*

# Poetry のインストール
RUN curl -sSL https://install.python-poetry.org | python -
ENV PATH="/root/.local/bin:$PATH"

# 作業ディレクトリの設定
WORKDIR /app

# キャッシュを有効にするため、pyproject.toml と poetry.lock を先にコピー
COPY pyproject.toml poetry.lock* /app/

# 仮想環境を作成せずに Poetry 経由で依存パッケージをインストール
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi

# アプリケーションのソースコードをコピー
COPY . /app

# Flask アプリケーションが使用するポート（app.py 内で 5001 番ポートを指定しているため）
EXPOSE 5001

# Flask アプリを起動
CMD ["python", "app.py"]