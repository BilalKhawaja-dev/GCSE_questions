// Topic preset data structure for GCSE Edexcel Mathematics

export type TierType = 'foundation' | 'higher' | 'both';
export type DomainType = 'number' | 'algebra' | 'ratio-proportion' | 'geometry' | 'probability' | 'statistics';

export interface TopicPreset {
  id: string;
  title: string;
  domain: DomainType;
  tier: TierType;
  icon: string;
  foundationQuery: string;
  higherQuery: string;
  allQuery: string;
}

export const TOPIC_PRESETS: TopicPreset[] = [
  // Number Domain
  {
    id: 'fractions',
    title: 'Fractions',
    domain: 'number',
    tier: 'both',
    icon: '½',
    foundationQuery: '5 Foundation fractions questions',
    higherQuery: '5 Higher fractions questions',
    allQuery: '5 fractions questions'
  },
  {
    id: 'decimals',
    title: 'Decimals',
    domain: 'number',
    tier: 'both',
    icon: '0.5',
    foundationQuery: '5 Foundation decimals questions',
    higherQuery: '5 Higher decimals questions',
    allQuery: '5 decimals questions'
  },
  {
    id: 'percentages',
    title: 'Percentages',
    domain: 'number',
    tier: 'both',
    icon: '%',
    foundationQuery: '5 Foundation percentages questions',
    higherQuery: '5 Higher percentages questions',
    allQuery: '5 percentages questions'
  },
  {
    id: 'standard-form',
    title: 'Standard Form',
    domain: 'number',
    tier: 'higher',
    icon: '10ⁿ',
    foundationQuery: '5 Foundation standard form questions',
    higherQuery: '5 Higher standard form questions',
    allQuery: '5 standard form questions'
  },
  {
    id: 'surds',
    title: 'Surds',
    domain: 'number',
    tier: 'higher',
    icon: '√',
    foundationQuery: '5 Foundation surds questions',
    higherQuery: '5 Higher surds questions',
    allQuery: '5 surds questions'
  },
  {
    id: 'indices',
    title: 'Indices',
    domain: 'number',
    tier: 'both',
    icon: 'xⁿ',
    foundationQuery: '5 Foundation indices questions',
    higherQuery: '5 Higher indices questions',
    allQuery: '5 indices questions'
  },
  {
    id: 'bidmas',
    title: 'BIDMAS',
    domain: 'number',
    tier: 'both',
    icon: '( )',
    foundationQuery: '5 Foundation BIDMAS questions',
    higherQuery: '5 Higher BIDMAS questions',
    allQuery: '5 BIDMAS questions'
  },
  {
    id: 'prime-factors',
    title: 'Prime Factors',
    domain: 'number',
    tier: 'both',
    icon: '2×3',
    foundationQuery: '5 Foundation prime factors questions',
    higherQuery: '5 Higher prime factors questions',
    allQuery: '5 prime factors questions'
  },
  {
    id: 'lcm-hcf',
    title: 'LCM & HCF',
    domain: 'number',
    tier: 'both',
    icon: '∩∪',
    foundationQuery: '5 Foundation LCM and HCF questions',
    higherQuery: '5 Higher LCM and HCF questions',
    allQuery: '5 LCM and HCF questions'
  },
  {
    id: 'rounding',
    title: 'Rounding',
    domain: 'number',
    tier: 'both',
    icon: '≈',
    foundationQuery: '5 Foundation rounding questions',
    higherQuery: '5 Higher rounding questions',
    allQuery: '5 rounding questions'
  },
  {
    id: 'bounds',
    title: 'Upper & Lower Bounds',
    domain: 'number',
    tier: 'higher',
    icon: '±',
    foundationQuery: '5 Foundation bounds questions',
    higherQuery: '5 Higher bounds questions',
    allQuery: '5 bounds questions'
  },
  
  // Algebra Domain
  {
    id: 'linear-equations',
    title: 'Linear Equations',
    domain: 'algebra',
    tier: 'both',
    icon: 'x=',
    foundationQuery: '5 Foundation linear equations questions',
    higherQuery: '5 Higher linear equations questions',
    allQuery: '5 linear equations questions'
  },
  {
    id: 'quadratics',
    title: 'Quadratics',
    domain: 'algebra',
    tier: 'higher',
    icon: 'x²',
    foundationQuery: '5 Foundation quadratics questions',
    higherQuery: '5 Higher quadratics questions',
    allQuery: '5 quadratics questions'
  },
  {
    id: 'simultaneous-equations',
    title: 'Simultaneous Equations',
    domain: 'algebra',
    tier: 'higher',
    icon: '{ }',
    foundationQuery: '5 Foundation simultaneous equations questions',
    higherQuery: '5 Higher simultaneous equations questions',
    allQuery: '5 simultaneous equations questions'
  },
  {
    id: 'inequalities',
    title: 'Inequalities',
    domain: 'algebra',
    tier: 'both',
    icon: '<>',
    foundationQuery: '5 Foundation inequalities questions',
    higherQuery: '5 Higher inequalities questions',
    allQuery: '5 inequalities questions'
  },
  {
    id: 'sequences',
    title: 'Sequences',
    domain: 'algebra',
    tier: 'both',
    icon: '1,2,3',
    foundationQuery: '5 Foundation sequences questions',
    higherQuery: '5 Higher sequences questions',
    allQuery: '5 sequences questions'
  },
  {
    id: 'graphs',
    title: 'Graphs',
    domain: 'algebra',
    tier: 'both',
    icon: '📈',
    foundationQuery: '5 Foundation graphs questions',
    higherQuery: '5 Higher graphs questions',
    allQuery: '5 graphs questions'
  },
  {
    id: 'expanding-brackets',
    title: 'Expanding Brackets',
    domain: 'algebra',
    tier: 'both',
    icon: '( )',
    foundationQuery: '5 Foundation expanding brackets questions',
    higherQuery: '5 Higher expanding brackets questions',
    allQuery: '5 expanding brackets questions'
  },
  {
    id: 'factorising',
    title: 'Factorising',
    domain: 'algebra',
    tier: 'both',
    icon: '[ ]',
    foundationQuery: '5 Foundation factorising questions',
    higherQuery: '5 Higher factorising questions',
    allQuery: '5 factorising questions'
  },
  {
    id: 'rearranging-formulae',
    title: 'Rearranging Formulae',
    domain: 'algebra',
    tier: 'both',
    icon: '⇄',
    foundationQuery: '5 Foundation rearranging formulae questions',
    higherQuery: '5 Higher rearranging formulae questions',
    allQuery: '5 rearranging formulae questions'
  },
  {
    id: 'functions',
    title: 'Functions',
    domain: 'algebra',
    tier: 'higher',
    icon: 'f(x)',
    foundationQuery: '5 Foundation functions questions',
    higherQuery: '5 Higher functions questions',
    allQuery: '5 functions questions'
  },
  
  // Ratio & Proportion Domain
  {
    id: 'ratio',
    title: 'Ratio',
    domain: 'ratio-proportion',
    tier: 'both',
    icon: ':',
    foundationQuery: '5 Foundation ratio questions',
    higherQuery: '5 Higher ratio questions',
    allQuery: '5 ratio questions'
  },
  {
    id: 'proportion',
    title: 'Proportion',
    domain: 'ratio-proportion',
    tier: 'both',
    icon: '∝',
    foundationQuery: '5 Foundation proportion questions',
    higherQuery: '5 Higher proportion questions',
    allQuery: '5 proportion questions'
  },
  {
    id: 'growth-decay',
    title: 'Growth & Decay',
    domain: 'ratio-proportion',
    tier: 'higher',
    icon: '↗↘',
    foundationQuery: '5 Foundation growth and decay questions',
    higherQuery: '5 Higher growth and decay questions',
    allQuery: '5 growth and decay questions'
  },
  
  // Geometry Domain
  {
    id: 'area-perimeter',
    title: 'Area & Perimeter',
    domain: 'geometry',
    tier: 'both',
    icon: '□',
    foundationQuery: '5 Foundation area and perimeter questions',
    higherQuery: '5 Higher area and perimeter questions',
    allQuery: '5 area and perimeter questions'
  },
  {
    id: 'pythagoras',
    title: 'Pythagoras',
    domain: 'geometry',
    tier: 'both',
    icon: 'a²+b²',
    foundationQuery: '5 Foundation Pythagoras questions',
    higherQuery: '5 Higher Pythagoras questions',
    allQuery: '5 Pythagoras questions'
  },
  {
    id: 'trigonometry',
    title: 'Trigonometry',
    domain: 'geometry',
    tier: 'higher',
    icon: 'sin',
    foundationQuery: '5 Foundation trigonometry questions',
    higherQuery: '5 Higher trigonometry questions',
    allQuery: '5 trigonometry questions'
  },
  {
    id: 'circle-theorems',
    title: 'Circle Theorems',
    domain: 'geometry',
    tier: 'higher',
    icon: '○',
    foundationQuery: '5 Foundation circle theorems questions',
    higherQuery: '5 Higher circle theorems questions',
    allQuery: '5 circle theorems questions'
  },
  {
    id: 'vectors',
    title: 'Vectors',
    domain: 'geometry',
    tier: 'higher',
    icon: '→',
    foundationQuery: '5 Foundation vectors questions',
    higherQuery: '5 Higher vectors questions',
    allQuery: '5 vectors questions'
  },
  {
    id: 'transformations',
    title: 'Transformations',
    domain: 'geometry',
    tier: 'both',
    icon: '↻',
    foundationQuery: '5 Foundation transformations questions',
    higherQuery: '5 Higher transformations questions',
    allQuery: '5 transformations questions'
  },
  {
    id: 'angles',
    title: 'Angles',
    domain: 'geometry',
    tier: 'both',
    icon: '∠',
    foundationQuery: '5 Foundation angles questions',
    higherQuery: '5 Higher angles questions',
    allQuery: '5 angles questions'
  },
  {
    id: '3d-shapes',
    title: '3D Shapes',
    domain: 'geometry',
    tier: 'both',
    icon: '🔷',
    foundationQuery: '5 Foundation 3D shapes questions',
    higherQuery: '5 Higher 3D shapes questions',
    allQuery: '5 3D shapes questions'
  },
  {
    id: 'bearings',
    title: 'Bearings',
    domain: 'geometry',
    tier: 'both',
    icon: '🧭',
    foundationQuery: '5 Foundation bearings questions',
    higherQuery: '5 Higher bearings questions',
    allQuery: '5 bearings questions'
  },
  {
    id: 'similar-shapes',
    title: 'Similar Shapes',
    domain: 'geometry',
    tier: 'both',
    icon: '△≅',
    foundationQuery: '5 Foundation similar shapes questions',
    higherQuery: '5 Higher similar shapes questions',
    allQuery: '5 similar shapes questions'
  },
  
  // Probability Domain
  {
    id: 'basic-probability',
    title: 'Basic Probability',
    domain: 'probability',
    tier: 'both',
    icon: '🎲',
    foundationQuery: '5 Foundation basic probability questions',
    higherQuery: '5 Higher basic probability questions',
    allQuery: '5 basic probability questions'
  },
  {
    id: 'tree-diagrams',
    title: 'Tree Diagrams',
    domain: 'probability',
    tier: 'both',
    icon: '🌳',
    foundationQuery: '5 Foundation tree diagrams questions',
    higherQuery: '5 Higher tree diagrams questions',
    allQuery: '5 tree diagrams questions'
  },
  {
    id: 'venn-diagrams',
    title: 'Venn Diagrams',
    domain: 'probability',
    tier: 'both',
    icon: '⊕',
    foundationQuery: '5 Foundation Venn diagrams questions',
    higherQuery: '5 Higher Venn diagrams questions',
    allQuery: '5 Venn diagrams questions'
  },
  {
    id: 'conditional-probability',
    title: 'Conditional Probability',
    domain: 'probability',
    tier: 'higher',
    icon: 'P(A|B)',
    foundationQuery: '5 Foundation conditional probability questions',
    higherQuery: '5 Higher conditional probability questions',
    allQuery: '5 conditional probability questions'
  },
  
  // Statistics Domain
  {
    id: 'averages',
    title: 'Averages',
    domain: 'statistics',
    tier: 'both',
    icon: 'x̄',
    foundationQuery: '5 Foundation averages questions',
    higherQuery: '5 Higher averages questions',
    allQuery: '5 averages questions'
  },
  {
    id: 'data-representation',
    title: 'Data Representation',
    domain: 'statistics',
    tier: 'both',
    icon: '📊',
    foundationQuery: '5 Foundation data representation questions',
    higherQuery: '5 Higher data representation questions',
    allQuery: '5 data representation questions'
  },
  {
    id: 'scatter-graphs',
    title: 'Scatter Graphs',
    domain: 'statistics',
    tier: 'both',
    icon: '⋯',
    foundationQuery: '5 Foundation scatter graphs questions',
    higherQuery: '5 Higher scatter graphs questions',
    allQuery: '5 scatter graphs questions'
  },
  {
    id: 'cumulative-frequency',
    title: 'Cumulative Frequency',
    domain: 'statistics',
    tier: 'higher',
    icon: '∑',
    foundationQuery: '5 Foundation cumulative frequency questions',
    higherQuery: '5 Higher cumulative frequency questions',
    allQuery: '5 cumulative frequency questions'
  },
  {
    id: 'histograms',
    title: 'Histograms',
    domain: 'statistics',
    tier: 'higher',
    icon: '▂▄▆',
    foundationQuery: '5 Foundation histograms questions',
    higherQuery: '5 Higher histograms questions',
    allQuery: '5 histograms questions'
  },
  {
    id: 'box-plots',
    title: 'Box Plots',
    domain: 'statistics',
    tier: 'higher',
    icon: '⊟',
    foundationQuery: '5 Foundation box plots questions',
    higherQuery: '5 Higher box plots questions',
    allQuery: '5 box plots questions'
  },
  {
    id: 'stem-leaf',
    title: 'Stem & Leaf',
    domain: 'statistics',
    tier: 'both',
    icon: '🌿',
    foundationQuery: '5 Foundation stem and leaf questions',
    higherQuery: '5 Higher stem and leaf questions',
    allQuery: '5 stem and leaf questions'
  },
  {
    id: 'pie-charts',
    title: 'Pie Charts',
    domain: 'statistics',
    tier: 'both',
    icon: '🥧',
    foundationQuery: '5 Foundation pie charts questions',
    higherQuery: '5 Higher pie charts questions',
    allQuery: '5 pie charts questions'
  }
];

export const DOMAIN_LABELS: Record<DomainType, string> = {
  'number': 'Number',
  'algebra': 'Algebra',
  'ratio-proportion': 'Ratio & Proportion',
  'geometry': 'Geometry',
  'probability': 'Probability',
  'statistics': 'Statistics'
};

export type GradeFilterType = 'all' | 'foundation' | 'higher';

export const GRADE_FILTERS: Array<{ value: GradeFilterType; label: string; description: string }> = [
  { value: 'all', label: 'All Topics', description: 'Mixed difficulty' },
  { value: 'foundation', label: 'Foundation (1-4)', description: 'Grades 1-4' },
  { value: 'higher', label: 'Higher (5-9)', description: 'Grades 5-9' }
];
