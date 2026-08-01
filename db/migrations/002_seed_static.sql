-- 정적 시드 — DB_SCHEMA.md §1 시드 값 그대로 (멱등 적용).

-- claim_type: 고정 vocabulary + PUFFERY (requires_search=false, 예산 0)
INSERT INTO claim_type VALUES
 ('SUPERLATIVE_FIRST','최초/유일 주장',        TRUE, 4, 180, 3),
 ('RANKING',          '1위/순위 주장',          TRUE, 4,  30, 3),
 ('CLINICAL_COMPLETION','임상/시험 완료 주장',  TRUE, 3,  60, 3),
 ('AI_PERFORMANCE',   'AI 성능 주장',           TRUE, 4,  14, 3),
 ('GENERAL_FACTUAL',  '기타 검증가능 사실주장', TRUE, 3,  30, 3),
 ('PUFFERY',          '주관적 과장',           FALSE, 0, 999, 0)
ON CONFLICT (claim_type_code) DO NOTHING;

INSERT INTO verdict_type VALUES
 ('REFUTED','falsifier 기준 전부 충족하는 반례 존재'),
 ('NOT_REFUTED','실행 쿼리에서 기준 충족 반례 미발견. 참이라는 뜻 아님'),
 ('PUBLIC_SUBSTANTIATION_NOT_FOUND','공개 근거 자체가 확인되지 않음'),
 ('PUFFERY','주관적 과장. 검증 대상 아님')
ON CONFLICT (verdict_code) DO NOTHING;

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
  ('GENERAL_FACTUAL',     '{"scope":true,"metric":false,"timeframe":true,"target_entity":false,"geography":false}')
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
