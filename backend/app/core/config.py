import os

# 이 시스템은 SQLite를 DB로 쓰고 있다.
# 이건 backend 폴더에서 db 파일의 위치를 뜻한다
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///../sevensplit.db")

