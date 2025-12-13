#!/usr/bin/env python3
"""Quick test for code block formatting."""

from app.services.export_service import ExportService

es = ExportService()

# Test case: code block with 'int' that could be misinterpreted as LaTeX
test_md = """# Test Code Block

Here is some code:

```c
#include <stdio.h>
int main() {
    printf("Hello");
    return 0;
}
```

That's the code.
"""

result = es._markdown_to_reportlab_html(test_md)

print("Result:")
print(result)
print("\n" + "="*80 + "\n")

# Check for issues
if 'int main' in result:
    print("✓ 'int main' preserved correctly")
else:
    print("✗ 'int main' not found or corrupted")

if 'Courier' in result:
    print("✓ Courier font applied")
else:
    print("✗ Courier font not found")

if '&lt;' in result or '<' in result:
    print("✓ HTML escaping working")
else:
    print("? HTML escaping status unclear")

if '__CODE_BLOCK' not in result:
    print("✓ Placeholders removed")
else:
    print("✗ Placeholders still present")
