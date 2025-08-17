# 🌍 We Planet - 家族向けエコ活動支援アプリ バックエンド

## プロジェクト概要

We Planetは、家族でエコ活動を楽しく継続できる支援アプリケーションのバックエンドAPIです。FastAPI + Azure + JWT認証による堅牢なアーキテクチャで、40以上のAPIエンドポイントを提供します。

### 主要機能
- 👥 **家族管理システム**: 家族メンバーの招待・管理
- 🌱 **エコ活動追跡**: 日々のエコ活動記録・統計
- 🏆 **バッジシステム**: 成果に応じたバッジ獲得
- 🎯 **ミッションシステム**: 期間限定チャレンジ
- 📁 **ファイル管理**: Azure Blob Storageによる画像アップロード
- 🔐 **JWT認証**: セキュアな認証・認可システム

## 技術スタック

### コア技術
- **Web Framework**: FastAPI 0.104.1
- **言語**: Python 3.11+
- **データベース**: Azure SQL Database
- **認証**: JWT (JSON Web Tokens)
- **ストレージ**: Azure Blob Storage
- **ORM**: SQLAlchemy 2.0
- **バリデーション**: Pydantic V2

### 開発・テスト
- **テスト**: pytest + httpx
- **コード品質**: Black + Flake8
- **型チェック**: mypy
- **依存関係管理**: pip-tools

### Azure統合
- **Azure SQL Database**: メインデータストレージ
- **Azure Blob Storage**: 画像・ファイルストレージ
- **Azure App Service**: ホスティング対応

## プロジェクト構造

```
Gas-Care-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPIアプリケーション
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py               # 認証API
│   │   ├── families.py           # 家族管理API
│   │   ├── activities.py         # エコ活動API
│   │   ├── badges.py             # バッジシステムAPI
│   │   ├── missions.py           # ミッションAPI
│   │   └── upload.py             # ファイルアップロードAPI
│   ├── core/
│   │   ├── __init__.py
│   │   ├── auth.py               # JWT認証ロジック
│   │   ├── security.py           # セキュリティ機能
│   │   ├── database.py           # データベース設定
│   │   ├── config.py             # 設定管理
│   │   └── azure_storage.py      # Azure Blob Storage
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py               # ユーザーモデル
│   │   ├── family.py             # 家族モデル
│   │   ├── activity.py           # 活動モデル
│   │   ├── badge.py              # バッジモデル
│   │   └── mission.py            # ミッションモデル
│   └── schemas/
│       ├── __init__.py
│       ├── user.py               # ユーザースキーマ
│       ├── family.py             # 家族スキーマ
│       ├── activity.py           # 活動スキーマ
│       ├── badge.py              # バッジスキーマ
│       └── mission.py            # ミッションスキーマ
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # テスト設定
│   ├── api/
│   │   ├── test_auth.py          # 認証APIテスト
│   │   ├── test_families.py      # 家族APIテスト
│   │   ├── test_activities.py    # 活動APIテスト
│   │   ├── test_badges.py        # バッジAPIテスト
│   │   ├── test_missions.py      # ミッションAPIテスト
│   │   └── test_upload.py        # アップロードAPIテスト
│   ├── core/
│   │   ├── test_auth.py          # 認証ロジックテスト
│   │   ├── test_security.py      # セキュリティテスト
│   │   ├── test_azure_storage.py # Azure Storageテスト
│   │   └── test_database.py      # データベーステスト
│   └── models/
│       ├── test_user.py          # ユーザーモデルテスト
│       ├── test_family.py        # 家族モデルテスト
│       ├── test_activity.py      # 活動モデルテスト
│       ├── test_badge.py         # バッジモデルテスト
│       └── test_mission.py       # ミッションモデルテスト
├── requirements.txt              # 依存関係
├── .env.example                  # 環境変数テンプレート
├── .gitignore                    # Git除外設定
└── README.md                     # このファイル
```

## セットアップ手順

### 1. 環境構築

```bash
# リポジトリクローン
git clone https://github.com/Ryuya-hub/Gas-Care-backend.git
cd Gas-Care-backend

# 仮想環境作成
python -m venv venv

# 仮想環境有効化 (Windows)
venv\Scripts\activate

# 仮想環境有効化 (macOS/Linux)
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt
```

### 2. 環境変数設定

`.env.example`を`.env`にコピーして設定:

```env
# データベース設定
DATABASE_URL=mssql://username:password@server.database.windows.net/dbname?driver=ODBC+Driver+17+for+SQL+Server

# JWT設定
JWT_SECRET_KEY=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Azure Blob Storage設定
AZURE_STORAGE_CONNECTION_STRING=your_azure_storage_connection_string
AZURE_STORAGE_CONTAINER_NAME=your_container_name

# CORS設定
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### 3. データベース初期化

```bash
# データベースマイグレーション実行
python -c "from app.core.database import create_tables; create_tables()"
```

### 4. アプリケーション起動

```bash
# 開発サーバー起動
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

アプリケーションは `http://localhost:8000` で起動します。

## API仕様

### エンドポイント一覧

#### 認証 (`/auth`)
- `POST /auth/register` - ユーザー登録
- `POST /auth/login` - ログイン
- `POST /auth/refresh` - トークンリフレッシュ
- `POST /auth/logout` - ログアウト
- `GET /auth/me` - 現在のユーザー情報

#### 家族管理 (`/families`)
- `POST /families` - 家族作成
- `GET /families` - 家族一覧取得
- `GET /families/{family_id}` - 家族詳細取得
- `PUT /families/{family_id}` - 家族情報更新
- `DELETE /families/{family_id}` - 家族削除
- `POST /families/{family_id}/invite` - メンバー招待
- `POST /families/{family_id}/join` - 家族参加
- `DELETE /families/{family_id}/members/{user_id}` - メンバー削除

#### エコ活動 (`/activities`)
- `POST /activities` - 活動記録作成
- `GET /activities` - 活動一覧取得
- `GET /activities/{activity_id}` - 活動詳細取得
- `PUT /activities/{activity_id}` - 活動更新
- `DELETE /activities/{activity_id}` - 活動削除
- `GET /activities/stats` - 統計情報取得
- `GET /activities/family/{family_id}` - 家族の活動取得

#### バッジシステム (`/badges`)
- `GET /badges` - バッジ一覧取得
- `GET /badges/{badge_id}` - バッジ詳細取得
- `GET /badges/user/{user_id}` - ユーザーのバッジ取得
- `POST /badges/{badge_id}/award` - バッジ授与

#### ミッション (`/missions`)
- `GET /missions` - ミッション一覧取得
- `GET /missions/{mission_id}` - ミッション詳細取得
- `GET /missions/active` - アクティブミッション取得
- `POST /missions/{mission_id}/participate` - ミッション参加
- `POST /missions/{mission_id}/complete` - ミッション完了

#### ファイルアップロード (`/upload`)
- `POST /upload/image` - 画像アップロード
- `GET /upload/image/{filename}` - 画像取得
- `DELETE /upload/image/{filename}` - 画像削除

### 認証方式

すべてのAPIエンドポイント（認証エンドポイントを除く）は、JWTトークンによる認証が必要です。

```bash
# リクエストヘッダー例
Authorization: Bearer <jwt_token>
```

### レスポンス形式

成功レスポンス:
```json
{
  "status": "success",
  "data": {...},
  "message": "Operation completed successfully"
}
```

エラーレスポンス:
```json
{
  "status": "error",
  "error": "Error description",
  "details": {...}
}
```

## データベース設計

### 主要テーブル

#### Users（ユーザー）
- `id`: プライマリキー
- `email`: メールアドレス（ユニーク）
- `username`: ユーザー名
- `password_hash`: ハッシュ化パスワード
- `created_at`: 作成日時
- `updated_at`: 更新日時

#### Families（家族）
- `id`: プライマリキー
- `name`: 家族名
- `description`: 説明
- `created_by`: 作成者ID
- `created_at`: 作成日時

#### FamilyMembers（家族メンバー）
- `id`: プライマリキー
- `family_id`: 家族ID（外部キー）
- `user_id`: ユーザーID（外部キー）
- `role`: 役割（owner/member）
- `joined_at`: 参加日時

#### Activities（エコ活動）
- `id`: プライマリキー
- `user_id`: ユーザーID（外部キー）
- `family_id`: 家族ID（外部キー）
- `type`: 活動タイプ
- `description`: 説明
- `date`: 活動日
- `points`: 獲得ポイント

#### Badges（バッジ）
- `id`: プライマリキー
- `name`: バッジ名
- `description`: 説明
- `icon_url`: アイコンURL
- `criteria`: 獲得条件

#### Missions（ミッション）
- `id`: プライマリキー
- `title`: タイトル
- `description`: 説明
- `start_date`: 開始日
- `end_date`: 終了日
- `reward_points`: 報酬ポイント

## テスト実行

### 全テスト実行
```bash
pytest
```

### カバレッジ付きテスト実行
```bash
pytest --cov=app --cov-report=html
```

### 特定テスト実行
```bash
# APIテストのみ
pytest tests/api/

# 認証テストのみ
pytest tests/api/test_auth.py

# 特定テストメソッド
pytest tests/api/test_auth.py::test_register_user
```

## 開発ガイドライン

### コーディング規約
- **フォーマッター**: Black
- **リンター**: Flake8
- **型チェック**: mypy
- **インポート順序**: isort

### Git ワークフロー
1. `main`ブランチから`feature/feature-name`でブランチ作成
2. 機能実装・テスト作成
3. プルリクエスト作成
4. コードレビュー
5. `main`ブランチにマージ

### API設計原則
- RESTful設計に準拠
- 適切なHTTPステータスコード使用
- 一貫したレスポンス形式
- 包括的なエラーハンドリング

## デプロイ

### Azure App Service デプロイ

```bash
# Azure CLI ログイン
az login

# リソースグループ作成
az group create --name we-planet-rg --location japaneast

# App Service プラン作成
az appservice plan create --name we-planet-plan --resource-group we-planet-rg --sku B1 --is-linux

# Web App 作成
az webapp create --resource-group we-planet-rg --plan we-planet-plan --name we-planet-api --runtime "PYTHON|3.11" --deployment-local-git

# 環境変数設定
az webapp config appsettings set --resource-group we-planet-rg --name we-planet-api --settings @appsettings.json
```

### Docker デプロイ

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを開く

## サポート

問題や質問がある場合は、[Issues](https://github.com/Ryuya-hub/Gas-Care-backend/issues)でお知らせください。

---

**We Planet Backend** - 家族で楽しむエコライフをサポート 🌍
