@"
import re
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union
import json
import unicodedata
from urllib.parse import urlparse
import math

def generate_uuid() -> str:
    """UUID生成"""
    return str(uuid.uuid4())

def generate_short_id(length: int = 8) -> str:
    """短縮ID生成"""
    return str(uuid.uuid4()).replace('-', '')[:length]

def slugify(text: str, max_length: int = 50) -> str:
    """URLスラッグ生成"""
    # Unicode正規化
    text = unicodedata.normalize('NFKD', text)
    # 小文字に変換
    text = text.lower()
    # 特殊文字を削除
    text = re.sub(r'[^\w\s-]', '', text)
    # スペースをハイフンに変換
    text = re.sub(r'[-\s]+', '-', text)
    # 先頭・末尾のハイフンを削除
    text = text.strip('-')
    # 最大長でカット
    return text[:max_length]

def hash_string(text: str, algorithm: str = 'sha256') -> str:
    """文字列のハッシュ化"""
    if algorithm == 'md5':
        return hashlib.md5(text.encode()).hexdigest()
    elif algorithm == 'sha1':
        return hashlib.sha1(text.encode()).hexdigest()
    elif algorithm == 'sha256':
        return hashlib.sha256(text.encode()).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

def validate_email(email: str) -> bool:
    """メールアドレス検証"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username: str) -> Dict[str, Any]:
    """ユーザー名検証"""
    result = {
        "is_valid": True,
        "issues": []
    }
    
    if len(username) < 3:
        result["issues"].append("ユーザー名は3文字以上である必要があります")
        result["is_valid"] = False
    
    if len(username) > 50:
        result["issues"].append("ユーザー名は50文字以下である必要があります")
        result["is_valid"] = False
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        result["issues"].append("ユーザー名は英数字、アンダースコア、ハイフンのみ使用可能です")
        result["is_valid"] = False
    
    if username.startswith('-') or username.endswith('-'):
        result["issues"].append("ユーザー名の先頭・末尾にハイフンは使用できません")
        result["is_valid"] = False
    
    return result

def validate_url(url: str) -> bool:
    """URL検証"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def sanitize_filename(filename: str) -> str:
    """ファイル名のサニタイズ"""
    # 危険な文字を削除
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # 連続するドットを単一のドットに
    filename = re.sub(r'\.+', '.', filename)
    # 先頭・末尾の空白とドットを削除
    filename = filename.strip(' .')
    # 最大長制限
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:255-len(ext)-1] + '.' + ext if ext else name[:255]
    
    return filename

def format_file_size(size_bytes: int) -> str:
    """ファイルサイズの人間が読める形式への変換"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def calculate_co2_reduction(activity_type: str, amount: float = 1.0) -> float:
    """活動タイプに基づくCO2削減量計算"""
    co2_factors = {
        "リサイクル": 0.5,      # kg per action
        "節電": 0.4,           # kg per kWh
        "節水": 0.001,         # kg per liter
        "交通": 2.3,           # kg per km (car vs public transport)
        "廃棄物削減": 0.3,      # kg per action
        "グリーン購入": 0.2,    # kg per action
        "その他": 0.1          # kg per action
    }
    
    return co2_factors.get(activity_type, 0.1) * amount

def calculate_points(
    activity_type: str, 
    co2_reduction: float, 
    base_points: int = 10
) -> int:
    """ポイント計算"""
    # CO2削減量に基づくボーナス
    co2_bonus = int(co2_reduction * 10)  # 1kg CO2 = 10 bonus points
    
    # 活動タイプに基づく係数
    type_multipliers = {
        "リサイクル": 1.0,
        "節電": 1.2,
        "節水": 1.1,
        "交通": 1.5,
        "廃棄物削減": 1.3,
        "グリーン購入": 1.4,
        "その他": 1.0
    }
    
    multiplier = type_multipliers.get(activity_type, 1.0)
    total_points = int((base_points + co2_bonus) * multiplier)
    
    return max(total_points, 1)  # 最低1ポイント

def calculate_level_from_xp(experience_points: int) -> int:
    """経験値からレベルを計算"""
    # レベル1 = 0-999 XP, レベル2 = 1000-2999 XP, etc.
    if experience_points < 1000:
        return 1
    return int(experience_points / 1000) + 1

def calculate_xp_for_level(level: int) -> int:
    """レベルに必要な経験値を計算"""
    if level <= 1:
        return 0
    return (level - 1) * 1000

def calculate_level_progress(experience_points: int) -> Dict[str, Any]:
    """レベル進捗を計算"""
    current_level = calculate_level_from_xp(experience_points)
    current_level_xp = calculate_xp_for_level(current_level)
    next_level_xp = calculate_xp_for_level(current_level + 1)
    
    progress_xp = experience_points - current_level_xp
    required_xp = next_level_xp - current_level_xp
    progress_percentage = (progress_xp / required_xp) * 100 if required_xp > 0 else 0
    
    return {
        "current_level": current_level,
        "experience_points": experience_points,
        "current_level_xp": current_level_xp,
        "next_level_xp": next_level_xp,
        "progress_xp": progress_xp,
        "required_xp": required_xp,
        "progress_percentage": round(progress_percentage, 1)
    }

def calculate_streak_days(last_activity_date: Optional[datetime]) -> int:
    """連続日数を計算"""
    if not last_activity_date:
        return 0
    
    now = datetime.now(timezone.utc)
    last_activity = last_activity_date.replace(tzinfo=timezone.utc)
    
    # 日数の差を計算
    days_diff = (now.date() - last_activity.date()).days
    
    # 今日または昨日の活動があれば連続とみなす
    if days_diff <= 1:
        return 1  # 実際の連続日数計算はより複雑
    else:
        return 0  # 連続が途切れた

def format_datetime_jp(dt: datetime) -> str:
    """日本語形式の日時フォーマット"""
    if not dt:
        return ""
    
    # JSTに変換
    jst = dt.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9)))
    
    return jst.strftime("%Y年%m月%d日 %H:%M")

def format_date_jp(dt: datetime) -> str:
    """日本語形式の日付フォーマット"""
    if not dt:
        return ""
    
    # JSTに変換
    jst = dt.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9)))
    
    return jst.strftime("%Y年%m月%d日")

def time_ago_jp(dt: datetime) -> str:
    """相対時間の日本語表示"""
    if not dt:
        return ""
    
    now = datetime.now(timezone.utc)
    dt = dt.replace(tzinfo=timezone.utc)
    
    diff = now - dt
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years}年前"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months}ヶ月前"
    elif diff.days > 0:
        return f"{diff.days}日前"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}時間前"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}分前"
    else:
        return "たった今"

def paginate(query, page: int = 1, size: int = 20):
    """ページネーション"""
    offset = (page - 1) * size
    items = query.offset(offset).limit(size).all()
    total = query.count()
    pages = math.ceil(total / size)
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "has_prev": page > 1,
        "has_next": page < pages
    }

def deep_merge_dict(base: Dict, update: Dict) -> Dict:
    """辞書の深いマージ"""
    result = base.copy()
    
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = value
    
    return result

def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """安全なJSON読み込み"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default

def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """安全なJSON書き込み"""
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return default

def mask_email(email: str) -> str:
    """メールアドレスのマスキング"""
    if '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    
    if len(local) <= 2:
        masked_local = '*' * len(local)
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"

def generate_color_from_string(text: str) -> str:
    """文字列からカラーコードを生成"""
    hash_object = hashlib.md5(text.encode())
    hex_dig = hash_object.hexdigest()
    
    # 最初の6文字を取得してカラーコードにする
    color = "#" + hex_dig[:6]
    return color

def is_weekend(date: datetime) -> bool:
    """週末かどうか判定"""
    return date.weekday() >= 5  # 土曜日(5), 日曜日(6)

def get_week_start_end(date: datetime) -> tuple[datetime, datetime]:
    """週の開始日と終了日を取得"""
    # 月曜日を週の開始とする
    days_since_monday = date.weekday()
    week_start = date - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    
    return (
        week_start.replace(hour=0, minute=0, second=0, microsecond=0),
        week_end.replace(hour=23, minute=59, second=59, microsecond=999999)
    )

def get_month_start_end(date: datetime) -> tuple[datetime, datetime]:
    """月の開始日と終了日を取得"""
    month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 次の月の1日から1日引く
    if date.month == 12:
        next_month = date.replace(year=date.year + 1, month=1, day=1)
    else:
        next_month = date.replace(month=date.month + 1, day=1)
    
    month_end = next_month - timedelta(days=1)
    month_end = month_end.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return (month_start, month_end)
"@ | Out-File -FilePath app\utils\helpers.py -Encoding UTF8