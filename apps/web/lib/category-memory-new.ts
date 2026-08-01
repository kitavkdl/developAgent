export interface IndustryCategorySeed {
  categoryId: string;
  label: string;
  createdBy: "seed" | "demo";
  /** One-word centroid probes for the frontend tree demo (6–8). */
  centroidPhrases: string[];
}

export interface CategoryIndexPage {
  pageId: string;
  blockAddress: string;
  /** Short one-word range label shown on LEVEL 01 nodes. */
  label: string;
  keyRange: string;
  categoryIds: string[];
}

export const CATEGORY_REUSE_THRESHOLD_REFERENCE = 0.75;

const DEMO_PHRASE_BANK = [
  "세럼",
  "앰플",
  "크림",
  "토너",
  "쿠션",
  "선크림",
  "에센스",
  "마스크",
] as const;

/** LEVEL 04 token leaves for a selected one-word phrase (6–8). */
const TOKEN_LEAVES_BY_PHRASE: Record<string, string[]> = {
  세럼: ["세럼", "히알루론", "나이아신", "레티놀", "펩타이드", "세라마이드", "판테놀"],
  앰플: ["비건", "세럼", "진정", "앰플", "미백", "수분", "탄력"],
  크림: ["수분", "크림", "나이트", "아이", "장벽", "진정", "영양"],
  토너: ["토너", "패드", "각질", "pH", "수분", "진정", "미스트"],
  쿠션: ["쿠션", "파운데이션", "커버", "톤업", "리필", "SPF", "글로우"],
  선크림: ["선크림", "자외선", "무기자차", "톤업", "워터프루프", "스틱", "젤"],
  에센스: ["에센스", "부스팅", "발효", "수분", "광채", "안티에이징", "피토"],
  마스크: ["마스크", "팩", "시트", "모델링", "수면", "클레이", "버블"],
};

function demoCategory(
  categoryId: string,
  label: string,
  phrases: string[] = [...DEMO_PHRASE_BANK].slice(0, 7),
): IndustryCategorySeed {
  return {
    categoryId,
    label,
    createdBy: "demo",
    centroidPhrases: phrases,
  };
}

export const INDUSTRY_CATEGORY_SEEDS: IndustryCategorySeed[] = [
  {
    categoryId: "BEAUTY_PERSONAL_CARE",
    label: "뷰티",
    createdBy: "seed",
    centroidPhrases: [...DEMO_PHRASE_BANK],
  },
  {
    categoryId: "DIGITAL_HEALTH",
    label: "디지털헬스",
    createdBy: "seed",
    centroidPhrases: ["혈당", "수면", "원격", "웨어러블", "복약", "심박", "헬스케어"],
  },
  {
    categoryId: "EDUCATION_EDTECH",
    label: "에듀테크",
    createdBy: "seed",
    centroidPhrases: ["강의", "튜터", "코딩", "영어", "자격증", "학원", "부트캠프"],
  },
  {
    categoryId: "ELECTRONICS_APPLIANCE",
    label: "가전",
    createdBy: "seed",
    centroidPhrases: ["청소기", "냉장고", "세탁기", "노트북", "이어폰", "블렌더", "공기청정"],
  },
  {
    categoryId: "FASHION_APPAREL",
    label: "패션",
    createdBy: "seed",
    centroidPhrases: ["티셔츠", "아우터", "스니커즈", "데님", "가방", "지갑", "액세서리"],
  },
  {
    categoryId: "FINANCE_FINTECH",
    label: "핀테크",
    createdBy: "seed",
    centroidPhrases: ["주식", "적금", "대출", "보험", "증권", "금리", "결제"],
  },
  {
    categoryId: "FITNESS_WELLNESS",
    label: "피트니스",
    createdBy: "seed",
    centroidPhrases: ["헬스", "요가", "필라테스", "단백질", "홈트", "스트레칭", "PT"],
  },
  {
    categoryId: "FOOD_SUPPLEMENT",
    label: "건기식",
    createdBy: "seed",
    centroidPhrases: ["유산균", "오메가", "루테인", "비타민", "콜라겐", "프로틴", "간편식"],
  },
  {
    categoryId: "HOUSEHOLD_CHEMICAL",
    label: "생활화학",
    createdBy: "seed",
    centroidPhrases: ["세제", "유연제", "살균", "탈취", "방향", "주방", "곰팡이"],
  },
  {
    categoryId: "KIDS_BABY",
    label: "유아동",
    createdBy: "seed",
    centroidPhrases: ["분유", "기저귀", "유모차", "카시트", "장난감", "이유식", "세제"],
  },
  {
    categoryId: "PET",
    label: "반려동물",
    createdBy: "seed",
    centroidPhrases: ["사료", "간식", "보험", "병원", "모래", "스크래처", "장난감"],
  },
  {
    categoryId: "REALESTATE_INTERIOR",
    label: "부동산",
    createdBy: "seed",
    centroidPhrases: ["아파트", "분양", "중개", "인테리어", "리모델링", "소파", "매트리스"],
  },
  {
    categoryId: "TRAVEL_LODGING",
    label: "여행",
    createdBy: "seed",
    centroidPhrases: ["호텔", "리조트", "항공", "펜션", "글램핑", "패키지", "예약"],
  },
  {
    categoryId: "UNCATEGORIZED",
    label: "미분류",
    createdBy: "seed",
    centroidPhrases: ["기타", "미정", "폴백", "임시", "보류", "검토", "대기"],
  },
  // Frontend demo fillers so every leaf page stays in the 6–8 node band.
  demoCategory("DEMO_SKINCARE", "스킨케어"),
  demoCategory("DEMO_MAKEUP", "메이크업"),
  demoCategory("DEMO_HAIR", "헤어"),
  demoCategory("DEMO_BODY", "바디"),
  demoCategory("DEMO_DEVICE", "디바이스"),
  demoCategory("DEMO_CLINIC", "클리닉"),
  demoCategory("DEMO_MOBILE", "모바일"),
  demoCategory("DEMO_WEARABLE", "웨어러블"),
  demoCategory("DEMO_TELEMED", "원격의료"),
  demoCategory("DEMO_COURSE", "코스", ["강의", "커리큘럼", "퀴즈", "과제", "수료", "멘토", "라이브"]),
  demoCategory("DEMO_TUTOR", "튜터", ["튜터", "회화", "문법", "발음", "작문", "듣기", "단어"]),
  demoCategory("DEMO_BOOTCAMP", "부트캠프"),
  demoCategory("DEMO_TV", "TV"),
  demoCategory("DEMO_AUDIO", "오디오"),
  demoCategory("DEMO_KITCHEN", "주방가전"),
  demoCategory("DEMO_STREET", "스트릿"),
  demoCategory("DEMO_LUXURY", "럭셔리"),
  demoCategory("DEMO_SPORTSWEAR", "스포츠웨어"),
  demoCategory("DEMO_BROKER", "증권"),
  demoCategory("DEMO_BANK", "은행"),
  demoCategory("DEMO_INSURE", "보험"),
  demoCategory("DEMO_YOGA", "요가"),
  demoCategory("DEMO_GYM", "헬스장"),
  demoCategory("DEMO_SUPPLEMENT", "보충제"),
  demoCategory("DEMO_SNACK", "간편식"),
  demoCategory("DEMO_VITAMIN", "비타민"),
  demoCategory("DEMO_CLEANER", "세제"),
  demoCategory("DEMO_SCENT", "방향"),
  demoCategory("DEMO_DISINFECT", "살균"),
  demoCategory("DEMO_STROLLER", "유모차"),
  demoCategory("DEMO_TOY", "장난감"),
  demoCategory("DEMO_FORMULA", "분유"),
  demoCategory("DEMO_FEED", "사료"),
  demoCategory("DEMO_VET", "동물병원"),
  demoCategory("DEMO_LITTER", "모래"),
  demoCategory("DEMO_LISTING", "매물"),
  demoCategory("DEMO_REMODEL", "리모델링"),
  demoCategory("DEMO_FURNITURE", "가구"),
  demoCategory("DEMO_HOTEL", "호텔"),
  demoCategory("DEMO_FLIGHT", "항공"),
  demoCategory("DEMO_CAMP", "캠핑"),
  demoCategory("DEMO_MISC_A", "알파"),
  demoCategory("DEMO_MISC_B", "베타"),
  demoCategory("DEMO_MISC_C", "감마"),
  demoCategory("DEMO_MISC_D", "델타"),
  demoCategory("DEMO_MISC_E", "엡실론"),
  demoCategory("DEMO_MISC_F", "제타"),
];

export const CATEGORY_INDEX_PAGES: CategoryIndexPage[] = [
  {
    pageId: "leaf-page-01",
    blockAddress: "0x0118",
    label: "Beauty",
    keyRange: "Beauty",
    // Phase2: 뷰티 leaf is created at runtime after the rightmost probe.
    categoryIds: [
      "DEMO_SKINCARE",
      "DEMO_MAKEUP",
      "DEMO_HAIR",
      "DEMO_BODY",
      "DEMO_DEVICE",
      "DEMO_CLINIC",
    ],
  },
  {
    pageId: "leaf-page-02",
    blockAddress: "0x0120",
    label: "Digital",
    keyRange: "Digital",
    categoryIds: [
      "DIGITAL_HEALTH",
      "DEMO_MOBILE",
      "DEMO_WEARABLE",
      "DEMO_TELEMED",
      "DEMO_MISC_A",
      "DEMO_MISC_B",
      "DEMO_MISC_C",
    ],
  },
  {
    pageId: "leaf-page-03",
    blockAddress: "0x0128",
    label: "Edu",
    keyRange: "Edu",
    categoryIds: [
      "EDUCATION_EDTECH",
      "DEMO_COURSE",
      "DEMO_TUTOR",
      "DEMO_BOOTCAMP",
      "DEMO_MISC_D",
      "DEMO_MISC_E",
      "DEMO_MISC_F",
    ],
  },
  {
    pageId: "leaf-page-04",
    blockAddress: "0x0130",
    label: "Electro",
    keyRange: "Electro",
    categoryIds: [
      "ELECTRONICS_APPLIANCE",
      "DEMO_TV",
      "DEMO_AUDIO",
      "DEMO_KITCHEN",
      "DEMO_DEVICE",
      "DEMO_MISC_A",
      "DEMO_MISC_B",
    ],
  },
  {
    pageId: "leaf-page-05",
    blockAddress: "0x0138",
    label: "Fashion",
    keyRange: "Fashion",
    categoryIds: [
      "FASHION_APPAREL",
      "DEMO_STREET",
      "DEMO_LUXURY",
      "DEMO_SPORTSWEAR",
      "DEMO_MISC_C",
      "DEMO_MISC_D",
      "DEMO_MISC_E",
    ],
  },
  {
    pageId: "leaf-page-06",
    blockAddress: "0x0140",
    label: "Finance",
    keyRange: "Finance",
    categoryIds: [
      "FINANCE_FINTECH",
      "DEMO_BROKER",
      "DEMO_BANK",
      "DEMO_INSURE",
      "DEMO_MISC_F",
      "DEMO_MISC_A",
      "DEMO_MISC_B",
    ],
  },
  {
    pageId: "leaf-page-07",
    blockAddress: "0x0148",
    label: "Life",
    keyRange: "Life",
    categoryIds: [
      "FITNESS_WELLNESS",
      "FOOD_SUPPLEMENT",
      "HOUSEHOLD_CHEMICAL",
      "KIDS_BABY",
      "PET",
      "REALESTATE_INTERIOR",
      "TRAVEL_LODGING",
    ],
  },
];

export const DEMO_LOOKUP = {
  branchId: "leaf-page-01",
  categoryId: "BEAUTY_PERSONAL_CARE",
  phrase: "앰플",
  keyword: "앰플",
} as const;

/** Runtime-created leaf appended after L2 rightmost probe (phase2). */
export const DEMO_CREATED_CATEGORY_ID = DEMO_LOOKUP.categoryId;

export function categoryById(categoryId: string) {
  return INDUSTRY_CATEGORY_SEEDS.find(
    (category) => category.categoryId === categoryId,
  );
}

export function pageForCategory(categoryId: string) {
  const found = CATEGORY_INDEX_PAGES.find((page) =>
    page.categoryIds.includes(categoryId),
  );
  if (found) return found;
  if (categoryId === DEMO_CREATED_CATEGORY_ID) {
    return CATEGORY_INDEX_PAGES.find(
      (page) => page.pageId === DEMO_LOOKUP.branchId,
    );
  }
  return undefined;
}

export function phraseKeywords(phrase: string): string[] {
  const curated = TOKEN_LEAVES_BY_PHRASE[phrase];
  if (curated) return curated;

  const parts = Array.from(
    new Set(
      phrase
        .split(/\s+/)
        .map((keyword) => keyword.trim())
        .filter(Boolean),
    ),
  );

  if (parts.length >= 6) return parts.slice(0, 8);
  if (parts.length === 0) return [...DEMO_PHRASE_BANK].slice(0, 7);

  const padded = [...parts];
  for (const filler of DEMO_PHRASE_BANK) {
    if (padded.length >= 7) break;
    if (!padded.includes(filler)) padded.push(filler);
  }
  return padded;
}
