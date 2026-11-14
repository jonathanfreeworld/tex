"""단일 Streamlit 서버에서 20명의 기록을 공유하는 SQLite 저장소."""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from learning import QUESTIONS, UNIT_MAP, STAGES

DB_PATH = Path(os.environ.get('TAX_DB_PATH', Path(__file__).parent / 'data' / 'classroom.db'))

@contextmanager
def connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    with connection() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY, org TEXT NOT NULL, name TEXT NOT NULL,
            created TEXT NOT NULL, UNIQUE(org,name));
        CREATE TABLE IF NOT EXISTS progress (
            student TEXT NOT NULL REFERENCES students(id), unit TEXT NOT NULL,
            stage TEXT NOT NULL CHECK(stage IN ('learn','practice','check')),
            updated TEXT NOT NULL, PRIMARY KEY(student,unit,stage));
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, student TEXT NOT NULL REFERENCES students(id),
            question TEXT NOT NULL, unit TEXT NOT NULL, answer INTEGER NOT NULL,
            correct INTEGER NOT NULL CHECK(correct IN (0,1)), created TEXT NOT NULL,
            nonce TEXT NOT NULL UNIQUE);
        CREATE INDEX IF NOT EXISTS attempt_student ON attempts(student,id);
        CREATE TABLE IF NOT EXISTS notes (
            student TEXT NOT NULL REFERENCES students(id), question TEXT NOT NULL,
            body TEXT NOT NULL, updated TEXT NOT NULL, PRIMARY KEY(student,question));
        ''')

def now():
    return datetime.now(timezone.utc).isoformat()

def normalized(value, limit):
    value = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(value))).strip()
    if not value or len(value)>limit or any(ord(c)<32 for c in value):
        raise ValueError(f'입력값은 1~{limit}자로 적어 주세요.')
    return value

def register(org, name):
    org, name = normalized(org,60), normalized(name,40)
    ident = hashlib.sha256((org+'\0'+name).encode()).hexdigest()
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute('SELECT * FROM students WHERE id=?',(ident,)).fetchone()
        if existing:
            return dict(existing)
        if db.execute('SELECT COUNT(*) FROM students').fetchone()[0]>=20:
            raise ValueError('20명 정원이 찼습니다. 담당 교수자에게 문의해 주세요.')
        db.execute('INSERT INTO students VALUES (?,?,?,?)',(ident,org,name,now()))
    return dict(id=ident,org=org,name=name)

def snapshot(student=None):
    result = {}
    with connection() as db:
        for table in ('students','progress','attempts','notes'):
            field = 'id' if table=='students' else 'student'
            sql = f'SELECT * FROM {table}'
            args = ()
            if student:
                sql += f' WHERE {field}=?'
                args = (student,)
            if table=='attempts':
                sql += ' ORDER BY id'
            result[table] = [dict(row) for row in db.execute(sql,args).fetchall()]
    return result

def mark(student, unit, stage):
    if unit not in UNIT_MAP or stage not in STAGES:
        raise ValueError('알 수 없는 학습 단계입니다.')
    with connection() as db:
        if stage=='check':
            actual = {r[0] for r in db.execute('SELECT DISTINCT question FROM attempts WHERE student=? AND unit=?',(student,unit))}
            expected = {q for q in QUESTIONS if QUESTIONS[q]['unit']==unit}
            if not expected.issubset(actual):
                raise ValueError('확인하기 8문항에 모두 응답해 주세요.')
        db.execute('INSERT INTO progress VALUES (?,?,?,?) ON CONFLICT(student,unit,stage) DO UPDATE SET updated=excluded.updated',
                   (student,unit,stage,now()))

def answer(student, question, choice, nonce):
    q = QUESTIONS.get(question)
    if not q or isinstance(choice,bool) or not isinstance(choice,int) or not 0<=choice<len(q['options']):
        raise ValueError('보기를 선택해 주세요.')
    with connection() as db:
        existing = db.execute('SELECT * FROM attempts WHERE nonce=?',(nonce,)).fetchone()
        if existing:
            if existing['student']!=student or existing['question']!=question:
                raise ValueError('잘못된 제출 요청입니다.')
            return bool(existing['correct'])
        correct = int(choice==q['correct'])
        db.execute('INSERT INTO attempts (student,question,unit,answer,correct,created,nonce) VALUES (?,?,?,?,?,?,?)',
                   (student,question,q['unit'],choice,correct,now(),nonce))
    return bool(correct)

def save_note(student, question, body):
    if question not in QUESTIONS:
        raise ValueError('알 수 없는 문항입니다.')
    with connection() as db:
        db.execute('INSERT INTO notes VALUES (?,?,?,?) ON CONFLICT(student,question) DO UPDATE SET body=excluded.body,updated=excluded.updated',
                   (student,question,str(body)[:1200],now()))

def initial_teacher_password():
    supplied = os.environ.get('TEACHER_PASSWORD')
    if supplied:
        return supplied
    keyfile = DB_PATH.parent / 'teacher_password.txt'
    keyfile.parent.mkdir(parents=True,exist_ok=True)
    if not keyfile.exists():
        try:
            fd=os.open(keyfile,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                f.write(secrets.token_urlsafe(18))
        except FileExistsError:
            pass
    return keyfile.read_text(encoding='utf-8').strip()

def password_matches(supplied, expected):
    return bool(expected) and hmac.compare_digest(hashlib.sha256(supplied.encode()).digest(),hashlib.sha256(expected.encode()).digest())
