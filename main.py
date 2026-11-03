from openai import OpenAI, BadRequestError, APIConnectionError
import os
import time
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
import base64
import json
from threading import Thread

import utils

os.chdir(os.path.dirname(__file__))

config = utils.load_config()
if not config:
    exit(1)
url = config.get("base_url","http://127.0.0.1")
port = config.get("port",None)
api = config.get("api_key")
model = config.get("model")
sec = config.get("connection_retry",60)
max_attempt = 3
save = os.path.abspath(config.get("save_location",r".\output"))
if not (url and api and model):
    print("Invalid config.json, required fields: 'url', 'api', 'model'")
    exit(2)

client = OpenAI(base_url=f"{url}:{port}",api_key=api) if port else OpenAI(base_url=url,api_key=api)


sys_prompt = utils.sys_instruction
custom_instructions = utils.load_instruction()
def get_img_category(img_path:str):
    attempt=0
    while True: #Checkpoint alpha
        try:
            with open(img_path,'rb') as f:
                b64_img = base64.b64encode(f.read()).decode("utf-8")
        except (FileNotFoundError,OSError) as e:
            utils.log(level="ERROR",line=f"Image Source Not Found Error; line 36 [{e}]")
            start_time = time.time();elapsed = 0
            retry = 30
            while retry>elapsed:
                elapsed = time.time() - start_time
                live.update(info + f"\n[red]Image Source Not Found, Did you disconnect the disk?. Retrying in {retry - elapsed:.1f}sec...[/]",refresh=True)
                time.sleep(0.1)
            live.update(info, refresh=True)
            continue
        break
    _,ext = os.path.splitext(img_path)
    ext = ext[1:]
    encoded_img = f"data:image/{ext};base64,{b64_img}"
    msg = [
        {"role":"system","content":sys_prompt},
        {"role":"user","content":[{"type":"image_url","image_url":{"url":encoded_img}},{"type":"text","text":custom_instructions}]}
    ]
    while True: #Checkpoint Beta
        try:
            response = client.chat.completions.create(
                messages=msg,
                model=model,
                tools=utils.tools_schema
            )
        except (ConnectionError,APIConnectionError) as e:
            utils.log(level="ERROR",line=f"Connection Error; line 42 [{e}]")
            s_t = time.time();elapsed = 0
            while sec-1>elapsed:
                elapsed = time.time() - s_t
                live.update(info + f"\n[red]Connection Error. Retrying in {sec - elapsed:.1f}sec...[/]",refresh=True)
                time.sleep(0.1)
            live.update(info, refresh=True)
            continue
        except BadRequestError as e:
            if attempt>=max_attempt:
                attempt = 0
                #utils.log(level="WARN",line=f"Due to BadRequest Error Image {count} [{img_path}] was skipped!")
                return "skip"
            attempt += 1
            #utils.log(level="ERROR",line=f"Bad Request Error ({attempt}/{max_attempt}); line 42 [{e}]")
            live.update(info + f"\n[red]Bad Request Error. Retrying Attempt {attempt}/{max_attempt}...[/]",refresh=True)
            time.sleep(3)
            #live.update(info, refresh=True)
            continue

        if not response.choices[0].message.tool_calls:
            utils.log(level="WARN",line=f"Category not generated; line 46. [Content: {response.choices[0].message.content}]")
            continue
        tool_call = response.choices[0].message.tool_calls[0]
        args = json.loads(tool_call.function.arguments)
        category = args.get("category")

        #Checks:
        if not category:
            utils.log(level="WARN",line=f"Tool_call has no args! [Tool Call: {tool_call}][Args: {args}]")
            continue
        if category not in utils.categories:
            utils.log(level="WARN",line=f"Incorrect category generated; line57. [Tool Call {tool_call}][Categoty: {category}]")
            continue
        return category

def copy(source:str,destination_dir:str,name:str=None):
    if not name:
        name = os.path.basename(source)
    with open(source,'rb') as f:
        source_file_data = f.read()
    os.makedirs(destination_dir,exist_ok=True)
    destination = os.path.join(destination_dir,name)
    copy=0

    while True:
        if os.path.exists(destination):
            copy+=1
            name,ext = os.path.splitext(name)
            destination = os.path.join(destination_dir,name+f'({copy})'+ext)
            name = name+ext
            continue
        break

    with open(destination,'wb') as f:
        f.write(source_file_data)

def progress_bar(complete:int,total:int,width:int=50):
    comp_bar = "#"
    emp_bar = "-"
    if complete<=0:
        return emp_bar*width
    elif complete>=total:
        return comp_bar*width
    comp = int((complete/total)*width)
    prog_bar = comp_bar*comp + emp_bar*(width-comp)
    return prog_bar

def format_time(sec:float):
    if not sec:
        return None
    m = int(sec//60)
    hr = m//60
    day = hr//24
    week = day//7
    return f"{str(week)+' Week(s) ' if week else ''}{str(day%7)+' Day(s) ' if day else ''}{str(hr%24)+' Hr(s) ' if hr else ''}{str(m%60)+' Min(s) ' if m else ''}{str(round(sec%60))+' Sec ' if sec else ''}"

def avg(l:list):
    if not l:
        return None
    return sum(l)/len(l)



img_ext = (".jpeg",".png",".jpg")

console = Console()

if __name__=="__main__":
    try:
        utils.log(line="Image organizing started.")
        console.print(Markdown("# Image Organizing System"),style="red")
        console.print(f"Save Location: '{save}'",style="cyan")
        console.print(f"Categories Found: {utils.categories}",style="yellow")
        console.print(f"Logs: '{utils.log_path}'",style="red")

        while True:
            path = input("Enter Path to Images: ")
            if (path.startswith('"') and path.endswith('"')) or (path.startswith("'") and path.endswith("'")):
                path = path[1:-1]
            if os.path.exists(path):
                break
            console.print(f"Invalid Path: {path}")

        while True:
            is_resume = input("Resume Progress?(Y/n): ")
            if is_resume.lower()[0] == 'y':
                try:
                    resume = int(input("Resume Progress From(0 to cancel): "))
                except ValueError:
                    console.print("Please Enter a Valid Integer!")
                    continue
            elif is_resume.lower()[0] == 'n':
                resume = False
            else:
                console.print(f"Invalid Choice: {is_resume}")
                continue
            break

        console.print("\n")

        os.chdir(path)

        #Calculate Images:
        live = Live(refresh_per_second=10,transient=True)
        all_imgs_count=0
        live.start()
        for root,dirs,files in os.walk('./'):
            imgs = [file for file in files if file.endswith(img_ext)]
            all_imgs_count += len(imgs)
            #print(len(imgs),root)
            live.update(f"Total Found- {all_imgs_count} Files\nFolder: {root}\nCalculating...")
        live.stop()
        console.print(f"Total Files found in dir: {all_imgs_count}",style="yellow")

        if resume:
            console.print(f"Resuming From: {resume}")

        #Sort Images:
        all_files=os.walk('./')
        count=0;per_img_time = []
        with Live(auto_refresh=False,vertical_overflow="visible",) as live:
            for root,dirs,files in all_files:
                dirs.sort()
                files.sort()
                imgs = [file for file in files if file.endswith(img_ext)]
                dir_count = 0;total_dir = len(imgs)
                for img in imgs:
                    #Resume Progress:
                    if resume:
                        dir_count += 1;count += 1;resume-=1
                        continue

                    #Time Calculation:
                    start_time = time.time()
                    time_remaining = avg(per_img_time) * (all_imgs_count - count) if per_img_time else None
                    time_remaining = format_time(time_remaining)

                    path = os.path.join(root,img)

                    #Printing Info
                    info = f"[cyan]{'Current Directory: ':<30}{root} ['{os.path.abspath(root)}'][/]\n[green]{'Dir Progress: ':<30}{progress_bar(dir_count,total_dir)} | {dir_count/total_dir*100:.2f}% [{dir_count}/{total_dir}][/]\n[red]{'Total Progress: ':<30}{progress_bar(count,all_imgs_count)} | {count/all_imgs_count*100:.2f}% [{count}/{all_imgs_count}][/]\n[yellow]{'Processing: ':<30}{img} ['{os.path.abspath(path)}'][/]\n[green]{'Estimated Time Remaining:':<30}{time_remaining if time_remaining else "Estimating..."} [{round(avg(per_img_time),1) if per_img_time else 'Calculating'} sec per Image][/]"
                    live.update(info,refresh=True)

                    try:
                        category = get_img_category(path) #Main Function Call
                    except Exception as e:
                        utils.log(level="ERROR",line=f"Error raised at category generation function; line 130. [Error: {e}]")
                        dir_count += 1;count += 1
                        continue

                    dir_count += 1;count += 1

                    per_img_time.append(time.time() - start_time)
                    if len(per_img_time) > 100:
                        per_img_time = per_img_time[-99:]

                    #Custom Logic Here For Future Moda:
                    if category == "skip":
                        utils.log(level="WARN",line=f"Skipping image {count} - {img} due to BadRequestError [{os.path.abspath(path)}]")
                        continue
                    if category=="not_documents":
                        continue
                    #----------------------------------

                    save_category = os.path.join(save,category)
                    copy(source=path,destination_dir=save_category)
                    category = None

        console.print("Image Organizing completed!")
        time.sleep(5)
        input("Press Enter to exit...")

    except KeyboardInterrupt:
        console.print("\nUser Interupted; Exiting...",style="red")
        exit(0)