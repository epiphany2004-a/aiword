import os
from openai import OpenAI
import sys
import concurrent.futures
import json
from typing import List, Dict
import time
import random
import re
import base64
from google import genai
from google.genai import types


class config:
    gemini_api_key_proxies=['sk-NnnfVt8qOw1fjLJTAioOqskes58DzrQrd5Whm1jb4iFBZUaW',
                    'sk-5Cn0qnkYfOcLU34QSqZAhv3qIQFYCsjItxJecBLwm3FibE89',
                    'sk-NnnfVt8qOw1fjLJTAioOqskes58DzrQrd5Whm1jb4iFBZUaW',
                    'sk-VwuzXf5AFpqHpsV8voGB8St4ghUcQASu8Qb4en0sDgBEHE2E',
                    'sk-ZHXuoH6fWM3whCI7mHs5WmLhm8YyhTpD0jUJOeftf7tkTeRq',
                    'sk-Bo4rszk4F0k0YP95N36i0tphfq2vy7cpDN8zA1dBbatDB9vx'
    
    
    ]
    deepseek_api_key_proxies=['sk-e55b7cdf0c904972a19ebff027810be4','sk-4aea9785847f4d1984804181d8c5ac6c',
                              'sk-2bca7d408bd14f3a8cafa84e720d16a5','sk-1c727fbfd020451fa9e1675ef79aac73',
                              'sk-b5fc0a867ceb441c96f23dc02d32ffb7']
class ChatAgent:
    def __init__(self, api_key=None, base_url=None):
        """
        初始化聊天代理
        
        Args:
            api_key (str): OpenAI API密钥
            base_url (str): API基础URL
        """
        self.client = OpenAI(
            api_key=api_key or 'sk-flkc4hxNDiW41zPVfBF8om9EO8lkFY19lLbSdAgceg7LF3Ko',
            base_url=base_url or "https://api.aiclaude.site/v1"
        )
        self.model = "gemini-2.5-pro-exp-03-25"
        self.conversation_history = []

    def add_message(self, role, content):
        """
        添加消息到对话历史
        
        Args:
            role (str): 消息角色 ('user' 或 'assistant')
            content (str): 消息内容
        """
        self.conversation_history.append({"role": role, "content": content})

    def chat(self, prompt):
        """
        普通对话方法
        
        Args:
            prompt (str): 用户输入的提示文本
        
        Returns:
            str: 模型的响应
        """
        try:
            self.add_message("user", prompt)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history
            )
            response_content = response.choices[0].message.content
            self.add_message("assistant", response_content)
            return response_content
        except Exception as e:
            return f"发生错误: {str(e)}"

    def chat_stream(self, prompt):
        """
        流式对话方法
        
        Args:
            prompt (str): 用户输入的提示文本
        """
        try:
            self.add_message("user", prompt)
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                stream=True
            )
            
            print("AI: ", end="", flush=True)
            full_response = ""
            for chunk in stream:
                try:
                    if chunk.choices[0].delta.reasoning_content is not None:
                        reasoning = chunk.choices[0].delta.reasoning_content
                        print(reasoning, end="", flush=True)
                except:
                    pass
                try:
                    if chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        print(content, end="", flush=True)
                        full_response += content                    
                except:
                    pass

            
            self.add_message("assistant", full_response)

            return full_response
            
        except Exception as e:
            print(f"发生错误: {str(e)}")

    def clear_history(self):
        """清除对话历史"""
        self.conversation_history = []

    def set_system_prompy(self,prompt):
        self.conversation_history.append({"role": "system", "content": prompt})

def gemini_get_words_agent(word):
    # 创建聊天代理实例
    agent = ChatAgent(api_key=config.gemini_api_key_proxies[random.randint(0, len(config.gemini_api_key_proxies) - 1)])
    prompt ="""# 角色
            你是一位语言学专家和创意记忆大师，你的任务是为一款AI背单词应用提供高质量、结构化的单词学习内容。你需要确保信息的准确性，并且让助记内容和例句充满创意、易于理解和实用。

            # 任务
            根据我提供的英文单词，生成一个包含其详细信息的JSON对象。请严格遵循下面定义的JSON结构和内容要求。

            # 输出格式 (JSON结构)
            {
            "word": "单词本身",
            "phonetic": "国际音标 (IPA)",
            "definitions": [
                {
                "partOfSpeech": "词性 (例如: v., n., adj.)",
                "meaning": "中文释义"
                }
            ],
            "mnemonics": {
                "homophone": "【谐音助记】通过有趣的谐音联想来帮助记忆。",
                "etymology": "【词根词缀】通过拆解单词的词根、词缀来解释其构成和本意。"
            },
            "examples": [
                {
                "en": "包含目标单词的英文例句。",
                "cn": "对应例句的中文翻译。"
                }
            ]
            }

            # 要求与规则
            1.  **严格JSON格式**：你的回复必须是一个完整的、格式正确的JSON对象，不要在JSON代码块前后添加任何额外的解释或文字。
            2.  **内容语言**：除`word`, `phonetic` 和 `examples`中的`en`字段外，所有内容都必须使用**简体中文**。
            3.  **助记内容质量**：
                *   `homophone`：必须有趣且逻辑自洽。
                *   `etymology`：必须准确，基于真实的词源学。
            4.  **例句质量**：请提供1个实用且常见的例句。英文例句必须自然地包含目标单词。
            5.  **处理空缺**：如果某个助记方法不适用于当前单词，请返回一个空字符串 `""` 作为其值，但不要省略该字段。

            # 示例 (Example)
            如果输入的单词是 "disguise"，你应该输出如下格式：
            ```json
            {
            "word": "disguise",
            "phonetic": "/dɪsˈɡaɪz/",
            "definitions": [
                {
                "partOfSpeech": "v.",
                "meaning": "伪装；假扮；掩饰"
                },
                {
                "partOfSpeech": "n.",
                "meaning": "伪装；伪装用品；假装"
                }
            ],
            "mnemonics": {
                "homophone": "dis(这个) + guise(音近'guys', 家伙们) -> '这个家伙'不是他本人，他只是在'伪装'。",
                "etymology": "词根: dis- (否定, 相反) + guise (样子, 外观) -> 使外观变得不同 -> 伪装。"
            },
            "examples": [
                {
                "en": "He made no attempt to disguise his accent.",
                "cn": "他没有试图掩饰自己的口音。"
                }
            ]
            }
            ```
            """
    agent.set_system_prompy(prompt)
    # 测试流式输出
    user_input = word
    print(f"用户: {user_input}")    
    response = agent.chat(user_input)  # 直接使用返回值
    print(f"AI: {response}")
    return response
    

def extract_json_from_text(text: str) -> Dict:
    """
    从文本中提取JSON内容
    
    Args:
        text (str): 包含JSON的文本
        
    Returns:
        Dict: 提取的JSON对象
    """
    try:
        # 尝试直接解析
        return json.loads(text)
    except json.JSONDecodeError:
        # 如果直接解析失败，尝试提取JSON部分
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(json_pattern, text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 如果还是失败，尝试提取最外层的花括号内容
        brace_pattern = r'\{[\s\S]*\}'
        match = re.search(brace_pattern, text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        
        raise ValueError("无法从文本中提取有效的JSON内容")

def gemini_process_word_list(word_list: List[str], max_workers: int = 20) -> List[Dict]:
    """
    并发处理单词列表
    
    Args:
        word_list (List[str]): 要处理的单词列表
        max_workers (int): 最大并发数
        
    Returns:
        List[Dict]: 处理结果列表
    """
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_word = {executor.submit(gemini_get_words_agent, word): word for word in word_list}
        
        # 收集结果
        for future in concurrent.futures.as_completed(future_to_word):
            word = future_to_word[future]
            try:
                result = future.result()
                # 提取JSON内容
                try:
                    json_result = extract_json_from_text(result)
                    results.append(json_result)
                    print(f"完成处理单词: {word}")
                except ValueError as e:
                    print(f"警告: 单词 '{word}' 的响应无法提取JSON: {str(e)}")
                    continue
            except Exception as e:
                print(f"处理单词 '{word}' 时发生错误: {str(e)}")
    
    return results

def deepseek_agent_get_sentence(word):
    """
    使用DeepSeek生成句子填空题
    
    Args:
        word (str): 目标单词
        
    Returns:
        str: 生成的句子填空题JSON
    """
    agent = ChatAgent(
        api_key=config.deepseek_api_key_proxies[random.randint(0, len(config.deepseek_api_key_proxies) - 1)],
        base_url="https://api.deepseek.com"
    )
    agent.model = "deepseek-reasoner"
    
    prompt = """你是一位英语教育专家，专门为单词复习创建填空题。请根据给定的单词，生成一个包含以下结构的JSON对象：

{
"sentence_template": "包含________的英文句子模板",
"correct_answer": "正确的单词",
"options": [
    {
    "word": "正确单词",
    "definition": "中文释义"
    },
    {
    "word": "干扰词1",
    "definition": "中文释义"
    },
    {
    "word": "干扰词2", 
    "definition": "中文释义"
    },
    {
    "word": "干扰词3",
    "definition": "中文释义"
    }
],
"main_sentence_details": {
    "en": "完整的英文句子，正确单词用<strong>标签包围",
    "cn": "完整的中文翻译"
}
}

要求：
1. 句子模板要自然、实用
2. 干扰词要与正确单词形似或音似，但意思不同
3. 所有释义使用中文
4. 严格按JSON格式输出，不要添加其他文字"""
    
    agent.set_system_prompy(prompt)
    response = agent.chat_stream(f"请为单词 '{word}' 生成一个句子填空题。")
    return response

def deepseek_process_sentence_list(word_list: List[str], max_workers: int = 5) -> List[Dict]:
    """
    并发处理单词列表，生成句子填空题
    
    Args:
        word_list (List[str]): 要处理的单词列表
        max_workers (int): 最大并发数，建议不要太高避免API限制
        
    Returns:
        List[Dict]: 处理结果列表
    """
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_word = {executor.submit(deepseek_agent_get_sentence, word): word for word in word_list}
        
        # 收集结果
        for future in concurrent.futures.as_completed(future_to_word):
            word = future_to_word[future]
            try:
                result = future.result()
                # 提取JSON内容
                try:
                    json_result = extract_json_from_text(result)
                    results.append(json_result)
                    print(f"✅ 完成处理单词: {word}")
                except ValueError as e:
                    print(f"❌ 警告: 单词 '{word}' 的响应无法提取JSON: {str(e)}")
                    print(f"原始响应: {result}")
                    continue
            except Exception as e:
                print(f"❌ 处理单词 '{word}' 时发生错误: {str(e)}")
    
    return results

def deepseek_agent_get_essay_structure(essay_title,essay_content):
    agent = ChatAgent(
        api_key=config.deepseek_api_key_proxies[random.randint(0, len(config.deepseek_api_key_proxies) - 1)],
        base_url="https://api.deepseek.com"
    )
    agent.model = "deepseek-reasoner"
    system_prompt = """你是一位专业的英语写作评分专家，专门为英语作文提供详细的评分和修改建议。

请根据给定的作文题目和内容，生成一个包含以下结构的JSON对象：

```json
{
    "score": "一个介于1到20之间的整数，代表你的综合评分（大作文满分20，小作文满分10）。",
    "radarData": [
        "一个包含5个整数的数组，分别代表以下五个维度的得分（每项满分4分）：[逻辑结构, 词汇丰富度, 句式多样性, 语法准确性, 论证相关性]"
    ],
    "suggestions": [
        {
            "id": "一个从1开始递增的唯一数字ID",
            "text": "原文中你识别出的、可以改进的单词、短语或整个句子",
            "type": "问题类型，必须是以下四种之一：'upgradeable' (词汇可升级), 'repetitive' (重复使用), 'incorrect' (用词不当/错误), 'sentence_structure' (句式可优化)",
            "suggestion": "你提供的、更高级或更地道的替换建议（可以是词、短语或重写后的整个句子）"
        }
    ]
}
```

评分标准：
1. **逻辑结构 (0-4分)**：文章结构清晰，段落组织合理，逻辑连贯
2. **词汇丰富度 (0-4分)**：词汇使用准确、丰富，避免重复
3. **句式多样性 (0-4分)**：句式变化多样，避免单调
4. **语法准确性 (0-4分)**：语法正确，拼写准确
5. **论证相关性 (0-4分)**：论证充分，与主题相关

建议要求：
- 至少提供5-10个具体的修改建议
- 建议要具体、实用、可操作
- 重点关注词汇升级、句式优化、语法错误修正
- 确保建议的改进能提升文章质量

示例输出：
```json
{
    "score": 16,
    "radarData": [4, 3, 3, 4, 4],
    "suggestions": [
        {
            "id": 1,
            "text": "shown in the picture",
            "type": "upgradeable",
            "suggestion": "vividly depicted in the cartoon"
        },
        {
            "id": 2,
            "text": "put together",
            "type": "upgradeable",
            "suggestion": "harmoniously blended"
        },
        {
            "id": 3,
            "text": "very",
            "type": "repetitive",
            "suggestion": "extremely"
        },
        {
            "id": 4,
            "text": "People can now easily enjoy food from other countries, which is a good thing.",
            "type": "sentence_structure",
            "suggestion": "The newfound accessibility of international cuisine not only enriches our daily lives but also fosters cross-cultural understanding."
        }
    ]
}
```

请严格按照JSON格式输出，不要添加其他解释文字。"""
    
    agent.set_system_prompy(system_prompt)
    user_prompt = f"请为以下作文进行评分和修改建议：\n\n题目：{essay_title}\n\n内容：{essay_content}"
    response = agent.chat_stream(user_prompt)
    print('==========================================')
    print('作文评分结果：',response)
    return response

def gemini_ocr(image_list):
    """
    使用Gemini进行OCR识别，支持多张图片。
    image_list: [(file_path, mime_type), ...] 或 [(bytes, mime_type), ...]
    """
    client = genai.Client(api_key="AIzaSyACDHvJG3P_NH81KTiWyIiP-MK08scXtRA")

    # 文本提示
    prompt = '''请识别这些图片中的所有文字内容，用中文回答。
包括英文和中文。请准确提取所有可见的文本，保持原有的格式和结构。
如果是图像或者表格，请用最简洁的文字描述，不含个人观点与情感。

# 输出格式
{
    "title": "识别到的题目",
    "writing": "识别到的作文内容"
}
example:
{
    "title": "Write an essay of 160-200 words based on the following drawing. In your essay, you should\n            1) describe the drawing briefly,\n            2) explain its intended meaning, and\n            3) give your comments.\n            You should write neatly on ANSWER SHEET 2. (20 points)\n\n            [图片内容描述：一张漫画图，其中包含两名男性人物和中文文字。\n            左侧男子沮丧地抱头，上方有文字气泡写着："全完了！"\n            右侧男子面带笑容，手指下方，上方有文字气泡写着："幸好还剩点儿。"\n            两名男子之间，地面上有一个破裂的瓶子，瓶中的液体似乎已大部分洒出。]",
    "writing": "This picture shows us a very interesting scene. There are two man looking at a broken bottle on the ground. Most of the water inside is gone. The man on the left looks very sad, he think all is lost. But the man on the right is smile. He is happy because there is still a little water left in the bottle. They have a very different reaction to the same thing....."
}
'''

    contents = [prompt]

    if not image_list:
        raise ValueError("image_list不能为空")

    # 处理第一张图片（上传文件）
    first_img = image_list[0]
    if isinstance(first_img[0], str):
        # 文件路径
        uploaded_file = client.files.upload(file=first_img[0])
        contents.append(uploaded_file)
    elif isinstance(first_img[0], bytes):
        # bytes
        contents.append(
            types.Part.from_bytes(
                data=first_img[0],
                mime_type=first_img[1]
            )
        )
    else:
        raise ValueError("image_list中的元素应为(文件路径, mime_type)或(bytes, mime_type)")

    # 处理剩余图片（bytes方式）
    for img in image_list[1:]:
        if isinstance(img[0], str):
            with open(img[0], 'rb') as f:
                img_bytes = f.read()
            contents.append(
                types.Part.from_bytes(
                    data=img_bytes,
                    mime_type=img[1]
                )
            )
        elif isinstance(img[0], bytes):
            contents.append(
                types.Part.from_bytes(
                    data=img[0],
                    mime_type=img[1]
                )
            )
        else:
            raise ValueError("image_list中的元素应为(文件路径, mime_type)或(bytes, mime_type)")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents
    )

    print(response.text)
    return response.text

def deepseek_get_words_agent(word):
    """
    使用DeepSeek生成单词学习内容，结构与gemini_get_words_agent一致。
    """
    agent = ChatAgent(
        api_key=config.deepseek_api_key_proxies[random.randint(0, len(config.deepseek_api_key_proxies) - 1)],
        base_url="https://api.deepseek.com"
    )
    agent.model = "deepseek-reasoner"
    prompt = '''# 角色
你是一位语言学专家和创意记忆大师，你的任务是为一款AI背单词应用提供高质量、结构化的单词学习内容。你需要确保信息的准确性，并且让助记内容和例句充满创意、易于理解和实用。

# 任务
根据我提供的英文单词，生成一个包含其详细信息的JSON对象。请严格遵循下面定义的JSON结构和内容要求。

# 输出格式 (JSON结构)
{
"word": "单词本身",
"phonetic": "国际音标 (IPA)",
"definitions": [
    {
    "partOfSpeech": "词性 (例如: v., n., adj.)",
    "meaning": "中文释义"
    }
],
"mnemonics": {
    "homophone": "【谐音助记】通过有趣的谐音联想来帮助记忆。",
    "etymology": "【词根词缀】通过拆解单词的词根、词缀来解释其构成和本意。"
},
"examples": [
    {
    "en": "包含目标单词的英文例句。",
    "cn": "对应例句的中文翻译。"
    }
]
}

# 要求与规则
1.  **严格JSON格式**：你的回复必须是一个完整的、格式正确的JSON对象，不要在JSON代码块前后添加任何额外的解释或文字。
2.  **内容语言**：除`word`, `phonetic` 和 `examples`中的`en`字段外，所有内容都必须使用**简体中文**。
3.  **助记内容质量**：
    *   `homophone`：必须有趣且逻辑自洽。
    *   `etymology`：必须准确，基于真实的词源学。
4.  **例句质量**：请提供1个实用且常见的例句。英文例句必须自然地包含目标单词。
5.  **处理空缺**：如果某个助记方法不适用于当前单词，请返回一个空字符串 `""` 作为其值，但不要省略该字段。
# 示例 (Example)
            如果输入的单词是 "disguise"，你应该输出如下格式：
            ```json
            {
            "word": "disguise",
            "phonetic": "/dɪsˈɡaɪz/",
            "definitions": [
                {
                "partOfSpeech": "v.",
                "meaning": "伪装；假扮；掩饰"
                },
                {
                "partOfSpeech": "n.",
                "meaning": "伪装；伪装用品；假装"
                }
            ],
            "mnemonics": {
                "homophone": "dis(这个) + guise(音近'guys', 家伙们) -> '这个家伙'不是他本人，他只是在'伪装'。",
                "etymology": "词根: dis- (否定, 相反) + guise (样子, 外观) -> 使外观变得不同 -> 伪装。"
            },
            "examples": [
                {
                "en": "He made no attempt to disguise his accent.",
                "cn": "他没有试图掩饰自己的口音。"
                }
            ]
            }
            ```
'''
    agent.set_system_prompy(prompt)
    user_input = word
    print(f"用户: {user_input}")    
    response = agent.chat_stream(user_input)  # 直接使用返回值
    print(f"DeepSeek AI: {response}")
    return response

def deepseek_process_word_list(word_list: List[str], max_workers: int = 20) -> List[Dict]:
    """
    并发处理单词列表，使用deepseek_get_words_agent生成单词学习内容。
    Args:
        word_list (List[str]): 要处理的单词列表
        max_workers (int): 最大并发数
    Returns:
        List[Dict]: 处理结果列表
    """
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_word = {executor.submit(deepseek_get_words_agent, word): word for word in word_list}
        for future in concurrent.futures.as_completed(future_to_word):
            word = future_to_word[future]
            try:
                result = future.result()
                try:
                    json_result = extract_json_from_text(result)
                    results.append(json_result)
                    print(f"完成处理单词: {word}")
                except ValueError as e:
                    print(f"警告: 单词 '{word}' 的响应无法提取JSON: {str(e)}")
                    continue
            except Exception as e:
                print(f"处理单词 '{word}' 时发生错误: {str(e)}")
    return results

if __name__ == "__main__":
    # 测试OCR功能
    print("测试OCR功能...")
    
    img_path = "api/test.png"
    with open(img_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    print(gemini_ocr([(img_path, 'image/png')]))

    # image_list应该是一个包含(文件路径, mime类型)元组的列表
    # 每个元组代表一张图片
    # image_list = [
    #     ('api/test.png', 'image/png'), 
    #     ('api/test2.png', 'image/png')
    # ]
    # print(gemini_ocr(image_list))
    # # pass
    # word_list = ['disguise','people']
    # print(deepseek_process_word_list(word_list))


