-- 정적 시드: verdict_type / claim_type / falsifier_spec / 업종 13종
-- 업종 centroid_embedding은 API 키가 필요하므로 scripts/seed_categories.py에서 별도 계산.
-- 임계값·예산·TTL은 전부 미검증 추정치 (DECISIONS D-11). 실측 후 이 파일에서 조정.

INSERT INTO verdict_type (code, label_ko, description) VALUES
  ('REFUTED',                          '반례 발견',
   'falsifier 기준을 전부 충족하는 반례 문서가 실재함. evidence_link 필수.'),
  ('NOT_REFUTED',                      '반례 미발견',
   '실행한 N개 쿼리에서 기준 충족 반례를 찾지 못함. "사실이다"라는 뜻이 아님.'),
  ('PUBLIC_SUBSTANTIATION_NOT_FOUND',  '공개 실증자료 미확인',
   '실증이 필요한 유형인데 공개 근거 자체가 확인되지 않음.'),
  ('PUFFERY',                          '주관적 과장 표현',
   '검증 대상이 아님. 검색을 실행하지 않음 (tool_call 0건).')
ON CONFLICT (code) DO NOTHING;

-- 검색 예산: SCIENTIFIC 경로 최대 3 / GENERAL 경로 최대 4 (ARCHITECTURE §3)
INSERT INTO claim_type (code, label_ko, default_search_budget, max_evidence_per_query, default_ttl_days) VALUES
  ('SUPERLATIVE_FIRST',   '최초/유일 주장',     4, 5, 180),
  ('RANKING',             '순위/1위 주장',      4, 5,  30),
  ('CLINICAL_COMPLETION', '임상/인증 완료 주장', 3, 5,  90),
  ('AI_PERFORMANCE',      'AI 성능 주장',       4, 5,  14),
  ('GENERAL_FACTUAL',     '일반 사실 주장',     4, 5,  60)
ON CONFLICT (code) DO NOTHING;

-- required_match_fields: true인 필드가 전부 충족돼야만 코드가 REFUTED 조립 (PRD N1)
--  * SUPERLATIVE_FIRST/RANKING: 반례는 '타사의 선행/상충 기록'이므로 target_match는 요구하지 않음.
--    대신 동일 범주(scope)·동일 지표(metric)·시점(timeframe)이 전부 일치해야 함.
--  * CLINICAL_COMPLETION: 그 제품/회사 자체에 대한 기록이어야 함(target). 타사 임상은 반례 아님.
--  * GENERAL_FACTUAL: 주체(target)에 대한 반대 사실의 1차 자료 + 시점 일치.
INSERT INTO falsifier_spec (claim_type_code, required_match_fields, prompt_version) VALUES
  ('SUPERLATIVE_FIRST',   '{"scope_match": true, "metric_match": true, "timeframe_match": true, "target_match": false}', 'v1'),
  ('RANKING',             '{"scope_match": true, "metric_match": true, "timeframe_match": true, "target_match": false}', 'v1'),
  ('CLINICAL_COMPLETION', '{"scope_match": true, "metric_match": false, "timeframe_match": false, "target_match": true}', 'v1'),
  ('AI_PERFORMANCE',      '{"scope_match": true, "metric_match": true, "timeframe_match": false, "target_match": false}', 'v1'),
  ('GENERAL_FACTUAL',     '{"scope_match": true, "metric_match": false, "timeframe_match": true, "target_match": true}', 'v1')
ON CONFLICT (claim_type_code) DO NOTHING;

-- 업종 13종 (centroid는 seed 스크립트에서 채움). 데모 시드는 D-08에 따라 2~3개 업종에 몰 것.
INSERT INTO industry_category (code, label_ko, created_by) VALUES
  ('cosmetics_beauty',   '화장품/뷰티',      'seed'),
  ('food_beverage',      '식품/음료',        'seed'),
  ('home_appliance',     '가전',             'seed'),
  ('health_supplement',  '건강기능식품',      'seed'),
  ('fashion',            '패션/의류',        'seed'),
  ('mobile_app_service', '모바일 앱/서비스', 'seed'),
  ('finance',            '금융',             'seed'),
  ('education',          '교육',             'seed'),
  ('travel_lodging',     '여행/숙박',        'seed'),
  ('automotive',         '자동차',           'seed'),
  ('furniture_interior', '가구/인테리어',    'seed'),
  ('medical_device',     '의료기기',         'seed'),
  ('baby_kids',          '유아용품',         'seed')
ON CONFLICT (code) DO NOTHING;
