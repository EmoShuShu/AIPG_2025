import re

input_file = "AMTR_2025.md"
output_file = "parallel.txt"

def clean_line(line):
    """去掉注释符号 > 和收尾空格"""
    return line.lstrip(">").strip()

def is_english(line):
    return bool(re.search(r"[A-Za-z]", line)) and not bool(re.search(r"[\u4e00-\u9fff]", line))

def is_chinese(line):
    return bool(re.search(r"[\u4e00-\u9fff]", line))

def prompt_user():
    while True:
        choice = input("请选择处理正文(body)还是注释(comment)：").strip().lower()
        if choice in ["body", "comment"]:
            return choice
        print("输入无效，请重新输入：body 或 comment")

# 用户选择模式
mode = prompt_user()
process_comment = (mode == "comment")

eng_block = []
zh_block = []
pairs = []
state = "eng"  # 当前在积累英文组还是中文组

with open(input_file, "r", encoding="utf-8") as f:
    for raw in f:
        original_line = raw.rstrip("\n")

        # 判断是否处理这一行（正文或注释）
        is_comment_line = original_line.strip().startswith(">")
        if process_comment != is_comment_line:
            continue  # 跳过不属于本次处理模式的部分

        line = clean_line(original_line)

        if not line:
            continue  # 跳过空行

        if is_english(line):
            if state == "zh":
                # 上一组中文结束，进行配对
                for e, z in zip(eng_block, zh_block):
                    pairs.append((e, z))
                eng_block = []
                zh_block = []
                state = "eng"
            eng_block.append(line)

        elif is_chinese(line):
            if state == "eng":
                state = "zh"
            zh_block.append(line)

# 文件末尾仍有未配对的 block，需要处理
if eng_block and zh_block:
    for e, z in zip(eng_block, zh_block):
        pairs.append((e, z))

# 输出最终结果
with open(output_file, "w", encoding="utf-8") as f:
    for en, zh in pairs:
        f.write(f"{en} ||| {zh}\n")

print(f"处理完成，共生成 {len(pairs)} 对平行语料，输出至 {output_file}")
