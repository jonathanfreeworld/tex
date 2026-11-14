"""실행 중 SQLite의 WAL 내용을 포함한 일관된 백업을 만듭니다."""
import sqlite3
from datetime import datetime
from pathlib import Path
from database import DB_PATH

if not DB_PATH.exists():
    raise SystemExit('아직 학습 DB가 없습니다. 앱을 먼저 실행하세요.')
target=Path(__file__).parent/'backups'/('classroom_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.db')
target.parent.mkdir(parents=True,exist_ok=True)
source=sqlite3.connect(DB_PATH)
destination=sqlite3.connect(target)
try:
    source.backup(destination)
finally:
    destination.close()
    source.close()
print('백업 완료:',target)
