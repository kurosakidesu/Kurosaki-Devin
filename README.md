# 社内メモ管理アプリ

社内メモを管理するシンプルなWebアプリケーションです。

## 機能

- メモの追加
- メモ一覧の表示（新しい順）
- メモの削除

## 技術スタック

- Python 3
- Flask
- SQLite

## セットアップと起動方法

### 1. リポジトリをクローン

```bash
git clone https://github.com/kurosakidesu/Kurosaki-Devin.git
cd Kurosaki-Devin
```

### 2. 仮想環境を作成（推奨）

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

### 4. アプリケーションを起動

```bash
python app.py
```

ブラウザで http://127.0.0.1:5000 にアクセスしてください。

## ファイル構成

```
.
├── README.md
├── app.py                # Flaskアプリケーション本体
├── requirements.txt      # 依存パッケージ
└── templates/
    └── index.html        # メモ管理画面のテンプレート
```
