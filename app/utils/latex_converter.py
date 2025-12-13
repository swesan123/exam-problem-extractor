"""LaTeX conversion utility for math expressions."""

import re
from typing import Optional


def convert_to_latex(text: str) -> str:
    """
    Convert plain text math expressions to LaTeX format.

    Detects common math patterns and converts them to LaTeX syntax.
    Preserves existing LaTeX if already formatted.
    Skips conversion for code blocks to avoid converting programming keywords.

    Args:
        text: Input text with potential math expressions

    Returns:
        Text with math expressions converted to LaTeX format
    """
    if not text:
        return text

    # Check if text already contains LaTeX delimiters
    if re.search(r'\$.*?\$|\\\(.*?\\\)|\\\[.*?\\\]|\\begin\{.*?\}', text):
        # Already has LaTeX, return as-is (but ensure proper formatting)
        return text

    # Extract and protect code blocks (both fenced ``` and inline `)
    code_blocks = []
    code_block_placeholders = []
    
    # Process fenced code blocks (```...```)
    def replace_fenced_code(match):
        placeholder = f'__FENCED_CODE_{len(code_blocks)}__'
        code_blocks.append(match.group(0))  # Store entire code block
        code_block_placeholders.append(placeholder)
        return placeholder
    
    result = re.sub(r'```[\s\S]*?```', replace_fenced_code, text)
    
    # Process inline code (`...`)
    def replace_inline_code(match):
        placeholder = f'__INLINE_CODE_{len(code_blocks)}__'
        code_blocks.append(match.group(0))  # Store entire inline code
        code_block_placeholders.append(placeholder)
        return placeholder
    
    result = re.sub(r'`[^`]+`', replace_inline_code, result)

    # Pattern 1: Exponents (x^2, x^3, etc.) - but not if already in LaTeX
    # Match patterns like: x^2, (x+1)^2, but avoid matching $x^2$ or \(x^2\)
    def replace_exponent(match):
        base = match.group(1)
        exp = match.group(2)
        # Check if already in LaTeX context
        before = result[:match.start()]
        after = result[match.end():]
        # Simple check: if surrounded by $ or \(, skip
        if not (before.rstrip().endswith('$') or before.rstrip().endswith('\\(')):
            return f"${base}^{{{exp}}}$"
        return match.group(0)

    # More careful exponent replacement - only if not already in LaTeX
    result = re.sub(
        r'([a-zA-Z0-9\)]+)\^([0-9]+|[a-zA-Z]+)',
        lambda m: f"${m.group(1)}^{{{m.group(2)}}}$" if not _in_latex_context(result, m.start()) else m.group(0),
        result
    )

    # Pattern 2: Square roots (sqrt(x), sqrt(expression))
    result = re.sub(
        r'sqrt\(([^)]+)\)',
        lambda m: f"$\\sqrt{{{m.group(1)}}}$" if not _in_latex_context(result, m.start()) else m.group(0),
        result
    )

    # Pattern 3: Fractions (1/2, x/y) - but be careful not to match dates or ratios
    # Only match if it looks like a mathematical fraction (numbers or variables)
    result = re.sub(
        r'\b([0-9]+|[a-zA-Z]+)/([0-9]+|[a-zA-Z]+)\b',
        lambda m: f"$\\frac{{{m.group(1)}}}{{{m.group(2)}}}$" if _is_math_fraction(m.group(0)) and not _in_latex_context(result, m.start()) else m.group(0),
        result
    )

    # Pattern 4: Greek letters (alpha, beta, etc.) - convert to LaTeX
    greek_map = {
        'alpha': r'$\alpha$', 'beta': r'$\beta$', 'gamma': r'$\gamma$',
        'delta': r'$\delta$', 'epsilon': r'$\epsilon$', 'theta': r'$\theta$',
        'lambda': r'$\lambda$', 'mu': r'$\mu$', 'pi': r'$\pi$', 'sigma': r'$\sigma$',
        'phi': r'$\phi$', 'omega': r'$\omega$',
        'Alpha': r'$A$', 'Beta': r'$B$', 'Gamma': r'$\Gamma$', 'Delta': r'$\Delta$',
        'Theta': r'$\Theta$', 'Lambda': r'$\Lambda$', 'Pi': r'$\Pi$', 'Sigma': r'$\Sigma$',
        'Phi': r'$\Phi$', 'Omega': r'$\Omega$'
    }
    for greek, latex in greek_map.items():
        # Only replace if not already in LaTeX context
        pattern = r'\b' + re.escape(greek) + r'\b'
        result = re.sub(
            pattern,
            lambda m, g=greek, l=latex: l if not _in_latex_context(result, m.start()) else m.group(0),
            result,
            flags=re.IGNORECASE
        )

    # Pattern 5: Integrals (integral, int)
    # Be more careful: only convert "int" if it's clearly mathematical context
    # Don't convert if it looks like a programming keyword (e.g., "int main", "int x", "int(")
    result = re.sub(
        r'\bintegral\b',
        lambda m: r'$\int$' if not _in_latex_context(result, m.start()) else m.group(0),
        result,
        flags=re.IGNORECASE
    )
    # For "int", only convert if it's followed by a space and NOT by common programming patterns
    # This avoids converting "int main()", "int x", etc.
    result = re.sub(
        r'\bint\b(?=\s+(?!main|main\(|return|void|char|float|double|long|short|unsigned|signed|const|static|struct|enum|union|typedef|auto|register|extern|volatile|restrict|_Bool|_Complex|_Imaginary|if|for|while|do|switch|case|default|break|continue|goto|sizeof|typeof|alignof|__attribute__|__builtin_))',
        lambda m: r'$\int$' if not _in_latex_context(result, m.start()) else m.group(0),
        result,
        flags=re.IGNORECASE
    )

    # Pattern 6: Summation (sum, sigma)
    # Be careful: "sum" could be a variable name in code
    # Only convert if it's clearly mathematical context
    result = re.sub(
        r'\bsum\b(?=\s*(?:of|over|from|to|=\s*\$|=\s*\\sum|\()|$)',
        lambda m: r'$\sum$' if not _in_latex_context(result, m.start()) else m.group(0),
        result,
        flags=re.IGNORECASE
    )

    # Clean up: remove duplicate $ delimiters that might have been created
    result = re.sub(r'\$\$+', '$$', result)
    result = re.sub(r'\$\s+\$', ' ', result)

    # Restore code blocks after all LaTeX conversion
    for placeholder, code_block in zip(code_block_placeholders, code_blocks):
        result = result.replace(placeholder, code_block)

    return result


def _in_latex_context(text: str, position: int) -> bool:
    """
    Check if position is already inside LaTeX delimiters.

    Args:
        text: Full text
        position: Position to check

    Returns:
        True if position is inside LaTeX delimiters
    """
    before = text[:position]
    after = text[position:]

    # Count unclosed $ delimiters before position
    dollar_count = before.count('$') - before.count('\\$')
    if dollar_count % 2 == 1:
        return True

    # Check for \( and \)
    paren_open = before.count('\\(') - before.count('\\)')
    if paren_open > 0:
        return True

    # Check for \[ and \]
    bracket_open = before.count('\\[') - before.count('\\]')
    if bracket_open > 0:
        return True

    return False


def _is_math_fraction(fraction_str: str) -> bool:
    """
    Determine if a fraction string looks like a mathematical fraction.

    Args:
        fraction_str: String like "1/2" or "x/y"

    Returns:
        True if it looks like a math fraction
    """
    # Simple heuristic: if both parts are numbers or single letters, likely math
    parts = fraction_str.split('/')
    if len(parts) != 2:
        return False

    part1, part2 = parts[0], parts[1]

    # Both are numbers
    if part1.isdigit() and part2.isdigit():
        return True

    # Both are single letters (variables)
    if len(part1) == 1 and len(part2) == 1 and part1.isalpha() and part2.isalpha():
        return True

    # One is number, one is letter
    if (part1.isdigit() and part2.isalpha()) or (part1.isalpha() and part2.isdigit()):
        return True

    return False

