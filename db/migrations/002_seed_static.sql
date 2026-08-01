-- 정적 시드 — DB_SCHEMA.md §1 시드 값 그대로 (멱등 적용).

-- claim_type: 고정 vocabulary + PUFFERY (requires_search=false, 예산 0)
INSERT INTO claim_type VALUES
 ('SUPERLATIVE_FIRST','최초/유일 주장',        TRUE, 4, 180, 3),
 ('RANKING',          '1위/순위 주장',          TRUE, 4,  30, 3),
 ('CLINICAL_COMPLETION','임상/시험 완료 주장',  TRUE, 3,  60, 3),
 ('AI_PERFORMANCE',   'AI 성능 주장',           TRUE, 4,  14, 3),
 ('GENERAL_FACTUAL',  '기타 검증가능 사실주장', TRUE, 3,  30, 3),
 ('SELF_REPORTED_PRIVATE_METRIC', '비상장/사기업 자체발표 지표', TRUE, 3, 90, 3),
 ('PUFFERY',          '주관적 과장',           FALSE, 0, 999, 0)
ON CONFLICT (claim_type_code) DO NOTHING;

INSERT INTO verdict_type VALUES
 ('CONTRADICTED','falsifier 기준 전부 충족하는 반박 근거 존재'),
 ('CORROBORATED','falsifier와 동일한 기준을 전부 충족하는 뒷받침 근거 존재. 완전한 사실 확정은 아님'),
 ('UNVERIFIED','실행 쿼리 범위에서 반증도 뒷받침 근거도 미발견. 참도 거짓도 아님 — 판단 유보'),
 ('PUFFERY','주관적 과장. 검증 대상 아님')
ON CONFLICT (verdict_code) DO NOTHING;

-- 구 4값(REFUTED/NOT_REFUTED/PUBLIC_SUBSTANTIATION_NOT_FOUND) 정리 — 참조하는
-- verdict 행이 남아있지 않은 룩업 값만 제거 (이미 배포된 환경의 과거 판정
-- 기록은 verdict_type FK 때문에 안전하게 남겨둔다).
DELETE FROM verdict_type
WHERE verdict_code IN ('REFUTED', 'NOT_REFUTED', 'PUBLIC_SUBSTANTIATION_NOT_FOUND')
  AND NOT EXISTS (
    SELECT 1 FROM verdict v WHERE v.verdict_code = verdict_type.verdict_code
  );

-- falsifier_spec 초기값 (DB_SCHEMA.md — "반드시 이 값으로 시드")
-- 읽는 법: 최초 주장은 scope+timeframe이 맞아야 깨지고 target은 무관.
--          1위 주장은 metric+timeframe+geography. 임상 완료는 target_entity만.
INSERT INTO falsifier_spec (falsifier_spec_id, claim_type_code, required_match_fields, prompt_version)
SELECT gen_random_uuid(), v.code, v.fields::jsonb, 'v1'
FROM (VALUES
  ('SUPERLATIVE_FIRST',   '{"scope":true,"metric":false,"timeframe":true,"target_entity":false,"geography":false}'),
  ('RANKING',             '{"scope":false,"metric":true,"timeframe":true,"target_entity":false,"geography":true}'),
  ('CLINICAL_COMPLETION', '{"scope":false,"metric":false,"timeframe":false,"target_entity":true,"geography":false}'),
  ('AI_PERFORMANCE',      '{"scope":true,"metric":true,"timeframe":true,"target_entity":false,"geography":false}'),
  ('GENERAL_FACTUAL',     '{"scope":true,"metric":false,"timeframe":true,"target_entity":false,"geography":false}'),
  -- 자체발표 지표: 같은 회사·같은 지표·같은 시점의 모순만 반례로 인정 (엄격) —
  -- H1(자기모순) 외의 우연한 일치를 반례로 오인하지 않기 위해 target_entity도 필수.
  ('SELF_REPORTED_PRIVATE_METRIC', '{"scope":true,"metric":true,"timeframe":true,"target_entity":true,"geography":false}')
) AS v(code, fields)
WHERE NOT EXISTS (SELECT 1 FROM falsifier_spec f WHERE f.claim_type_code = v.code);

-- 업종 카테고리 시드 (DB_SCHEMA.md §4 — 13종). centroid는 scripts/seed_categories.py에서 계산.
-- ⚠️ 데모 데이터는 2~3개 업종(뷰티/건강기능식품 등)에 몰아서 시드할 것 — 파티셔닝 때문에
--    카테고리 간 캐시 히트가 안 생겨 reuse_count가 왜소해 보임.
INSERT INTO industry_category (category_id, label, created_by) VALUES
  ('BEAUTY_PERSONAL_CARE', '뷰티/퍼스널케어',   'seed'),
  ('ELECTRONICS_APPLIANCE','가전/전자',         'seed'),
  ('EDUCATION_EDTECH',     '교육/에듀테크',     'seed'),
  ('FOOD_SUPPLEMENT',      '식품/건강기능식품', 'seed'),
  ('FINANCE_FINTECH',      '금융/핀테크',       'seed'),
  ('FASHION_APPAREL',      '패션/의류',         'seed'),
  ('PET',                  '반려동물',          'seed'),
  ('KIDS_BABY',            '유아동',            'seed'),
  ('FITNESS_WELLNESS',     '피트니스/웰니스',   'seed'),
  ('HOUSEHOLD_CHEMICAL',   '생활화학',          'seed'),
  ('DIGITAL_HEALTH',       '디지털헬스',        'seed'),
  ('TRAVEL_LODGING',       '여행/숙박',         'seed'),
  ('REALESTATE_INTERIOR',  '부동산/인테리어',   'seed'),
  ('UNCATEGORIZED',        '미분류 (폴백)',     'seed')
ON CONFLICT (category_id) DO NOTHING;
