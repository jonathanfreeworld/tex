import os
import tempfile
import unittest
from pathlib import Path
import database as db
from learning import UNITS, QUESTIONS, questions, first_latest

class ClassroomTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=db.DB_PATH
        db.DB_PATH=Path(self.tmp.name)/'test.db'
        db.init_db()
    def tearDown(self):
        db.DB_PATH=self.old
        self.tmp.cleanup()
    def test_content(self):
        self.assertEqual(len(UNITS),31)
        self.assertEqual(len(QUESTIONS),248)
        for q in QUESTIONS.values():
            self.assertEqual(len(q['options']),2 if q['type']=='OX' else 4)
            self.assertEqual(len(q['options']),len(set(q['options'])))
            self.assertIn(q['correct'],range(len(q['options'])))
    def test_capacity_and_normalization(self):
        a=db.register('  A  반  ','학생1')
        self.assertEqual(a['id'],db.register('A 반','학생1')['id'])
        for i in range(19):db.register('A',str(i))
        with self.assertRaises(ValueError):db.register('A','21번째')
        self.assertEqual(a['id'],db.register('A 반','학생1')['id'])
    def test_grade_note_retry_and_isolation(self):
        a=db.register('A','학생')
        b=db.register('B','학생')
        qs=questions(UNITS[0])
        with self.assertRaises(ValueError):db.mark(a['id'],'i1','check')
        db.mark(a['id'],'i1','learn')
        db.mark(a['id'],'i1','learn')
        self.assertEqual(len(db.snapshot(a['id'])['progress']),1)
        for i,q in enumerate(qs):
            self.assertFalse(db.answer(a['id'],q['id'],(q['correct']+1)%len(q['options']),str(i)))
        db.answer(a['id'],qs[0]['id'],0,'0')
        self.assertEqual(len(db.snapshot(a['id'])['attempts']),8)
        db.mark(a['id'],'i1','check')
        db.save_note(a['id'],qs[0]['id'],'차변과 대변을 구분')
        self.assertTrue(db.answer(a['id'],qs[0]['id'],qs[0]['correct'],'retry'))
        snapshot=db.snapshot(a['id'])
        first,last=first_latest(snapshot['attempts'])
        self.assertEqual(sum(r['correct'] for r in first),0)
        self.assertEqual(sum(r['correct'] for r in last),1)
        self.assertEqual(snapshot['notes'][0]['body'],'차변과 대변을 구분')
        self.assertEqual(db.snapshot(b['id'])['attempts'],[])
        self.assertEqual(len(db.snapshot()['attempts']),9)
    def test_password_and_invalid_answer(self):
        self.assertTrue(db.password_matches('한글암호','한글암호'))
        self.assertFalse(db.password_matches('wrong','right'))
        self.assertFalse(db.password_matches('',''))
        a=db.register('A','학생')
        with self.assertRaises(ValueError):db.answer(a['id'],'i1-ox0',99,'bad')

if __name__=='__main__':unittest.main()
