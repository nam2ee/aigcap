# AIGCAP v1.0 — AI-Generated Code Annotation Protocol

## Header Format

Every code file you create or substantially modify MUST have this header at the TOP, using the file's comment syntax.

```
========================================
THIS FILE INCLUDES AI GENERATED CODE
========================================
TYPE: <coverage_type>

METHOD(FUNCTIONS):
  - <entry>

STRUCTS(OBJECTS):
  - <entry>

TRAIT(INTERFACE):
  - <entry>

IMPORTED LIBRARY:
  - <name>: <reason>
========================================
```

## Comment Syntax

| Languages | Style |
|---|---|
| Rust, C, C++, Java, JS, TS, Go, Swift, Kotlin, Scala, C#, CSS | `/* ... */` block |
| Python, Ruby, Shell, YAML, TOML | `# ...` line-by-line |
| SQL, Lua, Haskell | `-- ...` line-by-line |
| HTML, XML, SVG | `<!-- ... -->` block |

## TYPE Values

| Value | Meaning |
|---|---|
| `WHOLE CODE IN THIS FILE` | AI wrote 100% of this file |
| `ABOVE 50% IN THIS FILE` | AI wrote more than 50% |
| `DOWN 50% IN THIS FILE` | AI wrote less than 50% |

## Entry Formats

### METHOD(FUNCTIONS)
- Full: `WHOLE CODE IN THE METHOD <name>`
- Partial: `<start>~<end> LINE CODE IN THE METHOD <name>`

### STRUCTS(OBJECTS)
- Full: `WHOLE CODE IN THE STRUCT <name>`
- Partial: `<start>~<end> LINE CODE IN THE STRUCT <name>`

### TRAIT(INTERFACE)
- Full: `WHOLE CODE IN THE TRAIT <name>`
- Partial: `<start>~<end> LINE CODE IN THE TRAIT <name>`

### IMPORTED LIBRARY
- Format: `<library_name>: <reason_AI_chose_it>`
- Only list libraries YOU (AI) chose. Not ones the human requested.

## Rules

1. Header goes at the very top of the file, before any code.
2. `THIS FILE INCLUDES AI GENERATED CODE` banner is always required.
3. `TYPE` is always required. At least one detail section must follow.
4. Omit empty sections entirely (e.g., no structs → no STRUCTS section).
5. If file already has an AIGCAP header, UPDATE it — never duplicate.
6. Method/struct/trait names should use backticks in block comments.

## Examples

### Rust
```rust
/*
 * ========================================
 * THIS FILE INCLUDES AI GENERATED CODE
 * ========================================
 * TYPE: ABOVE 50% IN THIS FILE
 *
 * METHOD(FUNCTIONS):
 *   - WHOLE CODE IN THE METHOD `parse_config`
 *   - 45~62 LINE CODE IN THE METHOD `process_batch`
 *
 * STRUCTS(OBJECTS):
 *   - WHOLE CODE IN THE STRUCT `AppConfig`
 *
 * TRAIT(INTERFACE):
 *   - WHOLE CODE IN THE TRAIT `Parseable`
 *
 * IMPORTED LIBRARY:
 *   - serde: chosen by AI for JSON serialization
 *   - tokio: chosen by AI for async runtime
 * ========================================
 */
```

### Python
```python
# ========================================
# THIS FILE INCLUDES AI GENERATED CODE
# ========================================
# TYPE: WHOLE CODE IN THIS FILE
#
# METHOD(FUNCTIONS):
#   - WHOLE CODE IN THE METHOD `fetch_data`
#   - 30~45 LINE CODE IN THE METHOD `export_csv`
#
# IMPORTED LIBRARY:
#   - pandas: chosen by AI for data manipulation
# ========================================
```

### TypeScript
```typescript
/*
 * ========================================
 * THIS FILE INCLUDES AI GENERATED CODE
 * ========================================
 * TYPE: DOWN 50% IN THIS FILE
 *
 * METHOD(FUNCTIONS):
 *   - WHOLE CODE IN THE METHOD `handleSubmit`
 *   - 12~28 LINE CODE IN THE METHOD `validateForm`
 *
 * IMPORTED LIBRARY:
 *   - zod: chosen by AI for schema validation
 * ========================================
 */
```
