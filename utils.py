import json
import os
from typing import Literal
from datetime import datetime
import sys

log_path = os.path.join(os.path.dirname(__file__),'logs.log')
log_path = os.path.abspath(log_path)
sys_instruction = """The `sort_image` tool contains the complete and authoritative list of allowed categories in its `category` enum. Categories may be built-in or custom. Treat every enum value as an opaque label: preserve its spelling, capitalization, spaces, punctuation, and accents exactly.

## Decision process

1. Inspect the entire image.
2. Compare the visible content with every available category label and its meaning.
3. Select the one category that best describes the main subject or purpose of the image.
4. When several categories fit, choose the most specific one. When the image is unclear, choose the best broad category that exists in the enum.
5. Never invent, rewrite, normalize, combine, or abbreviate a category. Never use a fallback such as `other` unless it is explicitly present in the enum.

Classify visible content only. Do not guess hidden content, file metadata, location, date, photographer, or intent. A readable text image should use a document or text-related category when one exists. A person-focused image should use a people or portrait-related category when one exists. Use the exact custom label supplied by the tool when it is the best match.

## Output contract

Your only output must be exactly one call to `sort_image`. Do not output explanations, markdown, plain-text JSON, greetings, or multiple calls. Pass exactly one argument field:

`{"category":"<one exact enum value>"}`

Call `sort_image` exactly once. Never call any other tool."""

def load_config(path:str=r'.\config.json'):
    if not path.endswith(".json"):
        path+=".json"
    
    if not os.path.exists(path):
        print("Config Not Found!")
        return None
    with open(path,'r') as f:
        config = json.load(f)
    return config

def log(line:str,path:str=log_path,level:Literal["DEBUG","INFO","WARN","ERROR","FATAL"]="INFO"):
    d = {
        "timestamp": datetime.now().strftime(r"%A, %d-%B-%Y, %I:%M %p"),
        "level": level,
        "details":line
    }
    with open(path,'a') as file:
        file.write(json.dumps(d)+'\n')

def load_instruction(path:str=r".\instructions.md"):
    if not os.path.exists(path):
        return "Sort the given image."
    with open(path,'r') as f:
        instructions = f.read()
    return instructions

def load_schema(path:str):
    with open(path,'r') as f:
        return json.load(f)

categories = load_schema(r".\categories.json").get("categories",[])
tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "sort_image",
            "description": "Sort the image into exactly one category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": categories
                    }
                },
                "required": ["category"],
                "additionalProperties": False
            }
        }
    }
]