"""Streamlit의 AppTest로 학생·교수자 실제 위젯 흐름을 검증합니다."""
import os
import tempfile
from pathlib import Path
from streamlit.testing.v1 import AppTest

def run_test():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['TAX_DB_PATH']=str(Path(tmp)/'classroom.db')
        os.environ['TEACHER_PASSWORD']='local-test-teacher-password'
        at=AppTest.from_file(str(Path(__file__).with_name('app.py')),default_timeout=40).run()
        assert not at.exception,[e.message for e in at.exception]
        at.radio(key='nav').set_value('학생 입장').run()
        at.text_input(key='login_org').input('검증 훈련원')
        at.text_input(key='login_name').input('가상학생')
        at.button(key='FormSubmitter:student_login-학생 입장').click().run()
        assert not at.exception,[e.message for e in at.exception]
        assert at.session_state['student']['name']=='가상학생'
        assert at.session_state['nav']=='학습하기'
        sid=at.session_state['student']['id']
        at.button(key='learn_i1').click().run()
        pp='practice:'+sid+':i1'
        at.radio(key=pp+':pick').set_value(1)
        at.button(key='FormSubmitter:'+pp+'-풀이 확인').click().run()
        at.button(key='practice_done_i1').click().run()
        assert not at.exception,[e.message for e in at.exception]
        from learning import questions,UNITS
        qs=questions(UNITS[0])
        prefix='quiz:'+sid+':i1:'
        for i,q in enumerate(qs):
            print('UI question',i+1)
            answer=(q['correct']+1)%len(q['options']) if i==0 else q['correct']
            at.radio(key=prefix+f'0:choice:{i}').set_value(answer)
            at.button(key='FormSubmitter:'+prefix+f'0:form:{i}-정답 확인').click().run()
            assert not at.exception,[e.message for e in at.exception]
            if i==0:
                at.text_area[0].input('틀린 용어를 다시 확인하기')
                at.button(key='FormSubmitter:note:quiz:'+sid+':'+q['id']+'-오답 메모 저장').click().run()
            if i<7:at.button(key=prefix+'next').click().run()
        at.button(key=prefix+'finish').click().run()
        at.radio(key='nav').set_value('나의 진도').run()
        assert not at.exception,[e.message for e in at.exception]
        at.radio(key='nav').set_value('오답 노트').run()
        assert len(at.expander)==1
        retry='retry:'+sid+':'+qs[0]['id']
        at.radio(key=retry+':pick').set_value(qs[0]['correct'])
        at.button(key='FormSubmitter:'+retry+'-재도전 채점').click().run()
        assert not at.exception,[e.message for e in at.exception]
        assert len(at.expander)==0
        at.checkbox[0].uncheck().run()
        assert len(at.expander)==1
        at.radio(key='nav').set_value('교수자 대시보드').run()
        at.text_input(key='teacher_input').input('wrong')
        at.button(key='FormSubmitter:teacher_login-교수자 입장').click().run()
        assert not at.session_state['teacher']
        at.text_input(key='teacher_input').input('local-test-teacher-password')
        at.button(key='FormSubmitter:teacher_login-교수자 입장').click().run()
        assert at.session_state['teacher']
        assert not at.exception,[e.message for e in at.exception]
        assert any('가상학생' in str(d.value) for d in at.dataframe)
        assert any('틀린 용어를 다시 확인하기' in str(d.value) for d in at.dataframe)
        print('PASS: student login, 3 learning stages, 8-question scoring, note save, progress, wrong notes, teacher login, dashboard and answer records.')

if __name__=='__main__':run_test()
