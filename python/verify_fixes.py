import ast
import sys
from pathlib import Path


def verify_document_tools():
    file_path = Path("src/mcp_server/features/documents/document_tools.py")
    print(f"Verifying {file_path}...")

    with open(file_path) as f:
        tree = ast.parse(f.read())

    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "manage_document":
            found = True
            # Find 'content' argument
            for arg in node.args.kwonlyargs: # It's likely a kwonlyarg or regular arg depending on position
                if arg.arg == "content":
                    # Check annotation
                    # We expect 'Any' which is a Name node with id='Any'
                    if isinstance(arg.annotation, ast.Name) and arg.annotation.id == "Any":
                        print("✅ manage_document: 'content' parameter type is 'Any'")
                    else:
                        print(f"❌ manage_document: 'content' parameter type is {ast.dump(arg.annotation)}")
                        return False

            # Also check args if not in kwonlyargs
            for arg in node.args.args:
                if arg.arg == "content":
                     if isinstance(arg.annotation, ast.Name) and arg.annotation.id == "Any":
                        print("✅ manage_document: 'content' parameter type is 'Any'")
                     else:
                        print(f"❌ manage_document: 'content' parameter type is {ast.dump(arg.annotation)}")
                        return False

    if not found:
        print("❌ manage_document function not found")
        return False
    return True

def verify_version_tools():
    file_path = Path("src/mcp_server/features/documents/version_tools.py")
    print(f"Verifying {file_path}...")

    with open(file_path) as f:
        tree = ast.parse(f.read())

    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "manage_version":
            found = True
            # Check defaults
            # defaults list corresponds to the last n args.
            # We need to map args to defaults.
            args = node.args.args
            defaults = node.args.defaults

            # Calculate offset
            offset = len(args) - len(defaults)

            field_name_index = -1
            for i, arg in enumerate(args):
                if arg.arg == "field_name":
                    field_name_index = i
                    break

            if field_name_index == -1:
                print("❌ manage_version: 'field_name' argument not found")
                return False

            if field_name_index >= offset:
                default_val = defaults[field_name_index - offset]
                if isinstance(default_val, ast.Constant) and default_val.value == "docs":
                    print("✅ manage_version: 'field_name' has default value 'docs'")
                else:
                    print(f"❌ manage_version: 'field_name' default is {ast.dump(default_val)}")
                    return False
            else:
                print("❌ manage_version: 'field_name' has no default value")
                return False

    if not found:
        print("❌ manage_version function not found")
        return False
    return True

if __name__ == "__main__":
    success = True
    if not verify_document_tools():
        success = False
    if not verify_version_tools():
        success = False

    if success:
        print("\nAll verifications PASSED")
        sys.exit(0)
    else:
        print("\nVerification FAILED")
        sys.exit(1)
