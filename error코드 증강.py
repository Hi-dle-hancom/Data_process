import json
import random
import string
import os
import stat
import tempfile
import numpy as np 
from abc import ABC, abstractmethod 

# --- Helper Function: Generate Realistic Variable Names ---
def get_random_name(is_class=False):
    """Generates meaningful variable, function, or class names in English."""
    prefixes = ['user', 'product', 'data', 'config', 'item', 'order', 'file']
    suffixes = ['list', 'dict', 'id', 'name', 'processor', 'manager', 'service']
    name = f"{random.choice(prefixes)}_{random.choice(suffixes)}"
    return name.title().replace('_', '') if is_class else name

# --- Error Generator: Base Class ---
class BaseErrorGenerator(ABC): 
    """Base class for all error generators."""
    def __init__(self):
        pass 

    @abstractmethod 
    def generate_simple_case(self) -> dict: # [변경점 1] 반환 타입 힌트 추가: -> dict
        """Generates a simple error case."""
        pass

    @abstractmethod 
    def generate_complex_case(self) -> dict: # [변경점 1] 반환 타입 힌트 추가: -> dict
        """Generates a complex error case."""
        pass

    def __call__(self):
        """Randomly selects and runs a case to return error data."""
        return random.choice([self.generate_simple_case, self.generate_complex_case])()

# --- PREVIOUSLY DEFINED ERROR GENERATORS ---
# (TypeError, IndexError, KeyError, AttributeError, NameError, NumpyValueError)
# ... The original classes from the previous answer go here ...
class TypeErrorGenerator(BaseErrorGenerator):
    def generate_simple_case(self):
        number = random.randint(10, 500)
        return {
            "error_context": {
                "title": "TypeError: can only concatenate str (not \"int\") to str",
                "error_log": f"Traceback (most recent call last):\n  File \"<stdin>\", line 2, in <module>\nTypeError: can only concatenate str (not \"int\") to str",
                "language": "python",
                "description": "Concatenating a string with an integer using the '+' operator.",
                "buggy_code_snippet": f"item_id = {number}\n# TypeError: Attempting to concatenate a string directly with an integer item_id.\nprint(\"Item ID: \" + item_id)"
            },
            "fixed_code_snippet": f"item_id = {number}\n# Fix: Use an f-string to safely format the integer as a string.\nprint(f\"Item ID: {{item_id}}\")"
        }

    def generate_complex_case(self):
        wrong_arg = random.randint(100, 999)
        return {
            "error_context": {
                "title": "TypeError: object of type 'int' has no len()",
                "error_log": f"Traceback (most recent call last):\n  File \"<stdin>\", line 1, in <module>\nTypeError: object of type 'int' has no len()",
                "language": "python",
                "description": "Passing an argument of an unsupported type (integer) to a function that expects a sequence (like a list or string).",
                "buggy_code_snippet": f"user_count = {wrong_arg}\n# TypeError: Using len() on an integer type, which has no length.\nprint(len(user_count))"
            },
            "fixed_code_snippet": f"user_count = {wrong_arg}\n# Fix: Convert the integer to a string to check its length.\nprint(len(str(user_count)))"
        }

class IndexErrorGenerator(BaseErrorGenerator):
    def generate_simple_case(self):
        list_len = random.randint(3, 6)
        elements = [random.randint(1, 100) for _ in range(list_len)]
        list_var = get_random_name()
        bad_index = list_len + random.randint(1, 3)
        return {
            "error_context": {
                "title": "IndexError: list index out of range",
                "error_log": f"Traceback (most recent call last):\n  File \"<stdin>\", line 2, in <module>\nIndexError: list index out of range",
                "language": "python",
                "description": "Accessing an index that is outside the bounds of a list.",
                "buggy_code_snippet": f"{list_var} = {elements}\n# IndexError: Attempting to access index {bad_index} in a list of size {list_len}.\nprint({list_var}[{bad_index}])"
            },
            "fixed_code_snippet": f"{list_var} = {elements}\n# Fix: To access the last element, use index -1.\nprint({list_var}[-1])"
        }

    def generate_complex_case(self):
        return {
            "error_context": {
                "title": "IndexError: list index out of range",
                "error_log": f"Traceback (most recent call last):\n  File \"<stdin>\", line 2, in <module>\nIndexError: list index out of range",
                "language": "python",
                "description": "Attempting to access an element (e.g., the first one at index 0) from an empty list.",
                "buggy_code_snippet": "data_points = []\n# IndexError: Attempting to access the first element of an empty list.\nfirst_point = data_points[0]"
            },
            "fixed_code_snippet": "data_points = []\n# Fix: Prevent the error by first checking if the list is empty.\nfirst_point = data_points[0] if data_points else None\nprint(first_point)"
        }

class KeyErrorGenerator(BaseErrorGenerator):
    def generate_simple_case(self):
        dict_var, key1, val1, bad_key = get_random_name(), 'name', 'Alice', 'age'
        return {
            "error_context": {
                "title": f"KeyError: '{bad_key}'",
                "error_log": f"Traceback (most recent call last):\n  File \"<stdin>\", line 2, in <module>\nKeyError: '{bad_key}'",
                "language": "python",
                "description": "Accessing a non-existent key in a dictionary.",
                "buggy_code_snippet": f"{dict_var} = {{'{key1}': '{val1}'}}\n# KeyError: The key '{bad_key}' does not exist in the dictionary.\nprint({dict_var}['{bad_key}'])"
            },
            "fixed_code_snippet": f"{dict_var} = {{'{key1}': '{val1}'}}\n# Fix: Use the .get() method to handle missing keys by returning a default value.\nprint({dict_var}.get('{bad_key}', 'N/A'))"
        }

    def generate_complex_case(self):
        user_profile = get_random_name()
        bad_key = 'zipcode'
        return {
            "error_context": {
                "title": f"KeyError: '{bad_key}'",
                "error_log": f"Traceback (most recent call last):\n  File \"<stdin>\", line 3, in <module>\nKeyError: '{bad_key}'",
                "language": "python",
                "description": "Accessing a non-existent key in a nested dictionary.",
                "buggy_code_snippet": f"{user_profile} = {{\n    'name': 'Bob',\n    'details': {{'email': 'bob@example.com'}}\n}}\n# KeyError: The key '{bad_key}' is missing from the nested 'details' dictionary.\nzip_code = {user_profile}['details']['{bad_key}']"
            },
            "fixed_code_snippet": f"{user_profile} = {{\n    'name': 'Bob',\n    'details': {{'email': 'bob@example.com'}}\n}}\n# Fix: Use chained .get() calls for safe access in nested structures.\nzip_code = {user_profile}.get('details', {{}}).get('{bad_key}', 'Not Provided')\nprint(zip_code)"
        }

class AttributeErrorGenerator(BaseErrorGenerator):
    def generate_simple_case(self):
        var_name = get_random_name()
        num = random.randint(100, 999)
        return {
            "error_context": {
                "title": "AttributeError: 'int' object has no attribute 'lower'",
                "error_log": f"Traceback (most recent call last):\n  File \"<stdin>\", line 2, in <module>\nAttributeError: 'int' object has no attribute 'lower'",
                "language": "python",
                "description": "Calling a method on an object that does not have it. For instance, calling a string method on an integer.",
                "buggy_code_snippet": f"{var_name} = {num}\n# AttributeError: The integer object has no '.lower()' method.\nprint({var_name}.lower())"
            },
            "fixed_code_snippet": f"{var_name} = {num}\n# Fix: Convert the object to a string before calling the method.\nprint(str({var_name}).lower())"
        }

    def generate_complex_case(self):
        class_name = get_random_name(is_class=True)
        return {
            "error_context": {
                "title": "AttributeError: 'NoneType' object has no attribute 'name'",
                "error_log": f"Traceback (most recent call last):\n  File \"<stdin>\", line 7, in <module>\nAttributeError: 'NoneType' object has no attribute 'name'",
                "language": "python",
                "description": "Trying to access an attribute or method on a variable that is None, often happening after a function fails to return an object.",
                "buggy_code_snippet": f"class {class_name}:\n    def __init__(self, name): self.name = name\n\ndef find_user(id):\n    if id != 1: return None\n    return {class_name}('Admin')\n\nuser = find_user(99) # The function returns None\n# AttributeError: 'user' is None, so it has no '.name' attribute.\nprint(user.name)"
            },
            "fixed_code_snippet": f"class {class_name}:\n    def __init__(self, name): self.name = name\n\ndef find_user(id):\n    if id != 1: return None\n    return {class_name}('Admin')\n\nuser = find_user(99)\n# Fix: Access the attribute only after checking that the object is not None.\nif user:\n    print(user.name)\nelse:\n    print('User not found')"
        }

class NameErrorGenerator(BaseErrorGenerator):
    def generate_simple_case(self):
        var_name = get_random_name()
        mistyped_var = var_name[:-1] + random.choice(string.ascii_lowercase)
        return {
            "error_context": {
                "title": f"NameError: name '{mistyped_var}' is not defined",
                "error_log": f"Traceback (most recent call last):\n  File \"<stdin>\", line 2, in <module>\nNameError: name '{mistyped_var}' is not defined",
                "language": "python",
                "description": "Using a variable name that has not been defined, often due to a typo.",
                "buggy_code_snippet": f"{var_name} = \"Hello, World!\"\n# NameError: The variable '{mistyped_var}' is not defined due to a typo.\nprint({mistyped_var})"
            },
            "fixed_code_snippet": f"{var_name} = \"Hello, World!\"\n# Fix: Correct the typo in the variable name.\nprint({var_name})"
        }

    def generate_complex_case(self):
        func_name, var_name = get_random_name(), get_random_name()
        return {
            "error_context": {
                "title": f"NameError: name '{var_name}' is not defined",
                "error_log": f"Traceback (most recent call last):\n  File \"<stdin>\", line 5, in <module>\nNameError: name '{var_name}' is not defined",
                "language": "python",
                "description": "Attempting to access a variable outside of its scope (e.g., a variable defined inside a function is not accessible globally).",
                "buggy_code_snippet": f"def {func_name}():\n    # {var_name} is a local variable inside the function.\n    {var_name} = 'Local scope'\n\n{func_name}()\n# NameError: Cannot access {var_name} outside of the function's scope.\nprint({var_name})"
            },
            "fixed_code_snippet": f"def {func_name}():\n    {var_name} = 'Local scope'\n    return {var_name} # Fix: Modify the function to return the value.\n\nresult = {func_name}()\nprint(result)"
        }

class NumpyValueErrorGenerator(BaseErrorGenerator):
    def generate_simple_case(self):
        len1, len2 = random.sample(range(3, 7), 2)
        arr1, arr2 = get_random_name(), get_random_name()
        return {
            "error_context": {
                "title": f"ValueError: operands could not be broadcast together with shapes ({len1},) ({len2},)",
                "error_log": f"Traceback (most recent call last):\n  File \"<stdin>\", line 3, in <module>\nValueError: operands could not be broadcast together with shapes ({len1},) ({len2},)",
                "language": "python",
                "description": "Attempting an element-wise operation on two NumPy arrays with incompatible shapes that cannot be broadcast.",
                "buggy_code_snippet": f"import numpy as np\n{arr1} = np.arange({len1})\n{arr2} = np.arange({len2})\n# ValueError: Operation fails because the two arrays have different shapes.\nresult = {arr1} + {arr2}"
            },
            "fixed_code_snippet": f"import numpy as np\n{arr1} = np.arange({len1})\n{arr2}_unfit = np.arange({len2})\n# Fix: Resize one array to match the other's shape before the operation.\n{arr2}_fit = np.resize({arr2}_unfit, {arr1}.shape)\nresult = {arr1} + {arr2}_fit"
        }

    def generate_complex_case(self):
        return {
            "error_context": {
                "title": "ValueError: setting an array element with a sequence.",
                "error_log": "Traceback (most recent call last):\n  File \"<stdin>\", line 2, in <module>\nValueError: setting an array element with a sequence.",
                "language": "python",
                "description": "Creating a NumPy array from a ragged list (a list of lists with different lengths) without specifying dtype=object.",
                "buggy_code_snippet": "import numpy as np\n# ValueError: Cannot create array because the inner lists have different lengths.\ndata = [[1, 2], [3, 4, 5], [6]]\narr = np.array(data)"
            },
            "fixed_code_snippet": "import numpy as np\ndata = [[1, 2], [3, 4, 5], [6]]\n# Fix: Specify dtype=object to create an array that can hold objects of varying lengths.\narr = np.array(data, dtype=object)"
        }
        
# --- NEWLY ADDED ERROR GENERATORS ---

class ZeroDivisionErrorGenerator(BaseErrorGenerator):
    def generate_simple_case(self):
        numerator = random.randint(10, 100)
        return {
            "error_context": {
                "title": "ZeroDivisionError: division by zero",
                "error_log": "Traceback (most recent call last):\n  File \"<stdin>\", line 1, in <module>\nZeroDivisionError: division by zero",
                "language": "python",
                "description": "Attempting to divide any number by zero.",
                "buggy_code_snippet": f"result = {numerator} / 0"
            },
            "fixed_code_snippet": f"numerator = {numerator}\ndenominator = 0\n# Fix: Check if the denominator is zero before performing the division.\nresult = numerator / denominator if denominator != 0 else float('inf')\nprint(result)"
        }

    def generate_complex_case(self):
        items = random.randint(100, 200)
        user_count = 0
        return {
            "error_context": {
                "title": "ZeroDivisionError: division by zero",
                "error_log": "Traceback (most recent call last):\n  File \"<stdin>\", line 3, in <module>\nZeroDivisionError: division by zero",
                "language": "python",
                "description": "A calculation error where a variable that is supposed to be a divisor becomes zero during runtime.",
                "buggy_code_snippet": f"total_items = {items}\nactive_users = {user_count}\n# ZeroDivisionError: active_users can be zero, leading to a crash.\nitems_per_user = total_items / active_users"
            },
            "fixed_code_snippet": f"total_items = {items}\nactive_users = {user_count}\n# Fix: Handle the case where the divisor is zero to avoid the error.\nif active_users > 0:\n    items_per_user = total_items / active_users\nelse:\n    items_per_user = 0\nprint(items_per_user)"
        }

class RecursionErrorGenerator(BaseErrorGenerator):
    def generate_simple_case(self):
        func_name = get_random_name()
        return {
            "error_context": {
                "title": "RecursionError: maximum recursion depth exceeded",
                "error_log": f"Traceback (most recent call last):\n  ...\n  File \"<stdin>\", line 2, in {func_name}\nRecursionError: maximum recursion depth exceeded",
                "language": "python",
                "description": "A function calls itself endlessly without a proper base case to stop the recursion.",
                "buggy_code_snippet": f"def {func_name}(n):\n    # RecursionError: The function calls itself without a condition to stop it.\n    return {func_name}(n + 1)\n\n{func_name}(1)"
            },
            "fixed_code_snippet": f"def {func_name}(n, limit=10):\n    # Fix: Add a base case to terminate the recursion.\n    if n >= limit:\n        return\n    print(n)\n    {func_name}(n + 1, limit)\n\n{func_name}(1)"
        }

    def generate_complex_case(self):
        return {
            "error_context": {
                "title": "RecursionError: maximum recursion depth exceeded in comparison",
                "error_log": "Traceback (most recent call last):\n  ...\n  File \"<stdin>\", line 2, in factorial\nRecursionError: maximum recursion depth exceeded in comparison",
                "language": "python",
                "description": "A recursive function has a base case that is never met for a certain input, leading to infinite recursion.",
                "buggy_code_snippet": "def factorial(n):\n    # The base case `n == 0` is never reached for negative numbers.\n    if n == 0:\n        return 1\n    return n * factorial(n - 1)\n\n# RecursionError: Calling with a negative number causes infinite recursion.\nfactorial(-1)"
            },
            "fixed_code_snippet": "def factorial(n):\n    # Fix: Add a check for invalid input to prevent infinite recursion.\n    if not isinstance(n, int) or n < 0:\n        raise ValueError(\"Factorial is not defined for non-integers or negative numbers\")\n    if n == 0:\n        return 1\n    return n * factorial(n - 1)\n\ntry:\n    print(factorial(5))\n    print(factorial(-1))\nexcept ValueError as e:\n    print(e)"
        }
        
class ModuleNotFoundErrorGenerator(BaseErrorGenerator):
    def generate_simple_case(self):
        module_name = ''.join(random.choices(string.ascii_lowercase, k=10)) + '_utils'
        return {
            "error_context": {
                "title": f"ModuleNotFoundError: No module named '{module_name}'",
                "error_log": f"Traceback (most recent call last):\n  File \"<stdin>\", line 1, in <module>\nModuleNotFoundError: No module named '{module_name}'",
                "language": "python",
                "description": "Attempting to import a module that does not exist or is not installed in the current environment.",
                "buggy_code_snippet": f"# ModuleNotFoundError: '{module_name}' is not a real module.\nimport {module_name}"
            },
            "fixed_code_snippet": "# Fix: Ensure the module you are importing exists and is spelled correctly.\n# For example, to use the 'math' module:\nimport math\nprint(math.pi)"
        }

    def generate_complex_case(self):
        package_name = get_random_name()
        func_name = get_random_name()
        return {
            "error_context": {
                "title": f"ImportError: cannot import name '{func_name}' from '{package_name}'",
                "error_log": f"Traceback (most recent call last):\n  File \"<stdin>\", line 1, in <module>\nImportError: cannot import name '{func_name}' from '{package_name}' (unknown location)",
                "language": "python",
                "description": "Trying to import a specific function or class from a module, but that name does not exist within the module.",
                "buggy_code_snippet": f"# Assuming 'os' is a valid module, but it does not have a function named '{func_name}'\n# ImportError: The name '{func_name}' does not exist in the 'os' module.\nfrom os import {func_name}"
            },
            "fixed_code_snippet": "# Fix: Import a name that actually exists in the module.\n# For example, importing 'path' from the 'os' module.\nfrom os import path\nprint(path.sep)"
        }

class FileNotFoundErrorGenerator(BaseErrorGenerator):
    def generate_simple_case(self):
        bad_filename = "non_existent_file_" + "".join(random.choices(string.digits, k=8)) + ".txt"
        return {
            "error_context": {
                "title": f"FileNotFoundError: [Errno 2] No such file or directory: '{bad_filename}'",
                "error_log": f"Traceback (most recent call last):\n  File \"<stdin>\", line 1, in <module>\nFileNotFoundError: [Errno 2] No such file or directory: '{bad_filename}'",
                "language": "python",
                "description": "Trying to open and read from a file that does not exist at the specified path.",
                "buggy_code_snippet": f"# FileNotFoundError: The file '{bad_filename}' does not exist.\nwith open('{bad_filename}', 'r') as f:\n    content = f.read()"
            },
            "fixed_code_snippet": f"import os\n\nfile_path = '{bad_filename}'\n# Fix: Check if the file exists before attempting to open it.\nif os.path.exists(file_path):\n    with open(file_path, 'r') as f:\n        content = f.read()\nelse:\n    print(f\"File not found at path: {{file_path}}\")"
        }

    def generate_complex_case(self):
        return self.generate_simple_case()

class PermissionErrorGenerator(BaseErrorGenerator):
    def generate_simple_case(self):
        return {
            "error_context": {
                "title": "PermissionError: [Errno 13] Permission denied",
                "error_log": "Traceback (most recent call last):\n  File \"<stdin>\", line 1, in <module>\nPermissionError: [Errno 13] Permission denied: '/root/protected_file.txt'",
                "language": "python",
                "description": "Attempting to perform an operation (like creating or writing to a file) in a directory where the user lacks the necessary permissions.",
                "buggy_code_snippet": "# This code will fail if run by a non-root user.\n# PermissionError: Trying to write to a protected directory.\nwith open('/root/protected_file.txt', 'w') as f:\n    f.write('This will fail')"
            },
            "fixed_code_snippet": "import os\nimport tempfile\n\n# Use tempfile.gettempdir() to find a user-writable directory.\nfile_path = os.path.join(tempfile.gettempdir(), 'my_app_file.txt')\n\n# Fix: Ensure you are writing to a directory where you have permissions.\ntry:\n    with open(file_path, 'w') as f:\n        f.write('This will succeed')\n    print(f\"Successfully wrote to {{file_path}}\")\n    os.remove(file_path) # Clean up the file\nexcept PermissionError:\n    print(\"Could not write to the chosen directory.\")"
        }

    def generate_complex_case(self):
        return self.generate_simple_case()

class SyntaxErrorGenerator(BaseErrorGenerator):
    def generate_simple_case(self):
        code_str = "version = 3.10."
        return {
            "error_context": {
                "title": "SyntaxError: invalid syntax",
                "error_log": f"  File \"<string>\", line 1\n    {code_str}\n                  ^\nSyntaxError: invalid syntax",
                "language": "python",
                "description": "The Python parser encounters code that does not conform to the language's syntax, such as an incomplete statement. Generated using exec().",
                "buggy_code_snippet": "# SyntaxError: The statement is incomplete.\nexec('version = 3.10.')"
            },
            "fixed_code_snippet": "# Fix: Complete the statement with valid syntax.\ncode_to_run = 'version = 3.10'\nexec(code_to_run)\nprint('Code executed successfully')"
        }

    def generate_complex_case(self):
        code_str = "print('Hello' "
        return {
            "error_context": {
                "title": "SyntaxError: unterminated string literal",
                "error_log": f"  File \"<string>\", line 1\n    {code_str}\n           ^\nSyntaxError: unterminated string literal (detected at line 1)",
                "language": "python",
                "description": "A string literal is missing its closing quotation mark. Generated using exec().",
                "buggy_code_snippet": "# SyntaxError: The string is not closed properly.\nexec(\"print('Hello' \")"
            },
            "fixed_code_snippet": "# Fix: Add the closing parenthesis and quotation mark.\ncode_to_run = \"print('Hello')\"\nexec(code_to_run)"
        }

class IndentationErrorGenerator(BaseErrorGenerator):
    def generate_simple_case(self):
        # Use repr() to safely represent the string with newlines in the f-string
        code_str = 'def my_function():\\nprint("This is wrong")'
        return {
            "error_context": {
                "title": "IndentationError: expected an indented block",
                "error_log": "  File \"<string>\", line 2\n    print(\"This is wrong\")\n    ^\nIndentationError: expected an indented block after function definition on line 1",
                "language": "python",
                "description": "A code block that requires indentation (e.g., after a 'def', 'if', or 'for') is missing it. Generated using exec().",
                "buggy_code_snippet": f"# IndentationError: The line after the function definition is not indented.\ncode_to_run = {repr(code_str)}\nexec(code_to_run)"
            },
            "fixed_code_snippet": "# Fix: Add the correct indentation (usually 4 spaces).\ncode_to_run = 'def my_function():\\n    print(\"This is correct\")'\nexec(code_to_run)"
        }

    def generate_complex_case(self):
        code_str = 'for i in range(5):\\n    print(i)\\n  print("done")'
        return {
            "error_context": {
                "title": "IndentationError: unindent does not match any outer indentation level",
                "error_log": "  File \"<string>\", line 3\n    print(\"done\")\n    ^\nIndentationError: unindent does not match any outer indentation level",
                "language": "python",
                "description": "A line is indented at a level that does not match any of the previous indentation levels. Generated using exec().",
                "buggy_code_snippet": f"# IndentationError: The indentation of the last line is incorrect.\ncode_to_run = {repr(code_str)}\nexec(code_to_run)"
            },
            "fixed_code_snippet": "# Fix: Align the indentation level correctly.\ncode_to_run = 'for i in range(5):\\n    print(i)\\nprint(\"done\")' # Unindented to be outside the loop\nexec(code_to_run)"
        }
        
# --- Main Generation Function ---
def generate_dataset(num_examples, output_file):
    """Generates a dataset of error examples with the requested final structure."""
    
    error_generators = [
        # Original
        TypeErrorGenerator(),
        IndexErrorGenerator(),
        KeyErrorGenerator(),
        AttributeErrorGenerator(),
        NameErrorGenerator(),
        # Newly Added
        ZeroDivisionErrorGenerator(),
        RecursionErrorGenerator(),
        ModuleNotFoundErrorGenerator(),
        FileNotFoundErrorGenerator(),
        PermissionErrorGenerator(),
        SyntaxErrorGenerator(),
        IndentationErrorGenerator(),
    ]
    
    # [변경점 1] numpy 임포트 확인 로직 변경
    try:
        import numpy as np_check
        error_generators.append(NumpyValueErrorGenerator())
    except ImportError:
        print("⚠️ Warning: numpy is not installed. Skipping NumpyValueError examples.")

    with open(output_file, 'w', encoding='utf-8') as f:
        for i in range(num_examples):
            generator = random.choice(error_generators)
            error_data = generator()
            # Save in JSONL format, one JSON object per line.
            f.write(json.dumps(error_data) + '\n')
            
    print(f"✅ Success! Generated {num_examples} examples in '{output_file}'.")

# --- How to Use ---
if __name__ == "__main__":
    number_of_examples = 15000 # Increased to cover more variety
    output_filename = 'error333.jsonl'
    
    generate_dataset(number_of_examples, output_filename)