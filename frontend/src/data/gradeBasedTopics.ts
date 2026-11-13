// Grade-based topic organization for Edexcel GCSE Mathematics

export type GradeLevel = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9;
export type DomainType = 'number' | 'algebra' | 'ratio' | 'geometry' | 'probability' | 'statistics';

export interface GradeTopic {
  id: string;
  title: string;
  domain: DomainType;
  grade: GradeLevel;
  icon: string;
}

// Grade 1 Topics (16 topics)
export const GRADE_1_TOPICS: GradeTopic[] = [
  { id: 'place-value', title: 'Place Value', domain: 'number', grade: 1, icon: '123' },
  { id: 'ordering-integers', title: 'Ordering Integers', domain: 'number', grade: 1, icon: '↕️' },
  { id: 'ordering-decimals', title: 'Ordering Decimals', domain: 'number', grade: 1, icon: '0.1' },
  { id: 'reading-scales', title: 'Reading Scales', domain: 'number', grade: 1, icon: '📏' },
  { id: 'notation', title: 'Mathematical Notation', domain: 'number', grade: 1, icon: '±' },
  { id: 'real-life-tables', title: 'Real-Life Tables', domain: 'number', grade: 1, icon: '📊' },
  { id: 'algebraic-conventions', title: 'Algebraic Conventions', domain: 'algebra', grade: 1, icon: 'x' },
  { id: 'coordinates', title: 'Coordinates', domain: 'algebra', grade: 1, icon: '(x,y)' },
  { id: 'geometric-definitions', title: 'Geometric Definitions', domain: 'geometry', grade: 1, icon: '△' },
  { id: 'polygons', title: 'Polygons', domain: 'geometry', grade: 1, icon: '⬡' },
  { id: 'symmetries', title: 'Symmetries', domain: 'geometry', grade: 1, icon: '⚖️' },
  { id: 'tessellations', title: 'Tessellations', domain: 'geometry', grade: 1, icon: '🔲' },
  { id: 'angles-names', title: 'Names of Angles', domain: 'geometry', grade: 1, icon: '∠' },
  { id: 'probability-scale', title: 'Probability Scale', domain: 'probability', grade: 1, icon: '0-1' },
  { id: 'tally-charts', title: 'Tally Charts', domain: 'statistics', grade: 1, icon: '||||' },
  { id: 'pictograms', title: 'Pictograms', domain: 'statistics', grade: 1, icon: '👤' }
];

// Grade 2 Topics (51 topics)
export const GRADE_2_TOPICS: GradeTopic[] = [
  // Number (18 topics)
  { id: 'adding-integers', title: 'Adding Integers', domain: 'number', grade: 2, icon: '+' },
  { id: 'subtracting-integers', title: 'Subtracting Integers', domain: 'number', grade: 2, icon: '-' },
  { id: 'four-rules-negatives', title: 'Four Rules of Negatives', domain: 'number', grade: 2, icon: '±' },
  { id: 'multiplying-integers', title: 'Multiplying Integers', domain: 'number', grade: 2, icon: '×' },
  { id: 'dividing-integers', title: 'Dividing Integers', domain: 'number', grade: 2, icon: '÷' },
  { id: 'inverse-operations', title: 'Inverse Operations', domain: 'number', grade: 2, icon: '⇄' },
  { id: 'money', title: 'Money', domain: 'number', grade: 2, icon: '£' },
  { id: 'negatives-real-life', title: 'Negatives in Real Life', domain: 'number', grade: 2, icon: '🌡️' },
  { id: 'intro-fractions', title: 'Introduction to Fractions', domain: 'number', grade: 2, icon: '½' },
  { id: 'equivalent-fractions', title: 'Equivalent Fractions', domain: 'number', grade: 2, icon: '=' },
  { id: 'simplifying-fractions', title: 'Simplifying Fractions', domain: 'number', grade: 2, icon: '↓' },
  { id: 'halfway-values', title: 'Half-Way Values', domain: 'number', grade: 2, icon: '⬌' },
  { id: 'factors-multiples', title: 'Factors, Multiples, Primes', domain: 'number', grade: 2, icon: '🔢' },
  { id: 'powers-of-10', title: 'Powers of 10', domain: 'number', grade: 2, icon: '10ⁿ' },
  { id: 'rounding-10-100', title: 'Rounding (10, 100, 1000)', domain: 'number', grade: 2, icon: '≈' },
  { id: 'rounding-dp', title: 'Rounding to Decimal Places', domain: 'number', grade: 2, icon: '0.0' },
  { id: 'index-notation-num', title: 'Index Notation', domain: 'number', grade: 2, icon: 'n²' },
  // Algebra (5 topics)
  { id: 'algebra-add-sub', title: 'Algebra Addition/Subtraction', domain: 'algebra', grade: 2, icon: 'x±y' },
  { id: 'index-notation-alg', title: 'Index Notation (Algebra)', domain: 'algebra', grade: 2, icon: 'x²' },
  { id: 'algebra-multiply', title: 'Algebra Multiplication', domain: 'algebra', grade: 2, icon: 'xy' },
  { id: 'algebra-divide', title: 'Algebra Division', domain: 'algebra', grade: 2, icon: 'x/y' },
  { id: 'function-machines', title: 'Function Machines', domain: 'algebra', grade: 2, icon: '→' },
  { id: 'sequences-term', title: 'Sequences (Term to Term)', domain: 'algebra', grade: 2, icon: '1,2,3' }
];

// Simplified - will add more grades in next update
export const ALL_GRADE_TOPICS = [
  ...GRADE_1_TOPICS,
  ...GRADE_2_TOPICS
];

export const DOMAIN_LABELS: Record<DomainType, string> = {
  'number': 'Number',
  'algebra': 'Algebra',
  'ratio': 'Ratio & Proportion',
  'geometry': 'Geometry',
  'probability': 'Probability',
  'statistics': 'Statistics'
};

export type GradeFilterType = 'all' | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9;

export const GRADE_FILTERS: Array<{ value: GradeFilterType; label: string }> = [
  { value: 'all', label: 'All Grades' },
  { value: 1, label: 'Grade 1' },
  { value: 2, label: 'Grade 2' },
  { value: 3, label: 'Grade 3' },
  { value: 4, label: 'Grade 4' },
  { value: 5, label: 'Grade 5' },
  { value: 6, label: 'Grade 6' },
  { value: 7, label: 'Grade 7' },
  { value: 8, label: 'Grade 8' },
  { value: 9, label: 'Grade 9' }
];