"""전산세무 2급 학습실 — 실행: streamlit run app.py"""
from pathlib import Path
import time
import uuid
from datetime import datetime, timezone, timedelta
import pandas as pd
import streamlit as st
import database as db
from learning import UNITS, QUESTIONS, UNIT_MAP, STAGES, SOURCES, questions, first_latest, percent

st.set_page_config(page_title='세무 한 걸음 · 전산세무 2급',page_icon='🌱',layout='wide')
db.init_db()
st.session_state.setdefault('student',None)
st.session_state.setdefault('teacher',False)
st.session_state.setdefault('nav','학습실 홈')

st.markdown('''<style>
.block-container{max-width:1250px;padding-top:2rem;padding-bottom:3rem}h1,h2,h3,p{word-break:keep-all}h1{font-size:2rem!important;letter-spacing:-1px}h2{font-size:1.45rem!important}h3{font-size:1.1rem!important}.stApp{background:#FAFBF7}[data-testid="stSidebar"]{background:#FFFFFF;border-right:1px solid #E5EBDD}[data-testid="stMetric"]{background:#fff;border:1px solid #e2eadb;border-radius:14px;padding:17px}[data-testid="stMetricValue"]{color:#52866C;font-size:1.8rem}.hero{background:#e8f2e5;border:1px solid #dbe8d3;border-radius:20px;padding:28px 32px;margin:16px 0 25px}.hero h2{font-size:1.9rem!important;line-height:1.6;color:#426348}.hero p{color:#7b9172}.eyebrow{color:#8b9f80;font-size:11px;letter-spacing:2px}.badge{display:inline-block;padding:4px 10px;background:#f4f8ec;color:#82976a;border:1px solid #dce8ce;border-radius:5px;font-size:11px}.concept{background:#fff;border:1px solid #e2e9da;border-radius:13px;padding:19px 22px;margin:12px 0}.concept strong{font-size:16px;color:#527343}.concept p{font-size:14px;color:#859478;margin:9px 0 0}.stTabs [data-baseweb="tab-list"]{gap:16px}.stTabs [data-baseweb="tab"]{font-size:13px;white-space:nowrap}button[kind="primary"]{border-radius:8px}div[data-testid="stForm"]{background:#fff;border-color:#e3eadb;border-radius:14px}textarea{font-size:14px!important}.muted{color:#9ca78e;font-size:12px}.footer{border-top:1px solid #e3e9db;padding-top:20px;margin-top:35px;color:#a4ae98;font-size:11px}@media(max-width:650px){.block-container{padding:1rem}.hero{padding:22px}.hero h2{font-size:1.45rem!important}.stTabs [data-baseweb="tab-list"]{gap:8px}h1{font-size:1.6rem!important}}
</style>''',unsafe_allow_html=True)

def navigate(page):
    st.session_state.nav=page

def logout():
    st.session_state.student=None
    st.session_state.teacher=False
    for key in list(st.session_state):
        if key.startswith(('quiz:','practice:','note:','retry:')):
            del st.session_state[key]
    st.session_state.nav='학생 입장'

def flash(kind,message):
    st.session_state.flash=(kind,message)

def student_login():
    try:
        student=db.register(st.session_state.login_org,st.session_state.login_name)
        st.session_state.student=student
        st.session_state.teacher=False
        st.session_state.nav='학습하기'
        flash('success','입장했어요. 나의 속도로 한 걸음씩 시작해요.')
    except (ValueError, OSError) as e:
        flash('error',str(e))

def teacher_login():
    if time.time()<st.session_state.get('teacher_lock_until',0):
        flash('error','잠시 후 다시 시도해 주세요.')
        return
    try:
        expected=st.secrets.get('teacher_password','')
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        expected=''
    expected=expected or db.initial_teacher_password()
    if db.password_matches(st.session_state.teacher_input,expected):
        st.session_state.teacher=True
        st.session_state.student=None
        st.session_state.teacher_failures=0
        st.session_state.teacher_input=''
        flash('success','교수자 대시보드에 입장했습니다.')
    else:
        count=st.session_state.get('teacher_failures',0)+1
        st.session_state.teacher_failures=count
        if count>=5:
            st.session_state.teacher_lock_until=time.time()+60
            st.session_state.teacher_failures=0
        flash('error','비밀번호를 확인해 주세요. 5회 실패하면 이 세션은 1분간 대기합니다.')

with st.sidebar:
    st.markdown('## 🌱 세무 한 걸음')
    st.caption('TAX LEARNING STUDIO')
    st.markdown('**전산세무 2급 학습실**')
    st.caption('2027 대비 · 공식 기준 확인 전')
    st.divider()
    st.radio('학습 메뉴',['학습실 홈','학습하기','나의 진도','오답 노트','교수자 대시보드','학습 안내·출처','학생 입장'],key='nav',label_visibility='collapsed')
    st.divider()
    if st.session_state.student:
        st.write('👋 **'+st.session_state.student['name']+' 님**')
        st.caption(st.session_state.student['org'])
        st.button('로그아웃',on_click=logout,use_container_width=True)
    elif st.session_state.teacher:
        st.success('교수자 접속 중')
        st.button('로그아웃',on_click=logout,use_container_width=True)
    else:
        st.caption('소속과 이름으로 입장하면\n학습 기록을 이어 갈 수 있어요.')
    st.info('처음이어도 괜찮아요.\n\n한 단원씩, 내 속도로.')

if 'flash' in st.session_state:
    kind,message=st.session_state.pop('flash')
    getattr(st,kind)(message)
student=st.session_state.student
state=db.snapshot(student['id']) if student else {'students':[],'progress':[],'attempts':[],'notes':[]}
first,latest=first_latest(state['attempts'])
completed={(r['unit'],r['stage']) for r in state['progress']}


def title(eyebrow,heading,description):
    st.caption(eyebrow)
    st.title(heading)
    st.caption(description)


def login_notice():
    st.info('소속과 이름으로 학생 입장 후 기록을 저장할 수 있어요.')
    st.button('학생 입장하기',on_click=navigate,args=('학생 입장',),key='need_login')


def metrics():
    finished=sum(all((u['id'],s) in completed for s in STAGES) for u in UNITS)
    wrong=sum(not r['correct'] for r in latest)
    cols=st.columns(4)
    cols[0].metric('완료한 단원',f'{finished} / {len(UNITS)}')
    cols[1].metric('단계 진도',f"{percent(len(completed),len(UNITS)*3)}%")
    cols[2].metric('최초 정답률',f"{percent(sum(r['correct'] for r in first),len(first))}%" if first else '—')
    cols[3].metric('복습할 오답',f'{wrong} 문항')


def note_editor(q, prefix):
    sid=student['id']
    old=next((n['body'] for n in state['notes'] if n['question']==q['id']),'')
    with st.form('note:'+prefix+':'+sid+':'+q['id']):
        body=st.text_area('왜 헷갈렸을까요?',value=old,max_chars=1200,placeholder='헷갈린 점과 다음에 기억할 내용을 적어 보세요.',key='note:body:'+prefix+':'+sid+':'+q['id'])
        if st.form_submit_button('오답 메모 저장'):
            db.save_note(sid,q['id'],body)
            st.success('메모를 저장했어요.')


def complete_stage(sid,uid,stage):
    try:
        db.mark(sid,uid,stage)
        flash('success',STAGES[stage]+' 완료! 다음 탭에서 학습을 이어 가세요.')
    except ValueError as e:
        flash('error',str(e))

def submit_question(sid,qid,choice_key,result_key,nonce):
    choice=st.session_state.get(choice_key)
    if choice is None:
        flash('warning','보기를 선택해 주세요.')
        return
    correct=db.answer(sid,qid,choice,nonce)
    st.session_state[result_key]={'correct':correct,'choice':choice}

def submit_retry(sid,qid,choice_key):
    choice=st.session_state.get(choice_key)
    if choice is None:
        flash('warning','보기를 선택해 주세요.')
        return
    correct=db.answer(sid,qid,choice,uuid.uuid4().hex)
    flash('success' if correct else 'warning','복습 성공! 기록을 갱신했어요.' if correct else '다시 핵심 개념을 읽어 보세요.')

def next_question(prefix,index):
    st.session_state[prefix+'index']=index

def restart_quiz(prefix,round_no):
    st.session_state[prefix+'round']=round_no+1
    st.session_state[prefix+'index']=0

def render_unit(unit):
    uid=unit['id']
    st.markdown('### '+unit['title'])
    labels=[('✓ ' if (uid,s) in completed else '')+label for s,label in STAGES.items()]
    learn,practice,check=st.tabs(labels)
    with learn:
        st.caption('STEP 01 · 핵심을 이해해요')
        for index,card in enumerate(unit['cards'],1):
            st.markdown(f"**0{index} · {card['term']}**")
            st.write(card['definition'])
        if unit['mode']=='실기':
            st.info('KcLep 실습 흐름\n\n'+'\n\n'.join(f'{i}. {s}' for i,s in enumerate(unit['steps'],1)))
            st.caption('웹에서는 판단·계산·전표 원리를 연습합니다. 실제 프로그램 조작은 교육용 KcLep에서 별도로 연습하세요.')
        st.button('배우기 완료',key='learn_'+uid,type='primary',disabled=not student,on_click=complete_stage,args=((student or {}).get('id'),uid,'learn'))
    with practice:
        st.caption('STEP 02 · 부담 없이 연습해요')
        prefix='practice:'+ (student['id'] if student else 'guest')+':'+uid
        with st.form(prefix):
            pick=st.radio(unit['practice'],range(len(unit['options'])),format_func=lambda i:unit['options'][i],index=None,key=prefix+':pick')
            if st.form_submit_button('풀이 확인'):
                if pick is None:
                    st.warning('보기를 선택해 주세요.')
                else:
                    st.session_state[prefix+':result']=pick==unit['correct']
        if prefix+':result' in st.session_state:
            correct=st.session_state[prefix+':result']
            (st.success if correct else st.info)('정답이에요!' if correct else '괜찮아요. 풀이를 읽어 볼까요?')
            st.write(unit['explain'])
            st.button('해 보기 완료',key='practice_done_'+uid,disabled=not student,on_click=complete_stage,args=((student or {}).get('id'),uid,'practice'))
    with check:
        st.caption('STEP 03 · OX 3문항 + 4지선다 5문항')
        if not student:
            st.info('학생 입장 후 즉시 채점과 오답 저장을 이용할 수 있어요.')
            return
        qs=questions(unit)
        prefix='quiz:'+student['id']+':'+uid+':'
        idx=st.session_state.setdefault(prefix+'index',0)
        round_no=st.session_state.setdefault(prefix+'round',0)
        q=qs[idx]
        result_key=prefix+f'{round_no}:result:{idx}'
        result=st.session_state.get(result_key)
        nonce=st.session_state.setdefault(prefix+f'{round_no}:nonce:{idx}',uuid.uuid4().hex)
        st.progress(idx/8,text=f"{q['type']} · {idx+1} / 8문항")
        with st.form(prefix+f'{round_no}:form:{idx}'):
            choice=st.radio(q['prompt'],range(len(q['options'])),format_func=lambda i:q['options'][i],index=None,key=prefix+f'{round_no}:choice:{idx}',disabled=result is not None)
            st.form_submit_button('정답 확인',type='primary',disabled=result is not None,on_click=submit_question,args=(student['id'],q['id'],prefix+f'{round_no}:choice:{idx}',result_key,nonce))
        if result is not None:
            (st.success if result['correct'] else st.warning)('정답이에요!' if result['correct'] else '오답 노트에 자동 저장했어요.')
            st.write('**정답: '+q['options'][q['correct']]+'**')
            st.write(q['explain'])
            if not result['correct']:
                note_editor(q,'quiz')
            if idx<7:
                st.button('다음 문항 →',key=prefix+'next',type='primary',on_click=next_question,args=(prefix,idx+1))
            else:
                st.button('확인하기 완료',key=prefix+'finish',type='primary',on_click=complete_stage,args=(student['id'],uid,'check'))
        if (uid,'check') in completed:
            st.success('이 단원의 확인하기를 완료했어요.')
            st.button('8문항 다시 풀기',key=prefix+'restart',on_click=restart_quiz,args=(prefix,round_no))


def render_learning():
    title('LEARNING JOURNEY','오늘의 배움을 시작해요.','과목 → 단원 → 배우기·해 보기·확인하기 탭으로 이동하세요.')
    if not student:
        st.info('지금은 미리보기예요. 학생 입장 후 학습 진도를 저장할 수 있어요.')
    modes=['입문','필기','실기']
    for mode,mode_tab in zip(modes,st.tabs(['처음 배우는 회계','필기 · 개념 다지기','실기 · 실무 익히기'])):
        with mode_tab:
            subset=[u for u in UNITS if u['mode']==mode]
            subjects=list(dict.fromkeys(u['subject'] for u in subset))
            for subject,subject_tab in zip(subjects,st.tabs(subjects)):
                with subject_tab:
                    selected=[u for u in subset if u['subject']==subject]
                    unit_tabs=st.tabs([u['title'] for u in selected])
                    for unit,unit_tab in zip(selected,unit_tabs):
                        with unit_tab:
                            render_unit(unit)


def render_progress():
    title('MY PROGRESS','조금씩, 쌓이고 있어요.','단계 진도와 확인하기 정답률을 따로 확인하세요.')
    if not student:
        login_notice();return
    metrics()
    st.progress(len(completed)/(len(UNITS)*3))
    rows=[]
    for subject in dict.fromkeys(u['subject'] for u in UNITS):
        ids={u['id'] for u in UNITS if u['subject']==subject}
        a=[r for r in first if r['unit'] in ids]
        b=[r for r in latest if r['unit'] in ids]
        rows.append({'과목':subject,'단계 진도(%)':percent(sum(uid in ids for uid,s in completed),len(ids)*3),'최초 정답률(%)':percent(sum(r['correct'] for r in a),len(a)) if a else None,'최근 정답률(%)':percent(sum(r['correct'] for r in b),len(b)) if b else None})
    st.subheader('과목별 학습 현황')
    st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    detail=[{'과목':u['subject'],'단원':u['title'],**{label:'✓ 완료' if (u['id'],s) in completed else '미완료' for s,label in STAGES.items()}} for u in UNITS]
    st.subheader('단원별 완료 단계')
    st.dataframe(pd.DataFrame(detail),hide_index=True,use_container_width=True)


def render_notes():
    title('MISTAKES MAKE PROGRESS','틀린 만큼, 더 단단하게.','틀린 이유를 적고 다시 풀어 보세요. 재도전 후에도 기록은 남아요.')
    if not student:
        login_notice();return
    historical={r['question'] for r in state['attempts'] if not r['correct']}
    last={r['question']:r for r in latest}
    st.caption(f"누적 오답 {len(historical)}문항 · 현재 복습할 오답 {sum(not r['correct'] for r in latest)}문항")
    only=st.checkbox('아직 틀린 문항만 보기',value=True)
    selected=[QUESTIONS[q] for q in QUESTIONS if q in historical and (not only or not last[q]['correct'])]
    if not selected:
        st.success('조건에 맞는 오답이 없어요. 확인하기를 풀거나 필터를 바꿔 보세요.');return
    for q in selected:
        resolved=last[q['id']]['correct']
        with st.expander(('✓ 복습 완료 · ' if resolved else '복습 필요 · ')+UNIT_MAP[q['unit']]['title']+' / '+q['type']+' / '+q['id']):
            st.write('**'+q['prompt']+'**')
            wrong=next(r for r in reversed(state['attempts']) if r['question']==q['id'] and not r['correct'])
            st.write('틀렸던 내 답: '+q['options'][wrong['answer']])
            st.write('정답: '+q['options'][q['correct']])
            st.info(q['explain'])
            note_editor(q,'notebook')
            prefix='retry:'+student['id']+':'+q['id']
            with st.form(prefix):
                choice=st.radio('다시 풀기',range(len(q['options'])),format_func=lambda i:q['options'][i],index=None,key=prefix+':pick')
                st.form_submit_button('재도전 채점',on_click=submit_retry,args=(student['id'],q['id'],prefix+':pick'))


def safe_csv(frame):
    frame=frame.copy()
    for col in frame.select_dtypes(include=['object']).columns:
        frame[col]=frame[col].map(lambda v:"'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v)
    return frame.to_csv(index=False).encode('utf-8-sig')


def render_teacher():
    title("TEACHER'S DESK",'우리 반의 배움을 한눈에.','최초 응답으로 어려운 문항을 찾고, 최근 결과로 성장을 확인하세요.')
    if not st.session_state.teacher:
        with st.form('teacher_login'):
            st.text_input('교수자 비밀번호',type='password',key='teacher_input')
            st.form_submit_button('교수자 입장',on_click=teacher_login,type='primary')
        st.caption('초기 비밀번호는 서버의 data/teacher_password.txt에서 확인합니다. 직접 지정하려면 실행 안내를 참고하세요.')
        # 학생 화면 방문 시에도 첫 실행 비밀번호가 생성되도록 하지는 않습니다.
        db.initial_teacher_password()
        return
    data=db.snapshot()
    st.button('최신 기록 새로고침',key='teacher_refresh')
    first_all,last_all=first_latest(data['attempts'])
    cols=st.columns(4)
    cols[0].metric('등록 학생',f"{len(data['students'])} / 20명")
    cols[1].metric('평균 단계 진도',f"{percent(len(data['progress']),len(data['students'])*len(UNITS)*3)}%")
    cols[2].metric('최초 응답 정답률',f"{percent(sum(r['correct'] for r in first_all),len(first_all))}%" if first_all else '—')
    cols[3].metric('미해결 오답',f"{sum(not r['correct'] for r in last_all)}건")
    if not data['students']:
        st.info('학생이 소속과 이름으로 입장하면 기록이 나타납니다.');return
    smap={s['id']:s for s in data['students']}
    sid=st.selectbox('학생 선택',['all']+list(smap),format_func=lambda i:'전체 학생' if i=='all' else smap[i]['org']+' · '+smap[i]['name'])
    subjects=['전체']+list(dict.fromkeys(u['subject'] for u in UNITS))
    subject=st.selectbox('과목 선택',subjects)
    ids={u['id'] for u in UNITS if subject=='전체' or u['subject']==subject}
    included=[s for s in data['students'] if sid=='all' or s['id']==sid]
    student_tab,question_tab,response_tab=st.tabs(['학생별 진도','많이 틀린 문항','응답·오답 메모'])
    with student_tab:
        rows=[]
        for s in included:
            p=[r for r in data['progress'] if r['student']==s['id'] and r['unit'] in ids]
            pairs={(r['unit'],r['stage']) for r in p}
            a=[r for r in first_all if r['student']==s['id'] and r['unit'] in ids]
            b=[r for r in last_all if r['student']==s['id'] and r['unit'] in ids]
            rows.append({'소속':s['org'],'이름':s['name'],'단계 진도(%)':percent(len(p),len(ids)*3),'완료 단원':sum(all((uid,t) in pairs for t in STAGES) for uid in ids),'최초 정답률(%)':percent(sum(r['correct'] for r in a),len(a)) if a else None,'최근 정답률(%)':percent(sum(r['correct'] for r in b),len(b)) if b else None,'미해결 오답':sum(not r['correct'] for r in b)})
        frame=pd.DataFrame(rows)
        st.dataframe(frame,hide_index=True,use_container_width=True)
        st.download_button('학생 현황 CSV 내려받기',safe_csv(frame),file_name='전산세무_학습현황.csv',mime='text/csv')
        if sid!='all':
            pairs={(r['unit'],r['stage']) for r in data['progress'] if r['student']==sid}
            st.subheader('선택 학생의 단원별 진도')
            detail=[{'과목':u['subject'],'단원':u['title'],**{label:'완료' if (u['id'],s) in pairs else '미완료' for s,label in STAGES.items()}} for u in UNITS if u['id'] in ids]
            st.dataframe(pd.DataFrame(detail),hide_index=True,use_container_width=True)
    chosen=[r for r in first_all if (sid=='all' or r['student']==sid) and r['unit'] in ids]
    with question_tab:
        st.caption('최초 응답 기준 · 오답 학생 수 순 · 정답률 분모는 응답한 학생입니다.')
        stats=[]
        for q in QUESTIONS.values():
            a=[r for r in chosen if r['question']==q['id']]
            if a:
                wrong=sum(not r['correct'] for r in a)
                stats.append({'문항ID':q['id'],'단원':UNIT_MAP[q['unit']]['title'],'문항':q['prompt'],'응답 학생':len(a),'오답 학생':wrong,'오답률(%)':percent(wrong,len(a))})
        if not stats:
            st.info('분석할 응답이 아직 없습니다.')
        else:
            frame=pd.DataFrame(stats).sort_values(['오답 학생','오답률(%)'],ascending=False)
            st.dataframe(frame,hide_index=True,use_container_width=True)
            qid=st.selectbox('선택지별 응답 확인',frame['문항ID'].tolist(),format_func=lambda i:i+' · '+QUESTIONS[i]['prompt'])
            q=QUESTIONS[qid]
            dist=pd.DataFrame({'선택지':q['options'],'응답 수':[sum(r['question']==qid and r['answer']==i for r in chosen) for i in range(len(q['options']))]})
            st.bar_chart(dist.set_index('선택지'),color='#A6C5B0')
            st.write('정답: '+q['options'][q['correct']])
            st.caption(q['explain'])
    with response_tab:
        attempts=[r for r in data['attempts'] if (sid=='all' or r['student']==sid) and r['unit'] in ids]
        note_map={(r['student'],r['question']):r['body'] for r in data['notes']}
        rows=[]
        for r in reversed(attempts):
            q=QUESTIONS[r['question']]
            s=smap[r['student']]
            kst=datetime.fromisoformat(r['created']).astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')
            rows.append({'소속':s['org'],'이름':s['name'],'단원':UNIT_MAP[r['unit']]['title'],'문항ID':q['id'],'문항':q['prompt'],'제출 답':q['options'][r['answer']],'정답':q['options'][q['correct']],'결과':'정답' if r['correct'] else '오답','오답 메모':note_map.get((r['student'],q['id']),''),'제출시각(한국)':kst})
        if rows:
            frame=pd.DataFrame(rows)
            st.dataframe(frame,hide_index=True,use_container_width=True)
            st.download_button('응답·메모 CSV 내려받기',safe_csv(frame),file_name='전산세무_응답기록.csv',mime='text/csv')
        else:
            st.info('제출된 응답이 아직 없습니다.')


def render_guide():
    title('GUIDE & REFERENCES','배움의 기준을 확인해요.','자료 확인일: 2026년 11월 14일')
    st.warning('2027년 공식 출제기준은 웹 검색에서 확인하지 못했습니다. 현재 공개 평가범위를 바탕으로 만든 잠정 학습안입니다. 공식 공고 후 범위와 적용 세법을 검토해 업데이트해야 합니다.')
    st.markdown('### 학습 구성')
    st.write('31개 단원 · 핵심 개념 93개 · OX 93문항 + 4지선다 155문항 = 확인 문항 248개')
    st.write('이론 30%·실무 70% 구조를 참고했습니다. OX는 개념 확인용이며 실제 KcLep 조작 실습은 별도로 진행합니다.')
    st.markdown('### 참고한 웹 자료')
    for label,url in SOURCES:
        st.markdown(f'- [{label}]({url})')
    st.write('기초 개념과 예제는 교육용으로 직접 작성했습니다. 세무 설명은 국세청 안내를 참고했으며 기출문제를 복제하지 않았습니다. 세율·공제한도·보험료율 등은 2027 적용 자료 확인이 필요합니다.')
    st.markdown('### 기록과 식별')
    st.write('소속·이름·학습 완료·응답·오답 메모를 서버에 저장하고 담당 교수자에게 보여 줍니다. 소속과 이름을 똑같이 입력하면 기록을 이어 갑니다. 동명이인은 이름 뒤에 번호를 붙여 주세요. 실제 주민등록번호 등 민감한 정보는 입력하지 마세요.')
    st.write('이 방식은 이름에 따른 학습자 식별입니다. 같은 소속·이름을 아는 사람의 재입장이 가능하므로 수업 참여자에게만 사이트를 공유해 주세요.')
    st.markdown('### 진도·정답률')
    st.write('진도는 완료한 단계 수 ÷ 전체 93단계입니다. 확인하기는 단원 8문항에 모두 응답해야 완료됩니다. 최초 정답률은 첫 응답, 최근 정답률은 마지막 응답을 기준으로 계산합니다.')


page=st.session_state.nav
if page=='학습실 홈':
    title('LEARN AT YOUR OWN PACE','오늘도, 한 걸음 더.','어려운 세무도 작게 나누면 쉬워져요.')
    st.markdown('<div class="hero"><span class="badge">처음 시작하는 전산세무 2급</span><h2>이해하고, 연습하고,<br>내 것으로 만들어요.</h2><p>배우기 → 해 보기 → 확인하기<br>세 단계로 쌓는 나의 세무 실력.</p></div>',unsafe_allow_html=True)
    st.button('학습 시작하기 →',on_click=navigate,args=('학습하기',),type='primary')
    metrics()
    st.subheader('나의 학습 여정')
    outline=[{'구분':u['mode'],'과목':u['subject'],'단원':u['title'],'단계':'배우기 → 해 보기 → 확인하기'} for u in UNITS]
    keyword=st.text_input('단원 검색',placeholder='예: 부가가치세, 원가')
    shown=[r for r in outline if not keyword or keyword in r['과목']+r['단원']]
    st.dataframe(pd.DataFrame(shown),hide_index=True,use_container_width=True)
    st.caption('2027 공식 출제기준 확인 전의 잠정 구성입니다. 적용 기준은 학습 안내에서 확인하세요.')
elif page=='학생 입장':
    title('WELCOME TO CLASS','반가워요, 배움을 시작해요.','소속과 이름을 다음 입장 때도 똑같이 입력해 주세요.')
    if student:
        st.success(student['name']+' 님으로 입장해 있어요.')
        st.button('학습하러 가기',on_click=navigate,args=('학습하기',),type='primary')
    else:
        with st.form('student_login'):
            st.text_input('소속',placeholder='예: 한걸음직업훈련원 1반',max_chars=60,key='login_org')
            st.text_input('이름',placeholder='예: 김하늘',max_chars=40,key='login_name')
            st.caption('학습 기록과 응답은 담당 교수자가 확인합니다. 동명이인은 이름 뒤 번호로 구분하세요.')
            st.form_submit_button('학생 입장',type='primary',on_click=student_login)
elif page=='학습하기':
    render_learning()
elif page=='나의 진도':
    render_progress()
elif page=='오답 노트':
    render_notes()
elif page=='교수자 대시보드':
    render_teacher()
else:
    render_guide()
st.markdown('<div class="footer">🌱 세무 한 걸음 · 오늘의 작은 이해가 내일의 자신감으로.</div>',unsafe_allow_html=True)
