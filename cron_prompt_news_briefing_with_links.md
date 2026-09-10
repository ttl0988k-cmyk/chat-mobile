지금 실시간 뉴스에서 중요한 것 5개를 뽑아서 Supabase messages 테이블에 INSERT해줘. 이건 크론 작업이라 새 세션에서 실행되며, 결과는 모바일 앱(다온 작업실)에 표시된다.

[작업 절차]
1. 네이버 뉴스 홈(https://news.naver.com) 또는 다음 뉴스(https://news.daum.net)를 열어서 실시간 주요 뉴스 5개를 골라라. 브라우저 도구(browser_navigate, browser_snapshot 등)를 사용해라. 각 뉴스는 제목 + 언론사 + 1줄 요약 + 기사 링크로 구성.
2. Supabase에 INSERT할 준비: 아래 정보를 사용해라.
   - Supabase URL: https://gfpsahhfllozfqczyoza.supabase.co
   - API 키: C:\daon\.env 파일을 읽어서 SUPABASE_SERVICE_ROLE_KEY 값을 가져와라 (파일 읽기 도구 사용)
   - INSERT 경로: POST /rest/v1/messages
   - 헤더: apikey: <SERVICE_ROLE_KEY>, Authorization: Bearer <SERVICE_ROLE_KEY>, Content-Type: application/json
3. 먼저 기존 conversation이 있는지 확인해라:
   - GET /rest/v1/conversations?select=id,title,updated_at&order=updated_at.desc&limit=5 (같은 헤더 사용)
   - "뉴스 브리핑"이라는 제목의 conversation이 있으면 그것을 재사용하고, 없으면 새로 생성해라.
   - 새로 생성: POST /rest/v1/conversations body: {"user_id": "2e8e15e5-73bf-483f-bc96-5094cf2d9a01", "device": "mobile", "title": "뉴스 브리핑"}
   - 생성 후 GET으로 id를 조회해라.
4. 해당 conversation_id로 messages에 INSERT해라:
   - role: "assistant", user_id: "2e8e15e5-73bf-483f-bc96-5094cf2d9a01"
   - content: 아래 형식의 텍스트
   - metadata: {"type": "news_briefing", "source": "cron"}
5. content 형식 (마크다운):
   📰 실시간 뉴스 브리핑 (시각)
   
   1. [제목] - 언론사
      요약 한 줄
      🔗 [기사 보기](기사 URL)
   2. ... (5개까지)
   
   (시각은 현재 한국시간으로)

[중요]
- 반드시 service_role 키를 .env에서 읽어서 사용해라 (anon 키 아님!)
- user_id는 2e8e15e5-73bf-483f-bc96-5094cf2d9a01 (ttl0988k@gmail.com) 고정
- INSERT 성공 확인 후 HTTP 응답 코드를 보고해라
- 네트워크/도구 실패 시에도 최선의 결과를 만들어라
- 각 뉴스 항목에 실제 기사 URL을 🔗 [기사 보기](URL) 형식으로 반드시 포함해라. URL은 브라우저에서 수집한 실제 기사 링크여야 한다.
