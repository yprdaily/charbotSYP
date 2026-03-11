CorpBot Widget + API

社内問い合わせ削減・ナレッジ管理用のチャットボットシステムです。
Google Workspace 環境に最適化されており、バックエンドのデータベース（Headless CMS）として Google Sheets を利用し、フロントエンドは Chrome 拡張機能としてグループウェア上にオーバーレイ表示されます。

アーキテクチャ

Frontend: React + Vite (拡張機能内にウィジェットとして埋め込み)

Backend: FastAPI + Python (GCP Cloud Run 上で稼働、Google Sheets API と連携)

Extension: Chrome 拡張機能 (Manifest V3, Shadow DOM によるホストページの CSS 汚染防止、Google OAuth2 認証)

ディレクトリ構成

/frontend/ : チャットUIウィジェットの React ソースコード

/backend/ : 検索ロジックやスプレッドシート連携、OIDC認証を担う FastAPI アプリケーション

/extension/ : Chrome 拡張機能の本体。フロントエンドのビルド結果(widget/フォルダ)がここに格納されます

/scripts/, /ops/ : セキュリティ設定やデプロイを補助する各種スクリプト

開発環境のセットアップ (Windows向け)

1. 事前準備

開発にあたり、以下のツールがインストールされている必要があります。

Git

Node.js (LTS推奨)

Python (3.11以上推奨)

2. セキュリティ・ツールの設定 (初回のみ)

APIキーやサービスアカウントキーなどのシークレット情報の誤コミットを物理的に防ぐため、必ず初回にフックを設定してください。

.\scripts\setup-security.cmd



※ pre-commit と detect-secrets がインストール・設定されます。

3. バックエンドの環境変数設定

backend/.env.example をコピーして backend/.env を作成し、必要な設定値（スプレッドシートのID、JWT用の秘密鍵など）を記入してください。

ローカル開発サーバーの起動

以下のスクリプトを実行すると、Python の仮想環境のセットアップとバックエンドサーバー (localhost:8000)、およびフロントエンド開発サーバー (localhost:5173) が同時に立ち上がります。

.\run_dev.ps1



ビルドと拡張機能の読み込み (ポートフォリオ用)

当リポジトリはポートフォリオ向けに、**ローカル開発環境用（デモ用）**と**本番公開用**で設定ファイルが切り替わる仕組みになっています。
それぞれ、`extension/config.development.js` および `extension/config.production.js` がビルド時に自動で適用されます。

フロントエンドのビルド

`frontend` フォルダに移動し、用途に合わせてビルドコマンドを実行してください。

```powershell
cd frontend

# ローカル開発用 (localhost:8000向け) にビルドする場合
npm run build:dev

# 本番環境用 (Cloud Runなど) にビルドする場合
npm run build:prod
```

※ ビルド成果物と選択された `config.js` は自動的に `extension/widget/` にコピーされ、拡張機能から読み込める状態になります。

拡張機能の読み込み

Chromeブラウザで chrome://extensions を開きます。

右上の「デベロッパー モード」をオンにします。

「パッケージ化されていない拡張機能を読み込む」をクリックし、本リポジトリの extension フォルダ を選択します。

セキュリティに関する注意事項 (重要)

.env や *.json (Google のサービスアカウントキー等)、*.pem などのシークレット情報は 絶対に Git にコミットしないでください。

万が一シークレットをコミットしてしまった場合の対応手順は RUNBOOK.md を確認してください。

その他のセキュリティ方針については SECURITY.md を参照してください。

デプロイ (Cloud Run)

バックエンドのコンテナは cloudbuild.yaml を使用して GCP (Cloud Run) へデプロイされます。詳細は環境ごとの CI/CD パイプラインの設定に準じます。
