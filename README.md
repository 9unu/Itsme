# Itsme 프로젝트 (Django)
: 스마트워치에서 제안되는 무뚝뚝한 답장을 사용자 말투로 변환해서 제안하는 프로젝트

## Django 프론트 엔드 프로세스
사용자로부터 카카오톡 텍스트 파일을 업로드 받아 백엔드 프로세스로 넘기는 웹사이트 (삭제 선택 가능)

![프론트엔드 플로우 차트](https://github.com/9unu/Itsme_web/assets/124652096/07188f18-590a-4793-a77e-2ba72deef0ab)
## Django 백엔드 프로세스
1. 웹사이트에서 전달받은 카카오톡 텍스트 파일을 활용하여 사용자 말투로 문장의 문체를 변환하는 Seq2Seq 모델을 학습 
2. 학습된 변환기를 활용하여 스마트워치의 답장 리스트를 사용자 말투로 변환하여 Postgresql DB에 저장

![Web_flow_chart](https://github.com/9unu/Itsme_web/assets/124652096/ff56d659-e16e-40d2-a094-ba6bee377dde)
