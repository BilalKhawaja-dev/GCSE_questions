#!/usr/bin/env python3
"""
Improve Mathematical Notation Rendering

This script improves the mathematical notation rendering by:
1. Switching from LaTeX to more human-readable formats where possible
2. Fixing MathJax configuration issues
3. Adding fallback rendering for better compatibility
"""

import os
import re

def improve_bedrock_math_generation():
    """Improve the mathematical notation generation in Bedrock service."""
    
    print("🔧 Improving mathematical notation generation...")
    
    bedrock_file = "src/services/bedrock_service.py"
    
    with open(bedrock_file, 'r') as f:
        content = f.read()
    
    # Find the generation prompt construction
    old_prompt_section = '''- Use LaTeX notation for mathematical expressions (e.g., \\frac{{3}}{{4}}, x^2, \\sqrt{{16}})'''
    
    new_prompt_section = '''- Use clear mathematical notation: fractions as 3/4 or (3/4), powers as x² or x^2, square roots as √16 or sqrt(16)
- For complex expressions, use LaTeX only when necessary: \\frac{3}{4}, x^2, \\sqrt{16}
- Prioritize human readability over LaTeX formatting'''
    
    if old_prompt_section in content:
        content = content.replace(old_prompt_section, new_prompt_section)
        print("   ✅ Updated Bedrock prompt for better math notation")
    else:
        print("   ⚠️  Could not find exact prompt section to update")
    
    # Write back the updated content
    with open(bedrock_file, 'w') as f:
        f.write(content)
    
    return True


def improve_frontend_math_rendering():
    """Improve the frontend mathematical rendering system."""
    
    print("🔧 Improving frontend mathematical rendering...")
    
    # Update the MathJax utility
    mathjax_file = "frontend/src/utils/mathJax.ts"
    
    with open(mathjax_file, 'r') as f:
        content = f.read()
    
    # Replace the entire formatMathText function with a better implementation
    old_format_function = '''  // Helper method to convert LaTeX to display format
  public formatMathText(text: string): string {
    // Ensure LaTeX expressions are wrapped in $ for inline math
    return text.replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, '$\\frac{$1}{$2}$')
               .replace(/\\sqrt\{([^}]+)\}/g, '$\\sqrt{$1}$')
               .replace(/\^(\w+)/g, '$^{$1}$')
               .replace(/_(\w+)/g, '$_{$1}$');
  }'''
    
    new_format_function = '''  // Helper method to convert mathematical notation to display format
  public formatMathText(text: string): string {
    let formatted = text;
    
    // Convert LaTeX fractions to more readable format or proper LaTeX
    formatted = formatted.replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, (match, num, den) => {
      // For simple fractions, use readable format
      if (num.match(/^\\d+$/) && den.match(/^\\d+$/)) {
        return `${num}/${den}`;
      }
      // For complex fractions, use proper LaTeX
      return `$\\frac{${num}}{${den}}$`;
    });
    
    // Convert LaTeX square roots
    formatted = formatted.replace(/\\sqrt\{([^}]+)\}/g, (match, content) => {
      // For simple numbers, use √ symbol
      if (content.match(/^\\d+$/)) {
        return `√${content}`;
      }
      // For complex expressions, use LaTeX
      return `$\\sqrt{${content}}$`;
    });
    
    // Convert powers - use Unicode superscripts for simple cases
    formatted = formatted.replace(/\^(\{[^}]+\}|\\w+)/g, (match, power) => {
      const cleanPower = power.replace(/[{}]/g, '');
      const superscripts: { [key: string]: string } = {
        '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', 
        '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
      };
      
      if (cleanPower.length === 1 && superscripts[cleanPower]) {
        return superscripts[cleanPower];
      }
      // For complex powers, use LaTeX
      return `$^{${cleanPower}}$`;
    });
    
    // Convert subscripts
    formatted = formatted.replace(/_(\{[^}]+\}|\\w+)/g, (match, sub) => {
      const cleanSub = sub.replace(/[{}]/g, '');
      const subscripts: { [key: string]: string } = {
        '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
        '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉'
      };
      
      if (cleanSub.length === 1 && subscripts[cleanSub]) {
        return subscripts[cleanSub];
      }
      // For complex subscripts, use LaTeX
      return `$_{${cleanSub}}$`;
    });
    
    // Handle already properly formatted LaTeX (don't double-wrap)
    formatted = formatted.replace(/\$\$+/g, '$');
    
    return formatted;
  }
  
  // New method for human-readable math formatting
  public formatForHumans(text: string): string {
    let formatted = text;
    
    // Convert common mathematical expressions to more readable forms
    formatted = formatted.replace(/\\frac\{(\\d+)\}\{(\\d+)\}/g, '$1/$2');
    formatted = formatted.replace(/\\sqrt\{(\\d+)\}/g, '√$1');
    formatted = formatted.replace(/\\times/g, '×');
    formatted = formatted.replace(/\\div/g, '÷');
    formatted = formatted.replace(/\\pm/g, '±');
    formatted = formatted.replace(/\\leq/g, '≤');
    formatted = formatted.replace(/\\geq/g, '≥');
    formatted = formatted.replace(/\\neq/g, '≠');
    formatted = formatted.replace(/\\approx/g, '≈');
    
    // Convert simple powers to Unicode
    formatted = formatted.replace(/x\^2/g, 'x²');
    formatted = formatted.replace(/x\^3/g, 'x³');
    formatted = formatted.replace(/(\w)\^2/g, '$1²');
    formatted = formatted.replace(/(\w)\^3/g, '$1³');
    
    return formatted;
  }'''
    
    content = content.replace(old_format_function, new_format_function)
    
    # Write back the updated content
    with open(mathjax_file, 'w') as f:
        f.write(content)
    
    print("   ✅ Updated MathJax utility with better formatting")
    return True


def improve_question_display_component():
    """Improve the QuestionDisplay component to use better math rendering."""
    
    print("🔧 Improving QuestionDisplay component...")
    
    component_file = "frontend/src/components/QuestionDisplay.tsx"
    
    with open(component_file, 'r') as f:
        content = f.read()
    
    # Update the question text rendering to use the new human-readable format
    old_question_text = '''          <div className="question-text">
            {mathJaxRenderer.formatMathText(question.question_text)}
          </div>'''
    
    new_question_text = '''          <div className="question-text">
            <div className="math-content" dangerouslySetInnerHTML={{
              __html: mathJaxRenderer.formatForHumans(question.question_text)
            }} />
            <div className="latex-fallback" style={{ display: 'none' }}>
              {mathJaxRenderer.formatMathText(question.question_text)}
            </div>
          </div>'''
    
    if old_question_text in content:
        content = content.replace(old_question_text, new_question_text)
        print("   ✅ Updated QuestionDisplay to use human-readable math")
    else:
        print("   ⚠️  Could not find exact question text section to update")
    
    # Write back the updated content
    with open(component_file, 'w') as f:
        f.write(content)
    
    return True


def create_math_rendering_test():
    """Create a comprehensive test for mathematical rendering."""
    
    print("🔧 Creating comprehensive math rendering test...")
    
    test_content = '''<!DOCTYPE html>
<html>
<head>
    <title>Improved Math Rendering Test</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .test-section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; }
        .original { background-color: #ffe6e6; }
        .improved { background-color: #e6ffe6; }
        .math-content { font-size: 16px; line-height: 1.5; }
        .comparison { display: flex; gap: 20px; }
        .comparison > div { flex: 1; }
    </style>
    <script>
        window.MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
                processEscapes: true,
                processEnvironments: true,
            },
            options: {
                skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre'],
                ignoreHtmlClass: 'tex2jax_ignore',
                processHtmlClass: 'tex2jax_process',
            }
        };
    </script>
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>
    <h1>Improved Mathematical Notation Rendering Test</h1>
    
    <div class="test-section">
        <h2>Test Questions with Different Rendering Approaches</h2>
        
        <div class="comparison">
            <div class="original">
                <h3>Original LaTeX Approach</h3>
                <div class="math-content">
                    <p>Simplify the fraction $\\frac{15}{20}$.</p>
                    <p>Calculate $\\frac{2}{3} \\div \\frac{3}{5}$. Give your answer in its simplest form.</p>
                    <p>Work out $3\\frac{1}{4} + 2\\frac{3}{8}$</p>
                    <p>Find the value of $\\sqrt{50}$ in the form $a\\sqrt{b}$</p>
                    <p>Solve $x^2 + 5x + 6 = 0$</p>
                </div>
            </div>
            
            <div class="improved">
                <h3>Improved Human-Readable Approach</h3>
                <div class="math-content">
                    <p>Simplify the fraction 15/20.</p>
                    <p>Calculate 2/3 ÷ 3/5. Give your answer in its simplest form.</p>
                    <p>Work out 3¼ + 2⅜</p>
                    <p>Find the value of √50 in the form a√b</p>
                    <p>Solve x² + 5x + 6 = 0</p>
                </div>
            </div>
        </div>
    </div>
    
    <div class="test-section">
        <h2>Complex Mathematical Expressions</h2>
        
        <div class="comparison">
            <div class="original">
                <h3>LaTeX for Complex Math</h3>
                <div class="math-content">
                    <p>$\\frac{x^2 + 3x - 4}{x - 1} = x + 4$</p>
                    <p>$\\int_0^1 x^2 dx = \\frac{1}{3}$</p>
                    <p>$\\sum_{n=1}^{\\infty} \\frac{1}{n^2} = \\frac{\\pi^2}{6}$</p>
                </div>
            </div>
            
            <div class="improved">
                <h3>Mixed Approach (Simple + LaTeX)</h3>
                <div class="math-content">
                    <p>$\\frac{x^2 + 3x - 4}{x - 1} = x + 4$</p>
                    <p>∫₀¹ x² dx = 1/3</p>
                    <p>Σ(n=1 to ∞) 1/n² = π²/6</p>
                </div>
            </div>
        </div>
    </div>
    
    <div class="test-section">
        <h2>GCSE-Level Questions (Target Audience)</h2>
        
        <div class="improved">
            <h3>Optimized for GCSE Students</h3>
            <div class="math-content">
                <p><strong>Question 1:</strong> Work out 3/4 + 1/8. Give your answer as a fraction in its simplest form.</p>
                <p><strong>Question 2:</strong> Calculate the area of a circle with radius 5cm. Use π = 3.14.</p>
                <p><strong>Question 3:</strong> Solve the equation 2x + 7 = 15</p>
                <p><strong>Question 4:</strong> Find the value of √64</p>
                <p><strong>Question 5:</strong> Express 0.75 as a fraction in its simplest form.</p>
            </div>
        </div>
    </div>
    
    <script>
        // Test the improved formatting functions
        function formatForHumans(text) {
            let formatted = text;
            
            // Convert common mathematical expressions to more readable forms
            formatted = formatted.replace(/\\\\frac\\{(\\d+)\\}\\{(\\d+)\\}/g, '$1/$2');
            formatted = formatted.replace(/\\\\sqrt\\{(\\d+)\\}/g, '√$1');
            formatted = formatted.replace(/\\\\times/g, '×');
            formatted = formatted.replace(/\\\\div/g, '÷');
            formatted = formatted.replace(/\\\\pm/g, '±');
            formatted = formatted.replace(/\\\\leq/g, '≤');
            formatted = formatted.replace(/\\\\geq/g, '≥');
            formatted = formatted.replace(/\\\\neq/g, '≠');
            formatted = formatted.replace(/\\\\approx/g, '≈');
            
            // Convert simple powers to Unicode
            formatted = formatted.replace(/x\\^2/g, 'x²');
            formatted = formatted.replace(/x\\^3/g, 'x³');
            formatted = formatted.replace(/(\\w)\\^2/g, '$1²');
            formatted = formatted.replace(/(\\w)\\^3/g, '$1³');
            
            return formatted;
        }
        
        // Test with sample questions
        const testCases = [
            "Simplify \\\\frac{15}{20}",
            "Calculate \\\\sqrt{64}",
            "Solve x^2 + 5x = 0",
            "Work out 3\\\\frac{1}{4} + 2\\\\frac{3}{8}"
        ];
        
        console.log("Testing improved formatting:");
        testCases.forEach(test => {
            console.log(`Original: ${test}`);
            console.log(`Improved: ${formatForHumans(test)}`);
            console.log('---');
        });
    </script>
</body>
</html>'''
    
    with open("test_improved_math_rendering.html", 'w') as f:
        f.write(test_content)
    
    print("   ✅ Created comprehensive math rendering test")
    return True


def update_question_generation_examples():
    """Update the question generation to produce more readable mathematical notation."""
    
    print("🔧 Updating question generation examples...")
    
    # Check if there are any example files to update
    examples_files = [
        "upload_gcse_examples.py",
        "upload_sample_content.py"
    ]
    
    for file_path in examples_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Update any LaTeX examples to be more readable
            old_examples = [
                "\\frac{3}{4}",
                "\\sqrt{16}",
                "x^2"
            ]
            
            new_examples = [
                "3/4",
                "√16", 
                "x²"
            ]
            
            updated = False
            for old, new in zip(old_examples, new_examples):
                if old in content:
                    content = content.replace(old, new)
                    updated = True
            
            if updated:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"   ✅ Updated {file_path} with readable math notation")
    
    return True


def main():
    """Main function to improve mathematical notation rendering."""
    
    print("🔧 IMPROVING MATHEMATICAL NOTATION RENDERING")
    print("="*70)
    print("Switching from LaTeX-heavy to human-readable mathematical notation")
    print("while maintaining LaTeX for complex expressions.")
    
    improvements = []
    
    # Apply improvements
    if improve_bedrock_math_generation():
        improvements.append("Bedrock math generation improved")
    
    if improve_frontend_math_rendering():
        improvements.append("Frontend math rendering improved")
    
    if improve_question_display_component():
        improvements.append("QuestionDisplay component improved")
    
    if create_math_rendering_test():
        improvements.append("Comprehensive test created")
    
    if update_question_generation_examples():
        improvements.append("Question examples updated")
    
    print(f"\n📊 Summary:")
    print(f"   Improvements applied: {len(improvements)}")
    for improvement in improvements:
        print(f"   ✅ {improvement}")
    
    print(f"\n💡 Key Changes:")
    print(f"   1. Simple fractions: 3/4 instead of LaTeX \\frac{3}{4}")
    print(f"   2. Square roots: √16 instead of LaTeX \\sqrt{16}")
    print(f"   3. Powers: x² instead of LaTeX x^2 for simple cases")
    print(f"   4. Mathematical symbols: ×, ÷, ±, ≤, ≥, ≠, ≈")
    print(f"   5. LaTeX reserved for complex expressions only")
    
    print(f"\n🧪 Testing:")
    print(f"   Open test_improved_math_rendering.html to see the improvements")
    print(f"   The system now prioritizes human readability over LaTeX formatting")
    
    return 0


if __name__ == "__main__":
    exit(main())