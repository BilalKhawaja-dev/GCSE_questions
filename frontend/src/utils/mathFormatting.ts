/**
 * Mathematical formatting utilities for converting LaTeX to human-readable text.
 * 
 * Converts LaTeX mathematical expressions to Unicode symbols and plain text
 * for better readability without requiring special rendering libraries.
 */

// Superscript character mappings
const SUPERSCRIPT_MAP: Record<string, string> = {
  '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
  '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
  '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
  'n': 'ⁿ', 'x': 'ˣ', 'y': 'ʸ'
};

// Subscript character mappings
const SUBSCRIPT_MAP: Record<string, string> = {
  '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
  '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
  '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
  'a': 'ₐ', 'e': 'ₑ', 'i': 'ᵢ', 'o': 'ₒ', 'u': 'ᵤ',
  'x': 'ₓ', 'n': 'ₙ'
};

// Mathematical operator replacements
const OPERATOR_REPLACEMENTS: [RegExp, string][] = [
  [/\\times/g, '×'],
  [/\\div/g, '÷'],
  [/\\pm/g, '±'],
  [/\\mp/g, '∓'],
  [/\\cdot/g, '·'],
  [/\\ast/g, '*'],
  [/\\star/g, '⋆'],
  [/\\circ/g, '∘'],
  [/\\bullet/g, '•'],
];

// Comparison operator replacements
const COMPARISON_REPLACEMENTS: [RegExp, string][] = [
  [/\\leq/g, '≤'],
  [/\\geq/g, '≥'],
  [/\\neq/g, '≠'],
  [/\\approx/g, '≈'],
  [/\\equiv/g, '≡'],
  [/\\sim/g, '∼'],
  [/\\ll/g, '≪'],
  [/\\gg/g, '≫'],
];

// Set theory and logic symbols
const SET_LOGIC_REPLACEMENTS: [RegExp, string][] = [
  [/\\in/g, '∈'],
  [/\\notin/g, '∉'],
  [/\\subset/g, '⊂'],
  [/\\supset/g, '⊃'],
  [/\\subseteq/g, '⊆'],
  [/\\supseteq/g, '⊇'],
  [/\\cup/g, '∪'],
  [/\\cap/g, '∩'],
  [/\\emptyset/g, '∅'],
  [/\\infty/g, '∞'],
  [/\\forall/g, '∀'],
  [/\\exists/g, '∃'],
  [/\\neg/g, '¬'],
  [/\\land/g, '∧'],
  [/\\lor/g, '∨'],
];

// Greek letter replacements
const GREEK_REPLACEMENTS: [RegExp, string][] = [
  [/\\alpha/g, 'α'], [/\\beta/g, 'β'], [/\\gamma/g, 'γ'], [/\\delta/g, 'δ'],
  [/\\epsilon/g, 'ε'], [/\\zeta/g, 'ζ'], [/\\eta/g, 'η'], [/\\theta/g, 'θ'],
  [/\\iota/g, 'ι'], [/\\kappa/g, 'κ'], [/\\lambda/g, 'λ'], [/\\mu/g, 'μ'],
  [/\\nu/g, 'ν'], [/\\xi/g, 'ξ'], [/\\pi/g, 'π'], [/\\rho/g, 'ρ'],
  [/\\sigma/g, 'σ'], [/\\tau/g, 'τ'], [/\\upsilon/g, 'υ'], [/\\phi/g, 'φ'],
  [/\\chi/g, 'χ'], [/\\psi/g, 'ψ'], [/\\omega/g, 'ω'],
  [/\\Gamma/g, 'Γ'], [/\\Delta/g, 'Δ'], [/\\Theta/g, 'Θ'], [/\\Lambda/g, 'Λ'],
  [/\\Xi/g, 'Ξ'], [/\\Pi/g, 'Π'], [/\\Sigma/g, 'Σ'], [/\\Phi/g, 'Φ'],
  [/\\Psi/g, 'Ψ'], [/\\Omega/g, 'Ω'],
];

// Function name replacements
const FUNCTION_REPLACEMENTS: [RegExp, string][] = [
  [/\\sin/g, 'sin'], [/\\cos/g, 'cos'], [/\\tan/g, 'tan'],
  [/\\log/g, 'log'], [/\\ln/g, 'ln'], [/\\exp/g, 'exp'],
  [/\\lim/g, 'lim'], [/\\max/g, 'max'], [/\\min/g, 'min'],
];

/**
 * Convert a string to superscript characters where possible.
 */
function toSuperscript(text: string): string {
  if (text.length === 1 && SUPERSCRIPT_MAP[text]) {
    return SUPERSCRIPT_MAP[text];
  }
  if (/^\d+$/.test(text) && text.length <= 2) {
    return text.split('').map(c => SUPERSCRIPT_MAP[c] || c).join('');
  }
  return `^(${text})`;
}

/**
 * Convert a string to subscript characters where possible.
 */
function toSubscript(text: string): string {
  if (text.length === 1 && SUBSCRIPT_MAP[text]) {
    return SUBSCRIPT_MAP[text];
  }
  if (/^\d+$/.test(text) && text.length <= 2) {
    return text.split('').map(c => SUBSCRIPT_MAP[c] || c).join('');
  }
  return `_(${text})`;
}

/**
 * Convert LaTeX mathematical expressions to human-readable plain text.
 * 
 * @param text - Input text containing LaTeX expressions
 * @returns Text with LaTeX expressions converted to Unicode/plain text
 * 
 * @example
 * convertLatexToPlainText("\\frac{3}{5}") // Returns "(3)/(5)"
 * convertLatexToPlainText("x^{2}") // Returns "x²"
 * convertLatexToPlainText("\\sqrt{16}") // Returns "√16"
 */
export function convertLatexToPlainText(text: string): string {
  if (!text) return text;

  let result = text;

  // Step 0: Remove math mode delimiters but preserve content
  result = result.replace(/\$([^$]+)\$/g, '$1');
  result = result.replace(/\\\(([^)]+)\\\)/g, '$1');
  result = result.replace(/\\\[([^\]]+)\\\]/g, '$1');

  // Step 1: Convert fractions - \frac{numerator}{denominator} → (numerator)/(denominator)
  // Handle derivative notation first
  result = result.replace(/\\frac\{d\}\{dx\}/g, 'd/dx');
  result = result.replace(/\\frac\{d\}\{d([a-zA-Z])\}/g, 'd/d$1');

  // General fraction conversion with nested brace handling
  let prevResult = '';
  while (prevResult !== result) {
    prevResult = result;
    result = result.replace(/\\frac\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}/g, 
      (_, num, den) => `(${num})/(${den})`);
  }

  // Step 2: Convert square roots - \sqrt{x} → √x
  result = result.replace(/\\sqrt\{([^}]+)\}/g, '√$1');

  // Step 3: Convert exponents - x^{2} → x²
  result = result.replace(/\^?\{([^}]+)\}/g, (match, exp) => {
    if (match.startsWith('^')) {
      return toSuperscript(exp);
    }
    return match;
  });
  result = result.replace(/\\?\^\{([^}]+)\}/g, (_, exp) => toSuperscript(exp));
  result = result.replace(/\^([0-9])/g, (_, digit) => SUPERSCRIPT_MAP[digit] || `^${digit}`);

  // Step 4: Convert subscripts - x_{1} → x₁
  result = result.replace(/\\?_\{([^}]+)\}/g, (_, sub) => toSubscript(sub));
  result = result.replace(/_([0-9])/g, (_, digit) => SUBSCRIPT_MAP[digit] || `_${digit}`);

  // Step 5: Apply all operator replacements
  for (const [pattern, replacement] of OPERATOR_REPLACEMENTS) {
    result = result.replace(pattern, replacement);
  }

  // Step 6: Apply comparison operator replacements
  for (const [pattern, replacement] of COMPARISON_REPLACEMENTS) {
    result = result.replace(pattern, replacement);
  }

  // Step 7: Apply set theory and logic replacements
  for (const [pattern, replacement] of SET_LOGIC_REPLACEMENTS) {
    result = result.replace(pattern, replacement);
  }

  // Step 8: Apply Greek letter replacements
  for (const [pattern, replacement] of GREEK_REPLACEMENTS) {
    result = result.replace(pattern, replacement);
  }

  // Step 9: Apply function name replacements
  for (const [pattern, replacement] of FUNCTION_REPLACEMENTS) {
    result = result.replace(pattern, replacement);
  }

  // Step 10: Clean up remaining LaTeX commands
  result = result.replace(/\\(?:text|mathrm|mathbf|mathit|mathcal|mathbb|mathfrak)\{([^}]+)\}/g, '$1');
  result = result.replace(/\\(?:left|right|big|Big|bigg|Bigg)([()[\]|])/g, '$1');
  result = result.replace(/\\(?:quad|qquad|,|;|!|\s)/g, ' ');

  // Remove remaining unhandled LaTeX commands
  result = result.replace(/\\[a-zA-Z]+\*?/g, '');

  // Step 11: Clean up orphaned braces and whitespace
  result = result.replace(/\{([^{}]*)\}/g, '$1');
  result = result.replace(/\s+/g, ' ');
  result = result.trim();

  return result;
}

/**
 * Format mathematical text for display, converting LaTeX and handling line breaks.
 * 
 * @param text - Input text to format
 * @returns HTML-safe formatted text with LaTeX converted and line breaks as <br>
 */
export function formatMathematicalText(text: string): string {
  if (!text) return '';
  
  // First convert LaTeX to plain text
  let formatted = convertLatexToPlainText(text);
  
  // Then handle line breaks for HTML display
  formatted = formatted.replace(/\n/g, '<br>');
  
  return formatted.trim();
}

const mathFormatting = { convertLatexToPlainText, formatMathematicalText };
export default mathFormatting;
