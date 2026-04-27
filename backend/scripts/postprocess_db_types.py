import re
import sys


def _ensure_any_in_typing_import(source: str) -> str:
    """
    Ensure `Any` is imported from `typing`.

    Supports both:
    - from typing import Any, Optional
    - from typing import (Optional, ...)
    """

    # Single-line: from typing import X, Y
    single_line_pattern = re.compile(r'^from typing import (.+)$', re.MULTILINE)
    match = single_line_pattern.search(source)
    if match:
        imported = match.group(1)
        # Avoid treating the parenthesized multiline form as a single-line import.
        if imported.strip().startswith('('):
            match = None
        else:
            if 'Any' in {item.strip() for item in imported.split(',')}:
                return source
            new_imported = 'Any, ' + imported.strip()
            return source[: match.start(1)] + new_imported + source[match.end(1) :]

    # Multiline parenthesized import
    multiline_start = re.compile(r'^from typing import \(\s*$', re.MULTILINE)
    match = multiline_start.search(source)
    if not match:
        return source

    # Find the closing paren after the start
    closing_index = source.find(')', match.end())
    if closing_index == -1:
        return source

    block = source[match.end() : closing_index]
    if re.search(r'^\s*Any\s*,?\s*$', block, re.MULTILINE):
        return source

    insertion = '    Any,\n'
    return source[: match.end()] + insertion + source[match.end() :]


def _remove_pydantic_json_import_if_unused(source: str) -> str:
    if 'Json[' in source:
        return source

    # Remove Json from: from pydantic import BaseModel, Field, Json
    pydantic_import = re.compile(r'^from pydantic import (.+)$', re.MULTILINE)
    match = pydantic_import.search(source)
    if not match:
        return source

    imported = [item.strip() for item in match.group(1).split(',')]
    if 'Json' not in imported:
        return source

    imported = [item for item in imported if item != 'Json']
    new_line = 'from pydantic import ' + ', '.join(imported)
    return source[: match.start()] + new_line + source[match.end() :]


def _propagate_optional_nullability_to_typed_dicts(source: str) -> str:
    """
    Supabase's Python generator often emits:
    - `class PublicX(BaseModel)` fields as Optional[T] (nullable DB columns)
    - `class PublicXInsert/Update(TypedDict)` fields as NotRequired[Annotated[T, ...]] (T non-Optional)

    But Supabase updates *do* support explicitly clearing nullable columns via `None`.
    This pass propagates nullability from BaseModel -> Insert/Update TypedDicts by rewriting:

        Annotated[T, Field(alias='field')] -> Annotated[Optional[T], Field(alias='field')]
    """

    # 1) Collect nullable fields per `PublicX(BaseModel)` class.
    base_nullable_fields: dict[str, set[str]] = {}
    class_header_re = re.compile(r'^class\s+(Public\w+)\(BaseModel\):\s*$', re.MULTILINE)
    optional_field_re = re.compile(r'^\s{4}(\w+):\s+Optional\[', re.MULTILINE)

    matches = list(class_header_re.finditer(source))
    for idx, match in enumerate(matches):
        class_name = match.group(1)
        block_start = match.end()
        block_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(source)
        block = source[block_start:block_end]

        nullable_fields = {m.group(1) for m in optional_field_re.finditer(block)}
        if nullable_fields:
            base_nullable_fields[class_name] = nullable_fields

    if not base_nullable_fields:
        return source

    # 2) Rewrite Insert/Update TypedDict blocks (line-oriented).
    lines = source.splitlines(keepends=True)

    typed_dict_header_re = re.compile(r'^class\s+(Public\w+)(Insert|Update)\(TypedDict\):\s*$')
    field_alias_re = re.compile(r"Field\(alias=(['\"])([^'\"]+)\1\)")

    current_base_model: str | None = None
    current_nullable_fields: set[str] | None = None

    for i, line in enumerate(lines):
        header_match = typed_dict_header_re.match(line)
        if header_match:
            base_name = header_match.group(1)
            current_base_model = base_name
            current_nullable_fields = base_nullable_fields.get(base_name)
            continue

        # Leaving the class block when a new top-level class starts.
        if current_base_model is not None and line.startswith('class '):
            current_base_model = None
            current_nullable_fields = None

        if current_nullable_fields is None:
            continue

        alias_match = field_alias_re.search(line)
        if not alias_match:
            continue

        field_alias = alias_match.group(2)
        if field_alias not in current_nullable_fields:
            continue

        if 'Annotated[' not in line:
            continue

        annotated_start = line.find('Annotated[')
        type_start = annotated_start + len('Annotated[')

        sep_match = re.search(
            r",\s*Field\(alias=(?:'"
            + re.escape(field_alias)
            + r"'|\""
            + re.escape(field_alias)
            + r'\")\)\]',
            line,
        )
        if not sep_match:
            continue

        type_end = sep_match.start()
        type_text = line[type_start:type_end].strip()
        if type_text.startswith('Optional['):
            continue

        new_type_text = f'Optional[{type_text}]'
        lines[i] = line[:type_start] + new_type_text + line[type_end:]

    return ''.join(lines)


def main() -> int:
    source = sys.stdin.read()

    updated = source
    if 'Json[Any]' in updated:
        updated = updated.replace('Json[Any]', 'dict[str, Any]')
        updated = _ensure_any_in_typing_import(updated)
        updated = _remove_pydantic_json_import_if_unused(updated)

    updated = _propagate_optional_nullability_to_typed_dicts(updated)

    sys.stdout.write(updated)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
