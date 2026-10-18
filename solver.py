import ast
import operator
from sympy import symbols, sympify, solve, Eq
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application

# --- الجزء الأول: الحساب العادي الآمن ---
SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

def safe_eval(node):
    if isinstance(node, ast.Num): # لتوافق بايثون القديم
        return node.n
    elif isinstance(node, ast.Constant): # لتوافق بايثون الجديد
        return node.value
    elif isinstance(node, ast.BinOp):
        return SAFE_OPS[type(node.op)](safe_eval(node.left), safe_eval(node.right))
    elif isinstance(node, ast.UnaryOp):
        return SAFE_OPS[type(node.op)](safe_eval(node.operand))
    else:
        raise ValueError("عملية غير مسموحة")

def solve_arithmetic(expr: str):
    expr = expr.replace("×", "*").replace("÷", "/").replace("^", "**")
    try:
        tree = ast.parse(expr, mode="eval")
        result = safe_eval(tree.body)
    except Exception:
        return None, ["⚠️ تعبير حسابي غير صالح"]
    
    steps = [
        f"📥 التعبير: {expr}",
        f"🔢 نطبق ترتيب العمليات (أقواس → أس → ضرب/قسمة → جمع/طرح)",
        f"✅ الناتج: {result}"
    ]
    return result, steps

# --- الجزء الثاني: حل المعادلات ---
x, y = symbols('x y')

def solve_equation(expr: str):
    try:
        transformations = standard_transformations + (implicit_multiplication_application,)
        if "=" in expr:
            left, right = expr.split("=")
            eq = Eq(parse_expr(left, transformations=transformations),
                    parse_expr(right, transformations=transformations))
        else:
            eq = parse_expr(expr, transformations=transformations)
        
        solutions = solve(eq, x)
        if not solutions:
            return None, ["⚠️ لم يتم إيجاد حل للمعادلة"]
        
        steps = [
            f"📥 المعادلة: {expr}",
            "1️⃣ نرتب المعادلة ونبسطها",
            f"2️⃣ نحل بالنسبة للمجهول x",
            f"✅ الحل: x = {', '.join(str(s) for s in solutions)}"
        ]
        return solutions, steps
    except Exception as e:
        return None, [f"⚠️ خطأ في قراءة المعادلة: {str(e)}"]

# --- الجزء الثالث: تحويل الأنظمة ---
def decimal_to_binary(n: int):
    if n == 0: return "0", ["📥 العدد: 0", "✅ الناتج: 0"]
    steps = [f"📥 العدد: {n} (عشري) → ثنائي", ""]
    remainders = []
    i = 1
    temp = n
    while temp > 0:
        remainder = temp % 2
        steps.append(f"{i}️⃣ {temp} ÷ 2 = {temp // 2} والباقي {remainder}")
        remainders.append(str(remainder))
        temp //= 2
        i += 1
    result = "".join(reversed(remainders))
    steps.append("")
    steps.append(f"📖 نقرأ البواقي من الأسفل للأعلى: {result}")
    steps.append(f"✅ الناتج: {result}")
    return result, steps

def binary_to_decimal(binary: str):
    binary = binary.strip()
    steps = [f"📥 العدد: {binary} (ثنائي) → عشري", ""]
    total = 0
    length = len(binary)
    for i, digit in enumerate(binary):
        power = length - i - 1
        value = int(digit) * (2 ** power)
        steps.append(f"{i+1}️⃣ {digit}×2^{power} = {value}")
        total += value
    steps.append(f"✅ الناتج: {total}")
    return total, steps

def decimal_to_hex(n: int):
    if n == 0: return "0", ["📥 العدد: 0", "✅ الناتج: 0"]
    hex_chars = "0123456789ABCDEF"
    steps = [f"📥 العدد: {n} (عشري) → ست عشري", ""]
    remainders = []
    i = 1
    temp = n
    while temp > 0:
        remainder = temp % 16
        hex_char = hex_chars[remainder]
        steps.append(f"{i}️⃣ {temp} ÷ 16 = {temp // 16} والباقي {remainder} ({hex_char})")
        remainders.append(hex_char)
        temp //= 16
        i += 1
    result = "".join(reversed(remainders))
    steps.append(f"✅ الناتج: {result}")
    return result, steps

def hex_to_decimal(hex_str: str):
    hex_str = hex_str.strip().upper()
    steps = [f"📥 العدد: {hex_str} (ست عشري) → عشري", ""]
    total = 0
    length = len(hex_str)
    for i, char in enumerate(hex_str):
        power = length - i - 1
        value = int(char, 16) * (16 ** power)
        steps.append(f"{i+1}️⃣ {char}×16^{power} = {value}")
        total += value
    steps.append(f"✅ الناتج: {total}")
    return total, steps
